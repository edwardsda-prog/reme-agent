# Dispatch — Sub-Orchestrator M2 (`sub_orch_m2`)

## Identity & Paths
- **Your Identity**: `sub_orch_m2` (Sub-orchestrator for Milestone 2)
- **Hierarchy Level**: Sub-orchestrator
- **Your Working Directory**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_m2/`
- **Parent Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`
- **Original Request Path**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
- **Project Scope Document**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`

## Files to Read First
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/handoff.md`
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_explorer_survey_3/handoff.md`

## Assigned Scope: Milestone 2 (M2) — Discovery Engine (`ukd-reme-aesp-ds`) & BigQuery (`ukd_reme_demo`) Provisioning
You own **Features 4, 5, 6, 7, 8, 9, 10, 11, and 12** from `PROJECT.md`:
1. **`scripts/setup_reme_datastore.py`**:
   - Execute under `admin@edwardsda.altostrat.com` (`GOOGLE_API_USE_CLIENT_CERTIFICATE=false`), project `antig-dave` (`284046449012`). Always include header `"X-Goog-User-Project": "antig-dave"` on Discovery Engine REST API calls.
   - Inspect `gs://remedata` in `antig-dave` and verify `gs://remedata/2350-T-250-523.pdf` is present.
   - Generate rich NDJSON metadata (`documents.jsonl` with `id`, `jsonData` containing `title`, `aesp_reference`, `chapter_paragraph`, `equipment_platform`, `component`, `ipc_army_code`, `nsn`, `security_classification`, `unit`, and `content.uri`) and upload to `gs://remedata/documents.jsonl`.
   - Create unstructured OCR datastore `ukd-reme-aesp-ds` in `location=eu` (`https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores?dataStoreId=ukd-reme-aesp-ds`) with `CONTENT_REQUIRED` and `ocrParsingConfig.useNativeText = True` (handling HTTP 409 idempotently).
   - Trigger document import (`branches/0/documents:import`) from `gs://remedata/documents.jsonl` with `reconciliationMode: "INCREMENTAL"`, poll the LRO until completion, and run a verification `:search` query against `ukd-reme-aesp-ds`.
   - **CRITICAL Safe Patching of `pixel_mobile_demos`**:
     - Per `teamwork_explorer_survey_3/handoff.md`, in `location=eu`, the engine with `displayName: "pixel_mobile_demos"` has actual `engineId` **`pixel-mobile-demos_1793177711952`**, and its pre-existing datastore with `displayName: "jointservicepubs"` has actual `dataStoreId` **`jointservicepubs_1793177321711`**.
     - Your script MUST dynamically resolve the engine (try `GET .../engines/pixel_mobile_demos`; if 404, `GET .../engines` and match `displayName == "pixel_mobile_demos"` or `pixel-mobile-demos_1793177711952`), read its existing `dataStoreIds` (`["jointservicepubs_1793177321711"]`), and `PATCH .../engines/{engine_id}?updateMask=dataStoreIds` with the union (`["jointservicepubs_1793177321711", "ukd-reme-aesp-ds"]`) so `jointservicepubs_1793177321711` is NEVER removed and existing attached agents (`13073824185441632570` and `deep_research`) are untouched.
2. **`scripts/seed_demo1_bigquery.py`**:
   - Provision dataset `antig-dave.ukd_reme_demo` in `location="europe-west1"` with explicit non-empty dataset `description`.
   - Create and seed all 3 tables in `antig-dave.ukd_reme_demo` (`location="europe-west1"`):
     - `ipc_nsn_catalogue` (6 primary FV432 K60 rows `5360-99-812-1740` + 5 secondary Jackal 2 rows `5330-99-812-4410`)
     - `spta_sector_grids` (5 rows: `bravo-4`, `bravo 4`, `su 1482 4621` -> `51.2185, -1.7925`, `alpha-1` -> `51.2310, -1.8150`, `london` -> `51.5007, -0.1246`)
     - `group_chat_tickets` (13 columns + 1 initial baseline ticket `TKT-REME-041`)
   - **MANDATORY METADATA**: The dataset and all 3 tables MUST have explicit non-empty table-level `description` metadata AND explicit non-empty column-level `description` on EVERY `bigquery.SchemaField` as specified in `teamwork_spec_miner_survey_1/handoff.md` lines 171–234.
3. **Note on Running Python in Parallel with M1**:
   - Because M1 is running `uv sync` concurrently, run your scripts via `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --no-project --with google-cloud-bigquery --with google-cloud-storage --with google-auth --with requests python3 scripts/...` (or once `.venv` is ready, `uv run python scripts/...`) so you do not race on `.venv`.

## Exclusive File Write Ownership
You and your Worker own ONLY:
- `scripts/setup_reme_datastore.py`
- `scripts/seed_demo1_bigquery.py`
Do NOT modify any other files in the repository.

## Sub-Orchestrator Procedure
This scope fits a single **2B Iteration Loop**:
1. Create `BRIEFING.md`, `progress.md`, and `SCOPE.md` in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/sub_orch_m2/`.
2. Run **2B Iteration Loop** (`3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate` in `GATE_STATUS.md`), passing `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` to every subagent and the mandatory integrity warning to your Worker.
3. When the Gate passes (`PASS`), write your `handoff.md` and send a completion message via `send_message` to `6f912669-38e4-4574-904f-704d623a5d01`.
