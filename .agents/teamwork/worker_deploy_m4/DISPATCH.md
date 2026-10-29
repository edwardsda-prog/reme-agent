# Dispatch: Worker Remediation, Evaluation, Cloud Deployment & E2E Pass (`worker_deploy_m4`) — 2026-10-29T12:11:00Z

## Role & Identity
- **Identity**: `worker_deploy_m4` (`teamwork_worker`)
- **Working Directory (metadata only)**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_deploy_m4/`
- **Parent Orchestrator Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Required Reading Before Starting
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` (MANDATORY)
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_READY.md` (Section 4: Escalated Implementation Defects)
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/test_writer_e2e_1/handoff.md`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md` (Phases 4, 5, 6, 7, 8)
6. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/handoff.md` (`agents-cli 1.12.0` CLI flags and eval schema)

## Exclusive File Write Ownership
You have EXCLUSIVE write ownership of:
- `app/schemas.py`, `app/tools.py`, `app/agent.py`, `app/__init__.py`
- `cloud_run_chat_app/main.py`, `cloud_run_chat_app/templates/index.html`, `cloud_run_chat_app/Dockerfile`, `cloud_run_chat_app/requirements.txt`
- `tests/unit/test_tools.py`, `tests/unit/test_chat_api.py`
- `tests/eval/eval_config.yaml`, `tests/eval/datasets/basic-dataset.json`
- `scripts/deploy_demo.sh`
- `.env`

**CRITICAL BOUNDARY**:
- Do NOT modify `AGENTS.md`, `PROJECT.md`, `docs/`, `TEST_INFRA.md`, `TEST_READY.md`, or `tests/e2e/*`! You must fix the implementation files so that all 256 opaque-box E2E tests in `tests/e2e/` pass genuinely.
- Always use `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` and active `gcloud` account `admin@edwardsda.altostrat.com` (NEVER `edwardsda@google.com`).

## Step-by-Step Deliverables

### Step 1: Fix the 6 Implementation Contract Discrepancies (`TEST_READY.md § 4`)
1. **`app/schemas.py`**:
   - Ensure `ActiveTicketState` includes `rag_snippets: list[str] = Field(default_factory=list)` and exact fields per `PROJECT.md § Interface Contracts 2` (`repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `sector_display_name`, `latitude`, `longitude`, `coords_label`, `rag_snippets`).
   - Ensure `TicketPayload` sets `callsign: str = "Cpl MacDonald (4 Bn REME FRT)"`, `sector_display_name: Optional[str] = "Salisbury Plain (SPTA) — Sector Bravo-4"`, and `status: str = "DISPATCH_READY"`.
2. **`app/tools.py`**:
   - Keep module-level pre-warmed `_BQ_CLIENT` and `_CREDENTIALS` singletons and zero `gcloud` subprocess calls.
   - Fix `GOLDEN_FALLBACK_K60` to exact values from `docs/architecture/implementation-plan.md` Phase 4.2:
     - `repair_classification`: `"Unit / FRT Level 2 Repair"`
     - `aesp_reference`: `"AESP 2350-T-250-523 (Ch 1-2, Para 17.4, Page 14)"`
     - `part_name`: `"Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)"`
     - `nsn`: `"5360-99-812-1740"`
     - `technical_limits`: `"Free length 79.4 mm; replace if compressed under 54.6 mm at 40 lbs load — do NOT pack with washers."`
   - Fix `GOLDEN_FALLBACK_JACKAL` to exact values from `docs/architecture/implementation-plan.md` Phase 4.2:
     - `repair_classification`: `"Unit / FRT Level 2 Repair"`
     - `aesp_reference`: `"AESP 2320-J-100-522 (Para 4.12)"`
     - `part_name`: `"Hydraulic Manifold High-Pressure Seal Kit"`
     - `nsn`: `"5330-99-812-4410"`
     - `technical_limits`: `"Replace O-ring and backup ring; torque manifold bolts to 45 Nm; pressure test to 250 bar."`
   - Fix `GOLDEN_FALLBACK_GRID` to exact values from `docs/architecture/implementation-plan.md` Phase 4.2:
     - `sector_display_name`: `"Salisbury Plain (SPTA) — Sector Bravo-4"`
     - `latitude`: `51.2185`
     - `longitude`: `-1.7925`
     - `coords_label`: `"51.2185° N, 1.7925° W (Salisbury Plain — Sector Bravo-4)"`
   - In `diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext) -> dict`:
     - Do NOT mention `tool_context` in the docstring.
     - Query `ukd_reme_demo.ipc_nsn_catalogue` and `ukd_reme_demo.spta_sector_grids` in `europe-west1` using parameterized SQL (`bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("query", "STRING", fault_query)])` and `bigquery.ScalarQueryParameter("grid", "STRING", spoken_sector_grid)`).
     - Construct `ActiveTicketState(**part_record, **grid_record, rag_snippets=rag_snippets)`, store `ticket_state.model_dump()` in `tool_context.state["active_ticket"]`, and return `ticket_state.model_dump()` (flat dictionary with `repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `sector_display_name`, `latitude`, `longitude`, `coords_label`, `rag_snippets`).
   - In `publish_ticket_to_chat(tool_context: ToolContext) -> dict`:
     - Do NOT mention `tool_context` in the docstring.
     - Read `active = tool_context.state.get("active_ticket") if tool_context and hasattr(tool_context, "state") else None`. If not `active`, fall back to `{**GOLDEN_FALLBACK_K60, **GOLDEN_FALLBACK_GRID}`.
     - Generate `ticket_id = f"TKT-REME-{uuid.uuid4().hex[:4].upper()}"`.
     - Build `TicketPayload` with `google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"`.
     - POST `payload.model_dump()` to `{CLOUD_RUN_CHAT_URL}/api/tickets` (`timeout=2.0`).
     - Filter row dict to the 13 `group_chat_tickets` columns (`BQ_TICKET_COLUMNS`) before calling `bq_client.insert_rows_json(f"{PROJECT_ID}.{BQ_DATASET}.group_chat_tickets", [bq_row])`.
     - Return `{"published": True, "ticket": payload.model_dump(), "confirmation_badge": f"✅ Ticket {ticket_id} Published to 4 Bn REME Group Chat"}`.
3. **`app/agent.py`**:
   - Update `SYSTEM_INSTRUCTION` per `docs/architecture/implementation-plan.md` Phase 4.3 so it includes the exact Scene 2 Native Structured Markdown Card header (`### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card`), `🔊 **15s Audio Brief:**`, the 3 `<details open>` collapsible sections (`Chip 1 — Repair Classification`, `Chip 2 — Part Name & NSN`, `Chip 3 — Technical Limits`), the warning `do NOT pack with washers`, and the Scene 2 confirmation badge.
4. **`cloud_run_chat_app/main.py`**:
   - `POST /api/tickets` must return HTTP `200` (not 201) with `{"status": "published", "ticket": ticket_dict}` and ensure that if a duplicate `ticket_id` is posted, any existing entry with that `ticket_id` is removed and the new entry is inserted at index `0` (`ACTIVE_TICKETS.insert(0, ticket_dict)`).
   - `POST /api/reset` and `POST /api/tickets/reset` must clear `ACTIVE_TICKETS.clear()` in-memory immediately (`<1s`, no BigQuery DELETE query!) and return HTTP `200` `{"status": "reset", "tickets": []}`.
5. **`tests/unit/test_tools.py` & `tests/unit/test_chat_api.py`**:
   - Update unit tests to match the authoritative `PROJECT.md` / `implementation-plan.md` contracts (`5360-99-812-1740`, `5330-99-812-4410`, `51.2185, -1.7925`, flat `ActiveTicketState` dict, `TKT-REME-`, HTTP 200 `published`, `reset` -> `[]`).
6. **`tests/eval/datasets/basic-dataset.json` & `scripts/deploy_demo.sh`**:
   - Update `tests/eval/datasets/basic-dataset.json` to include all 3 evaluation cases (`scene1_k60_oil_pressure_diagnosis` with `5360-99-812-1740` & `79.4 mm` & `54.6 mm`, `scene1_jackal2_409_3211_diagnosis` with `5330-99-812-4410` & `250 bar`, and `scene2_publish_ticket_to_chat` with `publish_ticket_to_chat` & `Published to 4 Bn REME Group Chat`) in valid `agents-cli eval` format (`eval_set_id` + `eval_cases`).
   - Update `scripts/deploy_demo.sh` per `docs/architecture/implementation-plan.md` Phase 8 (with `CHAT_SERVICE_NAME="reme-chat-demonstrator"`, `SA_EMAIL="sa-reme-demo@antig-dave.iam.gserviceaccount.com"`, `--min-instances 1 --max-instances 1 --allow-unauthenticated`, `agents-cli deploy` without `--no-confirm-project`, `gcloud agent-registry agents list`, and `agents-cli publish gemini` with `--gemini-enterprise-app-id "projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952"` and `--display-name "REME-Artificer"`).

### Step 2: Run Unit & Full 256-Test E2E Suite
- Run `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v` and fix any remaining issues in your owned files until **100% of unit tests AND 256/256 E2E tests pass**!

### Step 3: Phase 7 Local Smoke Testing, UI Verification & `agents-cli eval run`
- Start `cloud_run_chat_app` locally on `127.0.0.1:8080`, verify `GET /`, `POST /api/tickets`, `GET /api/tickets`, and `POST /api/reset` (`<1s`).
- Run a local smoke test of `reme_artificer_agent` (Scene 1 K60 diagnosis + Scene 2 publish to group chat) against `http://localhost:8080` and verify the ticket arrives in `http://localhost:8080/api/tickets`.
- Run `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli eval run tests/eval/datasets/basic-dataset.json --config tests/eval/eval_config.yaml --project antig-dave` and record the results.

### Step 4: Phase 8 Live Cloud Deployment & Registration
- Deploy `reme-chat-demonstrator` to Cloud Run in `europe-west1`:
  ```bash
  GOOGLE_API_USE_CLIENT_CERTIFICATE=false gcloud run deploy reme-chat-demonstrator \
    --source ./cloud_run_chat_app \
    --project antig-dave \
    --region europe-west1 \
    --service-account sa-reme-demo@antig-dave.iam.gserviceaccount.com \
    --allow-unauthenticated \
    --min-instances 1 \
    --max-instances 1 \
    --set-env-vars "GCP_PROJECT_ID=antig-dave,BQ_DATASET=ukd_reme_demo,BQ_LOCATION=europe-west1,GOOGLE_API_USE_CLIENT_CERTIFICATE=false" \
    --quiet
  ```
- Capture `CHAT_URL`, update `CLOUD_RUN_CHAT_URL` in `.env`, and verify `GET ${CHAT_URL}/`, `POST ${CHAT_URL}/api/tickets`, `GET ${CHAT_URL}/api/tickets`, and `POST ${CHAT_URL}/api/reset`.
- Deploy `reme_artificer_agent` to Vertex AI Agent Engine in `europe-west1` via `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli deploy --target agent_runtime --project antig-dave --region europe-west1 --env-vars "GOOGLE_CLOUD_PROJECT=antig-dave,GCP_PROJECT_ID=antig-dave,GOOGLE_CLOUD_LOCATION=europe-west1,BQ_DATASET=ukd_reme_demo,BQ_LOCATION=europe-west1,DISCOVERY_ENGINE_LOCATION=eu,VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds,CLOUD_RUN_CHAT_URL=${CHAT_URL},GOOGLE_API_USE_CLIENT_CERTIFICATE=false"`.
- Verify Agent Registry in `europe-west1`:
  `GOOGLE_API_USE_CLIENT_CERTIFICATE=false gcloud agent-registry agents list --project antig-dave --location europe-west1`
- Publish `"REME-Artificer"` to `pixel_mobile_demos` (`pixel-mobile-demos_1793177711952`):
  `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli publish gemini --agent-runtime-id "${AGENT_ENGINE_ID}" --gemini-enterprise-app-id "projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952" --display-name "REME-Artificer" --description "UK Defence 4 Bn REME Tactical Sustainment & AESP 2350-T-250-523 Artificer Agent" --project antig-dave --region europe-west1`
  (If `agents-cli publish gemini` needs fallback or verification, also verify via `GET https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents` that `"REME-Artificer"` is registered and pre-existing agents `13073824185441632570` and `deep_research` are untouched).
- Re-run `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v` to confirm 100% pass after `.env` update!
- Write `handoff.md` in `.agents/teamwork/worker_deploy_m4/handoff.md` and notify parent (`6f912669-38e4-4574-904f-704d623a5d01`) via `send_message`.


## 2026-10-29T12:13:31Z
You are `worker_deploy_m4` (Remediation, Evaluation, Cloud Deployment & E2E Pass Worker).
Your working directory for metadata (`progress.md`, `handoff.md`) is: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_deploy_m4/`
Your Parent Orchestrator Conversation ID is: `6f912669-38e4-4574-904f-704d623a5d01`

Execute all 4 steps in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_deploy_m4/DISPATCH.md`.
