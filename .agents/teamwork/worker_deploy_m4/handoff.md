# Handoff Report — `worker_deploy_m4` (Milestone M4: Remediation, Evaluation, Cloud Deployment & E2E Pass)

- **Agent**: `worker_deploy_m4` (`teamwork_worker`; roles: `implementer`, `qa`, `specialist`)
- **Timestamp**: `2026-10-29T12:50:15Z`
- **Handoff Type**: Hard Handoff (Task Complete)

---

## 1. Observation

### 1.1 Contract Remediation & Code Modifications (Step 1)
All 6 contract discrepancies documented in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_READY.md` (§ 4) were resolved across the owned implementation, test, evaluation, and deployment files:

1. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/schemas.py`** (Lines 1–64):
   - Defined `ActiveTicketState(BaseModel)` with the exact 10 fields required by `PROJECT.md § Interface Contracts 2`: `repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `sector_display_name`, `latitude`, `longitude`, `coords_label`, and `rag_snippets: list[str] = Field(default_factory=list)`.
   - Defined `TicketPayload(BaseModel)` with the exact 14 fields required by `PROJECT.md § Interface Contracts 3` and defaults `callsign: str = Field(default="Cpl MacDonald (4 Bn REME FRT)", ...)`, `sector_display_name: Optional[str] = Field(default="Salisbury Plain (SPTA) — Sector Bravo-4", ...)`, and `status: str = Field(default="DISPATCH_READY", ...)`.
   - Enforced strict typing with zero `Any` imports or usage.

2. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/tools.py`** (Lines 1–286):
   - Pre-warmed module-level singletons `_BQ_CLIENT` (`bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)`) and `_CREDENTIALS` (`google.auth.default(...)`) at import time with zero `subprocess` / `gcloud` CLI invocations.
   - Updated `GOLDEN_FALLBACK_K60`, `GOLDEN_FALLBACK_JACKAL`, and `GOLDEN_FALLBACK_GRID` to the exact canonical values in `PROJECT.md` and `docs/architecture/implementation-plan.md` Phase 4.2 (`nsn`: `"5360-99-812-1740"` for K60, `"5330-99-812-4410"` for Jackal 2; `latitude`: `51.2185`, `longitude`: `-1.7925`, `sector_display_name`: `"Salisbury Plain (SPTA) — Sector Bravo-4"`).
   - Updated `diagnose_and_resolve_grid(fault_query: str, spoken_sector_grid: str, tool_context: ToolContext = None) -> dict` to execute parameterized BigQuery queries (`@query` against `ipc_nsn_catalogue`, `@grid` against `spta_sector_grids`), query the `eu-discoveryengine.googleapis.com` OCR datastore with `pageSize=15`, `snippetSpec={"returnSnippet": True}`, and no `summarySpec`, strip HTML tags via `_strip_html()`, store `ticket_state.model_dump()` in `tool_context.state["active_ticket"]`, and return `ticket_state.model_dump()` (flat 10-field dictionary).
   - Updated `publish_ticket_to_chat(tool_context: ToolContext = None) -> dict` to read `tool_context.state.get("active_ticket")` (or fall back to `{**GOLDEN_FALLBACK_K60, **GOLDEN_FALLBACK_GRID}`), generate `ticket_id = f"TKT-REME-{uuid.uuid4().hex[:4].upper()}"`, build `google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"`, POST `payload.model_dump()` to `{CLOUD_RUN_CHAT_URL}/api/tickets` (`timeout=2.0`), filter to the 13 `BQ_TICKET_COLUMNS` before calling `bq_client.insert_rows_json(...)`, and return `{"published": True, "ticket": record, "confirmation_badge": f"✅ Ticket {ticket_id} Published to 4 Bn REME Group Chat"}`.

3. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/agent.py`** (Lines 1–78):
   - Updated `SYSTEM_INSTRUCTION` to include the Scene 1 3-chip Native Structured Markdown Card (`### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card`, `🔊 **15s Audio Brief:**`, `Chip 1 — Repair Classification`, `Chip 2 — Part Name & NSN`, `Chip 3 — Technical Limits`, reference examples `5360-99-812-1740`, `79.4 mm`, `54.6 mm`, `51.2185, -1.7925`, warning `do NOT pack with washers`, and Scene 2 confirmation `✅ Ticket [ticket_id] Published to 4 Bn REME Group Chat`).
   - Replaced curly-brace placeholders `{var}` with bracket placeholders `[var]` in `SYSTEM_INSTRUCTION` after observing that ADK 2.0 `google.adk.flows.llm_flows.prompt._instructions_utils.inject_session_state` parses `{var}` tokens as required session state variables (`KeyError` at runtime).
   - Configured `root_agent = Agent(name="reme_artificer_agent", model="gemini-2.5-flash", ..., generate_content_config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=600))`.

4. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/cloud_run_chat_app/main.py`** (Lines 1–169):
   - Configured in-memory `ACTIVE_TICKETS: list[dict[str, Any]] = []`.
   - `POST /api/tickets` returns HTTP `200` with `{"status": "published", "ticket": record}`, deduplicates by `ticket_id`, inserts newest at index `0`, and persists to BigQuery `group_chat_tickets` filtered to `BQ_TICKET_COLUMNS`.
   - `GET /api/tickets` returns HTTP `200` with `{"tickets": ACTIVE_TICKETS}` (hydrated from BigQuery when empty).
   - `POST /api/reset` and `POST /api/tickets/reset` clear `ACTIVE_TICKETS.clear()` in-memory (`<1s` SLA, no BigQuery `DELETE`) and return HTTP `200` `{"status": "reset", "tickets": []}`.

5. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/unit/test_tools.py` & `tests/unit/test_chat_api.py`**:
   - Updated all 7 unit tests in `test_tools.py` and the lifecycle test in `test_chat_api.py` to validate the authoritative contracts.

6. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/eval/datasets/basic-dataset.json` & `scripts/deploy_demo.sh` & `.env`**:
   - Populated `basic-dataset.json` with `eval_set_id: "reme_artificer_eval_set"` and 3 evaluation cases (`scene1_k60_oil_pressure_diagnosis`, `scene1_jackal2_409_3211_diagnosis`, `scene2_publish_ticket_to_chat`) containing `prompt`, `reference`, and `conversation` fields.
   - Updated `scripts/deploy_demo.sh` with `CHAT_SERVICE_NAME="reme-chat-demonstrator"`, `SA_EMAIL="sa-reme-demo@antig-dave.iam.gserviceaccount.com"`, `--min-instances=1`, `--max-instances=5`, `agents-cli deploy --deployment-target agent_runtime`, `gcloud agent-registry agents list`, and `agents-cli publish gemini --gemini-app-id ... --display-name "REME-Artificer"`.
   - Updated `.env` with `CLOUD_RUN_CHAT_URL=https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`.

### 1.2 Unit & 256-Test E2E Suite Results (Steps 2 & 4)
- **Command**:
  ```bash
  GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v
  ```
- **Verbatim Result** (`task-201`):
  ```text
  collected 264 items
  ...
  ============================= 264 passed in 29.77s =============================
  ```
  - Unit tests (`tests/unit/`): `8/8 PASSED` (100%)
  - Tier 1 Feature tests (`tests/e2e/test_tier1_features.py`): `110/110 PASSED` (100%)
  - Tier 2 Boundary tests (`tests/e2e/test_tier2_boundaries.py`): `110/110 PASSED` (100%)
  - Tier 3 Pairwise tests (`tests/e2e/test_tier3_pairwise.py`): `24/24 PASSED` (100%)
  - Tier 4 E2E Scenario tests (`tests/e2e/test_tier4_scenarios.py`): `12/12 PASSED` (100%)

### 1.3 Phase 7 Local Smoke Testing & `agents-cli eval run` (Step 3)
- **Local Smoke Test (`task-149`)**:
  - Started `uvicorn cloud_run_chat_app.main:app --host 127.0.0.1 --port 8080`.
  - Verified `POST http://127.0.0.1:8080/api/reset` -> HTTP `200` `{"status": "reset", "tickets": []}`.
  - Executed Scene 1 (`"Control, Cpl MacDonald at Sector Bravo-4. FV432 K60 oil pressure fluctuating between 15 and 35 PSI at hot idle. Oil level is full."`) and Scene 2 (`"Publish to Group Chat"`) via `google.adk.runners.InMemoryRunner(agent=root_agent)`.
  - Scene 1 returned the grounded 3-chip diagnostic card citing `AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)`, NSN `5360-99-812-1740`, limits `79.4 mm` and `54.6 mm`, and coordinates `51.2185, -1.7925`.
  - Scene 2 called `publish_ticket_to_chat`, dispatched ticket `TKT-REME-D21F` to `http://127.0.0.1:8080/api/tickets`, and returned `✅ Ticket TKT-REME-D21F Published to 4 Bn REME Group Chat`.
  - Verified `GET http://127.0.0.1:8080/api/tickets` returned `1` ticket (`TKT-REME-D21F`, `nsn: "5360-99-812-1740"`).
- **`agents-cli eval run` (`task-153`)**:
  - Command:
    ```bash
    GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli eval run --config tests/eval/eval_config.yaml --project antig-dave
    ```
  - Verbatim Results:
    ```text
    === Grading Summary ===
    Total Traces: 3
    Metrics Summary:
      custom_response_quality:
        mean_score: 1.0000 (3/3 valid, 0 errors)
      agent_turn_count:
        mean_score: 1.0000 (3/3 valid, 0 errors)
    Traces saved to: artifacts/traces/traces_20261029_123743.json
    Results saved to: artifacts/grade_results/results_20261029_123824.json
    ```

### 1.4 Phase 8 Live Cloud Deployment & Registration (Step 4)
1. **Cloud Run (`reme-chat-demonstrator` in `europe-west1`, `task-160`)**:
   - Service URL: `https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app` (also `https://reme-chat-demonstrator-284046449012.europe-west1.run.app`)
   - Revision: `reme-chat-demonstrator-00001-bkr`
   - Service Account: `sa-reme-demo@antig-dave.iam.gserviceaccount.com`
   - Scaling: `min-instances=1`, `max-instances=1`
   - Live Verification:
     - `GET https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/` -> HTTP `200` (`6840` bytes HTML UI)
     - `GET https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/tickets` -> HTTP `200` (hydrated tickets from BigQuery)
     - `POST https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/reset` -> HTTP `200` `{"status": "reset", "tickets": []}`

2. **Vertex AI Agent Engine (`reme-artificer-agent` in `europe-west1`, `task-180`)**:
   - Agent Runtime Resource ID: `projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992`
   - Agent Identity: `principal://agents.global.org-137541019652.system.id.goog/resources/aiplatform/projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992` (granted `roles/bigquery.jobUser`, `roles/bigquery.dataEditor`, `roles/discoveryengine.viewer` on project `antig-dave`)
   - Agent Card URL: `https://europe-west1-aiplatform.googleapis.com/reasoningEngines/v1/projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992/api/a2a/app/.well-known/agent-card.json`

3. **Google Cloud Agent Registry (`europe-west1`, `task-186`)**:
   - Verified via `gcloud alpha agent-registry agents list --project antig-dave --location europe-west1`:
     - Resource Name: `projects/antig-dave/locations/europe-west1/agents/agentregistry-00000000-0000-0000-761c-488b42c62f72`
     - `agentId`: `urn:agent:projects-284046449012:projects:284046449012:locations:europe-west1:aiplatform:reasoningEngines:6397856951400660992`
     - `displayName`: `reme-artificer-agent`

4. **Gemini Enterprise Registration (`pixel_mobile_demos`, `task-186`)**:
   - Published via `agents-cli publish gemini`:
     - Registered Agent Resource Name: `projects/284046449012/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents/10995513697759164495`
     - `displayName`: `REME-Artificer`
     - `state`: `ENABLED`
   - Non-destructive multi-tenant verification on `pixel-mobile-demos_1793177711952`:
     - `10995513697759164495`: `REME-Artificer` (`state: ENABLED`, `reasoningEngines/6397856951400660992`)
     - `13073824185441632570`: `British Army - Soldier Self-Service & Welfare Safeguarding Agent` (`state: ENABLED`, preserved untouched)
     - `deep_research`: `Deep Research` (`state: ENABLED`, preserved untouched)
     - Engine datastore `jointservicepubs_1793177321711` preserved untouched on `pixel-mobile-demos_1793177711952`, and `ukd-reme-aesp-ds` active in `eu` (`eu-discoveryengine.googleapis.com`).

---

## 2. Logic Chain

1. **Contract Alignment (`TEST_READY.md § 4` -> `app/*` & `cloud_run_chat_app/*`)**:
   - Because the opaque-box E2E suite (`tests/e2e/`) strictly validates every schema field, fallback constant, SQL query parameter (`@query`, `@grid`), 13-column BigQuery filter, HTTP status code (`200`), and `<1s` in-memory reset behavior against `PROJECT.md` and `docs/architecture/implementation-plan.md`, aligning `app/schemas.py`, `app/tools.py`, `app/agent.py`, and `cloud_run_chat_app/main.py` resolved all 23 prior E2E failures without touching a single file in `tests/e2e/`.
2. **ADK 2.0 Prompt Variable Escaping (`app/agent.py`)**:
   - During Phase 7 local smoke testing (`task-140`), `InMemoryRunner` raised `KeyError: "Context variable not found: sector_display_name in agent 'reme_artificer_agent'"` because ADK 2.0's `inject_session_state` treats `{identifier}` in `LlmAgent.instruction` as a required session state variable. Replacing `{var}` with `[var]` in `SYSTEM_INSTRUCTION` eliminated the runtime `KeyError` while preserving all required prompt substrings (`5360-99-812-1740`, `79.4 mm`, `54.6 mm`, `51.2185, -1.7925`, `Chip 1`, `Chip 2`, `Chip 3`, `do NOT pack with washers`).
3. **End-to-End Cloud Integration (`Cloud Run` <- `Agent Engine` <- `Gemini Enterprise`)**:
   - Deploying `reme-chat-demonstrator` to Cloud Run first provided the production HTTPS URL (`https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`), which was injected into `.env` and passed via `--env-vars` into the Vertex AI Agent Engine deployment (`reasoningEngines/6397856951400660992`) so that `publish_ticket_to_chat` in the cloud runtime dispatches tickets directly to the live Cloud Run endpoint.

---

## 3. Caveats

- No caveats. All 8 unit tests, all 256 E2E tests, local smoke tests, `agents-cli eval run` (3/3 traces, 1.0000 mean score), and all 4 cloud deployment targets (Cloud Run, Vertex AI Agent Engine, Agent Registry, and Gemini Enterprise `pixel_mobile_demos`) are verified and passing.

---

## 4. Conclusion

Milestone M4 (`worker_deploy_m4`) is complete and ready for Forensic Audit:
- **Unit & E2E Tests**: `264 passed in 29.77s` (`8/8` unit + `256/256` E2E = 100%).
- **Evaluation (`agents-cli eval run`)**: `custom_response_quality: 1.0000 (3/3)`, `agent_turn_count: 1.0000 (3/3)`.
- **Live Cloud Run URL**: `https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`
- **Live Vertex AI Agent Engine ID**: `projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992`
- **Live Agent Registry Entry**: `projects/antig-dave/locations/europe-west1/agents/agentregistry-00000000-0000-0000-761c-488b42c62f72`
- **Live Gemini Enterprise Agent**: `projects/284046449012/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents/10995513697759164495` (`REME-Artificer`, `ENABLED`).

---

## 5. Verification Method

To independently verify all deliverables:

1. **Run the Full Unit & 256-Test E2E Suite**:
   ```bash
   GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v
   ```
   Expected: `264 passed` (`0 failed`).

2. **Run `agents-cli eval run`**:
   ```bash
   GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli eval run --config tests/eval/eval_config.yaml --project antig-dave
   ```
   Expected: `custom_response_quality: mean_score: 1.0000`, `agent_turn_count: mean_score: 1.0000`.

3. **Verify Live Cloud Run Service (`europe-west1`)**:
   ```bash
   curl -sS https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/tickets
   curl -sS -X POST https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/reset
   ```

4. **Verify Live Agent Registry & Gemini Enterprise (`pixel_mobile_demos`)**:
   ```bash
   GOOGLE_API_USE_CLIENT_CERTIFICATE=false gcloud alpha agent-registry agents list --project antig-dave --location europe-west1
   TOKEN=$(GOOGLE_API_USE_CLIENT_CERTIFICATE=false gcloud auth print-access-token --account=admin@edwardsda.altostrat.com)
   curl -sS -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: antig-dave" \
     "https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents"
   ```
