# Handoff Report — `challenger_r1_2` (Challenger 2 — Empirical Live System & End-to-End Oracle Verifier)

- **Agent**: `challenger_r1_2` (Empirical Challenger; roles: `critic`, `specialist`)
- **Timestamp**: `2026-10-29T13:04:20Z`
- **Handoff Type**: Hard Handoff (Task Complete)
- **Verdict**: **`REQUEST_CHANGES`**

---

## Challenge Summary

**Overall risk assessment**: **HIGH** (Live BigQuery data in `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` overwrites `GOLDEN_FALLBACK_JACKAL` and `GOLDEN_FALLBACK_K60` in `app/tools.py`, causing live Jackal 2 queries to omit `250 bar` / `AESP 2320-J-100-522`, live K60 queries to omit the exact substring `do NOT pack with washers`, and live Jackal 2 queries containing `"oil"`/`"relief"`/`"spring"` to return the wrong vehicle's NSN `5360-99-812-1740`).

### Challenges

#### [High] Challenge 1 — Live BigQuery `ipc_nsn_catalogue` Overwrites `GOLDEN_FALLBACK_JACKAL` & Strips `"250 bar"` and `"AESP 2320-J-100-522"`
- **Assumption challenged**: `worker_deploy_m4` assumed that updating `GOLDEN_FALLBACK_JACKAL` in `app/tools.py:81–90` satisfies the Jackal 2 (`409 3211`) contract (`"250 bar"`, `"AESP 2320-J-100-522"`). In `tests/e2e/test_tier4_scenarios.py:98` (`test_scenario_02_jackal2_hydraulic_fault_409_end_to_end_triage_and_dispatch`), `_BQ_CLIENT` is mocked to `None`, so the test only exercised the offline fallback dict and never tested live BigQuery.
- **Attack scenario**: Invoke `diagnose_and_resolve_grid("Jackal 2 fault code 409 3211 hydraulic manifold pressure drop", "Sector Bravo-4", ctx)` against live GCP (`antig-dave.ukd_reme_demo.ipc_nsn_catalogue`). Because `scripts/seed_demo1_bigquery.py:121–135` seeded `ipc_nsn_catalogue` with:
  - `aesp_reference`: `"AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)"` (missing `-522`)
  - `technical_limits`: `"Torque to 45 Nm. Depressurise hydraulic accumulator prior to seal replacement."` (missing `"250 bar"`)
  `app/tools.py:215–225` overwrites `part_data` with the live BigQuery row.
- **Blast radius**: Every live Scene 1 Jackal 2 (`409 3211`) tool execution against BigQuery fails the oracle check `assert "250 bar" in res_j["technical_limits"]` (`DISPATCH.md:21`, `TEST_READY.md:70`).
- **Mitigation**: Update `IPC_SEED_ROWS` for `JACKAL_KEYWORDS` in `scripts/seed_demo1_bigquery.py:121–135` so `aesp_reference` is `"AESP 2320-J-100-522 (Ch 4, Para 4.12, Page 42)"` and `technical_limits` is `"Replace O-ring and backup ring; torque manifold bolts to 45 Nm; pressure test to 250 bar. Depressurise hydraulic accumulator prior to seal replacement."`, then re-run `scripts/seed_demo1_bigquery.py` against `antig-dave.ukd_reme_demo`.

#### [High] Challenge 2 — Unordered `LIMIT 1` Keyword Matching in `diagnose_and_resolve_grid` Returns FV432 K60 NSN (`5360-99-812-1740`) for Jackal 2 (`409`) Queries Containing `"oil"`, `"relief"`, or `"spring"`
- **Assumption challenged**: `app/tools.py:199–204` assumes `SELECT ... FROM ipc_nsn_catalogue WHERE LOWER(@query) LIKE CONCAT('%', LOWER(keyword_tag), '%') LIMIT 1` will return the Jackal 2 row whenever a user asks about Jackal 2 (`409`).
- **Attack scenario**: A field mechanic asks about a Jackal 2 fault and mentions `"oil"`, `"relief"`, or `"spring"` (e.g., `"Jackal 2 fault code 409 hydraulic oil leak"`, `"Jackal 2 409 3211 relief valve"`, or `"Jackal 2 409 suspension spring"`). Because `ipc_nsn_catalogue` has `keyword_tag` rows `"oil"`, `"relief"`, and `"spring"` mapped to `K60-RELIEF-02..04` (`NSN: 5360-99-812-1740`) and the SQL query has no `ORDER BY` or vehicle filter, BigQuery returns the FV432 K60 row (`5360-99-812-1740`) instead of the Jackal 2 row (`5330-99-812-4410`).
- **Blast radius**: Misdiagnoses Jackal 2 (`409`) faults as FV432 K60 engine faults whenever common mechanical words (`"oil"`, `"relief"`, `"spring"`) appear in the prompt.
- **Mitigation**: In `app/tools.py:199–204`, either filter by platform when `"jackal"` or `"409"` is in `q_lower` (e.g. `AND part_id LIKE 'JACKAL%'` vs `AND part_id LIKE 'K60%'`) or add an explicit `ORDER BY CASE WHEN keyword_tag IN ('jackal', '409') THEN 0 WHEN keyword_tag IN ('k60', '2350', '17.4') THEN 1 ELSE 2 END`.

#### [Low] Challenge 3 — K60 Washer Prohibition Substring Drift (`do NOT pack with washers` vs `do not use washers to pack up behind a weak spring`) & Duplicate BigQuery Ticket Insert
- **Assumption challenged**:
  1. `DISPATCH.md:20` and `TEST_READY.md:69` check for exact substring `"do NOT pack with washers"` in Scene 1 K60 `technical_limits`. While `GOLDEN_FALLBACK_K60` (`app/tools.py:75–78`) contains `"— do NOT pack with washers."`, `scripts/seed_demo1_bigquery.py:112–117` seeded live `ipc_nsn_catalogue` with `"do not use washers to pack up behind a weak spring (prohibited packing washer NSN 5310-99-122-6412)."` (which differs in casing/phrasing).
  2. Both `publish_ticket_to_chat` (`app/tools.py:356`) and `create_ticket` (`cloud_run_chat_app/main.py:100`) call `_BQ_CLIENT.insert_rows_json("antig-dave.ukd_reme_demo.group_chat_tickets", [bq_row])`.
- **Attack scenario**: Calling `publish_ticket_to_chat` once inserts 2 identical rows for the same `ticket_id` into `antig-dave.ukd_reme_demo.group_chat_tickets` (observed empirically for `TKT-REME-4EEA`).
- **Blast radius**: Low — `ACTIVE_TICKETS` in Cloud Run deduplicates in memory (`len == 1`), and BigQuery audit queries still find the ticket, though duplicate rows accumulate in `group_chat_tickets` and case-sensitive checks for `"do NOT pack with washers"` on `res_k60["technical_limits"]` fail when live BigQuery is used.
- **Mitigation**: Append `" — do NOT pack with washers."` to K60 `technical_limits` in `scripts/seed_demo1_bigquery.py:112–117` (and re-seed), and optionally avoid duplicate BigQuery inserts when `publish_ticket_to_chat` receives HTTP 200 from Cloud Run `/api/tickets`.

### Stress Test Results

| Scenario | Expected Behavior | Actual Empirical Behavior | Result |
|---|---|---|---|
| Unit + E2E Test Suite (`tests/unit/` + `tests/e2e/test_tier1..4`) | 264/264 pass | `264 passed in 38.59s` | **PASS** |
| Tier 5 Adversarial Suite (`tests/e2e/test_tier5_adversarial.py`) | 30/30 pass | `30 passed in 9.32s` | **PASS** |
| Live Scene 1 K60 Query (`diagnose_and_resolve_grid` against live EU Discovery Engine & Belgium BigQuery) | NSN `5360-99-812-1740`, `79.4 mm`, `54.6 mm`, `do NOT pack with washers`, `51.2185, -1.7925`, non-empty `rag_snippets` without `<b>`/`</b>` | Latency `0.984s`; NSN `5360-99-812-1740`, `79.4 mm`, `54.6 mm`, `51.2185, -1.7925`, non-empty `rag_snippets` free of `<b>`/`</b>`; `technical_limits` from live BQ has `"do not use washers to pack up behind a weak spring"` instead of exact `"do NOT pack with washers"` | **PARTIAL FAIL** (phrasing drift vs `GOLDEN_FALLBACK_K60`) |
| Live Scene 1 Jackal 2 (`409 3211`) Query (`diagnose_and_resolve_grid` against live Belgium BigQuery) | NSN `5330-99-812-4410` and `250 bar` | Latency `0.910s`; NSN `5330-99-812-4410`, but `technical_limits` is `"Torque to 45 Nm. Depressurise hydraulic accumulator prior to seal replacement."` (**missing `250 bar`**) | **FAIL** |
| Live Scene 1 Jackal 2 (`409`) with `"oil"` / `"relief"` / `"spring"` in prompt | NSN `5330-99-812-4410` (Jackal 2) | Returns NSN `5360-99-812-1740` (FV432 K60) due to unordered `LIMIT 1` SQL match on `keyword_tag` | **FAIL** |
| Live Scene 2 `publish_ticket_to_chat` -> Cloud Run & BigQuery | Dispatches `TKT-REME-XXXX` to live Cloud Run `/api/tickets`, returned by `GET /api/tickets`, persisted in `ukd_reme_demo.group_chat_tickets` | Latency `0.275s`; `TKT-REME-4EEA` returned by `GET /api/tickets` and persisted in BigQuery (`2` rows inserted) | **PASS** |
| Live Scene 3 `POST /api/reset` `<1.0s` SLA + Re-publish 1 clean K60 ticket | HTTP `200` `{"status": "reset", "tickets": []}` in `<1.0s`, followed by 1 clean K60 ticket on live UI | Reset completed in **`0.044s`** (`HTTP 200`); re-published `TKT-REME-8884` (`5360-99-812-1740`), verified `len(tickets) == 1` on `GET /api/tickets` and `GET /` (`11035` bytes, `0.082s`) | **PASS** |

### Unchallenged Areas
- None within the scope assigned in `DISPATCH.md`.

---

## 1. Observation

1. **Test Suite Execution (`task-19` & `task-58`)**:
   - Command: `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v`
     - Result: `264 passed in 38.59s` (`test_tier1_features.py` through `test_tier4_scenarios.py` + `tests/unit/`).
   - Command: `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/e2e/test_tier5_adversarial.py -v`
     - Result: `30 passed in 9.32s`.

2. **Live End-to-End Oracle Execution Against GCP (`task-28`, `/usr/local/google/home/edwardsda/.gemini/antigravity/brain/48fd87c2-26fb-4328-b466-1cc81a9bd9fc/.system_generated/tasks/task-28.log`)**:
   - **Scene 1 K60 Query**:
     ```json
     {
       "repair_classification": "L1 FRT Fix (Bench Check) / L2 Workshop",
       "aesp_reference": "AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)",
       "part_name": "Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)",
       "nsn": "5360-99-812-1740",
       "technical_limits": "Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits; do not use washers to pack up behind a weak spring (prohibited packing washer NSN 5310-99-122-6412).",
       "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
       "latitude": 51.2185,
       "longitude": -1.7925,
       "coords_label": "51.2185° N, 1.7925° W",
       "rag_snippets": [
         "... of adjustment Brake linings worn beyond adjustable limits Oil level low External oil pipes restricted or leaking Oil cooler section of heat exchanger&nbsp;..."
       ]
     }
     ```
   - **Scene 1 Jackal 2 (`409 3211`) Query**:
     ```json
     {
       "repair_classification": "L2 Workshop Repair",
       "aesp_reference": "AESP 2320-J-100, Ch 4, Para 4.12 (Page 42)",
       "part_name": "Hydraulic Manifold High-Pressure Seal Kit",
       "nsn": "5330-99-812-4410",
       "technical_limits": "Torque to 45 Nm. Depressurise hydraulic accumulator prior to seal replacement.",
       "sector_display_name": "Salisbury Plain (SPTA) — Sector Bravo-4",
       "latitude": 51.2185,
       "longitude": -1.7925,
       "coords_label": "51.2185° N, 1.7925° W",
       "rag_snippets": [
         ") 13.2.2 Lower bush ID 12.75 mm (0.502in.) OD 15.09 mm (0.594in.) 13.3 Locally manufacture stepped drifts to drive out and fit the bushes, refer to Para&nbsp;..."
       ]
     }
     ```
   - **Adversarial Keyword Collision Test on Live BigQuery**:
     ```text
     Query: 'Jackal 2 fault code 409 hydraulic oil leak' -> NSN: 5360-99-812-1740 (Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711))
     Query: 'Jackal 2 409 3211 relief valve' -> NSN: 5360-99-812-1740 (Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711))
     Query: 'Jackal 2 409 suspension spring' -> NSN: 5360-99-812-1740 (Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711))
     ```
   - **Scene 2 Ticket Dispatch & BigQuery Persistence**:
     - `publish_ticket_to_chat` dispatched `TKT-REME-4EEA` in `0.275s` to `https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/tickets`, confirmed via `GET /api/tickets` and BigQuery `SELECT` on `antig-dave.ukd_reme_demo.group_chat_tickets`.
   - **Scene 3 `<1.0s` Reset & Final Clean K60 Ticket on Live UI**:
     - `POST https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/reset` returned HTTP `200` `{"status": "reset", "tickets": []}` in **`0.044s`**.
     - Re-published 1 clean K60 ticket (`TKT-REME-8884`, `nsn: "5360-99-812-1740"`). Confirmed `GET https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/tickets` returns exactly 1 ticket (`TKT-REME-8884`).

---

## 2. Logic Chain

1. In `app/tools.py:81–90`, `worker_deploy_m4` updated `GOLDEN_FALLBACK_JACKAL["technical_limits"]` to include `"pressure test to 250 bar"` and `GOLDEN_FALLBACK_K60["technical_limits"]` (`app/tools.py:75–78`) to include `"— do NOT pack with washers."`.
2. However, `worker_deploy_m4` did **not** update `IPC_SEED_ROWS` in `scripts/seed_demo1_bigquery.py:103–136` or re-seed `antig-dave.ukd_reme_demo.ipc_nsn_catalogue` in BigQuery.
3. Because `tests/e2e/test_tier4_scenarios.py:39` and `:98` mock `_BQ_CLIENT = None`, the automated test suite only asserted against the in-memory `GOLDEN_FALLBACK_*` dicts in `app/tools.py` and never caught that live BigQuery queries in `diagnose_and_resolve_grid` (`app/tools.py:197–226`) overwrite `part_data` with the older seed strings from `ipc_nsn_catalogue` (which lack `"250 bar"` for Jackal 2 and use different wording for the K60 washer prohibition).
4. Furthermore, `app/tools.py:199–204` executes `SELECT ... FROM ipc_nsn_catalogue WHERE LOWER(@query) LIKE CONCAT('%', LOWER(keyword_tag), '%') LIMIT 1` without ordering or platform filtering, causing any Jackal 2 (`409`) query that also mentions `"oil"`, `"relief"`, or `"spring"` to match a K60 row first and return the wrong NSN (`5360-99-812-1740`).

---

## 3. Caveats

- No caveats. All claims were verified directly against live GCP (`ukd-reme-aesp-ds` in `eu`, `ukd_reme_demo` in `europe-west1`, and `https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`). One clean K60 ticket (`TKT-REME-8884`) has been left active on the live Cloud Run UI as instructed.

---

## 4. Conclusion

**Verdict: `REQUEST_CHANGES`**

Before final sign-off, remediate the two live BigQuery oracle defects uncovered by empirical testing:
1. **Sync `scripts/seed_demo1_bigquery.py` (`IPC_SEED_ROWS`, lines 103–136) with `GOLDEN_FALLBACK_K60` / `GOLDEN_FALLBACK_JACKAL` and re-run `scripts/seed_demo1_bigquery.py`** so live BigQuery `ipc_nsn_catalogue` returns `"250 bar"` and `"AESP 2320-J-100-522"` for Jackal 2 (`5330-99-812-4410`) and `"do NOT pack with washers"` for K60 (`5360-99-812-1740`).
2. **Prevent K60/Jackal keyword collision in `app/tools.py:199–204`** by prioritizing platform-specific keywords (`'jackal'`, `'409'` vs `'k60'`) or filtering `part_id` based on `("jackal" in q_lower or "409" in q_lower)` so Jackal 2 queries mentioning `"oil"`, `"relief"`, or `"spring"` never return the K60 NSN (`5360-99-812-1740`).

---

## 5. Verification Method

Run the following command against live GCP after applying the fixes:

```bash
GOOGLE_API_USE_CLIENT_CERTIFICATE=false CLOUD_RUN_CHAT_URL="https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app" uv run python -c '
from app.tools import diagnose_and_resolve_grid
class Ctx: state = {}
k60 = diagnose_and_resolve_grid("FV432 K60 oil pressure fluctuating at Sector Bravo-4", "Sector Bravo-4", Ctx())
assert k60["nsn"] == "5360-99-812-1740" and "79.4 mm" in k60["technical_limits"] and "54.6 mm" in k60["technical_limits"] and "do NOT pack with washers" in k60["technical_limits"]
j2 = diagnose_and_resolve_grid("Jackal 2 fault code 409 3211 hydraulic oil leak", "Sector Bravo-4", Ctx())
assert j2["nsn"] == "5330-99-812-4410" and "250 bar" in j2["technical_limits"]
print("LIVE ORACLE VERIFIED!")
'
```
