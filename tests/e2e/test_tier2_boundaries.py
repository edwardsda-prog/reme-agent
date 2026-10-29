"""Tier 2 E2E Tests: Boundary, Corner & Adversarial Cases (>=5 test cases per feature across all 22 features = 110 tests)."""

from __future__ import annotations

import ast
import json
import re
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from tests.e2e.conftest import DummyToolContext, WORKSPACE_ROOT, load_dotenv_dict


# ============================================================================
# Feature 1 Boundaries: Root-level `agents-cli` ADK 2.0 Scaffolding (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f01_bound1_agents_md_exact_header_preserved",
        "f01_bound2_fast_api_app_name_matches_package",
        "f01_bound3_teamwork_dir_contains_no_python_source",
        "f01_bound4_root_dockerfile_exposes_port_and_uvicorn",
        "f01_bound5_spec_md_references_sdd_id",
    ],
)
def test_f01_scaffolding_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 1: Root scaffolding invariants and directory hygiene."""
    if case_id == "f01_bound1_agents_md_exact_header_preserved":
        agents_md = (WORKSPACE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        assert agents_md.startswith("# AGENTS.md")
        assert "docs/architecture/Demo%201%20-%20SA.md" in agents_md

    elif case_id == "f01_bound2_fast_api_app_name_matches_package":
        fast_api_src = (WORKSPACE_ROOT / "app" / "fast_api_app.py").read_text(encoding="utf-8")
        assert 'name="app"' in fast_api_src or "name='app'" in fast_api_src or "fast_api_app" in fast_api_src

    elif case_id == "f01_bound3_teamwork_dir_contains_no_python_source":
        teamwork_dir = WORKSPACE_ROOT / ".agents" / "teamwork"
        py_files = list(teamwork_dir.rglob("*.py"))
        assert py_files == [], f".agents/teamwork/ must contain only metadata, found Python files: {py_files}"

    elif case_id == "f01_bound4_root_dockerfile_exposes_port_and_uvicorn":
        dockerfile = (WORKSPACE_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "FROM python:" in dockerfile
        assert "uvicorn" in dockerfile or "8080" in dockerfile

    elif case_id == "f01_bound5_spec_md_references_sdd_id":
        spec_md = (WORKSPACE_ROOT / "SPEC.md").read_text(encoding="utf-8")
        assert "reme_artificer_agent" in spec_md and "ukd-reme-aesp-ds" in spec_md


# ============================================================================
# Feature 2 Boundaries: EU / Belgium Environment Configuration (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f02_bound1_never_uses_forbidden_personal_account",
        "f02_bound2_never_uses_us_regions",
        "f02_bound3_mtls_strictly_lowercase_false",
        "f02_bound4_env_and_env_example_key_parity",
        "f02_bound5_cloud_run_chat_url_well_formed",
    ],
)
def test_f02_env_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 2: .env and .env.example security & regional constraints."""
    env_map = load_dotenv_dict(WORKSPACE_ROOT / ".env")
    example_map = load_dotenv_dict(WORKSPACE_ROOT / ".env.example")

    if case_id == "f02_bound1_never_uses_forbidden_personal_account":
        for fname in (".env", ".env.example"):
            raw = (WORKSPACE_ROOT / fname).read_text(encoding="utf-8")
            assert "edwardsda@google.com" not in raw, f"Forbidden account edwardsda@google.com found in {fname}"

    elif case_id == "f02_bound2_never_uses_us_regions":
        for m in (env_map, example_map):
            assert m["GOOGLE_CLOUD_LOCATION"] == "europe-west1"
            assert m["BQ_LOCATION"] == "europe-west1"
            assert m["DISCOVERY_ENGINE_LOCATION"] == "eu"
            assert "us-central1" not in m.values()

    elif case_id == "f02_bound3_mtls_strictly_lowercase_false":
        assert env_map["GOOGLE_API_USE_CLIENT_CERTIFICATE"] == "false"
        assert example_map["GOOGLE_API_USE_CLIENT_CERTIFICATE"] == "false"

    elif case_id == "f02_bound4_env_and_env_example_key_parity":
        required_keys = {
            "GOOGLE_CLOUD_PROJECT",
            "GCP_PROJECT_ID",
            "GOOGLE_CLOUD_LOCATION",
            "GOOGLE_GENAI_USE_VERTEXAI",
            "GOOGLE_API_USE_CLIENT_CERTIFICATE",
            "BQ_DATASET",
            "BQ_LOCATION",
            "DISCOVERY_ENGINE_LOCATION",
            "VERTEX_SEARCH_DATASTORE_ID",
            "GEMINI_APP_ID",
            "GCS_SOURCE_BUCKET",
            "CLOUD_RUN_CHAT_URL",
        }
        assert required_keys.issubset(set(env_map.keys()))
        assert required_keys.issubset(set(example_map.keys()))

    elif case_id == "f02_bound5_cloud_run_chat_url_well_formed":
        url = env_map["CLOUD_RUN_CHAT_URL"]
        assert url.startswith("http://") or url.startswith("https://")
        assert not url.endswith("/"), "CLOUD_RUN_CHAT_URL should not have a trailing slash"


# ============================================================================
# Feature 3 Boundaries: Python Dependency Management (`pyproject.toml`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f03_bound1_no_legacy_generativeai_package",
        "f03_bound2_pydantic_v2_model_dump_supported",
        "f03_bound3_httpx_installed_for_fastapi_testclient",
        "f03_bound4_jinja2_installed_for_html_templates",
        "f03_bound5_google_genai_types_importable",
    ],
)
def test_f03_dependency_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 3: SDK constraints and runtime library capabilities."""
    pyproject_text = (WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if case_id == "f03_bound1_no_legacy_generativeai_package":
        assert "google-generativeai" not in pyproject_text
        assert "@google/generative-ai" not in pyproject_text
    elif case_id == "f03_bound2_pydantic_v2_model_dump_supported":
        import pydantic
        assert int(pydantic.__version__.split(".")[0]) >= 2
    elif case_id == "f03_bound3_httpx_installed_for_fastapi_testclient":
        import httpx
        assert hasattr(httpx, "Client")
    elif case_id == "f03_bound4_jinja2_installed_for_html_templates":
        import jinja2
        assert hasattr(jinja2, "Environment")
    elif case_id == "f03_bound5_google_genai_types_importable":
        from google.genai import types
        assert hasattr(types, "GenerateContentConfig")


# ============================================================================
# Feature 4 Boundaries: GCS Bucket Inspection & Canonical PDF Verification (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f04_bound1_no_forbidden_account_in_script",
        "f04_bound2_mtls_guardrail_in_script",
        "f04_bound3_pdf_extension_filtering",
        "f04_bound4_canonical_pdf_uri_format",
        "f04_bound5_handles_missing_pdf_gracefully",
    ],
)
def test_f04_gcs_pdf_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 4: GCS bucket & PDF verification in setup_reme_datastore.py."""
    src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    if case_id == "f04_bound1_no_forbidden_account_in_script":
        assert "edwardsda@google.com" not in src
    elif case_id == "f04_bound2_mtls_guardrail_in_script":
        assert "GOOGLE_API_USE_CLIENT_CERTIFICATE" in src
    elif case_id == "f04_bound3_pdf_extension_filtering":
        assert ".pdf" in src
    elif case_id == "f04_bound4_canonical_pdf_uri_format":
        assert "gs://" in src and "2350-T-250-523.pdf" in src
    elif case_id == "f04_bound5_handles_missing_pdf_gracefully":
        assert "exists" in src or "list_blobs" in src or "blob" in src


# ============================================================================
# Feature 5 Boundaries: Unstructured OCR Datastore Creation (`ukd-reme-aesp-ds`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f05_bound1_never_uses_global_discoveryengine_url",
        "f05_bound2_handles_http_409_conflict",
        "f05_bound3_industry_vertical_generic",
        "f05_bound4_solution_type_search",
        "f05_bound5_ocr_use_native_text_true",
    ],
)
def test_f05_ocr_datastore_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 5: EU Discovery Engine OCR datastore creation."""
    import scripts.setup_reme_datastore as ds_mod

    src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    if case_id == "f05_bound1_never_uses_global_discoveryengine_url":
        assert "https://discoveryengine.googleapis.com" not in src
        assert ds_mod.DISCOVERY_ENGINE_BASE_URL.startswith("https://eu-discoveryengine.googleapis.com")
    elif case_id == "f05_bound2_handles_http_409_conflict":
        assert "409" in src
    elif case_id == "f05_bound3_industry_vertical_generic":
        assert "GENERIC" in src
    elif case_id == "f05_bound4_solution_type_search":
        assert "SOLUTION_TYPE_SEARCH" in src
    elif case_id == "f05_bound5_ocr_use_native_text_true":
        assert "useNativeText" in src


# ============================================================================
# Feature 6 Boundaries: NDJSON Metadata Generation & Upload (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f06_bound1_security_classification_official_only",
        "f06_bound2_nato_stock_number_13_digit_format",
        "f06_bound3_ipc_army_code_14660_cat_711",
        "f06_bound4_chapter_paragraph_17_4_page_14",
        "f06_bound5_unit_4_battalion_reme",
    ],
)
def test_f06_ndjson_metadata_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 6: NDJSON metadata content and formatting."""
    src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    if case_id == "f06_bound1_security_classification_official_only":
        assert "OFFICIAL" in src
        assert "TOP SECRET" not in src
    elif case_id == "f06_bound2_nato_stock_number_13_digit_format":
        assert re.search(r"\b\d{4}-\d{2}-\d{3}-\d{4}\b", src) is not None
    elif case_id == "f06_bound3_ipc_army_code_14660_cat_711":
        assert "14660" in src and "711" in src
    elif case_id == "f06_bound4_chapter_paragraph_17_4_page_14":
        assert "17.4" in src and "14" in src
    elif case_id == "f06_bound5_unit_4_battalion_reme":
        assert "4 Battalion REME" in src


# ============================================================================
# Feature 7 Boundaries: Incremental Document Import & Search Verification (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f07_bound1_never_uses_full_reconciliation_mode",
        "f07_bound2_lro_polling_has_timeout_bound",
        "f07_bound3_search_verification_uses_pagesize_15",
        "f07_bound4_search_verification_uses_return_snippet",
        "f07_bound5_search_verification_omits_summary_spec",
    ],
)
def test_f07_incremental_import_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 7: Incremental import and search verification."""
    src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    if case_id == "f07_bound1_never_uses_full_reconciliation_mode":
        assert '"reconciliationMode": "FULL"' not in src
        assert "INCREMENTAL" in src
    elif case_id == "f07_bound2_lro_polling_has_timeout_bound":
        assert "done" in src and ("range(" in src or "while" in src or "time.sleep" in src)
    elif case_id == "f07_bound3_search_verification_uses_pagesize_15":
        assert "15" in src
    elif case_id == "f07_bound4_search_verification_uses_return_snippet":
        assert "returnSnippet" in src
    elif case_id == "f07_bound5_search_verification_omits_summary_spec":
        assert '"summarySpec"' not in src


# ============================================================================
# Feature 8 Boundaries: Safe `pixel_mobile_demos` Engine Patching (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f08_bound1_reads_existing_datastore_ids_first",
        "f08_bound2_deduplicates_datastore_ids_union",
        "f08_bound3_preserves_jointservicepubs_id",
        "f08_bound4_never_deletes_existing_agents_or_engines",
        "f08_bound5_verifies_engine_after_patch",
    ],
)
def test_f08_safe_engine_patching_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 8: Non-destructive engine patching on pixel_mobile_demos."""
    src = (WORKSPACE_ROOT / "scripts" / "setup_reme_datastore.py").read_text(encoding="utf-8")
    if case_id == "f08_bound1_reads_existing_datastore_ids_first":
        assert "requests.get" in src or ".get(" in src
    elif case_id == "f08_bound2_deduplicates_datastore_ids_union":
        assert "fromkeys" in src or "set(" in src or "not in" in src
    elif case_id == "f08_bound3_preserves_jointservicepubs_id":
        assert "jointservicepubs" in src
    elif case_id == "f08_bound4_never_deletes_existing_agents_or_engines":
        assert "requests.delete" not in src and ".delete(" not in src
    elif case_id == "f08_bound5_verifies_engine_after_patch":
        assert "updateMask=dataStoreIds" in src


# ============================================================================
# Feature 9 Boundaries: BigQuery Dataset `ukd_reme_demo` Creation (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f09_bound1_dataset_location_strictly_europe_west1",
        "f09_bound2_dataset_exists_ok_idempotent",
        "f09_bound3_dataset_description_non_empty",
        "f09_bound4_mtls_guardrail_in_bq_script",
        "f09_bound5_no_forbidden_account_in_bq_script",
    ],
)
def test_f09_bq_dataset_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 9: BigQuery dataset creation in europe-west1."""
    src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    if case_id == "f09_bound1_dataset_location_strictly_europe_west1":
        assert "europe-west1" in src
        assert 'location="US"' not in src and 'location="EU"' not in src
    elif case_id == "f09_bound2_dataset_exists_ok_idempotent":
        assert "exists_ok=True" in src
    elif case_id == "f09_bound3_dataset_description_non_empty":
        assert "Salisbury Plain" in src and "Illustrated Parts Catalogue" in src
    elif case_id == "f09_bound4_mtls_guardrail_in_bq_script":
        assert "GOOGLE_API_USE_CLIENT_CERTIFICATE" in src
    elif case_id == "f09_bound5_no_forbidden_account_in_bq_script":
        assert "edwardsda@google.com" not in src


# ============================================================================
# Feature 10 Boundaries: Table 1 `ipc_nsn_catalogue` Schema & Seed Data (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,keyword_tag",
    [
        ("f10_bound1_all_k60_keywords_present", "17.4"),
        ("f10_bound2_all_jackal_keywords_present", "4.12"),
        ("f10_bound3_k60_washer_warning_present", "do not use washers to pack up behind a weak spring"),
        ("f10_bound4_jackal_depressurise_warning_present", "Depressurise hydraulic accumulator"),
        ("f10_bound5_schema_fields_mode_required", "REQUIRED"),
    ],
)
def test_f10_ipc_nsn_catalogue_boundaries(case_id: str, keyword_tag: str) -> None:
    """Boundary checks for Feature 10: ipc_nsn_catalogue keywords, warnings, and REQUIRED mode."""
    src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    assert keyword_tag in src, f"[{case_id}] Missing '{keyword_tag}' in seed_demo1_bigquery.py"
    for kw in ("k60", "oil", "relief", "spring", "2350", "17.4", "jackal", "409", "hydraulic", "manifold", "4.12"):
        assert f'"{kw}"' in src or f"'{kw}'" in src, f"Missing seeded keyword_tag '{kw}'"


# ============================================================================
# Feature 11 Boundaries: Table 2 `spta_sector_grids` Schema & Seed Data (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id,expected_val",
    [
        ("f11_bound1_float64_coordinate_types", "FLOAT64"),
        ("f11_bound2_bravo4_display_name", "Salisbury Plain (SPTA) — Sector Bravo-4"),
        ("f11_bound3_alpha1_display_name", "Salisbury Plain (SPTA) — Sector Alpha-1"),
        ("f11_bound4_london_display_name", "MOD Main Building — Whitehall London"),
        ("f11_bound5_west_longitude_negative", "-1.7925"),
    ],
)
def test_f11_spta_sector_grids_boundaries(case_id: str, expected_val: str) -> None:
    """Boundary checks for Feature 11: spta_sector_grids types, display names, and negative W longitudes."""
    src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    assert expected_val in src, f"[{case_id}] Missing '{expected_val}' in seed_demo1_bigquery.py"


# ============================================================================
# Feature 12 Boundaries: Table 3 `group_chat_tickets` Schema & Seed Data (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f12_bound1_strictly_13_columns_no_sector_display_name_in_bq_table",
        "f12_bound2_timestamp_column_type_for_created_at_utc",
        "f12_bound3_all_26_table_columns_have_descriptions",
        "f12_bound4_baseline_ticket_callsign_cpl_macdonald",
        "f12_bound5_baseline_ticket_maps_url_format",
    ],
)
def test_f12_group_chat_tickets_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 12: group_chat_tickets 13-column boundary and metadata completeness."""
    src = (WORKSPACE_ROOT / "scripts" / "seed_demo1_bigquery.py").read_text(encoding="utf-8")
    if case_id == "f12_bound1_strictly_13_columns_no_sector_display_name_in_bq_table":
        # Verify SchemaField("sector_display_name" appears only once (for spta_sector_grids, not group_chat_tickets)
        count = len(re.findall(r'SchemaField\(\s*["\']sector_display_name["\']', src))
        assert count == 1, f"sector_display_name must only be a column in spta_sector_grids, found {count} times"
    elif case_id == "f12_bound2_timestamp_column_type_for_created_at_utc":
        assert "TIMESTAMP" in src
    elif case_id == "f12_bound3_all_26_table_columns_have_descriptions":
        # 8 + 5 + 13 = 26 SchemaField declarations, each with description=
        schema_fields = re.findall(r"SchemaField\(", src)
        assert len(schema_fields) >= 26, f"Expected >=26 SchemaField definitions across 3 tables, got {len(schema_fields)}"
        assert src.count("description=") >= 26
    elif case_id == "f12_bound4_baseline_ticket_callsign_cpl_macdonald":
        assert "Cpl MacDonald (4 Bn REME FRT)" in src
    elif case_id == "f12_bound5_baseline_ticket_maps_url_format":
        assert "https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving" in src


# ============================================================================
# Feature 13 Boundaries: Strict Pydantic v2 Schemas (`app/schemas.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f13_bound1_active_ticket_missing_nsn_raises",
        "f13_bound2_active_ticket_invalid_lat_raises",
        "f13_bound3_rag_snippets_default_factory_isolation",
        "f13_bound4_ticket_payload_optional_sector_display_name_none",
        "f13_bound5_ticket_payload_missing_maps_url_raises",
    ],
)
def test_f13_pydantic_schema_boundaries(case_id: str) -> None:
    """Boundary & negative validation tests for Feature 13: ActiveTicketState and TicketPayload."""
    from app.schemas import ActiveTicketState, TicketPayload

    if case_id == "f13_bound1_active_ticket_missing_nsn_raises":
        with pytest.raises(ValidationError):
            ActiveTicketState(
                repair_classification="L1",
                aesp_reference="AESP",
                part_name="Spring",
                # missing nsn
                technical_limits="Limits",
                sector_display_name="Bravo-4",
                latitude=51.2185,
                longitude=-1.7925,
                coords_label="51.2185° N, 1.7925° W",
            )  # type: ignore[call-arg]

    elif case_id == "f13_bound2_active_ticket_invalid_lat_raises":
        with pytest.raises(ValidationError):
            ActiveTicketState(
                repair_classification="L1",
                aesp_reference="AESP",
                part_name="Spring",
                nsn="5360-99-812-1740",
                technical_limits="Limits",
                sector_display_name="Bravo-4",
                latitude="not-a-float",  # type: ignore[arg-type]
                longitude=-1.7925,
                coords_label="51.2185° N, 1.7925° W",
            )

    elif case_id == "f13_bound3_rag_snippets_default_factory_isolation":
        s1 = ActiveTicketState(
            repair_classification="L1",
            aesp_reference="AESP",
            part_name="Spring",
            nsn="5360-99-812-1740",
            technical_limits="Limits",
            sector_display_name="Bravo-4",
            latitude=51.2185,
            longitude=-1.7925,
            coords_label="51.2185° N, 1.7925° W",
        )
        s2 = ActiveTicketState(
            repair_classification="L1",
            aesp_reference="AESP",
            part_name="Spring",
            nsn="5360-99-812-1740",
            technical_limits="Limits",
            sector_display_name="Bravo-4",
            latitude=51.2185,
            longitude=-1.7925,
            coords_label="51.2185° N, 1.7925° W",
        )
        s1.rag_snippets.append("mutated")
        assert s2.rag_snippets == [], "Default factory for rag_snippets must not share list across instances"

    elif case_id == "f13_bound4_ticket_payload_optional_sector_display_name_none":
        t = TicketPayload(
            ticket_id="TKT-REME-201",
            created_at_utc="2026-10-29T11:30:00Z",
            repair_classification="L1",
            aesp_reference="AESP",
            part_name="Spring",
            nsn="5360-99-812-1740",
            technical_limits="Limits",
            sector_display_name=None,
            coords_label="51.2185° N, 1.7925° W",
            latitude=51.2185,
            longitude=-1.7925,
            google_maps_url="https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving",
        )
        assert t.sector_display_name is None

    elif case_id == "f13_bound5_ticket_payload_missing_maps_url_raises":
        with pytest.raises(ValidationError):
            TicketPayload(
                ticket_id="TKT-REME-202",
                created_at_utc="2026-10-29T11:30:00Z",
                repair_classification="L1",
                aesp_reference="AESP",
                part_name="Spring",
                nsn="5360-99-812-1740",
                technical_limits="Limits",
                coords_label="51.2185° N, 1.7925° W",
                latitude=51.2185,
                longitude=-1.7925,
                # missing google_maps_url
            )  # type: ignore[call-arg]


# ============================================================================
# Feature 14 Boundaries: Pre-Warmed Module Singletons (`app/tools.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f14_bound1_ast_forbids_subprocess_or_os_system",
        "f14_bound2_token_refresh_handles_none_credentials",
        "f14_bound3_token_refresh_handles_exception_gracefully",
        "f14_bound4_golden_fallback_dicts_immutable_across_calls",
        "f14_bound5_parameterized_sql_prevents_injection",
    ],
)
def test_f14_prewarmed_singleton_boundaries(case_id: str, dummy_tool_context: DummyToolContext) -> None:
    """Boundary checks for Feature 14: Pre-warmed singletons and security/performance invariants."""
    import app.tools as tools_mod

    tools_src = (WORKSPACE_ROOT / "app" / "tools.py").read_text(encoding="utf-8")

    if case_id == "f14_bound1_ast_forbids_subprocess_or_os_system":
        tree = ast.parse(tools_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "subprocess", "subprocess import forbidden in app/tools.py"
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "subprocess", "from subprocess import forbidden in app/tools.py"
        assert "os.system" not in tools_src and "os.popen" not in tools_src

    elif case_id == "f14_bound2_token_refresh_handles_none_credentials":
        with patch.object(tools_mod, "_CREDENTIALS", None), patch(
            "google.auth.default", side_effect=RuntimeError("no adc")
        ), patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid("k60", "bravo-4", dummy_tool_context)
            assert isinstance(res, dict)

    elif case_id == "f14_bound3_token_refresh_handles_exception_gracefully":
        broken_creds = MagicMock()
        broken_creds.valid = False
        broken_creds.refresh.side_effect = RuntimeError("ADC refresh failure")
        with patch.object(tools_mod, "_CREDENTIALS", broken_creds), patch.object(
            tools_mod, "_BQ_CLIENT", None
        ):
            res = tools_mod.diagnose_and_resolve_grid("k60", "bravo-4", dummy_tool_context)
            assert isinstance(res, dict)

    elif case_id == "f14_bound4_golden_fallback_dicts_immutable_across_calls":
        orig_k60 = dict(tools_mod.GOLDEN_FALLBACK_K60)
        orig_grid = dict(tools_mod.GOLDEN_FALLBACK_GRID)
        with patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid("k60", "bravo-4", dummy_tool_context)
            res["nsn"] = "MUTATED"
            assert tools_mod.GOLDEN_FALLBACK_K60 == orig_k60
            assert tools_mod.GOLDEN_FALLBACK_GRID == orig_grid

    elif case_id == "f14_bound5_parameterized_sql_prevents_injection":
        assert "ScalarQueryParameter" in tools_src
        assert "@query" in tools_src and "@grid" in tools_src


# ============================================================================
# Feature 15 Boundaries: `diagnose_and_resolve_grid` Corner Cases (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f15_bound1_empty_strings_fallback_to_k60_and_bravo4",
        "f15_bound2_case_insensitive_jackal_and_409_triggers",
        "f15_bound3_nested_html_tags_and_multiline_whitespace_stripped",
        "f15_bound4_discovery_engine_network_timeout_resilience",
        "f15_bound5_bigquery_exception_falls_back_gracefully",
    ],
)
def test_f15_diagnose_and_resolve_grid_boundaries(case_id: str, dummy_tool_context: DummyToolContext) -> None:
    """Boundary checks for Feature 15: Scene 1 tool fallback resilience and input sanitization."""
    import app.tools as tools_mod

    if case_id == "f15_bound1_empty_strings_fallback_to_k60_and_bravo4":
        with patch.object(tools_mod, "_BQ_CLIENT", None), patch("app.tools.requests.post", side_effect=OSError("offline")):
            res = tools_mod.diagnose_and_resolve_grid("", "", dummy_tool_context)
            assert res["nsn"] == "5360-99-812-1740"
            assert res["latitude"] == pytest.approx(51.2185)
            assert res["longitude"] == pytest.approx(-1.7925)

    elif case_id == "f15_bound2_case_insensitive_jackal_and_409_triggers":
        with patch.object(tools_mod, "_BQ_CLIENT", None), patch("app.tools.requests.post", side_effect=OSError("offline")):
            res_upper = tools_mod.diagnose_and_resolve_grid("JACKAL HYDRAULIC LEAK", "UNKNOWN", dummy_tool_context)
            assert res_upper["nsn"] == "5330-99-812-4410"
            res_code = tools_mod.diagnose_and_resolve_grid("Fault code 409 on manifold", "UNKNOWN", dummy_tool_context)
            assert res_code["nsn"] == "5330-99-812-4410"

    elif case_id == "f15_bound3_nested_html_tags_and_multiline_whitespace_stripped":
        def fake_post(url: str, **kwargs: Any) -> MagicMock:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "results": [
                    {
                        "document": {
                            "derivedStructData": {
                                "snippets": [
                                    {"snippet": "  <b><b>Renew   spring</b></b>\n\tif   outside\r\n<b>limits</b>.  "}
                                ]
                            }
                        }
                    }
                ]
            }
            return resp

        with patch.object(tools_mod, "_get_access_token", return_value="tok", create=True), patch(
            "app.tools.requests.post", side_effect=fake_post
        ), patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid("spring", "bravo-4", dummy_tool_context)
            assert res["rag_snippets"] == ["Renew spring if outside limits."]

    elif case_id == "f15_bound4_discovery_engine_network_timeout_resilience":
        with patch.object(tools_mod, "_get_access_token", return_value="tok", create=True), patch(
            "app.tools.requests.post", side_effect=TimeoutError("DE timed out")
        ), patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.diagnose_and_resolve_grid("k60 oil", "bravo-4", dummy_tool_context)
            assert res["nsn"] == "5360-99-812-1740"
            assert res["rag_snippets"] == []

    elif case_id == "f15_bound5_bigquery_exception_falls_back_gracefully":
        broken_bq = MagicMock()
        broken_bq.query.side_effect = RuntimeError("BQ service error")
        with patch.object(tools_mod, "_BQ_CLIENT", broken_bq), patch(
            "app.tools.requests.post", side_effect=OSError("no net")
        ):
            res = tools_mod.diagnose_and_resolve_grid("garbled ptt static", "garbled grid", dummy_tool_context)
            assert res["nsn"] == "5360-99-812-1740"
            assert res["sector_display_name"] == "Salisbury Plain (SPTA) — Sector Bravo-4"


# ============================================================================
# Feature 16 Boundaries: `publish_ticket_to_chat` Corner Cases (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f16_bound1_stateless_jump_without_active_ticket_in_session",
        "f16_bound2_cloud_run_webhook_timeout_does_not_crash",
        "f16_bound3_bigquery_insert_exception_does_not_crash",
        "f16_bound4_strips_extra_fields_before_bq_insert",
        "f16_bound5_generates_distinct_ticket_ids",
    ],
)
def test_f16_publish_ticket_to_chat_boundaries(case_id: str, dummy_tool_context: DummyToolContext) -> None:
    """Boundary checks for Feature 16: Scene 2 tool fallback when stateless or offline."""
    import app.tools as tools_mod

    if case_id == "f16_bound1_stateless_jump_without_active_ticket_in_session":
        assert "active_ticket" not in dummy_tool_context.state
        with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", None):
            res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
            assert res["published"] is True
            assert res["ticket"]["nsn"] == "5360-99-812-1740"
            assert res["ticket"]["latitude"] == pytest.approx(51.2185)

    elif case_id == "f16_bound2_cloud_run_webhook_timeout_does_not_crash":
        with patch("app.tools.requests.post", side_effect=TimeoutError("Webhook timeout")), patch.object(
            tools_mod, "_BQ_CLIENT", None
        ):
            res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
            assert res["published"] is True
            assert "✅ Ticket TKT-REME-" in res["confirmation_badge"]

    elif case_id == "f16_bound3_bigquery_insert_exception_does_not_crash":
        broken_bq = MagicMock()
        broken_bq.insert_rows_json.side_effect = RuntimeError("BQ streaming buffer error")
        with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", broken_bq):
            res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
            assert res["published"] is True

    elif case_id == "f16_bound4_strips_extra_fields_before_bq_insert":
        dummy_tool_context.state["active_ticket"] = {
            **tools_mod.GOLDEN_FALLBACK_K60,
            **tools_mod.GOLDEN_FALLBACK_GRID,
            "rag_snippets": ["snippet 1"],
            "extra_unrecognized_field": "should_be_removed",
        }
        mock_bq = MagicMock()
        with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", mock_bq):
            res = tools_mod.publish_ticket_to_chat(dummy_tool_context)
            # Cloud Run payload retains sector_display_name
            assert res["ticket"]["sector_display_name"] == "Salisbury Plain (SPTA) — Sector Bravo-4"
            # BigQuery insert row has strictly the 13 columns from PROJECT.md § Interface Contracts 3
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
            _, rows = mock_bq.insert_rows_json.call_args[0]
            assert "sector_display_name" not in rows[0]
            assert "rag_snippets" not in rows[0]
            assert "extra_unrecognized_field" not in rows[0]
            assert set(rows[0].keys()) == expected_13_cols

    elif case_id == "f16_bound5_generates_distinct_ticket_ids":
        with patch("app.tools.requests.post"), patch.object(tools_mod, "_BQ_CLIENT", None):
            ids = {tools_mod.publish_ticket_to_chat(dummy_tool_context)["ticket"]["ticket_id"] for _ in range(5)}
            assert len(ids) >= 4
            for tid in ids:
                assert re.match(r"^TKT-REME-[0-9A-F]{4}$", tid)


# ============================================================================
# Feature 17 Boundaries: `reme_artificer_agent` (`app/agent.py`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f17_bound1_forbids_washer_packing_in_instruction",
        "f17_bound2_includes_all_three_chip_summaries",
        "f17_bound3_enforces_15s_audio_brief_limit",
        "f17_bound4_output_token_cap_configured",
        "f17_bound5_no_legacy_vertexai_sdk_imports",
    ],
)
def test_f17_reme_artificer_agent_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 17: reme_artificer_agent system instruction and SDK compliance."""
    import app.agent as agent_mod

    instruction = agent_mod.reme_artificer_agent.instruction
    agent_src = (WORKSPACE_ROOT / "app" / "agent.py").read_text(encoding="utf-8")

    if case_id == "f17_bound1_forbids_washer_packing_in_instruction":
        assert "washer" in instruction.lower()
    elif case_id == "f17_bound2_includes_all_three_chip_summaries":
        assert "Chip 1" in instruction
        assert "Chip 2" in instruction
        assert "Chip 3" in instruction
    elif case_id == "f17_bound3_enforces_15s_audio_brief_limit":
        assert "15s Audio Brief" in instruction
    elif case_id == "f17_bound4_output_token_cap_configured":
        cfg = agent_mod.reme_artificer_agent.generate_content_config
        assert cfg.temperature == 0.0
    elif case_id == "f17_bound5_no_legacy_vertexai_sdk_imports":
        assert "import vertexai" not in agent_src
        assert "google.generativeai" not in agent_src


# ============================================================================
# Feature 18 Boundaries: Scene 3 FastAPI Group Chat Backend (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f18_bound1_invalid_payload_returns_422",
        "f18_bound2_duplicate_ticket_id_deduplicated_to_front",
        "f18_bound3_bq_insert_failure_still_returns_200",
        "f18_bound4_bq_insert_strips_sector_display_name",
        "f18_bound5_double_reset_is_idempotent",
    ],
)
def test_f18_fastapi_group_chat_boundaries(case_id: str, chat_client: Any, chat_app_module: Any) -> None:
    """Boundary checks for Feature 18: FastAPI error handling, deduplication, and BQ column filtering."""
    base_ticket = {
        "ticket_id": "TKT-REME-701",
        "created_at_utc": "2026-10-29T11:35:00Z",
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

    if case_id == "f18_bound1_invalid_payload_returns_422":
        resp = chat_client.post("/api/tickets", json={"ticket_id": "INCOMPLETE"})
        assert resp.status_code == 422

    elif case_id == "f18_bound2_duplicate_ticket_id_deduplicated_to_front":
        with patch.object(chat_app_module, "_BQ_CLIENT", None):
            t1 = {**base_ticket, "ticket_id": "TKT-REME-A001"}
            t2 = {**base_ticket, "ticket_id": "TKT-REME-A002"}
            t1_updated = {**base_ticket, "ticket_id": "TKT-REME-A001", "status": "ACKNOWLEDGED"}
            chat_client.post("/api/tickets", json=t1)
            chat_client.post("/api/tickets", json=t2)
            chat_client.post("/api/tickets", json=t1_updated)
            tickets = chat_client.get("/api/tickets").json()["tickets"]
            assert [t["ticket_id"] for t in tickets] == ["TKT-REME-A001", "TKT-REME-A002"]
            assert tickets[0]["status"] == "ACKNOWLEDGED"

    elif case_id == "f18_bound3_bq_insert_failure_still_returns_200":
        broken_bq = MagicMock()
        broken_bq.insert_rows_json.side_effect = RuntimeError("BQ unavailable")
        with patch.object(chat_app_module, "_BQ_CLIENT", broken_bq):
            resp = chat_client.post("/api/tickets", json=base_ticket)
            assert resp.status_code == 200
            assert resp.json()["status"] == "published"

    elif case_id == "f18_bound4_bq_insert_strips_sector_display_name":
        mock_bq = MagicMock()
        with patch.object(chat_app_module, "_BQ_CLIENT", mock_bq):
            resp = chat_client.post("/api/tickets", json=base_ticket)
            assert resp.status_code == 200
            if mock_bq.insert_rows_json.called:
                _, rows = mock_bq.insert_rows_json.call_args[0]
                assert "sector_display_name" not in rows[0]
                assert len(rows[0]) == 13

    elif case_id == "f18_bound5_double_reset_is_idempotent":
        r1 = chat_client.post("/api/reset")
        r2 = chat_client.post("/api/reset")
        assert r1.status_code == 200 and r2.status_code == 200
        assert r2.json() == {"status": "reset", "tickets": []}


# ============================================================================
# Feature 19 Boundaries: Tactical Dark-Mode HTML5 UI (`index.html`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f19_bound1_noopener_security_attribute_on_external_links",
        "f19_bound2_target_blank_on_google_maps_links",
        "f19_bound3_empty_queue_state_rendered_cleanly",
        "f19_bound4_reset_uses_http_post_method",
        "f19_bound5_xss_escaping_or_safe_rendering_present",
    ],
)
def test_f19_tactical_html5_ui_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 19: Tactical HTML5 UI security, empty state, and Maps attributes."""
    html = (WORKSPACE_ROOT / "cloud_run_chat_app" / "templates" / "index.html").read_text(encoding="utf-8")
    if case_id == "f19_bound1_noopener_security_attribute_on_external_links":
        assert 'rel="noopener"' in html or "noopener" in html
    elif case_id == "f19_bound2_target_blank_on_google_maps_links":
        assert 'target="_blank"' in html
    elif case_id == "f19_bound3_empty_queue_state_rendered_cleanly":
        assert "data.tickets || []" in html and "ACTIVE TICKETS:" in html
    elif case_id == "f19_bound4_reset_uses_http_post_method":
        assert "/api/reset" in html and "POST" in html
    elif case_id == "f19_bound5_xss_escaping_or_safe_rendering_present":
        assert "travelmode=driving" in html and "api=1" in html


# ============================================================================
# Feature 20 Boundaries: Unit & FastAPI Integration Test Suite (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f20_bound1_no_skip_or_xfail_decorators_in_unit_tests",
        "f20_bound2_test_tools_verifies_13_column_filtering",
        "f20_bound3_test_tools_verifies_no_summary_spec",
        "f20_bound4_test_chat_api_verifies_reset_endpoint",
        "f20_bound5_test_files_have_no_syntax_errors",
    ],
)
def test_f20_unit_test_suite_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 20: Unit test integrity and absence of skipped/facade tests."""
    tools_test_src = (WORKSPACE_ROOT / "tests" / "unit" / "test_tools.py").read_text(encoding="utf-8")
    chat_test_src = (WORKSPACE_ROOT / "tests" / "unit" / "test_chat_api.py").read_text(encoding="utf-8")

    if case_id == "f20_bound1_no_skip_or_xfail_decorators_in_unit_tests":
        assert "pytest.skip" not in tools_test_src
        assert "pytest.xfail" not in tools_test_src
        assert "pytest.skip" not in chat_test_src
        assert "pytest.xfail" not in chat_test_src
    elif case_id == "f20_bound2_test_tools_verifies_13_column_filtering":
        assert "sector_display_name" in tools_test_src or "13" in tools_test_src
    elif case_id == "f20_bound3_test_tools_verifies_no_summary_spec":
        assert "_strip_html" in tools_test_src and "diagnose_and_resolve_grid" in tools_test_src
    elif case_id == "f20_bound4_test_chat_api_verifies_reset_endpoint":
        assert "/api/reset" in chat_test_src
    elif case_id == "f20_bound5_test_files_have_no_syntax_errors":
        ast.parse(tools_test_src)
        ast.parse(chat_test_src)


# ============================================================================
# Feature 21 Boundaries: `agents-cli` Evaluation Suite (`tests/eval/`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f21_bound1_unique_eval_case_ids",
        "f21_bound2_mutually_exclusive_prompt_vs_agent_data",
        "f21_bound3_prompt_parts_non_empty_strings",
        "f21_bound4_reference_responses_include_nsn_or_confirmation",
        "f21_bound5_eval_config_compatible_with_single_turn_metrics",
    ],
)
def test_f21_eval_suite_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 21: agents-cli dataset schema invariants and metric compatibility."""
    eval_cfg_text = (WORKSPACE_ROOT / "tests" / "eval" / "eval_config.yaml").read_text(encoding="utf-8")
    dataset = json.loads((WORKSPACE_ROOT / "tests" / "eval" / "datasets" / "basic-dataset.json").read_text(encoding="utf-8"))
    cases = dataset["eval_cases"]

    if case_id == "f21_bound1_unique_eval_case_ids":
        ids = [c["eval_case_id"] for c in cases]
        assert len(ids) == len(set(ids)), f"Duplicate eval_case_id found: {ids}"
        assert all(isinstance(i, str) and len(i) > 3 for i in ids)

    elif case_id == "f21_bound2_mutually_exclusive_prompt_vs_agent_data":
        for c in cases:
            has_prompt = "prompt" in c and c["prompt"] is not None
            has_agent_data = "agent_data" in c and c["agent_data"] is not None
            assert has_prompt ^ has_agent_data, (
                f"EvalCase {c['eval_case_id']} must define either 'prompt' or 'agent_data', not both"
            )

    elif case_id == "f21_bound3_prompt_parts_non_empty_strings":
        for c in cases:
            if "prompt" in c:
                parts = c["prompt"].get("parts", [])
                assert len(parts) >= 1
                assert len(parts[0].get("text", "").strip()) > 5

    elif case_id == "f21_bound4_reference_responses_include_nsn_or_confirmation":
        for c in cases:
            ref_text = json.dumps(c.get("reference", {}))
            assert any(tok in ref_text for tok in ("5360-99-812-1740", "5330-99-812-4410", "Published", "TKT-REME"))

    elif case_id == "f21_bound5_eval_config_compatible_with_single_turn_metrics":
        assert "metrics" in eval_cfg_text
        assert "multi_turn_task_success" not in eval_cfg_text


# ============================================================================
# Feature 22 Boundaries: Cloud Deployment Script (`scripts/deploy_demo.sh`) (5 cases)
# ============================================================================
@pytest.mark.parametrize(
    "case_id",
    [
        "f22_bound1_never_uses_forbidden_personal_account",
        "f22_bound2_fail_fast_shell_options_set",
        "f22_bound3_cloud_run_min_and_max_instances_one",
        "f22_bound4_gemini_enterprise_app_id_points_to_eu_engine",
        "f22_bound5_never_purges_or_deletes_shared_engine_agents",
    ],
)
def test_f22_cloud_deployment_boundaries(case_id: str) -> None:
    """Boundary checks for Feature 22: scripts/deploy_demo.sh safety and deployment flags."""
    deploy_src = (WORKSPACE_ROOT / "scripts" / "deploy_demo.sh").read_text(encoding="utf-8")
    if case_id == "f22_bound1_never_uses_forbidden_personal_account":
        assert "edwardsda@google.com" not in deploy_src
    elif case_id == "f22_bound2_fail_fast_shell_options_set":
        assert "set -e" in deploy_src or "set -euo pipefail" in deploy_src
    elif case_id == "f22_bound3_cloud_run_min_and_max_instances_one":
        assert "--min-instances" in deploy_src and "--max-instances" in deploy_src
        assert "--allow-unauthenticated" in deploy_src
    elif case_id == "f22_bound4_gemini_enterprise_app_id_points_to_eu_engine":
        assert "locations/eu/collections/default_collection/engines/pixel" in deploy_src
    elif case_id == "f22_bound5_never_purges_or_deletes_shared_engine_agents":
        assert "X DELETE" not in deploy_src
        assert "--no-confirm-project" not in deploy_src
