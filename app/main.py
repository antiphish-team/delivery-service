import hashlib
import hmac
import json
import secrets
import threading
import time
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import (
    CLEANUP_INTERVAL_SECONDS,
    FLAG,
    INACTIVE_SHIPMENT_RETENTION_HOURS,
    PROCESSED_EVENT_RETENTION_SECONDS,
    REPORT_ISSUE_URL,
    WEBHOOK_SECRET,
    WEBHOOK_TOLERANCE_SECONDS,
)
from database import cleanup_expired_records, connection, initialize_database, utc_now
from models import CourierEvent, ShipmentCreate, SupportRequestCreate
from sessions import guest_session
from state_machine import ALLOWED_TRANSITIONS, STATUS_LABELS


APP_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Courier Gateway", docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory=APP_DIR / "templates")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
cleanup_lock = threading.Lock()
next_cleanup_at = 0.0


@app.on_event("startup")
def startup() -> None:
    initialize_database()


def shipment_payload(row, include_flag: bool = False) -> dict:
    shipment = dict(row)
    shipment["statusLabel"] = STATUS_LABELS[shipment["status"]]
    if include_flag and shipment["status"] == "archived":
        shipment["flag"] = FLAG
    return shipment


def maybe_cleanup_expired_records() -> None:
    global next_cleanup_at

    now = time.monotonic()
    if now < next_cleanup_at:
        return
    with cleanup_lock:
        if now < next_cleanup_at:
            return
        cleanup_expired_records(INACTIVE_SHIPMENT_RETENTION_HOURS, PROCESSED_EVENT_RETENTION_SECONDS)
        next_cleanup_at = now + CLEANUP_INTERVAL_SECONDS


def load_owned_shipment(shipment_id: str, session_id: str):
    with connection() as database:
        return database.execute(
            "SELECT * FROM shipments WHERE id = ? AND session_id = ?", (shipment_id, session_id)
        ).fetchone()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request, response: Response, courier_session: str | None = Cookie(default=None)):
    guest_session(response, courier_session)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"report_issue_url": REPORT_ISSUE_URL},
        headers=dict(response.headers),
    )


@app.get("/support", response_class=HTMLResponse, include_in_schema=False)
def support(request: Request, response: Response, courier_session: str | None = Cookie(default=None)):
    guest_session(response, courier_session)
    return templates.TemplateResponse(
        request=request,
        name="support.html",
        context={"report_issue_url": REPORT_ISSUE_URL},
        headers=dict(response.headers),
    )


@app.get("/api/shipments")
def list_shipments(response: Response, courier_session: str | None = Cookie(default=None)):
    session_id = guest_session(response, courier_session)
    maybe_cleanup_expired_records()
    with connection() as database:
        shipments = database.execute(
            "SELECT * FROM shipments WHERE session_id = ? ORDER BY created_at DESC", (session_id,)
        ).fetchall()
    return {"shipments": [shipment_payload(shipment, include_flag=True) for shipment in shipments]}


@app.post("/api/shipments", status_code=201)
def create_shipment(
    payload: ShipmentCreate,
    response: Response,
    courier_session: str | None = Cookie(default=None),
):
    session_id = guest_session(response, courier_session)
    maybe_cleanup_expired_records()
    shipment_id = f"SHP-{secrets.token_hex(5).upper()}"
    now = utc_now()
    with connection() as database:
        database.execute(
            """INSERT INTO shipments (id, session_id, origin, destination, recipient, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'created', ?, ?)""",
            (shipment_id, session_id, payload.origin, payload.destination, payload.recipient, payload.description, now, now),
        )
        shipment = database.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
    return shipment_payload(shipment)


@app.get("/api/shipments/{shipment_id}")
def get_shipment(shipment_id: str, response: Response, courier_session: str | None = Cookie(default=None)):
    session_id = guest_session(response, courier_session)
    maybe_cleanup_expired_records()
    shipment = load_owned_shipment(shipment_id, session_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment_payload(shipment, include_flag=True)


@app.post("/api/support-requests", status_code=201)
def create_support_request(
    payload: SupportRequestCreate,
    response: Response,
    courier_session: str | None = Cookie(default=None),
):
    session_id = guest_session(response, courier_session)
    shipment = load_owned_shipment(payload.shipmentId, session_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    ticket_id = f"SUP-{secrets.token_hex(5).upper()}"
    with connection() as database:
        database.execute(
            "INSERT INTO support_requests (id, shipment_id, session_id, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (ticket_id, payload.shipmentId, session_id, payload.message, utc_now()),
        )
    return {"ticketId": ticket_id}


def verify_webhook(request: Request, raw_body: bytes) -> None:
    signature_values = request.headers.getlist("x-courier-signature")
    timestamp_values = request.headers.getlist("x-courier-timestamp")
    if len(signature_values) != 1 or len(timestamp_values) != 1:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    signature = signature_values[0]
    timestamp = timestamp_values[0]
    try:
        timestamp_value = int(timestamp)
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Webhook timestamp expired") from error

    if abs(int(time.time()) - timestamp_value) > WEBHOOK_TOLERANCE_SECONDS:
        raise HTTPException(status_code=401, detail="Webhook timestamp expired")
    if not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    message = timestamp.encode("ascii") + b"." + raw_body
    expected = hmac.new(WEBHOOK_SECRET.encode(), message, hashlib.sha256).hexdigest()
    supplied = signature.removeprefix("sha256=")
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@app.post("/api/webhooks/courier")
async def courier_webhook(request: Request):
    raw_body = await request.body()
    verify_webhook(request, raw_body)
    maybe_cleanup_expired_records()
    try:
        payload = CourierEvent.model_validate(json.loads(raw_body))
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid webhook event") from error

    with connection() as database:
        if database.execute("SELECT 1 FROM processed_events WHERE event_id = ?", (payload.eventId,)).fetchone():
            raise HTTPException(status_code=409, detail="Event already processed")

        shipment = database.execute("SELECT * FROM shipments WHERE id = ?", (payload.shipmentId,)).fetchone()
        if shipment is None:
            raise HTTPException(status_code=404, detail="Shipment not found")
        if ALLOWED_TRANSITIONS.get(shipment["status"]) != payload.status:
            raise HTTPException(status_code=409, detail="Invalid shipment state transition")

        database.execute(
            "UPDATE shipments SET status = ?, updated_at = ? WHERE id = ?",
            (payload.status, utc_now(), payload.shipmentId),
        )
        database.execute(
            "INSERT INTO processed_events (event_id, processed_at) VALUES (?, ?)",
            (payload.eventId, utc_now()),
        )
    return {"status": "ok", "shipmentStatus": payload.status}