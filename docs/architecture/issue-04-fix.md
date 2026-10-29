# Issue Fix: The Agent returns too much Information and the image provided in the prompt by the user must be made available in the Chat Application with the Ticket

## Current Symptoms
- **Observed Behavior:** The Agent returns too much Information once the soldier prompts Publish to Group Chat" to broadcast this recovery ticket
- **Error Trace / Logs:** 
  ```text
Callsign: Cpl MacDonald (4 Bn REME FRT)
Casualty Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)
Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)
Demand Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740
Tactical Navigation: Open Universal Google Maps Route (51.2185, -1.7925)
Routing Tier: TIER_3_PARALLEL_HYBRID_TRIAGE
Tool Cache Status: MEMORY_TTL_HIT (parallel_fanout=True)
Sub-Tool Latencies: DiscoveryEngine=0.0 ms | BQ_NSN=0.0 ms | BQ_Grid=0.0 ms (Total Tool Wall-Clock: 0.02 ms)
Context Cache Config: ENABLED (min_tokens=2048, ttl_seconds=7200, static_prefix_tokens=5764)
Reasoning Overhead: DISABLED (thinking_budget=0, temperature=0.0)
  ```
- **Reproduction Steps:**
Publish to Group Chat" to broadcast this recovery ticket


## Expected Behavior
Callsign: 
Vehicle Location:
Grounded Manual: 
Demand Component: 
The Image that the user provides in the prompt is saved to a GCS bucket by the Agent. The image is associated with the ticket and made available in the Chat Application

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

Callsign: Cpl MacDonald (4 Bn REME FRT)
Vehicle Location: Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)
Grounded Manual: AESP 2350-T-250-523, Ch 1-2, Para 17.4 (Page 14)
Demand Component: Oil Pressure Relief Valve Spring (IPC Army Code 14660 Cat 711) — NSN: 5360-99-812-1740

Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket

## Target Files

- [`app/schemas.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py): Add `image_gcs_uri`, `image_url`, and `formatted_publish_response` fields to [`ActiveTicketState`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py#L44-L81) and [`TicketPayload`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py#L99-L116), plus [`format_concise_publish_output()`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py#L83-L96).
- [`app/tools.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/tools.py): Add `TICKET_IMAGES_BUCKET = "antig-dave-reme-ticket-images-eu"`, pre-warmed `storage.Client` helper `upload_prompt_image_to_gcs()`, propagate `image_gcs_uri` and `image_url` in [`diagnose_and_resolve_grid`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/tools.py#L388-L607) and [`publish_ticket_to_chat`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/tools.py#L610-L698), and include automatic 13-column fallback on BigQuery `insert_rows_json`.
- [`app/agent.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py): Update `SYSTEM_INSTRUCTION` Scene 2 and Example 2 to emit the exact concise `Callsign:` / `Vehicle Location:` / `Grounded Manual:` / `Demand Component:` + `Next Action:` format; extract multimodal image bytes in [`fast_path_before_model_callback`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py#L496-L575) and upload to `gs://antig-dave-reme-ticket-images-eu`; update [`transparency_after_model_callback`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py#L578-L700) to enforce the concise Scene 2 response and suppress `Tactical Navigation` and `Agent Execution Trace` on publish turns.
- [`cloud_run_chat_app/requirements.txt`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/cloud_run_chat_app/requirements.txt): Add `google-cloud-storage>=2.18.0`.
- [`cloud_run_chat_app/main.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/cloud_run_chat_app/main.py): Add `image_gcs_uri` and `image_url` to [`TicketPayload`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/cloud_run_chat_app/main.py#L46-L60), add `GET /api/ticket-image/{blob_path:path}` proxy endpoint backed by `gs://antig-dave-reme-ticket-images-eu`, and persist `image_gcs_uri` / `image_url` to BigQuery `group_chat_tickets` with 13-column fallback.
- [`cloud_run_chat_app/templates/index.html`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/cloud_run_chat_app/templates/index.html): Render the attached field photograph inside `.ticket-card` when `ticket.image_url` or `ticket.image_gcs_uri` is present.
- [`scripts/seed_demo1_bigquery.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/scripts/seed_demo1_bigquery.py) & [`scripts/deploy_demo.sh`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/scripts/deploy_demo.sh): Add `NULLABLE` columns `image_gcs_uri` and `image_url` with descriptions to `group_chat_tickets`, and provision `gs://antig-dave-reme-ticket-images-eu` in `europe-west1`.
- [`tests/unit/test_tools.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/unit/test_tools.py) & [`tests/unit/test_chat_api.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/unit/test_chat_api.py): Regression test the prompt `"Publish to Group Chat" to broadcast this recovery ticket` and verify GCS image upload, BigQuery CRUD insertion, and Chat Application ticket image rendering.

## Context Validation Rules
- Ensure the data can be inserted into Bigquery as per the existing CRUD operations undertook by the agent
- Ensure the image is available in the ticket in the Chat application
