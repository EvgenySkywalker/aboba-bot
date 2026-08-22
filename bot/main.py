from bot.handlers.commands.start import start
from bot.handlers.expenses import ExpensesHandler
from bot.handlers.mention import MentionHandler
from bot.handlers.aboba import handle_text
from bot.handlers.photo import PhotoHandler
from telegram.ext import (
    Application,
    MessageHandler, filters, CommandHandler,
)

from bot.models.settings import config
from bot.utils.filters.mention import build_expenses_mention_filter
from bot.utils.filters.photo import build_expenses_photo_filter
from bot.utils.logger.logger import logger


def main() -> None:
    logger.setLevel(config.log_level)

    expenses_handler = ExpensesHandler(config)
    photo_handler = PhotoHandler(expenses_handler, config)
    mention_handler = MentionHandler(expenses_handler, config)

    application = Application.builder().token(config.tg_token.get_secret_value()).build()
    application.add_handler(MessageHandler(build_expenses_photo_filter(config), photo_handler.handle, block=False))
    application.add_handler(MessageHandler(build_expenses_mention_filter(config), mention_handler.handle, block=False))
    application.add_handler(CommandHandler("start", start, filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.TEXT, handle_text))
    logger.info('Starting up bot application')
    application.run_polling(allowed_updates=[])
