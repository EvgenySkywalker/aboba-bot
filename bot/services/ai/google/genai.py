from google import genai
from google.genai import types
from google.genai.types import Part

from bot.models.settings import Settings
from bot.utils.logger.logger import logger
from bot.utils.prompts.prompt_reader import PromptReader


class GenAI:
    def __init__(self, config: Settings):
        logger.info('Starting up GenAI client')
        self.client = genai.Client(api_key=config.ai_token.get_secret_value()).aio
        logger.info('GenAI started')
        self.model = config.ai_model.name
        self.secondary_model = config.ai_model.secondary_name
        self.analyze_check_prompt = PromptReader().receipt_analyze_prompt + ', '.join(config.expense_categories)

    async def generate_response(self, contents: list[Part], use_secondary: bool = False) -> str | None:
        response = await self.client.models.generate_content(
            model=self.model if not (use_secondary and self.secondary_model is not None) else self.secondary_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=[self.analyze_check_prompt],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        return response.text
