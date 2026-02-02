import unittest
from unittest.mock import patch
from app.handlers.populate_runners import lambda_handler


class PopulateRunnersHandlerTest(unittest.TestCase):
    @patch("app.handlers.populate_runners.ClubScraper")
    def test_lambda_handler_uses_params_from_event(self, mock_club_scraper):
        mock_scraper_instance = mock_club_scraper.return_value
        mock_scraper_instance.scrape_recent_results.return_value = True

        event = {"clubNum": 1234, "clubName": "My Club"}
        response = lambda_handler(event, None)

        mock_club_scraper.assert_called_with(club_id=1234, club_name="My Club")
        self.assertEqual(response["statusCode"], 200)

    @patch("app.handlers.populate_runners.ClubScraper")
    def test_lambda_handler_uses_defaults(self, mock_club_scraper):
        mock_scraper_instance = mock_club_scraper.return_value
        mock_scraper_instance.scrape_recent_results.return_value = True

        event = {}
        response = lambda_handler(event, None)

        mock_club_scraper.assert_called_with(club_id=1832, club_name="Bellahouston Harriers")
        self.assertEqual(response["statusCode"], 200)
