import asyncio
import re
from typing import Protocol, cast

from google.genai import types
from google.genai.types import Part
from pydantic import TypeAdapter
from telegram import Update, Message

from bot.handlers.base import BaseHandler
from bot.handlers.expenses import ExpensesHandler, ExpensesMessageDebouncer
from bot.models.settings import Settings
from bot.services.ai.google.genai import GenAI
from bot.services.money_provider.money_provider import MoneyProvider
from bot.utils.logger.logger import logger
from bot.models.receipt import Receipt
from bot.models.money_provider import MoneyProvider as MoneyProviderModel
from bot.utils.rate_limiter.rate_limiter import TimedRateLimiter


class AIClient(Protocol):
    async def generate_response(self, contents: list[Part], use_secondary: bool = False) -> str | None:
        ...


class PhotoHandler(BaseHandler):
    SECONDARY_MODEL_FALLBACK_DURATION_SECONDS = 120

    def __init__(
        self,
        expenses_handler: ExpensesHandler,
        config: Settings,
    ):
        self.expenses_handler = expenses_handler
        
        self.money_provider = MoneyProvider(config)
        
        self.ai_client = GenAI(config)
        self._use_secondary = False
        self._reset_use_secondary_task = None
        self.ai_limiter = TimedRateLimiter(
            max_calls=config.ai_model.quota_size,
            period_seconds=config.ai_model.quota_period_seconds,
        )
        self.ai_images_per_message_limit = config.ai_model.images_per_message_limit

        self.debouncer = ExpensesMessageDebouncer(
            config.single_message_debouncer_period_seconds,
            config.ai_model.images_per_message_limit,
        )

        self._markdown_json = re.compile(r'```(?:json)?\s*([\s\S]*?)\s*```')
        self._raw_json = re.compile(r'(\[[\s\S]*\])')

    async def extract_money_provider(self, update: Update) -> MoneyProviderModel:
        assert update.message is not None
        provider = await self.money_provider.resolve_by_caption(update.message.caption, update.message.media_group_id)
        if provider is not None:
            return provider

        assert update.effective_user is not None
        return self.money_provider.resolve_by_user_id(update.effective_user.id)

    async def _handle(self, update: Update) -> None:
        assert update.message is not None
        assert update.message.photo is not None

        money_provider = await self.extract_money_provider(update)

        await self.mark_seen(update.message)

        await self.debouncer.add_event(money_provider, update.message, self._process_messages)
        logger.debug('Added photo to debouncer %s queue', money_provider.name)

    async def _process_messages(self, messages: list[Message], money_provider: MoneyProviderModel) -> None:
        return await self.handle_with_error(messages[-1], self._process(messages, money_provider))

    async def _process(self, messages: list[Message], money_provider: MoneyProviderModel) -> None:
        contents, results = [], []
        for idx, message in enumerate(messages):
            photo_file = await message.photo[-1].get_file()

            image_part = types.Part.from_bytes(
                data=await photo_file.download_as_bytearray(),
                mime_type='image/jpeg'
            )
            contents.append(image_part)

            if len(contents) == self.ai_images_per_message_limit:
                logger.debug('Image per message limit was reached')
                start, end = idx + 1 - len(contents), idx + 1
                results += await self._batch_call_ai(messages[start:end], contents)
                contents = []

        if contents:
            results += await self._batch_call_ai(messages[-len(contents):], contents)

        valid_results = await self.expenses_handler.save_receipt(money_provider, results)

        for message, receipt in valid_results:
            await self.reply(
                message,
                self.expenses_handler.build_beautiful_receipt(money_provider, receipt),
                parse_mode='Markdown',
            )
            await self.mark_completed(message)

    async def _batch_call_ai(self, messages: list[Message], contents: list[Part]) -> list[tuple[Message, Receipt]]:
        response_text = None
        async with self.ai_limiter:
            response_text = await self._call_ai(contents)

        try:
            receipts = TypeAdapter(list[Receipt]).validate_json(self._extract_json(response_text))
        except Exception:
            logger.error(response_text)
            raise

        receipts = cast(list[Receipt], receipts)

        if len(receipts) != len(messages):
            await self.reply(
                messages[-1],
                'Так как было отправлено %d фото\nно обнаружено %d чеков,\n'
                'связь фото с чеками нарушена\n'
                '* Данные будут внесены, но чеки будут привязаны к последней обработанной фотографии' % (
                    len(messages),
                    len(receipts),
                )
            )
            return [(messages[-1], receipt) for receipt in receipts]

        return list(zip(messages, receipts))

    async def _call_ai(self, contents: list[Part]) -> str:
        try:
            response_text = await self.ai_client.generate_response(contents=contents, use_secondary=self._use_secondary)
        except Exception as e:
            logger.error(e)
            if self._use_secondary:
                raise e
            response_text = await self.ai_client.generate_response(
                contents=contents,
                use_secondary=True,
            )
            self._use_secondary = True
            self._reset_use_secondary_task = asyncio.create_task(self._reset_use_secondary())
            self._reset_use_secondary_task.add_done_callback(self._on_reset_use_secondary)

        assert response_text is not None
        return response_text

    def _extract_json(self, text: str) -> str:
        match = re.search(self._markdown_json, text)
        if match:
            return match.group(1).strip()

        json_match = re.search(self._raw_json, text)
        if json_match:
            return json_match.group(1).strip()

        return text.strip()

    async def _reset_use_secondary(self) -> None:
        await asyncio.sleep(self.SECONDARY_MODEL_FALLBACK_DURATION_SECONDS)
        self._use_secondary = False

    def _on_reset_use_secondary(self, _: asyncio.Task) -> None:
        self._reset_use_secondary_task = None
