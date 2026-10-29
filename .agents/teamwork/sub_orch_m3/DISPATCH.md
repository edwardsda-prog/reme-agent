# Dispatch — Sub-Orchestrator M3 (`sub_orch_m3`)

## Identity & Paths
- **Your Identity**: `sub_orch_m3` (Sub-orchestrator for Milestone 3)
- **Hierarchy Level**: Sub-orchestrator
- **Your Working Directory**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_m3/`
- **Parent Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`
- **Original Request Path**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
- **Project Scope Document**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`

## Files to Read First
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/handoff.md`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_explorer_survey_3/handoff.md`

## Assigned Scope: Milestone 3 (M3) — Scene 3 Cloud Run Tactical Group Chat App (`cloud_run_chat_app/`) & API Unit Tests
You own **Features 18, 19, and 20 (chat API)** from `PROJECT.md`:
1. **`cloud_run_chat_app/main.py`**:
   - FastAPI backend serving on port `8080`.
   - In-memory `ACTIVE_TICKETS: list[dict] = []` for `<20ms` instant reads.
   - `GET /`: Renders `templates/index.html` (`4 Bn REME — Sustainment Group Chat`).
   - `GET /api/tickets`: Returns `{"tickets": ACTIVE_TICKETS}` in `<20ms`.
   - `POST /api/tickets`: Validates incoming ticket payload via Pydantic `TicketPayload` (matching the interface contract in `PROJECT.md`), prepends to `ACTIVE_TICKETS` (deduplicating by `ticket_id`), and optionally logs to BigQuery `ukd_reme_demo.group_chat_tickets` in a non-blocking/try-except block (filtering strictly to the 13 table columns). Returns `{"status": "published", "ticket": ticket_dict}`.
   - `POST /api/reset` (and alias `POST /api/tickets/reset`): Clears `ACTIVE_TICKETS.clear()` in `<1s` and returns `{"status": "reset", "tickets": []}`.
2. **`cloud_run_chat_app/templates/index.html`**:
   - High-contrast ruggedised dark-mode tactical HTML5 UI (`OFFICIAL — 4 BN REME SUSTAINMENT GROUP CHAT` banner).
   - `[Reset Demo]` button wired to `POST /api/reset` (`<1s` reset).
   - `1000ms` live polling (`fetch('/api/tickets')`) rendering live ticket cards (`ticket_id`, `callsign`, `repair_classification`, `aesp_reference`, `part_name`, `nsn`, `technical_limits`, `coords_label`, `status`).
   - 1-tap Google Maps Universal URL buttons supporting BOTH URL formats referenced in `ORIGINAL_REQUEST.md` and `implementation-plan.md`:
     - Primary button: `https://www.google.com/maps/dir/?api=1&destination=${ticket.latitude},${ticket.longitude}&travelmode=driving`
     - Secondary / pin link: `https://www.google.com/maps/search/?api=1&query=${ticket.latitude},${ticket.longitude}`
     (Also render a default/initial view or dynamic DOM cards so both static HTML inspection and live JS rendering expose the Google Maps URL structure clearly).
3. **`cloud_run_chat_app/Dockerfile` & `cloud_run_chat_app/requirements.txt`**:
   - `python:3.12-slim` Dockerfile running `uvicorn main:app --host 0.0.0.0 --port 8080`.
   - `requirements.txt` with `fastapi`, `uvicorn[standard]`, `google-cloud-bigquery`, `pydantic>=2.0.0`, `jinja2`.
4. **`tests/unit/test_chat_api.py`**:
   - Comprehensive FastAPI `TestClient` unit & integration tests verifying `GET /`, `GET /api/tickets` (`<20ms`), `POST /api/tickets` (valid payload, deduplication, Google Maps URL presence, error boundary on invalid payload), and `POST /api/reset` (`<1s` clear).
   - Run via `uv run --no-project --with fastapi --with uvicorn --with jinja2 --with pydantic --with httpx --with pytest --with google-cloud-bigquery pytest tests/unit/test_chat_api.py` (and `uv run pytest tests/unit/test_chat_api.py` once `.venv` exists).

## Exclusive File Write Ownership
You and your Worker own ONLY:
- `cloud_run_chat_app/main.py`
- `cloud_run_chat_app/templates/index.html`
- `cloud_run_chat_app/Dockerfile`
- `cloud_run_chat_app/requirements.txt`
- `tests/unit/test_chat_api.py`
Do NOT modify any other files in the repository.

## Sub-Orchestrator Procedure
This scope fits a single **2B Iteration Loop**:
1. Create `BRIEFING.md`, `progress.md`, and `SCOPE.md` in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_m3/`.
2. Run **2B Iteration Loop** (`3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate` in `GATE_STATUS.md`), passing `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` to every subagent and the mandatory integrity warning to your Worker.
3. When the Gate passes (`PASS`), write your `handoff.md` and send a completion message via `send_message` to `6f912669-38e4-4574-904f-704d623a5d01`.
