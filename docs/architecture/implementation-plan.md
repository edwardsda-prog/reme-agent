# Local & Cloud Implementation Plan: Pixel Roots — Demo 1 ("Snap, Diagnose, Pin & Demand")

| Field | Specification Value |
| :--- | :--- |
| **Source of Truth** | [Demo 1 - SA.md](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/docs/architecture/Demo%201%20-%20SA.md) (`SDD-DEMO1-ADK2-003`) & [AGENTS.md](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/AGENTS.md) |
| **Target GCP Project** | `antig-dave` (Authenticated as `admin@edwardsda.altostrat.com`; Runtime SA: `sa-reme-demo@antig-dave.iam.gserviceaccount.com`) |
| **Regional Deployment (Belgium)** | **`europe-west1`** — Vertex AI (`gemini-2.5-flash`), Agent Engine (`agent_runtime`), Agent Registry, Cloud Run (`reme-chat-demonstrator`), and BigQuery (`ukd_reme_demo`) |
| **Multi-Region EU Endpoint** | **`eu`** — Discovery Engine Datastore (`ukd-reme-aesp-ds`) & Gemini Enterprise App (`pixel_mobile_demos`) |
| **Source GCS Bucket & RAG** | `gs://remedata` (in `antig-dave`) -> Indexed into dedicated datastore `ukd-reme-aesp-ds` with generated JSONL metadata (`documents.jsonl`). Existing `jointservicepubs` datastore on `pixel_mobile_demos` is preserved and not used by this agent. |
| **Agent Lifecycle Tooling** | **`agents-cli`** (`scaffold create`, `run`, `eval run`, `deploy` to Agent Engine & Agent Registry, `publish gemini` to `pixel_mobile_demos`) |
| **Scene 3 Handoff App** | **FastAPI + High-Contrast Tactical HTML5 Group Chat** (`cloud_run_chat_app`) -> **Google Maps Universal URL (`api=1`)** |

---

## 1. Architecture & Design Decisions (Resolved via `/grill-me`)

1. **Strict EU / Belgium Residency (`europe-west1` & `eu`)**:
   - **Belgium (`europe-west1`)**: All regional compute, model inference, and structured data reside in Belgium (`europe-west1`):
     - Vertex AI Gemini API calls (`GOOGLE_CLOUD_LOCATION=europe-west1`, `gemini-2.5-flash`, `temperature=0.0`).
     - Vertex AI Agent Engine (`agent_runtime`) & Google Cloud Agent Registry (`--region europe-west1`).
     - Google Cloud BigQuery dataset `ukd_reme_demo` (`location="europe-west1"`).
     - Google Cloud Run Scene 3 Group Chat service `reme-chat-demonstrator` (`--region europe-west1`).
   - **EU Multi-Region (`eu`)**: Discovery Engine / Gemini Enterprise resources use the EU multi-region endpoint (`https://eu-discoveryengine.googleapis.com/v1alpha/...`, `DISCOVERY_ENGINE_LOCATION=eu`):
     - Dedicated datastore: `projects/antig-dave/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds`.
     - Shared Gemini Enterprise App: `projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos`.

2. **Root-Level `agents-cli` Project Layout**:
   - The workspace root (`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`) hosts the `agents-cli` project directly (`app/`, `tests/eval/`, `agents-cli-manifest.yaml`, `pyproject.toml`, `Dockerfile`) alongside `cloud_run_chat_app/` and `scripts/`.
   - All `agents-cli` lifecycle commands (`agents-cli info`, `agents-cli run`, `agents-cli eval run`, `agents-cli deploy`, `agents-cli publish gemini`) execute directly from the repository root without changing directories.

3. **Dedicated `ukd-reme-aesp-ds` Datastore, `gs://remedata` Metadata Generation & Safe `pixel_mobile_demos` Linking**:
   - We do **not** query or alter the existing `jointservicepubs` datastore.
   - `scripts/setup_reme_datastore.py` inspects `gs://remedata` in `antig-dave`, creates the unstructured OCR datastore `ukd-reme-aesp-ds` in location `eu`, generates rich NDJSON metadata (`documents.jsonl`) for the source PDFs in `gs://remedata`, uploads `gs://remedata/documents.jsonl`, and imports/indexes the documents into `ukd-reme-aesp-ds`.
   - Once indexed, `scripts/setup_reme_datastore.py` fetches the current `dataStoreIds` list from `pixel_mobile_demos` and patches `dataStoreIds` with the union (`["jointservicepubs", "ukd-reme-aesp-ds"]`) so `jointservicepubs` and all existing agents on `pixel_mobile_demos` remain completely intact.

4. **BigQuery Metadata Completeness (Table & Column Descriptions)**:
   - Every table in `ukd_reme_demo` (`ipc_nsn_catalogue`, `spta_sector_grids`, `group_chat_tickets`) is provisioned in `europe-west1` with explicit table-level `description` metadata and explicit column-level `description` metadata on every `bigquery.SchemaField`.

5. **ADK 2.0 Performance & Latency Guardrails**:
   - **Pre-Warmed Singletons**: `bigquery.Client(project="antig-dave", location="europe-west1")` and in-memory Application Default Credentials (`google.auth.default()`) are initialized at module import time in `app/tools.py` to avoid 2–3s setup latency per tool call.
   - **Single-Pass EU Discovery Engine Search**: `diagnose_and_resolve_grid` queries `https://eu-discoveryengine.googleapis.com/.../dataStores/ukd-reme-aesp-ds/servingConfigs/default_search:search` with `pageSize: 15`, `snippetSpec: {"returnSnippet": true}`, omitting `summarySpec` (saving ~3s of duplicate backend LLM generation), and stripping `<b>`/`</b>` HTML tags.
   - **Stage-Proof Golden-Path Fallbacks**: Parameterized SQL queries (`bigquery.ScalarQueryParameter`) with deterministic fallback to the seeded **FV432 Rolls-Royce K60 Oil Pressure Relief Valve Spring (`NSN: 5360-99-812-1740`)** (or **Jackal 2 `ERR-409` (`NSN: 5330-99-812-4410`)** when `"409"` / `"jackal"` is present) and **Salisbury Plain Sector Bravo-4 (`51.2185° N, 1.7925° W`)**.

---

## 2. Target Workspace Directory Layout

```text
/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/
├── AGENTS.md                              # Project context & quality bounds (preserved)
├── SPEC.md                                # Authoritative specification blueprint
├── agents-cli-manifest.yaml               # agents-cli project configuration (adk, agent_runtime, europe-west1)
├── pyproject.toml                         # uv / Python project dependencies managed by agents-cli
├── Dockerfile                             # Agent Runtime container build definition (from agents-cli scaffold)
├── .env.example                           # Template environment variables (EU / Belgium)
├── .env                                   # Local runtime environment config (antig-dave, europe-west1, eu)
├── docs/
│   └── architecture/
│       ├── Demo 1 - SA.md                 # Solutions Architecture Guide (Source of Truth)
│       └── implementation-plan.md         # This step-by-step implementation plan
├── scripts/
│   ├── setup_reme_datastore.py            # Inspects gs://remedata, generates documents.jsonl, creates & indexes ukd-reme-aesp-ds (eu), patches pixel_mobile_demos
│   ├── seed_demo1_bigquery.py             # Creates & seeds ukd_reme_demo in europe-west1 with full Table & Column descriptions
│   └── deploy_demo.sh                     # Provisions sa-reme-demo, deploys Cloud Run chat app, runs agents-cli deploy & publish gemini
├── app/                                   # Scaffolded ADK 2.0 Agent package (reme_artificer_agent)
│   ├── __init__.py                        # Exports root_agent
│   ├── agent.py                           # Single ADK 2.0 LlmAgent (reme_artificer_agent, gemini-2.5-flash, temp=0.0)
│   ├── schemas.py                         # Strict Pydantic v2 schemas for ActiveTicketState & TicketPayload
│   └── tools.py                           # 2 Composite Tools (diagnose_and_resolve_grid, publish_ticket_to_chat)
├── cloud_run_chat_app/                    # Scene 3 Lightweight HTML5/FastAPI Group Chat App (deployed to europe-west1)
│   ├── Dockerfile                         # python:3.12-slim container running uvicorn on port 8080
│   ├── requirements.txt                   # FastAPI, uvicorn, google-cloud-bigquery, pydantic
│   ├── main.py                            # FastAPI app (GET /, GET/POST /api/tickets, POST /api/reset)
│   └── templates/
│       └── index.html                     # Tactical Dark-Mode HTML5 UI + 1-Tap Google Maps Deep Link
└── tests/                                 # Unit, Integration & agents-cli Evaluation Suite
    ├── unit/
    │   ├── test_tools.py                  # Unit tests for Scene 1 & Scene 2 composite tools + fallbacks
    │   └── test_chat_api.py               # Integration tests for FastAPI Group Chat routes & stage reset
    └── eval/                              # Scaffolded agents-cli evaluation suite
        ├── eval_config.yaml               # Evaluation metrics config (multi_turn_task_success, tool_use_quality, custom rubric)
        └── datasets/
            └── basic-dataset.json         # Scene 1 (K60 & Jackal 2) and Scene 2 ("Publish to Group Chat") eval cases
```

---

## 3. Step-by-Step Implementation Phases

### Phase 1: `agents-cli` Project Scaffolding & EU Environment Configuration

1. **Scaffold via `agents-cli` into Workspace Root**:
   - Run `agents-cli scaffold create reme-artificer-agent --output-dir /tmp --agent adk --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md --prototype` and copy the scaffolded structure (`app/`, `tests/`, `pyproject.toml`, `Dockerfile`, `agents-cli-manifest.yaml`) into `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/` while preserving the existing `AGENTS.md` and `docs/`.
   - Enhance the project for `agent_runtime` in `europe-west1`:
     ```bash
     agents-cli scaffold enhance . --deployment-target agent_runtime --region europe-west1
     ```
   - Verify with `agents-cli info` that the project is recognized at the workspace root.
2. **Configure `.env.example` and `.env` (Belgium `europe-west1` & `eu`)**:
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
3. **Sync Dependencies with `uv`**:
   - Add `google-cloud-bigquery`, `google-cloud-discoveryengine`, `google-cloud-storage`, `fastapi`, `uvicorn[standard]`, `jinja2`, `requests`, `httpx`, and `pytest` to `pyproject.toml` and run `uv sync`.

---

### Phase 2: Discovery Engine Datastore (`ukd-reme-aesp-ds`) & `gs://remedata` Metadata Pipeline (`scripts/setup_reme_datastore.py`)

1. **Inspect Source Bucket (`gs://remedata` in `antig-dave`)**:
   - List all PDF/document blobs in `gs://remedata` (such as `2350-T-250-523.pdf`).
   - If the AESP 2350-T-250-523 document is not yet present in `gs://remedata`, upload/verify it so the bucket has the canonical source PDF(s).
2. **Create Dedicated EU Unstructured OCR Datastore (`ukd-reme-aesp-ds`)**:
   - Target endpoint: `https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores?dataStoreId=ukd-reme-aesp-ds`
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
3. **Generate & Upload JSONL Metadata (`gs://remedata/documents.jsonl`)**:
   - For each PDF in `gs://remedata`, construct an NDJSON metadata record with structured domain attributes:
     ```json
     {
       "id": "aesp-2350-t-250-523",
       "jsonData": "{\"title\": \"AESP 2350-T-250-523: FV432 Armoured Personnel Carrier — Engine & Lubrication System Technical Manual\", \"aesp_reference\": \"AESP 2350-T-250-523\", \"chapter_paragraph\": \"Ch 1-2, Para 17.4 (Page 14)\", \"equipment_platform\": \"FV432 APC (Rolls-Royce K60 Multi-Fuel Engine)\", \"component\": \"Oil Pressure Relief Valve Spring\", \"ipc_army_code\": \"14660 (Cat 711)\", \"nsn\": \"5360-99-812-1740\", \"security_classification\": \"OFFICIAL\", \"unit\": \"4 Battalion REME\"}",
       "content": {
         "mimeType": "application/pdf",
         "uri": "gs://remedata/<filename>.pdf"
       }
     }
     ```
   - Upload `documents.jsonl` to `gs://remedata/documents.jsonl`.
4. **Trigger Incremental Import & Index Verification**:
   - Call `POST https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/branches/0/documents:import` with `inputUris: ["gs://remedata/documents.jsonl"]` and `reconciliationMode: "INCREMENTAL"`.
   - Poll the long-running operation until indexing succeeds, then run a verification search query against `ukd-reme-aesp-ds`.
5. **Safely Link `ukd-reme-aesp-ds` to `pixel_mobile_demos` (Preserving `jointservicepubs`)**:
   - `GET https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos` to read existing `dataStoreIds` (confirming `jointservicepubs` is present).
   - `PATCH .../engines/pixel_mobile_demos?updateMask=dataStoreIds` passing the combined list (e.g. `["jointservicepubs", "ukd-reme-aesp-ds"]`) so `jointservicepubs` is never removed.

---

### Phase 3: BigQuery Schema Provisioning (`europe-west1`) with Full Table & Column Descriptions (`scripts/seed_demo1_bigquery.py`)

1. **Dataset Provisioning**:
   - Dataset ID: `antig-dave.ukd_reme_demo`
   - Location: `europe-west1` (Belgium)
   - Dataset Description: `"4 Battalion REME Tactical Sustainment Demonstrator (Demo 1) — Grounded Illustrated Parts Catalogue (IPC), Salisbury Plain Training Area (SPTA) Sector Grids, and Field Recovery Group Chat Tickets."`

2. **Table 1 — `ipc_nsn_catalogue`**:
   - **Table Description**: `"Illustrated Parts Catalogue (IPC) and Army Equipment Support Publication (AESP) lookup table mapping vehicle fault keywords to 13-digit NATO Stock Numbers (NSNs), repair level classifications (L1 FRT vs L2 Workshop), and technical condemnation limits."`
   - **Columns & Descriptions**:
     | Column Name | Type | Mode | Column Description |
     | :--- | :--- | :--- | :--- |
     | `part_id` | `STRING` | `REQUIRED` | `"Unique internal catalogue identifier for the seeded part record (e.g., K60-RELIEF-01)."` |
     | `keyword_tag` | `STRING` | `REQUIRED` | `"Lowercase search trigger keyword matched against spoken or typed field fault descriptions (e.g., k60, oil, relief, spring, 2350, 17.4, jackal, 409)."` |
     | `ipc_army_code` | `STRING` | `REQUIRED` | `"Official UK Ministry of Defence Illustrated Parts Catalogue (IPC) Army Code and Category reference (e.g., Army Code 14660 Cat 711)."` |
     | `aesp_reference` | `STRING` | `REQUIRED` | `"Authoritative Army Equipment Support Publication (AESP) document code, chapter, paragraph, and page number governing the inspection or repair."` |
     | `part_name` | `STRING` | `REQUIRED` | `"Official nomenclature of the replacement component as listed in the Illustrated Parts Catalogue."` |
     | `nsn` | `STRING` | `REQUIRED` | `"13-digit NATO Stock Number (NSN) formatted as NNNN-NN-NNN-NNNN used for supply demand."` |
     | `repair_classification` | `STRING` | `REQUIRED` | `"Authorized REME repair echelon classification indicating whether the fault is a Level 1 Forward Repair Team (FRT) fix or Level 2 Workshop repair."` |
     | `technical_limits` | `STRING` | `REQUIRED` | `"Mandatory engineering condemnation limits, spring load/length tolerances, torque settings, and safety warnings extracted from the AESP."` |
   - **Seed Data**:
     - Primary FV432 Rolls-Royce K60 Engine Oil Pressure Relief Valve Spring rows (`keyword_tag` in `["k60", "oil", "relief", "spring", "2350", "17.4"]`, `nsn="5360-99-812-1740"`).
     - Secondary Jackal 2 `ERR-409` Hydraulic Manifold High-Pressure Seal Kit rows (`keyword_tag` in `["jackal", "409", "hydraulic", "manifold", "4.12"]`, `nsn="5330-99-812-4410"`).

3. **Table 2 — `spta_sector_grids`**:
   - **Table Description**: `"Geospatial lookup table mapping spoken Salisbury Plain Training Area (SPTA) tactical sector names and British National Grid references to WGS84 decimal latitude and longitude coordinates for Google Maps recovery routing."`
   - **Columns & Descriptions**:
     | Column Name | Type | Mode | Column Description |
     | :--- | :--- | :--- | :--- |
     | `sector_key` | `STRING` | `REQUIRED` | `"Lowercase normalized sector key or grid string matched against Push-to-Talk voice transcripts (e.g., bravo-4, bravo 4, su 1482 4621, alpha-1, london)."` |
     | `sector_display_name` | `STRING` | `REQUIRED` | `"Human-readable tactical sector designation displayed on diagnostic cards and group chat tickets (e.g., Salisbury Plain (SPTA) — Sector Bravo-4)."` |
     | `latitude` | `FLOAT64` | `REQUIRED` | `"WGS84 decimal latitude coordinate in degrees (positive for North) used for Google Maps destination routing."` |
     | `longitude` | `FLOAT64` | `REQUIRED` | `"WGS84 decimal longitude coordinate in degrees (negative for West) used for Google Maps destination routing."` |
     | `coords_label` | `STRING` | `REQUIRED` | `"Formatted cardinal coordinate string for UI display on tactical cards (e.g., 51.2185° N, 1.7925° W)."` |
   - **Seed Data**:
     - Sector Bravo-4 (`"bravo-4"`, `"bravo 4"`, `"su 1482 4621"` -> `51.2185, -1.7925`), Sector Alpha-1 (`"alpha-1"` -> `51.2310, -1.8150`), and Whitehall London (`"london"` -> `51.5007, -0.1246`).

4. **Table 3 — `group_chat_tickets`**:
   - **Table Description**: `"Persistent audit and dispatch log of field sustainment tickets published by 4 Battalion REME Forward Repair Teams (FRTs) to the B Echelon Recovery Group Chat."`
   - **Columns & Descriptions**:
     | Column Name | Type | Mode | Column Description |
     | :--- | :--- | :--- | :--- |
     | `ticket_id` | `STRING` | `REQUIRED` | `"Unique tactical sustainment ticket identifier formatted as TKT-REME-XXXX."` |
     | `created_at_utc` | `TIMESTAMP` | `REQUIRED` | `"UTC timestamp when the field artificer published the diagnostic ticket to the group chat."` |
     | `callsign` | `STRING` | `REQUIRED` | `"Originating field artificer callsign and unit designation (e.g., Cpl MacDonald (4 Bn REME FRT))."` |
     | `repair_classification` | `STRING` | `REQUIRED` | `"Authorized REME repair level classification (e.g., L1 FRT Fix (Bench Check) / L2 Workshop)."` |
     | `aesp_reference` | `STRING` | `REQUIRED` | `"Grounded AESP publication, chapter, paragraph, and page reference cited in the diagnosis."` |
     | `part_name` | `STRING` | `REQUIRED` | `"Official IPC nomenclature of the demanded replacement component."` |
     | `nsn` | `STRING` | `REQUIRED` | `"13-digit NATO Stock Number (NSN) demanded for the repair."` |
     | `technical_limits` | `STRING` | `REQUIRED` | `"Engineering condemnation limits and safety warnings included in the ticket."` |
     | `coords_label` | `STRING` | `REQUIRED` | `"Formatted cardinal coordinate string for the casualty vehicle location (e.g., 51.2185° N, 1.7925° W)."` |
     | `latitude` | `FLOAT64` | `REQUIRED` | `"WGS84 decimal latitude of the casualty vehicle for recovery navigation."` |
     | `longitude` | `FLOAT64` | `REQUIRED` | `"WGS84 decimal longitude of the casualty vehicle for recovery navigation."` |
     | `google_maps_url` | `STRING` | `REQUIRED` | `"Universal Google Maps turn-by-turn navigation deep link (api=1) locked to the casualty vehicle coordinates."` |
     | `status` | `STRING` | `REQUIRED` | `"Current operational dispatch status of the recovery ticket (e.g., DISPATCH_READY, ACKNOWLEDGED, RESOLVED)."` |

---

### Phase 4: ADK 2.0 Agent & Stage-Proof Composite Tools (`app/`)

1. **Strict Pydantic Schemas (`app/schemas.py`)**:
   - `ActiveTicketState` and `TicketPayload` enforcing type safety across `tool_context.state["active_ticket"]`, BigQuery persistence, and the FastAPI `/api/tickets` webhook.
2. **Composite Tools (`app/tools.py`)**:
   - **Pre-Warmed Module Singletons**:
     - `_BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location="europe-west1")`
     - `_CREDENTIALS, _ = google.auth.default()`
   - **`diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext) -> dict`**:
     1. Queries EU Discovery Engine datastore `ukd-reme-aesp-ds` (`https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/servingConfigs/default_search:search`) with `pageSize=15`, `snippetSpec={"returnSnippet": True}`, no `summarySpec`, and HTML tag stripping.
     2. Queries `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` (`location="europe-west1"`) via parameterized SQL (`@query`), falling back deterministically to `GOLDEN_FALLBACK_K60` (or `GOLDEN_FALLBACK_JACKAL` if `"409"` / `"jackal"` is in `fault_query`).
     3. Queries `antig-dave.ukd_reme_demo.spta_sector_grids` (`location="europe-west1"`) via parameterized SQL (`@grid`), falling back deterministically to `GOLDEN_FALLBACK_GRID` (`51.2185, -1.7925`).
     4. Saves the validated dictionary to `tool_context.state["active_ticket"]` and returns it.
   - **`publish_ticket_to_chat(tool_context: ToolContext) -> dict`**:
     1. Reads `tool_context.state.get("active_ticket")` (or falls back to `GOLDEN_FALLBACK_K60` + `GOLDEN_FALLBACK_GRID`).
     2. Builds `TicketPayload` with `ticket_id`, `created_at_utc`, `callsign="Cpl MacDonald (4 Bn REME FRT)"`, and `google_maps_url="https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"`.
     3. Pushes immediately via `POST {CLOUD_RUN_CHAT_URL}/api/tickets` (`<20ms` in-memory update).
     4. Inserts row into `antig-dave.ukd_reme_demo.group_chat_tickets`.
3. **Single `LlmAgent` Definition (`app/agent.py`)**:
   - `root_agent = LlmAgent(name="reme_artificer_agent", model="gemini-2.5-flash", ...)` with `temperature=0.0`.
   - System instruction enforces the exact **Scene 2 Native Structured Markdown Card Template** (Section 5.1 of `Demo 1 - SA.md` with the 15s Audio Brief and 3 `<details open>` chips) and the Scene 2 publish confirmation badge.

---

### Phase 5: Scene 3 Cloud Run Lightweight HTML5/FastAPI Group Chat App (`cloud_run_chat_app/`)

1. **FastAPI Service (`cloud_run_chat_app/main.py`)**:
   - `GET /`: Serves `templates/index.html` (`4 Bn REME — Sustainment Group Chat`).
   - `GET /api/tickets`: Returns in-memory `ACTIVE_TICKETS` (`<20ms` response, polled every `1000ms`).
   - `POST /api/tickets`: Validates incoming `TicketPayload`, prepends to `ACTIVE_TICKETS`, and triggers background BigQuery insert if needed.
   - `POST /api/reset`: Stage Reset button endpoint — clears `ACTIVE_TICKETS` in memory immediately (`<1s` reset between takes).
2. **Tactical Dark-Mode HTML5 UI (`cloud_run_chat_app/templates/index.html`)**:
   - High-contrast ruggedised dark theme with `OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT` banner, `[Reset Demo]` button, live 1s polling, and the 1-tap Google Maps Universal URL button:
     ```html
     <a href="https://www.google.com/maps/dir/?api=1&destination={{ ticket.latitude }},{{ ticket.longitude }}&travelmode=driving"
        target="_blank" rel="noopener"
        class="inline-flex items-center px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg shadow">
        📍 {{ ticket.coords_label }} — Deploy via Google Maps
     </a>
     ```

---

### Phase 6: Local Testing, `agents-cli eval`, Cloud Deployment (`europe-west1`) & Publishing to `pixel_mobile_demos`

1. **Unit & FastAPI Integration Tests (`pytest`)**:
   - Run `uv run pytest tests/unit/` to verify `diagnose_and_resolve_grid`, `publish_ticket_to_chat`, golden-path fallbacks, and all FastAPI endpoints (`/`, `/api/tickets`, `/api/reset`).
2. **Local Smoke Testing & Browser UI Verification**:
   - Start `cloud_run_chat_app` locally on `http://localhost:8080`.
   - Run `agents-cli run` prompts for Scene 1 (K60 fault in Sector Bravo-4) and Scene 2 ("Publish to Group Chat").
   - Open `http://localhost:8080` in the built-in browser tool, take screenshots verifying the live Ticket Card, the Google Maps deep link, and the `[Reset Demo]` button.
3. **Agent Evaluation via `agents-cli eval run`**:
   - Configure `tests/eval/datasets/basic-dataset.json` and `tests/eval/eval_config.yaml` with cases for:
     1. Primary FV432 K60 Oil Pressure Relief Valve Spring diagnosis in Sector Bravo-4.
     2. Secondary Jackal 2 `ERR-409` Hydraulic Manifold diagnosis.
     3. Multi-turn diagnosis followed by `"Publish to Group Chat"`.
   - Run `agents-cli eval run` and verify evaluation scores before cloud deployment.
4. **Cloud Deployment to `europe-west1` & Publishing to `pixel_mobile_demos`**:
   - **Step 4.1 — Service Account (`sa-reme-demo@antig-dave.iam.gserviceaccount.com`)**:
     - Ensure `roles/aiplatform.user`, `roles/discoveryengine.viewer`, `roles/bigquery.dataEditor`, and `roles/bigquery.jobUser` are granted, along with Reasoning Engine Service Agent permissions (`service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`).
   - **Step 4.2 — Deploy Scene 3 Cloud Run Group Chat App (`europe-west1`)**:
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
   - **Step 4.3 — Deploy Agent to Vertex AI Agent Engine & Agent Registry (`europe-west1`) via `agents-cli`**:
     ```bash
     agents-cli deploy \
       --project antig-dave \
       --region europe-west1 \
       --service-account sa-reme-demo@antig-dave.iam.gserviceaccount.com \
       --min-instances 1 \
       --env-vars "GOOGLE_CLOUD_PROJECT=antig-dave,GOOGLE_CLOUD_LOCATION=europe-west1,BQ_DATASET=ukd_reme_demo,BQ_LOCATION=europe-west1,DISCOVERY_ENGINE_LOCATION=eu,VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds,CLOUD_RUN_CHAT_URL=${CLOUD_RUN_CHAT_URL}" \
       --no-confirm-project
     ```
   - **Step 4.4 — Verify Auto-Registration in Agent Registry (`europe-west1`)**:
     ```bash
     gcloud agent-registry agents list --project antig-dave --location europe-west1
     ```
   - **Step 4.5 — Publish Agent to Gemini Enterprise (`pixel_mobile_demos` in `eu`) via `agents-cli`**:
     ```bash
     agents-cli publish gemini \
       --registration-type adk \
       --gemini-app-id projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos \
       --display-name "REME-Artificer" \
       --description "4 Bn REME Tactical Sustainment Artificer Agent (AESP 2350-T-250-523 & SPTA Grid Resolution)" \
       --tool-description "Diagnoses vehicle mechanical faults against AESP technical manuals, resolves NATO Stock Numbers (NSNs) and Salisbury Plain (SPTA) sector grids, and dispatches recovery tickets to the 4 Bn REME Group Chat."
     ```

---

## 4. Execution Checklist

- [ ] **Phase 1**: Scaffold ADK project at workspace root via `agents-cli scaffold create`, configure `.env` (`europe-west1` / `eu`), and run `uv sync`.
- [ ] **Phase 2**: Create and execute `scripts/setup_reme_datastore.py` to inspect `gs://remedata`, generate & upload `gs://remedata/documents.jsonl`, create & index `ukd-reme-aesp-ds` (`location=eu`), and append `ukd-reme-aesp-ds` to `pixel_mobile_demos` alongside `jointservicepubs`.
- [ ] **Phase 3**: Create and execute `scripts/seed_demo1_bigquery.py` to create dataset `ukd_reme_demo` (`location=europe-west1`) and seed `ipc_nsn_catalogue`, `spta_sector_grids`, and `group_chat_tickets` with full table and column descriptions.
- [ ] **Phase 4**: Implement `app/schemas.py`, `app/tools.py`, and `app/agent.py` (`reme_artificer_agent`).
- [ ] **Phase 5**: Implement `cloud_run_chat_app` (`main.py`, `templates/index.html`, `Dockerfile`, `requirements.txt`).
- [ ] **Phase 6**: Run `pytest`, verify local Scene 1 -> Scene 2 -> Scene 3 + browser UI screenshots, run `agents-cli eval run`, and execute deployment (`agents-cli deploy` & `agents-cli publish gemini`) upon approval.
