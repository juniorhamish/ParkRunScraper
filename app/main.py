import datetime
import time

from playwright.sync_api import sync_playwright

from app.parkrun_result import ParkrunResult
from app.utils.http_utils import create_session, init_playwright

if __name__ == "__main__":
    start = time.time()
    session = create_session()
    all_parkrunners = set()
    with sync_playwright() as playwright_context_manager:
        browser, page, context = init_playwright(playwright_context_manager)
        start_date = datetime.date(2025, 9, 20)
        end_date = datetime.date.today()

        current_date = start_date
        while current_date <= end_date:
            parkrun_result = ParkrunResult(session, page, current_date)
            parkrun_result.fetch_results()
            if not parkrun_result.success:
                break
            all_parkrunners.update(parkrun_result.runner_ids)
            current_date += datetime.timedelta(days=1)
            cookies = context.cookies()
            for cookie in cookies:
                session.cookies.set(cookie["name"], cookie["value"])
        print("All parkrunners: " + str(len(all_parkrunners)))
        print(all_parkrunners)

        browser.close()
    end = time.time()
    print(f"Total time: {datetime.timedelta(seconds=end - start)}")
