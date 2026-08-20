from bot.models.money_provider import MoneyProvider as MoneyProviderModel
from bot.models.settings import Settings


class MoneyProvider:
    TOGETHER_CAPTION = 'вместе'

    def __init__(self, config: Settings):
        self.user_id_provider_map: dict[int, MoneyProviderModel] = {}
        for user_id, user in config.users.items():
            self.user_id_provider_map[user_id] = MoneyProviderModel(name=user.name, table_name=user.table_name)

        self.aliases_provider_map: dict[str, MoneyProviderModel] = {}
        for user in config.users.values():
            provider = MoneyProviderModel(name=user.name, table_name=user.table_name)
            self.aliases_provider_map[user.name.lower()] = provider
            for alias in user.aliases:
                self.aliases_provider_map[alias.lower()] = provider

        self.together_provider = MoneyProviderModel(
            name='вместе',
            table_name=', '.join([user.table_name for user in config.users.values()]),
        )

    def resolve(self, caption: str | None, user_id: int) -> MoneyProviderModel | None:
        if caption is None:
            if (provider := self.user_id_provider_map.get(user_id)) is not None:
                return provider
            return None

        caption_lower = caption.lower()

        provider = self.aliases_provider_map.get(caption_lower)
        if provider is not None:
            return provider

        if caption_lower == self.TOGETHER_CAPTION:
            return self.together_provider

        return None
