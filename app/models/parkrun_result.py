import datetime
import requests
from bs4 import BeautifulSoup

from app.utils.http_utils import get_html_content


class ParkrunResult:
    date: datetime.date
    success: bool
    session: requests.Session
    runner_ids: list[str]
    url: str

    def __init__(self, session, page, context, date, club_id=1832, club_name="Bellahouston Harriers"):
        self.session = session
        self.page = page
        self.context = context
        self.date = date
        self.club_id = club_id
        self.club_name = club_name
        self.runner_ids = []
        self.success = False
        self.url = f"https://www.parkrun.com/results/consolidatedclub/?clubNum={self.club_id}&eventdate={self.date.strftime('%Y-%m-%d')}"

    def fetch_results(self):
        html, success = get_html_content(self.url, self.session, self.page, self.context)
        if success:
            self.parse_results(html)
        self.success = success

    def parse_results(self, html_content: str):
        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                cell_values = [cell.text for cell in cells]
                if any(self.club_name in cell for cell in cell_values):
                    for cell in cells:
                        if cell.a and "parkrunner" in cell.a["href"]:
                            self.runner_ids.append(cell.a["href"].split("/")[-1])
