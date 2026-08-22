import datetime
import re

from telegram import Update, Message

from bot.handlers.base import BaseHandler
from bot.handlers.expenses import ExpensesHandler, ExpensesMessageDebouncer
from bot.models.money_provider import MoneyProvider as MoneyProviderModel
from bot.models.settings import Settings
from bot.models.spending import Spending
from bot.services.money_provider.money_provider import MoneyProvider
from bot.utils.logger.logger import logger


class MentionHandler(BaseHandler):
    MESSAGE_DEBOUNCER_MAX_SIZE = 10

    def __init__(self, expenses_handler: ExpensesHandler, config: Settings):
        self.expenses_handler = expenses_handler

        self.money_provider = MoneyProvider(config)

        self.debouncer = ExpensesMessageDebouncer(
            config.single_message_debouncer_period_seconds,
            self.MESSAGE_DEBOUNCER_MAX_SIZE,
        )

    async def extract_money_provider(self, update: Update) -> MoneyProviderModel:
        assert update.effective_user is not None
        return self.money_provider.resolve_by_user_id(update.effective_user.id)

    async def _handle(self, update: Update) -> None:
        assert update.message is not None
        assert update.message.photo is not None

        money_provider = await self.extract_money_provider(update)

        await self.mark_seen(update.message)

        await self.debouncer.add_event(money_provider, update.message, self._process_messages)
        logger.debug('Added mention to debouncer %s queue', money_provider.name)

    async def _process_messages(self, messages: list[Message], money_provider: MoneyProviderModel) -> None:
        return await self.handle_with_error(messages[-1], self._process(messages, money_provider))

    async def _process(self, messages: list[Message], money_provider: MoneyProviderModel) -> None:
        results = []
        for message in messages:
            assert message.text is not None
            spending = self.parse_expense_text(message.text, message.date.date())
            results.append((message, spending))

        items = await self.expenses_handler.save_spending(money_provider, results)

        for message, spending in items:
            await self.reply(
                message,
                self.expenses_handler.build_beautiful_spending(money_provider, spending),
                parse_mode='Markdown',
            )
            await self.mark_completed(message)

    @staticmethod
    def parse_expense_text(text: str, message_date: datetime.date) -> Spending:
        patterns = {
            'amount': r'(?:Сумма|amount)\b\s*:?\s*(.+)',
            'recipient': r'(?:Получатель|recipient)\b\s*:?\s*(.+)',
            'date': r'(?:Дата|date)\b\s*:?\s*(.+)',
            'category': r'(?:Категория|category)\b\s*:?\s*(.+)',
            'description': r'(?:Описание|description)\b\s*:?\s*(.+)',
        }

        extracted_data = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            for key, pattern in patterns.items():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value.lower() not in ("не указано", "none", "-", ""):
                        extracted_data[key] = value
                    break

        if 'date' not in extracted_data:
            extracted_data['date'] = message_date

        for fmt in ('%d', '%m-%d', '%m.%d', '%m/%d', '%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d'):
            try:
                dt = datetime.datetime.strptime(extracted_data['date'], fmt)
            except ValueError:
                continue

            match fmt:
                case '%m-%d' | '%m.%d' | '%m/%d':
                    dt = dt.replace(year=datetime.datetime.now().year)
                case '%d':
                    dt = dt.replace(month=datetime.datetime.now().month, year=datetime.datetime.now().year)
            extracted_data['date'] = dt.date()
            break

        extracted_data['category'] = extracted_data['category'].capitalize()

        return Spending(**extracted_data)
