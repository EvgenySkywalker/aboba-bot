from functools import reduce
from operator import or_
from telegram.ext import filters
from bot.models.settings import Settings
from bot.utils.filters.group_thread import get_group_thread_filter


def build_expenses_photo_filter(config: Settings) -> filters.BaseFilter:
    _filter = reduce(or_, [filters.User(user_id=uid) for uid in config.users.keys()])

    if config.group_chat_id is not None:
        _filter = get_group_thread_filter(_filter, config.group_chat_id, config.personal_expenses_thread_id)
    else:
        _filter = _filter & filters.ChatType.PRIVATE

    return _filter & filters.PHOTO
