import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from config import DATABASE_PATH


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(DATABASE_PATH)
    database.row_factory = sqlite3.Row
    try:
        yield database
        database.commit()
    finally:
        database.close()


def initialize_database() -> None:
    with connection() as database:
        database.executescript(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                recipient TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_shipments_session ON shipments(session_id);
            CREATE INDEX IF NOT EXISTS idx_shipments_cleanup ON shipments(status, updated_at);
            CREATE INDEX IF NOT EXISTS idx_events_cleanup ON processed_events(processed_at);
            """
        )


def cleanup_expired_records(inactive_shipment_retention_hours: int, processed_event_retention_seconds: int) -> None:
    shipment_cutoff = (datetime.now(UTC) - timedelta(hours=inactive_shipment_retention_hours)).isoformat(timespec="seconds")
    event_cutoff = (datetime.now(UTC) - timedelta(seconds=processed_event_retention_seconds)).isoformat(timespec="seconds")
    with connection() as database:
        database.execute(
            "DELETE FROM shipments WHERE status != 'archived' AND updated_at < ?",
            (shipment_cutoff,),
        )
        database.execute("DELETE FROM processed_events WHERE processed_at < ?", (event_cutoff,))