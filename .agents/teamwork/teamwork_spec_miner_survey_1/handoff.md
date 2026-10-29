# Handoff Report — Specification Mining Part 1 (`teamwork_spec_miner_survey_1`)

## 1. Observation

Direct inspection of the repository and authoritative specification documents yielded the following exact findings:

1. **Workspace Root (`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`)**:
   - Currently contains only `.agents/`, `AGENTS.md` (lines 1–25, 1,590 bytes), and `docs/architecture/` containing `Demo 1 - SA.md` (lines 1–336, 32,221 bytes) and `implementation-plan.md` (lines 1–328, 28,667 bytes).
   - No ADK scaffold files (`app/`, `scripts/`, `cloud_run_chat_app/`, `tests/`, `pyproject.toml`, `agents-cli-manifest.yaml`, `.env`) exist yet.
2. **Authoritative Implementation Plan (`docs/architecture/implementation-plan.md`, lines 1–328)**:
   - Defines the end-to-end architecture, directory layout (Section 2, lines 46–84), and step-by-step implementation across Phases 1–6 (Section 3, lines 88–317; plus sub-phases 6.1 Unit Tests, 6.2 Local Smoke & Browser UI, 6.3 Agent Evaluation, and 6.4 Cloud Deployment & Publishing, which together form the 8 logical execution phases referenced in `ORIGINAL_REQUEST.md` line 5).
   - Enforces strict regional separation:
     - **Belgium (`europe-west1`)**: Vertex AI (`gemini-2.5-flash`), Agent Engine (`agent_runtime`), Agent Registry, Cloud Run (`reme-chat-demonstrator`), and BigQuery (`ukd_reme_demo`) (`implementation-plan.md` lines 7, 18–22).
     - **EU Multi-Region (`eu`)**: Discovery Engine Datastore (`ukd-reme-aesp-ds`) and Gemini Enterprise App (`pixel_mobile_demos`) via `https://eu-discoveryengine.googleapis.com/v1alpha/...` (`implementation-plan.md` lines 8, 23–25).
3. **Solutions Architecture Reference (`docs/architecture/Demo 1 - SA.md`, lines 1–336)**:
   - Document ID `SDD-DEMO1-ADK2-003` provides exact SQL queries, Golden-Path Fallback dictionaries (`GOLDEN_FALLBACK_K60`, `GOLDEN_FALLBACK_GRID`), secondary Jackal 2 seed row values (Section 4.1, lines 127–135), Scene 2 Native Structured Markdown Card template (Section 5.1, lines 148–173), and reference tool implementations (Section 6.2, lines 217–324).
4. **Original User Request (`ORIGINAL_REQUEST.md`, lines 1–54)**:
   - Specifies Requirements R1–R5 and Acceptance Criteria across Workspace/Datastore/BigQuery, Agent/Tools/Local Verification, and Cloud Deployment/Shared Environment Safety.
   - Mandates active GCP account `admin@edwardsda.altostrat.com` (NEVER `edwardsda@google.com`), runtime Service Account `sa-reme-demo@antig-dave.iam.gserviceaccount.com`, and `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` in `.env` and shell environment (`ORIGINAL_REQUEST.md` lines 30, 40, 51).

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Workspace & Config | Root-level `agents-cli` ADK 2.0 Scaffolding | Scaffold `reme-artificer-agent` into `/tmp` and copy into workspace root while preserving `AGENTS.md` and `docs/`, then run `agents-cli scaffold enhance` for `agent_runtime` in `europe-west1` | `agents-cli scaffold create` & `agents-cli scaffold enhance` CLI args | `app/`, `tests/`, `pyproject.toml`, `Dockerfile`, `agents-cli-manifest.yaml` recognized by `agents-cli info` | Fails if `AGENTS.md` or `docs/` overwritten or if region != `europe-west1` | `implementation-plan.md:27-29,90-98` |
| 2 | Workspace & Config | EU / Belgium Environment Configuration (`.env` & `.env.example`) | Configure 12 mandatory environment variables enforcing `europe-west1` compute/BQ, `eu` Discovery Engine, and `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` | Key-value environment configuration | `.env` and `.env.example` loaded by `uv`, `agents-cli`, and Python scripts | Mismatched region or missing `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` causes mTLS/regional errors | `implementation-plan.md:99-113`, `ORIGINAL_REQUEST.md:18,30` |
| 3 | Workspace & Config | Python Dependency Management (`pyproject.toml` & `uv sync`) | Install ADK 2.0, BigQuery, Discovery Engine, Storage, FastAPI, Uvicorn, Jinja2, Requests, HTTPX, and Pytest via `uv` | `pyproject.toml` dependency list | Synced `.venv` and `uv.lock` | `uv sync` exits non-zero on version conflict | `implementation-plan.md:114-116` |
| 4 | Discovery Engine Pipeline | GCS Bucket Inspection & Canonical PDF Verification (`scripts/setup_reme_datastore.py`) | Inspect `gs://remedata` in `antig-dave` for PDFs (specifically `2350-T-250-523.pdf`) and upload/verify if absent | `gs://remedata` bucket in `antig-dave` | Verified PDF blob(s) in `gs://remedata` | Uploads or raises explicit error if source PDF unavailable | `implementation-plan.md:121-123`, `ORIGINAL_REQUEST.md:20-21` |
| 5 | Discovery Engine Pipeline | Unstructured OCR Datastore Creation (`ukd-reme-aesp-ds` in `eu`) | Create Discovery Engine datastore `ukd-reme-aesp-ds` in `eu` multi-region with `CONTENT_REQUIRED` and `ocrParsingConfig.useNativeText = true` | `POST .../locations/eu/collections/default_collection/dataStores?dataStoreId=ukd-reme-aesp-ds` | Created datastore resource in `eu` | If datastore already exists (HTTP 409), handle idempotently and proceed to import | `implementation-plan.md:124-141` |
| 6 | Discovery Engine Pipeline | NDJSON Metadata Generation & Upload (`gs://remedata/documents.jsonl`) | Generate rich JSONL metadata (`id`, `jsonData` string with `title`, `aesp_reference`, `chapter_paragraph`, `equipment_platform`, `component`, `ipc_army_code`, `nsn`, `security_classification`, `unit`, and `content.uri`) for each PDF in `gs://remedata` | PDF blob list in `gs://remedata` | `gs://remedata/documents.jsonl` | Invalid JSONL structure rejected by `:import` API | `implementation-plan.md:142-154` |
| 7 | Discovery Engine Pipeline | Incremental Document Import & Search Verification | Trigger `branches/0/documents:import` with `reconciliationMode: "INCREMENTAL"`, poll LRO until completion, and execute verification search query | `gs://remedata/documents.jsonl` | Indexed AESP documents verified via `:search` | LRO timeout or empty search verification logged/handled | `implementation-plan.md:155-157` |
| 8 | Discovery Engine Pipeline | Safe `pixel_mobile_demos` Engine Patching | `GET` existing `dataStoreIds` on `pixel_mobile_demos` (`eu`) and `PATCH ?updateMask=dataStoreIds` with union `["jointservicepubs", "ukd-reme-aesp-ds"]` | Existing `pixel_mobile_demos` engine config | Updated engine linking both `jointservicepubs` and `ukd-reme-aesp-ds` | MUST NEVER remove `jointservicepubs` or alter existing agents | `implementation-plan.md:31-34,158-160` |
| 9 | BigQuery Provisioning | Dataset `ukd_reme_demo` Creation (`scripts/seed_demo1_bigquery.py`) | Provision dataset `antig-dave.ukd_reme_demo` in `europe-west1` with mandatory dataset `description` | Dataset ID, `location="europe-west1"`, description string | BigQuery dataset in Belgium (`europe-west1`) | Idempotent (`exists_ok=True`) with updated description | `implementation-plan.md:166-170` |
| 10 | BigQuery Provisioning | Table 1: `ipc_nsn_catalogue` Schema, Metadata & Seed Data | Create table with 8 `REQUIRED` `STRING` columns, explicit table description, explicit column descriptions on every `SchemaField`, and seed 6 K60 rows (`5360-99-812-1740`) + 5 Jackal 2 rows (`5330-99-812-4410`) | Schema definition + 11 seed rows | Populated `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` | Fails verification if any column or table lacks `description` | `implementation-plan.md:171-186`, `Demo 1 - SA.md:127-140` |
| 11 | BigQuery Provisioning | Table 2: `spta_sector_grids` Schema, Metadata & Seed Data | Create table with 5 `REQUIRED` columns (`sector_key`, `sector_display_name`, `latitude`, `longitude`, `coords_label`), explicit table & column descriptions, and seed Bravo-4 (`bravo-4`, `bravo 4`, `su 1482 4621`), Alpha-1 (`alpha-1`), and London (`london`) | Schema definition + 5 seed rows | Populated `antig-dave.ukd_reme_demo.spta_sector_grids` | Fails verification if any column or table lacks `description` | `implementation-plan.md:188-199`, `Demo 1 - SA.md:141` |
| 12 | BigQuery Provisioning | Table 3: `group_chat_tickets` Schema, Metadata & Initial Seed | Create table with 13 `REQUIRED` columns (`ticket_id`, `created_at_utc`, `callsign`, `repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `coords_label`, `latitude`, `longitude`, `google_maps_url`, `status`), explicit table & column descriptions | Schema definition (+ optional initial seed ticket) | Provisioned `antig-dave.ukd_reme_demo.group_chat_tickets` | Fails verification if any column or table lacks `description` | `implementation-plan.md:201-219`, `Demo 1 - SA.md:142` |
| 13 | ADK 2.0 Schemas | Strict Pydantic v2 Schemas (`app/schemas.py`) | Define `ActiveTicketState` (9 fields + optional RAG snippet field) and `TicketPayload` (13 fields matching `group_chat_tickets`) | Dict / JSON state & webhook payloads | Validated Pydantic models | Raises `ValidationError` on missing/mistyped fields | `implementation-plan.md:68,224-225` |
| 14 | ADK 2.0 Tools | Pre-Warmed Module Singletons (`app/tools.py`) | Initialize `_BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location="europe-west1")` and `_CREDENTIALS, _ = google.auth.default()` at module import time; zero `gcloud` subprocess calls | Module import | In-memory cached ADC credentials & BQ client | Graceful fallback if credentials cannot refresh in isolated unit test | `implementation-plan.md:40,227-229`, `ORIGINAL_REQUEST.md:27,45` |
| 15 | ADK 2.0 Tools | Scene 1 Composite Tool: `diagnose_and_resolve_grid` (`app/tools.py`) | Single-pass EU Discovery Engine search (`pageSize: 15`, `snippetSpec: {"returnSnippet": True}`, NO `summarySpec`, strip `<b>`/`</b>`) + parameterized BQ lookup on `ipc_nsn_catalogue` (`@query`) + parameterized BQ lookup on `spta_sector_grids` (`@grid`) + writes `tool_context.state["active_ticket"]` | `fault_query: str`, `spoken_sector_grid: str`, `tool_context: ToolContext` | Dict containing `ActiveTicketState` fields (+ cleaned AESP snippets) | Any exception or 0-row SQL result falls back deterministically to `GOLDEN_FALLBACK_JACKAL` (if `"409"` or `"jackal"` in `fault_query`) or `GOLDEN_FALLBACK_K60`, and `GOLDEN_FALLBACK_GRID` | `implementation-plan.md:230-234`, `Demo 1 - SA.md:223-290` |
| 16 | ADK 2.0 Tools | Scene 2 Composite Tool: `publish_ticket_to_chat` (`app/tools.py`) | Reads `tool_context.state.get("active_ticket")` (or falls back to `GOLDEN_FALLBACK_K60` + `GOLDEN_FALLBACK_GRID`), builds `TicketPayload` (`TKT-REME-XXXX`, `Cpl MacDonald (4 Bn REME FRT)`, `google_maps_url`, `DISPATCH_READY`), POSTs to `{CLOUD_RUN_CHAT_URL}/api/tickets`, and inserts row into `ukd_reme_demo.group_chat_tickets` | `tool_context: ToolContext` | `{"published": True, "ticket": payload}` | Catches HTTP and BigQuery exceptions so stage demo never crashes | `implementation-plan.md:235-239`, `Demo 1 - SA.md:291-324` |
| 17 | ADK 2.0 Agent | `reme_artificer_agent` (`app/agent.py` & `app/__init__.py`) | Single ADK 2.0 `LlmAgent` (`name="reme_artificer_agent"`, `model="gemini-2.5-flash"`, `temperature=0.0`) exported as `root_agent`, instructed to render the Scene 2 Native Structured Markdown Card (15s Audio Brief + 3 `<details open>` chips) and Scene 2 publish confirmation badge | Multimodal image/text/PTT prompt | Native Structured Markdown Card or `✅ Ticket TKT-REME-XXXX Published to 4 Bn REME Group Chat` | Deterministic `temperature=0.0` + tool fallback guarantees grounded output | `implementation-plan.md:240-243`, `Demo 1 - SA.md:148-173` |
| 18 | Scene 3 Cloud Run App | FastAPI Group Chat Backend (`cloud_run_chat_app/main.py`) | Serves HTML UI (`GET /`), returns in-memory `ACTIVE_TICKETS` (`GET /api/tickets` in `<20ms`), receives & prepends tickets (`POST /api/tickets` + async BQ insert), and clears in-memory tickets (`POST /api/reset` in `<1s`) | HTTP requests on port `8080` | HTML5 page or JSON responses | Validates payload via Pydantic; ignores/handles BQ errors on startup/insert | `implementation-plan.md:246-252`, `Demo 1 - SA.md:174-184` |
| 19 | Scene 3 Cloud Run App | Tactical Dark-Mode HTML5 UI (`cloud_run_chat_app/templates/index.html`) | Ruggedised high-contrast dark UI with `OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT` banner, `[Reset Demo]` button, 1000ms live polling of `/api/tickets`, and 1-tap Google Maps Universal URL button | Browser `GET /` + 1s `fetch('/api/tickets')` | Live-updating tactical ticket cards with Google Maps deep link | Renders clean empty state after `[Reset Demo]` | `implementation-plan.md:253-261`, `Demo 1 - SA.md:185-191` |
| 20 | Testing & Evaluation | Unit & FastAPI Integration Test Suite (`tests/unit/test_tools.py`, `tests/unit/test_chat_api.py`) | Pytest suite verifying `diagnose_and_resolve_grid` (K60, Jackal 2, fallbacks, HTML tag stripping), `publish_ticket_to_chat` (with/without prior state), and FastAPI `/`, `/api/tickets`, `/api/reset` | `uv run pytest tests/unit/` | All unit & integration tests passing | Fails if any fallback, schema, or route regresses | `implementation-plan.md:77-79,267-268` |
| 21 | Testing & Evaluation | `agents-cli` Evaluation Suite (`tests/eval/eval_config.yaml`, `tests/eval/datasets/basic-dataset.json`) | Evaluation dataset covering (1) Primary FV432 K60 diagnosis in Sector Bravo-4, (2) Secondary Jackal 2 `ERR-409` diagnosis, and (3) Multi-turn diagnosis followed by `"Publish to Group Chat"` | `agents-cli eval run` | Evaluation metrics (`multi_turn_task_success`, `tool_use_quality`, custom rubric) | Reports failing turns/rubrics if tool calls or NSNs mismatch | `implementation-plan.md:80-84,273-278` |
| 22 | Cloud Deployment | Automated Deployment Script & Cloud Publishing (`scripts/deploy_demo.sh`) | Provisions `sa-reme-demo@antig-dave.iam.gserviceaccount.com` + IAM roles, deploys `reme-chat-demonstrator` to Cloud Run (`europe-west1`), deploys agent to Agent Engine (`europe-west1`) via `agents-cli deploy`, verifies Agent Registry (`gcloud agent-registry agents list`), and publishes `"REME-Artificer"` to `pixel_mobile_demos` (`eu`) via `agents-cli publish gemini` | Execution of `scripts/deploy_demo.sh` / CLI commands as `admin@edwardsda.altostrat.com` | Live Cloud Run service, Agent Engine runtime, Agent Registry entry, and Gemini Enterprise agent | Must preserve all existing agents and `jointservicepubs` on `pixel_mobile_demos` | `implementation-plan.md:279-316`, `ORIGINAL_REQUEST.md:29-30,50-53` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `diagnose_and_resolve_grid` — Noisy PTT / Unmatched Fault Query | `fault_query="garbled static noise"` (0 rows returned from `ipc_nsn_catalogue` or BigQuery exception) | Gracefully falls back to `GOLDEN_FALLBACK_K60` (`nsn="5360-99-812-1740"`, `aesp_reference="AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)"`, `repair_classification="L1 FRT Fix (Bench Check) / L2 Workshop"`). |
| 2 | `diagnose_and_resolve_grid` — Storyboard Jackal 2 Variant | `fault_query="Jackal 2 ERR-409 hydraulic manifold fault"` (when DB is unreachable or 0 rows returned, or matched via `keyword_tag` in `["jackal", "409", "hydraulic", "manifold", "4.12"]`) | Returns `GOLDEN_FALLBACK_JACKAL` (`nsn="5330-99-812-4410"`, `aesp_reference="AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)"`, `part_name="Hydraulic Manifold High-Pressure Seal Kit"`, `repair_classification="L2 Workshop Repair"`). |
| 3 | `diagnose_and_resolve_grid` — Unmatched / Garbled Spoken Grid | `spoken_sector_grid="unknown grid reference"` (0 rows returned from `spta_sector_grids` or BigQuery exception) | Gracefully falls back to `GOLDEN_FALLBACK_GRID` (`sector_display_name="Salisbury Plain (SPTA) — Sector Bravo-4"`, `latitude=51.2185`, `longitude=-1.7925`, `coords_label="51.2185° N, 1.7925° W"`). |
| 4 | `diagnose_and_resolve_grid` — Discovery Engine Snippet HTML Tags | Discovery Engine returns snippets containing `<b>oil pressure</b>` or `</b>` tags | Strips all `<b>` and `</b>` (and general HTML tags/excess whitespace) before returning snippets to the LLM, and omits `summarySpec` in REST payload to save ~3s latency. |
| 5 | `publish_ticket_to_chat` — Direct Scene 2 Jump (Empty Session State) | `tool_context.state.get("active_ticket")` is `None` or empty (presenter skipped Scene 1) | Populates default ticket by merging `{**GOLDEN_FALLBACK_K60, **GOLDEN_FALLBACK_GRID}` and publishes seamlessly with `status="DISPATCH_READY"`. |
| 6 | `publish_ticket_to_chat` — Cloud Run Webhook Unreachable / Timeout | `CLOUD_RUN_CHAT_URL` unreachable or times out (`timeout=2.0`) | Catches `Exception`, still attempts BigQuery insert into `group_chat_tickets`, and returns `{"published": True, "ticket": payload}` so the live presentation never errors out. |
| 7 | `POST /api/reset` — Stage Reset Between Takes | Presenter clicks `[Reset Demo]` immediately after publishing a ticket (while BigQuery streaming buffer still holds rows) | Clears in-memory `ACTIVE_TICKETS` list immediately (`<1s`) without issuing a failing `DELETE` against BigQuery's streaming buffer. |
| 8 | `scripts/setup_reme_datastore.py` — Shared `pixel_mobile_demos` App Patching | `pixel_mobile_demos` already has `dataStoreIds: ["jointservicepubs"]` (and possibly other datastores/agents) | Performs `GET` first, computes set union preserving all existing IDs (`["jointservicepubs", "ukd-reme-aesp-ds"]`), and patches with `updateMask=dataStoreIds` so `jointservicepubs` is never unlinked. |
| 9 | Google Maps Universal URL Format Dual Reference | `ORIGINAL_REQUEST.md:30` mentions both `https://www.google.com/maps/search/?api=1&query={lat},{lng}` and `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving` (`implementation-plan.md:237,256`) | Primary URL in `TicketPayload.google_maps_url` and `index.html` button is `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving` (and UI/card can also expose or support `maps/search/?api=1&query={lat},{lng}` if checked by tests). |
| 10 | GCP Authentication & mTLS Guardrail | Environment has `edwardsda@google.com` or client certificate auto-enabled | Must force `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` and active account `admin@edwardsda.altostrat.com` across all `gcloud`, `uv`, and `agents-cli` invocations. |

---

## 2. Logic Chain

1. **Mapping the 8-Phase Request to the 6-Phase Plan**:
   - `ORIGINAL_REQUEST.md` (line 5) instructs: *"Execute the 8-phase plan found in `docs/architecture/implementation-plan.md` from end to end"*.
   - In `docs/architecture/implementation-plan.md` (lines 88–317), Section 3 has 6 top-level headings (`Phase 1` through `Phase 6`), where `Phase 6` is subdivided into 4 distinct operational stages (`6.1 Unit & FastAPI Integration Tests`, `6.2 Local Smoke Testing & Browser UI Verification`, `6.3 Agent Evaluation via agents-cli eval run`, and `6.4 Cloud Deployment to europe-west1 & Publishing to pixel_mobile_demos`).
   - Therefore, our Phase-by-Phase specification below documents **Phases 1 through 8** explicitly (mapping Phases 1–5 1:1 and splitting Phase 6 into Phases 6, 7, and 8 while preserving the exact `Phase 6.1–6.4` labels from `implementation-plan.md`) so downstream builder, tester, and deployer agents have an unambiguous 8-phase roadmap.

2. **Complete File Inventory & Module Boundaries**:
   - By cross-referencing `implementation-plan.md` Section 2 (lines 48–84) and `Demo 1 - SA.md` Section 6 (lines 195–324), we derive the exact 20-file target structure and every interface contract required across the repository.

---

### Complete Phase-by-Phase Technical Specification (Phases 1–8)

#### Phase 1: Workspace Layout, `agents-cli` Scaffolding & EU/Belgium Environment Configuration
- **Files Created / Modified**:
  - `AGENTS.md` (Preserved verbatim)
  - `SPEC.md` (Created: Authoritative specification blueprint summarizing `Demo 1 - SA.md` & `implementation-plan.md`)
  - `agents-cli-manifest.yaml` (Created via `agents-cli scaffold create` + `enhance` for `agent_runtime` in `europe-west1`)
  - `Dockerfile` (Created at root via `agents-cli scaffold create` for Agent Runtime container build)
  - `pyproject.toml` (Created via `agents-cli scaffold create` and augmented with required packages)
  - `.env.example` & `.env` (Created at root)
- **Exact Commands**:
  ```bash
  export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
  gcloud config set account admin@edwardsda.altostrat.com
  gcloud config set project antig-dave

  agents-cli scaffold create reme-artificer-agent \
    --output-dir /tmp \
    --agent adk \
    --deployment-target agent_runtime \
    --region europe-west1 \
    --agent-guidance-filename AGENTS.md \
    --prototype
  # Copy scaffolded app/, tests/, pyproject.toml, Dockerfile, agents-cli-manifest.yaml to workspace root WITHOUT overwriting AGENTS.md or docs/
  agents-cli scaffold enhance . --deployment-target agent_runtime --region europe-west1
  agents-cli info
  ```
- **Exact `.env` and `.env.example` Contents** (`implementation-plan.md` lines 100–113):
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
  GEMINI_APP_ID=projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos
  GCS_SOURCE_BUCKET=remedata
  CLOUD_RUN_CHAT_URL=http://localhost:8080
  ```
- **Required Python Dependencies in `pyproject.toml`** (`implementation-plan.md` line 115):
  - `google-adk>=2.0.0` (or scaffolded ADK version), `google-genai`, `google-cloud-bigquery`, `google-cloud-discoveryengine`, `google-cloud-storage`, `fastapi`, `uvicorn[standard]`, `jinja2`, `requests`, `httpx`, `pydantic>=2.0.0`, `pytest` (and `uv sync`).

---

#### Phase 2: Discovery Engine Datastore (`ukd-reme-aesp-ds`) & `gs://remedata` Pipeline (`scripts/setup_reme_datastore.py`)
- **File Created**: `scripts/setup_reme_datastore.py`
- **Step-by-Step Behavior**:
  1. **GCS Inspection**: Using `google.cloud.storage.Client(project="antig-dave")`, inspect bucket `gs://remedata`. Ensure `2350-T-250-523.pdf` is present (if missing, generate/upload a valid PDF containing AESP 2350-T-250-523 Ch 1-2 Para 17.4 K60 Oil Pressure Relief Valve Spring technical specification and Jackal 2 AESP 2320-J-100 Ch 4 Para 4.12 so OCR indexing succeeds).
  2. **Datastore Creation (`location=eu`)**:
     - Endpoint: `POST https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores?dataStoreId=ukd-reme-aesp-ds`
     - Payload:
       ```json
       {
         "displayName": "UK Defence REME AESP Technical Manuals (Demo 1)",
         "industryVertical": "GENERIC",
         "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
         "contentConfig": "CONTENT_REQUIRED",
         "documentProcessingConfig": {
           "defaultParsingConfig": {
             "ocrParsingConfig": {
               "useNativeText": true
             }
           }
         }
       }
       ```
     - Handle HTTP 409 (`ALREADY_EXISTS`) gracefully.
  3. **Generate & Upload `documents.jsonl`**:
     - For `2350-T-250-523.pdf` (and any other PDF in `gs://remedata`), generate NDJSON lines:
       ```json
       {"id": "aesp-2350-t-250-523", "jsonData": "{\"title\": \"AESP 2350-T-250-523: FV432 Armoured Personnel Carrier — Engine & Lubrication System Technical Manual\", \"aesp_reference\": \"AESP 2350-T-250-523\", \"chapter_paragraph\": \"Ch 1-2, Para 17.4 (Page 14)\", \"equipment_platform\": \"FV432 APC (Rolls-Royce K60 Multi-Fuel Engine)\", \"component\": \"Oil Pressure Relief Valve Spring\", \"ipc_army_code\": \"14660 (Cat 711)\", \"nsn\": \"5360-99-812-1740\", \"security_classification\": \"OFFICIAL\", \"unit\": \"4 Battalion REME\"}", "content": {"mimeType": "application/pdf", "uri": "gs://remedata/2350-T-250-523.pdf"}}
       ```
     - Upload to `gs://remedata/documents.jsonl`.
  4. **Incremental Import & Polling**:
     - Endpoint: `POST https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/branches/0/documents:import`
     - Payload: `{"gcsSource": {"inputUris": ["gs://remedata/documents.jsonl"], "dataSchema": "document"}, "reconciliationMode": "INCREMENTAL"}`
     - Poll operation until `done: true`, then verify search via `POST .../dataStores/ukd-reme-aesp-ds/servingConfigs/default_search:search`.
  5. **Safe Patching of `pixel_mobile_demos`**:
     - `GET https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos`
     - Read existing `dataStoreIds` (must confirm `jointservicepubs` is retained).
     - Compute union: `updated_ids = list(dict.fromkeys(existing_ids + ["jointservicepubs", "ukd-reme-aesp-ds"]))`.
     - `PATCH https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos?updateMask=dataStoreIds` with `{"dataStoreIds": updated_ids}`.

---

#### Phase 3: BigQuery Schema Provisioning (`europe-west1`) with Full Table & Column Descriptions (`scripts/seed_demo1_bigquery.py`)
- **File Created**: `scripts/seed_demo1_bigquery.py`
- **Dataset Specification**:
  - Dataset ID: `antig-dave.ukd_reme_demo`
  - Location: `europe-west1`
  - Description: `"4 Battalion REME Tactical Sustainment Demonstrator (Demo 1) — Grounded Illustrated Parts Catalogue (IPC), Salisbury Plain Training Area (SPTA) Sector Grids, and Field Recovery Group Chat Tickets."`
- **Table 1: `ipc_nsn_catalogue`**:
  - Table Description: `"Illustrated Parts Catalogue (IPC) and Army Equipment Support Publication (AESP) lookup table mapping vehicle fault keywords to 13-digit NATO Stock Numbers (NSNs), repair level classifications (L1 FRT vs L2 Workshop), and technical condemnation limits."`
  - Schema (`bigquery.SchemaField` with `mode="REQUIRED"` and exact `description`):
    1. `part_id` (`STRING`, `REQUIRED`): `"Unique internal catalogue identifier for the seeded part record (e.g., K60-RELIEF-01)."`
    2. `keyword_tag` (`STRING`, `REQUIRED`): `"Lowercase search trigger keyword matched against spoken or typed field fault descriptions (e.g., k60, oil, relief, spring, 2350, 17.4, jackal, 409)."`
    3. `ipc_army_code` (`STRING`, `REQUIRED`): `"Official UK Ministry of Defence Illustrated Parts Catalogue (IPC) Army Code and Category reference (e.g., Army Code 14660 Cat 711)."`
    4. `aesp_reference` (`STRING`, `REQUIRED`): `"Authoritative Army Equipment Support Publication (AESP) document code, chapter, paragraph, and page number governing the inspection or repair."`
    5. `part_name` (`STRING`, `REQUIRED`): `"Official nomenclature of the replacement component as listed in the Illustrated Parts Catalogue."`
    6. `nsn` (`STRING`, `REQUIRED`): `"13-digit NATO Stock Number (NSN) formatted as NNNN-NN-NNN-NNNN used for supply demand."`
    7. `repair_classification` (`STRING`, `REQUIRED`): `"Authorized REME repair echelon classification indicating whether the fault is a Level 1 Forward Repair Team (FRT) fix or Level 2 Workshop repair."`
    8. `technical_limits` (`STRING`, `REQUIRED`): `"Mandatory engineering condemnation limits, spring load/length tolerances, torque settings, and safety warnings extracted from the AESP."`
  - Seed Rows:
    - **Primary FV432 K60 Rows (6 rows, `part_id` `K60-RELIEF-01` .. `K60-RELIEF-06`)**:
      - `keyword_tag`: `"k60"`, `"oil"`, `"relief"`, `"spring"`, `"2350"`, `"17.4"`
      - `ipc_army_code`: `"Army Code 14660 (Cat 711)"`
      - `aesp_reference`: `"AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)"`
      - `part_name`: `"Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)"`
      - `nsn`: `"5360-99-812-1740"`
      - `repair_classification`: `"L1 FRT Fix (Bench Check) / L2 Workshop"`
      - `technical_limits`: `"Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits; do not use washers to pack up behind a weak spring."`
    - **Secondary Jackal 2 Rows (5 rows, `part_id` `JACKAL-MANIFOLD-01` .. `JACKAL-MANIFOLD-05`)**:
      - `keyword_tag`: `"jackal"`, `"409"`, `"hydraulic"`, `"manifold"`, `"4.12"`
      - `ipc_army_code`: `"Army Code 23200 (Cat 412)"`
      - `aesp_reference`: `"AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)"`
      - `part_name`: `"Hydraulic Manifold High-Pressure Seal Kit"`
      - `nsn`: `"5330-99-812-4410"`
      - `repair_classification`: `"L2 Workshop Repair"`
      - `technical_limits`: `"Torque to 45 Nm. Depressurise hydraulic accumulator prior to seal replacement."`
- **Table 2: `spta_sector_grids`**:
  - Table Description: `"Geospatial lookup table mapping spoken Salisbury Plain Training Area (SPTA) tactical sector names and British National Grid references to WGS84 decimal latitude and longitude coordinates for Google Maps recovery routing."`
  - Schema (`bigquery.SchemaField` with `mode="REQUIRED"` and exact `description`):
    1. `sector_key` (`STRING`, `REQUIRED`): `"Lowercase normalized sector key or grid string matched against Push-to-Talk voice transcripts (e.g., bravo-4, bravo 4, su 1482 4621, alpha-1, london)."`
    2. `sector_display_name` (`STRING`, `REQUIRED`): `"Human-readable tactical sector designation displayed on diagnostic cards and group chat tickets (e.g., Salisbury Plain (SPTA) — Sector Bravo-4)."`
    3. `latitude` (`FLOAT64`, `REQUIRED`): `"WGS84 decimal latitude coordinate in degrees (positive for North) used for Google Maps destination routing."`
    4. `longitude` (`FLOAT64`, `REQUIRED`): `"WGS84 decimal longitude coordinate in degrees (negative for West) used for Google Maps destination routing."`
    5. `coords_label` (`STRING`, `REQUIRED`): `"Formatted cardinal coordinate string for UI display on tactical cards (e.g., 51.2185° N, 1.7925° W)."`
  - Seed Rows (5 rows):
    - `("bravo-4", "Salisbury Plain (SPTA) — Sector Bravo-4", 51.2185, -1.7925, "51.2185° N, 1.7925° W")`
    - `("bravo 4", "Salisbury Plain (SPTA) — Sector Bravo-4", 51.2185, -1.7925, "51.2185° N, 1.7925° W")`
    - `("su 1482 4621", "Salisbury Plain (SPTA) — Sector Bravo-4", 51.2185, -1.7925, "51.2185° N, 1.7925° W")`
    - `("alpha-1", "Salisbury Plain (SPTA) — Sector Alpha-1", 51.2310, -1.8150, "51.2310° N, 1.8150° W")`
    - `("london", "MOD Main Building — Whitehall London", 51.5007, -0.1246, "51.5007° N, 0.1246° W")`
- **Table 3: `group_chat_tickets`**:
  - Table Description: `"Persistent audit and dispatch log of field sustainment tickets published by 4 Battalion REME Forward Repair Teams (FRTs) to the B Echelon Recovery Group Chat."`
  - Schema (`bigquery.SchemaField` with `mode="REQUIRED"` and exact `description`):
    1. `ticket_id` (`STRING`, `REQUIRED`): `"Unique tactical sustainment ticket identifier formatted as TKT-REME-XXXX."`
    2. `created_at_utc` (`TIMESTAMP`, `REQUIRED`): `"UTC timestamp when the field artificer published the diagnostic ticket to the group chat."`
    3. `callsign` (`STRING`, `REQUIRED`): `"Originating field artificer callsign and unit designation (e.g., Cpl MacDonald (4 Bn REME FRT))."`
    4. `repair_classification` (`STRING`, `REQUIRED`): `"Authorized REME repair level classification (e.g., L1 FRT Fix (Bench Check) / L2 Workshop)."`
    5. `aesp_reference` (`STRING`, `REQUIRED`): `"Grounded AESP publication, chapter, paragraph, and page reference cited in the diagnosis."`
    6. `part_name` (`STRING`, `REQUIRED`): `"Official IPC nomenclature of the demanded replacement component."`
    7. `nsn` (`STRING`, `REQUIRED`): `"13-digit NATO Stock Number (NSN) demanded for the repair."`
    8. `technical_limits` (`STRING`, `REQUIRED`): `"Engineering condemnation limits and safety warnings included in the ticket."`
    9. `coords_label` (`STRING`, `REQUIRED`): `"Formatted cardinal coordinate string for the casualty vehicle location (e.g., 51.2185° N, 1.7925° W)."`
    10. `latitude` (`FLOAT64`, `REQUIRED`): `"WGS84 decimal latitude of the casualty vehicle for recovery navigation."`
    11. `longitude` (`FLOAT64`, `REQUIRED`): `"WGS84 decimal longitude of the casualty vehicle for recovery navigation."`
    12. `google_maps_url` (`STRING`, `REQUIRED`): `"Universal Google Maps turn-by-turn navigation deep link (api=1) locked to the casualty vehicle coordinates."`
    13. `status` (`STRING`, `REQUIRED`): `"Current operational dispatch status of the recovery ticket (e.g., DISPATCH_READY, ACKNOWLEDGED, RESOLVED)."`
  - Seed Row: Seed 1 initial baseline ticket (e.g. `ticket_id="TKT-REME-041"`, `callsign="Cpl MacDonald (4 Bn REME FRT)"`, K60 + Bravo-4 fields, `status="DISPATCH_READY"`) so `group_chat_tickets` is non-empty and verifiable immediately after seeding.

---

#### Phase 4: ADK 2.0 Agent, Pydantic Schemas & Stage-Proof Composite Tools (`app/`)
- **Files Created / Modified**:
  - `app/__init__.py`: Exports `root_agent` (`from .agent import root_agent`).
  - `app/schemas.py`:
    - `ActiveTicketState(BaseModel)`:
      - `repair_classification: str`
      - `aesp_reference: str`
      - `part_name: str`
      - `nsn: str`
      - `technical_limits: str`
      - `sector_display_name: str`
      - `latitude: float`
      - `longitude: float`
      - `coords_label: str`
      - `rag_snippets: Optional[ list[str] ] = None` (or optional string/list if included in tool return)
    - `TicketPayload(BaseModel)`:
      - `ticket_id: str`
      - `created_at_utc: str`
      - `callsign: str = "Cpl MacDonald (4 Bn REME FRT)"`
      - `repair_classification: str`
      - `aesp_reference: str`
      - `part_name: str`
      - `nsn: str`
      - `technical_limits: str`
      - `sector_display_name: Optional[str] = "Salisbury Plain (SPTA) — Sector Bravo-4"` (note: exclude `sector_display_name` when inserting into `group_chat_tickets` if table has the exact 13 columns, or select only the 13 table columns on BQ insert!)
      - `coords_label: str`
      - `latitude: float`
      - `longitude: float`
      - `google_maps_url: str`
      - `status: str = "DISPATCH_READY"`
  - `app/tools.py`:
    - **Module-Level Pre-Warmed Singletons**:
      ```python
      PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "antig-dave")
      BQ_LOCATION = os.environ.get("BQ_LOCATION", "europe-west1")
      _BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
      _CREDENTIALS, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
      ```
    - **Golden-Path Fallback Constants**:
      - `GOLDEN_FALLBACK_K60`:
        ```python
        {
            "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
            "aesp_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
            "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
            "nsn": "5360-99-812-1740",
            "technical_limits": (
                "Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) "
                "under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits; "
                "do not use washers to pack up behind a weak spring."
            ),
        }
        ```
      - `GOLDEN_FALLBACK_JACKAL`:
        ```python
        {
            "repair_classification": "L2 Workshop Repair",
            "aesp_reference": "AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)",
            "part_name": "Hydraulic Manifold High-Pressure Seal Kit",
            "nsn": "5330-99-812-4410",
            "technical_limits": "Torque to 45 Nm. Depressurise hydraulic accumulator prior to seal replacement.",
        }
        ```
      - `GOLDEN_FALLBACK_GRID`:
        ```python
        {
            "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
            "latitude": 51.2185,
            "longitude": -1.7925,
            "coords_label": "51.2185° N, 1.7925° W",
        }
        ```
    - **Tool 1: `diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext) -> dict`**:
      - Refreshes `_CREDENTIALS` in memory if needed (NEVER spawns `gcloud` subprocess).
      - Calls `POST https://eu-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/servingConfigs/default_search:search` with payload:
        ```json
        {
          "query": fault_query,
          "pageSize": 15,
          "contentSearchSpec": {
            "snippetSpec": {"returnSnippet": true}
          }
        }
        ```
        Strips `<b>` and `</b>` tags (`re.sub(r"</?b>", "", snippet)`) and normalizes whitespace.
      - Selects initial fallback: `GOLDEN_FALLBACK_JACKAL.copy()` if `"409"` in `fault_query.lower()` or `"jackal"` in `fault_query.lower()` else `GOLDEN_FALLBACK_K60.copy()`.
      - Runs parameterized BigQuery query on `ipc_nsn_catalogue` (`WHERE LOWER(@query) LIKE CONCAT('%', LOWER(keyword_tag), '%') LIMIT 1`).
      - Runs parameterized BigQuery query on `spta_sector_grids` (`WHERE LOWER(@grid) LIKE CONCAT('%', LOWER(sector_key), '%') LIMIT 1`) with fallback to `GOLDEN_FALLBACK_GRID.copy()`.
      - Validates with `ActiveTicketState`, stores dict in `tool_context.state["active_ticket"]`, and returns it.
    - **Tool 2: `publish_ticket_to_chat(tool_context: ToolContext) -> dict`**:
      - Reads `tool_context.state.get("active_ticket")` or merges `{**GOLDEN_FALLBACK_K60, **GOLDEN_FALLBACK_GRID}`.
      - Builds `TicketPayload` with `ticket_id=f"TKT-REME-{uuid.uuid4().hex[:4].upper()}"`, `created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()`, `callsign="Cpl MacDonald (4 Bn REME FRT)"`, `google_maps_url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"`, `status="DISPATCH_READY"`.
      - POSTs payload to `{CLOUD_RUN_CHAT_URL}/api/tickets` (`timeout=2.0`).
      - Inserts the 13 table columns of `payload` into `{PROJECT_ID}.{BQ_DATASET}.group_chat_tickets` via `_BQ_CLIENT.insert_rows_json(...)`.
      - Returns `{"published": True, "ticket": payload}`.
  - `app/agent.py`:
    - `reme_artificer_agent = LlmAgent(name="reme_artificer_agent", model="gemini-2.5-flash", instruction=SYSTEM_INSTRUCTION, tools=[diagnose_and_resolve_grid, publish_ticket_to_chat], generate_content_config=types.GenerateContentConfig(temperature=0.0))`
    - `root_agent = reme_artificer_agent`
    - `SYSTEM_INSTRUCTION` enforces the exact Scene 2 Native Structured Markdown Card Template (`Demo 1 - SA.md` lines 152–173):
      ```markdown
      ### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card
      🔊 **15s Audio Brief:** *"AESP 2350-T-250-523 Para 17.4: fatigued K60 oil pressure relief valve spring. Renew if under 79.4mm free length or outside 14.3 to 16.2kg at 54.6mm. Do not pack with washers. NSN 5360-99-812-1740. Coordinates locked."*

      <details open>
      <summary><b>🏷️ Chip 1 — Classification: {repair_classification}</b></summary>
      Renew 1 single part ({part_name}). <b>Warning:</b> {technical_limits}
      </details>

      <details open>
      <summary><b>📖 Chip 2 — AESP Ref: {aesp_reference}</b></summary>
      • <b>Technical Limits:</b> {technical_limits}
      </details>

      <details open>
      <summary><b>🔩 Chip 3 — NSN: {nsn} | 📍 Coords: {coords_label}</b></summary>
      • <b>Catalogue:</b> {part_name}<br>
      • <b>Sector Grid:</b> {sector_display_name} ({latitude}, {longitude})
      </details>

      👉 *Say **"Publish to Group Chat"** to dispatch ticket to B Echelon.*
      ```
      And when the user says `"Publish to Group Chat"`, calls `publish_ticket_to_chat` and outputs:
      `✅ Ticket {ticket_id} Published to 4 Bn REME Group Chat` (along with the ticket summary and Google Maps link).

---

#### Phase 5: Scene 3 Cloud Run Lightweight HTML5/FastAPI Group Chat App (`cloud_run_chat_app/`)
- **Files Created**:
  - `cloud_run_chat_app/Dockerfile`: `python:3.12-slim` container installing `requirements.txt` and running `uvicorn main:app --host 0.0.0.0 --port 8080`.
  - `cloud_run_chat_app/requirements.txt`: `fastapi`, `uvicorn[standard]`, `google-cloud-bigquery`, `pydantic`, `jinja2`.
  - `cloud_run_chat_app/main.py`:
    - In-memory `ACTIVE_TICKETS: list[dict] = []` seeded with the default K60 Bravo-4 ticket (or loaded from BigQuery on startup) for instant `<20ms` reads.
    - `GET /`: Renders `templates/index.html` (`4 Bn REME — Sustainment Group Chat`).
    - `GET /api/tickets`: Returns `{"tickets": ACTIVE_TICKETS}` (or list of tickets) in `<20ms`.
    - `POST /api/tickets`: Validates incoming `TicketPayload`, prepends to `ACTIVE_TICKETS` (deduplicating by `ticket_id`), and optionally triggers background BigQuery insert.
    - `POST /api/reset`: Clears `ACTIVE_TICKETS.clear()` in `<1s` and returns `{"status": "reset", "tickets": []}`.
  - `cloud_run_chat_app/templates/index.html`:
    - High-contrast ruggedised dark-mode UI (`OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT` header).
    - `[Reset Demo]` button calling `POST /api/reset`.
    - `setInterval` polling `GET /api/tickets` every `1000ms`.
    - Renders each ticket card (`ticket_id`, `callsign`, `repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `coords_label`) and the 1-tap Google Maps Universal URL button:
      ```html
      <a href="https://www.google.com/maps/dir/?api=1&destination={{ ticket.latitude }},{{ ticket.longitude }}&travelmode=driving"
         target="_blank" rel="noopener"
         class="inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg shadow">
         📍 {{ ticket.coords_label }} — Deploy via Google Maps
      </a>
      ```
      *(Note: To satisfy both URL patterns mentioned in `ORIGINAL_REQUEST.md:30`, `index.html` can also include a secondary link or data attribute for `https://www.google.com/maps/search/?api=1&query={{ ticket.latitude }},{{ ticket.longitude }}` alongside the primary `maps/dir/?api=1` button.)*

---

#### Phase 6 (Plan §6.1 & §6.2): Unit Tests, FastAPI Integration Tests & Local Browser UI Verification
- **Files Created**:
  - `tests/unit/test_tools.py`:
    - Verifies module-level `_BQ_CLIENT` and `_CREDENTIALS` singletons exist and `app/tools.py` contains zero `subprocess` / `gcloud` invocations.
    - Tests `diagnose_and_resolve_grid` for K60 query, Jackal 2 (`409` / `jackal`) query, 0-row/exception Golden-Path Fallbacks (`5360-99-812-1740`, `5330-99-812-4410`, `51.2185, -1.7925`), Discovery Engine payload (`pageSize: 15`, `snippetSpec: {"returnSnippet": True}`, absence of `summarySpec`), and `<b>`/`</b>` HTML stripping.
    - Tests `publish_ticket_to_chat` both with populated `tool_context.state["active_ticket"]` and with empty state (fallback).
  - `tests/unit/test_chat_api.py`:
    - Uses FastAPI `TestClient` to test `GET /`, `GET /api/tickets`, `POST /api/tickets`, and `POST /api/reset`.
- **Verification Commands**:
  - `uv run pytest tests/unit/`
  - Start local `uvicorn` on `http://localhost:8080`, test `agents-cli run` for Scene 1 & Scene 2, and verify UI rendering & `[Reset Demo]` in headless browser.

---

#### Phase 7 (Plan §6.3): Agent Evaluation Suite (`tests/eval/` & `agents-cli eval run`)
- **Files Created / Modified**:
  - `tests/eval/eval_config.yaml`: Configures `multi_turn_task_success`, `tool_use_quality`, and custom rubric.
  - `tests/eval/datasets/basic-dataset.json`:
    - Case 1: Primary FV432 K60 Oil Pressure Relief Valve Spring diagnosis in Sector Bravo-4 (`diagnose_and_resolve_grid` -> `5360-99-812-1740`, `51.2185, -1.7925`).
    - Case 2: Secondary Jackal 2 `ERR-409` Hydraulic Manifold diagnosis (`diagnose_and_resolve_grid` -> `5330-99-812-4410`).
    - Case 3: Multi-turn diagnosis followed by `"Publish to Group Chat"` (`diagnose_and_resolve_grid` -> `publish_ticket_to_chat`).
- **Execution Command**:
  - `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli eval run`

---

#### Phase 8 (Plan §6.4): Cloud Deployment (`europe-west1`), Agent Registry Verification & Publishing to `pixel_mobile_demos` (`scripts/deploy_demo.sh`)
- **File Created**: `scripts/deploy_demo.sh`
- **Step-by-Step Cloud Operations (Executed as `admin@edwardsda.altostrat.com` with `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`)**:
  1. **IAM & Service Account (`sa-reme-demo@antig-dave.iam.gserviceaccount.com`)**:
     - Create `sa-reme-demo` if not exists.
     - Grant `roles/aiplatform.user`, `roles/discoveryengine.viewer`, `roles/bigquery.dataEditor`, and `roles/bigquery.jobUser` on `antig-dave`, plus Reasoning Engine Service Agent (`service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) permissions.
  2. **Deploy Cloud Run Service (`reme-chat-demonstrator` in `europe-west1`)**:
     ```bash
     gcloud run deploy reme-chat-demonstrator \
       --source cloud_run_chat_app/ \
       --project antig-dave \
       --region europe-west1 \
       --service-account sa-reme-demo@antig-dave.iam.gserviceaccount.com \
       --allow-unauthenticated \
       --min-instances 1 \
       --max-instances 1 \
       --set-env-vars="GOOGLE_CLOUD_PROJECT=antig-dave,BQ_DATASET=ukd_reme_demo,BQ_LOCATION=europe-west1"
     ```
     - Capture live `CLOUD_RUN_CHAT_URL` and update `.env`.
  3. **Deploy ADK Agent to Vertex AI Agent Engine (`europe-west1`)**:
     ```bash
     agents-cli deploy \
       --project antig-dave \
       --region europe-west1 \
       --service-account sa-reme-demo@antig-dave.iam.gserviceaccount.com \
       --min-instances 1 \
       --env-vars "GOOGLE_CLOUD_PROJECT=antig-dave,GOOGLE_CLOUD_LOCATION=europe-west1,BQ_DATASET=ukd_reme_demo,BQ_LOCATION=europe-west1,DISCOVERY_ENGINE_LOCATION=eu,VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds,CLOUD_RUN_CHAT_URL=${CLOUD_RUN_CHAT_URL}" \
       --no-confirm-project
     ```
  4. **Verify Auto-Registration in Agent Registry (`europe-west1`)**:
     ```bash
     gcloud agent-registry agents list --project antig-dave --location europe-west1
     ```
  5. **Publish Agent to Gemini Enterprise (`pixel_mobile_demos` in `eu`)**:
     ```bash
     agents-cli publish gemini \
       --registration-type adk \
       --gemini-app-id projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos \
       --display-name "REME-Artificer" \
       --description "4 Bn REME Tactical Sustainment Artificer Agent (AESP 2350-T-250-523 & SPTA Grid Resolution)" \
       --tool-description "Diagnoses vehicle mechanical faults against AESP technical manuals, resolves NATO Stock Numbers (NSNs) and Salisbury Plain (SPTA) sector grids, and dispatches recovery tickets to the 4 Bn REME Group Chat."
     ```
     *(If `agents-cli publish gemini` requires fallback or verification against the EU Discovery Engine REST endpoint `https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos/assistants/default_assistant/agents`, verify that `"REME-Artificer"` is registered and all pre-existing agents and `jointservicepubs` remain untouched.)*

---

## 3. Caveats

1. **`AGENTS.md` Boilerplate vs. ADK 2.0 Architecture**:
   - The existing `AGENTS.md` file in the workspace contains a short generic Next.js/Prisma header (`AGENTS.md:3-6`), whereas both `ORIGINAL_REQUEST.md` and `docs/architecture/implementation-plan.md` explicitly instruct preserving `AGENTS.md` while building the Python ADK 2.0 + FastAPI + BigQuery architecture defined in `Demo 1 - SA.md` and `implementation-plan.md`. Do NOT delete `AGENTS.md`.
2. **BigQuery `insert_rows_json` Strict Column Matching**:
   - `ActiveTicketState` contains `sector_display_name`, whereas Table 3 (`group_chat_tickets`) has 13 columns and does NOT include `sector_display_name` (`implementation-plan.md:204-219`). When `publish_ticket_to_chat` inserts `payload` into `group_chat_tickets` via `insert_rows_json`, it MUST filter `payload` to only the 13 schema columns of `group_chat_tickets` so BigQuery does not reject the insert with `no such field: sector_display_name`.

---

## 4. Conclusion

The authoritative specification across `docs/architecture/implementation-plan.md`, `docs/architecture/Demo 1 - SA.md`, and `ORIGINAL_REQUEST.md` is complete, self-consistent, and ready for parallel execution:
1. **Infrastructure & Data Layer (Phases 1–3)**: Root-level `agents-cli` scaffold in `europe-west1`, `scripts/setup_reme_datastore.py` indexing `gs://remedata` into `ukd-reme-aesp-ds` (`eu`) and safely patching `pixel_mobile_demos` alongside `jointservicepubs`, and `scripts/seed_demo1_bigquery.py` provisioning `ukd_reme_demo` (`europe-west1`) with 100% table and column descriptions.
2. **Application & Agent Layer (Phases 4–5)**: `app/schemas.py`, `app/tools.py`, and `app/agent.py` implementing `reme_artificer_agent` (`gemini-2.5-flash`, `temperature=0.0`) with pre-warmed clients, single-pass EU Discovery Engine search (`pageSize: 15`, no `summarySpec`), and stage-proof Golden-Path Fallbacks, paired with `cloud_run_chat_app/` (`FastAPI` + tactical dark-mode `index.html`).
3. **Verification & Cloud Deployment Layer (Phases 6–8)**: Unit/integration tests in `tests/unit/`, local smoke & browser verification, `agents-cli eval run` against `tests/eval/datasets/basic-dataset.json`, and full deployment to Cloud Run (`europe-west1`), Agent Engine + Agent Registry (`europe-west1`), and `pixel_mobile_demos` (`eu`).

---

## 5. Verification Method

To independently verify this specification and the subsequent implementation:
1. **Inspect Source Documents**:
   - `docs/architecture/implementation-plan.md` (lines 1–328)
   - `docs/architecture/Demo 1 - SA.md` (lines 1–336)
   - `.agents/teamwork/ORIGINAL_REQUEST.md` (lines 1–54)
2. **Run Verification Commands Post-Implementation**:
   - `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli info`
   - `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run python scripts/setup_reme_datastore.py`
   - `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run python scripts/seed_demo1_bigquery.py`
   - `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/`
   - `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli eval run`
   - `gcloud agent-registry agents list --project antig-dave --location europe-west1`
