# Issue Fix: The Agent returns too much Information

## Current Symptoms
- **Observed Behavior:** The Agent returns too much Information
- **Error Trace / Logs:** 
  ```text
@REME-Artificer — Grounded AESP Diagnostic Card
🔊 15s Audio Brief: "Acknowledge fault at Salisbury Plain (SPTA) — Sector Bravo-4. Per AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14), this is a L1 FRT Fix (Bench Check) / L2 Workshop. Demand Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711), NSN 5360-99-812-1740. Check limits: Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits — do NOT pack with washers; do not use washers to pack up behind a weak spring (prohibited packing washer NSN 5310-99-122-6412). Say 'Publish to Group Chat' to dispatch."
Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)
Authorised Echelon: L1 FRT Fix (Bench Check) / L2 Workshop
Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711)
NATO Stock Number (NSN): 5360-99-812-1740 (e.g. 5360-99-812-1740)
Engineering Limits: Free length must be 79.4 mm (3.126 in); compress to 54.6 mm (2.150 in) under 14.3–16.2 kg (31.5–35.6 lb) load. Renew spring if outside limits — do NOT pack with washers; do not use washers to pack up behind a weak spring (prohibited packing washer NSN 5310-99-122-6412). (e.g. Free length = 79.4 mm, Minimum serviceable = 54.6 mm — Warning: do NOT pack with washers)
Casualty Grid: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W, e.g. 51.2185, -1.7925)

👉 Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket and Google Maps pin to the 4 Bn REM

Routing Tier: TIER_3_PARALLEL_HYBRID_TRIAGE
Tool Cache Status: MEMORY_TTL_HIT (parallel_fanout=True)
Sub-Tool Latencies: DiscoveryEngine=0.0 ms | BQ_NSN=0.0 ms | BQ_Grid=0.0 ms (Total Tool Wall-Clock: 0.02 ms)
Context Cache Config: ENABLED (min_tokens=2048, ttl_seconds=7200, static_prefix_tokens=5764)
Reasoning Overhead: DISABLED (thinking_budget=0, temperature=0.0)

  ```
- **Reproduction Steps:**
Run Prompt FV432 K60 low oil pressure at Sector Bravo-4


## Expected Behavior
Classification:
AESP Ref: 
NSN: 
Coordinates of Sector : 

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

- [Example: Classification: L2 Repair, 
AESP Ref: Para 4.12 (Torque 45Nm)
NSN: 5330-99-812-4410.
Coordinates of Sector : 51.5007° N, 0.1246° W

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

## Target Files

- [`app/schemas.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py): Added `concise_aesp_ref`, `visual_assessment`, `requires_new_part`, `field_fixable_by_soldier`, and `formatted_concise_response` to `ActiveTicketState`, plus `format_concise_triage_output()`.
- [`app/tools.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/tools.py): Added multimodal damage assessment profiles (`GOLDEN_FALLBACK_FIELD_FIX`, `GOLDEN_FALLBACK_HYDRAULIC_PIPE`, `GOLDEN_FALLBACK_SAFETY_VALVE`, `GOLDEN_FALLBACK_VALVE_AND_PIPE`), `_select_special_damage_profile()`, and `_derive_concise_aesp_ref()` in `diagnose_and_resolve_grid()`.
- [`app/agent.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py): Updated `SYSTEM_INSTRUCTION` Scene 1 and few-shot examples to emit only the 5-line concise format, added `_has_multimodal_image_part()` in `fast_path_before_model_callback`, and updated `transparency_after_model_callback` to enforce the 5-line concise output and suppress the inline `Agent Execution Trace` block on Scene 1 triage turns.
- [`scripts/seed_demo1_bigquery.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/scripts/seed_demo1_bigquery.py): Added `JACKAL-PIPE-01` (`4710-99-812-4420`), `JACKAL-VALVE-01` (`4820-99-812-4415`), `JACKAL-VALVE-PIPE-01` (`4820-99-812-4415, 4710-99-812-4420`), and `JACKAL-FIELD-FIX-01` (`N/A (Field Fix — Re-torque union to 45Nm)`) to `IPC_SEED_ROWS`.
- [`tests/unit/test_tools.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/unit/test_tools.py): Added `test_issue_03_concise_triage_output_and_multimodal_photo_assessment` regression test for prompt `"FV432 K60 low oil pressure at Sector Bravo-4"` and multimodal photo assessment (field-fix vs. broken pipe/valve/both).
- [`tests/e2e/test_tier4_scenarios.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/e2e/test_tier4_scenarios.py): Added `test_scenario_15_issue_03_concise_output_and_photo_valve_pipe_assessment` E2E scenario test.

## Context Validation Rules
- The agent will analyse the photograph sent in the original prompt. The agent will assess whether a new part is required or the soldier can fix the issue in the field. For example if hydraulic valve or pipe is broken, a new pipe or safety valve or both will be provided
