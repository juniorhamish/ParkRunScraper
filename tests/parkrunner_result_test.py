import unittest

from app.parkrunner_result import ParkrunnerResult


class ParkrunnerResultTest(unittest.TestCase):
    def test_parkrunner_id_parsed_from_parkrunner_url(self):
        result = ParkrunnerResult(
            event_url="",
            time_in_seconds=0,
            parkrunner_url="https://www.parkrun.dk/amagerstrandpark/parkrunner/2243726?something=something",
        )
        self.assertEqual("2243726", result.parkrunner_id)


if __name__ == "__main__":
    unittest.main()
