import asyncio

from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Привет, {update.effective_user.first_name}!\n'
             f'TG User ID: {update.effective_user.id}\n'
             f'IP: `121.200.161.128`',
        parse_mode='Markdown',
    )
    await asyncio.sleep(15)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Шучу, телега не палит IP :(')
