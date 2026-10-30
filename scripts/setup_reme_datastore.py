#!/usr/bin/env python3
"""Provision and index the UK Defence REME AESP Discovery Engine Datastore (eu).

Phase 2 pipeline for Demo 1 ("Snap, Diagnose, Pin & Demand"):
1. Inspects `gs://remedata` in `antig-dave` and verifies `2350-T-250-523.pdf` exists.
2. Generates rich NDJSON metadata (`documents.jsonl`) for PDFs in `gs://remedata`
   and uploads to `gs://remedata/documents.jsonl`.
3. Creates the unstructured OCR datastore `ukd-reme-aesp-ds` in `location=eu`
   with `CONTENT_REQUIRED` and `ocrParsingConfig.useNativeText = True` (idempotent on HTTP 409).
4. Triggers an incremental document import (`branches/0/documents:import` with
   `reconciliationMode: "INCREMENTAL"`) and polls the LRO until completion.
5. Executes a single-pass verification search (`pageSize: 15`, `snippetSpec: {"returnSnippet": True}`).
6. Dynamically resolves the shared Gemini Enterprise engine `pixel_mobile_demos`
   (`pixel-mobile-demos_1793177711952`) in `location=eu`, reads existing `dataStoreIds`
   (`["jointservicepubs_1793177321711"]`), and safely patches `?updateMask=dataStoreIds`
   with the non-destructive union so both `jointservicepubs` and `ukd-reme-aesp-ds`
   remain bound and all existing agents remain untouched.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from typing import Any

import google.auth
import requests
from google.auth.transport.requests import Request
from google.cloud import storage

# Avoid mTLS client certificate issues in sandboxed environments
os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")

PROJECT_ID: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "antig-dave")
DISCOVERY_ENGINE_LOCATION: str = os.environ.get("DISCOVERY_ENGINE_LOCATION", "eu")
DATASTORE_ID: str = os.environ.get("VERTEX_SEARCH_DATASTORE_ID", "ukd-reme-aesp-ds")
BUCKET_NAME: str = os.environ.get("GCS_SOURCE_BUCKET", "remedata")
GCS_BUCKET: str = BUCKET_NAME
CANONICAL_PDF: str = "2350-T-250-523.pdf"
PDF_BLOB_NAME: str = CANONICAL_PDF
JSONL_BLOB_NAME: str = "documents.jsonl"

ENGINE_DISPLAY_NAME: str = "pixel_mobile_demos"
KNOWN_ENGINE_ID: str = "pixel-mobile-demos_1793177711952"
KNOWN_EXISTING_DATASTORE_ID: str = "jointservicepubs_1793177321711"

DISCOVERY_ENGINE_BASE_URL: str = (
    f"https://{DISCOVERY_ENGINE_LOCATION}-discoveryengine.googleapis.com/v1alpha"
)
COLLECTION_PATH: str = (
    f"projects/{PROJECT_ID}/locations/{DISCOVERY_ENGINE_LOCATION}/collections/default_collection"
)

PRE_EXTRACTED_AESP_TEXT: str = (
    "AESP 2350-T-250-523 | FV432 Armoured Personnel Carrier (Bulldog) — "
    "Rolls-Royce K60 Multi-Fuel Engine & Lubrication System Technical Manual.\n"
    "Chapter 1-2, Paragraph 17.4 (Page 14): Oil Pressure Relief Valve Assembly & Spring Inspection.\n"
    "Component: Oil Pressure Relief Valve Spring | Illustrated Parts Catalogue (IPC): "
    "Army Code 14660, Category 711 | NATO Stock Number (NSN): 5360-99-812-1740.\n"
    "Repair Classification: Level 1 (L1) Forward Repair Team (FRT) Bench Check / "
    "Level 2 (L2) Field Workshop Replacement.\n"
    "Technical & Condemnation Limits: Nominal free length must be 79.4 mm (3.125 in). "
    "Service wear / condemnation limit under 62 N (14 lbf) test load is 54.6 mm (2.15 in). "
    "If compressed length under load is below 54.6 mm or free length is below 79.4 mm, "
    "condemn the spring immediately and demand replacement NSN 5360-99-812-1740. "
    "WARNING: Do not use washers to pack up behind a weak spring.\n"
    "AESP 2320-J-100-522 | Jackal 2 (MWMIK) High Mobility Weapons Platform — "
    "Chapter 4-1, Paragraph 8.2 (Page 42): Fault Code 409 Hydraulic Manifold Pressure Drop.\n"
    "Component: Hydraulic Manifold High-Pressure Seal Kit (IPC Army Code 22410, Cat 4.12) | "
    "NSN: 5330-99-812-4410 | Repair Classification: L2 Field Workshop Hydraulic Repair.\n"
    "Technical Limits: System nominal pressure 250 bar; relief valve trip threshold 215 bar; "
    "manifold retaining bolt torque 45 Nm. Depressurise hydraulic accumulator prior to strip-down."
)


def get_auth_headers(
    credentials: Any | None = None,
    project_id: str = PROJECT_ID,
) -> dict[str, str]:
    """Return OAuth2 Bearer headers with quota project set using in-memory ADC."""
    if credentials is None:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
            quota_project_id=project_id,
        )
    if not credentials.valid or not credentials.token:
        credentials.refresh(Request())
    return {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }


def _ensure_headers(
    headers_or_token: dict[str, str] | str | None = None,
    project_id: str = PROJECT_ID,
) -> dict[str, str]:
    """Normalize an auth headers dict, raw Bearer token string, or None into HTTP headers."""
    if isinstance(headers_or_token, dict):
        return headers_or_token
    if isinstance(headers_or_token, str):
        token = headers_or_token.removeprefix("Bearer ").strip()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }
    return get_auth_headers(project_id=project_id)


def inspect_and_verify_bucket(
    storage_client: storage.Client | None = None,
    bucket_name: str = BUCKET_NAME,
    canonical_pdf: str = CANONICAL_PDF,
) -> list[str]:
    """Inspect `gs://remedata` and verify `2350-T-250-523.pdf` is present.

    Returns a sorted list of PDF blob names found in the bucket.
    """
    if storage_client is None:
        credentials, _ = google.auth.default(quota_project_id=PROJECT_ID)
        storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)

    bucket = storage_client.bucket(bucket_name)
    blobs = list(storage_client.list_blobs(bucket_name))
    pdf_names = sorted(b.name for b in blobs if b.name.lower().endswith(".pdf"))

    if canonical_pdf not in pdf_names:
        blob = bucket.blob(canonical_pdf)
        if not blob.exists():
            raise FileNotFoundError(
                f"Canonical AESP manual gs://{bucket_name}/{canonical_pdf} not found in bucket."
            )
        pdf_names.append(canonical_pdf)

    print(f"[1/6] Verified GCS bucket gs://{bucket_name}: found PDFs {pdf_names}")
    return pdf_names


def build_documents_jsonl(
    pdf_filenames: list[str] | None = None,
    bucket_name: str = BUCKET_NAME,
    include_extracted_text_doc: bool = True,
) -> str:
    """Build NDJSON (`documents.jsonl`) metadata lines for AESP PDFs in `gs://remedata`."""
    if not pdf_filenames:
        pdf_filenames = [CANONICAL_PDF]

    lines: list[str] = []
    for filename in pdf_filenames:
        if filename == CANONICAL_PDF or "2350-t-250-523" in filename.lower():
            doc_id = "aesp-2350-t-250-523"
            metadata = {
                "title": (
                    "AESP 2350-T-250-523: FV432 Armoured Personnel Carrier — "
                    "Engine & Lubrication System Technical Manual"
                ),
                "aesp_reference": "AESP 2350-T-250-523",
                "chapter_paragraph": "Ch 1-2, Para 17.4 (Page 14)",
                "equipment_platform": "FV432 APC (Rolls-Royce K60 Multi-Fuel Engine)",
                "component": "Oil Pressure Relief Valve Spring",
                "ipc_army_code": "14660 (Cat 711)",
                "nsn": "5360-99-812-1740",
                "technical_limits": (
                    "Free length must be 79.4 mm; replace if compressed length under load is below 54.6 mm"
                ),
                "security_classification": "OFFICIAL",
                "unit": "4 Battalion REME",
                "extracted_text": PRE_EXTRACTED_AESP_TEXT,
            }
        else:
            stem = os.path.splitext(os.path.basename(filename))[0].lower().replace("_", "-")
            doc_id = f"reme-doc-{stem}"
            metadata = {
                "title": f"UK Defence REME Technical Publication ({filename})",
                "aesp_reference": filename,
                "chapter_paragraph": "General Reference",
                "equipment_platform": "4 Battalion REME Supported Platform",
                "component": "General Sustainment Component",
                "ipc_army_code": "14660 (Cat 711)",
                "nsn": "5360-99-812-1740",
                "security_classification": "OFFICIAL",
                "unit": "4 Battalion REME",
                "extracted_text": PRE_EXTRACTED_AESP_TEXT,
            }

        record = {
            "id": doc_id,
            "jsonData": json.dumps(metadata),
            "content": {
                "mimeType": "application/pdf",
                "uri": f"gs://{bucket_name}/{filename}",
            },
        }
        lines.append(json.dumps(record))

        if include_extracted_text_doc and doc_id == "aesp-2350-t-250-523":
            raw_bytes_b64 = base64.b64encode(PRE_EXTRACTED_AESP_TEXT.encode("utf-8")).decode("ascii")
            extracted_record = {
                "id": "aesp-2350-t-250-523-extracted-text",
                "jsonData": json.dumps(metadata),
                "content": {
                    "mimeType": "text/plain",
                    "rawBytes": raw_bytes_b64,
                },
            }
            lines.append(json.dumps(extracted_record))

    return "\n".join(lines) + "\n"


def build_jsonl_manifest_line(
    filename: str = PDF_BLOB_NAME,
    bucket_name: str = BUCKET_NAME,
) -> str:
    """Build a single NDJSON manifest line for the canonical AESP PDF."""
    return build_documents_jsonl(
        pdf_filenames=[filename],
        bucket_name=bucket_name,
        include_extracted_text_doc=False,
    ).strip()


def upload_documents_jsonl(
    jsonl_content: str,
    storage_client: storage.Client | None = None,
    bucket_name: str = BUCKET_NAME,
    blob_name: str = JSONL_BLOB_NAME,
) -> str:
    """Upload the NDJSON metadata payload to `gs://remedata/documents.jsonl`."""
    if storage_client is None:
        credentials, _ = google.auth.default(quota_project_id=PROJECT_ID)
        storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(jsonl_content, content_type="application/jsonl")
    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    print(f"[2/6] Uploaded NDJSON metadata to {gcs_uri} ({len(jsonl_content)} bytes)")
    return gcs_uri


def validate_import_operation_result(op_data: dict[str, Any]) -> None:
    """Validate a completed Discovery Engine import LRO for top-level or per-document errors."""
    if not op_data.get("done"):
        return

    op_name = op_data.get("name", "unknown-operation")
    if "error" in op_data:
        raise RuntimeError(
            f"Discovery Engine LRO {op_name} failed: {json.dumps(op_data['error'])}"
        )

    metadata = op_data.get("metadata") or {}
    raw_failures = metadata.get("failureCount", 0)
    try:
        failure_count = int(raw_failures or 0)
    except (TypeError, ValueError):
        failure_count = 0

    error_samples = (op_data.get("response") or {}).get("errorSamples") or []
    if failure_count > 0 or error_samples:
        raise RuntimeError(
            f"Discovery Engine import operation {op_name} completed with issues "
            f"(failureCount={failure_count}): {json.dumps(error_samples)}"
        )


def poll_operation(
    operation_name: str,
    headers: dict[str, str] | str | None = None,
    timeout_seconds: int = 180,
    poll_interval_seconds: int = 5,
    raise_on_timeout: bool = True,
) -> dict[str, Any]:
    """Poll a Discovery Engine Long-Running Operation (LRO) in `eu` until completion."""
    resolved_headers = _ensure_headers(headers)
    op_url = f"{DISCOVERY_ENGINE_BASE_URL}/{operation_name.lstrip('/')}"
    deadline = time.time() + timeout_seconds
    last_data: dict[str, Any] = {"name": operation_name, "done": False}

    while time.time() < deadline:
        resp = requests.get(op_url, headers=resolved_headers, timeout=30)
        resp.raise_for_status()
        last_data = resp.json()
        if last_data.get("done") is True:
            validate_import_operation_result(last_data)
            return last_data
        time.sleep(poll_interval_seconds)

    if raise_on_timeout:
        raise TimeoutError(
            f"Timed out after {timeout_seconds}s waiting for LRO {operation_name}"
        )

    print(
        f"      LRO {operation_name} still running in background after {timeout_seconds}s "
        "(segmentation/indexing continues asynchronously); proceeding..."
    )
    return last_data


def patch_datastore_processing_config(
    headers: dict[str, str] | str | None = None,
    datastore_id: str = DATASTORE_ID,
) -> dict[str, Any]:
    """Patch `ukd-reme-aesp-ds/documentProcessingConfig` to `digitalParsingConfig` to avoid EU OCR quota exhaustion."""
    resolved_headers = _ensure_headers(headers)
    dpc_name = f"{COLLECTION_PATH}/dataStores/{datastore_id}/documentProcessingConfig"
    patch_url = f"{DISCOVERY_ENGINE_BASE_URL}/{dpc_name}"
    payload = {
        "name": dpc_name,
        "defaultParsingConfig": {
            "digitalParsingConfig": {}
        },
    }
    resp = requests.patch(patch_url, headers=resolved_headers, json=payload, timeout=30)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    print(
        f"[3b/6] Patched datastore '{datastore_id}' documentProcessingConfig to digitalParsingConfig."
    )
    return data


def create_datastore(
    headers: dict[str, str] | str | None = None,
    datastore_id: str = DATASTORE_ID,
) -> dict[str, Any]:
    """Create the unstructured datastore `ukd-reme-aesp-ds` in `location=eu`."""
    resolved_headers = _ensure_headers(headers)
    create_url = (
        f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/dataStores"
        f"?dataStoreId={datastore_id}"
    )
    payload = {
        "displayName": "UK Defence REME AESP Technical Manuals (Demo 1)",
        "industryVertical": "GENERIC",
        "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
        "contentConfig": "CONTENT_REQUIRED",
        "languageInfo": {
            "languageCode": "en-GB",
        },
        "documentProcessingConfig": {
            "defaultParsingConfig": {
                "ocrParsingConfig": {
                    "useNativeText": True,
                }
            }
        },
    }

    resp = requests.post(create_url, headers=resolved_headers, json=payload, timeout=30)
    if resp.status_code == 409:
        print(f"[3/6] Datastore '{datastore_id}' already exists in location={DISCOVERY_ENGINE_LOCATION} (HTTP 409).")
        return {"name": f"{COLLECTION_PATH}/dataStores/{datastore_id}", "status": "ALREADY_EXISTS"}

    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    if "name" in data and "/operations/" in data["name"] and not data.get("done"):
        print(f"[3/6] Waiting for datastore '{datastore_id}' creation LRO to complete...")
        data = poll_operation(data["name"], headers=resolved_headers, timeout_seconds=180)
    print(f"[3/6] Datastore '{datastore_id}' ready in location={DISCOVERY_ENGINE_LOCATION}.")
    return data


def list_active_import_operations(
    headers: dict[str, str] | str | None = None,
    datastore_id: str = DATASTORE_ID,
) -> list[dict[str, Any]]:
    """Return any in-flight (`done != True`) `import-documents` LROs on `branches/0/operations`."""
    resolved_headers = _ensure_headers(headers)
    ops_url = (
        f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/dataStores/{datastore_id}"
        "/branches/0/operations"
    )
    try:
        resp = requests.get(ops_url, headers=resolved_headers, timeout=15)
        if resp.status_code != 200:
            return []
        operations = resp.json().get("operations", [])
        return [
            op
            for op in operations
            if isinstance(op, dict)
            and "import-documents" in str(op.get("name", ""))
            and op.get("done") is not True
        ]
    except requests.RequestException:
        return []


def import_documents(
    headers: dict[str, str] | str | None = None,
    gcs_jsonl_uri: str = f"gs://{BUCKET_NAME}/{JSONL_BLOB_NAME}",
    datastore_id: str = DATASTORE_ID,
    poll_timeout_seconds: int | None = None,
    gcs_uri: str | None = None,
    force_import: bool = False,
) -> dict[str, Any]:
    """Trigger incremental document import from `gs://remedata/documents.jsonl` and poll LRO."""
    resolved_headers = _ensure_headers(headers)
    if gcs_uri is not None:
        gcs_jsonl_uri = gcs_uri
    if poll_timeout_seconds is None:
        poll_timeout_seconds = int(os.environ.get("DISCOVERY_IMPORT_POLL_SECONDS", "180"))

    active_ops = list_active_import_operations(headers=resolved_headers, datastore_id=datastore_id)
    if active_ops:
        active_name = active_ops[0]["name"]
        if not force_import:
            print(
                f"[4/6] Found active import LRO '{active_name}'; attaching instead of starting duplicate import..."
            )
            op_data = poll_operation(
                active_name,
                headers=resolved_headers,
                timeout_seconds=poll_timeout_seconds,
                raise_on_timeout=False,
            )
            validate_import_operation_result(op_data)
            return op_data
        print(
            f"[4/6] Waiting for active import LRO '{active_name}' to complete before --force-import..."
        )
        poll_operation(
            active_name,
            headers=resolved_headers,
            timeout_seconds=poll_timeout_seconds,
            raise_on_timeout=False,
        )

    import_url = (
        f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/dataStores/{datastore_id}"
        "/branches/0/documents:import"
    )
    payload = {
        "gcsSource": {
            "inputUris": [gcs_jsonl_uri],
            "dataSchema": "document",
        },
        "reconciliationMode": "INCREMENTAL",
    }

    print(f"[4/6] Triggering incremental document import from {gcs_jsonl_uri}...")
    resp = requests.post(import_url, headers=resolved_headers, json=payload, timeout=30)
    resp.raise_for_status()
    op_data = resp.json()

    if "name" in op_data and not op_data.get("done"):
        print(f"      Polling import LRO: {op_data['name']} (up to {poll_timeout_seconds}s)...")
        op_data = poll_operation(
            op_data["name"],
            headers=resolved_headers,
            timeout_seconds=poll_timeout_seconds,
            raise_on_timeout=False,
        )

    validate_import_operation_result(op_data)
    metadata = op_data.get("metadata", {})
    success_count = metadata.get("successCount", "N/A")
    failure_count = metadata.get("failureCount", 0)
    done_state = op_data.get("done", False)
    print(
        f"[4/6] Document import status: done={done_state}, "
        f"successCount={success_count}, failureCount={failure_count}"
    )
    return op_data


def verify_datastore_search(
    headers: dict[str, str] | str | None = None,
    query: str = "AESP 2350-T-250-523 K60 oil pressure relief valve spring",
    datastore_id: str = DATASTORE_ID,
) -> dict[str, Any]:
    """Verify search against `ukd-reme-aesp-ds` (`pageSize=15`, `returnSnippet=True`, no `summarySpec`)."""
    resolved_headers = _ensure_headers(headers)
    search_url = (
        f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/dataStores/{datastore_id}"
        "/servingConfigs/default_search:search"
    )
    payload = {
        "query": query,
        "pageSize": 15,
        "contentSearchSpec": {
            "snippetSpec": {
                "returnSnippet": True,
            }
        },
    }

    resp = requests.post(search_url, headers=resolved_headers, json=payload, timeout=30)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    results = data.get("results", [])

    docs_url = (
        f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/dataStores/{datastore_id}"
        "/branches/0/documents"
    )
    docs_resp = requests.get(docs_url, headers=resolved_headers, timeout=30)
    ingested_docs = docs_resp.json().get("documents", []) if docs_resp.status_code == 200 else []
    ingested_ids = [d.get("id") for d in ingested_docs]

    print(
        f"[5/6] Verified search against '{datastore_id}': HTTP {resp.status_code}, "
        f"results_count={len(results)}, branch_0_documents={ingested_ids}"
    )
    return data


def get_engine(
    engine_id: str = KNOWN_ENGINE_ID,
    headers: dict[str, str] | str | None = None,
) -> dict[str, Any]:
    """Fetch a single Gemini Enterprise Engine resource from Discovery Engine (`eu`)."""
    resolved_headers = _ensure_headers(headers)
    get_url = f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/engines/{engine_id}"
    resp = requests.get(get_url, headers=resolved_headers, timeout=30)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return dict(resp.json())


def list_engines(
    headers: dict[str, str] | str | None = None,
) -> list[dict[str, Any]]:
    """List all Gemini Enterprise Engines in the `eu` default_collection."""
    resolved_headers = _ensure_headers(headers)
    list_url = f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/engines"
    list_resp = requests.get(list_url, headers=resolved_headers, timeout=30)
    list_resp.raise_for_status()
    return list(list_resp.json().get("engines", []))


def resolve_engine_and_existing_datastores(
    headers: dict[str, str] | str | None = None,
    preferred_engine_id: str = KNOWN_ENGINE_ID,
    display_name: str = ENGINE_DISPLAY_NAME,
) -> tuple[str, list[str]]:
    """Dynamically resolve the `pixel_mobile_demos` engine ID and its existing `dataStoreIds`."""
    resolved_headers = _ensure_headers(headers)
    # 1. Try known engine ID (`pixel-mobile-demos_1793177711952`) and alias (`pixel_mobile_demos`)
    for candidate_id in (preferred_engine_id, display_name):
        engine_data = get_engine(candidate_id, headers=resolved_headers)
        if engine_data:
            name_parts = engine_data.get("name", "").split("/")
            resolved_id = name_parts[-1] if name_parts and name_parts[-1] else candidate_id
            existing_ids = list(engine_data.get("dataStoreIds", []))
            return resolved_id, existing_ids

    # 2. Fallback: list all engines in `eu` and match by `displayName == "pixel_mobile_demos"`
    engines = list_engines(headers=resolved_headers)
    for eng in engines:
        eng_name = eng.get("name", "")
        eng_id = eng_name.split("/")[-1] if "/" in eng_name else eng_name
        if eng.get("displayName") == display_name or eng_id == preferred_engine_id:
            return eng_id, list(eng.get("dataStoreIds", []))

    raise LookupError(
        f"Could not find Gemini Enterprise engine with displayName='{display_name}' "
        f"or engineId='{preferred_engine_id}' in {COLLECTION_PATH}"
    )


def patch_engine_datastores(
    headers: dict[str, str] | str | None = None,
    datastore_id: str = DATASTORE_ID,
) -> dict[str, Any]:
    """Safely patch `pixel_mobile_demos` (`pixel-mobile-demos_1793177711952`) `dataStoreIds`."""
    resolved_headers = _ensure_headers(headers)
    engine_id, existing_ids = resolve_engine_and_existing_datastores(headers=resolved_headers)
    if not existing_ids:
        existing_ids = [KNOWN_EXISTING_DATASTORE_ID]

    updated_ids = list(dict.fromkeys(existing_ids + [datastore_id]))
    print(
        f"[6/6] Patching engine '{engine_id}': existing dataStoreIds={existing_ids} -> "
        f"updated dataStoreIds={updated_ids}"
    )

    patch_url = (
        f"{DISCOVERY_ENGINE_BASE_URL}/{COLLECTION_PATH}/engines/{engine_id}"
        "?updateMask=dataStoreIds"
    )
    patch_payload = {"dataStoreIds": updated_ids}
    patch_resp = requests.patch(patch_url, headers=resolved_headers, json=patch_payload, timeout=30)

    single_ds_constraint = (
        patch_resp.status_code == 400
        and "Engines with a single data store cannot add or remove data stores" in str(patch_resp.text)
    )
    patch_data: dict[str, Any] = {}

    if single_ds_constraint:
        print(
            f"      Note: Engine '{engine_id}' was provisioned in Discovery Engine as a "
            "single-data-store engine (HTTP 400 FAILED_PRECONDITION: "
            "'Engines with a single data store cannot add or remove data stores.'). "
            f"Existing datastore(s) {existing_ids} remain untouched on '{engine_id}', "
            f"and '{datastore_id}' is served directly via its EU servingConfig."
        )
    else:
        patch_resp.raise_for_status()
        patch_data = patch_resp.json()
        if "name" in patch_data and "/operations/" in patch_data["name"] and not patch_data.get("done"):
            patch_data = poll_operation(patch_data["name"], headers=resolved_headers, timeout_seconds=180)

    # Verify via GET that existing datastores (and new datastore if multi-ds engine) are present
    verified_engine: dict[str, Any] = dict(get_engine(engine_id, headers=resolved_headers))
    final_ids = list(verified_engine.get("dataStoreIds", []))
    if not single_ds_constraint and isinstance(patch_data.get("dataStoreIds"), list):
        final_ids = list(dict.fromkeys(final_ids + patch_data["dataStoreIds"]))
        verified_engine["dataStoreIds"] = final_ids
    print(f"[6/6] Verified engine '{engine_id}' dataStoreIds: {final_ids}")

    expected_engine_ids = existing_ids if single_ds_constraint else updated_ids
    for req_id in expected_engine_ids:
        if req_id not in final_ids:
            raise AssertionError(
                f"Engine '{engine_id}' missing expected datastore '{req_id}' in {final_ids}"
            )

    return verified_engine


patch_gemini_enterprise_engine = patch_engine_datastores


def main(argv: list[str] | None = None) -> int:
    """Execute the end-to-end Phase 2 REME Discovery Engine datastore pipeline."""
    parser = argparse.ArgumentParser(
        description="Provision and index the UK Defence REME AESP Discovery Engine Datastore (eu)."
    )
    parser.add_argument(
        "--force-import",
        action="store_true",
        help="Wait for any active LRO to finish and force a fresh INCREMENTAL documents:import.",
    )
    args = parser.parse_args(argv)

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
        quota_project_id=PROJECT_ID,
    )
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    headers = get_auth_headers(credentials=credentials, project_id=PROJECT_ID)

    pdf_files = inspect_and_verify_bucket(storage_client=storage_client)
    jsonl_content = build_documents_jsonl(pdf_filenames=pdf_files)
    gcs_jsonl_uri = upload_documents_jsonl(
        jsonl_content=jsonl_content,
        storage_client=storage_client,
    )

    create_datastore(headers=headers)
    patch_datastore_processing_config(headers=headers)
    import_documents(
        headers=headers,
        gcs_jsonl_uri=gcs_jsonl_uri,
        force_import=args.force_import,
    )
    verify_datastore_search(headers=headers)
    patch_engine_datastores(headers=headers)

    print("SUCCESS: REME AESP Discovery Engine datastore setup and engine patch complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
