from functools import reduce
from operator import or_

from telegram.ext import filters

from bot.models.settings import Settings


class IsPersonalExpensesThread(filters.MessageFilter):
    class Filter(filters.MessageFilter):
        def __init__(self, thread_id: int):
            super().__init__()
            self.thread_id = thread_id

        def filter(self, message: filters.Message) -> bool | filters.FilterDataDict | None:
            return message.message_thread_id == self.thread_id

    def __init__(self, config: Settings):
        super().__init__()
        self._filter = (
                filters.Chat(chat_id=config.group_chat_id)
                & filters.IS_TOPIC_MESSAGE
                & self.Filter(thread_id=config.personal_expenses_thread_id)
                & reduce(or_, [filters.User(user_id=key) for key in config.users.keys()])
                & filters.PHOTO
        )

    def filter(self, _: filters.Message) -> filters.MessageFilter:
        return self._filter
