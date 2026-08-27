from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv("FUNNEL_DB_PATH", ".runtime/funnel.sqlite3"))
HASH_SECRET = os.getenv("FUNNEL_HASH_SECRET", "").strip()
AUDIT_TOKEN = os.getenv("FUNNEL_AUDIT_TOKEN", "").strip()
ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv(
        "FUNNEL_ALLOWED_ORIGINS",
        "https://nobutakayamauchi.github.io",
    ).split(",")
    if item.strip()
]
RATE_LIMIT_PER_MINUTE = int(os.getenv("FUNNEL_RATE_LIMIT_PER_MINUTE", "120"))

ALLOWED_EVENTS = {
    "lp_view",
    "consult_click",
    "purchase_click",
    "contact_complete",
    # Diagnostic only. Real purchase authority must come from Stripe, not this browser event.
    "purchase_complete_client",
}

app = FastAPI(title="X Ads Funnel Telemetry", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["content-type", "authorization"],
)

_request_times: dict[str, deque[float]] = defaultdict(deque)


class FunnelEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    event: str = Field(min_length=1, max_length=40)
    product: str = Field(min_length=1, max_length=80)
    device_id: str = Field(min_length=8, max_length=120)
    session_id: str = Field(min_length=8, max_length=120)
    path: str = Field(default="", max_length=500)
    source: str = Field(default="", max_length=120)
    twclid: str = Field(default="", max_length=300)
    utm_source: str = Field(default="", max_length=120)
    utm_medium: str = Field(default="", max_length=120)
    utm_campaign: str = Field(default="", max_length=160)
    utm_content: str = Field(default="", max_length=160)
    campaign_id: str = Field(default="", max_length=120)
    line_item_id: str = Field(default="", max_length=120)


class ExclusionRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=120)
    label: str = Field(default="owner-device", max_length=120)


def _require_config() -> None:
    if not HASH_SECRET:
        raise HTTPException(status_code=503, detail="FUNNEL_HASH_SECRET is not configured")


def _require_audit_token(authorization: str | None) -> None:
    if not AUDIT_TOKEN:
        raise HTTPException(status_code=503, detail="FUNNEL_AUDIT_TOKEN is not configured")
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="audit authorization required")
    supplied = authorization[len(prefix):]
    if not hmac.compare_digest(supplied, AUDIT_TOKEN):
        raise HTTPException(status_code=403, detail="invalid audit authorization")


def _device_hash(device_id: str) -> str:
    _require_config()
    return hmac.new(
        HASH_SECRET.encode("utf-8"),
        device_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _rate_limit(request: Request) -> None:
    now = time.monotonic()
    key = request.client.host if request.client else "unknown"
    q = _request_times[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    q.append(now)


def _validate_origin(request: Request) -> None:
    origin = (request.headers.get("origin") or "").strip()
    if origin and origin not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="origin is not allowed")


@contextmanager
def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            received_at INTEGER NOT NULL,
            event TEXT NOT NULL,
            product TEXT NOT NULL,
            device_hash TEXT NOT NULL,
            session_id TEXT NOT NULL,
            path TEXT NOT NULL,
            source TEXT NOT NULL,
            twclid TEXT NOT NULL,
            utm_source TEXT NOT NULL,
            utm_medium TEXT NOT NULL,
            utm_campaign TEXT NOT NULL,
            utm_content TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            line_item_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_product_time
            ON events(product, received_at);
        CREATE INDEX IF NOT EXISTS idx_events_device
            ON events(device_hash);
        CREATE TABLE IF NOT EXISTS exclusions (
            device_hash TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """
    )


def _parse_event_body(raw: bytes) -> FunnelEvent:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid JSON body") from exc
    try:
        return FunnelEvent.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid event payload") from exc


def _insert_event(event: FunnelEvent) -> bool:
    if event.event not in ALLOWED_EVENTS:
        raise HTTPException(status_code=422, detail="unsupported event")
    device_hash = _device_hash(event.device_id)
    with _db() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO events (
                event_id, received_at, event, product, device_hash, session_id,
                path, source, twclid, utm_source, utm_medium, utm_campaign,
                utm_content, campaign_id, line_item_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                int(time.time()),
                event.event,
                event.product,
                device_hash,
                event.session_id,
                event.path,
                event.source,
                event.twclid,
                event.utm_source,
                event.utm_medium,
                event.utm_campaign,
                event.utm_content,
                event.campaign_id,
                event.line_item_id,
            ),
        )
        return cursor.rowcount == 1


def _query_summary(product: str, start_epoch: int, end_epoch: int) -> dict[str, Any]:
    if not product or len(product) > 80:
        raise HTTPException(status_code=422, detail="invalid product")
    if start_epoch < 0 or end_epoch <= start_epoch:
        raise HTTPException(status_code=422, detail="invalid time window")

    with _db() as conn:
        rows = conn.execute(
            """
            SELECT
                e.event,
                COUNT(*) AS total_events,
                COUNT(DISTINCT e.device_hash) AS total_devices,
                SUM(CASE WHEN x.device_hash IS NULL THEN 1 ELSE 0 END) AS audited_events,
                COUNT(DISTINCT CASE WHEN x.device_hash IS NULL THEN e.device_hash END) AS audited_devices
            FROM events e
            LEFT JOIN exclusions x ON x.device_hash = e.device_hash
            WHERE e.product = ? AND e.received_at >= ? AND e.received_at < ?
            GROUP BY e.event
            """,
            (product, start_epoch, end_epoch),
        ).fetchall()
        excluded = conn.execute("SELECT COUNT(*) FROM exclusions").fetchone()[0]

    event_map: dict[str, dict[str, int]] = {}
    for row in rows:
        event_map[row["event"]] = {
            "total_events": int(row["total_events"] or 0),
            "total_devices": int(row["total_devices"] or 0),
            "audited_events": int(row["audited_events"] or 0),
            "audited_devices": int(row["audited_devices"] or 0),
        }

    def devices(name: str) -> int:
        return event_map.get(name, {}).get("audited_devices", 0)

    lp = devices("lp_view")
    consult = devices("consult_click")
    purchase = devices("purchase_click")

    return {
        "ok": True,
        "product": product,
        "start_epoch": start_epoch,
        "end_epoch": end_epoch,
        "excluded_device_count": int(excluded),
        "events": event_map,
        "derived": {
            "lp_unique": lp,
            "consult_click_unique": consult,
            "purchase_click_unique": purchase,
            "consult_click_rate_from_lp": (consult / lp) if lp else None,
            "purchase_click_rate_from_lp": (purchase / lp) if lp else None,
        },
        "authority_note": (
            "Browser purchase completion is diagnostic only. Authoritative purchases must be "
            "joined from Stripe/payment records by the audit layer."
        ),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "x-ads-funnel-telemetry",
        "db_configured": bool(DB_PATH),
        "hash_secret_configured": bool(HASH_SECRET),
        "audit_token_configured": bool(AUDIT_TOKEN),
    }


@app.post("/v1/events")
async def ingest_event(request: Request) -> dict[str, Any]:
    _rate_limit(request)
    _validate_origin(request)
    raw = await request.body()
    if len(raw) > 20_000:
        raise HTTPException(status_code=413, detail="event too large")
    event = _parse_event_body(raw)
    inserted = _insert_event(event)
    return {"ok": True, "accepted": inserted}


@app.post("/v1/exclusions")
def add_exclusion(
    payload: ExclusionRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_audit_token(authorization)
    device_hash = _device_hash(payload.device_id)
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO exclusions(device_hash, label, created_at) VALUES (?, ?, ?)",
            (device_hash, payload.label, int(time.time())),
        )
    return {"ok": True, "excluded": True, "label": payload.label}


@app.delete("/v1/exclusions/{device_id}")
def remove_exclusion(
    device_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_audit_token(authorization)
    device_hash = _device_hash(device_id)
    with _db() as conn:
        cursor = conn.execute("DELETE FROM exclusions WHERE device_hash = ?", (device_hash,))
    return {"ok": True, "removed": cursor.rowcount == 1}


@app.get("/v1/summary")
def summary(
    product: str,
    start_epoch: int,
    end_epoch: int,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_audit_token(authorization)
    return _query_summary(product, start_epoch, end_epoch)
