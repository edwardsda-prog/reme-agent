#!/usr/bin/env python3
"""Provision and seed the UK Defence REME Demo 1 BigQuery dataset in Belgium (europe-west1).

Phase 3 pipeline for Demo 1 ("Snap, Diagnose, Pin & Demand"):
1. Provisions dataset `antig-dave.ukd_reme_demo` in `location="europe-west1"` with an
   explicit dataset-level `description`.
2. Creates and seeds all 3 tables with explicit table-level `description` metadata and
   explicit column-level `description` metadata on every `bigquery.SchemaField`:
   - `ipc_nsn_catalogue` (8 REQUIRED STRING columns; 6 FV432 K60 rows + 5 Jackal 2 rows)
   - `spta_sector_grids` (5 REQUIRED columns; 5 SPTA & London sector grid rows)
   - `group_chat_tickets` (13 REQUIRED columns; 1 baseline ticket `TKT-REME-041`)
3. Verifies row counts, key NSN/coordinate records, and `INFORMATION_SCHEMA` table and
   column descriptions.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import google.auth
from google.cloud import bigquery

# Avoid mTLS client certificate issues in sandboxed environments
os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")

PROJECT_ID: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "antig-dave")
DATASET_ID: str = os.environ.get("BQ_DATASET", "ukd_reme_demo")
LOCATION: str = os.environ.get("BQ_LOCATION", "europe-west1")

DATASET_DESCRIPTION: str = (
    "4 Battalion REME Tactical Sustainment Demonstrator (Demo 1) — Grounded Illustrated "
    "Parts Catalogue (IPC), Salisbury Plain Training Area (SPTA) Sector Grids, and Field "
    "Recovery Group Chat Tickets."
)

# ---------------------------------------------------------------------------
# Table 1: ipc_nsn_catalogue
# ---------------------------------------------------------------------------
IPC_TABLE_ID: str = "ipc_nsn_catalogue"
IPC_TABLE_DESCRIPTION: str = (
    "Illustrated Parts Catalogue (IPC) and Army Equipment Support Publication (AESP) "
    "lookup table mapping vehicle fault keywords to 13-digit NATO Stock Numbers (NSNs), "
    "repair level classifications (L1 FRT vs L2 Workshop), and technical condemnation limits."
)

IPC_SCHEMA: list[bigquery.SchemaField] = [
    bigquery.SchemaField(
        "part_id",
        "STRING",
        mode="REQUIRED",
        description="Unique internal catalogue identifier for the seeded part record (e.g., K60-RELIEF-01).",
    ),
    bigquery.SchemaField(
        "keyword_tag",
        "STRING",
        mode="REQUIRED",
        description="Lowercase search trigger keyword matched against spoken or typed field fault descriptions (e.g., k60, oil, relief, spring, 2350, 17.4, jackal, 409).",
    ),
    bigquery.SchemaField(
        "ipc_army_code",
        "STRING",
        mode="REQUIRED",
        description="Official UK Ministry of Defence Illustrated Parts Catalogue (IPC) Army Code and Category reference (e.g., Army Code 14660 Cat 711).",
    ),
    bigquery.SchemaField(
        "aesp_reference",
        "STRING",
        mode="REQUIRED",
        description="Authoritative Army Equipment Support Publication (AESP) document code, chapter, paragraph, and page number governing the inspection or repair.",
    ),
    bigquery.SchemaField(
        "part_name",
        "STRING",
        mode="REQUIRED",
        description="Official nomenclature of the replacement component as listed in the Illustrated Parts Catalogue.",
    ),
    bigquery.SchemaField(
        "nsn",
        "STRING",
        mode="REQUIRED",
        description="13-digit NATO Stock Number (NSN) formatted as NNNN-NN-NNN-NNNN used for supply demand.",
    ),
    bigquery.SchemaField(
        "repair_classification",
        "STRING",
        mode="REQUIRED",
        description="Authorized REME repair echelon classification indicating whether the fault is a Level 1 Forward Repair Team (FRT) fix or Level 2 Workshop repair.",
    ),
    bigquery.SchemaField(
        "technical_limits",
        "STRING",
        mode="REQUIRED",
        description="Mandatory engineering condemnation limits, spring load/length tolerances, torque settings, and safety warnings extracted from the AESP.",
    ),
]

K60_KEYWORDS: list[str] = ["k60", "oil", "relief", "spring", "2350", "17.4"]
JACKAL_KEYWORDS: list[str] = ["jackal", "409", "hydraulic", "manifold", "4.12"]

IPC_SEED_ROWS: list[dict[str, Any]] = [
    *[
        {
            "part_id": f"K60-RELIEF-0{idx}",
            "keyword_tag": kw,
            "ipc_army_code": "Army Code 14660 (Cat 711)",
            "aesp_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
            "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
            "nsn": "5360-99-812-1740",
            "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
            "technical_limits": (
                "Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) "
                "under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits "
                "— do NOT pack with washers; do not use washers to pack up behind a weak spring "
                "(prohibited packing washer NSN 5310-99-122-6412)."
            ),
        }
        for idx, kw in enumerate(K60_KEYWORDS, start=1)
    ],
    *[
        {
            "part_id": f"JACKAL-MANIFOLD-0{idx}",
            "keyword_tag": kw,
            "ipc_army_code": "Army Code 23200 (Cat 412)",
            "aesp_reference": "AESP 2320-J-100-522, Ch 4, Para 4.12 (Page 42)",
            "part_name": "Hydraulic Manifold High-Pressure Seal Kit",
            "nsn": "5330-99-812-4410",
            "repair_classification": "L2 Workshop Repair",
            "technical_limits": (
                "Replace O-ring and backup ring; torque manifold bolts to 45 Nm; "
                "pressure test to 250 bar. Depressurise hydraulic accumulator prior to seal replacement."
            ),
        }
        for idx, kw in enumerate(JACKAL_KEYWORDS, start=1)
    ],
    {
        "part_id": "JACKAL-PIPE-01",
        "keyword_tag": "hydraulic pipe",
        "ipc_army_code": "Army Code 23200 (Cat 415)",
        "aesp_reference": "AESP 2320-J-100-522, Ch 4, Para 4.12 (Page 42)",
        "part_name": "High-Pressure Hydraulic Pipe Assembly",
        "nsn": "4710-99-812-4420",
        "repair_classification": "L2 Repair (New Part Required)",
        "technical_limits": (
            "Depressurise hydraulic accumulator; replace ruptured high-pressure hydraulic pipe "
            "assembly (NSN 4710-99-812-4420); torque union fittings to 45 Nm; pressure test to 250 bar."
        ),
    },
    {
        "part_id": "JACKAL-VALVE-01",
        "keyword_tag": "safety valve",
        "ipc_army_code": "Army Code 23200 (Cat 418)",
        "aesp_reference": "AESP 2320-J-100-522, Ch 4, Para 4.14 (Page 44)",
        "part_name": "Hydraulic Manifold Safety Relief Valve",
        "nsn": "4820-99-812-4415",
        "repair_classification": "L2 Repair (New Part Required)",
        "technical_limits": (
            "Depressurise hydraulic accumulator; replace fractured hydraulic safety relief valve "
            "(NSN 4820-99-812-4415); torque manifold union to 45 Nm; pressure test to 250 bar."
        ),
    },
    {
        "part_id": "JACKAL-VALVE-PIPE-01",
        "keyword_tag": "valve and pipe",
        "ipc_army_code": "Army Code 23200 (Cat 415/418)",
        "aesp_reference": "AESP 2320-J-100-522, Ch 4, Para 4.12 & Para 4.14 (Page 42)",
        "part_name": "Hydraulic Safety Relief Valve & High-Pressure Pipe Assembly",
        "nsn": "4820-99-812-4415, 4710-99-812-4420",
        "repair_classification": "L2 Repair (New Part Required)",
        "technical_limits": (
            "Depressurise hydraulic accumulator; replace both fractured hydraulic safety relief valve "
            "(NSN 4820-99-812-4415) and ruptured high-pressure hydraulic pipe assembly (NSN 4710-99-812-4420); "
            "torque fittings to 45 Nm; pressure test to 250 bar."
        ),
    },
    {
        "part_id": "JACKAL-FIELD-FIX-01",
        "keyword_tag": "field fix",
        "ipc_army_code": "Army Code 23200 (Cat 412)",
        "aesp_reference": "AESP 2320-J-100-522, Ch 4, Para 4.12 (Page 42)",
        "part_name": "No Replacement Part Required (Field Re-Torque of Hydraulic Union)",
        "nsn": "N/A (Field Fix — Re-torque union to 45Nm)",
        "repair_classification": "L1 Field Fix (No New Part Required)",
        "technical_limits": (
            "Depressurise hydraulic accumulator to 0 bar; re-torque loose hydraulic union fitting "
            "to 45 Nm and wipe clean. Soldier can complete fix in the field; no new part required."
        ),
    },
]

# ---------------------------------------------------------------------------
# Table 2: spta_sector_grids
# ---------------------------------------------------------------------------
GRIDS_TABLE_ID: str = "spta_sector_grids"
GRIDS_TABLE_DESCRIPTION: str = (
    "Geospatial lookup table mapping spoken Salisbury Plain Training Area (SPTA) tactical "
    "sector names and British National Grid references to WGS84 decimal latitude and "
    "longitude coordinates for Google Maps recovery routing."
)

GRIDS_SCHEMA: list[bigquery.SchemaField] = [
    bigquery.SchemaField(
        "sector_key",
        "STRING",
        mode="REQUIRED",
        description="Lowercase normalized sector key or grid string matched against Push-to-Talk voice transcripts (e.g., bravo-4, bravo 4, su 1482 4621, alpha-1, london).",
    ),
    bigquery.SchemaField(
        "sector_display_name",
        "STRING",
        mode="REQUIRED",
        description="Human-readable tactical sector designation displayed on diagnostic cards and group chat tickets (e.g., Salisbury Plain (SPTA) — Sector Bravo-4).",
    ),
    bigquery.SchemaField(
        "latitude",
        "FLOAT64",
        mode="REQUIRED",
        description="WGS84 decimal latitude coordinate in degrees (positive for North) used for Google Maps destination routing.",
    ),
    bigquery.SchemaField(
        "longitude",
        "FLOAT64",
        mode="REQUIRED",
        description="WGS84 decimal longitude coordinate in degrees (negative for West) used for Google Maps destination routing.",
    ),
    bigquery.SchemaField(
        "coords_label",
        "STRING",
        mode="REQUIRED",
        description="Formatted cardinal coordinate string for UI display on tactical cards (e.g., 51.2185° N, 1.7925° W).",
    ),
]

GRIDS_SEED_ROWS: list[dict[str, Any]] = [
    {
        "sector_key": "bravo-4",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "coords_label": "51.2185° N, 1.7925° W",
    },
    {
        "sector_key": "bravo 4",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "coords_label": "51.2185° N, 1.7925° W",
    },
    {
        "sector_key": "su 1482 4621",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "coords_label": "51.2185° N, 1.7925° W",
    },
    {
        "sector_key": "alpha-1",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Alpha-1",
        "latitude": 51.2310,
        "longitude": -1.8150,
        "coords_label": "51.2310° N, 1.8150° W",
    },
    {
        "sector_key": "london",
        "sector_display_name": "MOD Main Building — Whitehall London",
        "latitude": 51.5007,
        "longitude": -0.1246,
        "coords_label": "51.5007° N, 0.1246° W",
    },
]

# ---------------------------------------------------------------------------
# Table 3: group_chat_tickets
# ---------------------------------------------------------------------------
TICKETS_TABLE_ID: str = "group_chat_tickets"
TICKETS_TABLE_DESCRIPTION: str = (
    "Persistent audit and dispatch log of field sustainment tickets published by 4 Battalion "
    "REME Forward Repair Teams (FRTs) to the B Echelon Recovery Group Chat."
)

TICKETS_SCHEMA: list[bigquery.SchemaField] = [
    bigquery.SchemaField(
        "ticket_id",
        "STRING",
        mode="REQUIRED",
        description="Unique tactical sustainment ticket identifier formatted as TKT-REME-XXXX.",
    ),
    bigquery.SchemaField(
        "created_at_utc",
        "TIMESTAMP",
        mode="REQUIRED",
        description="UTC timestamp when the field artificer published the diagnostic ticket to the group chat.",
    ),
    bigquery.SchemaField(
        "callsign",
        "STRING",
        mode="REQUIRED",
        description="Originating field artificer callsign and unit designation (e.g., Cpl MacDonald (4 Bn REME FRT)).",
    ),
    bigquery.SchemaField(
        "repair_classification",
        "STRING",
        mode="REQUIRED",
        description="Authorized REME repair level classification (e.g., L1 FRT Fix (Bench Check) / L2 Workshop).",
    ),
    bigquery.SchemaField(
        "aesp_reference",
        "STRING",
        mode="REQUIRED",
        description="Grounded AESP publication, chapter, paragraph, and page reference cited in the diagnosis.",
    ),
    bigquery.SchemaField(
        "part_name",
        "STRING",
        mode="REQUIRED",
        description="Official IPC nomenclature of the demanded replacement component.",
    ),
    bigquery.SchemaField(
        "nsn",
        "STRING",
        mode="REQUIRED",
        description="13-digit NATO Stock Number (NSN) demanded for the repair.",
    ),
    bigquery.SchemaField(
        "technical_limits",
        "STRING",
        mode="REQUIRED",
        description="Engineering condemnation limits and safety warnings included in the ticket.",
    ),
    bigquery.SchemaField(
        "coords_label",
        "STRING",
        mode="REQUIRED",
        description="Formatted cardinal coordinate string for the casualty vehicle location (e.g., 51.2185° N, 1.7925° W).",
    ),
    bigquery.SchemaField(
        "latitude",
        "FLOAT64",
        mode="REQUIRED",
        description="WGS84 decimal latitude of the casualty vehicle for recovery navigation.",
    ),
    bigquery.SchemaField(
        "longitude",
        "FLOAT64",
        mode="REQUIRED",
        description="WGS84 decimal longitude of the casualty vehicle for recovery navigation.",
    ),
    bigquery.SchemaField(
        "google_maps_url",
        "STRING",
        mode="REQUIRED",
        description="Universal Google Maps turn-by-turn navigation deep link (api=1) locked to the casualty vehicle coordinates.",
    ),
    bigquery.SchemaField(
        "status",
        "STRING",
        mode="REQUIRED",
        description="Current operational dispatch status of the recovery ticket (e.g., DISPATCH_READY, ACKNOWLEDGED, RESOLVED).",
    ),
    bigquery.SchemaField(
        "image_gcs_uri",
        "STRING",
        mode="NULLABLE",
        description="Google Cloud Storage URI (gs://antig-dave-reme-ticket-images-eu/tickets/...) of the casualty photograph provided by the soldier in the prompt.",
    ),
    bigquery.SchemaField(
        "image_url",
        "STRING",
        mode="NULLABLE",
        description="Web-accessible endpoint URL (/api/ticket-image/tickets/...) used by the Sustainment Group Chat web application to display the ticket photograph.",
    ),
]

TICKETS_SEED_ROWS: list[dict[str, Any]] = [
    {
        "ticket_id": "TKT-REME-041",
        "created_at_utc": "2026-10-29T11:00:00Z",
        "callsign": "Cpl MacDonald (4 Bn REME FRT)",
        "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
        "aesp_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
        "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
        "nsn": "5360-99-812-1740",
        "technical_limits": (
            "Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) "
            "under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits; "
            "do not use washers to pack up behind a weak spring."
        ),
        "coords_label": "51.2185° N, 1.7925° W",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "google_maps_url": (
            "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving"
        ),
        "status": "DISPATCH_READY",
    }
]


def create_reme_dataset(
    client: bigquery.Client,
    project_id: str = PROJECT_ID,
    dataset_id: str = DATASET_ID,
    location: str = LOCATION,
) -> bigquery.Dataset:
    """Create or update the `ukd_reme_demo` dataset in `europe-west1` with description."""
    dataset_ref = f"{project_id}.{dataset_id}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = location
    dataset.description = DATASET_DESCRIPTION

    dataset = client.create_dataset(dataset, exists_ok=True)
    dataset.description = DATASET_DESCRIPTION
    dataset = client.update_dataset(dataset, ["description"])
    print(
        f"[1/4] Provisioned BigQuery dataset '{dataset_ref}' in location='{dataset.location}' "
        f"with description ({len(dataset.description or '')} chars)."
    )
    return dataset


def create_and_seed_table(
    client: bigquery.Client,
    table_id: str,
    schema: list[bigquery.SchemaField],
    table_description: str,
    seed_rows: list[dict[str, Any]],
    project_id: str = PROJECT_ID,
    dataset_id: str = DATASET_ID,
    truncate: bool = True,
) -> bigquery.Table:
    """Create or update a BigQuery table with full metadata and load seed rows."""
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    table = bigquery.Table(table_ref, schema=schema)
    table.description = table_description
    table = client.create_table(table, exists_ok=True)

    # Ensure table description and column descriptions are explicitly applied
    table.description = table_description
    table.schema = schema
    table = client.update_table(table, ["description", "schema"])

    if not truncate:
        # For group_chat_tickets, avoid WRITE_TRUNCATE if baseline row already exists
        check_sql = f"SELECT COUNT(1) AS cnt FROM `{table_ref}` WHERE ticket_id = 'TKT-REME-041'"
        rows = list(client.query(check_sql).result())
        if rows and rows[0]["cnt"] > 0:
            print(
                f"      Table '{table_ref}' already contains baseline ticket TKT-REME-041; "
                "preserving existing rows."
            )
            return table

    write_disposition = (
        bigquery.WriteDisposition.WRITE_TRUNCATE
        if truncate
        else bigquery.WriteDisposition.WRITE_APPEND
    )
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=write_disposition,
    )
    load_job = client.load_table_from_json(seed_rows, table_ref, job_config=job_config)
    load_job.result()

    # Re-apply table description and column descriptions after WRITE_TRUNCATE load job
    table = client.get_table(table_ref)
    table.description = table_description
    table.schema = schema
    table = client.update_table(table, ["description", "schema"])

    print(
        f"      Seeded '{table_ref}': {len(seed_rows)} rows, "
        f"{len(table.schema)} columns with descriptions."
    )
    return table


def verify_provisioned_tables(
    client: bigquery.Client,
    project_id: str = PROJECT_ID,
    dataset_id: str = DATASET_ID,
) -> dict[str, Any]:
    """Verify row counts and non-empty table/column descriptions in BigQuery."""
    summary: dict[str, Any] = {}
    for table_id in (IPC_TABLE_ID, GRIDS_TABLE_ID, TICKETS_TABLE_ID):
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)
        if not table.description or not table.description.strip():
            raise AssertionError(f"Table '{table_ref}' is missing a table-level description!")
        for field in table.schema:
            if not field.description or not field.description.strip():
                raise AssertionError(
                    f"Column '{table_ref}.{field.name}' is missing a column-level description!"
                )

        count_sql = f"SELECT COUNT(1) AS cnt FROM `{table_ref}`"
        cnt = next(iter(client.query(count_sql).result()))["cnt"]
        summary[table_id] = {
            "row_count": cnt,
            "column_count": len(table.schema),
            "table_description_length": len(table.description),
        }

    print(f"[4/4] Verification passed: {summary}")
    return summary


def main() -> int:
    """Execute the end-to-end Phase 3 BigQuery schema provisioning and seeding pipeline."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
        quota_project_id=PROJECT_ID,
    )
    client = bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
        credentials=credentials,
    )

    create_reme_dataset(client=client)

    print("[2/4] Provisioning and seeding BigQuery tables...")
    create_and_seed_table(
        client=client,
        table_id=IPC_TABLE_ID,
        schema=IPC_SCHEMA,
        table_description=IPC_TABLE_DESCRIPTION,
        seed_rows=IPC_SEED_ROWS,
        truncate=True,
    )
    create_and_seed_table(
        client=client,
        table_id=GRIDS_TABLE_ID,
        schema=GRIDS_SCHEMA,
        table_description=GRIDS_TABLE_DESCRIPTION,
        seed_rows=GRIDS_SEED_ROWS,
        truncate=True,
    )
    print("[3/4] Provisioning and seeding group_chat_tickets table...")
    create_and_seed_table(
        client=client,
        table_id=TICKETS_TABLE_ID,
        schema=TICKETS_SCHEMA,
        table_description=TICKETS_TABLE_DESCRIPTION,
        seed_rows=TICKETS_SEED_ROWS,
        truncate=False,
    )

    verify_provisioned_tables(client=client)
    print("SUCCESS: BigQuery dataset 'ukd_reme_demo' provisioned and seeded in europe-west1.")
    return 0


seed_bigquery = main


if __name__ == "__main__":
    sys.exit(main())
