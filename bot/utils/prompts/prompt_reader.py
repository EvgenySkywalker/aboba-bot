import os

from bot.utils.logger.logger import logger


class PromptReader:
    ANALYZE_RECEIPT_PROMPT_PATH = 'bot/utils/prompts/prompt.txt'

    def __init__(self):
        self.receipt_analyze_prompt = self.get_prompt_from_file(self.ANALYZE_RECEIPT_PROMPT_PATH)

    @staticmethod
    def get_prompt_from_file(path: str) -> str | None:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as file:
                logger.info(f"Prompt {path} load from file successfully.")
                return file.read()
        else:
            logger.critical(f'File {path} not found!')
            exit(1)
