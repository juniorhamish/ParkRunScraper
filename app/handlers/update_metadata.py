from app.scrapers.runner_scraper import RunnerScraper


def lambda_handler(event, context):
    limit = event.get("limit", 200)
    print(f"Running update_metadata with limit {limit}")
    scraper = RunnerScraper()
    success = scraper.scrape_missing_metadata(limit=limit)
    return {
        "statusCode": 200 if success else 500,
        "body": "Metadata update completed" if success else "Metadata update failed",
    }
