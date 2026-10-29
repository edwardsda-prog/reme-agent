"""Unit and integration tests for Cloud Run Sustainment Group Chat FastAPI app."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from cloud_run_chat_app.main import BQ_TICKET_COLUMNS, app


@patch("cloud_run_chat_app.main._BQ_CLIENT")
def test_chat_api_lifecycle(mock_bq: MagicMock) -> None:
    mock_bq.insert_rows_json.return_value = []

    client = TestClient(app)

    # 1. Reset demo state first (<1s instant in-memory wipe)
    r_reset = client.post("/api/reset")
    assert r_reset.status_code == 200
    assert r_reset.json() == {"status": "reset", "tickets": []}

    # 2. Check HTML index page renders tactical banner and Google Maps URL patterns
    r_html = client.get("/")
    assert r_html.status_code == 200
    assert "OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT" in r_html.text
    assert "https://www.google.com/maps/dir/?api=1" in r_html.text
    assert "https://www.google.com/maps/search/?api=1" in r_html.text

    # 3. Post a new ticket from agent
    new_ticket = {
        "ticket_id": "TKT-REME-4821",
        "created_at_utc": "2026-04-20T10:15:00Z",
        "callsign": "Cpl MacDonald (4 Bn REME FRT)",
        "repair_classification": "Level 2 Unit Repair",
        "aesp_reference": "AESP 2350-T-100-201 (FV432 Mk2/1 Bulldog / Rolls-Royce K60 Powerpack)",
        "part_name": "Spring, Helical, Compression — Oil Pressure Relief Valve (Rolls-Royce K60)",
        "nsn": "5360-99-812-1740",
        "technical_limits": "38.2 mm minimum free length (do NOT pack with washers)",
        "coords_label": "51.2185, -1.7925 (Salisbury Plain Sector Bravo-4)",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
        "status": "DISPATCH_READY",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
    }
    r_post = client.post("/api/tickets", json=new_ticket)
    assert r_post.status_code == 200
    assert r_post.json()["status"] == "published"
    assert r_post.json()["ticket"]["ticket_id"] == "TKT-REME-4821"

    # Verify BigQuery insert row strictly filters to the 13 table columns
    inserted_rows = mock_bq.insert_rows_json.call_args[0][1]
    assert set(inserted_rows[0].keys()) == BQ_TICKET_COLUMNS
    assert "sector_display_name" not in inserted_rows[0]

    # 4. Verify GET /api/tickets returns the published ticket newest first
    r_get = client.get("/api/tickets")
    assert r_get.status_code == 200
    data = r_get.json()
    assert len(data["tickets"]) == 1
    assert data["tickets"][0]["ticket_id"] == "TKT-REME-4821"
    assert data["tickets"][0]["nsn"] == "5360-99-812-1740"

    # 5. Reset demo via /api/tickets/reset alias and confirm tickets list is empty
    r_reset2 = client.post("/api/tickets/reset")
    assert r_reset2.status_code == 200
    assert r_reset2.json() == {"status": "reset", "tickets": []}


@patch("cloud_run_chat_app.main._BQ_CLIENT")
def test_chat_api_ticket_with_prompt_image_and_bq_persistence(mock_bq: MagicMock) -> None:
    """Verifies Issue 04 Fix: prompt image associated with ticket, served via /api/ticket-image, and inserted into BigQuery."""
    import base64
    from cloud_run_chat_app.main import BQ_OPTIONAL_TICKET_COLUMNS

    mock_bq.insert_rows_json.return_value = []
    client = TestClient(app)
    client.post("/api/reset")

    sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    blob_path = "tickets/20261029T173000Z-a1b2c3d4.png"
    ticket_with_image = {
        "ticket_id": "TKT-REME-9041",
        "created_at_utc": "2026-10-29T17:30:00Z",
        "callsign": "Cpl MacDonald (4 Bn REME FRT)",
        "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
        "aesp_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
        "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
        "nsn": "5360-99-812-1740",
        "technical_limits": "Free length: 79.4 mm (3.126 in). Min under 14.3-16.2 kg load: 54.6 mm. Renew if outside limits — do NOT pack with washers.",
        "coords_label": "51.2185° N, 1.7925° W",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
        "status": "PUBLISHED",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "image_gcs_uri": f"gs://antig-dave-reme-ticket-images-eu/{blob_path}",
        "image_url": f"/api/ticket-image/{blob_path}",
        "image_base64": base64.b64encode(sample_png).decode("ascii"),
        "image_mime_type": "image/png",
    }

    r_post = client.post("/api/tickets", json=ticket_with_image)
    assert r_post.status_code == 200
    saved_ticket = r_post.json()["ticket"]
    assert saved_ticket["image_gcs_uri"] == f"gs://antig-dave-reme-ticket-images-eu/{blob_path}"
    assert saved_ticket["image_url"] == f"/api/ticket-image/{blob_path}"
    assert "image_base64" not in saved_ticket

    # Verify BigQuery row includes the 13 core columns + 2 image columns
    inserted_row = mock_bq.insert_rows_json.call_args[0][1][0]
    assert set(inserted_row.keys()) == (BQ_TICKET_COLUMNS | BQ_OPTIONAL_TICKET_COLUMNS)
    assert inserted_row["image_gcs_uri"] == f"gs://antig-dave-reme-ticket-images-eu/{blob_path}"
    assert inserted_row["image_url"] == f"/api/ticket-image/{blob_path}"

    # Verify GET /api/ticket-image/{blob_path} serves the image bytes with image/png content-type
    r_img = client.get(f"/api/ticket-image/{blob_path}")
    assert r_img.status_code == 200
    assert r_img.headers["content-type"].startswith("image/png")
    assert r_img.content == sample_png

    # Verify HTML template contains the FIELD CASUALTY PHOTOGRAPH block for rendering ticket.image_url
    r_html = client.get("/")
    assert r_html.status_code == 200
    assert "FIELD CASUALTY PHOTOGRAPH" in r_html.text
    assert "ticket.image_url" in r_html.text

    client.post("/api/reset")


