import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("jobs.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_jobs (
            url TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            status TEXT,
            timestamp TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def is_processed(url: str) -> bool:
    """Returns True if the job was successfully applied or intentionally skipped."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status FROM processed_jobs WHERE url = ? AND status IN ('applied', 'already_applied', 'skipped_low_match', 'skipped_external')",
        (url,),
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def update_job_status(url: str, title: str, company: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO processed_jobs (url, title, company, status, timestamp)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            status = excluded.status,
            timestamp = excluded.timestamp
        """,
        (url, title, company, status, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
