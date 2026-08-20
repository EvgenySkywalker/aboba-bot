from pydantic import SecretStr, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class User(BaseModel):
    name: str
    table_name: str
    aliases: set[str]


class AiModel(BaseModel):
    name: str
    quota_size: int
    quota_period_seconds: int
    images_per_message_limit: int


class Settings(BaseSettings):
    tg_token: SecretStr
    users: dict[int, User]
    group_chat_id: int
    personal_expenses_thread_id: int
    single_message_debouncer_period_seconds: int

    ai_token: SecretStr
    ai_model: AiModel

    spreadsheet_url: str

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        env_nested_delimiter='__',
    )


config = Settings()
