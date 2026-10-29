# TEST_READY.md — Requirement-Driven 4-Tier E2E Test Suite

## 1. Overview & Verification Status
- **Suite Path**: `tests/e2e/`
- **Infrastructure Doc**: `TEST_INFRA.md`
- **Target Specification**: `PROJECT.md § Feature Inventory` (Features F01–F22), `ORIGINAL_REQUEST.md`, `docs/architecture/implementation-plan.md`, and `docs/architecture/Demo 1 - SA.md`
- **Total E2E Test Cases**: **256** (`190 passed`, `66 failed` against current M1–M3 implementation)
  - **Tier 1 (`tests/e2e/test_tier1_features.py`)**: **110** test cases (5 distinct test cases per feature across all 22 features) — `85 passed`, `25 failed`
  - **Tier 2 (`tests/e2e/test_tier2_boundaries.py`)**: **110** test cases (5 distinct boundary/corner test cases per feature across all 22 features) — `88 passed`, `22 failed`
  - **Tier 3 (`tests/e2e/test_tier3_pairwise.py`)**: **24** cross-feature pairwise integration test cases (exceeds >=22 requirement) — `13 passed`, `11 failed`
  - **Tier 4 (`tests/e2e/test_tier4_scenarios.py`)**: **12** real-world tactical sustainment application scenarios (exceeds >=11 requirement) — `4 passed`, `8 failed`

---

## 2. How to Run the E2E Test Suite

Always prefix commands with `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`:

```bash
# Run the complete 4-tier E2E test suite (256 tests)
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/ -v

# Run individual tiers
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier1_features.py -v
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier2_boundaries.py -v
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier3_pairwise.py -v
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier4_scenarios.py -v

# Run unit + E2E test suites together
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v
```

---

## 3. 22-Feature Coverage Checklist (`PROJECT.md § Feature Inventory`)

- [x] **F01**: Root-Level `agents-cli` Project Scaffold & File Preservation (`AGENTS.md`, `docs/`, `app/`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F02**: Sovereign Environment Configuration (`.env` & `.env.example` with `antig-dave`, `europe-west1`, `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`, `eu`, `ukd-reme-aesp-ds`, `ukd_reme_demo`, `pixel-mobile-demos_1793177711952`, `remedata`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F03**: Dependency Configuration (`pyproject.toml` with `google-adk`, `google-genai`, `google-cloud-bigquery`, `google-cloud-storage`, `google-cloud-discoveryengine`, `google-auth`, `requests`, `pydantic`, `fastapi`, `jinja2`, `uvicorn`, `pytest`, `httpx`) — 5 Tier 1 + 5 Tier 2 + Pairwise coverage (**10/10 PASS**)
- [x] **F04**: GCS Source Inspection for `gs://remedata/2350-T-250-523.pdf` (`scripts/setup_reme_datastore.py`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F05**: Discovery Engine Datastore Creation (`ukd-reme-aesp-ds` in `eu` with `CONTENT_REQUIRED`, `ocrParsingConfig.useNativeText=True`, 409 idempotency) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F06**: JSONL Metadata Manifest Generation & Upload (`gs://remedata/documents.jsonl` with structured metadata) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F07**: Discovery Engine Incremental Document Import & Search Verification (`servingConfigs/default_search:search`, `returnSnippet: True`, no `summarySpec`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F08**: Non-Destructive Gemini Enterprise Engine Patch (`pixel-mobile-demos_1793177711952` preserving `jointservicepubs_1793177321711`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F09**: BigQuery Dataset Provisioning (`antig-dave.ukd_reme_demo` in `europe-west1` with dataset description) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F10**: Table 1 `ipc_nsn_catalogue` Schema, Metadata & Seed Data (8 described columns, 6 FV432/K60 rows including `5360-99-812-1740`, 5 Jackal 2 rows including `5330-99-812-4410`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F11**: Table 2 `spta_sector_grids` Schema, Metadata & Seed Data (5 described columns, 5 rows including `bravo-4` -> `51.2185, -1.7925`, `alpha-1` -> `51.2310, -1.8150`, `london` -> `51.5007, -0.1246`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F12**: Table 3 `group_chat_tickets` Schema, Metadata & Seed Data (13 described columns, baseline `TKT-REME-041` row, 100% column description coverage across all 26 columns) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F13**: Strict Pydantic v2 Schemas (`ActiveTicketState` & `TicketPayload` in `app/schemas.py`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**4/10 PASS — 6 fail due to `app/schemas.py` contract defects**)
- [x] **F14**: Pre-Warmed Module Singletons & Zero-Subprocess Auth (`_BQ_CLIENT`, `_CREDENTIALS`, zero `subprocess`/`gcloud` calls in `app/tools.py`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**8/10 PASS — 2 fail due to golden fallback constants & unparameterized SQL in `app/tools.py`**)
- [x] **F15**: Scene 1 Consolidated Tool `diagnose_and_resolve_grid` (`pageSize: 15`, `returnSnippet: True`, no `summarySpec`, HTML `<b>`/`</b>` stripping, golden fallbacks, `tool_context.state["active_ticket"]`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**0/10 PASS — 10 fail due to `app/tools.py` nested return dict, wrong BQ table names, and wrong golden NSNs**)
- [x] **F16**: Scene 2 Tool `publish_ticket_to_chat` (`TKT-REME-XXXX`, `https://www.google.com/maps/dir/?api=1&destination=51.2185,-1.7925&travelmode=driving`, Cloud Run POST, BigQuery 13-column `insert_rows_json`, confirmation badge) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**0/10 PASS — 10 fail due to `app/tools.py` missing stateless fallback, wrong ticket ID prefix, and missing `published`/`confirmation_badge` keys**)
- [x] **F17**: ADK Root Agent `reme_artificer_agent` (`gemini-2.5-flash`, `temperature=0.0`, 15s voice persona, Chip 1/2/3 prompts, washer safety guardrail) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**6/10 PASS — 4 fail due to missing Scene 2 Markdown card & washer prohibition in `app/agent.py`**)
- [x] **F18**: Cloud Run Group Chat FastAPI Backend (`GET /`, `GET /api/tickets` `<20ms`, `POST /api/tickets`, `POST /api/reset` & `POST /api/tickets/reset` `<1s`, `Dockerfile` on port 8080) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**3/10 PASS — 7 fail due to `cloud_run_chat_app/main.py` returning 201/`created`, resetting to `INITIAL_SEED_TICKET`, and running slow BQ DELETE**)
- [x] **F19**: Tactical Dark-Mode HTML5 Frontend (`OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT`, `#0b0f19` theme, 1000ms polling, `maps/dir/?api=1&destination=` & `maps/search/?api=1&query=` links, reset button) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**10/10 PASS**)
- [x] **F20**: Unit Test Suite (`tests/unit/test_tools.py` & `tests/unit/test_chat_api.py`) — 5 Tier 1 + 5 Tier 2 coverage (**10/10 PASS**)
- [x] **F21**: `agents-cli` Evaluation Dataset & Runner (`tests/eval/datasets/basic-dataset.json` with `eval_cases` & `tests/eval/eval_config.yaml`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**5/10 PASS — 5 fail due to wrong NSNs and only 2 eval cases in `basic-dataset.json`**)
- [x] **F22**: Idempotent Cloud Deployment & Gemini Enterprise Registration Script (`scripts/deploy_demo.sh` with `sa-reme-demo@antig-dave.iam.gserviceaccount.com`, Cloud Run `reme-chat-demonstrator`, `agents-cli deploy` without `--no-confirm-project`, `agents-cli publish gemini`) — 5 Tier 1 + 5 Tier 2 + Pairwise/Scenario coverage (**7/10 PASS — 3 fail due to service name/flags in `scripts/deploy_demo.sh`**)

---

## 4. Escalated Implementation Defects (`worker_core_m1_m3`)

All 66 failing tests trace directly to 6 implementation contract discrepancies in `worker_core_m1_m3`'s files against `PROJECT.md`:

1. **BigQuery Table Name & Parameterized Query Mismatch (`app/tools.py:238–298`)**:
   - `app/tools.py` queries `ukd_reme_demo.parts_inventory` (404 Not Found in BigQuery) and `ukd_reme_demo.training_area_grids` (404 Not Found in BigQuery) using unparameterized f-string SQL instead of `ukd_reme_demo.ipc_nsn_catalogue` and `ukd_reme_demo.spta_sector_grids` with `bigquery.ScalarQueryParameter` (`@query`, `@grid`) (`PROJECT.md § Interface Contracts 3 & Feature 15`).
2. **Golden Fallback Constants Mismatch (`app/tools.py:68–109`)**:
   - `GOLDEN_FALLBACK_K60` uses NSN `2930-99-801-4421` (`Rolls-Royce K60 Coolant Pump & Relief Valve Assembly`) instead of `5360-99-812-1740` (`Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)`, `AESP 2350-T-250-523 (Ch 1-2, Para 17.4, Page 14)`, limits `79.4 mm` / `54.6 mm` / `do NOT pack with washers`).
   - `GOLDEN_FALLBACK_JACKAL` uses NSN `2910-99-742-9910` (`Cummins ISBe Fuel Filter`) instead of `5330-99-812-4410` (`Hydraulic Manifold High-Pressure Seal Kit`, `AESP 2320-J-100-522 (Para 4.12)`, `250 bar`).
   - `GOLDEN_FALLBACK_GRID` uses `51.2093, -1.7862` instead of `51.2185, -1.7925` (`51.2185° N, 1.7925° W (Salisbury Plain — Sector Bravo-4)`).
3. **Pydantic Schemas (`app/schemas.py`) & Tool Return Contract (`app/tools.py`)**:
   - `ActiveTicketState` in `app/schemas.py` is missing `rag_snippets: list[str] = Field(default_factory=list)` (`PROJECT.md` line 99).
   - `TicketPayload` in `app/schemas.py` sets `status: str = "OPEN — AWAITING FRT DISPATCH"` instead of `"DISPATCH_READY"` (`PROJECT.md` line 114) and requires `callsign: str` without default `"Cpl MacDonald (4 Bn REME FRT)"` (`PROJECT.md` line 103).
   - `diagnose_and_resolve_grid` in `app/tools.py` returns nested `{"status": ..., "diagnosis": {...}, "location": {...}}` instead of a flat dict matching `ActiveTicketState.model_dump()`, and includes `tool_context:` in its docstring (`PROJECT.md` lines 123–128).
   - `publish_ticket_to_chat` in `app/tools.py` returns `{"status": "ERROR"}` when `tool_context.state` has no `"active_ticket"` instead of falling back to `{**GOLDEN_FALLBACK_K60, **GOLDEN_FALLBACK_GRID}` (`PROJECT.md` line 133), generates `REME-XXXX` instead of `TKT-REME-XXXX`, and omits `"published": True` and `"confirmation_badge": "✅ Ticket TKT-REME-XXXX Published to 4 Bn REME Group Chat"` (`PROJECT.md` line 135).
4. **Agent System Instruction (`app/agent.py`)**:
   - Missing Scene 2 Native Structured Markdown Card rules (`### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card`, `🔊 **15s Audio Brief:**`, 3 `<details open>` collapsible sections, Chip 1/2/3 summaries, and warning against packing washers) (`PROJECT.md` line 48).
5. **FastAPI Group Chat Contract (`cloud_run_chat_app/main.py`)**:
   - `POST /api/tickets` returns HTTP `201` with `{"status": "created"}` instead of HTTP `200` with `{"status": "published", "ticket": ...}` (`PROJECT.md` line 140), and updates duplicate `ticket_id` in-place rather than moving it to index 0.
   - `POST /api/reset` resets `ACTIVE_TICKETS` to `[INITIAL_SEED_TICKET]` (`REME-8801`) and runs a synchronous BigQuery `DELETE` query (which fails on streaming buffer rows and takes >1.6s) instead of clearing `ACTIVE_TICKETS` (`{"status": "reset", "tickets": []}`) in `<1s` (`PROJECT.md` line 141).
6. **Eval Dataset & Deploy Script (`tests/eval/datasets/basic-dataset.json`, `scripts/deploy_demo.sh`)**:
   - `tests/eval/datasets/basic-dataset.json` has only 2 cases (missing the 3rd publish case) and uses wrong NSNs (`2930-99-801-4421` and `2910-99-742-9910`) instead of `5360-99-812-1740`, `5330-99-812-4410`, and `publish_ticket_to_chat` (`PROJECT.md` line 52).
   - `scripts/deploy_demo.sh` uses `CHAT_SERVICE_NAME="reme-sustainment-chat"` instead of `"reme-chat-demonstrator"`, `--app-id` instead of `--gemini-enterprise-app-id`, and omits `sa-reme-demo@antig-dave.iam.gserviceaccount.com` and `--min-instances 1 --max-instances 1` (`PROJECT.md` line 53).
