Allocate a dedicated sub-agent team to build, test, and deploy this project in parallel worktrees. Execute the 8-phase plan found in `docs/architecture/implementation-plan.md` from end to end, performing all file modifications, local container builds, and final deployments natively without any human approvals or confirmation gates.

Working directory: /usr/local/google/home/edwardsda/Documents/Demo 1 - Reme
Integrity mode: development

Primary References:
- `docs/architecture/implementation-plan.md` (Full end-to-end implementation plan refined after `/grill-me`)
- `docs/architecture/Demo 1 - SA.md` (Solutions Architecture Guide SDD-DEMO1-ADK2-003)
- `AGENTS.md`

## Requirements

### R1. Workspace Layout, Scaffolding & EU/Belgium Environment Configuration
Set up a root-level `agents-cli` ADK 2.0 project (`app/`, `tests/eval/`, `agents-cli-manifest.yaml`, `Dockerfile`, `pyproject.toml`) at `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` alongside `cloud_run_chat_app/` and `scripts/`, preserving `AGENTS.md` and `docs/`. Configure `.env.example` and `.env` and sync dependencies with `uv`. Enforce strict Belgium (`europe-west1`) residency for BigQuery (`ukd_reme_demo`), Agent Engine (`agent_runtime`), Cloud Run (`reme-chat-demonstrator`), Agent Registry, and `gemini-2.5-flash` inference (`GOOGLE_CLOUD_LOCATION=europe-west1`), and use the `eu` multi-region (`https://eu-discoveryengine.googleapis.com/v1alpha/...`) for Discovery Engine (`ukd-reme-aesp-ds` and `pixel_mobile_demos`).

### R2. Discovery Engine Datastore (`ukd-reme-aesp-ds`) & `gs://remedata` Pipeline (`scripts/setup_reme_datastore.py`)
Inspect `gs://remedata` in `antig-dave` (ensuring `2350-T-250-523.pdf` is present), generate rich NDJSON metadata (`documents.jsonl` with `title`, `aesp_reference`, `equipment_platform`, `security_classification`, etc.), upload to `gs://remedata/documents.jsonl`, and create and index the unstructured OCR datastore `ukd-reme-aesp-ds` (`location=eu`). Safely patch `pixel_mobile_demos` `dataStoreIds` to include both `["jointservicepubs", "ukd-reme-aesp-ds"]` without removing `jointservicepubs` or modifying existing agents or datastores.

### R3. BigQuery Dataset & Table Provisioning with Full Metadata (`scripts/seed_demo1_bigquery.py`)
Create dataset `ukd_reme_demo` (`location="europe-west1"`) and seed all 3 tables (`ipc_nsn_catalogue`, `spta_sector_grids`, `group_chat_tickets`) with the primary FV432 K60 (`5360-99-812-1740`), secondary Jackal 2 (`5330-99-812-4410`), and SPTA sector grid records (`51.2185, -1.7925`, `51.2310, -1.8150`, `51.5007, -0.1246`). The dataset and all 3 tables MUST include explicit table-level `description` metadata and explicit column-level `description` metadata on every `bigquery.SchemaField`.

### R4. ADK 2.0 Agent, Schemas & Stage-Proof Composite Tools (`app/schemas.py`, `app/tools.py`, `app/agent.py`)
Implement strict Pydantic schemas (`ActiveTicketState`, `TicketPayload`), `reme_artificer_agent` (`LlmAgent` using `gemini-2.5-flash`, `temperature=0.0`) rendering the Native Structured Markdown Card (15s Audio Brief + 3 `<details open>` chips), and composite tools `diagnose_and_resolve_grid` and `publish_ticket_to_chat` with Golden-Path Fallbacks (FV432 K60 `5360-99-812-1740`, Jackal 2 `5330-99-812-4410`, Sector Bravo-4 `51.2185, -1.7925`). Pre-warm `bigquery.Client()` and `google.auth.default()` at module import time; never invoke `gcloud` subprocesses inside tool handlers. Query `ukd-reme-aesp-ds` directly from `diagnose_and_resolve_grid` with `pageSize: 15`, `snippetSpec: {"returnSnippet": True}`, and NO `summarySpec` (stripping `<b>`/`</b>` HTML tags).

### R5. Scene 3 Cloud Run Tactical Group Chat App (`cloud_run_chat_app/`), Testing, Evaluation & Cloud Deployment
Build the FastAPI + dark-mode tactical HTML5 UI (`main.py`, `templates/index.html`, `Dockerfile`, `requirements.txt`, `scripts/deploy_demo.sh`) with `<20ms` in-memory `ACTIVE_TICKETS`, `GET /`, `GET/POST /api/tickets`, `POST /api/reset`, and 1-tap Google Maps Universal URL (`https://www.google.com/maps/search/?api=1&query={lat},{lng}` as stated in the request context, or `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving` as in `docs/architecture/implementation-plan.md`). Execute all operations under GCP Project `antig-dave`, Active Account `admin@edwardsda.altostrat.com` (NEVER use `edwardsda@google.com`), Service Account `sa-reme-demo@antig-dave.iam.gserviceaccount.com`, and `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` in `.env` and environment when calling Google Cloud APIs or `gcloud`. Run unit/integration tests (`pytest`), local smoke and browser UI verification, `agents-cli eval run`, Cloud Run deployment (`reme-chat-demonstrator` in `europe-west1`), Agent Engine deployment (`agents-cli deploy` in `europe-west1`), Agent Registry verification (`gcloud agent-registry agents list`), and publishing to `pixel_mobile_demos` (`agents-cli publish gemini` with `--display-name "REME-Artificer"`), preserving all existing agents and datastores in `pixel_mobile_demos`.

## Verification Resources
- `docs/architecture/implementation-plan.md`
- `docs/architecture/Demo 1 - SA.md`
- `AGENTS.md`

## Acceptance Criteria

### Workspace, Datastore & BigQuery Infrastructure
- [ ] `agents-cli info` succeeds at `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` with `AGENTS.md` and `docs/` preserved, `.env` configured with `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`, `GOOGLE_CLOUD_LOCATION=europe-west1`, and `DISCOVERY_ENGINE_LOCATION=eu`, and `uv sync` completes cleanly.
- [ ] `scripts/setup_reme_datastore.py` uploads `gs://remedata/documents.jsonl`, indexes `ukd-reme-aesp-ds` (`location=eu`), verifies search against `ukd-reme-aesp-ds`, and patches `pixel_mobile_demos` `dataStoreIds` to include both `jointservicepubs` and `ukd-reme-aesp-ds` without removing `jointservicepubs`.
- [ ] `scripts/seed_demo1_bigquery.py` provisions `antig-dave.ukd_reme_demo` in `europe-west1` and seeds `ipc_nsn_catalogue`, `spta_sector_grids`, and `group_chat_tickets`, with non-empty table-level `description` and column-level `description` on every `bigquery.SchemaField`.

### Agent, Tools & Local Verification
- [ ] `app/tools.py` initializes `bigquery.Client()` and `google.auth.default()` at module import time, contains zero `gcloud` subprocess calls, queries `ukd-reme-aesp-ds` with `pageSize: 15` and `snippetSpec: {"returnSnippet": True}` without `summarySpec`, and implements deterministic Golden-Path Fallbacks for K60 (`5360-99-812-1740`), Jackal 2 (`5330-99-812-4410`), and Sector Bravo-4 (`51.2185, -1.7925`).
- [ ] `uv run pytest tests/unit/` passes all unit and FastAPI integration tests for `diagnose_and_resolve_grid`, `publish_ticket_to_chat`, golden-path fallbacks, and `/`, `/api/tickets`, and `/api/reset`.
- [ ] Local smoke testing with `agents-cli run` (Scene 1 & Scene 2) and browser UI verification on `http://localhost:8080` confirm the Native Structured Markdown Card (15s Audio Brief + 3 `<details open>` chips), live Ticket Card rendering, 1-tap Google Maps Universal URL, and `<1s` `[Reset Demo]` functionality.
- [ ] `agents-cli eval run` executes the Scene 1 (K60 & Jackal 2) and Scene 2 ("Publish to Group Chat") evaluation dataset in `tests/eval/datasets/basic-dataset.json`.

### Cloud Deployment & Shared Environment Safety
- [ ] All `gcloud` and Google Cloud API operations execute as `admin@edwardsda.altostrat.com` (never `edwardsda@google.com`) with `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` and runtime service account `sa-reme-demo@antig-dave.iam.gserviceaccount.com`.
- [ ] `reme-chat-demonstrator` is deployed to Cloud Run in `europe-west1` (`--min-instances 1 --max-instances 1 --allow-unauthenticated`) and responds to `GET /`, `GET/POST /api/tickets`, and `POST /api/reset`.
- [ ] `reme_artificer_agent` is deployed to Vertex AI Agent Engine in `europe-west1` via `agents-cli deploy`, listed in Agent Registry (`gcloud agent-registry agents list --project antig-dave --location europe-west1`), and published to `pixel_mobile_demos` as `"REME-Artificer"` via `agents-cli publish gemini`, with all pre-existing agents and `jointservicepubs` on `pixel_mobile_demos` intact.
