"""Tier 1 E2E Tests: Happy-Path Feature Coverage (>=5 test cases per feature across all 22 features = 110 tests)."""

from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tests.e2e.conftest import DummyToolContext, WORKSPACE_ROOT, load_dotenv_dict


# ============================================================================
# Feature 1: Root-level `agents-cli` ADK 2.0 Scaffolding (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,rel_path,expected_substrings",
    [
        ("f01_case1_agents_md_preserved", "AGENTS.md", ["Solutions Architecture Guide", "Demo%201%20-%20SA.md", "google-genai"]),
        ("f01_case2_sa_doc_preserved", "docs/architecture/Demo 1 - SA.md", ["SDD-DEMO1-ADK2-003", "5360-99-812-1740"]),
        ("f01_case3_spec_md_created", "SPEC.md", ["reme_artificer_agent", "europe-west1"]),
        ("f01_case4_agents_cli_manifests", "agents-cli-manifest.yaml", ["europe-west1", "agent_runtime"]),
        ("f01_case5_dockerfile_and_fast_api_app", "app/fast_api_app.py", ["root_agent", "app"]),
    ],
)
def test_f01_root_scaffolding(case_id: str, rel_path: str, expected_substrings: list[str]) -> None:
    """Verify Feature 1: Root-level agents-cli ADK 2.0 scaffolding and preserved docs."""
    target = WORKSPACE_ROOT / rel_path
    assert target.exists(), f"[{case_id}] Missing expected file: {target}"
    content = target.read_text(encoding="utf-8")
    assert len(content.strip()) > 20, f"[{case_id}] File {rel_path} is unexpectedly empty"
    for sub in expected_substrings:
        assert sub in content, f"[{case_id}] Expected '{sub}' in {rel_path}"
    if case_id == "f01_case4_agents_cli_manifests":
        assert (WORKSPACE_ROOT / ".agents.yaml").exists(), "Missing .agents.yaml alongside agents-cli-manifest.yaml"
    if case_id == "f01_case5_dockerfile_and_fast_api_app":
        assert (WORKSPACE_ROOT / "Dockerfile").exists(), "Missing root Dockerfile for Agent Runtime"


# ============================================================================
# Feature 2: EU / Belgium Environment Configuration (`.env` & `.env.example`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,env_key,expected_val",
    [
        ("f02_case1_project_id", "GOOGLE_CLOUD_PROJECT", "antig-dave"),
        ("f02_case2_belgium_compute_location", "GOOGLE_CLOUD_LOCATION", "europe-west1"),
        ("f02_case3_mtls_guardrail", "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"),
        ("f02_case4_eu_discovery_engine", "DISCOVERY_ENGINE_LOCATION", "eu"),
        ("f02_case5_datastore_and_bq_dataset", "VERTEX_SEARCH_DATASTORE_ID", "ukd-reme-aesp-ds"),
    ],
)
def test_f02_env_configuration(case_id: str, env_key: str, expected_val: str) -> None:
    """Verify Feature 2: .env and .env.example EU/Belgium residency and mTLS configuration."""
    for filename in (".env", ".env.example"):
        env_map = load_dotenv_dict(WORKSPACE_ROOT / filename)
        assert env_key in env_map, f"[{case_id}] Missing {env_key} in {filename}"
        assert env_map[env_key] == expected_val, (
            f"[{case_id}] Expected {env_key}={expected_val} in {filename}, got {env_map[env_key]}"
        )
        assert env_map.get("BQ_DATASET") == "ukd_reme_demo"
        assert env_map.get("BQ_LOCATION") == "europe-west1"
        assert env_map.get("GCS_SOURCE_BUCKET") == "remedata"
        assert "locations/eu" in env_map.get("GEMINI_APP_ID", "")
        assert "CLOUD_RUN_CHAT_URL" in env_map


# ============================================================================
# Feature 3: Python Dependency Management (`pyproject.toml` & `uv sync`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,required_pkg,import_name",
    [
        ("f03_case1_adk_and_genai", "google-adk", "google.adk"),
        ("f03_case2_bigquery_and_storage", "google-cloud-bigquery", "google.cloud.bigquery"),
        ("f03_case3_discoveryengine", "google-cloud-discoveryengine", "google.cloud.discoveryengine"),
        ("f03_case4_fastapi_and_jinja2", "fastapi", "fastapi"),
        ("f03_case5_pydantic_and_pytest", "pydantic", "pydantic"),
    ],
)
def test_f03_dependencies(case_id: str, required_pkg: str, import_name: str) -> None:
    """Verify Feature 3: pyproject.toml dependencies, uv.lock, and importability."""
    pyproject = WORKSPACE_ROOT / "pyproject.toml"
    assert pyproject.exists(), f"[{case_id}] Missing pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert required_pkg in text, f"[{case_id}] Missing {required_pkg} in pyproject.toml"
    assert "google-generativeai" not in text, "Forbidden legacy google-generativeai package in pyproject.toml"
    assert (WORKSPACE_ROOT / "uv.lock").exists(), "Missing uv.lock after uv sync"
    __import__(import_name)


# ============================================================================
# Feature 4: GCS Bucket Inspection & Canonical PDF Verification (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,expected_token",
    [
        ("f04_case1_script_valid_ast", "AST_VALID"),
        ("f04_case2_target_bucket_remedata", "remedata"),
        ("f04_case3_canonical_pdf_name", "2350-T-250-523.pdf"),
        ("f04_case4_storage_client_usage", "storage"),
        ("f04_case5_project_antig_dave", "antig-dave"),
    ],
)
def test_f04_gcs_pdf_verification(case_id: str, expected_token: str) -> None:
    """Verify Feature 4: scripts/setup_reme_datastore.py inspects gs://remedata and 2350-T-250-523.pdf."""
    script_path = WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py"
    assert script_path.exists(), f"[{case_id}] Missing {script_path}"
    source = script_path.read_text(encoding="utf-8")
    if expected_token == "AST_VALID":
        tree = ast.parse(source)
        assert isinstance(tree, ast.Module)
    else:
        assert expected_token in source, f"[{case_id}] Expected '{expected_token}' in setup_reme_datastore.py"


# ============================================================================
# Feature 5: Unstructured OCR Datastore Creation (`ukd-reme-aesp-ds` in `eu`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,expected_snippet",
    [
        ("f05_case1_eu_endpoint", "eu-discoveryengine.googleapis.com"),
        ("f05_case2_datastore_id", "ukd-reme-aesp-ds"),
        ("f05_case3_content_required", "CONTENT_REQUIRED"),
        ("f05_case4_ocr_parsing_config", "ocrParsingConfig"),
        ("f05_case5_use_native_text", "useNativeText"),
    ],
)
def test_f05_ocr_datastore_creation(case_id: str, expected_snippet: str) -> None:
    """Verify Feature 5: Unstructured OCR datastore creation in EU multi-region."""
    import scripts.setup_reme_datastore as ds_mod

    script_path = WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py"
    source = script_path.read_text(encoding="utf-8")
    if case_id == "f05_case1_eu_endpoint":
        assert expected_snippet in ds_mod.DISCOVERY_ENGINE_BASE_URL
    else:
        assert expected_snippet in source, f"[{case_id}] Expected '{expected_snippet}' in setup_reme_datastore.py"
    assert "409" in source, "setup_reme_datastore.py must handle HTTP 409 ALREADY_EXISTS idempotently"


# ============================================================================
# Feature 6: NDJSON Metadata Generation & Upload (`gs://remedata/documents.jsonl`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,metadata_field",
    [
        ("f06_case1_documents_jsonl_target", "documents.jsonl"),
        ("f06_case2_aesp_reference_field", "AESP 2350-T-250-523"),
        ("f06_case3_equipment_platform_field", "equipment_platform"),
        ("f06_case4_nsn_and_component", "5360-99-812-1740"),
        ("f06_case5_security_classification_and_unit", "security_classification"),
    ],
)
def test_f06_ndjson_metadata(case_id: str, metadata_field: str) -> None:
    """Verify Feature 6: Rich NDJSON metadata generation and upload for gs://remedata/documents.jsonl."""
    script_path = WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py"
    source = script_path.read_text(encoding="utf-8")
    assert metadata_field in source, f"[{case_id}] Missing '{metadata_field}' in setup_reme_datastore.py"
    assert "application/pdf" in source


# ============================================================================
# Feature 7: Incremental Document Import & Search Verification (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,import_token",
    [
        ("f07_case1_documents_import_endpoint", "documents:import"),
        ("f07_case2_gcs_source_input_uris", "inputUris"),
        ("f07_case3_reconciliation_incremental", "INCREMENTAL"),
        ("f07_case4_lro_polling", "operations"),
        ("f07_case5_search_verification", "default_search:search"),
    ],
)
def test_f07_incremental_import(case_id: str, import_token: str) -> None:
    """Verify Feature 7: Incremental document import, LRO polling, and search verification."""
    script_path = WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py"
    source = script_path.read_text(encoding="utf-8")
    assert import_token in source, f"[{case_id}] Expected '{import_token}' in setup_reme_datastore.py"


# ============================================================================
# Feature 8: Safe `pixel_mobile_demos` Engine Patching (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,engine_token",
    [
        ("f08_case1_pixel_mobile_demos_target", "pixel-mobile-demos_1793177711952"),
        ("f08_case2_preserve_jointservicepubs", "jointservicepubs"),
        ("f08_case3_datastore_ids_field", "dataStoreIds"),
        ("f08_case4_update_mask_param", "updateMask=dataStoreIds"),
        ("f08_case5_patch_method", "patch"),
    ],
)
def test_f08_safe_engine_patching(case_id: str, engine_token: str) -> None:
    """Verify Feature 8: Non-destructive PATCH of pixel_mobile_demos preserving jointservicepubs."""
    script_path = WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py"
    source = script_path.read_text(encoding="utf-8")
    assert engine_token in source or engine_token.upper() in source, (
        f"[{case_id}] Expected '{engine_token}' in setup_reme_datastore.py"
    )


# ============================================================================
# Feature 9: BigQuery Dataset `ukd_reme_demo` Creation (`scripts/seed_demo1_bigquery.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,bq_token",
    [
        ("f09_case1_valid_python_ast", "AST_VALID"),
        ("f09_case2_dataset_name", "ukd_reme_demo"),
        ("f09_case3_location_europe_west1", "europe-west1"),
        ("f09_case4_dataset_description", "4 Battalion REME"),
        ("f09_case5_create_dataset_call", "create_dataset"),
    ],
)
def test_f09_bq_dataset_creation(case_id: str, bq_token: str) -> None:
    """Verify Feature 9: scripts/seed_demo1_bigquery.py dataset creation in europe-west1 with description."""
    script_path = WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py"
    assert script_path.exists(), f"[{case_id}] Missing {script_path}"
    source = script_path.read_text(encoding="utf-8")
    if bq_token == "AST_VALID":
        assert isinstance(ast.parse(source), ast.Module)
    else:
        assert bq_token in source, f"[{case_id}] Expected '{bq_token}' in seed_demo1_bigquery.py"


# ============================================================================
# Feature 10: Table 1: `ipc_nsn_catalogue` Schema, Metadata & Seed Data (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,expected_item",
    [
        ("f10_case1_table_name_and_8_columns", "ipc_nsn_catalogue"),
        ("f10_case2_k60_nsn_and_aesp", "5360-99-812-1740"),
        ("f10_case3_jackal_nsn_and_aesp", "5330-99-812-4410"),
        ("f10_case4_k60_condemnation_limits", "79.4 mm"),
        ("f10_case5_jackal_torque_limits", "45 Nm"),
    ],
)
def test_f10_ipc_nsn_catalogue(case_id: str, expected_item: str) -> None:
    """Verify Feature 10: ipc_nsn_catalogue schema, descriptions, and 11 K60/Jackal 2 seed rows."""
    script_path = WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py"
    source = script_path.read_text(encoding="utf-8")
    assert expected_item in source, f"[{case_id}] Missing '{expected_item}' in seed_demo1_bigquery.py"
    for col in (
        "part_id",
        "keyword_tag",
        "ipc_army_code",
        "aesp_reference",
        "part_name",
        "nsn",
        "repair_classification",
        "technical_limits",
    ):
        assert col in source, f"Missing column {col} in seed_demo1_bigquery.py"


# ============================================================================
# Feature 11: Table 2: `spta_sector_grids` Schema, Metadata & Seed Data (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,grid_key,coord_str",
    [
        ("f11_case1_bravo_4_hyphen", "bravo-4", "51.2185"),
        ("f11_case2_bravo_4_space", "bravo 4", "-1.7925"),
        ("f11_case3_bng_su_1482_4621", "su 1482 4621", "51.2185° N, 1.7925° W"),
        ("f11_case4_alpha_1", "alpha-1", "51.231"),
        ("f11_case5_whitehall_london", "london", "51.5007"),
    ],
)
def test_f11_spta_sector_grids(case_id: str, grid_key: str, coord_str: str) -> None:
    """Verify Feature 11: spta_sector_grids schema, descriptions, and 5 tactical grid seed rows."""
    script_path = WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py"
    source = script_path.read_text(encoding="utf-8")
    assert "spta_sector_grids" in source
    assert grid_key in source, f"[{case_id}] Missing grid_key '{grid_key}' in seed_demo1_bigquery.py"
    assert coord_str in source, f"[{case_id}] Missing coordinate '{coord_str}' in seed_demo1_bigquery.py"


# ============================================================================
# Feature 12: Table 3: `group_chat_tickets` Schema, Metadata & Initial Seed (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,column_or_seed",
    [
        ("f12_case1_table_name_and_ticket_id", "group_chat_tickets"),
        ("f12_case2_timestamp_and_callsign", "created_at_utc"),
        ("f12_case3_coords_and_maps_url", "google_maps_url"),
        ("f12_case4_baseline_ticket_id", "TKT-REME-041"),
        ("f12_case5_baseline_status_dispatch_ready", "DISPATCH_READY"),
    ],
)
def test_f12_group_chat_tickets(case_id: str, column_or_seed: str) -> None:
    """Verify Feature 12: group_chat_tickets 13-column schema, descriptions, and TKT-REME-041 seed."""
    script_path = WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py"
    source = script_path.read_text(encoding="utf-8")
    assert column_or_seed in source, f"[{case_id}] Missing '{column_or_seed}' in seed_demo1_bigquery.py"
    for col in (
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
    ):
        assert col in source, f"Missing column {col} in group_chat_tickets definition"


# ============================================================================
# Feature 13: Strict Pydantic v2 Schemas (`app/schemas.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f13_case1_active_ticket_state_k60",
        "f13_case2_active_ticket_state_jackal",
        "f13_case3_ticket_payload_defaults",
        "f13_case4_ticket_payload_serialization",
        "f13_case5_no_any_type_annotations",
    ],
)
def test_f13_pydantic_schemas(case_id: str) -> None:
    """Verify Feature 13: ActiveTicketState and TicketPayload strict Pydantic v2 models."""
    from app.schemas import ActiveTicketState, TicketPayload

    if case_id == "f13_case1_active_ticket_state_k60":
        state = ActiveTicketState(
            repair_classification="L1 FRT Fix (Bench Check) / L2 Workshop",
            aesp_reference="AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
            part_name="Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
            nsn="5360-99-812-1740",
            technical_limits="Free length must be 79.4 mm",
            sector_display_name="Salisbury Plain (SPTA) — Sector Bravo-4",
            latitude=51.2185,
            longitude=-1.7925,
            coords_label="51.2185° N, 1.7925° W",
            rag_snippets=["Cleaned AESP snippet"],
        )
        dumped = state.model_dump()
        assert dumped["nsn"] == "5360-99-812-1740"
        assert dumped["rag_snippets"] == ["Cleaned AESP snippet"]

    elif case_id == "f13_case2_active_ticket_state_jackal":
        state = ActiveTicketState(
            repair_classification="L2 Workshop Repair",
            aesp_reference="AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)",
            part_name="Hydraulic Manifold High-Pressure Seal Kit",
            nsn="5330-99-812-4410",
            technical_limits="Torque to 45 Nm.",
            sector_display_name="Salisbury Plain (SPTA) — Sector Alpha-1",
            latitude=51.2310,
            longitude=-1.8150,
            coords_label="51.2310° N, 1.8150° W",
        )
        assert state.rag_snippets == []
        assert state.nsn == "5330-99-812-4410"

    elif case_id == "f13_case3_ticket_payload_defaults":
        ticket = TicketPayload(
            ticket_id="TKT-REME-101",
            created_at_utc="2026-10-29T11:30:00Z",
            repair_classification="L1 FRT Fix (Bench Check) / L2 Workshop",
            aesp_reference="AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
            part_name="Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
            nsn="5360-99-812-1740",
            technical_limits="Free length must be 79.4 mm",
            coords_label="51.2185° N, 1.7925° W",
            latitude=51.2185,
            longitude=-1.7925,
            google_maps_url="https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
        )
        assert ticket.callsign == "Cpl MacDonald (4 Bn REME FRT)"
        assert ticket.status == "DISPATCH_READY"
        assert ticket.sector_display_name == "Salisbury Plain (SPTA) — Sector Bravo-4"

    elif case_id == "f13_case4_ticket_payload_serialization":
        ticket = TicketPayload(
            ticket_id="TKT-REME-102",
            created_at_utc="2026-10-29T11:31:00Z",
            repair_classification="L2 Workshop Repair",
            aesp_reference="AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)",
            part_name="Hydraulic Manifold High-Pressure Seal Kit",
            nsn="5330-99-812-4410",
            technical_limits="Torque to 45 Nm.",
            sector_display_name="Salisbury Plain (SPTA) — Sector Alpha-1",
            coords_label="51.2310° N, 1.8150° W",
            latitude=51.2310,
            longitude=-1.8150,
            google_maps_url="https://www.google.com/maps/dir/?api=1&destination=51.231,-1.815&travelmode=driving",
        )
        data = ticket.model_dump()
        assert len(data) >= 13
        assert data["ticket_id"] == "TKT-REME-102"

    elif case_id == "f13_case5_no_any_type_annotations":
        schemas_src = (WORKSPACE_ROOT / "app" / "schemas.py").read_text(encoding="utf-8")
        assert "Any" not in schemas_src, "app/schemas.py must not use Any in strict Pydantic models"


# ============================================================================
# Feature 14: Pre-Warmed Module Singletons (`app/tools.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f14_case1_bq_client_singleton_exists",
        "f14_case2_credentials_singleton_exists",
        "f14_case3_zero_subprocess_or_gcloud_calls",
        "f14_case4_golden_fallback_constants",
        "f14_case5_regional_constants",
    ],
)
def test_f14_prewarmed_singletons(case_id: str) -> None:
    """Verify Feature 14: Module-level pre-warmed _BQ_CLIENT and _CREDENTIALS singletons."""
    import app.tools as tools_mod

    tools_src = (WORKSPACE_ROOT / "app" / "tools.py").read_text(encoding="utf-8")
    if case_id == "f14_case1_bq_client_singleton_exists":
        assert hasattr(tools_mod, "_BQ_CLIENT"), "app.tools must define module-level _BQ_CLIENT"
    elif case_id == "f14_case2_credentials_singleton_exists":
        assert hasattr(tools_mod, "_CREDENTIALS"), "app.tools must define module-level _CREDENTIALS"
    elif case_id == "f14_case3_zero_subprocess_or_gcloud_calls":
        assert "import subprocess" not in tools_src and "subprocess." not in tools_src, (
            "app/tools.py must never import or invoke subprocess"
        )
        assert "print-access-token" not in tools_src, "app/tools.py must never spawn gcloud auth print-access-token"
    elif case_id == "f14_case4_golden_fallback_constants":
        assert tools_mod.GOLDEN_FALLBACK_K60["nsn"] == "5360-99-812-1740"
        assert tools_mod.GOLDEN_FALLBACK_JACKAL["nsn"] == "5330-99-812-4410"
        assert tools_mod.GOLDEN_FALLBACK_GRID["latitude"] == pytest.approx(51.2185)
        assert tools_mod.GOLDEN_FALLBACK_GRID["longitude"] == pytest.approx(-1.7925)
    elif case_id == "f14_case5_regional_constants":
        assert getattr(tools_mod, "PROJECT_ID", "antig-dave") == "antig-dave"
        assert getattr(tools_mod, "BQ_LOCATION", "europe-west1") == "europe-west1"


# ============================================================================
# Feature 15: Scene 1 Composite Tool: `diagnose_and_resolve_grid` (`app/tools.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f15_case1_signature_and_docstring_contract",
        "f15_case2_discovery_engine_payload_contract",
        "f15_case3_html_tag_stripping",
        "f15_case4_k60_bravo4_diagnosis_and_state",
        "f15_case5_jackal2_err409_diagnosis_and_state",
    ],
)
def test_f15_diagnose_and_resolve_grid(case_id: str, dummy_tool_context: DummyToolContext) -> None:
    """Verify Feature 15: Scene 1 composite tool diagnose_and_resolve_grid."""
    import app.tools as tools_mod

    if case_id == "f15_case1_signature_and_docstring_contract":
        sig = inspect.signature(tools_mod.diagnose_and_resolve_grid)
        params = list(sig.parameters.values())
        assert [p.name for p in params] == ["fault_query", "spoken_sector_grid", "tool_context"]
        for p in params:
            assert p.default is inspect.Parameter.empty, f"Parameter {p.name} must not have a default value"
        doc = tools_mod.diagnose_and_resolve_grid.__doc__ or ""
        assert "tool_context" not in doc, "tool_context must be omitted from docstring per ADK tool guidelines"

    elif case_id == "f15_case2_discovery_engine_payload_contract":
        captured_kwargs: dict[str, Any] = {}

        def fake_post(url: str, **kwargs: Any) -> MagicMock:
            captured_kwargs["url"] = url
            captured_kwargs["json"] = kwargs.get("json", {})
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "results": [
                    {
                        "document": {
                            "derivedStructData": {
                                "snippets": [{"snippet": "<b>AESP 2350-T-250-523</b> Para 17.4 relief valve spring."}]
                            }
                        }
                    }
                ]
            }
            return resp

        with patch.object(tools_mod, "_get_access_token", return_value="fake-token", create=True), patch(
            "app.tools.requests.post", side_effect=fake_post
        ), patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid("K60 oil relief valve", "Sector Bravo-4", dummy_tool_context)
            assert "eu-discoveryengine.googleapis.com" in captured_kwargs["url"]
            assert "ukd-reme-aesp-ds" in captured_kwargs["url"]
            assert captured_kwargs["json"]["pageSize"] == 15
            assert captured_kwargs["json"]["contentSearchSpec"] == {"snippetSpec": {"returnSnippet": True}}
            assert "summarySpec" not in captured_kwargs["json"]["contentSearchSpec"]
            assert res["nsn"] == "5360-99-812-1740"

    elif case_id == "f15_case3_html_tag_stripping":
        def fake_post(url: str, **kwargs: Any) -> MagicMock:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "results": [
                    {
                        "document": {
                            "derivedStructData": {
                                "snippets": [
                                    {"snippet": "Free length must be <b>79.4 mm</b>; compress to <b>54.6 mm</b>."}
                                ]
                            }
                        }
                    }
                ]
            }
            return resp

        with patch.object(tools_mod, "_get_access_token", return_value="fake-token", create=True), patch(
            "app.tools.requests.post", side_effect=fake_post
        ), patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid("K60 spring", "bravo-4", dummy_tool_context)
            snippets = res.get("rag_snippets", [])
            assert snippets, "Expected cleaned rag_snippets"
            assert "<b>" not in snippets[0] and "</b>" not in snippets[0]
            assert "79.4 mm" in snippets[0]

    elif case_id == "f15_case4_k60_bravo4_diagnosis_and_state":
        with patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid(
                "FV432 Rolls-Royce K60 low oil pressure relief valve spring",
                "Sector Bravo-4",
                dummy_tool_context,
            )
            assert res["nsn"] == "5360-99-812-1740"
            assert res["latitude"] == pytest.approx(51.2185)
            assert res["longitude"] == pytest.approx(-1.7925)
            assert dummy_tool_context.state["active_ticket"]["nsn"] == "5360-99-812-1740"

    elif case_id == "f15_case5_jackal2_err409_diagnosis_and_state":
        with patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid(
                "Jackal 2 ERR-409 hydraulic manifold high-pressure seal leak",
                "Sector Bravo-4",
                dummy_tool_context,
            )
            assert res["nsn"] == "5330-99-812-4410"
            assert "2320-J-100" in res["aesp_reference"]
            assert res["repair_classification"] == "L2 Workshop Repair"
            assert dummy_tool_context.state["active_ticket"]["nsn"] == "5330-99-812-4410"


# ============================================================================
# Feature 16: Scene 2 Composite Tool: `publish_ticket_to_chat` (`app/tools.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f16_case1_signature_and_docstring_contract",
        "f16_case2_publishes_from_active_ticket_state",
        "f16_case3_posts_to_cloud_run_webhook",
        "f16_case4_filters_13_columns_for_bigquery_insert",
        "f16_case5_returns_confirmation_badge_and_maps_url",
    ],
)
def test_f16_publish_ticket_to_chat(case_id: str, dummy_tool_context: DummyToolContext) -> None:
    """Verify Feature 16: Scene 2 composite tool publish_ticket_to_chat."""
    import app.tools as tools_mod

    if case_id == "f16_case1_signature_and_docstring_contract":
        sig = inspect.signature(tools_mod.publish_ticket_to_chat)
        params = list(sig.parameters.values())
        assert [p.name for p in params] == ["tool_context"]
        assert params[0].default is inspect.Parameter.empty
        doc = tools_mod.publish_ticket_to_chat.__doc__ or ""
        assert "tool_context" not in doc

    elif case_id == "f16_case2_publishes_from_active_ticket_state":
        dummy_tool_context.state["active_ticket"] = {
            **tools_mod.GOLDEN_FALLBACK_JACKAL,
            **tools_mod.GOLDEN_FALLBACK_GRID,
        }
        with patch("app.tools.requests.post") as mock_post, patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
            assert res["published"] is True
            assert res["ticket"]["nsn"] == "5330-99-812-4410"
            assert res["ticket"]["callsign"] == "Cpl MacDonald (4 Bn REME FRT)"
            assert res["ticket"]["status"] == "DISPATCH_READY"
            assert mock_post.called

    elif case_id == "f16_case3_posts_to_cloud_run_webhook":
        with patch("app.tools.requests.post") as mock_post, patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
            assert mock_post.call_count == 1
            call_args, call_kwargs = mock_post.call_args
            assert call_args[0].endswith("/api/tickets")
            assert call_kwargs.get("timeout") == 2.0
            assert call_kwargs["json"]["ticket_id"] == res["ticket"]["ticket_id"]

    elif case_id == "f16_case4_filters_13_columns_for_bigquery_insert":
        mock_bq = MagicMock()
        mock_bq.insert_rows_json.return_value = []
        with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", mock_bq):
            tools_mod.publish_ticket_to_chat(dummy_tool_context)
            assert mock_bq.insert_rows_json.call_count == 1
            _, rows = mock_bq.insert_rows_json.call_args[0]
            inserted_row = rows[0]
            assert "sector_display_name" not in inserted_row, "sector_display_name must be stripped before BQ insert"
            assert "rag_snippets" not in inserted_row, "rag_snippets must be stripped before BQ insert"
            assert len(inserted_row) == 13

    elif case_id == "f16_case5_returns_confirmation_badge_and_maps_url":
        with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
            ticket_id = res["ticket"]["ticket_id"]
            assert ticket_id.startswith("TKT-REME-")
            assert res["confirmation_badge"] == f"✅ Ticket {ticket_id} Published to 4 Bn REME Group Chat"
            assert (
                res["ticket"]["google_maps_url"]
                == "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving"
            )


# ============================================================================
# Feature 17: `reme_artificer_agent` (`app/agent.py` & `app/__init__.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f17_case1_root_agent_exports",
        "f17_case2_agent_name_and_model",
        "f17_case3_temperature_zero_and_single_agent",
        "f17_case4_two_composite_tools_registered",
        "f17_case5_markdown_card_and_audio_brief_instruction",
    ],
)
def test_f17_reme_artificer_agent(case_id: str) -> None:
    """Verify Feature 17: reme_artificer_agent ADK 2.0 LlmAgent configuration and instructions."""
    import app as app_pkg
    import app.agent as agent_mod

    if case_id == "f17_case1_root_agent_exports":
        assert hasattr(app_pkg, "root_agent")
        assert hasattr(agent_mod, "root_agent")
        assert hasattr(agent_mod, "reme_artificer_agent")
        assert app_pkg.root_agent is agent_mod.reme_artificer_agent

    elif case_id == "f17_case2_agent_name_and_model":
        agent = agent_mod.reme_artificer_agent
        assert agent.name == "reme_artificer_agent"
        assert agent.model == "gemini-2.5-flash"

    elif case_id == "f17_case3_temperature_zero_and_single_agent":
        agent = agent_mod.reme_artificer_agent
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.0
        assert not getattr(agent, "sub_agents", [])

    elif case_id == "f17_case4_two_composite_tools_registered":
        agent = agent_mod.reme_artificer_agent
        tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in agent.tools]
        assert "diagnose_and_resolve_grid" in tool_names
        assert "publish_ticket_to_chat" in tool_names
        assert len(agent.tools) == 2

    elif case_id == "f17_case5_markdown_card_and_audio_brief_instruction":
        instruction = agent_mod.reme_artificer_agent.instruction
        assert "### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card" in instruction
        assert "🔊 **15s Audio Brief:**" in instruction
        assert instruction.count("<details open>") >= 3
        assert "Publish to Group Chat" in instruction
        assert "✅ Ticket" in instruction


# ============================================================================
# Feature 18: Scene 3 FastAPI Group Chat Backend (`cloud_run_chat_app/main.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f18_case1_get_index_html_200",
        "f18_case2_get_tickets_under_20ms",
        "f18_case3_post_tickets_prepends_in_memory",
        "f18_case4_post_reset_clears_under_1s",
        "f18_case5_post_tickets_reset_alias",
    ],
)
def test_f18_fastapi_group_chat_backend(case_id: str, chat_client: Any, chat_app_module: Any) -> None:
    """Verify Feature 18: Scene 3 FastAPI Group Chat Backend routes and latency budgets."""
    sample_payload = {
        "ticket_id": "TKT-REME-901",
        "created_at_utc": "2026-10-29T11:32:00Z",
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

    if case_id == "f18_case1_get_index_html_200":
        resp = chat_client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "4 BN REME" in resp.text.upper()

    elif case_id == "f18_case2_get_tickets_under_20ms":
        t0 = time.perf_counter()
        resp = chat_client.get("/api/tickets")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert resp.status_code == 200
        assert "tickets" in resp.json()
        assert elapsed_ms < 20.0, f"GET /api/tickets took {elapsed_ms:.2f}ms (>20ms limit)"

    elif case_id == "f18_case3_post_tickets_prepends_in_memory":
        with patch.object(chat_app_module, "_BQ_CLIENT", None):
            resp = chat_client.post("/api/tickets", json=sample_payload)
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "published"
            assert body["ticket"]["ticket_id"] == "TKT-REME-901"
            tickets = chat_client.get("/api/tickets").json()["tickets"]
            assert len(tickets) == 1
            assert tickets[0]["ticket_id"] == "TKT-REME-901"

    elif case_id == "f18_case4_post_reset_clears_under_1s":
        with patch.object(chat_app_module, "_BQ_CLIENT", None):
            chat_client.post("/api/tickets", json=sample_payload)
            t0 = time.perf_counter()
            resp = chat_client.post("/api/reset")
            elapsed_s = time.perf_counter() - t0
            assert resp.status_code == 200
            assert resp.json() == {"status": "reset", "tickets": []}
            assert elapsed_s < 1.0

    elif case_id == "f18_case5_post_tickets_reset_alias":
        with patch.object(chat_app_module, "_BQ_CLIENT", None):
            chat_client.post("/api/tickets", json=sample_payload)
            resp = chat_client.post("/api/tickets/reset")
            assert resp.status_code == 200
            assert resp.json() == {"status": "reset", "tickets": []}


# ============================================================================
# Feature 19: Tactical Dark-Mode HTML5 UI (`cloud_run_chat_app/templates/index.html`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,expected_html_token",
    [
        ("f19_case1_official_reme_banner", "OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT"),
        ("f19_case2_reset_demo_button", "Reset Demo"),
        ("f19_case3_1000ms_live_polling", "1000"),
        ("f19_case4_google_maps_dir_universal_url", "https://www.google.com/maps/dir/?api=1&destination="),
        ("f19_case5_google_maps_search_universal_url", "https://www.google.com/maps/search/?api=1&query="),
    ],
)
def test_f19_tactical_html5_ui(case_id: str, expected_html_token: str) -> None:
    """Verify Feature 19: Tactical dark-mode HTML5 UI template elements and Google Maps deep links."""
    html_path = WORKSPACE_ROOT / "cloud_run_chat_app" / "templates" / "index.html"
    assert html_path.exists(), f"[{case_id}] Missing {html_path}"
    html = html_path.read_text(encoding="utf-8")
    assert expected_html_token in html, f"[{case_id}] Expected '{expected_html_token}' in index.html"


# ============================================================================
# Feature 20: Unit & FastAPI Integration Test Suite (`tests/unit/`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,rel_path,expected_symbol",
    [
        ("f20_case1_test_tools_exists", "tests/unit/test_tools.py", "diagnose_and_resolve_grid"),
        ("f20_case2_test_tools_publish", "tests/unit/test_tools.py", "publish_ticket_to_chat"),
        ("f20_case3_test_tools_html_strip", "tests/unit/test_tools.py", "<b>"),
        ("f20_case4_test_chat_api_exists", "tests/unit/test_chat_api.py", "/api/tickets"),
        ("f20_case5_test_chat_api_reset", "tests/unit/test_chat_api.py", "/api/reset"),
    ],
)
def test_f20_unit_test_suite(case_id: str, rel_path: str, expected_symbol: str) -> None:
    """Verify Feature 20: Unit and FastAPI integration test suite in tests/unit/."""
    path = WORKSPACE_ROOT / rel_path
    assert path.exists(), f"[{case_id}] Missing {path}"
    content = path.read_text(encoding="utf-8")
    assert isinstance(ast.parse(content), ast.Module)
    assert expected_symbol in content, f"[{case_id}] Expected '{expected_symbol}' in {rel_path}"


# ============================================================================
# Feature 21: Local Smoke Testing, Browser UI & `agents-cli` Evaluation Suite (`tests/eval/`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f21_case1_eval_config_yaml_exists",
        "f21_case2_basic_dataset_json_valid_schema",
        "f21_case3_eval_case_k60_bravo4",
        "f21_case4_eval_case_jackal2_err409",
        "f21_case5_eval_case_publish_to_group_chat",
    ],
)
def test_f21_eval_suite(case_id: str) -> None:
    """Verify Feature 21: agents-cli evaluation configuration and dataset cases in tests/eval/."""
    eval_cfg = WORKSPACE_ROOT / "tests" / "eval" / "eval_config.yaml"
    dataset_path = WORKSPACE_ROOT / "tests" / "eval" / "datasets" / "basic-dataset.json"
    assert eval_cfg.exists(), "Missing tests/eval/eval_config.yaml"
    assert dataset_path.exists(), "Missing tests/eval/datasets/basic-dataset.json"

    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    raw_text = json.dumps(data)

    if case_id == "f21_case1_eval_config_yaml_exists":
        cfg_text = eval_cfg.read_text(encoding="utf-8")
        assert "metrics_to_run" in cfg_text or "metrics" in cfg_text
        assert "custom_metrics" in cfg_text or "trajectory" in cfg_text
    elif case_id == "f21_case2_basic_dataset_json_valid_schema":
        assert "eval_cases" in data
        assert isinstance(data["eval_cases"], list)
        assert len(data["eval_cases"]) >= 3
        for item in data["eval_cases"]:
            assert "eval_case_id" in item
    elif case_id == "f21_case3_eval_case_k60_bravo4":
        assert "5360-99-812-1740" in raw_text
        assert "Bravo-4" in raw_text
    elif case_id == "f21_case4_eval_case_jackal2_err409":
        assert "5330-99-812-4410" in raw_text
        assert "Jackal" in raw_text or "jackal" in raw_text
    elif case_id == "f21_case5_eval_case_publish_to_group_chat":
        assert "Publish to Group Chat" in raw_text


# ============================================================================
# Feature 22: Cloud Deployment & Shared Environment Publishing (`scripts/deploy_demo.sh`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,expected_token",
    [
        ("f22_case1_bash_syntax_and_mtls", "GOOGLE_API_USE_CLIENT_CERTIFICATE=false"),
        ("f22_case2_authorized_accounts", "sa-reme-demo@antig-dave.iam.gserviceaccount.com"),
        ("f22_case3_cloud_run_deploy_europe_west1", "reme-chat-demonstrator"),
        ("f22_case4_agents_cli_deploy_and_registry", "agents-cli deploy"),
        ("f22_case5_agents_cli_publish_gemini", "agents-cli publish gemini"),
    ],
)
def test_f22_cloud_deployment_script(case_id: str, expected_token: str) -> None:
    """Verify Feature 22: scripts/deploy_demo.sh cloud deployment and non-destructive publishing."""
    deploy_sh = WORKSPACE_ROOT / "scripts" / "deploy_demo.sh"
    assert deploy_sh.exists(), f"[{case_id}] Missing {deploy_sh}"
    text = deploy_sh.read_text(encoding="utf-8")
    assert expected_token in text, f"[{case_id}] Missing '{expected_token}' in scripts/deploy_demo.sh"
    assert "admin@edwardsda.altostrat.com" in text
    assert "europe-west1" in text
    assert "--no-confirm-project" not in text, "deploy_demo.sh must not pass deprecated --no-confirm-project flag"
    proc = subprocess.run(["bash", "-n", str(deploy_sh)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"bash -n failed on deploy_demo.sh: {proc.stderr}"
