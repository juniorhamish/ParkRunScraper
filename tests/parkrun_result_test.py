import datetime
import unittest
import os
from unittest.mock import patch, Mock
import httpretty

from app.parkrun_result import ParkrunResult
from app.utils.http_utils import create_session, init_playwright


def load_file_data(filename):
    with open(os.path.join(os.path.dirname(__file__), "data", filename), "r", encoding="utf-8") as f:
        return f.read()


def mock_response(filename="daily_result_no_runners.html"):
    html_content = load_file_data(filename)
    response = Mock()
    response.status_code = 200
    response.text = html_content
    return response


class ParkrunResultTest(unittest.TestCase):

    def setUp(self):
        self.session = create_session()

    def test_parkrun_result_has_date(self):
        parkrun_result = ParkrunResult(self.session, None, datetime.date(2025, 9, 27))
        self.assertEqual(datetime.date(2025, 9, 27), parkrun_result.date)

    @patch("requests.Session.get")
    def test_parkrun_result_no_runners(self, mock_get):
        mock_get.return_value = mock_response("daily_result_no_runners.html")

        parkrun_result = ParkrunResult(self.session, None, datetime.date(2025, 9, 26))
        parkrun_result.fetch_results()

        self.assertEqual([], parkrun_result.runner_ids)

    @patch("requests.Session.get")
    def test_parkrun_result_makes_get_request(self, mock_get):
        mock_get.return_value = mock_response()
        parkrun_result = ParkrunResult(self.session, None, datetime.date(2025, 9, 27))
        parkrun_result.fetch_results()

        mock_get.assert_called_with(
            "https://www.parkrun.com/results/consolidatedclub/?clubNum=1832&eventdate=2025-09-27"
        )
        self.assertTrue(parkrun_result.success)

    @patch("requests.Session.get")
    def test_parkrun_result_single_parkrun_single_runner(self, mock_get):
        mock_get.return_value = mock_response("daily_result_one_parkrun_one_runner.html")
        parkrun_result = ParkrunResult(self.session, None, datetime.date(2025, 9, 27))
        parkrun_result.fetch_results()

        self.assertEqual(["2243726"], parkrun_result.runner_ids)

    @patch("requests.Session.get")
    def test_parkrun_result_single_parkrun_multiple_runners(self, mock_get):
        mock_get.return_value = mock_response("daily_result_one_parkrun_multiple_runners.html")
        parkrun_result = ParkrunResult(self.session, None, datetime.date(2025, 9, 27))
        parkrun_result.fetch_results()

        self.assertEqual(["23575", "22507"], parkrun_result.runner_ids)

    @patch("requests.Session.get")
    def test_parkrun_result_multiple_parkruns_multiple_runners(self, mock_get):
        mock_get.return_value = mock_response("daily_result_multiple_parkruns_multiple_runners.html")
        parkrun_result = ParkrunResult(self.session, None, datetime.date(2025, 9, 27))
        parkrun_result.fetch_results()

        self.assertEqual(
            ["27348", "28837", "25484", "40197", "31202", "34610", "30600", "26919"], parkrun_result.runner_ids
        )

    @patch("requests.Session.get")
    def test_parkrun_result_bot_protection_uses_playwright(self, mock_get):
        mock_get.return_value = mock_response("daily_result_bot_protection.html")
        mock_page = Mock()
        mock_page.content.return_value = load_file_data("daily_result_one_parkrun_one_runner.html")
        parkrun_result = ParkrunResult(self.session, mock_page, datetime.date(2025, 9, 27))
        parkrun_result.fetch_results()

        self.assertEqual(["2243726"], parkrun_result.runner_ids)
        mock_page.goto.assert_called_with(
            "https://www.parkrun.com/results/consolidatedclub/?clubNum=1832&eventdate=2025-09-27", timeout=60000
        )
        mock_page.wait_for_load_state.assert_called_with("networkidle")

    @httpretty.activate()
    def test_parkrun_result_retries_on_4xx_errors(self):
        url = "https://www.parkrun.com/results/consolidatedclub/?clubNum=1832&eventdate=2025-09-27"
        httpretty.register_uri(
            httpretty.GET,
            url,
            responses=[
                httpretty.Response(body="First failure", status=408),
                httpretty.Response(body="Second failure", status=425),
                httpretty.Response(body="Third failure", status=429),
                httpretty.Response(body="Success", status=200),
            ],
        )
        parkrun_result = ParkrunResult(create_session(backoff_factor=0), None, datetime.date(2025, 9, 27))
        parkrun_result.fetch_results()

        self.assertTrue(parkrun_result.success)

    @httpretty.activate()
    def test_parkrun_result_retries_on_5xx_errors(self):
        url = "https://www.parkrun.com/results/consolidatedclub/?clubNum=1832&eventdate=2025-09-27"
        httpretty.register_uri(
            httpretty.GET,
            url,
            responses=[
                httpretty.Response(body="First failure", status=500),
                httpretty.Response(body="Second failure", status=502),
                httpretty.Response(body="Third failure", status=503),
                httpretty.Response(body="Fourth failure", status=504),
                httpretty.Response(body="Success", status=200),
            ],
        )
        parkrun_result = ParkrunResult(
            create_session(max_retries=4, backoff_factor=0), None, datetime.date(2025, 9, 27)
        )
        parkrun_result.fetch_results()

        self.assertTrue(parkrun_result.success)


if __name__ == "__main__":
    unittest.main()
