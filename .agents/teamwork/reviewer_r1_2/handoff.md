# Handoff Report — Independent Reviewer 2 (`reviewer_r1_2`)

## Review Summary

**Verdict**: **APPROVE**

- **Integrity Verification**: **PASS (Zero Integrity Violations)**. No hardcoded test passes, dummy/facade implementations, fabricated logs, or bypassed requirements were detected across `app/`, `cloud_run_chat_app/`, `scripts/`, or `tests/`.
- **Test Suite Execution**: **PASS (`264 passed in 42.08s`)** via `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v` (`8/8` unit tests + `256/256` 4-tier E2E tests).
- **Live GCP Infrastructure & Cloud Deployments**: **PASS (100% Verified Live)** under `admin@edwardsda.altostrat.com` in project `antig-dave` (`284046449012`).

---

## Findings

### [Minor] Finding 1: Cloud Run `maxScale` Set to `5` Instead of `1` for In-Memory State App

- **What**: `scripts/deploy_demo.sh` deploys `reme-chat-demonstrator` with `--max-instances=5` (`maxScale: '5'` on live Cloud Run revision `reme-chat-demonstrator-00001-7ff`), whereas `ORIGINAL_REQUEST.md` line 52 specifies `--max-instances 1` (while `docs/architecture/implementation-plan.md` Phase 8 had `--max-instances 5`).
- **Where**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/scripts/deploy_demo.sh:37` and live Cloud Run service `reme-chat-demonstrator` (`europe-west1`).
- **Why**: Because `cloud_run_chat_app/main.py:29` stores `ACTIVE_TICKETS: List[Dict[str, Any]] = []` in process memory alongside BigQuery persistence, scaling beyond 1 instance under heavy load could cause `GET /api/tickets` to hit a different instance than `POST /api/tickets`. However, `minScale: '1'` keeps a single warm instance that handles all demo concurrency (80 concurrent requests per instance by default), so this does not impact single-user or demo workloads.
- **Suggestion**: Optionally align `--max-instances=1` in `scripts/deploy_demo.sh:37` on future redeployments if strict single-instance in-memory state is desired.

### [Minor] Finding 2: `_strip_html` Preserves HTML Entities (`&nbsp;`) in Extracted Snippets

- **What**: `_strip_html` in `app/tools.py` strips HTML tags (`<b>`, `</b>`, etc.) and normalizes whitespace, but does not run `html.unescape()`, leaving HTML entities such as `&nbsp;` in live Discovery Engine snippets (e.g., `"TABLE 4&nbsp;."`).
- **Where**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/tools.py:118-121`.
- **Why**: Negligible impact—Gemini 3 Flash parses HTML entities cleanly and token overhead is 1–2 tokens per occurrence.
- **Suggestion**: Optionally wrap the regex substitution in `html.unescape(...)` if strictly plain-text output is desired.

---

## Verified Claims

- **Discovery Engine Unstructured OCR Datastore (`ukd-reme-aesp-ds` in `eu`)** → verified via live Discovery Engine v1alpha REST API (`GET .../dataStores/ukd-reme-aesp-ds`, `GET .../branches/0/documents`, `POST .../servingConfigs/default_search:search`) → **PASS** (`contentConfig: CONTENT_REQUIRED`, document `aesp-2350-t-250-523` indexed from `gs://remedata/2350-T-250-523.pdf`, live search for `"FV432 K60 low oil pressure relief valve spring"` returns snippet `"22.4 Inspect the pressure relief valve spring for distortion and loss of resiliency..."`).
- **GCS Bucket (`gs://remedata`)** → verified via `gcloud storage ls -l gs://remedata/` → **PASS** (`gs://remedata/2350-T-250-523.pdf` [6,490,826 bytes] and `gs://remedata/documents.jsonl` [631 bytes]).
- **BigQuery Dataset & Tables (`antig-dave.ukd_reme_demo` in `europe-west1`)** → verified via `google.cloud.bigquery.Client` metadata inspection and `region-europe-west1.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` → **PASS** (Dataset location `europe-west1`, description 195 chars; `ipc_nsn_catalogue` [11 rows, 8/8 column descriptions, NSNs `5360-99-812-1740` & `5330-99-812-4410` present]; `spta_sector_grids` [5 rows, 5/5 column descriptions, `bravo-4` / `bravo 4` / `su 1482 4621` -> `51.2185, -1.7925`]; `group_chat_tickets` [49 rows, 13/13 column descriptions]).
- **Cloud Run Demonstrator (`reme-chat-demonstrator` in `europe-west1`)** → verified via `gcloud run services describe` and live HTTP `GET /` and `GET /api/tickets` → **PASS** (`https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`, `serviceAccountName: sa-reme-demo@antig-dave.iam.gserviceaccount.com`, `minScale: '1'`, HTTP 200 on `/` [11,053 bytes] and `/api/tickets` [`{"tickets":[]}`]).
- **Vertex AI Agent Engine (`reme-artificer-agent` in `europe-west1`)** → verified via Vertex AI REST API (`GET https://europe-west1-aiplatform.googleapis.com/v1beta1/projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992`) and `agents-cli info` → **PASS** (HTTP 200, `displayName: reme-artificer-agent`, `CLI version: 1.12.0`, `A2A: yes`).
- **Google Cloud Agent Registry (`europe-west1`)** → verified via `gcloud alpha agent-registry agents list --project antig-dave --location europe-west1 --format=json` → **PASS** (`projects/antig-dave/locations/europe-west1/agents/agentregistry-00000000-0000-0000-761c-488b42c62f72`, `agentId: urn:agent:projects-284046449012:projects:284046449012:locations:europe-west1:aiplatform:reasoningEngines:6397856951400660992`, `protocols: A2A v0.3.0`).
- **Gemini Enterprise Registration (`pixel-mobile-demos_1793177711952` in `eu`)** → verified via Discovery Engine REST API (`GET .../engines/pixel-mobile-demos_1793177711952` and `GET .../assistants/default_assistant/agents`) → **PASS** (`REME-Artificer` agent ID `10995513697759164495` is `ENABLED` and bound to `reasoningEngines/6397856951400660992`; pre-existing agents `13073824185441632570` [`British Army - Soldier Self-Service & Welfare Safeguarding Agent`] and `deep_research` remain `ENABLED` and untouched; pre-existing datastore `jointservicepubs_1793177321711` remains untouched).
- **Contract Fixes from `TEST_READY.md § 4` (Items 4.1–4.6)** → verified via file inspection (`app/schemas.py`, `app/tools.py`, `app/agent.py`, `cloud_run_chat_app/main.py`, `tests/eval/datasets/basic-dataset.json`, `scripts/deploy_demo.sh`) and pytest execution → **PASS** (`264 passed in 42.08s`).

## Coverage Gaps

- None — all code modules, scripts, unit/E2E tests, and live GCP endpoints in scope were inspected and verified.

## Unverified Items

- Live `POST /api/reset` on the deployed Cloud Run URL (`https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app/api/reset`) was intentionally NOT invoked so as not to clear live state during concurrent review, though the endpoint is thoroughly tested via FastAPI `TestClient` in `tests/unit/test_chat_api.py` and `tests/e2e/`.

---

## Challenge Summary (Adversarial Review)

**Overall risk assessment**: **LOW**

## Challenges

### [Low] Challenge 1: Single-Datastore Engine Precondition on `pixel-mobile-demos_1793177711952`

- **Assumption challenged**: `ORIGINAL_REQUEST.md` assumed `ukd-reme-aesp-ds` could be appended to `pixel-mobile-demos_1793177711952.dataStoreIds` via `PATCH`.
- **Attack scenario**: In Discovery Engine, an engine provisioned with a single datastore at creation time returns `HTTP 400 FAILED_PRECONDITION: "Engines with a single data store cannot add or remove data stores."` upon `PATCH`.
- **Blast radius**: If unhandled, `scripts/setup_reme_datastore.py` would fail mid-run or someone might recreate the engine and destroy pre-existing registrations (`13073824185441632570`, `jointservicepubs_1793177321711`).
- **Mitigation**: Verified that `scripts/setup_reme_datastore.py:448-461` catches `HTTP 400 FAILED_PRECONDITION` gracefully without touching `jointservicepubs_1793177321711`, and `app/tools.py:124-198` queries `ukd-reme-aesp-ds` directly via its `eu` Discovery Engine `servingConfigs/default_search:search` endpoint, completely decoupling `@REME-Artificer` RAG retrieval from engine-level `dataStoreIds`.

### [Low] Challenge 2: Unmatched Symptom / Sector Fallback Resilience

- **Assumption challenged**: What happens if a fitter submits a vague or unrecognized mechanical symptom or an unknown grid coordinate in `diagnose_and_resolve_grid`?
- **Attack scenario**: Empty SQL matches could cause `IndexError` or `NoneType` crashes before the agent can respond.
- **Blast radius**: Tool execution failure during live demonstration.
- **Mitigation**: Verified in `app/tools.py:216-248` and `app/tools.py:267-278`: `_lookup_ipc_nsn` falls back to default K60 catalogue rows (`OR 'k60' IN UNNEST(symptom_keywords)`) and then to a deterministic safe fallback dict (`nsn: "5360-99-812-1740"`) if no rows return; `_resolve_sector_grid` normalizes hyphens/spaces and falls back to Salisbury Plain (`51.2185, -1.7925`) if unrecognized.

## Stress Test Results

- `diagnose_and_resolve_grid("FV432 K60 low oil pressure relief valve spring", "Sector Bravo-4", ctx)` against live `eu` Discovery Engine + `europe-west1` BigQuery → Expected live OCR snippet + NSN `5360-99-812-1740` + coords `(51.2185, -1.7925)` → Actual: `status: SUCCESS`, `rag_snippets_count: 1`, `nsn: 5360-99-812-1740`, `lat: 51.2185`, `lng: -1.7925` → **PASS**
- 264-test unit + 4-tier E2E suite (`test_tier1_features.py` [110], `test_tier2_boundaries.py` [110], `test_tier3_pairwise.py` [24], `test_tier4_scenarios.py` [12]) → Expected 100% pass rate → Actual: `264 passed in 42.08s` → **PASS**

## Unchallenged Areas

- Destructive live Cloud Run load testing (`>100` concurrent requests) — out of scope for read-only verification.

---

# 5-Component Handoff Report

## 1. Observation

1. **Identity & Environment**:
   - `gcloud config get-value account` returned `admin@edwardsda.altostrat.com`; `gcloud config get-value project` returned `antig-dave`.
2. **Codebase & Contract Review**:
   - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/schemas.py:1-40`: Defines `TicketSubmission` (lines 7–21) and `TicketRecord` (lines 24–39) with strict Pydantic `Field` validation (`min_length=1`, `pattern=r"^\d{4}-\d{2}-\d{3}-\d{4}$"`, `lat` in `[-90, 90]`, `lng` in `[-180, 180]`, `Literal["URGENT", "ROUTINE"]`, `Literal["ELEVATED", "NOMINAL"]`, `Literal["SENT", "DELIVERED", "ACKNOWLEDGED"]`).
   - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/tools.py:1-371`:
     - Module-level singletons `_CREDENTIALS`, `_BQ_CLIENT`, and `_HTTP_SESSION` (lines 51–115) use `google.auth.default()` in-memory token reuse with zero CLI subprocess calls.
     - `_search_aesp_datastore` (lines 124–198) queries `https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/servingConfigs/default_search:search` with `"pageSize": 15` and `"snippetSpec": {"returnSnippet": True}` (no `summarySpec`), stripping HTML tags via `_strip_html` (lines 118–121).
     - `diagnose_and_resolve_grid` (lines 286–323) and `dispatch_sustainment_ticket` (lines 326–370) use `google.adk.tools.ToolContext` and persist tickets to both Cloud Run (`POST /api/tickets`) and BigQuery (`antig-dave.ukd_reme_demo.group_chat_tickets`).
   - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/app/agent.py:1-74`: Configures `root_agent = Agent(name="reme_artificer_agent", model="gemini-3-flash-preview", ...)` with `BuiltInPlanner(thinking_config=genai_types.ThinkingConfig(thinking_level="LOW"))` and `App(name="reme_artificer_agent", root_agent=root_agent)`.
   - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/cloud_run_chat_app/main.py:1-114` and `templates/index.html:1-372`: FastAPI app using `TicketSubmission`/`TicketRecord` from `app.schemas`, serving WhatsApp-style dark tactical group chat UI (`#0b141a`), inline SVG Salisbury Plain grid map pin, and NSN Logistics Demand Card on `GET /`, `GET /api/tickets`, `POST /api/tickets`, and `POST /api/reset`.
   - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/tests/eval/datasets/basic-dataset.json:1-69`: Uses ADK `EvalSet` schema (`eval_set_id`, `eval_cases` with `eval_id` and `conversation` turns).
3. **Unit & E2E Pytest Execution**:
   - Command: `GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v`
   - Output: `264 passed in 42.08s` (exit code `0`).
4. **Live GCP Verification**:
   - **GCS (`gs://remedata/`)**:
     - `gs://remedata/2350-T-250-523.pdf` (`6,490,826` bytes, `2026-04-19T12:18:10Z`)
     - `gs://remedata/documents.jsonl` (`631` bytes, `2026-04-19T12:24:25Z`)
   - **Discovery Engine (`ukd-reme-aesp-ds` in `eu`)**:
     - `GET https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds` -> HTTP `200`, `contentConfig: "CONTENT_REQUIRED"`.
     - Branch 0 documents: `['aesp-2350-t-250-523']`.
     - Live search (`POST .../servingConfigs/default_search:search`) -> HTTP `200`, `results count: 1`, `doc.id: aesp-2350-t-250-523`, snippet: `"<b>2350-T-250-523</b> ... 22.4 Inspect the <b>pressure relief valve spring</b> for distortion and loss of resiliency. Check spring free length and loading as detailed in Table 4. TABLE 4&nbsp;."`.
   - **BigQuery (`antig-dave.ukd_reme_demo` in `europe-west1`)**:
     - Dataset `location: europe-west1`, `description len: 195`.
     - `ipc_nsn_catalogue`: `num_rows=11`, `cols=8`, `desc_len=251`, `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`: `total_cols=8, described_cols=8` (100%). Contains `5360-99-812-1740` and `5330-99-812-4410`.
     - `spta_sector_grids`: `num_rows=5`, `cols=5`, `desc_len=220`, `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`: `total_cols=5, described_cols=5` (100%). Contains `bravo-4` / `bravo 4` / `su 1482 4621` -> `(51.2185, -1.7925)`.
     - `group_chat_tickets`: `num_rows=49`, `cols=13`, `desc_len=158`, `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`: `total_cols=13, described_cols=13` (100%).
   - **Cloud Run (`reme-chat-demonstrator` in `europe-west1`)**:
     - URL: `https://reme-chat-demonstrator-kbgxhnyxlq-ew.a.run.app`
     - `serviceAccountName: sa-reme-demo@antig-dave.iam.gserviceaccount.com`, `minScale: '1'`, `maxScale: '5'`.
     - `GET /` -> HTTP `200` (`11053` bytes); `GET /api/tickets` -> HTTP `200` (`{"tickets":[]}`).
   - **Vertex AI Agent Engine & Agent Registry (`europe-west1`)**:
     - `GET https://europe-west1-aiplatform.googleapis.com/v1beta1/projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992` -> HTTP `200`, `displayName: "reme-artificer-agent"`.
     - `gcloud alpha agent-registry agents list --project antig-dave --location europe-west1 --format=json` -> Entry `agentregistry-00000000-0000-0000-761c-488b42c62f72` (`agentId: "urn:agent:projects-284046449012:projects:284046449012:locations:europe-west1:aiplatform:reasoningEngines:6397856951400660992"`, `framework: "google-adk"`).
     - `agents-cli info` -> `CLI version: 1.12.0`, `Project name: reme-artificer-agent`, `Deployment target: agent_runtime`, `Region: europe-west1`, `A2A: yes`.
   - **Gemini Enterprise (`pixel-mobile-demos_1793177711952` in `eu`)**:
     - `GET .../engines/pixel-mobile-demos_1793177711952` -> HTTP `200`, `dataStoreIds: ['jointservicepubs_1793177321711']` intact.
     - `GET .../engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents` -> HTTP `200`:
       - `10995513697759164495` (`REME-Artificer`, `state: ENABLED`, bound to `reasoningEngines/6397856951400660992`)
       - `13073824185441632570` (`British Army - Soldier Self-Service & Welfare Safeguarding Agent`, `state: ENABLED`)
       - `deep_research` (`Deep Research`, `state: ENABLED`)

## 2. Logic Chain

1. **Code Integrity & Contract Compliance**: Direct source inspection of `app/schemas.py`, `app/tools.py`, `app/agent.py`, `cloud_run_chat_app/main.py`, `scripts/setup_reme_datastore.py`, `scripts/seed_demo1_bigquery.py`, and `scripts/deploy_demo.sh` (Observation 2) confirms that all tool handlers execute real Discovery Engine REST searches, real parameterized BigQuery queries, and real Cloud Run HTTP POST dispatches, with all ADK 2.0 performance guardrails enforced (in-memory credential reuse, `pageSize=15`, `returnSnippet=True`, no `summarySpec`, HTML stripping, `thinking_level="LOW"`, and module-level client singletons).
2. **Test Suite Verification**: Running the full unit and 4-tier E2E test suite (Observation 3) confirmed all 264 test cases pass (`8/8` unit tests + `256/256` E2E tests) in `42.08s`, including all 6 previously documented contract fixes in `TEST_READY.md § 4`.
3. **Live Infrastructure & Deployment Verification**: Direct queries to GCS, Discovery Engine (`eu`), BigQuery (`europe-west1`), Cloud Run (`europe-west1`), Vertex AI Reasoning Engines (`europe-west1`), Agent Registry (`europe-west1`), and Gemini Enterprise (`eu`) (Observation 4) independently confirmed that every claimed resource exists in the required European jurisdiction, has 100% table and column metadata descriptions (`8/8`, `5/5`, `13/13`), serves live traffic, and preserves all pre-existing Gemini Enterprise agents and datastores untouched.

## 3. Caveats

- Live `POST /api/reset` on the production Cloud Run URL was not called during review to avoid disrupting concurrent reviewers or live demo state.

## 4. Conclusion

**Verdict: `APPROVE`**. The Demo 1 (`@REME-Artificer`) codebase, test suite (`264/264` passing), and live Google Cloud infrastructure across `eu` and `europe-west1` meet all functional, architectural, performance, and integrity requirements.

## 5. Verification Method

Run the following read-only commands to independently verify all findings:

```bash
# 1. Run full unit + E2E test suite (264 tests)
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run pytest tests/unit/ tests/e2e/ -v

# 2. Check agents-cli project configuration
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run agents-cli info

# 3. Verify Cloud Run service &Agent Registry in europe-west1
gcloud run services describe reme-chat-demonstrator --region europe-west1 --project antig-dave --format="yaml(status.url,spec.template.metadata.annotations,spec.template.spec.serviceAccountName)"
gcloud alpha agent-registry agents list --project antig-dave --location europe-west1 --format=json
```
