import requests
from bs4 import BeautifulSoup
from app.utils.db_utils import DBClient
from app.utils.http_utils import create_session, init_playwright, get_html_content
from playwright.sync_api import sync_playwright


class RunnerScraper:
    def __init__(self):
        self.base_url = "https://www.parkrun.org.uk/parkrunner/{}/"

    def scrape_missing_metadata(self, limit=200):
        with DBClient() as db_client:
            runner_ids = db_client.get_runners_missing_metadata(limit=limit)
            if not runner_ids:
                print("No runners missing metadata.")
                return True

            with sync_playwright() as playwright_context_manager:
                session = create_session()
                browser, page, context = init_playwright(playwright_context_manager)

                for runner_id in runner_ids:
                    url = self.base_url.format(runner_id)
                    print(f"Scraping metadata for runner {runner_id} from {url}")
                    html, success = get_html_content(url, session, page, context)

                    if success:
                        metadata = self.parse_runner_metadata(html)
                        if metadata.get("name"):
                            db_client.update_runner_metadata(runner_id, metadata["name"])
                        else:
                            print(f"Could not find name for runner {runner_id}")
                    else:
                        print(f"Failed to fetch metadata for runner {runner_id}")

                browser.close()
        return True

    def parse_runner_metadata(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        # Parkrun runner pages usually have the name in an h2
        header = soup.find("h2")
        name = header.text.strip() if header else None

        # Fallback to title if h2 is not helpful
        if not name or name.lower() == "parkrunner":
            title = soup.find("title")
            if title:
                # Title format is often "parkrunner results | Name"
                parts = title.text.split("|")
                if len(parts) > 1:
                    name = parts[-1].strip()

        if name:
            # The format is often 'First LAST (Runner ID)'
            # Remove the runner ID in brackets if it exists
            if "(" in name:
                name = name.rsplit("(", 1)[0].strip()

            # Make the name Title Case
            name = name.title()

        return {"name": name}
