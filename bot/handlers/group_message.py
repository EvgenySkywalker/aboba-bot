import asyncio
from datetime import datetime
from itertools import chain
from typing import Protocol, Any

from google.genai import types
from google.genai.types import Part
from gspread import Worksheet
from gspread.utils import ValueInputOption
from pydantic import TypeAdapter, ValidationError
from telegram import Update, PhotoSize, Message
from telegram.ext import ContextTypes

from bot.models.processing import ProcessPayload
from bot.models.settings import Settings
from bot.services.money_provider.money_provider import MoneyProvider
from bot.utils.currency_converter.currency_converter import CurrencyConverter
from bot.utils.event_debouncer.event_debouncer import EventDebouncer
from bot.utils.logger.logger import logger
from bot.models.check_info import CheckInfo
from bot.models.money_provider import MoneyProvider as MoneyProviderModel
from bot.utils.rate_limiter.rate_limiter import TimedRateLimiter

SingleUpdateDebouncer = EventDebouncer[MoneyProviderModel, ProcessPayload]


class AIClient(Protocol):
    async def generate_response(self, contents: list[Any]) -> str | None:
        ...


class GroupMessageHandler:
    TEXT = 'Записал на счет - %s'
    MEDIA_GROUP_WAIT_TIME_SECONDS = 5

    def __init__(
            self,
            money_provider: MoneyProvider,
            ai_client: AIClient,
            analyze_check_prompt: str,
            worksheet: Worksheet,
            currency_converter: CurrencyConverter,
            config: Settings,
    ):
        self.money_provider = money_provider
        self.ai_client = ai_client
        self.analyze_check_prompt = analyze_check_prompt
        self.worksheet = worksheet
        self.currency_converter = currency_converter
        self.limiter = TimedRateLimiter(
            max_calls=config.ai_model.quota_size,
            period_seconds=config.ai_model.quota_period_seconds,
        )
        self.images_per_message_limit = config.ai_model.images_per_message_limit
        self.media_groups_storage: dict[str, list[PhotoSize]] = {}
        self.media_groups_handle_tasks: set[asyncio.Task] = set()
        self.su_debouncer = SingleUpdateDebouncer(
            config.single_message_debouncer_period_seconds,
            config.ai_model.images_per_message_limit,
        )

    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        assert update.message is not None
        assert update.message.photo is not None

        if update.message.media_group_id is None:
            await self.process_single_photo(update)
        else:
            task = asyncio.create_task(self.process_media_group(update))
            self.media_groups_handle_tasks.add(task)
            task.add_done_callback(self.media_groups_handle_tasks.discard)

    async def process_single_photo(self, update: Update) -> None:
        money_provider, message = await self._preprocess(update)

        await self.su_debouncer.add_event(
            money_provider,
            ProcessPayload(
                update=update,
                photos=[update.message.photo[-1]],
            ),
            self._process_single_photos_in_single_ai_call,
        )


    async def _process_single_photos_in_single_ai_call(
        self,
        money_provider: MoneyProviderModel,
        payloads: list[ProcessPayload],
    ) -> None:
        last_update = payloads[-1].update
        assert last_update.message is not None
        last_message = last_update.message

        try:
            results = await self.process_message(
                ProcessPayload(
                    update=last_update,
                    photos=list(chain.from_iterable(p.photos for p in payloads)),
                ),
                money_provider=money_provider,
            )
        except Exception as e:
            error_message = 'Ошибка: \n```\n%s\n```' % str(e)
            logger.error(error_message)
            await last_message.reply_text(error_message)
            return

        await last_message.set_reaction(reaction="👍")

        for result in results:
            await last_message.reply_text(
                self.build_beautiful_response(money_provider, result),
                parse_mode='Markdown',
            )

    async def process_media_group(self, update: Update) -> None:
        assert update.message is not None
        assert update.message.media_group_id is not None

        media_group_id = update.message.media_group_id

        if media_group_id not in self.media_groups_storage:
            self.media_groups_storage[media_group_id] = [update.message.photo[-1]]
        else:
            self.media_groups_storage[media_group_id].append(update.message.photo[-1])
            return

        money_provider, message = await self._preprocess(update)

        await asyncio.sleep(self.MEDIA_GROUP_WAIT_TIME_SECONDS)

        try:
            results = await self.process_message(
                ProcessPayload(
                    update=update,
                    photos=self.media_groups_storage.pop(media_group_id),
                ),
                money_provider=money_provider,
            )
        except Exception as e:
            error_message = 'Ошибка: \n```\n%s\n```' % str(e)
            logger.error(error_message)
            await update.message.reply_text(error_message)
            return

        await message.set_reaction(reaction="👍")

        for result in results:
            await message.reply_text(
                self.build_beautiful_response(money_provider, result),
                parse_mode='Markdown',
            )

    async def process_message(self, payload: ProcessPayload, money_provider: MoneyProviderModel) -> list[CheckInfo]:
        contents, results = [], []
        for photo in payload.photos:
            photo_file = await photo.get_file()

            image_part = types.Part.from_bytes(
                data=await photo_file.download_as_bytearray(),
                mime_type='image/jpeg'
            )
            contents.append(image_part)

            if len(contents) == self.images_per_message_limit:
                results += await self._process_batch(payload, money_provider, contents)
                contents = []

        if contents:
            results += await self._process_batch(payload, money_provider, contents)

        return results

    async def _preprocess(self, update: Update) -> tuple[MoneyProvider, Message]:
        assert update is not None
        assert update.message is not None
        assert update.effective_user is not None

        message = update.message
        await message.set_reaction(reaction="👀")

        if (money_provider := self.money_provider.resolve(message.caption, update.effective_user.id)) is not None:
            return money_provider, message

        raise ValueError('caption: %s, user_id: %d', message.caption, update.effective_user.id)

    async def _process_batch(
            self,
            payload: ProcessPayload,
            money_provider: MoneyProviderModel,
            contents: list[Part | str],
    ) -> list[CheckInfo]:
        assert payload.update.message

        results = []
        response_text = None
        contents.append(self.analyze_check_prompt)
        async with self.limiter:
            response_text = await self.ai_client.generate_response(contents=contents)

        if response_text is None:
            error_message = 'Ошибка во время отправки запроса в ИИ'
            logger.error(error_message)
            await payload.update.message.reply_text(error_message)
            return results

        try:
            checks = TypeAdapter(list[CheckInfo]).validate_json(response_text)
        except ValidationError as ve:
            error_message = 'Ошибка во время сериализации ответа ИИ: \n```\n%s\n```' % str(ve)
            logger.error(error_message)
            await payload.update.message.reply_text(error_message)
            return results

        for idx, check in enumerate(checks):
            if not check.is_readable:
                await payload.update.message.reply_text('Не получилось прочитать чек №%d' % idx)
                continue

            date = check.date.isoformat()
            rate = await self.currency_converter.get_jpy_rate(date, 'USD')
            for item in check.items:
                new_row = [
                    datetime.now().isoformat(),
                    date,
                    check.store_name,
                    item.category,
                    item.name,
                    item.count,
                    item.price_with_vat,
                    money_provider.table_name,
                    round(rate * item.price_with_vat, 2),
                ]
                self.worksheet.append_row(new_row, value_input_option=ValueInputOption.user_entered)

            check.total_amount_usd = round(rate * check.total_amount, 2)

            results.append(check)

        return results

    @classmethod
    def build_beautiful_response(cls, money_provider: MoneyProviderModel, check_info: CheckInfo) -> str:
        reply_message_text = cls.TEXT % money_provider.name
        lines = [
            f'👤 {reply_message_text}\n\n',
            f"🧾 **Чек:** {check_info.store_name} *({check_info.store_name_jp})*\n",
            f"🗓 **Дата:** {check_info.date}\n"
            "──────────────\n",
            "🛒 **Товары:**",
        ]

        for item in check_info.items:
            lines.append(
                f"\n• **{item.name}**\n"
                f"  ├ **Категория:** `{item.category}`\n"
                f"  ├ **Количество:** {item.count} шт.\n"
                f"  └ **Цена:** {item.price_with_vat} ¥\n"
            )

        lines.append("──────────────\n")
        lines.append(f"💰 **Итого:** `{check_info.total_amount} ¥` (${check_info.total_amount_usd})")

        return "\n".join(lines)
