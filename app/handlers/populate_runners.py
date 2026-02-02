from app.scrapers.club_scraper import ClubScraper


def lambda_handler(event, context):
    club_id = event.get("clubNum", 1832)
    club_name = event.get("clubName", "Bellahouston Harriers")
    scraper = ClubScraper(club_id=club_id, club_name=club_name)
    success = scraper.scrape_recent_results()
    return {"statusCode": 200 if success else 500, "body": "Scrape completed" if success else "Scrape failed"}
