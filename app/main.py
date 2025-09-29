import datetime
import time
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from app.parkrun_result import ParkrunResult
from app.utils.db_utils import init_db
from app.utils.http_utils import create_session, init_playwright

if __name__ == "__main__":
    start = time.time()
    session = create_session()
    conn = init_db()
    cur = conn.cursor()
    result = cur.execute(
        "SELECT last_scrape_time FROM public.last_scrape_metadata WHERE success = true ORDER BY last_scrape_time DESC LIMIT 1;"
    )
    last_scrape_time = cur.fetchone()[0]
    print(f"Last scrape time: {last_scrape_time.astimezone(ZoneInfo('Europe/London'))}")
    all_parkrunners = set()
    success = True
    with sync_playwright() as playwright_context_manager:
        browser, page, context = init_playwright(playwright_context_manager)
        start_date = (last_scrape_time - datetime.timedelta(days=15)).date()
        print(f"Scraping from {start_date.strftime('%Y-%m-%d')} to {datetime.date.today().strftime('%Y-%m-%d')}")
        end_date = datetime.date.today()

        current_date = start_date
        while current_date <= end_date:
            parkrun_result = ParkrunResult(session, page, current_date)
            parkrun_result.fetch_results()
            if not parkrun_result.success:
                success = False
                break
            all_parkrunners.update(parkrun_result.runner_ids)
            current_date += datetime.timedelta(days=1)
            cookies = context.cookies()
            for cookie in cookies:
                session.cookies.set(cookie["name"], cookie["value"])
        print("All parkrunners: " + str(len(all_parkrunners)))
        print(all_parkrunners)
        placeholders = ", ".join(["(%s)"] * len(all_parkrunners))
        params = list(all_parkrunners)
        cur.execute(
            f"""
                INSERT INTO public.runners(id)
                VALUES {placeholders}
                ON CONFLICT(id) DO NOTHING
                RETURNING id;
            """,
            params,
        )
        new_parkrunners = cur.fetchall()
        print(f"New parkrunners: {len(new_parkrunners)}")
        print([new_parkrunner[0] for new_parkrunner in new_parkrunners])
        cur.execute(
            "INSERT INTO public.last_scrape_metadata (last_scrape_time, new_parkrunners_count, success) VALUES (%s, %s, %s);",
            (datetime.datetime.now(tz=datetime.timezone.utc), len(new_parkrunners), success),
        )
        browser.close()
    conn.commit()
    cur.close()
    conn.close()
    end = time.time()
    print(f"Total time: {datetime.timedelta(seconds=end - start)}")
