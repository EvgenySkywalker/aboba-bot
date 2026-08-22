import abc
from typing import Coroutine, Any

from telegram import Update, Message
from telegram.ext import ContextTypes

from bot.utils.logger.logger import logger


class BaseHandler(abc.ABC):
    @abc.abstractmethod
    async def _handle(self, update: Update):
        ...

    async def handle(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        assert update is not None
        assert update.message is not None

        await self.handle_with_error(update.message, self._handle(update))

    async def handle_with_error(self, message: Message, c: Coroutine[Any, Any, None]):
        try:
            await c
        except Exception as e:
            await self.mark_failed(message)
            logger.error(e)
            await self.reply(message, str(e))
            raise e

    @staticmethod
    async def reply(message: Message, *args, **kwargs):
        try:
            await message.reply_text(*args, **kwargs)
        except Exception as e:
            logger.error(e)

    @staticmethod
    async def mark_seen(message: Message):
        try:
            await message.set_reaction(reaction="👀")
        except Exception as e:
            logger.error(e)

    @staticmethod
    async def mark_completed(message: Message):
        try:
            await message.set_reaction(reaction="👍")
        except Exception as e:
            logger.error(e)

    @staticmethod
    async def mark_failed(message: Message):
        try:
            await message.set_reaction(reaction="👎")
        except Exception as e:
            logger.error(e)
