from datetime import datetime, timezone
from os import getenv
from zoneinfo import ZoneInfo

import psycopg2
from dotenv import load_dotenv


def init_db():
    # Load .env.local only in development
    if getenv("ENV") != "production":
        load_dotenv("../.env.local")

    # Read environment variables
    db_name = getenv("DB_NAME")
    db_user = getenv("DB_USER")
    db_password = getenv("DB_PASSWORD")
    db_host = getenv("DB_HOST")
    db_port = getenv("DB_PORT")
    conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
    return conn


class DBClient:
    def __init__(self):
        self.conn = init_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def get_last_club_athlete_scrape_time(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT last_scrape_time FROM public.last_scrape_metadata WHERE success = true ORDER BY last_scrape_time DESC LIMIT 1;"
            )
            last_scrape_time = cur.fetchone()[0]
        print(f"Last scrape time: {last_scrape_time.astimezone(ZoneInfo('Europe/London'))}")
        return last_scrape_time

    def insert_new_parkrunners(self, all_parkrunners):
        print(f"Inserting {len(all_parkrunners)} parkrunners...")
        print(all_parkrunners)
        with self.conn.cursor() as cur:
            placeholders = ", ".join(["(%s)"] * len(all_parkrunners))
            params = list(all_parkrunners)
            cur.execute(
                f"INSERT INTO public.runners(id) VALUES {placeholders} ON CONFLICT(id) DO NOTHING RETURNING id;", params
            )
            new_parkrunners = [new_parkrunner[0] for new_parkrunner in cur.fetchall()]
        print(f"New parkrunners: {len(new_parkrunners)}")
        print(new_parkrunners)
        return new_parkrunners

    def add_last_scrape_metadata(self, new_parkrunners_count, success):
        now = datetime.now(tz=timezone.utc)
        print(
            f"Adding last scrape metadata...[last_scrape_time: {now.astimezone(ZoneInfo('Europe/London'))}, new_parkrunners_count: {new_parkrunners_count}, success: {success}]"
        )
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.last_scrape_metadata (last_scrape_time, new_parkrunners_count, success) VALUES (%s, %s, %s);",
                (now, new_parkrunners_count, success),
            )

    def get_runners_missing_metadata(self, limit=100):
        print(f"Fetching up to {limit} runners missing metadata...")
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM public.runners WHERE name IS NULL LIMIT %s;", (limit,))
            runners = [row[0] for row in cur.fetchall()]
        print(f"Found {len(runners)} runners.")
        return runners

    def update_runner_metadata(self, runner_id, name):
        print(f"Updating metadata for runner {runner_id}: name={name}")
        with self.conn.cursor() as cur:
            cur.execute("UPDATE public.runners SET name = %s WHERE id = %s;", (name, runner_id))
