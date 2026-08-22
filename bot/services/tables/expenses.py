import gspread
from gspread import Worksheet

from bot.models.settings import Settings
from bot.utils.logger.logger import logger


class Spreadsheets:
    SPREADSHEET_KEY_PATH='credentials/google-spreadsheet-key.json'

    def __init__(self, config: Settings):
        logger.info('Starting up Google Spreadsheets client')
        gc = gspread.service_account(filename=self.SPREADSHEET_KEY_PATH)
        self.sh = gc.open_by_url(config.spreadsheet_url)
        logger.info('Google Spreadsheets started')

        if config.worksheet_gid is not None:
            self.worksheet = self.sh.get_worksheet_by_id(config.worksheet_gid)
        else:
            self.worksheet = self.sh.sheet1

    def get_expenses_worksheet(self) -> Worksheet:
        return self.worksheet
