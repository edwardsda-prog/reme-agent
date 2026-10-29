# Specification — REME Field Service Engineer & Sustainment Agent (`reme_artificer_agent`)

## 1. Goal & Persona
Build an enterprise voice-first ADK 2.0 agent (`reme_artificer_agent`) acting as a British Army Royal Electrical and Mechanical Engineers (REME) Master Artificer supporting 4 Armoured Medical Regiment / Field Recovery Teams.

## 2. Capabilities & Tools
1. **`diagnose_and_resolve_grid(fault_query, spoken_sector_grid, tool_context)`**:
   - Searches the unstructured Vertex AI Search datastore (`ukd-reme-aesp-ds` in `eu`) for Army Equipment Support Publications (AESPs).
   - Queries BigQuery (`antig-dave.ukd_reme_demo.parts_inventory` and `training_area_grids` in `europe-west1`) for NATO Stock Numbers (NSN), technical tolerances, and WGS84 GPS coordinates.
   - Stages a validated `ActiveTicketState` in `tool_context.state["active_ticket"]` (human-in-the-loop gate).
2. **`publish_ticket_to_chat(tool_context)`**:
   - Reads the staged `active_ticket` from `tool_context.state["active_ticket"]` ONLY after explicit operator confirmation.
   - Persists the structured ticket to BigQuery (`ukd_reme_demo.group_chat_tickets`) and broadcasts via HTTP POST to the Sustainment Group Chat web app (`/api/tickets`).

## 3. Infrastructure Targets
- **Project**: `antig-dave`
- **Reasoning Engine / BigQuery / Cloud Run Region**: `europe-west1`
- **Discovery Engine Location**: `eu`
- **Gemini Enterprise App**: `projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952`
