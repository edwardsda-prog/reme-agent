# Dispatch — Sub-Orchestrator M1 (`sub_orch_m1`)

## Identity & Paths
- **Your Identity**: `sub_orch_m1` (Sub-orchestrator for Milestone 1)
- **Hierarchy Level**: Sub-orchestrator
- **Your Working Directory**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_m1/`
- **Parent Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`
- **Original Request Path**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
- **Project Scope Document**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`

## Files to Read First
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/handoff.md`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_explorer_survey_3/handoff.md`

## Assigned Scope: Milestone 1 (M1) — Workspace Scaffolding, ADK 2.0 Core & Tool Unit Tests
You own **Features 1, 2, 3, 13, 14, 15, 16, 17, and 20 (tools)** from `PROJECT.md`:
1. **Root `agents-cli` Scaffolding & Environment Setup**:
   - Run two-step `agents-cli` scaffolding (`agents-cli scaffold create reme-artificer-agent --output-dir /tmp --agent adk --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md --prototype`, copy scaffold files to `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` WITHOUT overwriting `AGENTS.md`, `PROJECT.md`, or `docs/`, then run `agents-cli scaffold enhance . --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md`).
   - Also create `agents-cli-manifest.yaml` (alongside `.agents.yaml`) and `SPEC.md` at the root so both `agents-cli info` and any file check for `agents-cli-manifest.yaml` and `SPEC.md` pass.
   - Create `.env.example` and `.env` at the workspace root with the exact 12 environment variables from `PROJECT.md § Interface Contracts` (`GOOGLE_API_USE_CLIENT_CERTIFICATE=false`, `GOOGLE_CLOUD_LOCATION=europe-west1`, `DISCOVERY_ENGINE_LOCATION=eu`, `VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds`, `GEMINI_APP_ID=projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952`, etc.).
   - Update `pyproject.toml` with all required dependencies (`google-adk>=2.0.0`, `google-genai`, `google-cloud-bigquery`, `google-cloud-discoveryengine`, `google-cloud-storage`, `fastapi`, `uvicorn[standard]`, `jinja2`, `requests`, `httpx`, `pydantic>=2.0.0`, `pytest`) and run `uv sync`.
   - Verify `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli info` succeeds at `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`.
2. **ADK 2.0 Schemas, Composite Tools & Agent (`app/`)**:
   - `app/schemas.py`: Implement strict Pydantic v2 models `ActiveTicketState` and `TicketPayload` per `PROJECT.md § Interface Contracts`.
   - `app/tools.py`:
     - Pre-warm `_BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)` and `_CREDENTIALS, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])` at module import time (gracefully handling isolated test environments if ADC is mocked).
     - **ZERO `gcloud` subprocess calls** anywhere in `app/`.
     - Implement `diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext) -> dict` (no default parameter values, `tool_context` omitted from docstring):
       - Queries `https://eu-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/servingConfigs/default_search:search` with `pageSize: 15`, `contentSearchSpec: {"snippetSpec": {"returnSnippet": True}}`, NO `summarySpec`, and header `"X-Goog-User-Project": PROJECT_ID`.
       - Strips `<b>` and `</b>` tags and normalizes whitespace in snippets.
       - Queries `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` (`@query`) and `antig-dave.ukd_reme_demo.spta_sector_grids` (`@grid`) in `europe-west1`.
       - Deterministic Golden-Path Fallbacks: `GOLDEN_FALLBACK_JACKAL` (`5330-99-812-4410`) when `"409"` or `"jackal"` in `fault_query.lower()`, else `GOLDEN_FALLBACK_K60` (`5360-99-812-1740`), and `GOLDEN_FALLBACK_GRID` (`51.2185, -1.7925`).
       - Saves state to `tool_context.state["active_ticket"]` and returns the dict.
     - Implement `publish_ticket_to_chat(tool_context: ToolContext) -> dict`:
       - Reads `tool_context.state.get("active_ticket")` or merges `{**GOLDEN_FALLBACK_K60, **GOLDEN_FALLBACK_GRID}`.
       - Builds `TicketPayload` (`TKT-REME-XXXX`, `callsign="Cpl MacDonald (4 Bn REME FRT)"`, `google_maps_url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"`, `status="DISPATCH_READY"`).
       - POSTs to `{CLOUD_RUN_CHAT_URL}/api/tickets` (`timeout=2.0`).
       - Inserts the exact 13 table columns (`ticket_id`, `created_at_utc`, `callsign`, `repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `coords_label`, `latitude`, `longitude`, `google_maps_url`, `status`) into `antig-dave.ukd_reme_demo.group_chat_tickets`.
       - Returns `{"published": True, "ticket": payload_dict, "confirmation_badge": f"✅ Ticket {ticket_id} Published to 4 Bn REME Group Chat"}`.
   - `app/agent.py` & `app/__init__.py` & `app/fast_api_app.py`:
     - Define `reme_artificer_agent = LlmAgent(name="reme_artificer_agent", model="gemini-2.5-flash", instruction=SYSTEM_INSTRUCTION, tools=[diagnose_and_resolve_grid, publish_ticket_to_chat], generate_content_config=types.GenerateContentConfig(temperature=0.0))` and export `root_agent = reme_artificer_agent`.
     - Ensure `SYSTEM_INSTRUCTION` renders the exact Scene 2 Native Structured Markdown Card (15s Audio Brief + 3 `<details open>` chips) and Scene 2 publish confirmation badge.
     - Ensure `app/fast_api_app.py` defines `App(name="app", root_agent=root_agent)`.
3. **Unit Tests (`tests/unit/test_tools.py`)**:
   - Implement comprehensive unit tests in `tests/unit/test_tools.py` covering module singletons, zero `gcloud` subprocesses, K60 & Jackal 2 diagnosis, Golden-Path Fallbacks, `pageSize: 15` + `snippetSpec` without `summarySpec`, `<b>`/`</b>` HTML stripping, and `publish_ticket_to_chat` (with and without prior session state).
   - Verify `uv run pytest tests/unit/test_tools.py` passes 100%.

## Exclusive File Write Ownership
You and your Worker own ONLY:
- `SPEC.md`, `.env`, `.env.example`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `agents-cli-manifest.yaml`, `.agents.yaml`
- `app/**` (`__init__.py`, `schemas.py`, `tools.py`, `agent.py`, `fast_api_app.py`)
- `tests/unit/test_tools.py`
Do NOT modify `AGENTS.md`, `PROJECT.md`, `docs/`, `scripts/`, `cloud_run_chat_app/`, `tests/unit/test_chat_api.py`, or `tests/e2e/`.

## Sub-Orchestrator Procedure
This scope fits a single **2B Iteration Loop**:
1. Create `BRIEFING.md`, `progress.md`, and `SCOPE.md` in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_m1/`.
2. Run **2B Iteration Loop** (`3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate` in `GATE_STATUS.md`), passing `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` to every subagent and the mandatory integrity warning to your Worker.
3. When the Gate passes (`PASS`), write your `handoff.md` and send a completion message via `send_message` to `6f912669-38e4-4574-904f-704d623a5d01`.
