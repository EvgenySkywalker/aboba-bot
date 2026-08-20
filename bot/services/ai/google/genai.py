from typing import Any

from google import genai
from google.genai import types

from bot.models.settings import Settings


class GenAI:
    def __init__(self, config: Settings):
        self.client = genai.Client(api_key=config.ai_token.get_secret_value()).aio
        self.model = config.ai_model.name

    async def generate_response(self, contents: list[Any]) -> str | None:
        response = await self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=[
                    'Ты помогаешь вести учет трат.',
                    'Твоя цель проанализировать фото и если это чек, выдать информацию о его содержимом.'
                ],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        return response.text
