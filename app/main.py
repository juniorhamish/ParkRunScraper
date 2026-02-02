import datetime
import time

from playwright.sync_api import sync_playwright

from app.parkrun_result import ParkrunResult
from app.utils.db_utils import DBClient
from app.utils.http_utils import create_session, init_playwright

if __name__ == "__main__":
    start = time.time()
    with DBClient() as db_client:
        all_parkrunners = set()
        success = True
        with sync_playwright() as playwright_context_manager:
            session = create_session()
            browser, page, context = init_playwright(playwright_context_manager)
            last_scrape_time = db_client.get_last_club_athlete_scrape_time()
            start_date = (last_scrape_time - datetime.timedelta(days=15)).date()
            end_date = datetime.date.today()
            print(f"Scraping from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            current_date = start_date
            while current_date <= end_date:
                parkrun_result = ParkrunResult(session, page, context, current_date)
                parkrun_result.fetch_results()
                success = parkrun_result.success
                if not success:
                    break
                all_parkrunners.update(parkrun_result.runner_ids)
                current_date += datetime.timedelta(days=1)
            new_parkrunners = db_client.insert_new_parkrunners(all_parkrunners)
            db_client.add_last_scrape_metadata(len(new_parkrunners), success)
            browser.close()
    end = time.time()
    print(f"Total time: {datetime.timedelta(seconds=end - start)}")
