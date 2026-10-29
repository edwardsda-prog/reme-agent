# E2E Test Infrastructure — UK Defence REME Artificer Demonstrator (`@REME-Artificer` — Demo 1)

## 1. Overview & Philosophy

This document specifies the requirement-driven, opaque-box 4-tier End-to-End (E2E) test suite for the **UK Defence REME Artificer Demonstrator (`@REME-Artificer` — Demo 1)** in `tests/e2e/`.

The test suite verifies all **22 features** enumerated in `PROJECT.md § Feature Inventory` against the authoritative specifications in:
- `.agents/teamwork/ORIGINAL_REQUEST.md` (Requirements R1–R5 and Acceptance Criteria)
- `PROJECT.md` (Feature Inventory #1–#22 and Interface Contracts §1–§5)
- `docs/architecture/implementation-plan.md` (Phases 1–6 / 8-Phase Execution Plan)
- `docs/architecture/Demo 1 - SA.md` (`SDD-DEMO1-ADK2-003`)

### Core Principles
1. **Opaque-Box Contract Verification**: Tests validate public interfaces, file/configuration contracts, Pydantic schemas (`ActiveTicketState`, `TicketPayload`), ADK 2.0 tool signatures and behavior (`diagnose_and_resolve_grid`, `publish_ticket_to_chat`), `LlmAgent` configuration (`reme_artificer_agent`, `gemini-2.5-flash`, `temperature=0.0`), Scene 3 FastAPI routes (`GET /`, `GET /api/tickets`, `POST /api/tickets`, `POST /api/reset`), HTML5 tactical UI, BigQuery/Discovery Engine provisioning scripts, and EU/Belgium (`europe-west1` / `eu`) residency guardrails.
2. **Stage-Proof Determinism & Isolation**: Every test sets up its own state (`DummyToolContext`, reset `ACTIVE_TICKETS`), cleans up after itself, and enforces `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`.
3. **4-Tier Progressive Verification**:
   - **Tier 1 (`tests/e2e/test_tier1_features.py`)**: Happy-path feature verification with **>= 5 distinct test cases per feature** across all 22 features (**110+ test cases**).
   - **Tier 2 (`tests/e2e/test_tier2_boundaries.py`)**: Boundary conditions, corner cases, malformed inputs, HTML tag stripping, 13-column BigQuery insert filtering, and stage-proof fallback resilience with **>= 5 test cases per feature** across all 22 features (**110+ test cases**).
   - **Tier 3 (`tests/e2e/test_tier3_pairwise.py`)**: Cross-feature pairwise integration tests (**24 test cases**, >= 22 required) verifying interactions across Scene 1, Session State, Scene 2, Scene 3 FastAPI, BigQuery schemas, and Discovery Engine snippets.
   - **Tier 4 (`tests/e2e/test_tier4_scenarios.py`)**: Realistic end-to-end tactical sustainment application journeys (**12 scenarios**, >= 11 required) simulating Cpl MacDonald (4 Bn REME FRT) on Salisbury Plain Training Area (SPTA).

---

## 2. Test Runner Command

Always run the E2E suite from the repository root with `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`:

```bash
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/ -v
```

To run a specific tier:

```bash
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier1_features.py -v
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier2_boundaries.py -v
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier3_pairwise.py -v
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier4_scenarios.py -v
```

---

## 3. Directory Layout

```text
tests/e2e/
├── __init__.py                 # E2E package marker
├── conftest.py                 # Shared fixtures, DummyToolContext, FastAPI client loader, env guardrails
├── test_tier1_features.py      # Tier 1: >=5 happy-path tests per feature (22 features = 110 tests)
├── test_tier2_boundaries.py    # Tier 2: >=5 boundary/adversarial tests per feature (22 features = 110 tests)
├── test_tier3_pairwise.py      # Tier 3: 24 cross-feature pairwise interaction tests (>=22 required)
└── test_tier4_scenarios.py     # Tier 4: 12 real-world SPTA tactical sustainment scenarios (>=11 required)
```

---

## 4. 22-Feature Coverage Matrix

| Feature # | Feature Name (`PROJECT.md`) | Milestone | Tier 1 Tests (`test_tier1_features.py`) | Tier 2 Tests (`test_tier2_boundaries.py`) | Tier 3 Pairwise (`test_tier3_pairwise.py`) | Tier 4 Scenarios (`test_tier4_scenarios.py`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F01** | Root-level `agents-cli` ADK 2.0 Scaffolding | M1 | `test_f01_root_scaffolding` (5 cases) | `test_f01_scaffolding_boundaries` (5 cases) | `test_pair_01`, `test_pair_21` | `test_scenario_10` |
| **F02** | EU / Belgium Environment Configuration (`.env` & `.env.example`) | M1 | `test_f02_env_configuration` (5 cases) | `test_f02_env_boundaries` (5 cases) | `test_pair_02`, `test_pair_19` | `test_scenario_10`, `test_scenario_11` |
| **F03** | Python Dependency Management (`pyproject.toml` & `uv sync`) | M1 | `test_f03_dependencies` (5 cases) | `test_f03_dependency_boundaries` (5 cases) | `test_pair_01` | `test_scenario_10` |
| **F04** | GCS Bucket Inspection & Canonical PDF Verification (`scripts/setup_reme_datastore.py`) | M2 | `test_f04_gcs_pdf_verification` (5 cases) | `test_f04_gcs_pdf_boundaries` (5 cases) | `test_pair_03`, `test_pair_15` | `test_scenario_11` |
| **F05** | Unstructured OCR Datastore Creation (`ukd-reme-aesp-ds` in `eu`) | M2 | `test_f05_ocr_datastore_creation` (5 cases) | `test_f05_ocr_datastore_boundaries` (5 cases) | `test_pair_03`, `test_pair_04` | `test_scenario_11` |
| **F06** | NDJSON Metadata Generation & Upload (`gs://remedata/documents.jsonl`) | M2 | `test_f06_ndjson_metadata` (5 cases) | `test_f06_ndjson_metadata_boundaries` (5 cases) | `test_pair_04`, `test_pair_15` | `test_scenario_09`, `test_scenario_11` |
| **F07** | Incremental Document Import & Search Verification | M2 | `test_f07_incremental_import` (5 cases) | `test_f07_incremental_import_boundaries` (5 cases) | `test_pair_05` | `test_scenario_11` |
| **F08** | Safe `pixel_mobile_demos` Engine Patching | M2 | `test_f08_safe_engine_patching` (5 cases) | `test_f08_safe_engine_patching_boundaries` (5 cases) | `test_pair_06`, `test_pair_22` | `test_scenario_11`, `test_scenario_12` |
| **F09** | BigQuery Dataset `ukd_reme_demo` Creation (`scripts/seed_demo1_bigquery.py`) | M2 | `test_f09_bq_dataset_creation` (5 cases) | `test_f09_bq_dataset_boundaries` (5 cases) | `test_pair_07` | `test_scenario_10`, `test_scenario_11` |
| **F10** | Table 1: `ipc_nsn_catalogue` Schema, Metadata & Seed Data | M2 | `test_f10_ipc_nsn_catalogue` (5 cases) | `test_f10_ipc_nsn_catalogue_boundaries` (5 cases) | `test_pair_07`, `test_pair_08`, `test_pair_09` | `test_scenario_01`, `test_scenario_02` |
| **F11** | Table 2: `spta_sector_grids` Schema, Metadata & Seed Data | M2 | `test_f11_spta_sector_grids` (5 cases) | `test_f11_spta_sector_grids_boundaries` (5 cases) | `test_pair_10`, `test_pair_11` | `test_scenario_01`, `test_scenario_04`, `test_scenario_05` |
| **F12** | Table 3: `group_chat_tickets` Schema, Metadata & Initial Seed | M2 | `test_f12_group_chat_tickets` (5 cases) | `test_f12_group_chat_tickets_boundaries` (5 cases) | `test_pair_12`, `test_pair_16` | `test_scenario_01`, `test_scenario_06` |
| **F13** | Strict Pydantic v2 Schemas (`app/schemas.py`) | M1 | `test_f13_pydantic_schemas` (5 cases) | `test_f13_pydantic_schema_boundaries` (5 cases) | `test_pair_08`, `test_pair_12`, `test_pair_13` | `test_scenario_01`, `test_scenario_02` |
| **F14** | Pre-Warmed Module Singletons (`app/tools.py`) | M1 | `test_f14_prewarmed_singletons` (5 cases) | `test_f14_prewarmed_singleton_boundaries` (5 cases) | `test_pair_02`, `test_pair_14` | `test_scenario_03`, `test_scenario_08` |
| **F15** | Scene 1 Composite Tool: `diagnose_and_resolve_grid` (`app/tools.py`) | M1 | `test_f15_diagnose_and_resolve_grid` (5 cases) | `test_f15_diagnose_and_resolve_grid_boundaries` (5 cases) | `test_pair_05`, `test_pair_08`, `test_pair_09`, `test_pair_10`, `test_pair_13` | `test_scenario_01`, `test_scenario_02`, `test_scenario_03`, `test_scenario_04`, `test_scenario_05` |
| **F16** | Scene 2 Composite Tool: `publish_ticket_to_chat` (`app/tools.py`) | M1 | `test_f16_publish_ticket_to_chat` (5 cases) | `test_f16_publish_ticket_to_chat_boundaries` (5 cases) | `test_pair_12`, `test_pair_13`, `test_pair_16`, `test_pair_17` | `test_scenario_01`, `test_scenario_02`, `test_scenario_03`, `test_scenario_06` |
| **F17** | `reme_artificer_agent` (`app/agent.py` & `app/__init__.py`) | M1 | `test_f17_reme_artificer_agent` (5 cases) | `test_f17_reme_artificer_agent_boundaries` (5 cases) | `test_pair_14`, `test_pair_18` | `test_scenario_01`, `test_scenario_09` |
| **F18** | Scene 3 FastAPI Group Chat Backend (`cloud_run_chat_app/main.py`) | M3 | `test_f18_fastapi_group_chat_backend` (5 cases) | `test_f18_fastapi_group_chat_boundaries` (5 cases) | `test_pair_16`, `test_pair_17`, `test_pair_20` | `test_scenario_01`, `test_scenario_06`, `test_scenario_07`, `test_scenario_08` |
| **F19** | Tactical Dark-Mode HTML5 UI (`cloud_run_chat_app/templates/index.html`) | M3 | `test_f19_tactical_html5_ui` (5 cases) | `test_f19_tactical_html5_ui_boundaries` (5 cases) | `test_pair_18`, `test_pair_20`, `test_pair_23` | `test_scenario_01`, `test_scenario_07`, `test_scenario_09` |
| **F20** | Unit & FastAPI Integration Test Suite (`tests/unit/test_tools.py`, `tests/unit/test_chat_api.py`) | M1, M3 | `test_f20_unit_test_suite` (5 cases) | `test_f20_unit_test_suite_boundaries` (5 cases) | `test_pair_21` | `test_scenario_10` |
| **F21** | Local Smoke Testing, Browser UI Verification & `agents-cli` Evaluation Suite (`tests/eval/`) | M4 | `test_f21_eval_suite` (5 cases) | `test_f21_eval_suite_boundaries` (5 cases) | `test_pair_21`, `test_pair_24` | `test_scenario_10`, `test_scenario_12` |
| **F22** | Cloud Deployment & Shared Environment Publishing (`scripts/deploy_demo.sh`) | M4, M5 | `test_f22_cloud_deployment_script` (5 cases) | `test_f22_cloud_deployment_boundaries` (5 cases) | `test_pair_19`, `test_pair_22`, `test_pair_24` | `test_scenario_11`, `test_scenario_12` |
