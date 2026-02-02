import unittest
from unittest.mock import patch, Mock
import datetime
from freezegun import freeze_time
from app.scrapers.club_scraper import ClubScraper


class ClubScraperTest(unittest.TestCase):
    def setUp(self):
        self.scraper = ClubScraper()

    @freeze_time("2025-10-20")
    @patch("app.scrapers.club_scraper.DBClient")
    @patch("app.scrapers.club_scraper.sync_playwright")
    @patch("app.scrapers.club_scraper.ParkrunResult")
    @patch("app.scrapers.club_scraper.init_playwright")
    @patch("app.scrapers.club_scraper.create_session")
    def test_scrape_recent_results(self, mock_session, mock_init_pw, mock_result, mock_sync_pw, mock_db_client):
        # Setup mocks
        db_instance = mock_db_client.return_value.__enter__.return_value
        # last scrape was 2025-10-15. 15th - 15 days = Oct 1. Oct 1 to Oct 20.
        db_instance.get_last_club_athlete_scrape_time.return_value = datetime.datetime(2025, 10, 15)

        mock_init_pw.return_value = (Mock(), Mock(), Mock())

        result_instance = mock_result.return_value
        result_instance.success = True
        result_instance.runner_ids = ["1", "2"]

        db_instance.insert_new_parkrunners.return_value = ["1", "2"]

        # Run
        success = self.scraper.scrape_recent_results()

        # Verify
        self.assertTrue(success)
        # Check if insert_new_parkrunners was called with a set containing "1" and "2"
        db_instance.insert_new_parkrunners.assert_called()
        db_instance.add_last_scrape_metadata.assert_called_with(2, True)


if __name__ == "__main__":
    unittest.main()
