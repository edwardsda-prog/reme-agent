# Dispatch: Worker GCP Infrastructure (M2 — Discovery Engine `ukd-reme-aesp-ds`, BigQuery `ukd_reme_demo`, & Service Account `sa-reme-demo`) — 2026-10-29T11:29:00Z

## Role & Identity
- **Identity**: `worker_gcp_m2` (`teamwork_worker`)
- **Working Directory (metadata only)**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_gcp_m2/`
- **Parent Orchestrator Conversation ID**: `6f912669-38e4-4574-904f-704d623a5d01`

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Required Reading Before Starting
1. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` (MANDATORY)
2. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
3. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md` (Phases 2, 3, and 8.1)
4. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_explorer_survey_3/handoff.md` (Live GCP audit findings)
5. `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_1/handoff.md`
6. Domain Skill: `/usr/local/google/home/edwardsda/.agents/skills/discovery-engine-adk-integration/SKILL.md`

## Exclusive File Write Ownership
You have EXCLUSIVE write ownership of:
- `scripts/setup_reme_datastore.py`
- `scripts/seed_demo1_bigquery.py`

**CRITICAL BOUNDARY**:
- Do NOT modify `pyproject.toml`, `uv.lock`, `.env`, `app/`, `cloud_run_chat_app/`, `tests/`, `AGENTS.md`, or `docs/`.
- When running Python scripts while `worker_core_m1_m3` is running `uv sync` in parallel, execute them with `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --no-project --with google-cloud-bigquery --with google-cloud-storage --with google-auth --with requests python3 scripts/...` so you never touch or lock the root `.venv` or `uv.lock`!
- Always verify active `gcloud` account is `admin@edwardsda.altostrat.com` (NEVER `edwardsda@google.com`).

## Deliverables & Execution Steps
1. **Service Account & IAM Provisioning**:
   - Create `sa-reme-demo@antig-dave.iam.gserviceaccount.com` (idempotently) in project `antig-dave`.
   - Bind required IAM roles on `antig-dave`:
     - `roles/bigquery.dataEditor`
     - `roles/bigquery.jobUser`
     - `roles/discoveryengine.viewer`
     - `roles/aiplatform.user`
     - `roles/storage.objectViewer`
     - `roles/logging.logWriter`
     - `roles/cloudtrace.agent`
2. **Phase 2: Discovery Engine Datastore (`scripts/setup_reme_datastore.py`)**:
   - Write `scripts/setup_reme_datastore.py` per `docs/architecture/implementation-plan.md` Phase 2 and `teamwork_explorer_survey_3/handoff.md`:
     - Verify `gs://remedata/2350-T-250-523.pdf` exists in `antig-dave`.
     - Generate rich NDJSON `documents.jsonl` (`id: "aesp-2350-t-250-523"`, `jsonData` with `title`, `aesp_reference`, `chapter_paragraph`, `equipment_platform`, `component`, `ipc_army_code`, `nsn`, `security_classification`, `unit`, and `content` pointing to `gs://remedata/2350-T-250-523.pdf`) and upload to `gs://remedata/documents.jsonl`.
     - Create unstructured OCR datastore `ukd-reme-aesp-ds` in `location=eu` (`ocrParsingConfig.useNativeText = True`, handling HTTP 409 idempotently).
     - Trigger incremental import (`branches/0/documents:import` with `reconciliationMode: "INCREMENTAL"`) from `gs://remedata/documents.jsonl` and poll LRO to completion.
     - Verify search against `ukd-reme-aesp-ds` (`servingConfigs/default_search:search`, `pageSize: 15`, `snippetSpec: {"returnSnippet": True}`).
     - **CRITICAL ENGINE PATCH**: In `location=eu`, the Gemini Enterprise engine with `displayName == "pixel_mobile_demos"` has actual `engineId` **`pixel-mobile-demos_1793177711952`** (and its existing datastore `jointservicepubs` has actual `dataStoreId` **`jointservicepubs_1793177321711`**). Resolve the engine dynamically (by checking `pixel-mobile-demos_1793177711952` and listing engines matching `displayName == "pixel_mobile_demos"`), read its existing `dataStoreIds` (`["jointservicepubs_1793177321711"]`), compute the non-destructive union `list(dict.fromkeys(existing_ids + ["ukd-reme-aesp-ds"]))`, and PATCH `?updateMask=dataStoreIds`. Verify via GET afterwards that BOTH `jointservicepubs_1793177321711` and `ukd-reme-aesp-ds` are present on `pixel-mobile-demos_1793177711952` and existing agents (`13073824185441632570` and `deep_research`) are untouched!
3. **Phase 3: BigQuery Provisioning (`scripts/seed_demo1_bigquery.py`)**:
   - Write and execute `scripts/seed_demo1_bigquery.py` to create dataset `antig-dave.ukd_reme_demo` (`location="europe-west1"`) with dataset `description`, and create + seed all 3 tables (`ipc_nsn_catalogue`, `spta_sector_grids`, `group_chat_tickets`) with non-empty table-level `description` and non-empty column-level `description` on EVERY `bigquery.SchemaField`.
   - Verify via BigQuery queries that all rows (`5360-99-812-1740`, `5330-99-812-4410`, `51.2185, -1.7925`, `51.2310, -1.8150`, `51.5007, -0.1246`, `TKT-REME-041`) and all table/column descriptions are populated in `INFORMATION_SCHEMA`.
4. Write `progress.md` and `handoff.md` in `.agents/teamwork/worker_gcp_m2/` and notify parent (`6f912669-38e4-4574-904f-704d623a5d01`) via `send_message`.


## 2026-10-29T11:31:04Z
You are `worker_gcp_m2` (`teamwork_worker`), assigned to implement and execute Milestone M2 (Service Account `sa-reme-demo@antig-dave.iam.gserviceaccount.com` + IAM bindings, Discovery Engine datastore `ukd-reme-aesp-ds` & `pixel_mobile_demos` patching in `scripts/setup_reme_datastore.py`, and BigQuery `antig-dave.ukd_reme_demo` provisioning & seeding in `scripts/seed_demo1_bigquery.py`).
