# Issue Fix 06: Agent Repeats Previous Turn Instead of Acknowledging Group Chat Publication

## Current Symptoms
- **Observed Behavior:** Once a fault is triaged in Turn 1 (e.g., `"Corporal McDonald in sector Bravo, the hydraulic safety valve and pipe are broken on the Jackal."`) and the user instructs the agent to publish the fault in Turn 2 (e.g., `"Publish on group chat."`), `publish_ticket_to_chat()` executes and persists the ticket to Cloud Run and BigQuery (`TKT-REME-B7A5` / `TKT-REME-8AD8`), **but the Agent's chat response repeats the previous Scene 1 triage turn verbatim** (`Classification: ... Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket`) instead of acknowledging that the ticket has been published.

## Root Cause Analysis (Live Session `10939182715978664`)
1. **Narrow Publish Intent Regex (`_PUBLISH_INTENT_TRIGGER`):**
   - In [`app/agent.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py), `_PUBLISH_INTENT_TRIGGER` only matched `publish\s+to\s+group\s+chat` (`"to"`, not `"on"` or `"in"`).
   - When the user said `"Publish on group chat."`, `_PUBLISH_INTENT_TRIGGER.search(user_text)` returned `None`, causing `fast_path_before_model_callback` to set `_enforce_concise_triage = True` and `_enforce_concise_publish = False`.
2. **Post-Tool State & Callback Override:**
   - Even when `gemini-2.5-flash` invoked `publish_ticket_to_chat()`, the tool did not flip `tool_context.state["_enforce_concise_publish"] = True` and `tool_context.state["_enforce_concise_triage"] = False`.
   - Furthermore, on the second ADK LLM pass (after `publish_ticket_to_chat` returned its `function_response`), `fast_path_before_model_callback` ran again on the conversation history and reset `_enforce_concise_triage = True`.
   - When `transparency_after_model_callback` ran on the final response, it saw `enforce_concise_triage == True` and overwrote the model's output with `active_ticket["formatted_concise_response"]` from Turn 1.
3. **Identical Trailing Prompt Line in Scene 2:**
   - `format_concise_publish_output()` in [`app/schemas.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py) previously ended with `Next Action: Tap or say "Publish to Group Chat" to broadcast this recovery ticket` instead of an explicit publication acknowledgement status line.

## Resolution Implemented
1. **Explicit Scene 2 Acknowledgement Line ([`app/schemas.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py)):**
   - Updated [`format_concise_publish_output`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/schemas.py#L46-L78) to accept `ticket_id: Optional[str] = None` and render:
     ```text
     Callsign: [callsign]
     Vehicle Location: [sector_display_name] ([coords_label])
     Grounded Manual: [aesp_reference]
     Demand Component: [part_name] — NSN: [nsn]

     Status: Fault ticket [ticket_id] published to 4 Bn REME Sustainment Group Chat.
     ```
2. **Authoritative Tool-Level State Synchronisation ([`app/tools.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/tools.py)):**
   - [`publish_ticket_to_chat`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/tools.py#L815-L945) now passes `ticket_id=ticket_id` to `format_concise_publish_output`, sets `tool_context.state["_enforce_concise_publish"] = True` and `tool_context.state["_enforce_concise_triage"] = False`, stores `tool_context.state["last_published_ticket"]`, and updates `active_ticket["ticket_id"]` and `active_ticket["formatted_publish_response"]`.
   - [`diagnose_and_resolve_grid`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/tools.py#L618-L812) explicitly sets `tool_context.state["_enforce_concise_triage"] = True` and `tool_context.state["_enforce_concise_publish"] = False`.
3. **Callback & Regex Hardening ([`app/agent.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py)):**
   - Broadened `_PUBLISH_INTENT_TRIGGER` and `_LIVE_GRID_OR_PUBLISH_TRIGGER` to match natural voice/text variations (`"publish on group chat"`, `"publish to group chat"`, `"publish in the chat"`, `"publish ticket"`, `"broadcast"`, `"dispatch"`, `"send it"`, `"confirm"`).
   - Added [`_latest_function_response_name`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py#L433-L445) check at the start of [`fast_path_before_model_callback`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py#L590-L615) so post-tool LLM passes preserve `_enforce_concise_publish = True` after `publish_ticket_to_chat` and never re-trigger Scene 1 triage formatting.
   - Updated [`transparency_after_model_callback`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py#L815-L915) and [`_build_concise_publish_from_state_or_text`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/app/agent.py#L728-L812) to include `ticket_id` and `Status: Fault ticket ... published to 4 Bn REME Sustainment Group Chat.`.
4. **Unit Test Verification ([`tests/unit/test_tools.py`](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/unit/test_tools.py)):**
   - Added `test_issue_06_publish_on_group_chat_acknowledges_and_never_repeats_scene1` covering the exact two-turn conversation from live session `10939182715978664`.
