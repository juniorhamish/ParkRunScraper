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
    browser = playwright_context_manager.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-zygote",
        ],
    )
    context = browser.new_context(user_agent=COMMON_USER_AGENT, viewport={"width": 1920, "height": 1080})
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
                time.sleep(random.uniform(2, 4))

            page.goto(url, timeout=60000)
            # Wait for content to load, sometimes networkidle is too fast for WAF challenges
            page.wait_for_load_state("networkidle")

            # Additional wait to ensure any challenge scripts have finished
            try:
                page.wait_for_selector("table", timeout=10000)
            except Exception:
                # If no table is found, it might be a page with no results, which is fine
                pass

            html = page.content()
            if any(signal in html for signal in bot_signals):
                print(f"Bot protection detected for: {url} even when using Playwright...sad")
                return html, False
            cookies = context.cookies()
            for cookie in cookies:
                session.cookies.set(cookie["name"], cookie["value"])
            print(
                f"Successfully retrieved content with Playwright and updated session cookies for: {url}"
            )

        success = True
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch results for: {url}. Error: {e}")
        success = False
        html = None
    return html, success
