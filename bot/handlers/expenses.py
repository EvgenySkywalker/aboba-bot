from datetime import datetime
from typing import cast, Any

from gspread.utils import ValueInputOption
from telegram import Message

from bot.models.settings import Settings
from bot.models.spending import Spending
from bot.services.tables.expenses import Spreadsheets
from bot.utils.currency_converter.currency_converter import CurrencyConverter
from bot.models.receipt import Receipt, ValidReceipt
from bot.models.money_provider import MoneyProvider as MoneyProviderModel
from bot.utils.event_debouncer.event_debouncer import EventDebouncer
from bot.utils.retry import retry_on_transient_errors

ExpensesMessageDebouncer = EventDebouncer[MoneyProviderModel, Message]


class ExpensesHandler:
    TEXT = 'Записал на счет - %s'

    def __init__(self, config: Settings):
        self.worksheet = Spreadsheets(config).get_expenses_worksheet()
        self.currency_converter = CurrencyConverter()

    async def save_receipt(
        self,
        money_provider: MoneyProviderModel,
        items: list[tuple[Message, Receipt]],
    ) -> list[tuple[Message, ValidReceipt]]:
        filtered_items = []
        rows = []
        for message, receipt in items:
            if not receipt.is_readable:
                await message.reply_text('Не получилось прочитать чек')
                continue

            receipt = cast(ValidReceipt, receipt)

            date = receipt.date.isoformat()
            rate = await self.currency_converter.get_jpy_rate(date, 'USD')
            for item in receipt.items:
                item.price_with_vat_usd = round(item.price_with_vat * rate, 2)
                rows.append([
                    datetime.now().isoformat(),
                    date,
                    receipt.store_name,
                    item.category,
                    item.name,
                    item.count,
                    item.price_with_vat,
                    money_provider.table_name,
                    item.price_with_vat_usd,
                ])
            receipt.total_amount_usd = round(receipt.total_amount * rate, 2)
            filtered_items.append((message, receipt))

        await retry_on_transient_errors(
            lambda: self.worksheet.append_rows(rows, value_input_option=ValueInputOption.user_entered),
        )

        return filtered_items

    async def save_spending(
        self,
        money_provider: MoneyProviderModel,
        items: list[tuple[Message, Spending]],
    ) -> list[tuple[Message, Spending]]:
        rows = []
        for message, spending in items:
            date = spending.date.isoformat()
            rate = await self.currency_converter.get_jpy_rate(date, 'USD')
            spending.amount_usd = round(rate * spending.amount, 2)
            rows.append([
                datetime.now().isoformat(),
                date,
                spending.recipient,
                spending.category,
                spending.description,
                1,
                spending.amount,
                money_provider.table_name,
                spending.amount_usd,
            ])

        await retry_on_transient_errors(
            lambda: self.worksheet.append_rows(rows, value_input_option=ValueInputOption.user_entered),
        )

        return items

    @classmethod
    def build_beautiful_spending(cls, money_provider: MoneyProviderModel, spending: Spending) -> str:
        reply_message_text = cls.TEXT % money_provider.name
        return '\n'.join([
            f'👤 {reply_message_text}\n\n',
            f'🧾 **Трата:** {spending.description}\n',
            f'🗓 **Дата:** {spending.date}\n'
            '──────────────\n',
            f'├ **Получатель:** {spending.recipient}\n',
            f'└ **Категория:** `{spending.category}`\n',
            '──────────────\n',
            f'💰 **Итого:** `{spending.amount} ¥` (${spending.amount_usd})',
        ])

    @classmethod
    def build_beautiful_receipt(cls, money_provider: MoneyProviderModel, receipt: ValidReceipt) -> str:
        reply_message_text = cls.TEXT % money_provider.name
        lines = [
            f'👤 {reply_message_text}\n\n',
            f'🧾 **Чек:** {receipt.store_name} *({receipt.store_name_jp})*\n',
            f'🗓 **Дата:** {receipt.date}\n'
            '──────────────\n',
            '🛒 **Товары:**',
        ]

        for item in receipt.items:
            lines.append(
                f'\n• **{item.name}**\n'
                f'  ├ **Категория:** `{item.category}`\n'
                f'  ├ **Количество:** {item.count} шт.\n'
                f'  └ **Цена:** `{item.price_with_vat} ¥` (${item.price_with_vat_usd})\n'
            )

        lines.append('──────────────\n')
        lines.append(f'💰 **Итого:** `{receipt.total_amount} ¥` (${receipt.total_amount_usd})')

        return '\n'.join(lines)
