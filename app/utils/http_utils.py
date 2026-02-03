import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry


def create_session(max_retries=3, backoff_factor=1):
    session = requests.Session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
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
        "Referer": "https://www.parkrun.com/results/consolidatedclub/?clubNum=1832&eventdate=2009-08-22",
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
    context = browser.new_context()
    page = context.new_page()
    page.set_extra_http_headers(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
    )
    return browser, page, context


def get_html_content(url, session, page, context):
    try:
        result = session.get(url)
        html = result.text
        if "JavaScript is disabled" in html:
            print(f"Bot protection has prevented loading data for: {url}.")
            page.goto(url, timeout=60000)
            page.wait_for_load_state("networkidle")
            html = page.content()
            cookies = context.cookies()
            for cookie in cookies:
                session.cookies.set(cookie["name"], cookie["value"])
        success = True
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch results for: {url}. Error: {e}")
        success = False
        html = None
    return html, success
