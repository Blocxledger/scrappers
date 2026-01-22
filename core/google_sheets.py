import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import OrderedDict
from datetime import datetime

class GoogleSheetsPipeline:
    def __init__(self):
        self.sheet = None
        self.headers_written = False
        self.headers = []
        self.date_str = datetime.now().strftime("%d-%m-%Y")
        self.sheet_title_running = f"{self.date_str} (RUNNING)"
        self.sheet_title_done = f"{self.date_str} (COMPLETED)"

    def open_spider(self, spider):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)

        self.spreadsheet = client.open_by_key(spider.sheet_id)

        try:
            self.sheet = self.spreadsheet.worksheet(self.sheet_title_running)
        except gspread.exceptions.WorksheetNotFound:
            self.sheet = self.spreadsheet.add_worksheet(title=self.sheet_title_running, rows="1000", cols="50")


    def process_item(self, item, spider):
        item = dict(item)
        # Write headers if not already done
        if not self.headers_written:
            self.headers = list(item.keys())
            self.sheet.clear()
            self.sheet.append_row(self.headers)
            self.headers_written = True

        # Write the item row in header order
        row = [item.get(key, "") for key in self.headers]
        self.sheet.append_row(row)

        return item
    
    def close_spider(self, spider):
        try:
            self.sheet.update_title(self.sheet_title_done)
        except Exception as e:
            spider.logger.error(f"Failed to rename sheet: {e}")
