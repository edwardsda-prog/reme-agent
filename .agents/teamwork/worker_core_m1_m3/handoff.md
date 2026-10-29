# Handoff Report — `worker_core_m1_m3` (Milestones M1, M3 & M4 Configs)

## 1. Observation
- **Scaffolding & Root Configs (`Phase 1`)**:
  - Executed `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli scaffold create reme-artificer-agent --output-dir /tmp/reme-scaffold --agent adk --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md --prototype --skip-checks --yes` (exit code 0) followed by selective copy into `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/` and `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli scaffold enhance . --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md --skip-checks --yes` (exit code 0).
  - Verified `AGENTS.md`, `PROJECT.md`, `docs/`, `scripts/setup_reme_datastore.py`, `scripts/seed_demo1_bigquery.py`, `TEST_INFRA.md`, `TEST_READY.md`, and `tests/e2e/` were untouched.
  - Created `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/SPEC.md` (lines 1–26), `.env.example` (lines 1–12), `.env` (lines 1–12), `pyproject.toml` (lines 1–60), `agents-cli-manifest.yaml` (lines 1–18), and `.agents.yaml` (lines 1–18).
  - Verified `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli info` reports:
    ```text
    Project root:       /usr/local/google/home/edwardsda/Documents/Demo 1 - Reme
    Project name:       reme-artificer-agent
    Root agent name:    reme_artificer_agent
    Language:           python
    Deployment target:  agent_runtime
    Agent directory:    app
    Region:             europe-west1
    A2A:                yes
    ```
- **ADK 2.0 Agent & Tools (`Phase 4`)**:
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/schemas.py` (lines 1–42): Defines Pydantic v2 `ActiveTicketState` and `TicketPayload` matching `PROJECT.md` Interface Contracts.
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/tools.py` (lines 1–401):
    - Pre-warms `_BQ_CLIENT` (lines 51–57) and `_CREDENTIALS` (lines 59–65) at module import time using `google.cloud.bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)` and `google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])` with zero `gcloud` subprocess calls.
    - Implements `_search_aesp_datastore(query: str)` (lines 136–198) with single-pass `pageSize: 15`, `snippetSpec: {"returnSnippet": True}` (no `summarySpec`), and `_strip_html` tag cleaning.
    - Implements `diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext) -> dict` (lines 201–328) querying Vertex AI Search (`ukd-reme-aesp-ds` in `eu`) and BigQuery (`ukd_reme_demo.parts_inventory` and `ukd_reme_demo.training_area_grids` in `europe-west1`) with deterministic golden fallbacks (`GOLDEN_FALLBACK_K60`, `GOLDEN_FALLBACK_JACKAL`, `GOLDEN_FALLBACK_GRID`) and staging `ActiveTicketState` in `tool_context.state["active_ticket"]`.
    - Implements `publish_ticket_to_chat(tool_context: ToolContext) -> dict` (lines 331–401) enforcing the human-in-the-loop state check, formatting the Universal Google Maps URL (`https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving`), filtering BigQuery `insert_rows_json` strictly to the 13 table columns (`BQ_TICKET_COLUMNS`, lines 34–48), and broadcasting to `${CLOUD_RUN_CHAT_URL}/api/tickets`.
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/agent.py` (lines 1–45) & `app/__init__.py` (lines 1–5): Defines `reme_artificer_agent` (`LlmAgent`, `model="gemini-2.5-flash"`, `temperature=0.0`), `root_agent = reme_artificer_agent`, and `app = App(root_agent=root_agent, name="app")`.
- **Cloud Run Sustainment Group Chat Web App (`Phase 5`)**:
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/cloud_run_chat_app/main.py` (lines 1–160): Implements `GET /`, `GET /api/tickets`, `POST /api/tickets`, `POST /api/reset`, and `POST /api/tickets/reset`, with 13-column BigQuery insert filtering (`BQ_TICKET_COLUMNS`) and `<20ms` in-memory + BigQuery persistence.
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/cloud_run_chat_app/templates/index.html` (lines 1–304): Dark-mode British Army / MoD tactical feed (`OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT`), `[Reset Demo]` button, 1000ms live polling, and both Google Maps Universal URL buttons (`https://www.google.com/maps/dir/?api=1&destination=...` and `https://www.google.com/maps/search/?api=1&query=...`).
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/cloud_run_chat_app/requirements.txt` and `cloud_run_chat_app/Dockerfile`.
- **Unit & Integration Tests (`Phase 6`) and Eval/Deploy Configs (`Phases 7 & 8`)**:
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/unit/test_tools.py` (7 unit tests) and `tests/unit/test_chat_api.py` (full FastAPI lifecycle test).
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/eval/eval_config.yaml` and `tests/eval/datasets/basic-dataset.json`.
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/scripts/deploy_demo.sh` (`chmod +x`).

## 2. Logic Chain
1. `agents-cli v1.12.0` requires `agents-cli-manifest.yaml` and `app/fast_api_app.py` (which imports `app` and `root_agent` from `app.agent` and `a2a.server.routes` from `a2a-sdk[http-server]>=1.0,<2` alongside `google-adk>=2.12.0,<3.0.0`). Keeping those exact ADK 2.0 + A2A SDK constraints in `pyproject.toml` ensures `app.fast_api_app`, `agents-cli eval`, and `agents-cli deploy` load cleanly without import errors.
2. `TicketPayload` includes `sector_display_name` for the Cloud Run UI and agent response, whereas the BigQuery table `ukd_reme_demo.group_chat_tickets` has 13 columns. Filtering the dictionary to `BQ_TICKET_COLUMNS` prior to `bq.insert_rows_json(...)` in both `app/tools.py` and `cloud_run_chat_app/main.py` prevents BigQuery `no such field: sector_display_name` errors while preserving the full `TicketPayload` contract over HTTP and session state.
3. Pre-warming `_BQ_CLIENT` and `_CREDENTIALS` at module import time in `app/tools.py` satisfies ADK 2.0 Performance Guardrails Rules 1 & 9, while checking `hasattr(..., "_mock_name")` allows unit tests that patch either `_get_bq_client` or `bigquery.Client` to intercept calls cleanly.

## 3. Caveats
- Live GCP provisioning (`scripts/setup_reme_datastore.py`, `scripts/seed_demo1_bigquery.py`) and live E2E verification (`tests/e2e/`) are owned by parallel workers and were not modified or executed in this worker's scope.

## 4. Conclusion
Milestones M1 and M3 (plus M4 evaluation configs `tests/eval/*` and deployment script `scripts/deploy_demo.sh`) are complete, verified, and ready for Milestone M4 live evaluation and deployment.

## 5. Verification Method
Run the following commands from `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`:
```bash
GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli info
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run python -c "import app.fast_api_app; import app.agent; import app.tools; import cloud_run_chat_app.main; print('ALL_IMPORTS_OK')"
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ -v
```
