import asyncio

from bot.models.money_provider import MoneyProvider as MoneyProviderModel
from bot.models.settings import Settings
from bot.utils.ttl_cache.ttl_cache import TtlCache


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
        self.cache = TtlCache()

    async def resolve_by_caption(self, caption: str | None, media_group_id: str | None) -> MoneyProviderModel | None:
        if caption is None:
            if media_group_id is None:
                return None
            for _ in range(3):
                caption_lower = self.cache.get(media_group_id)
                if caption_lower is not None:
                    break
                await asyncio.sleep(0.1)
            else:
                raise ValueError('media_group_id: %s' % media_group_id)
        else:
            caption_lower = caption.lower()

        provider = self.aliases_provider_map.get(caption_lower)

        if provider is None and caption_lower == self.TOGETHER_CAPTION:
            provider = self.together_provider

        if provider is None:
            raise ValueError('caption: %s' % caption)

        if media_group_id is not None:
            self.cache.put(media_group_id, caption_lower)

        return provider

    def resolve_by_user_id(self, user_id: int) -> MoneyProviderModel:
        if (provider := self.user_id_provider_map.get(user_id)) is not None:
            return provider

        raise ValueError('user_id: %d' % user_id)
