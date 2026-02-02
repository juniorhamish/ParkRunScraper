import unittest
from unittest.mock import patch, Mock
from app.scrapers.runner_scraper import RunnerScraper


class RunnerScraperTest(unittest.TestCase):
    def setUp(self):
        self.scraper = RunnerScraper()

    def test_parse_runner_metadata_from_h2(self):
        html = "<html><body><h2>John DOE (123456)</h2></body></html>"
        metadata = self.scraper.parse_runner_metadata(html)
        self.assertEqual("John Doe", metadata["name"])

    def test_parse_runner_metadata_from_title(self):
        html = (
            "<html><head><title>parkrunner results | Jane SMITH</title></head><body><h2>parkrunner</h2></body></html>"
        )
        metadata = self.scraper.parse_runner_metadata(html)
        self.assertEqual("Jane Smith", metadata["name"])

    @patch("app.scrapers.runner_scraper.DBClient")
    @patch("app.scrapers.runner_scraper.sync_playwright")
    @patch("app.scrapers.runner_scraper.get_html_content")
    @patch("app.scrapers.runner_scraper.create_session")
    @patch("app.scrapers.runner_scraper.init_playwright")
    def test_scrape_missing_metadata(
        self, mock_init_pw, mock_create_session, mock_get_html, mock_sync_pw, mock_db_client
    ):
        # Setup mocks
        db_instance = mock_db_client.return_value.__enter__.return_value
        db_instance.get_runners_missing_metadata.return_value = ["123"]

        mock_init_pw.return_value = (Mock(), Mock(), Mock())
        mock_get_html.return_value = ("<html><body><h2>John DOE (123)</h2></body></html>", True)

        # Run
        self.scraper.scrape_missing_metadata(limit=1)

        # Verify
        db_instance.update_runner_metadata.assert_called_with("123", "John Doe")


if __name__ == "__main__":
    unittest.main()
