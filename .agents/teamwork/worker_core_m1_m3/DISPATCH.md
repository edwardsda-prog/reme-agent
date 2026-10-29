# Dispatch: Worker Core (M1 & M3 — Scaffolding, ADK 2.0 Agent/Tools, Cloud Run Chat App, Unit Tests, Eval Config & Deploy Script) — 2026-10-29T11:29:00Z

## Role & Identity
- **Identity**: `worker_core_m1_m3` (`teamwork_worker`)
- **Working Directory (metadata only)**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_core_m1_m3/`
- **Parent Orchestrator Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Required Reading Before Starting
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` (MANDATORY)
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md`
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/handoff.md`
6. Domain Skills:
   - `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-scaffold/SKILL.md`
   - `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-adk-code/SKILL.md`
   - `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-eval/SKILL.md`
   - `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-deploy/SKILL.md`
   - `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-publish/SKILL.md`

## Exclusive File Write Ownership
You have EXCLUSIVE write ownership of:
- Root scaffold/config files: `SPEC.md`, `.env`, `.env.example`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `.agents.yaml`, `agents-cli-manifest.yaml`
- `app/__init__.py`, `app/schemas.py`, `app/tools.py`, `app/agent.py`, `app/fast_api_app.py`
- `cloud_run_chat_app/main.py`, `cloud_run_chat_app/templates/index.html`, `cloud_run_chat_app/Dockerfile`, `cloud_run_chat_app/requirements.txt`
- `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/test_tools.py`, `tests/unit/test_chat_api.py`
- `tests/eval/eval_config.yaml`, `tests/eval/datasets/basic-dataset.json`
- `scripts/deploy_demo.sh`

**CRITICAL BOUNDARY**:
- Do NOT modify `AGENTS.md`, `PROJECT.md`, or `docs/`.
- Do NOT write to `scripts/setup_reme_datastore.py`, `scripts/seed_demo1_bigquery.py`, `TEST_INFRA.md`, `TEST_READY.md`, or `tests/e2e/` (owned by parallel agents).

## Deliverables & Execution Steps
1. **Phase 1 Scaffolding & Environment**:
   - Run `agents-cli scaffold create reme-artificer-agent --template base --region europe-west1 --output-dir /tmp/reme-scaffold --agent-guidance-filename AGENTS.md`
   - Copy scaffolded files into `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` WITHOUT overwriting `AGENTS.md`, `PROJECT.md`, or `docs/`.
   - Run `agents-cli scaffold enhance . --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md`
   - Ensure both `.agents.yaml` and `agents-cli-manifest.yaml` exist at root.
   - Create `SPEC.md`, `.env.example`, and `.env` per `docs/architecture/implementation-plan.md` Phase 1 (setting `GEMINI_APP_ID=projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952`, `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`, `GOOGLE_CLOUD_PROJECT=antig-dave`, `GOOGLE_CLOUD_LOCATION=europe-west1`, `DISCOVERY_ENGINE_LOCATION=eu`, `VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds`).
   - Update `pyproject.toml` with all required dependencies (`google-adk>=2.0.0`, `google-genai`, `google-cloud-bigquery`, `google-cloud-discoveryengine`, `google-cloud-storage`, `fastapi`, `uvicorn[standard]`, `jinja2`, `requests`, `httpx`, `pydantic>=2.0.0`, `pytest`) and run `uv sync`.
   - Verify `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli info` succeeds cleanly.
2. **Phase 4 (`app/schemas.py`, `app/tools.py`, `app/agent.py`, `app/__init__.py`)**:
   - Implement `ActiveTicketState` and `TicketPayload` in `app/schemas.py`.
   - Implement `app/tools.py` with:
     - Pre-warmed module-level `_BQ_CLIENT` and `_CREDENTIALS` singletons (zero `gcloud` subprocess calls!).
     - `GOLDEN_FALLBACK_K60` (`5360-99-812-1740`), `GOLDEN_FALLBACK_JACKAL` (`5330-99-812-4410`), `GOLDEN_FALLBACK_GRID` (`51.2185, -1.7925`).
     - `_search_aesp_datastore` querying `ukd-reme-aesp-ds` (`location=eu`) with `pageSize: 15`, `snippetSpec: {"returnSnippet": True}`, NO `summarySpec`, stripping `<b>`/`</b>` tags.
     - `diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext) -> dict` (no default values in signature; omit `tool_context` from docstring).
     - `publish_ticket_to_chat(tool_context: ToolContext) -> dict` — **IMPORTANT**: When inserting into `ukd_reme_demo.group_chat_tickets` via `_BQ_CLIENT.insert_rows_json`, filter the row dictionary to the exact 13 table columns (`ticket_id`, `created_at_utc`, `callsign`, `repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `coords_label`, `latitude`, `longitude`, `google_maps_url`, `status`) so `sector_display_name` does not cause a BigQuery unknown field error; while still keeping `sector_display_name` in the `TicketPayload` sent to Cloud Run and returned to the agent!
   - Implement `app/agent.py` with `reme_artificer_agent` (`LlmAgent`, `model="gemini-2.5-flash"`, `temperature=0.0`) and export `root_agent = reme_artificer_agent` in both `app/agent.py` and `app/__init__.py`.
3. **Phase 5 (`cloud_run_chat_app/`)**:
   - Implement `cloud_run_chat_app/main.py` (`GET /`, `GET /api/tickets`, `POST /api/tickets`, `POST /api/reset`, `POST /api/tickets/reset`, filtering BQ insert rows to the 13 `group_chat_tickets` columns).
   - Implement `cloud_run_chat_app/templates/index.html` (dark-mode tactical UI `OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT`, `[Reset Demo]` button, 1000ms live polling, and BOTH Google Maps Universal URL links: primary 1-tap driving directions button `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving` and secondary map pin link `https://www.google.com/maps/search/?api=1&query={lat},{lng}`).
   - Implement `cloud_run_chat_app/requirements.txt` and `cloud_run_chat_app/Dockerfile`.
4. **Phase 6 (`tests/unit/test_tools.py`, `tests/unit/test_chat_api.py`)**:
   - Write comprehensive unit & FastAPI integration tests covering `diagnose_and_resolve_grid` (K60, Jackal 2, Golden-Path fallback, HTML tag stripping, `pageSize: 15`, no `summarySpec`), `publish_ticket_to_chat` (with active state, fallback without prior state, 13-column BQ insert filtering), and FastAPI `/`, `GET /api/tickets`, `POST /api/tickets`, `POST /api/reset`, `POST /api/tickets/reset` (`<1s`).
   - Run `uv run pytest tests/unit/ -v` and verify 100% pass.
5. **Phase 7 & 8 Configs (`tests/eval/`, `scripts/deploy_demo.sh`)**:
   - Create `tests/eval/eval_config.yaml` and `tests/eval/datasets/basic-dataset.json` (using `agents-cli 1.12.0` schema verified in `teamwork_spec_miner_survey_2/handoff.md`).
   - Create `scripts/deploy_demo.sh` (`chmod +x`) using the verified `agents-cli 1.12.0` flags (no `--no-confirm-project` on `agents-cli deploy`; `--gemini-enterprise-app-id "projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952"` on `agents-cli publish gemini`).
6. Write your `progress.md` and `handoff.md` in `.agents/teamwork/worker_core_m1_m3/` and notify parent (`6f912669-38e4-4574-904f-704d623a5d01`) via `send_message`.


## 2026-10-29T11:31:04Z
You are `worker_core_m1_m3` (`teamwork_worker`), assigned to implement Milestones M1 and M3 (Root `agents-cli` ADK 2.0 Scaffolding, Environment Config, `app/*`, `cloud_run_chat_app/*`, Unit Tests `tests/unit/*`, Eval Config `tests/eval/*`, and Deployment Script `scripts/deploy_demo.sh`).
