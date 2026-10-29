"""FastAPI Backend for 4 Bn REME Sustainment Group Chat Web Application."""

import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from google.cloud import bigquery, storage
from pydantic import BaseModel

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "antig-dave")
BQ_DATASET = os.environ.get("BQ_DATASET", "ukd_reme_demo")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "europe-west1")
TICKET_IMAGES_BUCKET = os.environ.get(
    "TICKET_IMAGES_BUCKET", "antig-dave-reme-ticket-images-eu"
)

# Baseline 13 columns in BigQuery table ukd_reme_demo.group_chat_tickets
BQ_TICKET_COLUMNS = {
    "ticket_id",
    "created_at_utc",
    "callsign",
    "repair_classification",
    "aesp_reference",
    "part_name",
    "nsn",
    "technical_limits",
    "coords_label",
    "latitude",
    "longitude",
    "google_maps_url",
    "status",
}

# Optional ticket image columns persisted when an image is attached to the ticket
BQ_OPTIONAL_TICKET_COLUMNS = {
    "image_gcs_uri",
    "image_url",
}

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="4 Bn REME Sustainment Group Chat",
    version="1.0.0",
)


class TicketPayload(BaseModel):
    ticket_id: str
    created_at_utc: str
    callsign: str = "Cpl MacDonald (4 Bn REME FRT)"
    repair_classification: str
    aesp_reference: str
    part_name: str
    nsn: str
    technical_limits: str
    sector_display_name: Optional[str] = "Salisbury Plain (SPTA) — Sector Bravo-4"
    coords_label: str
    latitude: float
    longitude: float
    google_maps_url: str
    status: str = "DISPATCH_READY"
    image_gcs_uri: Optional[str] = None
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None


# In-memory store for instant <20ms UI polling
ACTIVE_TICKETS: list[dict[str, Any]] = []
IMAGE_CACHE: dict[str, tuple[bytes, str]] = {}

try:
    _BQ_CLIENT: Optional[bigquery.Client] = bigquery.Client(
        project=PROJECT_ID, location=BQ_LOCATION
    )
except Exception as exc:
    logger.warning(f"Initial BigQuery singleton init deferred: {exc}")
    _BQ_CLIENT = None

try:
    _STORAGE_CLIENT: Optional[storage.Client] = storage.Client(project=PROJECT_ID)
except Exception as exc:
    logger.warning(f"Initial Storage singleton init deferred: {exc}")
    _STORAGE_CLIENT = None


def _blob_path_from_uri_or_url(
    image_gcs_uri: Optional[str], image_url: Optional[str]
) -> Optional[str]:
    """Resolves a relative GCS blob path (`tickets/...`) from a `gs://` URI or `/api/ticket-image/` URL."""
    if image_url and "/api/ticket-image/" in image_url:
        return image_url.split("/api/ticket-image/", 1)[1].lstrip("/")
    if image_gcs_uri and image_gcs_uri.startswith("gs://"):
        without_scheme = image_gcs_uri[len("gs://") :]
        parts = without_scheme.split("/", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1].lstrip("/")
    return None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Renders the dark-mode tactical Sustainment Group Chat web app."""
    return templates.TemplateResponse(request, "index.html", {"tickets": ACTIVE_TICKETS})


@app.get("/api/tickets")
async def get_tickets() -> dict[str, Any]:
    """Returns all active sustainment tickets ordered newest first."""
    return {"tickets": ACTIVE_TICKETS}


@app.get("/api/ticket-image/{blob_path:path}")
async def get_ticket_image(blob_path: str) -> Response:
    """Serves a ticket's casualty photograph from the in-memory cache or GCS bucket."""
    clean_path = blob_path.lstrip("/")
    cached = IMAGE_CACHE.get(clean_path)
    if cached is not None:
        raw_bytes, mime_type = cached
        return Response(content=raw_bytes, media_type=mime_type)

    if _STORAGE_CLIENT is not None:
        try:
            bucket = _STORAGE_CLIENT.bucket(TICKET_IMAGES_BUCKET)
            blob = bucket.blob(clean_path)
            raw_bytes = blob.download_as_bytes(timeout=3.0, retry=None)
            mime_type = blob.content_type or (
                "image/png" if clean_path.lower().endswith(".png") else "image/jpeg"
            )
            IMAGE_CACHE[clean_path] = (raw_bytes, mime_type)
            return Response(content=raw_bytes, media_type=mime_type)
        except Exception as exc:
            logger.warning(f"Ticket image GCS fetch failed for {clean_path}: {exc}")

    return JSONResponse(
        status_code=404,
        content={"error": f"Ticket image not found: {clean_path}"},
    )


@app.post("/api/tickets")
async def create_ticket(ticket: TicketPayload) -> dict[str, Any]:
    """Ingests a new ticket from the ADK agent or direct API call."""
    record = ticket.model_dump(exclude={"image_base64", "image_mime_type"})
    blob_path = _blob_path_from_uri_or_url(
        record.get("image_gcs_uri"), record.get("image_url")
    )

    if ticket.image_base64:
        try:
            raw_bytes = base64.b64decode(ticket.image_base64)
            mime_type = ticket.image_mime_type or "image/jpeg"
            if not blob_path:
                ext = "png" if "png" in mime_type.lower() else "jpg"
                digest = hashlib.sha256(raw_bytes).hexdigest()[:12]
                blob_path = f"tickets/ticket-img-{digest}.{ext}"
            IMAGE_CACHE[blob_path] = (raw_bytes, mime_type)
            if not record.get("image_gcs_uri"):
                record["image_gcs_uri"] = f"gs://{TICKET_IMAGES_BUCKET}/{blob_path}"
            if not record.get("image_url"):
                record["image_url"] = f"/api/ticket-image/{blob_path}"
        except Exception as exc:
            logger.warning(f"Failed to decode inline ticket image_base64: {exc}")

    if blob_path and not record.get("image_url"):
        record["image_url"] = f"/api/ticket-image/{blob_path}"

    ACTIVE_TICKETS[:] = [
        t for t in ACTIVE_TICKETS if t.get("ticket_id") != record["ticket_id"]
    ]
    ACTIVE_TICKETS.insert(0, record)

    if _BQ_CLIENT is not None:
        try:
            table_ref = f"{PROJECT_ID}.{BQ_DATASET}.group_chat_tickets"
            bq_row = {
                k: v
                for k, v in record.items()
                if k in BQ_TICKET_COLUMNS
                or (k in BQ_OPTIONAL_TICKET_COLUMNS and v is not None)
            }
            errors = _BQ_CLIENT.insert_rows_json(table_ref, [bq_row])
            if errors and any(k in bq_row for k in BQ_OPTIONAL_TICKET_COLUMNS):
                fallback_row = {
                    k: v for k, v in record.items() if k in BQ_TICKET_COLUMNS
                }
                _BQ_CLIENT.insert_rows_json(table_ref, [fallback_row])
        except Exception as exc:
            logger.warning(f"BigQuery insert skipped/failed: {exc}")

    return {"status": "published", "ticket": record}


@app.post("/api/reset")
@app.post("/api/tickets/reset")
async def reset_demo() -> dict[str, Any]:
    """Clears in-memory active tickets for <1s between-rehearsal reset."""
    ACTIVE_TICKETS.clear()
    return {"status": "reset", "tickets": []}

