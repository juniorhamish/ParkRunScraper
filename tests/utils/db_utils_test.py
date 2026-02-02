import os
import unittest
from unittest.mock import patch, Mock, MagicMock
from app.utils.db_utils import DBClient
from dateutil import parser
from freezegun import freeze_time


def create_mock_cursor():
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    return cursor


@patch("psycopg2.connect")
class DBClientTest(unittest.TestCase):
    def setUp(self):
        self.mock_connection = Mock()

    def test_context_manager_closes_connection(self, mock_connect):
        mock_connect.return_value = self.mock_connection
        with DBClient() as db_client:
            self.assertEqual(self.mock_connection, db_client.conn)
        self.mock_connection.close.assert_called_once()

    def test_context_manager_commits_connection(self, mock_connect):
        mock_connect.return_value = self.mock_connection
        with DBClient():
            pass
        self.mock_connection.commit.assert_called_once()

    def test_context_manager_rolls_back_connection_on_error(self, mock_connect):
        mock_connect.return_value = self.mock_connection
        try:
            with DBClient():
                raise ValueError("Test error")
        except ValueError:
            pass
        self.mock_connection.rollback.assert_called_once()

    @patch.dict(
        os.environ,
        {"DB_NAME": "test_db", "DB_USER": "test_user", "DB_PASSWORD": "password", "DB_HOST": "host", "DB_PORT": "port"},
    )
    def test_db_client_loads_env_variables(self, mock_connect):
        with DBClient():
            mock_connect.assert_called_with(
                dbname="test_db", user="test_user", password="password", host="host", port="port"
            )

    def test_get_last_club_athlete_scrape_time(self, mock_connect):
        expected_last_scrape_time = parser.isoparse("2025-10-01T23:26:00+01:00")
        mock_cursor = create_mock_cursor()
        mock_cursor.fetchone.return_value = [expected_last_scrape_time]
        mock_connect.return_value.cursor.return_value = mock_cursor
        with DBClient() as db_client:
            last_scrape_time = db_client.get_last_club_athlete_scrape_time()
        self.assertEqual(expected_last_scrape_time, last_scrape_time)
        mock_cursor.execute.assert_called_with(
            "SELECT last_scrape_time FROM public.last_scrape_metadata WHERE success = true ORDER BY last_scrape_time DESC LIMIT 1;"
        )
        mock_cursor.__exit__.assert_called_once()

    def test_insert_new_parkrunners(self, mock_connect):
        mock_cursor = create_mock_cursor()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [["12345"], ["67890"]]
        with DBClient() as db_client:
            new_parkrunners = db_client.insert_new_parkrunners(["12345", "67890"])
        mock_cursor.execute.assert_called_with(
            "INSERT INTO public.runners(id) VALUES (%s), (%s) ON CONFLICT(id) DO NOTHING RETURNING id;",
            ["12345", "67890"],
        )
        self.assertEqual(["12345", "67890"], new_parkrunners)
        mock_cursor.__exit__.assert_called_once()

    @freeze_time("2025-10-01T23:27:00+01:00")
    def test_add_last_scrape_metadata(self, mock_connect):
        mock_cursor = create_mock_cursor()
        mock_connect.return_value.cursor.return_value = mock_cursor
        with DBClient() as db_client:
            db_client.add_last_scrape_metadata(10, True)
        mock_cursor.execute.assert_called_with(
            "INSERT INTO public.last_scrape_metadata (last_scrape_time, new_parkrunners_count, success) VALUES (%s, %s, %s);",
            (parser.isoparse("2025-10-01T23:27:00+01:00"), 10, True),
        )
        mock_cursor.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
