from app.scrapers.club_scraper import ClubScraper
from app.scrapers.runner_scraper import RunnerScraper

if __name__ == "__main__":
    club_scraper = ClubScraper()
    club_scraper.scrape_recent_results()
    metadata_scraper = RunnerScraper()
    metadata_scraper.scrape_missing_metadata()
