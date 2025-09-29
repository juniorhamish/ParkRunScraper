import os

import psycopg2
from dotenv import load_dotenv

# Load .env.local only in development
if os.getenv("ENV") != "production":
    load_dotenv("../.env.local")

# Read environment variables
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


def init_db():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    return conn
