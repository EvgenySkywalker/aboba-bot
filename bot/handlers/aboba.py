from telegram import Update
from telegram.ext import ContextTypes


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.effective_message is not None
    assert update.effective_message.text is not None
    assert update.effective_chat is not None

    if update.effective_message.text.lower() == 'абоба':
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Абоба!")
