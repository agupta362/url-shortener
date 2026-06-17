import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

_conn = None

def get_connection():
    global _conn
    if _conn is not None and not _conn.closed:
        return _conn

    retries = 5
    while retries > 0:
        try:
            _conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
            print("Connected to database")
            return _conn
        except Exception:
            print(f"Database not ready, retrying... {retries} retries left")
            retries -= 1
            time.sleep(3)

    raise Exception("Failed to connect to database")

def execute_query(query, params=None, fetch=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetch == "all":
            return cursor.fetchall()
        if fetch == "one":
            return cursor.fetchone()
        conn.commit()
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()