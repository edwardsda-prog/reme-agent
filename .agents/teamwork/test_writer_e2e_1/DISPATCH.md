# Dispatch: E2E Test Writer (`TEST_INFRA.md`, `tests/e2e/`, `TEST_READY.md`) — 2026-10-29T11:29:00Z

## Role & Identity
- **Identity**: `test_writer_e2e_1` (`teamwork_test_writer`)
- **Working Directory (metadata only)**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/test_writer_e2e_1/`
- **Parent Orchestrator Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`

## Required Reading Before Starting
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` (MANDATORY)
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md` (Feature Inventory #1–#22 and Interface Contracts)
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md`
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/Demo 1 - SA.md`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`

## Exclusive File Write Ownership
You have EXCLUSIVE write ownership of:
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_INFRA.md`
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_READY.md`
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/e2e/` (`__init__.py`, `conftest.py`, `test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_pairwise.py`, `test_tier4_scenarios.py`)

**CRITICAL BOUNDARY**:
- Do NOT modify any implementation files (`app/`, `cloud_run_chat_app/`, `scripts/`, `tests/unit/`, `tests/eval/`, `pyproject.toml`, `AGENTS.md`, `docs/`).

## Deliverables & Methodology
Design and implement a comprehensive, requirement-driven, 4-tier pytest E2E test suite in `tests/e2e/` covering all 22 features in `PROJECT.md § Feature Inventory`:
1. **`TEST_INFRA.md`**: Document the test philosophy, 22-feature inventory mapping, test runner command (`GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/ -v`), directory layout, and Tier 1–4 coverage matrix.
2. **Tier 1 — Feature Coverage (`tests/e2e/test_tier1_features.py`, >=5 test cases per feature = >=110 tests)**:
   - Use `@pytest.mark.parametrize` and well-structured test functions so every one of the 22 features in `PROJECT.md § Feature Inventory` has >=5 distinct, meaningful test cases verifying happy-path compliance against the interface contracts and requirements in `ORIGINAL_REQUEST.md` and `implementation-plan.md`.
3. **Tier 2 — Boundary & Corner Cases (`tests/e2e/test_tier2_boundaries.py`, >=5 test cases per feature = >=110 tests)**:
   - Test boundary values, empty/whitespace/malformed inputs, case-insensitivity, missing session state (`active_ticket` absent), network/API failure fallbacks, extra BigQuery fields filtering (`sector_display_name` stripped before `insert_rows_json`), HTML `<b>`/`</b>` stripping, coordinates tolerances, etc.
4. **Tier 3 — Cross-Feature Pairwise Combinations (`tests/e2e/test_tier3_pairwise.py`, >=22 tests)**:
   - Test pairwise interactions across features (e.g., Scene 1 `diagnose_and_resolve_grid` -> session state -> Scene 2 `publish_ticket_to_chat` -> Scene 3 FastAPI `POST /api/tickets` -> `GET /api/tickets` -> `POST /api/reset`; K60 vs Jackal 2 switching; Bravo-4 vs Alpha-1 vs London grid resolution; BigQuery catalogue + Discovery Engine snippets + FastAPI UI rendering).
5. **Tier 4 — Real-World Application Scenarios (`tests/e2e/test_tier4_scenarios.py`, >=11 tests)**:
   - Full end-to-end user journeys simulating Cpl MacDonald on Salisbury Plain Training Area (SPTA):
     - Scenario 1: Full Golden Path (FV432 K60 Fuel Injection Pump failure in Sector Bravo-4 -> Scene 1 diagnosis -> Scene 2 publish -> Scene 3 Group Chat card + 1-tap Google Maps URL -> Reset Demo).
     - Scenario 2: Secondary Path (Jackal 2 Cummins ISBe 409-3211 rear crank seal oil leak in Sector Alpha-1 -> Scene 1 -> Scene 2 -> Scene 3).
     - Scenario 3: Stage Wi-Fi Drop / Offline Fallback Resilience (Discovery Engine & BigQuery unreachable -> deterministic Golden-Path fallback -> Scene 2 publish without prior state -> Scene 3 recovery).
     - Scenario 4–11: Additional realistic tactical sustainment, multi-ticket ordering, reset recovery, security classification, EU/Belgium residency verification, and live GCP infrastructure readiness scenarios.
6. **`TEST_READY.md`**: Publish `TEST_READY.md` at the project root with the test runner command, coverage summary table, and 22-feature checklist.
7. Write `progress.md` and `handoff.md` in `.agents/teamwork/test_writer_e2e_1/` and notify parent (`6f912669-38e4-4574-904f-704d623a5d01`) via `send_message`.


## 2026-10-29T11:31:04Z
You are `test_writer_e2e_1` (`teamwork_test_writer`), assigned to design and implement the 4-tier opaque-box E2E test suite (`TEST_INFRA.md`, `tests/e2e/`, and `TEST_READY.md`) covering all 22 features in `PROJECT.md § Feature Inventory`.

- Your working directory (metadata only — `BRIEFING.md`, `progress.md`, `handoff.md`): `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/test_writer_e2e_1/`
- Your parent orchestrator Conversation ID: `6f912669-38e4-4574-904f-704d623a5d01`
