from bot.services.money_provider.money_provider import MoneyProvider
from bot.utils.currency_converter.currency_converter import CurrencyConverter
from bot.services.ai.google.genai import GenAI
from bot.services.tables.expenses import Spreadsheets
from bot.handlers.aboba import handle_text
from bot.handlers.commands.start import start
from bot.handlers.group_message import GroupMessageHandler
from telegram.ext import (
    Application,
    MessageHandler, CommandHandler, filters,
)

from bot.models.settings import config
from bot.utils.filters.filters import IsPersonalExpensesThread
from bot.utils.prompts.prompt_reader import PromptReader


def main() -> None:
    handler = GroupMessageHandler(
        MoneyProvider(config),
        GenAI(config),
        PromptReader().check_analyze_prompt,
        Spreadsheets(config).get_expenses_worksheet(),
        CurrencyConverter(),
        config,
    )

    application = Application.builder().token(config.tg_token.get_secret_value()).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, handle_text))
    application.add_handler(MessageHandler(IsPersonalExpensesThread(config), handler.handle_group_message, block=False))
    application.run_polling(allowed_updates=[])
