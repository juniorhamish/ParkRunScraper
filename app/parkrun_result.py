import datetime
import requests
from bs4 import BeautifulSoup

base_url = "https://www.parkrun.com/results/consolidatedclub/?clubNum=1832&eventdate="


class ParkrunResult:
    date: datetime.date
    success: bool
    session: requests.Session
    runner_ids: list[str]
    url: str

    def __init__(self, session, page, date):
        self.session = session
        self.page = page
        self.date = date
        self.runner_ids = []
        self.success = False
        self.url = base_url + self.date.strftime("%Y-%m-%d")

    def fetch_results(self):
        try:
            result = self.session.get(self.url)
            html = result.text
            if "JavaScript is disabled" in html:
                print(f"Bot protection has prevented loading data for: {self.date.strftime('%Y-%m-%d')}.")
                self.page.goto(self.url, timeout=60000)
                self.page.wait_for_load_state("networkidle")
                html = self.page.content()
            self.parse_results(html)
            self.success = True
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch results for date: {self.date.strftime('%Y-%m-%d')}. Error: {e}")
            self.success = False

    def parse_results(self, html_content: str):
        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                cell_values = [cell.text for cell in cells]
                if any("Bellahouston Harriers" in cell for cell in cell_values):
                    for cell in cells:
                        if cell.a and "parkrunner" in cell.a["href"]:
                            self.runner_ids.append(cell.a["href"].split("/")[-1])
