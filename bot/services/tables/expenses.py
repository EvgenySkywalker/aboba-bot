import gspread
from gspread import Worksheet

from bot.models.settings import Settings


class Spreadsheets:
    SPREADSHEET_KEY_PATH='credentials/google-spreadsheet-key.json'

    def __init__(self, config: Settings):
        gc = gspread.service_account(filename=self.SPREADSHEET_KEY_PATH)
        self.sh = gc.open_by_url(config.spreadsheet_url)

    def get_expenses_worksheet(self) -> Worksheet:
        return self.sh.sheet1
