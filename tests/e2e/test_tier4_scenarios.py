"""Tier 4: End-to-End Tactical Sustainment Application Scenarios (>=11 scenarios).

Exercises complete multi-step application workflows across Scenes 1, 2, and 3
of the UK Defence 4 Bn REME Tactical Sustainment & Sovereign Voice Triage Demo.
"""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.e2e.conftest import (
    WORKSPACE_ROOT,
    DummyToolContext,
    load_dotenv_dict,
)


def test_scenario_01_golden_path_fv432_k60_scene1_to_scene2_to_scene3(
    chat_client: TestClient,
) -> None:
    """Scenario 01: Full Golden Path (FV432 K60 low oil pressure at Bravo-4 -> Diagnose -> Publish -> Cloud Run feed)."""
    import app.tools as tools_mod
    from app.schemas import ActiveTicketState, TicketPayload

    # Step 0: Presenter resets Cloud Run feed before live take
    reset_resp = chat_client.post("/api/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json() == {"status": "reset", "tickets": []}

    ctx = DummyToolContext()

    # Step 1 (Scene 1): Diagnose FV432 K60 fault & resolve Sector Bravo-4 grid
    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("simulate local tool call")
    ):
        diag = tools_mod.diagnose_and_resolve_grid(
            "FV432 Bulldog, K60 engine showing low oil pressure at idle, relief valve spring",
            "Salisbury Plain Sector Bravo-4",
            ctx,
        )

    state_model = ActiveTicketState(**diag)
    assert "L1 FRT Fix" in state_model.repair_classification
    assert "AESP 2350-T-250-523" in state_model.aesp_reference
    assert "Oil Pressure Relief Valve Spring" in state_model.part_name
    assert state_model.nsn == "5360-99-812-1740"
    assert "79.4 mm" in state_model.technical_limits
    assert "54.6 mm" in state_model.technical_limits
    assert state_model.latitude == pytest.approx(51.2185)
    assert state_model.longitude == pytest.approx(-1.7925)

    # Step 2 (Scene 2): Publish structured ticket to Group Chat webhook & BigQuery ledger
    mock_bq = MagicMock()
    mock_bq.insert_rows_json.return_value = []

    def post_to_chat_app(url: str, json: dict[str, Any], timeout: float = 3.0, **kwargs: Any) -> Any:
        return chat_client.post("/api/tickets", json=json)

    with patch("app.tools.requests.post", side_effect=post_to_chat_app), patch.object(
        tools_mod, "_BQ_CLIENT", mock_bq
    ):
        pub = tools_mod.publish_ticket_to_chat(ctx)

    assert pub["published"] is True
    assert "✅ Ticket TKT-REME-" in pub["confirmation_badge"]
    ticket_model = TicketPayload(**pub["ticket"])
    assert ticket_model.nsn == "5360-99-812-1740"
    assert (
        ticket_model.google_maps_url
        == "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving"
    )

    # Step 3 (Scene 3): Verify Cloud Run Group Chat feed contains the newly published ticket at index 0
    feed_resp = chat_client.get("/api/tickets")
    assert feed_resp.status_code == 200
    tickets = feed_resp.json()["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["ticket_id"] == ticket_model.ticket_id
    assert tickets[0]["nsn"] == "5360-99-812-1740"
    assert tickets[0]["coords_label"] == "51.2185° N, 1.7925° W"


def test_scenario_02_jackal2_hydraulic_fault_409_end_to_end_triage_and_dispatch(
    chat_client: TestClient,
) -> None:
    """Scenario 02: Secondary Golden Path (Jackal 2 MWMIK fault code 409 -> NSN 5330-99-812-4410 -> Dispatch)."""
    import app.tools as tools_mod

    chat_client.post("/api/reset")
    ctx = DummyToolContext()

    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("offline")
    ):
        diag = tools_mod.diagnose_and_resolve_grid(
            "Jackal 2 MWMIK hydraulic manifold pressure drop, fault code 409",
            "Bravo-4",
            ctx,
        )

    assert diag["nsn"] == "5330-99-812-4410"
    assert "AESP 2320-J-100-522" in diag["aesp_reference"]
    assert "Hydraulic Manifold" in diag["part_name"]
    assert "250 bar" in diag["technical_limits"]

    def post_to_chat_app(url: str, json: dict[str, Any], timeout: float = 3.0, **kwargs: Any) -> Any:
        return chat_client.post("/api/tickets", json=json)

    with patch("app.tools.requests.post", side_effect=post_to_chat_app), patch.object(
        tools_mod, "_BQ_CLIENT", None
    ):
        pub = tools_mod.publish_ticket_to_chat(ctx)

    assert pub["published"] is True
    tickets = chat_client.get("/api/tickets").json()["tickets"]
    assert tickets[0]["nsn"] == "5330-99-812-4410"
    assert "Hydraulic Manifold" in tickets[0]["part_name"]


def test_scenario_03_degraded_spta_comms_garbled_ptt_voice_and_network_outage_resilience(
    chat_client: TestClient,
) -> None:
    """Scenario 03: Degraded SPTA radio comms (garbled PTT voice + Discovery Engine/BQ outage) still completes cleanly."""
    import app.tools as tools_mod

    ctx = DummyToolContext()
    broken_bq = MagicMock()
    broken_bq.query.side_effect = RuntimeError("BQ unreachable over tactical link")
    broken_bq.insert_rows_json.side_effect = RuntimeError("BQ unreachable over tactical link")

    with patch.object(tools_mod, "_BQ_CLIENT", broken_bq), patch(
        "app.tools.requests.post", side_effect=TimeoutError("Tactical link timeout")
    ):
        diag = tools_mod.diagnose_and_resolve_grid("...krrshh... oil... spring...", "...bravo...", ctx)
        assert diag["nsn"] == "5360-99-812-1740"
        assert diag["latitude"] == pytest.approx(51.2185)
        assert diag["longitude"] == pytest.approx(-1.7925)

        pub = tools_mod.publish_ticket_to_chat(ctx)
        assert pub["published"] is True
        assert pub["ticket"]["nsn"] == "5360-99-812-1740"
        assert "✅ Ticket TKT-REME-" in pub["confirmation_badge"]


def test_scenario_04_stateless_scene2_jump_without_prior_scene1_turn(
    chat_client: TestClient,
) -> None:
    """Scenario 04: Presenter jumps straight to Scene 2 ('Log the job to the REME group chat') with empty session state."""
    import app.tools as tools_mod

    chat_client.post("/api/reset")
    fresh_ctx = DummyToolContext()
    assert "active_ticket" not in fresh_ctx.state

    def post_to_chat_app(url: str, json: dict[str, Any], timeout: float = 3.0, **kwargs: Any) -> Any:
        return chat_client.post("/api/tickets", json=json)

    with patch("app.tools.requests.post", side_effect=post_to_chat_app), patch.object(
        tools_mod, "_BQ_CLIENT", None
    ):
        pub = tools_mod.publish_ticket_to_chat(fresh_ctx)

    assert pub["published"] is True
    assert pub["ticket"]["nsn"] == "5360-99-812-1740"
    assert pub["ticket"]["latitude"] == pytest.approx(51.2185)
    assert pub["ticket"]["longitude"] == pytest.approx(-1.7925)
    tickets = chat_client.get("/api/tickets").json()["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["ticket_id"] == pub["ticket"]["ticket_id"]


def test_scenario_05_multi_sector_grid_resolution_alpha1_and_london_forward_mounting(
    chat_client: TestClient,
) -> None:
    """Scenario 05: Resolving alternative sectors (`alpha-1` and `london`) via BigQuery and dispatching recovery."""
    import app.tools as tools_mod

    chat_client.post("/api/reset")
    ctx = DummyToolContext()

    # Simulate BQ returning Sector Alpha-1 coordinates
    mock_bq = MagicMock()
    catalogue_row = dict(tools_mod.GOLDEN_FALLBACK_K60)
    alpha1_row = {
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Alpha-1",
        "latitude": 51.2310,
        "longitude": -1.8150,
        "coords_label": "51.2310° N, 1.8150° W",
    }
    mock_bq.query.side_effect = [
        MagicMock(result=MagicMock(return_value=[catalogue_row])),
        MagicMock(result=MagicMock(return_value=[alpha1_row])),
    ]

    with patch.object(tools_mod, "_BQ_CLIENT", mock_bq), patch(
        "app.tools.requests.post", side_effect=OSError("no DE")
    ):
        diag = tools_mod.diagnose_and_resolve_grid("K60 oil pressure spring", "alpha-1", ctx)

    assert diag["sector_display_name"] == "Salisbury Plain (SPTA) — Sector Alpha-1"
    assert diag["latitude"] == pytest.approx(51.2310)
    assert diag["longitude"] == pytest.approx(-1.8150)

    def post_to_chat_app(url: str, json: dict[str, Any], timeout: float = 3.0, **kwargs: Any) -> Any:
        return chat_client.post("/api/tickets", json=json)

    with patch("app.tools.requests.post", side_effect=post_to_chat_app), patch.object(
        tools_mod, "_BQ_CLIENT", None
    ):
        pub = tools_mod.publish_ticket_to_chat(ctx)

    assert "51.231" in pub["ticket"]["google_maps_url"]


def test_scenario_06_presenter_multi_take_reset_sla_and_idempotency(
    chat_client: TestClient,
) -> None:
    """Scenario 06: Presenter publishes multiple tickets across rehearsals and resets via `/api/reset` and `/api/tickets/reset` in <1s."""
    sample_base = {
        "created_at_utc": "2026-04-17T08:15:00Z",
        "callsign": "Cpl MacDonald (4 Bn REME FRT)",
        "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
        "aesp_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
        "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
        "nsn": "5360-99-812-1740",
        "technical_limits": "Free length must be 79.4 mm",
        "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
        "latitude": 51.2185,
        "longitude": -1.7925,
        "coords_label": "51.2185° N, 1.7925° W",
        "google_maps_url": "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
        "status": "DISPATCH_READY",
    }
    for idx in range(3):
        chat_client.post("/api/tickets", json={**sample_base, "ticket_id": f"TKT-REME-10{idx}"})

    assert len(chat_client.get("/api/tickets").json()["tickets"]) >= 3

    t0 = time.perf_counter()
    r1 = chat_client.post("/api/reset")
    dt1 = time.perf_counter() - t0
    assert r1.status_code == 200
    assert dt1 < 1.0
    assert r1.json() == {"status": "reset", "tickets": []}
    assert chat_client.get("/api/tickets").json()["tickets"] == []

    # Also verify alias `/api/tickets/reset`
    chat_client.post("/api/tickets", json={**sample_base, "ticket_id": "TKT-REME-999"})
    assert len(chat_client.get("/api/tickets").json()["tickets"]) == 1

    t1 = time.perf_counter()
    r2 = chat_client.post("/api/tickets/reset")
    dt2 = time.perf_counter() - t1
    assert r2.status_code == 200
    assert dt2 < 1.0
    assert r2.json() == {"status": "reset", "tickets": []}


def test_scenario_07_discovery_engine_ocr_ingestion_and_non_destructive_engine_patch_workflow() -> None:
    """Scenario 07: End-to-end execution of `setup_reme_datastore.py` pipeline (inspect PDF -> JSONL -> create DS -> import -> verify -> patch engine)."""
    import scripts.setup_reme_datastore as ds_mod

    # 1. Build JSONL manifest line
    manifest_line = ds_mod.build_documents_jsonl([ds_mod.CANONICAL_PDF]).strip().splitlines()[0]
    doc = json.loads(manifest_line)
    assert doc["id"] == "aesp-2350-t-250-523"
    assert doc["content"]["uri"] == "gs://remedata/2350-T-250-523.pdf"

    # 2. Create datastore (idempotent 409 handling)
    mock_post = MagicMock()
    mock_post.return_value.status_code = 409
    mock_post.return_value.text = "ALREADY_EXISTS"
    with patch("scripts.setup_reme_datastore.requests.post", mock_post):
        ds_res = ds_mod.create_datastore(headers={"Authorization": "Bearer tok"})
        assert ds_res["status"] == "ALREADY_EXISTS"

    # 3. Patch Gemini Enterprise engine preserving jointservicepubs_1793177321711
    mock_patch = MagicMock()
    mock_patch.return_value.status_code = 200
    mock_patch.return_value.json.return_value = {
        "dataStoreIds": ["jointservicepubs_1793177321711", "ukd-reme-aesp-ds"]
    }
    with patch.object(ds_mod, "list_engines", return_value=[]), patch.object(
        ds_mod, "get_engine", return_value={"dataStoreIds": ["jointservicepubs_1793177321711"]}
    ), patch("scripts.setup_reme_datastore.requests.patch", mock_patch):
        patch_res = ds_mod.patch_engine_datastores(headers={"Authorization": "Bearer tok"})
        assert "jointservicepubs_1793177321711" in patch_res["dataStoreIds"]
        assert "ukd-reme-aesp-ds" in patch_res["dataStoreIds"]


def test_scenario_08_bigquery_provisioning_3_tables_and_100_percent_column_descriptions() -> None:
    """Scenario 08: Verify `seed_demo1_bigquery.py` provisions all 3 tables with 100% table and column descriptions and seed rows."""
    import scripts.seed_demo1_bigquery as bq_mod

    src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    for table_name in ("ipc_nsn_catalogue", "spta_sector_grids", "group_chat_tickets"):
        assert table_name in src
    # Verify seed row collections exist and contain all required golden records
    assert "5360-99-812-1740" in src
    assert "5330-99-812-4410" in src
    assert "TKT-REME-041" in src
    assert hasattr(bq_mod, "create_reme_dataset") and hasattr(bq_mod, "create_and_seed_table")


def test_scenario_09_adk_agent_3_chip_conversation_flow_and_safety_guardrails(
    dummy_tool_context: DummyToolContext,
) -> None:
    """Scenario 09: Verify `reme_artificer_agent` supports the 3-Chip conversation flow and enforces safety warning against packing washers."""
    import app.agent as agent_mod
    import app.tools as tools_mod

    agent = agent_mod.reme_artificer_agent
    assert agent.name == "reme_artificer_agent"
    assert agent.model == "gemini-2.5-flash"

    # Chip 1 & Chip 2: Diagnose & inspect technical limits
    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("offline")
    ):
        chip1_data = tools_mod.diagnose_and_resolve_grid(
            "FV432 Bulldog, K60 engine showing low oil pressure at idle",
            "Salisbury Plain Sector Bravo-4",
            dummy_tool_context,
        )
    assert "washer" in chip1_data["technical_limits"].lower()
    assert "washer" in agent.instruction.lower()

    # Chip 3: Log the job to the REME group chat
    with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", None):
        chip3_data = tools_mod.publish_ticket_to_chat(dummy_tool_context)
    assert chip3_data["published"] is True
    assert chip3_data["ticket"]["nsn"] == "5360-99-812-1740"


def test_scenario_10_scene3_recovery_crew_ui_inspection_and_google_maps_navigation(
    chat_client: TestClient,
) -> None:
    """Scenario 10: Scene 3 Recovery Crew opens the Group Chat dashboard, views ticket metadata, and launches Google Maps route."""
    chat_client.post("/api/reset")
    dashboard_resp = chat_client.get("/")
    assert dashboard_resp.status_code == 200
    html = dashboard_resp.text

    # Verify tactical header, dark theme, 1s polling, and dual Google Maps links (dir + search)
    assert "OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT" in html
    assert any(c in html.lower() for c in ("#0b0f19", "#0b0f14", "--bg-dark"))
    assert "1000" in html
    assert "https://www.google.com/maps/dir/?api=1&destination=" in html
    assert "https://www.google.com/maps/search/?api=1&query=" in html

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

    # Verify API feed returns complete metadata for rendering the card
    tickets = chat_client.get("/api/tickets").json()["tickets"]
    t0 = tickets[0]
    assert t0["ticket_id"] == "TKT-REME-041"
    assert t0["nsn"] == "5360-99-812-1740"
    assert t0["latitude"] == pytest.approx(51.2185)
    assert t0["longitude"] == pytest.approx(-1.7925)
    assert t0["google_maps_url"] == "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving"


def test_scenario_11_eval_dataset_and_deployment_pipeline_readiness() -> None:
    """Scenario 11: Verify `tests/eval/datasets/basic-dataset.json` and `scripts/deploy_demo.sh` are aligned for Milestone 4 & 5."""
    dataset_path = WORKSPACE_ROOT / "tests" / "eval" / "datasets" / "basic-dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert "eval_cases" in dataset
    assert len(dataset["eval_cases"]) >= 3

    deploy_path = WORKSPACE_ROOT / "scripts" / "deploy_demo.sh"
    deploy_src = deploy_path.read_text(encoding="utf-8")
    assert "GOOGLE_API_USE_CLIENT_CERTIFICATE=false" in deploy_src
    assert "sa-reme-demo@antig-dave.iam.gserviceaccount.com" in deploy_src
    assert "reme-chat-demonstrator" in deploy_src
    assert "agents-cli deploy" in deploy_src
    assert "agents-cli publish gemini" in deploy_src
    assert "--no-confirm-project" not in deploy_src


def test_scenario_12_live_gcp_environment_and_bigquery_contract_verification() -> None:
    """Scenario 12: Verify `.env` sovereign configuration and live BigQuery / Discovery Engine contract alignment."""
    env_vars = load_dotenv_dict(WORKSPACE_ROOT / ".env")
    assert env_vars["GOOGLE_CLOUD_PROJECT"] == "antig-dave"
    assert env_vars["GOOGLE_CLOUD_LOCATION"] == "europe-west1"
    assert env_vars["DISCOVERY_ENGINE_LOCATION"] == "eu"
    assert env_vars["VERTEX_SEARCH_DATASTORE_ID"] == "ukd-reme-aesp-ds"
    assert env_vars["BQ_DATASET"] == "ukd_reme_demo"
    assert env_vars["BQ_LOCATION"] == "europe-west1"
    assert env_vars["GOOGLE_API_USE_CLIENT_CERTIFICATE"] == "false"

    # Verify live BigQuery client can be initialized without subprocess calls
    import app.tools as tools_mod

    tools_src = (WORKSPACE_ROOT / "app" / "tools.py").read_text(encoding="utf-8")
    assert "import subprocess" not in tools_src and "subprocess." not in tools_src
    assert hasattr(tools_mod, "_BQ_CLIENT")


def test_scenario_13_issue_01_datastore_import_concurrency_guard_and_failure_validation() -> None:
    """Scenario 13 (Issue 01 Fix): Verify digitalParsingConfig patch, pre-extracted text JSONL, active LRO attachment, and code 14 failure detection."""
    import base64
    import scripts.setup_reme_datastore as ds_mod

    # 1. Verify build_documents_jsonl produces canonical PDF record + pre-extracted rawBytes text record
    lines = ds_mod.build_documents_jsonl([ds_mod.CANONICAL_PDF]).strip().splitlines()
    assert len(lines) == 2
    pdf_doc = json.loads(lines[0])
    txt_doc = json.loads(lines[1])
    assert pdf_doc["id"] == "aesp-2350-t-250-523"
    assert "79.4 mm" in json.loads(pdf_doc["jsonData"])["extracted_text"]
    assert txt_doc["id"] == "aesp-2350-t-250-523-extracted-text"
    assert txt_doc["content"]["mimeType"] == "text/plain"
    decoded_text = base64.b64decode(txt_doc["content"]["rawBytes"]).decode("utf-8")
    assert "5360-99-812-1740" in decoded_text and "54.6 mm" in decoded_text

    # 2. Verify patch_datastore_processing_config patches documentProcessingConfig -> digitalParsingConfig
    mock_patch = MagicMock()
    mock_patch.return_value.status_code = 200
    mock_patch.return_value.json.return_value = {
        "name": "projects/antig-dave/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/documentProcessingConfig",
        "defaultParsingConfig": {"digitalParsingConfig": {}},
    }
    with patch("scripts.setup_reme_datastore.requests.patch", mock_patch):
        patch_res = ds_mod.patch_datastore_processing_config(headers={"Authorization": "Bearer tok"})
        assert "digitalParsingConfig" in patch_res["defaultParsingConfig"]
        assert "/documentProcessingConfig" in mock_patch.call_args[0][0]

    # 3. Verify import_documents attaches to active LRO instead of starting a conflicting duplicate import
    active_op = {
        "name": "projects/284046449012/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/branches/0/operations/import-documents-active",
        "done": False,
    }
    completed_op = {
        "name": active_op["name"],
        "done": True,
        "metadata": {"successCount": "2", "failureCount": "0"},
    }
    with patch.object(ds_mod, "list_active_import_operations", return_value=[active_op]), patch.object(
        ds_mod, "poll_operation", return_value=completed_op
    ) as mock_poll, patch("scripts.setup_reme_datastore.requests.post") as mock_post:
        res = ds_mod.import_documents(headers={"Authorization": "Bearer tok"}, force_import=False)
        assert res["done"] is True
        mock_post.assert_not_called()
        mock_poll.assert_called_once()

    # 4. Verify validate_import_operation_result raises RuntimeError on failureCount > 0 (e.g. code 14)
    failed_op = {
        "name": "projects/284046449012/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/branches/0/operations/import-documents-3049921257174640810",
        "done": True,
        "metadata": {"failureCount": "1", "totalCount": "1"},
        "response": {
            "errorSamples": [
                {
                    "code": 14,
                    "message": "Document was previously imported but not yet indexed. Resource is temporarily exhausted.",
                }
            ]
        },
    }
    with pytest.raises(RuntimeError, match="failureCount=1"):
        ds_mod.validate_import_operation_result(failed_op)


def test_scenario_14_issue_02_agent_performance_ttft_context_cache_and_transparency() -> None:
    """Scenario 14 (Issue 02 Fix): End-to-end verification of <5ms TTFT, >4,200-token context cache padding, parallel fan-out, and ExecutionTelemetry."""
    from google.adk.models.llm_request import LlmRequest
    from google.genai import types
    import app.agent as agent_mod
    import app.tools as tools_mod
    from app.schemas import ActiveTicketState, ExecutionTelemetry

    # 1. Verify Context Caching & static prompt padding invariants
    assert len(agent_mod.SYSTEM_INSTRUCTION) >= 18000
    assert agent_mod.ESTIMATED_STATIC_PROMPT_TOKENS >= 4200
    assert agent_mod.app.context_cache_config is not None
    assert agent_mod.app.context_cache_config.min_tokens == 2048
    assert agent_mod.app.context_cache_config.ttl_seconds == 7200
    assert agent_mod.app.events_compaction_config is not None
    assert (
        agent_mod.reme_artificer_agent.generate_content_config.thinking_config.thinking_budget
        == 0
    )

    # 2. Verify Reproduction Prompt 1 ("What is your operational capability") < 5ms TTFT
    t0 = time.perf_counter()
    r1 = agent_mod.fast_path_before_model_callback(
        DummyToolContext(),
        LlmRequest(
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="What is your operational capability")],
                )
            ]
        ),
    )
    ttft_r1_ms = (time.perf_counter() - t0) * 1000.0
    assert r1 is not None
    assert ttft_r1_ms < 5.0
    assert "TIER_1_FAST_PATH_CAPABILITY" in r1.content.parts[0].text
    assert "Agent Execution Trace" in r1.content.parts[0].text

    # 3. Verify Reproduction Prompt 2 ("Summarise the contents of 2350-T-250-523.pdf") < 5ms TTFT
    t1 = time.perf_counter()
    r2 = agent_mod.fast_path_before_model_callback(
        DummyToolContext(),
        LlmRequest(
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="Summarise the contents of 2350-T-250-523.pdf"
                        )
                    ],
                )
            ]
        ),
    )
    ttft_r2_ms = (time.perf_counter() - t1) * 1000.0
    assert r2 is not None
    assert ttft_r2_ms < 5.0
    assert "TIER_2_CACHED_AESP_SUMMARY" in r2.content.parts[0].text
    assert "5360-99-812-1740" in r2.content.parts[0].text
    assert "Agent Execution Trace" in r2.content.parts[0].text

    # 4. Verify parallel ThreadPoolExecutor fan-out & ExecutionTelemetry on diagnose_and_resolve_grid
    ctx = DummyToolContext()
    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("offline")
    ):
        diag = tools_mod.diagnose_and_resolve_grid(
            "FV432 K60 low oil pressure relief valve spring",
            "Sector Bravo-4",
            ctx,
        )
    state_obj = ActiveTicketState(**diag)
    assert state_obj.execution_telemetry is not None
    assert isinstance(state_obj.execution_telemetry, ExecutionTelemetry)
    assert state_obj.execution_telemetry.routing_tier == "TIER_3_PARALLEL_HYBRID_TRIAGE"
    assert state_obj.execution_telemetry.parallel_fanout is True
    assert len(state_obj.execution_telemetry.sources_consulted) == 3


def test_scenario_15_issue_03_concise_output_and_photo_valve_pipe_assessment() -> None:
    """Scenario 15 (Issue 03 Fix): End-to-end verification of 5-line concise Scene 1 output, suppressed verbose trace, and photo valve/pipe/field-fix provisioning."""
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    import app.agent as agent_mod
    import app.tools as tools_mod
    import scripts.seed_demo1_bigquery as seed_mod
    from app.schemas import ActiveTicketState

    # 1. Verify BigQuery seed catalogue contains the new hydraulic pipe, safety valve, combined, and field-fix rows
    seed_ids = {r["part_id"] for r in seed_mod.IPC_SEED_ROWS}
    assert "JACKAL-PIPE-01" in seed_ids
    assert "JACKAL-VALVE-01" in seed_ids
    assert "JACKAL-VALVE-PIPE-01" in seed_ids
    assert "JACKAL-FIELD-FIX-01" in seed_ids

    # 2. Verify Reproduction Prompt ("FV432 K60 low oil pressure at Sector Bravo-4") produces ONLY the 5-line concise format
    ctx = DummyToolContext()
    req = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="FV432 K60 low oil pressure at Sector Bravo-4"
                    )
                ],
            )
        ]
    )
    assert agent_mod.fast_path_before_model_callback(ctx, req) is None
    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("offline")
    ):
        diag = tools_mod.diagnose_and_resolve_grid(
            "FV432 K60 low oil pressure at Sector Bravo-4",
            "Sector Bravo-4",
            ctx,
        )
    ticket_state = ActiveTicketState(**diag)
    assert ticket_state.concise_aesp_ref.startswith("Para 17.4")
    assert "Classification: L1 FRT Fix (Bench Check) / L2 Workshop" in ticket_state.formatted_concise_response
    assert "NSN: 5360-99-812-1740" in ticket_state.formatted_concise_response
    assert "Coordinates of Sector : 51.2185° N, 1.7925° W" in ticket_state.formatted_concise_response
    assert 'Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket' in ticket_state.formatted_concise_response

    # Verify transparency_after_model_callback enforces concise 5-line output without Agent Execution Trace
    resp = agent_mod.transparency_after_model_callback(
        ctx,
        LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=ticket_state.formatted_concise_response)],
            )
        ),
    )
    assert resp is not None
    final_text = resp.content.parts[0].text
    assert final_text == ticket_state.formatted_concise_response
    assert "Agent Execution Trace" not in final_text
    assert "15s Audio Brief" not in final_text

    # 3. Verify Multimodal Photo Assessment: Both Hydraulic Safety Valve AND Pipe broken
    ctx_both = DummyToolContext()
    with patch.object(tools_mod, "_BQ_CLIENT", None), patch(
        "app.tools.requests.post", side_effect=OSError("offline")
    ):
        diag_both = tools_mod.diagnose_and_resolve_grid(
            "Photo shows broken hydraulic safety valve and cracked hydraulic pipe at Sector Bravo-4",
            "Sector Bravo-4",
            ctx_both,
        )
    state_both = ActiveTicketState(**diag_both)
    assert state_both.requires_new_part is True
    assert state_both.field_fixable_by_soldier is False
    assert state_both.repair_classification == "L2 Repair (New Part Required)"
    assert state_both.nsn == "4820-99-812-4415, 4710-99-812-4420"
    assert state_both.concise_aesp_ref == "Para 4.12 & Para 4.14 (Torque 45Nm)"


def test_scenario_16_issue_04_concise_publish_and_prompt_image_in_chat_ticket(
    chat_client: TestClient,
) -> None:
    """Scenario 16 (Issue 04 Fix): End-to-end verification of concise Scene 2 publish output, GCS image upload, BigQuery CRUD, and Chat App ticket image."""
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    import app.agent as agent_mod
    import app.tools as tools_mod
    import scripts.seed_demo1_bigquery as seed_mod

    # 1. Verify BigQuery schema in seed_demo1_bigquery.py includes image_gcs_uri and image_url
    schema_names = {f.name for f in seed_mod.TICKETS_SCHEMA}
    assert "image_gcs_uri" in schema_names
    assert "image_url" in schema_names

    # 2. Scene 1: Soldier provides an image in the prompt and reports a casualty at Sector Bravo-4
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    ctx = DummyToolContext()
    sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    req_scene1 = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=sample_png, mime_type="image/png"),
                    types.Part.from_text(
                        text="FV432 K60 low oil pressure at Sector Bravo-4"
                    ),
                ],
            )
        ]
    )

    with patch.object(tools_mod, "_STORAGE_CLIENT", mock_storage), patch.object(
        tools_mod, "_BQ_CLIENT", None
    ), patch("app.tools.requests.post", side_effect=OSError("offline")):
        assert agent_mod.fast_path_before_model_callback(ctx, req_scene1) is None
        diag = tools_mod.diagnose_and_resolve_grid(
            "FV432 K60 low oil pressure at Sector Bravo-4",
            "Sector Bravo-4",
            ctx,
        )

    assert diag["image_gcs_uri"].startswith("gs://antig-dave-reme-ticket-images-eu/tickets/")
    assert diag["image_url"].startswith("/api/ticket-image/tickets/")

    # 3. Scene 2: Soldier prompts 'Publish to Group Chat" to broadcast this recovery ticket'
    req_scene2 = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text='Publish to Group Chat" to broadcast this recovery ticket'
                    )
                ],
            )
        ]
    )
    assert agent_mod.fast_path_before_model_callback(ctx, req_scene2) is None
    assert ctx.state.get("_enforce_concise_publish") is True

    def _forward_to_test_client(url: str, json: dict, timeout: float = 5.0):
        return chat_client.post("/api/tickets", json=json)

    mock_agent_bq = MagicMock()
    mock_agent_bq.insert_rows_json.return_value = []

    with patch.object(tools_mod, "_BQ_CLIENT", mock_agent_bq), patch(
        "app.tools.requests.post", side_effect=_forward_to_test_client
    ):
        pub_result = tools_mod.publish_ticket_to_chat(ctx)

    expected_concise_publish = (
        "Callsign: Cpl MacDonald (4 Bn REME FRT)\n"
        "Vehicle Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)\n"
        "Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)\n"
        "Demand Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740\n\n"
        'Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket'
    )
    assert pub_result["formatted_publish_response"] == expected_concise_publish

    # 4. Verify transparency_after_model_callback enforces the exact concise Scene 2 response
    final_scene2_resp = agent_mod.transparency_after_model_callback(
        ctx,
        LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text=(
                            "Callsign: Cpl MacDonald (4 Bn REME FRT)\n"
                            "Casualty Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)\n"
                            "Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)\n"
                            "Demand Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740\n"
                            "Tactical Navigation: Open Universal Google Maps Route (51.2185, -1.7925)\n"
                            "Routing Tier: TIER_3_PARALLEL_HYBRID_TRIAGE\n"
                        )
                    )
                ],
            )
        ),
    )
    assert final_scene2_resp is not None
    assert final_scene2_resp.content.parts[0].text == expected_concise_publish

    # 5. Verify the Chat Application received the ticket with image_url and serves the image
    tickets = chat_client.get("/api/tickets").json()["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["image_gcs_uri"] == diag["image_gcs_uri"]
    assert tickets[0]["image_url"] == diag["image_url"]

    img_resp = chat_client.get(tickets[0]["image_url"])
    assert img_resp.status_code == 200
    assert img_resp.content == sample_png



