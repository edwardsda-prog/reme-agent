# Project: UK Defence REME Artificer Demonstrator (`@REME-Artificer` — Demo 1)

## Architecture

### Overview
Single-agent ADK 2.0 tactical sustainment demonstrator (`reme_artificer_agent`, `gemini-2.5-flash`, `temperature=0.0`) for **4 Battalion REME (Royal Electrical and Mechanical Engineers)** operating on **Salisbury Plain Training Area (SPTA)**. The system combines:
1. **Unstructured OCR RAG (`eu` multi-region)**: Discovery Engine datastore `ukd-reme-aesp-ds` indexing `gs://remedata/2350-T-250-523.pdf` (`AESP 2350-T-250-523`) and bound non-destructively to the shared Gemini Enterprise engine `pixel_mobile_demos` (`pixel-mobile-demos_1793177711952`) alongside the existing `jointservicepubs` (`jointservicepubs_1793177321711`) datastore.
2. **Structured Grounding & Audit Persistence (`europe-west1` Belgium)**: BigQuery dataset `antig-dave.ukd_reme_demo` containing 3 tables with 100% table-level and column-level `description` metadata: `ipc_nsn_catalogue`, `spta_sector_grids`, and `group_chat_tickets`.
3. **ADK 2.0 Agent & Stage-Proof Composite Tools (`europe-west1` Belgium)**:
   - `app/schemas.py`: Strict Pydantic v2 models (`ActiveTicketState`, `TicketPayload`).
   - `app/tools.py`: Module-level pre-warmed `_BQ_CLIENT` and `_CREDENTIALS` singletons (zero `gcloud` subprocess calls), `diagnose_and_resolve_grid` (single-pass `pageSize: 15`, `snippetSpec: {"returnSnippet": True}`, no `summarySpec`, HTML `<b>`/`</b>` stripping, parameterized SQL, deterministic Golden-Path Fallbacks for K60 `5360-99-812-1740`, Jackal 2 `5330-99-812-4410`, and Sector Bravo-4 `51.2185, -1.7925`), and `publish_ticket_to_chat`.
   - `app/agent.py`: `reme_artificer_agent` (`LlmAgent`, `gemini-2.5-flash`, `temperature=0.0`) rendering the Scene 2 Native Structured Markdown Card (15s Audio Brief + 3 `<details open>` chips) and Scene 2 publish confirmation badge.
4. **Scene 3 Live Group Chat Receiver (`europe-west1` Cloud Run)**: FastAPI + dark-mode tactical HTML5 web app (`cloud_run_chat_app/`, Cloud Run service `reme-chat-demonstrator`) with `<20ms` in-memory `ACTIVE_TICKETS`, `GET /`, `GET/POST /api/tickets`, `<1s` `POST /api/reset`, 1000ms live polling, and 1-tap Google Maps Universal URL buttons (`https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving` and `https://www.google.com/maps/search/?api=1&query={lat},{lng}`).

### Mandatory Environment & Identity Constraints
- **GCP Project**: `antig-dave` (Project Number `284046449012`)
- **Active Account**: `admin@edwardsda.altostrat.com` (NEVER use `edwardsda@google.com`)
- **Runtime Service Account**: `sa-reme-demo@antig-dave.iam.gserviceaccount.com`
- **mTLS Guardrail**: Always set `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` in `.env` and shell environment.
- **Regional Residency**:
  - `europe-west1` (Belgium): Vertex AI (`gemini-2.5-flash`), Agent Engine (`agent_runtime`), Agent Registry, Cloud Run (`reme-chat-demonstrator`), BigQuery (`ukd_reme_demo`).
  - `eu` Multi-Region (`https://eu-discoveryengine.googleapis.com/v1alpha/...`): Discovery Engine datastore `ukd-reme-aesp-ds` and Gemini Enterprise engine `pixel_mobile_demos` (actual resource ID: `pixel-mobile-demos_1793177711952`, with existing datastore ID `jointservicepubs_1793177321711`).

---

## Feature Inventory

Every feature from the Phase 0 Survey is assigned to an explicit implementation milestone below. No feature is left unassigned.

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Root-level `agents-cli` ADK 2.0 Scaffolding | Scaffold `reme-artificer-agent` via `agents-cli scaffold create` in `/tmp`, copy to workspace root preserving `AGENTS.md` and `docs/`, run `agents-cli scaffold enhance . --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md`, create `SPEC.md`, and verify `agents-cli info`. | M1 | survey |
| 2 | EU / Belgium Environment Configuration (`.env` & `.env.example`) | Configure `.env` and `.env.example` with `GOOGLE_CLOUD_PROJECT=antig-dave`, `GOOGLE_CLOUD_LOCATION=europe-west1`, `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`, `BQ_DATASET=ukd_reme_demo`, `BQ_LOCATION=europe-west1`, `DISCOVERY_ENGINE_LOCATION=eu`, `VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds`, `GEMINI_APP_ID`, `GCS_SOURCE_BUCKET=remedata`, `CLOUD_RUN_CHAT_URL`. | M1 | survey |
| 3 | Python Dependency Management (`pyproject.toml` & `uv sync`) | Configure `pyproject.toml` with `google-adk>=2.0.0`, `google-genai`, `google-cloud-bigquery`, `google-cloud-discoveryengine`, `google-cloud-storage`, `fastapi`, `uvicorn[standard]`, `jinja2`, `requests`, `httpx`, `pydantic>=2.0.0`, `pytest` and run `uv sync`. | M1 | survey |
| 4 | GCS Bucket Inspection & Canonical PDF Verification (`scripts/setup_reme_datastore.py`) | Inspect `gs://remedata` in `antig-dave` and verify `gs://remedata/2350-T-250-523.pdf` (`6.19 MiB`) is present. | M2 | survey |
| 5 | Unstructured OCR Datastore Creation (`ukd-reme-aesp-ds` in `eu`) | Create datastore `ukd-reme-aesp-ds` in `location=eu` with `CONTENT_REQUIRED` and `ocrParsingConfig.useNativeText = True` (handling HTTP 409 idempotently). | M2 | survey |
| 6 | NDJSON Metadata Generation & Upload (`gs://remedata/documents.jsonl`) | Generate rich NDJSON metadata (`id`, `jsonData` with `title`, `aesp_reference`, `chapter_paragraph`, `equipment_platform`, `component`, `ipc_army_code`, `nsn`, `security_classification`, `unit`, and `content.uri`) and upload to `gs://remedata/documents.jsonl`. | M2 | survey |
| 7 | Incremental Document Import & Search Verification | Trigger `branches/0/documents:import` (`reconciliationMode: "INCREMENTAL"`), poll LRO, and verify search on `ukd-reme-aesp-ds`. | M2 | survey |
| 8 | Safe `pixel_mobile_demos` Engine Patching | Resolve `pixel_mobile_demos` (`pixel-mobile-demos_1793177711952`) in `eu`, GET existing `dataStoreIds` (`["jointservicepubs_1793177321711"]`), and PATCH `?updateMask=dataStoreIds` with union preserving `jointservicepubs_1793177321711` alongside `ukd-reme-aesp-ds`. | M2 | survey |
| 9 | BigQuery Dataset `ukd_reme_demo` Creation (`scripts/seed_demo1_bigquery.py`) | Provision `antig-dave.ukd_reme_demo` in `location="europe-west1"` with explicit dataset `description`. | M2 | survey |
| 10 | Table 1: `ipc_nsn_catalogue` Schema, Metadata & Seed Data | Create table with 8 `REQUIRED` `STRING` columns, explicit table & column descriptions, and seed 6 K60 rows (`5360-99-812-1740`) + 5 Jackal 2 rows (`5330-99-812-4410`). | M2 | survey |
| 11 | Table 2: `spta_sector_grids` Schema, Metadata & Seed Data | Create table with 5 `REQUIRED` columns (`sector_key`, `sector_display_name`, `latitude`, `longitude`, `coords_label`), explicit table & column descriptions, and seed Bravo-4 (`bravo-4`, `bravo 4`, `su 1482 4621` -> `51.2185, -1.7925`), Alpha-1 (`51.2310, -1.8150`), and London (`51.5007, -0.1246`). | M2 | survey |
| 12 | Table 3: `group_chat_tickets` Schema, Metadata & Initial Seed | Create table with 13 `REQUIRED` columns, explicit table & column descriptions, and seed initial baseline ticket (`TKT-REME-041`). | M2 | survey |
| 13 | Strict Pydantic v2 Schemas (`app/schemas.py`) | Implement `ActiveTicketState` and `TicketPayload` with strict types (no `any`). | M1 | survey |
| 14 | Pre-Warmed Module Singletons (`app/tools.py`) | Initialize `_BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location="europe-west1")` and `_CREDENTIALS, _ = google.auth.default()` at module import time; zero `gcloud` subprocess calls. | M1 | survey |
| 15 | Scene 1 Composite Tool: `diagnose_and_resolve_grid` (`app/tools.py`) | Single-pass EU Discovery Engine search (`pageSize: 15`, `snippetSpec: {"returnSnippet": True}`, NO `summarySpec`, strip `<b>`/`</b>`) + parameterized BQ queries on `ipc_nsn_catalogue` and `spta_sector_grids` + writes `tool_context.state["active_ticket"]` + Golden-Path Fallbacks (`GOLDEN_FALLBACK_K60`, `GOLDEN_FALLBACK_JACKAL`, `GOLDEN_FALLBACK_GRID`). | M1 | survey |
| 16 | Scene 2 Composite Tool: `publish_ticket_to_chat` (`app/tools.py`) | Reads `tool_context.state.get("active_ticket")` (or falls back to K60 + Bravo-4), builds `TicketPayload`, POSTs to `{CLOUD_RUN_CHAT_URL}/api/tickets`, and inserts the 13 table columns into `ukd_reme_demo.group_chat_tickets`. | M1 | survey |
| 17 | `reme_artificer_agent` (`app/agent.py` & `app/__init__.py`) | Single ADK 2.0 `LlmAgent` (`name="reme_artificer_agent"`, `model="gemini-2.5-flash"`, `temperature=0.0`) exported as `root_agent`, rendering the Scene 2 Native Structured Markdown Card (15s Audio Brief + 3 `<details open>` chips) and Scene 2 publish confirmation badge. | M1 | survey |
| 18 | Scene 3 FastAPI Group Chat Backend (`cloud_run_chat_app/main.py`) | Serves HTML UI (`GET /`), returns `<20ms` in-memory `ACTIVE_TICKETS` (`GET /api/tickets`), accepts tickets (`POST /api/tickets` + async BQ insert), and clears in-memory tickets (`POST /api/reset` in `<1s`). | M3 | survey |
| 19 | Tactical Dark-Mode HTML5 UI (`cloud_run_chat_app/templates/index.html`) | Ruggedised high-contrast dark UI (`OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT`), `[Reset Demo]` button, 1000ms live polling of `/api/tickets`, and 1-tap Google Maps Universal URL buttons (`maps/dir/?api=1&destination=...` and `maps/search/?api=1&query=...`). | M3 | survey |
| 20 | Unit & FastAPI Integration Test Suite (`tests/unit/test_tools.py`, `tests/unit/test_chat_api.py`) | Pytest unit & integration tests verifying `diagnose_and_resolve_grid`, `publish_ticket_to_chat`, Golden-Path Fallbacks, HTML stripping, and FastAPI `/`, `/api/tickets`, `/api/reset`. | M1, M3 | survey |
| 21 | Local Smoke Testing, Browser UI Verification & `agents-cli` Evaluation Suite (`tests/eval/`) | Local smoke test (`agents-cli run` Scene 1 & Scene 2), browser UI verification on `http://localhost:8080`, and `agents-cli eval run` against `tests/eval/datasets/basic-dataset.json` (K60, Jackal 2, and Publish to Group Chat). | M4 | survey |
| 22 | Cloud Deployment & Shared Environment Publishing (`scripts/deploy_demo.sh`) | Provision `sa-reme-demo@antig-dave.iam.gserviceaccount.com` + IAM roles, deploy `reme-chat-demonstrator` to Cloud Run (`europe-west1`), deploy `reme_artificer_agent` to Agent Engine (`europe-west1`) via `agents-cli deploy`, verify Agent Registry (`gcloud agent-registry agents list`), and publish `"REME-Artificer"` to `pixel_mobile_demos` (`pixel-mobile-demos_1793177711952`) preserving existing agents and datastores; followed by full E2E & Tier 5 adversarial verification. | M4, M5 | survey |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Workspace Scaffolding, ADK 2.0 Core & Tool Unit Tests | Features 1, 2, 3, 13, 14, 15, 16, 17, 20 (tools): Root `agents-cli` scaffold, `.env`/`.env.example`, `SPEC.md`, `pyproject.toml`, `uv sync`, `app/schemas.py`, `app/tools.py`, `app/agent.py`, `app/fast_api_app.py`, `tests/unit/test_tools.py`. | none | DONE |
| M2 | Discovery Engine (`ukd-reme-aesp-ds`) & BigQuery (`ukd_reme_demo`) Provisioning | Features 4, 5, 6, 7, 8, 9, 10, 11, 12: Implement & run `scripts/setup_reme_datastore.py` (`gs://remedata/documents.jsonl`, `ukd-reme-aesp-ds` in `eu`, safe `pixel-mobile-demos_1793177711952` patch preserving `jointservicepubs_1793177321711`) and `scripts/seed_demo1_bigquery.py` (`ukd_reme_demo` in `europe-west1` with full table & column descriptions). | none | DONE |
| M3 | Scene 3 Cloud Run Tactical Group Chat App (`cloud_run_chat_app/`) & API Unit Tests | Features 18, 19, 20 (chat API): Implement `cloud_run_chat_app/main.py`, `cloud_run_chat_app/templates/index.html`, `cloud_run_chat_app/Dockerfile`, `cloud_run_chat_app/requirements.txt`, and `tests/unit/test_chat_api.py`. | none | DONE |
| M4 | Local Smoke Verification, Browser UI, Agent Evaluation & Cloud Deployment | Features 21, 22: Implement `tests/eval/eval_config.yaml`, `tests/eval/datasets/basic-dataset.json`, `scripts/deploy_demo.sh`; run local smoke (`agents-cli run`) + browser UI verification (`http://localhost:8080`), run `agents-cli eval run`, deploy `reme-chat-demonstrator` to Cloud Run (`europe-west1`), deploy `reme_artificer_agent` to Agent Engine (`europe-west1`), verify Agent Registry, and publish `"REME-Artificer"` to `pixel_mobile_demos` (`pixel-mobile-demos_1793177711952`). | M1, M2, M3 | DONE (`4a818072-9bb4-4e2a-9792-c997bc1edabb`: 264/264 tests pass, eval 1.0000, Cloud Run `https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`, Agent Engine `6397856951400660992`, Gemini Enterprise `10995513697759164495`) |
| M5 | Final Milestone: E2E Test Suite Pass (Tiers 1-4) & Adversarial Coverage Hardening (Tier 5) | Feature 22 (Final E2E & Hardening): Phase 1 passes 100% of E2E tests in `tests/e2e/` (`TEST_READY.md`); Phase 2 runs Tier 5 white-box adversarial coverage hardening (`test-coverage-audit`). | M1, M2, M3, M4, E2E Track | DONE (295/295 tests passing: 8/8 unit + 256/256 Tiers 1-4 E2E + 31/31 Tier 5 Adversarial; Iteration 2 Gate PASS: `c0141f2f`, `27c5181b`, `0c30cba5`, `88245d92` `APPROVE`, `8aaf80e4` `CLEAN`) |
| E2E | E2E Testing Track (`TEST_INFRA.md`, `tests/e2e/`, `TEST_READY.md`) | Requirement-driven opaque-box 4-tier E2E test suite covering all 22 features (Tier 1 >=5/feature, Tier 2 >=5/feature, Tier 3 pairwise, Tier 4 real-world scenarios). | none | DONE (256 tests in `tests/e2e/`, `TEST_READY.md` published) |

---

## Interface Contracts

### 1. Environment Variables (`.env` & `.env.example`)
```ini
GOOGLE_CLOUD_PROJECT=antig-dave
GCP_PROJECT_ID=antig-dave
GOOGLE_CLOUD_LOCATION=europe-west1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_API_USE_CLIENT_CERTIFICATE=false
BQ_DATASET=ukd_reme_demo
BQ_LOCATION=europe-west1
DISCOVERY_ENGINE_LOCATION=eu
VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds
GEMINI_APP_ID=projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952
GCS_SOURCE_BUCKET=remedata
CLOUD_RUN_CHAT_URL=http://localhost:8080
```

### 2. Pydantic Schemas (`app/schemas.py`) ↔ Tools (`app/tools.py`) ↔ Chat App (`cloud_run_chat_app/main.py`)
- **`ActiveTicketState(BaseModel)`**:
  - `repair_classification: str`
  - `aesp_reference: str`
  - `part_name: str`
  - `nsn: str`
  - `technical_limits: str`
  - `sector_display_name: str`
  - `latitude: float`
  - `longitude: float`
  - `coords_label: str`
  - `rag_snippets: list[str] = Field(default_factory=list)`
- **`TicketPayload(BaseModel)`**:
  - `ticket_id: str`
  - `created_at_utc: str`
  - `callsign: str = "Cpl MacDonald (4 Bn REME FRT)"`
  - `repair_classification: str`
  - `aesp_reference: str`
  - `part_name: str`
  - `nsn: str`
  - `technical_limits: str`
  - `sector_display_name: Optional[str] = "Salisbury Plain (SPTA) — Sector Bravo-4"`
  - `coords_label: str`
  - `latitude: float`
  - `longitude: float`
  - `google_maps_url: str`
  - `status: str = "DISPATCH_READY"`

### 3. BigQuery Tables (`antig-dave.ukd_reme_demo` in `europe-west1`)
- **`ipc_nsn_catalogue`** (8 `REQUIRED` `STRING` columns, all with `description`):
  - `part_id`, `keyword_tag`, `ipc_army_code`, `aesp_reference`, `part_name`, `nsn`, `repair_classification`, `technical_limits`
- **`spta_sector_grids`** (5 `REQUIRED` columns, all with `description`):
  - `sector_key` (`STRING`), `sector_display_name` (`STRING`), `latitude` (`FLOAT64`), `longitude` (`FLOAT64`), `coords_label` (`STRING`)
- **`group_chat_tickets`** (13 `REQUIRED` columns, all with `description`):
  - `ticket_id` (`STRING`), `created_at_utc` (`TIMESTAMP`), `callsign` (`STRING`), `repair_classification` (`STRING`), `aesp_reference` (`STRING`), `part_name` (`STRING`), `nsn` (`STRING`), `technical_limits` (`STRING`), `coords_label` (`STRING`), `latitude` (`FLOAT64`), `longitude` (`FLOAT64`), `google_maps_url` (`STRING`), `status` (`STRING`)
  - **CRITICAL**: When inserting a `TicketPayload` dict into `group_chat_tickets` via `insert_rows_json`, strip `sector_display_name` (or filter strictly to the 13 column names above) so BigQuery does not reject extra fields.

### 4. ADK 2.0 Composite Tools (`app/tools.py`) ↔ Agent (`app/agent.py`)
- `diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext) -> dict`:
  - No default parameter values in function signature; omit `tool_context` from docstring.
  - Queries `https://eu-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/servingConfigs/default_search:search` with `{"query": fault_query, "pageSize": 15, "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}}` (NO `summarySpec`), strips `<b>` and `</b>` tags.
  - Queries `ipc_nsn_catalogue` and `spta_sector_grids` in `europe-west1` with parameterized SQL (`@query`, `@grid`).
  - Falls back to `GOLDEN_FALLBACK_JACKAL` (`5330-99-812-4410`) if `"409"` or `"jackal"` in `fault_query.lower()`, else `GOLDEN_FALLBACK_K60` (`5360-99-812-1740`), and `GOLDEN_FALLBACK_GRID` (`51.2185, -1.7925`).
  - Writes `tool_context.state["active_ticket"]` and returns the dict.
- `publish_ticket_to_chat(tool_context: ToolContext) -> dict`:
  - Reads `tool_context.state.get("active_ticket")` or merges `{**GOLDEN_FALLBACK_K60, **GOLDEN_FALLBACK_GRID}`.
  - POSTs `TicketPayload` JSON to `{CLOUD_RUN_CHAT_URL}/api/tickets` (`timeout=2.0`) and inserts the 13 table columns into `ukd_reme_demo.group_chat_tickets`.
  - Returns `{"published": True, "ticket": payload_dict, "confirmation_badge": f"✅ Ticket {ticket_id} Published to 4 Bn REME Group Chat"}`.

### 5. FastAPI Group Chat Receiver (`cloud_run_chat_app/main.py`)
- `GET /` -> `200 OK` HTML (`templates/index.html`)
- `GET /api/tickets` -> `200 OK` `{"tickets": ACTIVE_TICKETS}` (`<20ms` in-memory read)
- `POST /api/tickets` -> `200 OK` `{"status": "published", "ticket": ticket_dict}` (prepends to `ACTIVE_TICKETS`)
- `POST /api/reset` (and alias `POST /api/tickets/reset`) -> `200 OK` `{"status": "reset", "tickets": []}` (`<1s` in-memory clear)

---

## Code Layout

```text
/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/
├── AGENTS.md                        # Preserved untouched (Read-only)
├── PROJECT.md                       # Project Orchestrator global index
├── SPEC.md                          # [M1] Authoritative specification summary
├── .env.example                     # [M1] Template environment variables
├── .env                             # [M1/M4] Local & deployment environment variables
├── pyproject.toml                   # [M1] Root Python dependencies & pytest config
├── uv.lock                          # [M1] Locked dependencies
├── Dockerfile                       # [M1] Root Agent Runtime container build file
├── agents-cli-manifest.yaml         # [M1] agents-cli manifest (alongside .agents.yaml)
├── .agents.yaml                     # [M1] agents-cli v1.12.0 config
├── docs/
│   └── architecture/
│       ├── Demo 1 - SA.md           # Preserved untouched (Read-only)
│       └── implementation-plan.md   # Preserved untouched (Read-only)
├── app/                             # [M1] Exclusive write ownership: Milestone 1
│   ├── __init__.py
│   ├── agent.py
│   ├── fast_api_app.py
│   ├── schemas.py
│   └── tools.py
├── scripts/                         # [M2 & M4] Write ownership split by file:
│   ├── setup_reme_datastore.py      # [M2] Exclusive write ownership: Milestone 2
│   ├── seed_demo1_bigquery.py       # [M2] Exclusive write ownership: Milestone 2
│   └── deploy_demo.sh               # [M4] Exclusive write ownership: Milestone 4
├── cloud_run_chat_app/              # [M3] Exclusive write ownership: Milestone 3
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── templates/
│       └── index.html
├── tests/
│   ├── unit/
│   │   ├── test_tools.py            # [M1] Exclusive write ownership: Milestone 1
│   │   └── test_chat_api.py         # [M3] Exclusive write ownership: Milestone 3
│   ├── eval/                        # [M4] Exclusive write ownership: Milestone 4
│   │   ├── eval_config.yaml
│   │   └── datasets/
│   │       └── basic-dataset.json
│   └── e2e/                         # [E2E Track] Exclusive write ownership: E2E Testing Track
├── TEST_INFRA.md                    # [E2E Track] Exclusive write ownership: E2E Testing Track
└── TEST_READY.md                    # [E2E Track] Exclusive write ownership: E2E Testing Track
```
