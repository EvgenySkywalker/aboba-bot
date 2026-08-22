from telegram import Message
from telegram.ext import filters


def get_group_thread_filter(_filter: filters.BaseFilter, group_chat_id: int, thread_id: int | None) -> filters.BaseFilter:
    _filter = _filter & filters.Chat(chat_id=group_chat_id)
    if thread_id is not None:
        class ThreadFilter(filters.MessageFilter):
            def filter(self, message: Message) -> bool:
                return getattr(message, "message_thread_id", None) == thread_id

        _filter = _filter & filters.IS_TOPIC_MESSAGE & ThreadFilter()

    return _filter
