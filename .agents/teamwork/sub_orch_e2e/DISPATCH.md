# Dispatch — E2E Testing Track Orchestrator (`sub_orch_e2e`)

## Identity & Paths
- **Your Identity**: `sub_orch_e2e` (E2E Testing Track Orchestrator)
- **Hierarchy Level**: Sub-orchestrator (E2E Testing Track)
- **Your Working Directory**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_e2e/`
- **Parent Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`
- **Original Request Path**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
- **Project Scope Document**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`

## Files to Read First
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/handoff.md`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_explorer_survey_3/handoff.md`

## Assigned Scope: E2E Testing Track (`TEST_INFRA.md`, `tests/e2e/`, `TEST_READY.md`)
Design and build the requirement-driven opaque-box 4-tier E2E test suite covering all 22 inventoried features in `PROJECT.md § Feature Inventory`:
1. **`TEST_INFRA.md` (at project root `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_INFRA.md`)**:
   - Follow the exact `TEST_INFRA.md` template from the Project Pattern: Test Philosophy, Feature Inventory (all 22 features from `PROJECT.md`), Test Architecture (`pytest tests/e2e/`), Real-World Application Scenarios (Tier 4), and Coverage Thresholds.
2. **4-Tier Test Suite in `tests/e2e/`**:
   - Use `teamwork_test_writer` (or `teamwork_worker`) to implement the E2E test suite under `tests/e2e/`:
     - **Tier 1 — Feature Coverage (`tests/e2e/test_tier1_features.py`)**: >=5 test cases per feature area (covering all 22 features in `PROJECT.md § Feature Inventory`, >=110 test cases total via parametrized & distinct test functions).
     - **Tier 2 — Boundary & Corner Cases (`tests/e2e/test_tier2_boundaries.py`)**: >=5 boundary/negative/edge test cases per feature area (>=110 test cases total: empty inputs, garbled PTT queries, missing session state, malformed payloads, HTML snippet stripping, missing descriptions check, EU vs non-EU endpoint checks, etc.).
     - **Tier 3 — Cross-Feature Combinations (`tests/e2e/test_tier3_combinations.py`)**: >=22 pairwise cross-feature interaction tests (e.g., Scene 1 K60 diagnosis -> state persistence -> Scene 2 publish -> FastAPI `/api/tickets` -> `/api/reset`; Jackal 2 diagnosis -> state overwrite -> publish; BigQuery schema descriptions + seed rows + tool query alignment).
     - **Tier 4 — Real-World Application Scenarios (`tests/e2e/test_tier4_scenarios.py`)**: >=11 realistic end-to-end operational scenarios (e.g., Full Salisbury Plain Exercise Scene 1->2->3 K60 lifecycle, Jackal 2 ERR-409 hydraulic manifold lifecycle, Stage Reset & Re-run under network blackout fallback, Shared `pixel_mobile_demos` non-destructive datastore & agent verification).
   - Ensure tests can run cleanly via `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/` (using progressive testability: tests that check live cloud deployment or local files should gracefully handle or test against the defined interfaces in `PROJECT.md`).
3. **`TEST_READY.md` (at project root `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_READY.md`)**:
   - Publish `TEST_READY.md` once the E2E test suite in `tests/e2e/` is complete and verified.

## Exclusive File Write Ownership
You and your Worker/Test Writer own ONLY:
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_INFRA.md`
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/TEST_READY.md`
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/e2e/**`
Do NOT modify implementation code or files outside your owned paths.

## Sub-Orchestrator Procedure
This scope fits a single **2B Iteration Loop**:
1. Create `BRIEFING.md`, `progress.md`, and `SCOPE.md` in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_e2e/`.
2. Run **2B Iteration Loop** (`3 Explorers -> 1 Worker/Test Writer -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate` in `GATE_STATUS.md`), passing `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` to every subagent and the mandatory integrity warning to your Worker.
3. When the Gate passes (`PASS`) and `TEST_READY.md` is published, write your `handoff.md` and send a completion message via `send_message` to `6f912669-38e4-4574-904f-704d623a5d01`.
