import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "shipments.db")))
REPORT_ISSUE_URL = os.getenv("REPORT_ISSUE_URL", "#")
WEBHOOK_SECRET = os.environ["COURIER_WEBHOOK_SECRET"]
FLAG = os.environ["FLAG"]
WEBHOOK_TOLERANCE_SECONDS = 300
INACTIVE_SHIPMENT_RETENTION_HOURS = int(os.getenv("INACTIVE_SHIPMENT_RETENTION_HOURS", "24"))
PROCESSED_EVENT_RETENTION_SECONDS = int(os.getenv("PROCESSED_EVENT_RETENTION_SECONDS", "600"))
CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "300"))
SESSION_COOKIE = "courier_session"