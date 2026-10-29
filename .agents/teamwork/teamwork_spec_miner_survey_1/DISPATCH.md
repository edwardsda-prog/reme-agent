# Dispatch — teamwork_spec_miner_survey_1

## Identity & Paths
- **Your Identity**: `teamwork_spec_miner_survey_1`
- **Archetype**: `teamwork_spec_miner`
- **Your Working Directory**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/`
- **Parent Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`
- **Original Request Path**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`

## Objective
Perform Phase 0 Survey (Specification Mining Part 1):
1. Read `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` in full.
2. Read `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md` in full.
3. Extract a complete, exhaustive Feature Inventory and Phase-by-Phase technical specification covering:
   - Every file to be created or modified, with exact relative paths and module boundaries.
   - Exact Pydantic schemas (`ActiveTicketState`, `TicketPayload`), tool signatures (`diagnose_and_resolve_grid`, `publish_ticket_to_chat`), Golden-Path Fallbacks, and `reme_artificer_agent` configuration and system prompt / Native Structured Markdown Card format.
   - Exact Discovery Engine datastore (`ukd-reme-aesp-ds`) and `pixel_mobile_demos` patching rules (`scripts/setup_reme_datastore.py`).
   - Exact BigQuery dataset (`ukd_reme_demo`) and 3 tables (`ipc_nsn_catalogue`, `spta_sector_grids`, `group_chat_tickets`) schemas, descriptions, and seed records (`scripts/seed_demo1_bigquery.py`).
   - Exact Cloud Run Tactical Group Chat App (`cloud_run_chat_app/`) endpoints, UI features, Google Maps Universal URL requirements, and deployment script (`scripts/deploy_demo.sh`).
   - Exact unit test (`tests/unit/`), evaluation (`tests/eval/datasets/basic-dataset.json`), Cloud Run deployment, Agent Engine deployment, Agent Registry verification, and Gemini Enterprise publishing requirements.

## Scope Boundaries
- Read-only specification investigation. Do NOT create or modify any project source code or cloud resources.
- Write all coordination/report files ONLY to `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/`.

## Output Requirements
- Maintain `BRIEFING.md` and `progress.md` in your working directory.
- Write your comprehensive findings and feature inventory to `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`.
- Send a concise completion message via `send_message` to `6f912669-38e4-4574-904f-704d623a5d01` referencing your `handoff.md`.


## 2026-10-29T11:11:54Z
You are `teamwork_spec_miner_survey_1` (`teamwork_spec_miner`).
Your working directory is `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/`.
Your parent conversation ID is `6f912669-38e4-4574-904f-704d623a5d01`.

MANDATORY FIRST STEPS:
1. Read `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` in full.
2. Read your assignment in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/DISPATCH.md`.
3. Create `BRIEFING.md` and `progress.md` in your working directory `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/`.

TASK:
Read `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md` in full and extract a complete, structured Feature Inventory and Phase-by-Phase specification (Phases 1 through 8) covering all files, Pydantic schemas, ADK tools, system instructions, Discovery Engine datastore scripts, BigQuery tables/descriptions/seed data, Cloud Run FastAPI app + HTML UI, tests, evals, and deployment commands.

Write your complete report to `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md` and notify parent (`6f912669-38e4-4574-904f-704d623a5d01`) via `send_message`.
