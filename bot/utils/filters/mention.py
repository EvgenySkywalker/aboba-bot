from functools import reduce
from operator import or_
from telegram import Message
from telegram.ext import filters
from bot.models.settings import Settings
from bot.utils.filters.group_thread import get_group_thread_filter


class QuickBotMentionFilter(filters.MessageFilter):
    def __init__(self, bot_username: str):
        super().__init__()
        self.mention_str = f"@{bot_username.lstrip('@')}".lower()

    def filter(self, message: Message) -> bool:
        text = message.text or message.caption or ""
        return self.mention_str in text.lower()


def build_expenses_mention_filter(config: Settings) -> filters.BaseFilter:
    _filter = reduce(or_, [filters.User(user_id=uid) for uid in config.users.keys()])

    if config.group_chat_id is not None:
        _filter = _filter & get_group_thread_filter(_filter, config.group_chat_id, config.personal_expenses_thread_id)
        _filter = _filter & filters.Entity(entity_type='mention') & QuickBotMentionFilter(config.bot_username)
    else:
        _filter = _filter & filters.ChatType.PRIVATE

    return _filter
