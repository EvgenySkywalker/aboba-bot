from pydantic import field_validator, BaseModel

from bot.models.settings import config


class Category(BaseModel):
    category: str

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in config.expense_categories:
            raise ValueError('Invalid category, available categories: %r' % config.expense_categories)
        return v
