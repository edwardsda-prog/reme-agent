# Forensic Audit Report & Handoff — `auditor_r2_1` (Round 2)

## Forensic Audit Report

**Work Product**: UK Defence REME Artificer Demonstrator (`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`) — Round 2 Remediated Codebase, 295-Test Suite (`tests/unit/` & `tests/e2e/`), and Live GCP Infrastructure (`antig-dave` / `284046449012`)
**Profile**: General Project (`Integrity Mode: development` per `ORIGINAL_REQUEST.md` line 8)
**Verdict**: **CLEAN**

### Phase Results
- **1. Hardcoded Output Detection**: **PASS** — Inspected `app/schemas.py`, `app/tools.py`, `app/agent.py`, `cloud_run_chat_app/main.py`, `scripts/setup_reme_datastore.py`, `scripts/seed_demo1_bigquery.py`, `tests/unit/`, and `tests/e2e/test_tier5_adversarial.py`. Grep searches across `app/`, `cloud_run_chat_app/`, `scripts/`, and `tests/` confirmed zero `PYTEST_CURRENT_TEST` branches, zero `sys.argv` test hooks, and zero hardcoded test pass/fail bypasses. `GOLDEN_FALLBACK_K60`, `GOLDEN_FALLBACK_JACKAL`, and `GOLDEN_FALLBACK_GRID` in `app/tools.py` (lines 70–99) are explicitly required by `ORIGINAL_REQUEST.md` R4 and `docs/architecture/implementation-plan.md` Phase 4.2, and are synchronized byte-for-byte with `IPC_SEED_ROWS` in `scripts/seed_demo1_bigquery.py` (lines 102–137).
- **2. Facade Detection**: **PASS** — All application modules, remediation changes, and tests implement genuine logic:
  - `app/tools.py` (lines 199–234): `diagnose_and_resolve_grid` executes live EU Discovery Engine retrieval (`_search_aesp_datastore`, `pageSize: 15`, `snippetSpec: {"returnSnippet": True}`, no `summarySpec`, HTML stripping via `_strip_html`) followed by parameterized BigQuery SQL against `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` with platform-priority ordering (`ORDER BY CASE WHEN LOWER(keyword_tag) IN ('jackal', '409', '3211', 'manifold') THEN 0 WHEN LOWER(keyword_tag) IN ('k60', 'fv432', '2350', '17.4') THEN 1 ELSE 2 END ASC, LENGTH(keyword_tag) DESC LIMIT 1`) and `spta_sector_grids` (`@grid`).
  - `scripts/seed_demo1_bigquery.py` (lines 99–137): Seeds 11 rows (6 K60 rows for `5360-99-812-1740` + 5 Jackal 2 rows for `5330-99-812-4410`) with `aesp_reference`, `part_name`, `repair_classification`, and `technical_limits` matching `GOLDEN_FALLBACK_K60` and `GOLDEN_FALLBACK_JACKAL`, and enforces table-level and column-level descriptions across all 3 tables.
  - `tests/unit/` (8 tests) & `tests/e2e/` (287 tests across Tiers 1–5, including 31 white-box adversarial tests in `tests/e2e/test_tier5_adversarial.py`): Zero `pytest.skip` or `pytest.xfail` calls exist anywhere in the test suite.
- **3. Pre-Populated Artifact & Layout Compliance Detection**: **PASS** — `git diff --stat AGENTS.md docs/` returned empty output (preserving `AGENTS.md` and `docs/` untouched). `find .agents/teamwork -type f \( -name "*.py" -o -name "AGENTS.md" -o -name "GEMINI.md" \)` returned empty output (zero source/test/rule files inside `.agents/teamwork/`).
- **4. Build and Run (Independent 295-Test Suite Execution)**: **PASS** — Independently ran `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --frozen pytest tests/unit/ tests/e2e/ -v`; all **295/295 tests passed in 37.31s** (`0 failed`, `0 skipped`).
- **5. Live GCP & Output Verification**: **PASS** — Independently verified live GCP state in project `antig-dave` (`284046449012`) as `admin@edwardsda.altostrat.com`:
  - **BigQuery (`europe-west1`)**: Dataset `antig-dave.ukd_reme_demo` (`location=europe-west1`, `Desc=True`) has `ipc_nsn_catalogue` (`rows=11`, `table_desc=True`, `cols=8`, `missing_col_desc=[]`, with 6 K60 rows and 5 Jackal 2 rows matching `GOLDEN_FALLBACK_K60` and `GOLDEN_FALLBACK_JACKAL` byte-for-byte), `spta_sector_grids` (`rows=5`, `table_desc=True`, `cols=5`, `missing_col_desc=[]`), and `group_chat_tickets` (`rows=164`, `table_desc=True`, `cols=13`, `missing_col_desc=[]`).
  - **Live Oracle Execution (`eu` Discovery Engine + `europe-west1` BigQuery)**: Direct execution of `diagnose_and_resolve_grid` against live GCP verified K60 (`5360-99-812-1740`, `"79.4 mm"`, `"54.6 mm"`, `"do NOT pack with washers"`, `len(rag_snippets) > 0`), Jackal 2 (`5330-99-812-4410`, `"250 bar"`, `"AESP 2320-J-100-522"`), and the overlapping keyword collision query (`"Jackal 2 fault 409-3211 hydraulic manifold relief valve spring oil leak"` -> `5330-99-812-4410`).
  - **Cloud Run (`europe-west1`)**: `reme-chat-demonstrator` (`https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`, `Ready=True`, service account `sa-reme-demo@antig-dave.iam.gserviceaccount.com`) returned HTTP 200 on `GET /` and `GET /api/tickets`.
  - **Vertex AI Agent Engine (`europe-west1`)**: `projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992` (`displayName: reme-artificer-agent`) is active and updated in-place (`updateTime: 2026-10-29T13:24:36.510515Z`).
  - **Agent Registry (`europe-west1`)**: `projects/antig-dave/locations/europe-west1/agents/agentregistry-00000000-0000-0000-761c-488b42c62f72` (`reme-artificer-agent`, `updateTime: 2026-10-29T13:21:51.060271Z`) is registered and bound to `reasoningEngines/6397856951400660992`.
  - **Gemini Enterprise (`eu`)**: Engine `pixel-mobile-demos_1793177711952` has agent `10995513697759164495` (`REME-Artificer`, `state: ENABLED`, bound to `reasoningEngines/6397856951400660992`), with pre-existing agents `13073824185441632570` (`British Army - Soldier Self-Service & Welfare Safeguarding Agent`, `ENABLED`), `deep_research` (`Deep Research`, `ENABLED`), and datastore `jointservicepubs_1793177321711` completely intact.
- **6. Dependency & Guardrail Audit**: **PASS** — Module-level `_BQ_CLIENT` and `_CREDENTIALS` singletons are pre-warmed at import time (`app/tools.py:51-67`); zero `subprocess` calls exist; Discovery Engine uses single-pass `pageSize: 15` with `snippetSpec` only and no `summarySpec`.

---

## 1. Observation

### 1.1 Source Code & Remediation Inspection
- **`app/tools.py` (lines 70–92, 199–234)**:
  - `GOLDEN_FALLBACK_K60` (lines 70–81) and `GOLDEN_FALLBACK_JACKAL` (lines 83–92) contain the exact engineering tolerances (`"79.4 mm"`, `"54.6 mm"`, `"do NOT pack with washers"`, `"250 bar"`, `"AESP 2320-J-100-522, Ch 4, Para 4.12 (Page 42)"`).
  - `sql_parts` (lines 201–213) uses parameterized SQL (`@query`) with deterministic `ORDER BY CASE WHEN LOWER(keyword_tag) IN ('jackal', '409', '3211', 'manifold') THEN 0 WHEN LOWER(keyword_tag) IN ('k60', 'fv432', '2350', '17.4') THEN 1 ELSE 2 END ASC, LENGTH(keyword_tag) DESC LIMIT 1`.
- **`scripts/seed_demo1_bigquery.py` (lines 99–137)**:
  - `K60_KEYWORDS = ["k60", "oil", "relief", "spring", "2350", "17.4"]` (6 rows) and `JACKAL_KEYWORDS = ["jackal", "409", "hydraulic", "manifold", "4.12"]` (5 rows) seed `IPC_SEED_ROWS` with exact strings matching `GOLDEN_FALLBACK_K60` and `GOLDEN_FALLBACK_JACKAL`.
- **`tests/e2e/test_tier5_adversarial.py` (lines 1–694)**:
  - Contains 31 white-box adversarial test executions across 15 test functions (with `@pytest.mark.parametrize`), including `test_tier5_live_bigquery_seed_sync_and_keyword_collision_precedence` (lines 634–692) which verifies seed sync, SQL `ORDER BY` precedence, and live GCP oracle calls for K60 and Jackal 2 overlap queries.

### 1.2 Raw Empirical Tool Output
```text
=== 1. GIT & LAYOUT CHECK ===
(empty output — 0 modifications to AGENTS.md or docs/; 0 .py/AGENTS.md/GEMINI.md files in .agents/teamwork/)

=== 2. GCLOUD ACCOUNT & PROJECT ===
admin@edwardsda.altostrat.com
antig-dave

=== 3. LIVE BIGQUERY ORACLE & SEED SYNC VERIFICATION ===
Dataset: ukd_reme_demo Location: europe-west1 Desc: True
Table ipc_nsn_catalogue: rows=11, table_desc=True, cols=8, missing_col_desc=[]
Table spta_sector_grids: rows=5, table_desc=True, cols=5, missing_col_desc=[]
Table group_chat_tickets: rows=164, table_desc=True, cols=13, missing_col_desc=[]
Live ipc_nsn_catalogue count: 11
Live K60 rows: 6 Live Jackal rows: 5
LIVE BIGQUERY & DISCOVERY ENGINE ORACLE VERIFIED!

=== 4. CLOUD RUN reme-chat-demonstrator (europe-west1) ===
https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app	True	sa-reme-demo@antig-dave.iam.gserviceaccount.com
GET / HTTP 200
{"tickets":[]}

=== 5. VERTEX AI AGENT ENGINE & AGENT REGISTRY (europe-west1) ===
ReasoningEngine: projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992 | displayName: reme-artificer-agent | updateTime: 2026-10-29T13:24:36.510515Z
Engine: projects/284046449012/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952 | dataStoreIds: ['jointservicepubs_1793177321711']
Agent: 10995513697759164495 | displayName: REME-Artificer | state: ENABLED | RE: projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992
Agent: 13073824185441632570 | displayName: British Army - Soldier Self-Service & Welfare Safeguarding Agent | state: ENABLED | RE: projects/284046449012/locations/europe-west1/reasoningEngines/1537628528537763840
Agent: deep_research | displayName: Deep Research | state: ENABLED | RE: 
name: projects/antig-dave/locations/europe-west1/agents/agentregistry-00000000-0000-0000-761c-488b42c62f72
displayName: reme-artificer-agent
updateTime: '2026-10-29T13:21:51.060271Z'

=== 6. PYTEST 295-TEST SUITE ===
collected 295 items
...
tests/e2e/test_tier5_adversarial.py::test_tier5_live_bigquery_seed_sync_and_keyword_collision_precedence PASSED [100%]
============================= 295 passed in 37.31s =============================
```

---

## 2. Logic Chain

1. **Resolution of Round 1 Challenger Defects**:
   - In Round 1 (`challenger_r1_2`), live BigQuery rows in `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` had drifted from `GOLDEN_FALLBACK_K60` / `GOLDEN_FALLBACK_JACKAL` and `sql_parts` lacked an `ORDER BY` clause before `LIMIT 1`.
   - Our direct query against live `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` (`location="europe-west1"`) confirmed that all 6 K60 rows and all 5 Jackal 2 rows now match `GOLDEN_FALLBACK_K60` and `GOLDEN_FALLBACK_JACKAL` byte-for-byte while preserving 100% table and column descriptions (`missing_col_desc=[]`).
   - Direct invocation of `diagnose_and_resolve_grid` against live GCP confirmed that K60 queries, Jackal 2 queries, and overlapping Jackal 2 + `"relief valve spring oil leak"` queries all return the exact expected NSNs, AESP references, and technical limits.
2. **Test Suite Integrity**:
   - All 295 tests (`8` unit + `287` E2E across Tiers 1–5) executed cleanly in `37.31s` with zero skips, xfails, or test-environment cheats.
3. **Live Cloud Deployment Sync**:
   - Reasoning Engine `6397856951400660992` in `europe-west1` was updated in-place (`updateTime: 2026-10-29T13:24:36.510515Z`) with the remediated `app/tools.py`, and remains registered in Agent Registry (`agentregistry-00000000-0000-0000-761c-488b42c62f72`) and enabled on Gemini Enterprise (`pixel-mobile-demos_1793177711952`, agent `10995513697759164495`) with all peer agents and datastores untouched.

---

## 3. Caveats

### Challenge Summary (Adversarial Review)

**Overall risk assessment**: LOW

### [Low] Challenge 1 — Secondary Jackal Keyword Tags (`"hydraulic"`, `"4.12"`) Rely on `LENGTH(keyword_tag) DESC` Tie-Breaker
- **Assumption challenged**: `app/tools.py:207` lists `('jackal', '409', '3211', 'manifold')` in `CASE ... THEN 0`, while `scripts/seed_demo1_bigquery.py:100` seeds `JACKAL_KEYWORDS = ["jackal", "409", "hydraulic", "manifold", "4.12"]`.
- **Attack scenario**: If a user omits `"jackal"`, `"409"`, and `"manifold"` and queries `"4.12 relief spring"` (where `"4.12"` has length 4 and `"relief"`/`"spring"` have length 6), both fall into `ELSE 2` and `"relief"`/`"spring"` win by `LENGTH(keyword_tag) DESC`. (Note: `"hydraulic"` has length 9 and beats `"relief"`/`"spring"` even in `ELSE 2`).
- **Blast radius**: Negligible — any realistic Jackal 2 query mentions `"jackal"`, `"409"`, `"manifold"`, or `"hydraulic"`, all of which resolve to `5330-99-812-4410`.
- **Mitigation**: Optional inclusion of `'hydraulic'` and `'4.12'` in the `CASE ... THEN 0` list in future maintenance.

---

## 4. Conclusion

The Round 2 remediated UK Defence REME Artificer Demonstrator codebase, the 295-test unit and Tiers 1–5 E2E suite (`295 passed in 37.31s`), and all live GCP deployments in `antig-dave` (`284046449012`) are **CLEAN** with **zero integrity violations**.

---

## 5. Verification Method

```bash
# 1. Run the complete 295-test unit + Tiers 1-5 E2E suite
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --frozen pytest tests/unit/ tests/e2e/ -v

# 2. Verify live BigQuery seed sync and overlapping keyword precedence against live GCP
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --frozen python -c '
from app.tools import diagnose_and_resolve_grid
res_k60 = diagnose_and_resolve_grid("FV432 K60 engine oil pressure fluctuating between 15 and 35 PSI at hot idle", "Sector Bravo-4", None)
assert res_k60["nsn"] == "5360-99-812-1740" and "do NOT pack with washers" in res_k60["technical_limits"]
res_j = diagnose_and_resolve_grid("Jackal 2 fault 409-3211 hydraulic manifold relief valve spring oil leak", "Sector Bravo-4", None)
assert res_j["nsn"] == "5330-99-812-4410" and "250 bar" in res_j["technical_limits"]
print("VERIFIED")
'
```
