import requests
import time
import random
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from playwright_stealth import Stealth

COMMON_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def create_session(max_retries=3, backoff_factor=1):
    session = requests.Session()
    session.headers = {
        "User-Agent": COMMON_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "priority": "u=0, i",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    retries = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[408, 425, 429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def init_playwright(playwright_context_manager):
    # Use a more realistic viewport and add some variety
    width = 1280 + random.randint(0, 100)
    height = 720 + random.randint(0, 100)

    browser = playwright_context_manager.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-zygote",
            # This is a key flag to hide the automation control
            "--disable-blink-features=AutomationControlled",
        ],
    )

    # Parkrun is UK-based, so setting locale and timezone helps look more like a local user
    context = browser.new_context(
        user_agent=COMMON_USER_AGENT,
        viewport={"width": width, "height": height},
        device_scale_factor=random.choice([1, 1.25, 1.5]),
        locale="en-GB",
        timezone_id="Europe/London",
        accept_downloads=False,
    )

    # Apply stealth to the context
    Stealth().apply_stealth_sync(context)

    page = context.new_page()
    return browser, page, context


def get_html_content(url, session, page, context):
    # Add a small random delay before each request to look less like a bot
    # Skip delay in tests to speed them up
    from os import getenv

    if getenv("ENV") != "test":
        time.sleep(random.uniform(1, 3))

    try:
        result = session.get(url)
        html = result.text

        # Check for common bot protection patterns
        bot_signals = [
            "JavaScript is disabled",
            "detected unusual traffic",
            "please complete the security check",
            "was not able to complete your request",
        ]

        if any(signal in html for signal in bot_signals):
            print(f"Bot protection detected for: {url}. Attempting with Playwright...")

            # Give it a bit of a "human" pause before trying Playwright
            if getenv("ENV") != "test":
                time.sleep(random.uniform(2, 5))

            page.goto(url, timeout=60000, wait_until="load")

            # Wait for content to load
            page.wait_for_load_state("networkidle")

            # Simulate some human activity to resolve potential behavioral challenges
            if getenv("ENV") != "test":
                time.sleep(random.uniform(1, 2))
                page.mouse.move(random.randint(100, 700), random.randint(100, 500))
                time.sleep(random.uniform(0.5, 1))
                page.mouse.wheel(0, random.randint(300, 700))
                time.sleep(random.uniform(1, 3))

            # Additional wait to ensure any challenge scripts have finished
            try:
                # Parkrun results are in tables, and runner profiles have h2/h1 headers
                page.wait_for_selector("table, h2, h1", timeout=15000)
            except Exception:
                pass

            html = page.content()

            # Check if we are still blocked
            if any(signal in html for signal in bot_signals):
                print(f"Bot protection STILL detected for: {url} even after Playwright. Possible IP block.")
                return html, False

            cookies = context.cookies()
            for cookie in cookies:
                session.cookies.set(cookie["name"], cookie["value"])
            print(f"Successfully retrieved content with Playwright and updated session cookies for: {url}")

        success = True
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch results for: {url}. Error: {e}")
        success = False
        html = None
    return html, success
