## 2026-10-29T13:10:00Z — Task Assignment from `teamwork_orchestrator_r1`

### Identity & Workspace
- **Your Identity**: `worker_remediate_r2` (Remediation & Live BQ Sync Worker; archetype `teamwork_worker`)
- **Your Working Directory**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_remediate_r2/`
- **Parent Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`

### Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT
> hardcode test results, create dummy/facade implementations, or
> circumvent the intended task. A teamwork_auditor will independently
> verify your work. Integrity violations WILL be detected and your
> work WILL be rejected.

### Mandatory Input Files (Read First)
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/challenger_r1_2/handoff.md`
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/scripts/seed_demo1_bigquery.py`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/tools.py`
6. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/e2e/test_tier5_adversarial.py`

### Exclusive Write Ownership
You have exclusive write ownership of:
- `scripts/seed_demo1_bigquery.py`
- `app/tools.py`
- `tests/e2e/test_tier5_adversarial.py`
Do NOT modify `AGENTS.md` or `docs/*`.

### Objective: Remediate the 2 Live BigQuery Oracle Defects Identified by `challenger_r1_2`

#### Step 1: Sync `scripts/seed_demo1_bigquery.py` with `GOLDEN_FALLBACK_K60` and `GOLDEN_FALLBACK_JACKAL` and Re-Seed Live BigQuery
1. In `scripts/seed_demo1_bigquery.py` (`IPC_SEED_ROWS`), update the seeded strings so they match the exact canonical strings in `app/tools.py`:
   - For all 6 **K60** rows (`K60-RELIEF-01` through `K60-RELIEF-06`):
     - `aesp_reference`: `"AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)"`
     - `part_name`: `"Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)"`
     - `nsn`: `"5360-99-812-1740"`
     - `repair_classification`: `"L1 FRT Fix (Bench Check) / L2 Workshop"`
     - `technical_limits`: `"Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits — do NOT pack with washers (prohibited packing washer NSN 5310-99-122-6412)."` (Note: includes both `"— do NOT pack with washers"` and `"(prohibited packing washer NSN 5310-99-122-6412)"` so every unit, E2E, and live oracle check passes!)
   - For all 5 **Jackal 2** rows (`JACKAL-HYD-01` through `JACKAL-HYD-05`):
     - `aesp_reference`: `"AESP 2320-J-100-522, Ch 4, Para 4.12 (Page 42)"`
     - `part_name`: `"Hydraulic Manifold High-Pressure Seal Kit"`
     - `nsn`: `"5330-99-812-4410"`
     - `repair_classification`: `"L2 Workshop — Hydraulic Pressure Test Required"`
     - `technical_limits`: `"Replace O-ring and backup ring; torque manifold bolts to 45 Nm; pressure test to 250 bar. Depressurise hydraulic accumulator prior to seal replacement."`
2. Execute `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run python scripts/seed_demo1_bigquery.py` to re-seed `antig-dave.ukd_reme_demo` in `europe-west1` (preserving 100% table and column `description` metadata).

#### Step 2: Prevent SQL Keyword Substring Collisions in `app/tools.py` (`diagnose_and_resolve_grid`)
1. In `app/tools.py` (`diagnose_and_resolve_grid`), when querying `ipc_nsn_catalogue`:
   - Currently, `WHERE LOWER(@query) LIKE CONCAT('%', LOWER(keyword_tag), '%') LIMIT 1` has no ordering or platform prioritization, so `"Jackal 2 fault code 409 hydraulic oil leak"` matches K60's `"oil"` keyword row first.
   - Fix the SQL query and/or post-filtering so platform-specific keywords take strict precedence, e.g.:
     ```sql
     SELECT repair_classification, aesp_reference, part_name, nsn, technical_limits
     FROM `antig-dave.ukd_reme_demo.ipc_nsn_catalogue`
     WHERE LOWER(@query) LIKE CONCAT('%', LOWER(keyword_tag), '%')
     ORDER BY
       CASE
         WHEN LOWER(keyword_tag) IN ('jackal', '409', '3211', 'manifold') THEN 0
         WHEN LOWER(keyword_tag) IN ('k60', 'fv432', '2350', '17.4') THEN 1
         ELSE 2
       END ASC,
       LENGTH(keyword_tag) DESC
     LIMIT 1
     ```
   - Also ensure that if `is_jackal` (`"409" in q_lower or "jackal" in q_lower`) is true, if a BigQuery row is returned whose `nsn` is NOT `"5330-99-812-4410"` (for example, in unit/E2E tests that mock a generic BQ row or in live BQ if someone queries `"Jackal 2 oil"` without matching `'jackal'`/`'409'`), wait: check what unit/E2E tests in `tests/unit/test_tools.py` and `tests/e2e/` mock for `_BQ_CLIENT.query`!
     - **IMPORTANT**: In some unit/E2E tests, `_BQ_CLIENT.query` is mocked with a `MagicMock` that returns custom test rows (or tests SQL parameterization `@query` and `@grid`). Updating the SQL string to add `ORDER BY CASE ... END ASC, LENGTH(keyword_tag) DESC` works transparently with both mocked `_BQ_CLIENT.query` and live BigQuery because live BigQuery has `keyword_tag = 'jackal'` and `keyword_tag = '409'` rows in `ipc_nsn_catalogue`!

#### Step 3: Add Regression Test to `tests/e2e/test_tier5_adversarial.py` & Verify All Tests + Live Oracle
1. Add a test function in `tests/e2e/test_tier5_adversarial.py` verifying:
   - The SQL query in `diagnose_and_resolve_grid` includes `ORDER BY` prioritizing `'jackal'` / `'409'` over generic keywords like `'oil'` / `'relief'` / `'spring'`, and `IPC_SEED_ROWS` in `scripts/seed_demo1_bigquery.py` contains `"250 bar"`, `"AESP 2320-J-100-522"`, and `"do NOT pack with washers"`.
   - Live execution of `diagnose_and_resolve_grid` against GCP for:
     - `"FV432 K60 oil pressure fluctuating at Sector Bravo-4"` -> `nsn == "5360-99-812-1740"`, `"79.4 mm"`, `"54.6 mm"`, `"do NOT pack with washers"`
     - `"Jackal 2 fault code 409 3211 hydraulic manifold pressure drop"` -> `nsn == "5330-99-812-4410"`, `"250 bar"`, `"AESP 2320-J-100-522"`
     - `"Jackal 2 fault code 409 hydraulic oil leak"` -> `nsn == "5330-99-812-4410"`, `"250 bar"`
2. Run the full test suite:
   ```bash
   GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v
   ```
   Confirm **100% pass (0 failures)**.
3. Redeploy the updated `app/tools.py` to Vertex AI Agent Engine in `europe-west1` so the live Reasoning Engine has the SQL ordering fix:
   ```bash
   GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run agents-cli deploy --deployment-target agent_runtime --region europe-west1 --project antig-dave
   ```
   (And if a new Reasoning Engine resource ID is created, or if it updates in place, check `gcloud alpha agent-registry agents list --project=antig-dave --location=europe-west1` and Gemini Enterprise `pixel-mobile-demos_1793177711952` to ensure `REME-Artificer` points to the active Reasoning Engine.)
4. Write `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_remediate_r2/handoff.md` and send completion message via `send_message` to `6f912669-38e4-4574-904f-704d623a5d01`.
