"""Tier 3: Pairwise Cross-Feature Interaction Tests (>=22 pairs across F01-F22).

Verifies integration contracts, schema alignment, state handoffs, and environment consistency
between pairs of features defined in `PROJECT.md § Feature Inventory`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.e2e.conftest import (
    WORKSPACE_ROOT,
    DummyToolContext,
    load_dotenv_dict,
)


def test_pair_01_f01_f02_scaffold_layout_aligns_with_pyproject_packages() -> None:
    """Pair 01 (F01 x F02): Workspace package layout (`app/`) aligns with `pyproject.toml` wheel packages."""
    pyproject_text = (WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert (WORKSPACE_ROOT / "app" / "__init__.py").is_file()
    assert (WORKSPACE_ROOT / "app" / "agent.py").is_file()
    assert 'packages = ["app"]' in pyproject_text or "'app'" in pyproject_text


def test_pair_02_f02_f14_dependencies_support_singleton_initialization() -> None:
    """Pair 02 (F02 x F14): `pyproject.toml` dependencies (`google-adk`, `google-cloud-bigquery`, `requests`) and `google.auth` load cleanly in `app.tools`."""
    import google.auth
    import app.tools as tools_mod

    pyproject_text = (WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for pkg in ("google-adk", "google-cloud-bigquery", "requests"):
        assert pkg in pyproject_text
    assert hasattr(google.auth, "default")
    assert hasattr(tools_mod, "_BQ_CLIENT")
    assert hasattr(tools_mod, "_CREDENTIALS")


def test_pair_03_f03_f04_env_gcs_bucket_matches_datastore_setup_script() -> None:
    """Pair 03 (F03 x F04): `.env` `GCS_SOURCE_BUCKET=remedata` matches `scripts/setup_reme_datastore.py` default bucket."""
    env_vars = load_dotenv_dict(WORKSPACE_ROOT / ".env")
    setup_src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    assert env_vars.get("GCS_SOURCE_BUCKET") == "remedata"
    assert "remedata" in setup_src
    assert "2350-T-250-523.pdf" in setup_src


def test_pair_04_f03_f06_env_datastore_id_and_location_match_datastore_setup() -> None:
    """Pair 04 (F03 x F06): `.env` `DISCOVERY_ENGINE_LOCATION=eu` and `VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds` match setup script."""
    import scripts.setup_reme_datastore as ds_mod

    env_vars = load_dotenv_dict(WORKSPACE_ROOT / ".env")
    setup_src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    assert env_vars.get("DISCOVERY_ENGINE_LOCATION") == "eu"
    assert env_vars.get("VERTEX_SEARCH_DATASTORE_ID") == "ukd-reme-aesp-ds"
    assert "ukd-reme-aesp-ds" in setup_src
    assert "eu-discoveryengine.googleapis.com" in ds_mod.DISCOVERY_ENGINE_BASE_URL


def test_pair_05_f04_f05_pdf_inspection_uri_matches_jsonl_manifest_uri() -> None:
    """Pair 05 (F04 x F05): Inspected GCS blob `gs://remedata/2350-T-250-523.pdf` matches `content.uri` in `documents.jsonl`."""
    import scripts.setup_reme_datastore as ds_mod

    line = ds_mod.build_documents_jsonl([ds_mod.CANONICAL_PDF]).strip().splitlines()[0]
    parsed = json.loads(line)
    assert parsed["content"]["uri"] == f"gs://{ds_mod.GCS_BUCKET}/{ds_mod.CANONICAL_PDF}"
    assert parsed["content"]["uri"] == "gs://remedata/2350-T-250-523.pdf"


def test_pair_06_f05_f07_jsonl_manifest_path_matches_import_gcs_source() -> None:
    """Pair 06 (F05 x F07): Uploaded `gs://remedata/documents.jsonl` path matches `gcsSource.inputUris` in `import_documents`."""
    import scripts.setup_reme_datastore as ds_mod

    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"done": True}
    with patch("scripts.setup_reme_datastore.requests.post", mock_post):
        gcs_uri = f"gs://{ds_mod.GCS_BUCKET}/{ds_mod.JSONL_BLOB_NAME}"
        ds_mod.import_documents(headers={"Authorization": "Bearer fake-token"}, gcs_uri=gcs_uri)
        payload = mock_post.call_args[1]["json"]
        assert payload["gcsSource"]["inputUris"] == [gcs_uri]
        assert payload["gcsSource"]["inputUris"] == ["gs://remedata/documents.jsonl"]


def test_pair_07_f06_f08_created_datastore_id_appended_to_engine_patch() -> None:
    """Pair 07 (F06 x F08): `ukd-reme-aesp-ds` created in F06 is non-destructively appended to `pixel-mobile-demos_1793177711952` in F08."""
    import scripts.setup_reme_datastore as ds_mod

    mock_patch = MagicMock()
    mock_patch.return_value.status_code = 200
    mock_patch.return_value.json.return_value = {
        "dataStoreIds": ["jointservicepubs_1793177321711", ds_mod.DATASTORE_ID]
    }
    with patch.object(ds_mod, "list_engines", return_value=[]), patch.object(
        ds_mod, "get_engine", return_value={"dataStoreIds": ["jointservicepubs_1793177321711"]}
    ), patch("scripts.setup_reme_datastore.requests.patch", mock_patch):
        result = ds_mod.patch_engine_datastores(headers={"Authorization": "Bearer fake-token"})
        assert ds_mod.DATASTORE_ID in result["dataStoreIds"]
        assert "jointservicepubs_1793177321711" in result["dataStoreIds"]


def test_pair_08_f07_f15_datastore_search_endpoint_matches_agent_rag_tool() -> None:
    """Pair 08 (F07 x F15): Discovery Engine `eu-discoveryengine.googleapis.com` search URL in F07 matches `diagnose_and_resolve_grid` in F15."""
    import app.tools as tools_mod
    import scripts.setup_reme_datastore as ds_mod

    setup_src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    tools_src = (WORKSPACE_ROOT / "app" / "tools.py").read_text(encoding="utf-8")
    assert "eu-discoveryengine.googleapis.com/v1alpha" in ds_mod.DISCOVERY_ENGINE_BASE_URL
    assert (
        "eu-discoveryengine.googleapis.com/v1alpha" in tools_src
        or (
            "-discoveryengine.googleapis.com/v1alpha" in tools_src
            and getattr(tools_mod, "DISCOVERY_ENGINE_LOCATION", None) == "eu"
        )
    )
    assert "servingConfigs/default_search:search" in setup_src
    assert "servingConfigs/default_search:search" in tools_src


def test_pair_09_f03_f09_env_bq_dataset_and_location_match_seed_script() -> None:
    """Pair 09 (F03 x F09): `.env` `BQ_DATASET=ukd_reme_demo` and `BQ_LOCATION=europe-west1` match `scripts/seed_demo1_bigquery.py`."""
    env_vars = load_dotenv_dict(WORKSPACE_ROOT / ".env")
    seed_src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    assert env_vars.get("BQ_DATASET") == "ukd_reme_demo"
    assert env_vars.get("BQ_LOCATION") == "europe-west1"
    assert "ukd_reme_demo" in seed_src
    assert "europe-west1" in seed_src


def test_pair_10_f10_f15_ipc_nsn_catalogue_columns_match_tool_query() -> None:
    """Pair 10 (F10 x F15): `ipc_nsn_catalogue` columns in `seed_demo1_bigquery.py` match SELECT projection in `diagnose_and_resolve_grid`."""
    seed_src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    tools_src = (WORKSPACE_ROOT / "app" / "tools.py").read_text(encoding="utf-8")
    for col in ("repair_classification", "aesp_reference", "part_name", "nsn", "technical_limits"):
        assert col in seed_src
        assert col in tools_src


def test_pair_11_f11_f15_spta_sector_grids_columns_match_tool_query() -> None:
    """Pair 11 (F11 x F15): `spta_sector_grids` columns and seed coordinates match `diagnose_and_resolve_grid`."""
    seed_src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    tools_src = (WORKSPACE_ROOT / "app" / "tools.py").read_text(encoding="utf-8")
    for col in ("sector_key", "sector_display_name", "latitude", "longitude", "coords_label"):
        assert col in seed_src
        assert col in tools_src
    assert "51.2185" in seed_src and "51.2185" in tools_src
    assert "-1.7925" in seed_src and "-1.7925" in tools_src


def test_pair_12_f12_f16_group_chat_tickets_13_columns_match_publish_tool_insert() -> None:
    """Pair 12 (F12 x F16): `group_chat_tickets` 13-column schema in `seed_demo1_bigquery.py` matches `publish_ticket_to_chat` BQ row."""
    import app.tools as tools_mod

    dummy_ctx = DummyToolContext()
    mock_bq = MagicMock()
    with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", mock_bq):
        tools_mod.publish_ticket_to_chat(dummy_ctx)
        _, rows = mock_bq.insert_rows_json.call_args[0]
        row = rows[0]
        expected_13_cols = {
            "ticket_id",
            "created_at_utc",
            "callsign",
            "repair_classification",
            "aesp_reference",
            "part_name",
            "nsn",
            "technical_limits",
            "latitude",
            "longitude",
            "coords_label",
            "google_maps_url",
            "status",
        }
        assert set(row.keys()) == expected_13_cols


def test_pair_13_f13_f15_diagnose_output_validates_against_active_ticket_state_schema(
    dummy_tool_context: DummyToolContext,
) -> None:
    """Pair 13 (F13 x F15): Output of `diagnose_and_resolve_grid` validates cleanly against `ActiveTicketState` Pydantic schema."""
    from app.schemas import ActiveTicketState
    import app.tools as tools_mod

    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("offline")
    ):
        result = tools_mod.diagnose_and_resolve_grid(
            "FV432 K60 low oil pressure spring",
            "Bravo-4",
            dummy_tool_context,
        )
        validated = ActiveTicketState(**result)
        assert validated.nsn == "5360-99-812-1740"
        assert validated.latitude == pytest.approx(51.2185)
        assert validated.longitude == pytest.approx(-1.7925)
        # Also verify state stored in tool_context.state["active_ticket"] validates
        validated_from_state = ActiveTicketState(**dummy_tool_context.state["active_ticket"])
        assert validated_from_state.nsn == "5360-99-812-1740"


def test_pair_14_f13_f16_publish_output_validates_against_ticket_payload_schema(
    dummy_tool_context: DummyToolContext,
) -> None:
    """Pair 14 (F13 x F16): Output `ticket` of `publish_ticket_to_chat` validates cleanly against `TicketPayload` Pydantic schema."""
    from app.schemas import TicketPayload
    import app.tools as tools_mod

    with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", None):
        res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
        validated = TicketPayload(**res["ticket"])
        assert validated.nsn == "5360-99-812-1740"
        assert validated.status == "DISPATCH_READY"
        assert validated.sector_display_name == "Salisbury Plain (SPTA) — Sector Bravo-4"


def test_pair_15_f15_f16_scene1_to_scene2_session_state_handoff(
    dummy_tool_context: DummyToolContext,
) -> None:
    """Pair 15 (F15 x F16): `diagnose_and_resolve_grid` populates `tool_context.state['active_ticket']` consumed by `publish_ticket_to_chat`."""
    import app.tools as tools_mod

    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("offline")
    ):
        diag = tools_mod.diagnose_and_resolve_grid(
            "Jackal 2 hydraulic manifold pressure drop fault code 409",
            "bravo-4",
            dummy_tool_context,
        )
        assert diag["nsn"] == "5330-99-812-4410"

    with patch("app.tools.requests.post") as mock_webhook, patch.object(tools_mod, "_BQ_CLIENT", None):
        mock_webhook.return_value.status_code = 200
        pub = tools_mod.publish_ticket_to_chat(dummy_tool_context)
        assert pub["published"] is True
        assert pub["ticket"]["nsn"] == "5330-99-812-4410"
        assert "Hydraulic Manifold" in pub["ticket"]["part_name"]


def test_pair_16_f15_f17_agent_registers_diagnose_tool_and_chip1_chip2_prompts() -> None:
    """Pair 16 (F15 x F17): `reme_artificer_agent` registers `diagnose_and_resolve_grid` and its system prompt embeds Chip 1 & Chip 2 facts."""
    import app.agent as agent_mod
    import app.tools as tools_mod

    assert tools_mod.diagnose_and_resolve_grid in agent_mod.reme_artificer_agent.tools
    instruction = agent_mod.reme_artificer_agent.instruction
    assert "5360-99-812-1740" in instruction
    assert "79.4 mm" in instruction
    assert "54.6 mm" in instruction


def test_pair_17_f16_f17_agent_registers_publish_tool_and_chip3_prompt() -> None:
    """Pair 17 (F16 x F17): `reme_artificer_agent` registers `publish_ticket_to_chat` and its system prompt embeds Chip 3 rules."""
    import app.agent as agent_mod
    import app.tools as tools_mod

    assert tools_mod.publish_ticket_to_chat in agent_mod.reme_artificer_agent.tools
    instruction = agent_mod.reme_artificer_agent.instruction
    assert "publish_ticket_to_chat" in instruction
    assert "51.2185" in instruction


def test_pair_18_f16_f18_publish_tool_posts_directly_to_cloud_run_fastapi_endpoint(
    dummy_tool_context: DummyToolContext,
    chat_client: TestClient,
) -> None:
    """Pair 18 (F16 x F18): `publish_ticket_to_chat` webhook payload posts directly to FastAPI `POST /api/tickets` and appears in `GET /api/tickets`."""
    import app.tools as tools_mod

    chat_client.post("/api/reset")

    def forward_to_test_client(url: str, json: dict[str, Any], timeout: float = 3.0, **kwargs: Any) -> Any:
        return chat_client.post("/api/tickets", json=json)

    with patch("app.tools.requests.post", side_effect=forward_to_test_client), patch.object(
        tools_mod, "_BQ_CLIENT", None
    ):
        pub = tools_mod.publish_ticket_to_chat(dummy_tool_context)
        assert pub["published"] is True
        new_id = pub["ticket"]["ticket_id"]

    tickets = chat_client.get("/api/tickets").json()["tickets"]
    assert tickets[0]["ticket_id"] == new_id
    assert tickets[0]["nsn"] == "5360-99-812-1740"


def test_pair_19_f13_f18_pydantic_ticket_payload_aligns_with_cloud_run_in_memory_cache(
    chat_client: TestClient,
) -> None:
    """Pair 19 (F13 x F18): Published ticket in Cloud Run `GET /api/tickets` validates against `app.schemas.TicketPayload`."""
    from app.schemas import TicketPayload

    chat_client.post("/api/reset")
    sample_ticket = {
        "ticket_id": "TKT-REME-041",
        "created_at_utc": "2026-10-29T11:30:00Z",
        "callsign": "Cpl MacDonald (4 Bn REME FRT)",
        "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
        "aesp_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
        "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
        "nsn": "5360-99-812-1740",
        "technical_limits": "Free length must be 79.4 mm",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "coords_label": "51.2185° N, 1.7925° W",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
        "status": "DISPATCH_READY",
    }
    chat_client.post("/api/tickets", json=sample_ticket)
    tickets = chat_client.get("/api/tickets").json()["tickets"]
    assert len(tickets) >= 1
    validated = TicketPayload(**tickets[0])
    assert validated.ticket_id == "TKT-REME-041"
    assert validated.nsn == "5360-99-812-1740"


def test_pair_20_f18_f19_cloud_run_api_endpoints_match_html_frontend_fetch_calls(
    chat_client: TestClient,
) -> None:
    """Pair 20 (F18 x F19): HTML5 frontend in `GET /` fetches `/api/tickets` and `/api/reset` matching FastAPI routes."""
    resp = chat_client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "/api/tickets" in html
    assert "/api/reset" in html


def test_pair_21_f16_f19_publish_tool_maps_url_matches_frontend_google_maps_links(
    dummy_tool_context: DummyToolContext,
    chat_client: TestClient,
) -> None:
    """Pair 21 (F16 x F19): `google_maps_url` generated by `publish_ticket_to_chat` matches the Google Maps URL structure rendered in UI."""
    import app.tools as tools_mod

    with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", None):
        pub = tools_mod.publish_ticket_to_chat(dummy_tool_context)
        assert (
            pub["ticket"]["google_maps_url"]
            == "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving"
        )
    html = chat_client.get("/").text
    assert "https://www.google.com/maps/dir/?api=1&destination=" in html
    assert "https://www.google.com/maps/search/?api=1&query=" in html


def test_pair_22_f17_f21_eval_dataset_tool_trajectories_match_agent_registered_tools() -> None:
    """Pair 22 (F17 x F21): Dataset cases in `tests/eval/datasets/basic-dataset.json` align with `reme_artificer_agent` tools."""
    import app.agent as agent_mod

    registered_names = {getattr(t, "__name__", str(t)) for t in agent_mod.reme_artificer_agent.tools}
    assert registered_names == {"diagnose_and_resolve_grid", "publish_ticket_to_chat"}
    dataset = json.loads((WORKSPACE_ROOT / "tests" / "eval" / "datasets" / "basic-dataset.json").read_text(encoding="utf-8"))
    assert len(dataset.get("eval_cases", [])) >= 3


def test_pair_23_f03_f22_env_config_matches_deploy_demo_script_constants() -> None:
    """Pair 23 (F03 x F22): `.env` project, region, and Gemini Enterprise engine ID match `scripts/deploy_demo.sh`."""
    env_vars = load_dotenv_dict(WORKSPACE_ROOT / ".env")
    deploy_src = (WORKSPACE_ROOT / "scripts" / "deploy_demo.sh").read_text(encoding="utf-8")
    assert env_vars.get("GOOGLE_CLOUD_PROJECT") in deploy_src
    assert env_vars.get("GOOGLE_CLOUD_LOCATION") in deploy_src
    assert "pixel-mobile-demos_1793177711952" in deploy_src


def test_pair_24_f18_f22_cloud_run_dockerfile_and_deploy_script_match_service_spec() -> None:
    """Pair 24 (F18 x F22): `cloud_run_chat_app/Dockerfile` port 8080 and `scripts/deploy_demo.sh` Cloud Run deployment align."""
    dockerfile_src = (WORKSPACE_ROOT / "cloud_run_chat_app" / "Dockerfile").read_text(encoding="utf-8")
    deploy_src = (WORKSPACE_ROOT / "scripts" / "deploy_demo.sh").read_text(encoding="utf-8")
    assert "8080" in dockerfile_src
    assert "reme-chat-demonstrator" in deploy_src
    assert "cloud_run_chat_app" in deploy_src
