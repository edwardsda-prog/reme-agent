# Specification Miner Report — Architecture, Guardrails & CLI Skills (`teamwork_spec_miner_survey_2`)

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Architecture & Identity | GCP Project & IAM Identity Enforcement | Strict target project (`antig-dave`), authorized active principal (`admin@edwardsda.altostrat.com`), dedicated runtime service account (`sa-reme-demo@antig-dave.iam.gserviceaccount.com`), Reasoning Engine service agent (`service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`), and mTLS bypass (`GOOGLE_API_USE_CLIENT_CERTIFICATE=false`). | `gcloud config get-value account`, `gcloud config get-value project`, `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` | Authenticated GCP API & ADC operations under `admin@edwardsda.altostrat.com` and `sa-reme-demo@antig-dave.iam.gserviceaccount.com` | Using `edwardsda@google.com` or omitting `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` causes 403/mTLS handshake failures in sandbox | `ORIGINAL_REQUEST.md` (R2), `Demo 1 - SA.md` (§2, §9), `implementation-plan.md` (Phase 1) |
| 2 | Architecture & Residency | Strict EU / Belgium Data Residency | Compute, LLM inference (`gemini-2.5-flash`), Agent Engine (`agent_runtime`), Agent Registry, Cloud Run (`reme-chat-demonstrator`), and BigQuery (`ukd_reme_demo`) pinned to `europe-west1` (Belgium); Discovery Engine (`ukd-reme-aesp-ds`, `pixel_mobile_demos`) pinned to `eu` multi-region (`https://eu-discoveryengine.googleapis.com/v1alpha/...`). | `.env` and runtime env vars (`GOOGLE_CLOUD_LOCATION=europe-west1`, `BQ_LOCATION=europe-west1`, `DISCOVERY_ENGINE_LOCATION=eu`) | All storage, inference, and search execute strictly in `europe-west1` / `eu` | Defaulting Discovery Engine to `global` or `us` returns `404 NOT_FOUND` for `ukd-reme-aesp-ds` and `pixel_mobile_demos` | `ORIGINAL_REQUEST.md` (R2, R4), `Demo 1 - SA.md` (§2, §4), `implementation-plan.md` |
| 3 | Agent Topology (ADK 2.0) | Single-Agent Architecture (`reme_artificer_agent`) | Single `LlmAgent` (`name="reme_artificer_agent"`, `model="gemini-2.5-flash"`, `temperature=0.0`) exported as `root_agent` in `app/agent.py` with `App(name="app", root_agent=root_agent)` in `app/fast_api_app.py`. Zero sub-agent delegation to prevent the 39–70% sequential handoff penalty. | Text or multimodal (image + spoken fault/grid) user turns | Scene 1: Grounded AESP Diagnostic Card with 15s Audio Brief + 3 `<details open>` collapsible chips; Scene 2: Ticket confirmation badge `✅ Ticket TKT-REME-XXXX Published to 4 Bn REME Group Chat` | `App(name=...)` mismatch with directory name `app` causes `ValueError: Agent directory name mismatch` at runtime | `Demo 1 - SA.md` (§3, §5.1, §5.2), `implementation-plan.md` (Phase 4.3), `google-agents-cli-adk-code` |
| 4 | Agent Tools (ADK 2.0) | Composite Tool 1: `diagnose_and_resolve_grid` | Executes single-pass RAG + BigQuery NSN & Grid resolution: (1) queries `ukd-reme-aesp-ds` (`pageSize=15`, `returnSnippet=True`, no `summarySpec`), (2) queries `ukd_reme_demo.ipc_nsn_catalogue` via parameterized SQL, (3) queries `ukd_reme_demo.spta_sector_grids` via parameterized SQL, (4) stores merged `ActiveTicketState` dict into `tool_context.state["active_ticket"]`. | `fault_query: str`, `spoken_sector_grid: str`, `tool_context: ToolContext` (no default values; `tool_context` omitted from docstring) | Dict matching `ActiveTicketState` (`equipment`, `fault_summary`, `aesp_reference`, `nsn_required`, `part_description`, `repair_level`, `sector_grid`, `latitude`, `longitude`, `coords_label`, `diagnostic_snippets`) | On empty query result or exception, returns deterministic Golden-Path Fallback (`GOLDEN_FALLBACK_K60` or `GOLDEN_FALLBACK_JACKAL` + `GOLDEN_FALLBACK_GRID`) and still writes `tool_context.state["active_ticket"]` | `Demo 1 - SA.md` (§3.2, §5.2), `implementation-plan.md` (Phase 4.2), `google-agents-cli-adk-code` |
| 5 | Agent Tools (ADK 2.0) | Composite Tool 2: `publish_ticket_to_chat` | Reads `tool_context.state.get("active_ticket")`, builds `TicketPayload` (`TKT-REME-XXXX`, `created_at_utc`, `callsign="Cpl MacDonald (4 Bn REME FRT)"`, Google Maps URL, `status="DISPATCH_READY"`), POSTs to `{CLOUD_RUN_CHAT_URL}/api/tickets` (`timeout=2.0`), and inserts audit record into BigQuery `ukd_reme_demo.group_chat_tickets`. | `tool_context: ToolContext` (omitted from docstring) | `{"status": "SUCCESS", "confirmation_badge": "✅ Ticket TKT-REME-XXXX Published to 4 Bn REME Group Chat", "ticket": payload}` | If `tool_context.state["active_ticket"]` is missing (e.g., stateless Scene 2 call), synthesizes payload from `GOLDEN_FALLBACK_K60` + `GOLDEN_FALLBACK_GRID`; catches HTTP/BQ errors gracefully so tool never crashes | `Demo 1 - SA.md` (§3.2, §5.2), `implementation-plan.md` (Phase 4.2) |
| 6 | Data Schemas (Pydantic v2) | Strict Typed State & Payload Models (`app/schemas.py`) | Pydantic v2 `BaseModel` definitions for `ActiveTicketState` and `TicketPayload` enforcing strict typing without `any`. | Field values from tool execution | Validated dictionary (`model_dump()`) for `tool_context.state` and REST/BigQuery persistence | Raises `ValidationError` if malformed fields are passed during unit/integration tests | `implementation-plan.md` (Phase 4.1), `AGENTS.md` |
| 7 | BigQuery Data Layer | Dataset & 3 Fully Described Tables (`ukd_reme_demo`) | Provisioned in `europe-west1` via `scripts/seed_demo1_bigquery.py`: `ipc_nsn_catalogue` (≥4 rows including K60 `5360-99-812-1740` and Jackal 2 `5330-99-812-4410`), `spta_sector_grids` (≥4 rows including Bravo-4 `51.2185, -1.7925`), and `group_chat_tickets` (audit log). | `scripts/seed_demo1_bigquery.py` execution | Dataset + 3 tables populated with dataset description, table `description` on all 3 tables, and column `description` on every `SchemaField` | Missing descriptions violate `ORIGINAL_REQUEST.md` R3/R5; duplicate seeding avoided via `delete_table(..., not_found_ok=True)` + recreate | `ORIGINAL_REQUEST.md` (R3, R5), `Demo 1 - SA.md` (§4.1), `implementation-plan.md` (Phase 2.1) |
| 8 | Discovery Engine & Gemini Enterprise | Unstructured OCR Datastore (`ukd-reme-aesp-ds`) & Non-Destructive Engine Patch (`pixel_mobile_demos`) | Creates `ukd-reme-aesp-ds` in `eu` (`SOLUTION_TYPE_SEARCH`, `CONTENT_REQUIRED`, `ocr-parser-1` enabled), uploads 2 PDFs (`FV432_K60_Engine_AESP.pdf`, `Jackal2_Coyote_Suspension_AESP.pdf`) + `metadata.jsonl` to `gs://antig-dave-reme-aesp-eu`, imports incrementally, and patches `pixel_mobile_demos.dataStoreIds` with the union of existing datastores (`jointservicepubs`) + `ukd-reme-aesp-ds`. | `scripts/setup_demo1_discovery_engine.py` | Indexed OCR AESP datastore bound to `pixel_mobile_demos` alongside existing `jointservicepubs` | `409 ALREADY_EXISTS` handled idempotently; overwriting `dataStoreIds` without reading existing IDs would break pre-existing demos (strictly forbidden) | `ORIGINAL_REQUEST.md` (R2, R3, R5), `Demo 1 - SA.md` (§4.2), `discovery-engine-adk-integration` |
| 9 | Cloud Run Receiver App | 4 Bn REME Live Group Chat Demonstrator (`cloud_run_chat_app/`) | FastAPI + Uvicorn app (`reme-chat-demonstrator`) deployed to Cloud Run (`europe-west1`, `--allow-unauthenticated`). Serves Dark Olive/Amber military tactical UI (`GET /`), accepts tickets (`POST /api/tickets`), lists tickets (`GET /api/tickets`), and resets demo (`POST /api/tickets/reset`), backed by in-memory deque + BigQuery `ukd_reme_demo.group_chat_tickets`. | `POST /api/tickets` JSON (`TicketPayload`), `GET /api/tickets`, `GET /` (1.5s auto-polling UI) | HTTP 200 JSON (`{"status": "published", "ticket_id": ...}` or `{"tickets": [...]}`) and rendered HTML card with clickable Google Maps link (`target="_blank"`) | If BigQuery fallback query fails on empty memory, logs warning and returns `{"tickets": []}` without HTTP 500 | `ORIGINAL_REQUEST.md` (R4, R5), `Demo 1 - SA.md` (§4.3, §6), `implementation-plan.md` (Phase 3) |
| 10 | ADK 2.0 Performance Guardrails | Sub-Second Tool Execution Invariants | (1) Module-level singleton `bigquery.Client` and `google.auth.default()` token caching (no `gcloud` subprocesses); (2) Single-pass `pageSize: 15` retrieval; (3) `snippetSpec: {"returnSnippet": True}` only (omit `summarySpec`); (4) Strip `<b>`/`</b>` tags and whitespace; (5) Single-agent topology with 2 tools (`temperature=0.0`, `max_output_tokens=1024`). | Tool calls inside `app/tools.py` and `LlmAgent` config in `app/agent.py` | End-to-end Scene 1 tool latency <1.5s (vs 30s+ with multi-turn pagination or CLI token spawning) | Spawning `gcloud auth print-access-token` adds 1.5–2.0s per call; including `summarySpec` adds ~3.0s duplicate LLM latency | `adk-2.0-performance-guardrails.md`, `Demo 1 - SA.md` (§2, §3.3), `implementation-plan.md` |
| 11 | `agents-cli` (v1.12.0) | Two-Step Project Scaffolding (`scaffold create` + `scaffold enhance`) | Creates ADK `agent_runtime` scaffold in `/tmp/reme-artificer-agent` and enhances workspace root while preserving `AGENTS.md` and `docs/`. | `agents-cli scaffold create reme-artificer-agent --output-dir /tmp --agent adk --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md --prototype` followed by copy and `agents-cli scaffold enhance . --deployment-target agent_runtime --region europe-west1 --agent-guidance-filename AGENTS.md` | `app/`, `tests/`, `pyproject.toml`, `.agents.yaml` configured for `agent_runtime` in `europe-west1` | Running `scaffold create` directly on an existing directory or a directory name with spaces/uppercase (`Demo 1 - Reme`) fails validation (must be `^[a-z0-9-]+$`, ≤26 chars) | `google-agents-cli-scaffold`, `implementation-plan.md` (Phase 4.0) |
| 12 | `agents-cli` (v1.12.0) | Local Execution & Warm Server (`agents-cli run`) | Runs agent locally in-process or against a persistent local FastAPI server (`--start-server` / `--stop-server`) to preserve multi-turn session state (`--session-id`) across Scene 1 and Scene 2. | `agents-cli run "<prompt>" [--start-server] [--session-id <id>] [-f <file>] [-v]` | Agent response text, tool call summary, and `Session ID: <uuid>` | Without `--start-server`, in-memory session state is lost when the CLI process exits after Scene 1 | `google-agents-cli-workflow`, `agents-cli run --help` |
| 13 | `agents-cli` (v1.12.0) | Evaluation Suite (`agents-cli eval run`) | Generates agent traces locally and grades them via Vertex Evaluation Service or local custom functions using `tests/eval/eval_config.yaml` and `tests/eval/datasets/basic-dataset.json`. | `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli eval run --config tests/eval/eval_config.yaml --project antig-dave` | Console score table + `artifacts/inference_results/` and `artifacts/grade_results/results_<timestamp>.json` | Exits `0` even if metric scores are `0.0`; single-turn managed metrics fail with `400 FAILED_PRECONDITION` if dataset contains multi-turn cases | `google-agents-cli-eval`, `agents-cli eval run --help` |
| 14 | `agents-cli` (v1.12.0) | Managed Agent Runtime Deployment (`agents-cli deploy`) | Deploys `app/` to Vertex AI Agent Engine (`agent_runtime`) in `europe-west1` with `--min-instances 1`, custom service account, and environment variables, writing `deployment_metadata.json` and auto-registering in Agent Registry. | `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli deploy --project antig-dave --region europe-west1 --service-account sa-reme-demo@antig-dave.iam.gserviceaccount.com --min-instances 1 --env-vars "..."` | `deployment_metadata.json` with `remote_agent_engine_id` (`projects/.../locations/europe-west1/reasoningEngines/<ID>`) | Passing deprecated flag `--no-confirm-project` fails in `agents-cli 1.12.0` (`No such option: --no-confirm-project`); use `--project antig-dave` instead | `google-agents-cli-deploy`, `agents-cli deploy --help` (`task-29`) |
| 15 | `agents-cli` (v1.12.0) | Non-Destructive Gemini Enterprise Publishing (`agents-cli publish gemini`) | Registers or updates the deployed Reasoning Engine on `pixel_mobile_demos` (`eu` location auto-detected from engine resource name) via `_upsert_agent` without disturbing any other registered agents. | `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli publish gemini --agent-runtime-id "<RESOURCE_NAME>" --gemini-enterprise-app-id "projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos" --display-name "REME-Artificer" --description "..."` | Agent resource `.../engines/pixel_mobile_demos/assistants/default_assistant/agents/<ID>` created or updated in `eu` | Interactive prompts hang if `--agent-runtime-id`, `--gemini-enterprise-app-id`, `--display-name`, and `--description` are not all passed explicitly | `google-agents-cli-publish`, `cmd_publish.py`, `agents-cli publish gemini --help` (`task-29`) |

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `AGENTS.md` Legacy Template Boilerplate vs. Python ADK 2.0 Architecture | Reading `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/AGENTS.md` alongside `Demo 1 - SA.md` and `implementation-plan.md` | `AGENTS.md` lines 3–6 and 17–19 contain residual web-template text (`Next.js 14`, `PostgreSQL via Prisma ORM`, `TypeScript`, `Jest`), whereas `AGENTS.md` line 9 explicitly designates `docs/architecture/Demo 1 - SA.md` (`SDD-DEMO1-ADK2-003`) as the **Primary Architecture & Design Reference**. `ORIGINAL_REQUEST.md` R1 forbids modifying `AGENTS.md`. Resolution: keep `AGENTS.md` untouched on disk, apply its universal engineering mandates (`google-genai` SDK, explicit error boundaries, strict Pydantic v2 types, local execution, browser screenshot verification, unit/integration tests via `pytest`), and build the 100% Python ADK 2.0 + FastAPI + BigQuery + Discovery Engine stack defined in `Demo 1 - SA.md` and `implementation-plan.md`. |
| 2 | `agents-cli deploy` Flag Change in v1.12.0 | Passing `--no-confirm-project` (shown in `implementation-plan.md` line 251 and older skill text) to `agents-cli deploy` v1.12.0 | Verified via `agents-cli deploy --help` (`task-29`): `agents-cli` v1.12.0 does **not** have a `--no-confirm-project` option. Passing `--no-confirm-project` causes Click to abort with `Error: No such option: --no-confirm-project`. Passing `--project antig-dave` explicitly already bypasses interactive project confirmation. |
| 3 | `agents-cli scaffold create` Directory & Name Constraints | Running `agents-cli scaffold create` inside `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` | Project name must match `^[a-z0-9-]+$` and be ≤26 characters (`Demo 1 - Reme` is invalid due to uppercase, spaces, and existing directory). Must scaffold to `/tmp/reme-artificer-agent` (`--output-dir /tmp`), copy scaffold files into workspace root without overwriting `AGENTS.md` or `docs/`, and then run `agents-cli scaffold enhance .`. |
| 4 | `agents-cli eval` Single-Turn vs. Multi-Turn Metric Crash | Including a multi-turn `EvalCase` (2+ turns in `agent_data.turns`) in `basic-dataset.json` while `eval_config.yaml` lists single-turn managed metrics (`final_response_quality`, `tool_use_quality`, `hallucination`, `safety`, `final_response_match`) | Vertex Evaluation Service returns `400 FAILED_PRECONDITION: Single-turn metric '<name>_v1' received agent_eval_data with 2 turns, expected 1` and drops that metric for the entire run. If `basic-dataset.json` mixes single-turn and multi-turn cases, either use multi-turn metrics (`multi_turn_task_success`, `multi_turn_trajectory_quality`, `multi_turn_tool_use_quality`) + local `custom_metrics` (`custom_function`), OR keep `basic-dataset.json` cases single-turn (one Scene 1 case, one Scene 2 case where `publish_ticket_to_chat` uses its Golden-Path Fallback when `active_ticket` is absent). |
| 5 | `agents-cli eval` Region Compatibility (`global` vs `europe-west1`) | Passing `--region europe-west1` to `agents-cli eval run` or `eval grade` | The Vertex Evaluation Service backend is only available in select regions (`global`, `us-central1`) and returns `400 FAILED_PRECONDITION: Unsupported region for Vertex Evaluation Service` if forced to an unsupported region. Leave `--region` unset on `agents-cli eval run` (defaults to `global` for the grading service) while `.env` keeps `GOOGLE_CLOUD_LOCATION=europe-west1` for the agent's own `eval generate` inference, or include local `custom_metrics` (`execution: local`) which run in-process without region limits. |
| 6 | Shared `pixel_mobile_demos` Engine Datastore Binding (`eu`) | Patching `dataStoreIds` on `projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos` | `pixel_mobile_demos` already has `dataStoreIds: ["jointservicepubs"]` attached. Overwriting `dataStoreIds` with `["ukd-reme-aesp-ds"]` alone detaches `jointservicepubs` and breaks sibling demos (`ORIGINAL_REQUEST.md` R2/R5). The PATCH script MUST GET the current `dataStoreIds` list first, take the union (`["jointservicepubs", "ukd-reme-aesp-ds"]`), and PATCH with `?updateMask=dataStoreIds`. |
| 7 | Shared `pixel_mobile_demos` Stale Agent Cleanup Hazard | Running Section 3 ("Purging stale Agent Registrations") from `discovery-engine-adk-integration/SKILL.md` | Section 3 of `discovery-engine-adk-integration` contains a generic loop that issues `DELETE` on **every** agent registered in the target Gemini Enterprise engine. In `pixel_mobile_demos`, this would destroy other shared demos in `antig-dave`! Instead, use `agents-cli publish gemini` (verified in `cmd_publish.py` `_upsert_agent` to only update an agent matching `agent_runtime_id` or create a new one), or if pruning stale REME registrations via REST, filter strictly by `agent.get("displayName") == "REME-Artificer"`. |
| 8 | Scene 2 Stateless Invocation / Missing `active_ticket` in `tool_context.state` | Invoking `publish_ticket_to_chat` in a fresh session (e.g., single-turn eval or direct Scene 2 test) where Scene 1 did not run in the same session | `tool_context.state.get("active_ticket")` returns `None`. `publish_ticket_to_chat` gracefully falls back to merging `GOLDEN_FALLBACK_K60` + `GOLDEN_FALLBACK_GRID`, constructs a valid `TicketPayload` (`NSN: 5360-99-812-1740`, `51.2185, -1.7925`), POSTs to Cloud Run, logs to BigQuery, and returns the `✅ Ticket TKT-REME-XXXX Published to 4 Bn REME Group Chat` confirmation badge. |
| 9 | SpokenPhonetic/Partial Fault or Grid Queries in Scene 1 | User says `"K60 low oil pressure"` or `"409 Jackal 2 leaking"` or `"Sector Bravo-4"` when Discovery Engine OCR indexing is still warming up or query phrasing varies | `diagnose_and_resolve_grid` uses `LOWER(@query) LIKE CONCAT('%', LOWER(keyword_tag), '%')` in BigQuery and checks `if not nsn_row:` to fall back to `GOLDEN_FALLBACK_JACKAL` (if `"409"` or `"jackal"` in `fault_query.lower()`) or `GOLDEN_FALLBACK_K60`, and `GOLDEN_FALLBACK_GRID` for Sector Bravo-4 (`51.2185, -1.7925`). |
| 10 | Model Selection Rule Reconciliation (`gemini-2.5-flash` vs `gemini-3.8-flash`) | Global rule `gemini-3-8-flash-integration.md` vs `ORIGINAL_REQUEST.md`, `Demo 1 - SA.md`, and `google-agents-cli-workflow` | `gemini-3-8-flash-integration.md` states "When writing Python code to invoke `gemini-3.8-flash` on the Gemini Enterprise Agent Platform...". However, `ORIGINAL_REQUEST.md` (R1, R4), `Demo 1 - SA.md` (§2, §3.1), and `implementation-plan.md` (Phase 4.3) explicitly mandate `model="gemini-2.5-flash"` in `europe-west1`, and `google-agents-cli-workflow` Principle 1 & 2 state: "If the user explicitly names a model, use that model — never substitute it." Therefore, `app/agent.py` MUST use `model="gemini-2.5-flash"` in `europe-west1`. |

---

# 5-Component Handoff Report

## 1. Observation

### 1.1 Project Specifications Read in Full
1. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md` (lines 1–54)**:
   - Mandates an end-to-end build, verification, and deployment of **Demo 1 — REME Light Role Field Artificer (`@REME-Artificer`)** following `docs/architecture/Demo 1 - SA.md` (`SDD-DEMO1-ADK2-003`) and `docs/architecture/implementation-plan.md`.
   - **R1 (Tech Stack & Rules)**: Follow `AGENTS.md`, ADK 2.0 Performance & Latency Guardrails, `discovery-engine-adk-integration` skill, and `google-agents-cli-*` skills. Use `agents-cli` (`scaffold`, `run`, `eval`, `deploy`, `publish`) for the ADK 2.0 project in the workspace root while preserving `docs/` and `AGENTS.md`.
   - **R2 (GCP Target, Residency & Shared Resource Safety)**:
     - Project ID: `antig-dave`
     - Active Account: `admin@edwardsda.altostrat.com` (NEVER `edwardsda@google.com`)
     - Compute / Vertex AI / BigQuery / Cloud Run Region: `europe-west1` (Belgium)
     - Discovery Engine Location: `eu` (`https://eu-discoveryengine.googleapis.com/v1alpha/...`)
     - Gemini Enterprise Engine: `pixel_mobile_demos` (`projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos`)
     - **Non-Destructive Requirement**: Never delete or overwrite pre-existing datastores (`jointservicepubs`), agents, or datasets belonging to other demos in `antig-dave`. When patching `pixel_mobile_demos` `dataStoreIds`, preserve existing datastore IDs alongside `ukd-reme-aesp-ds`.
   - **R3 (Data Layer & Grounding)**:
     - BigQuery dataset `antig-dave.ukd_reme_demo` (`europe-west1`) with 3 tables (`ipc_nsn_catalogue`, `spta_sector_grids`, `group_chat_tickets`), each populated with realistic British Army REME data AND full **table descriptions and column descriptions** on every table and column.
     - Generate two synthetic British Army AESP technical PDFs (`FV432_K60_Engine_AESP.pdf` and `Jackal2_Coyote_Suspension_AESP.pdf`), upload with `metadata.jsonl` to `gs://antig-dave-reme-aesp-eu` (`europe-west1`), ingest into unstructured Discovery Engine datastore `ukd-reme-aesp-ds` (`eu`) with `ocr-parser-1` enabled, and bind `ukd-reme-aesp-ds` to `pixel_mobile_demos`.
   - **R4 (Application & Agent Components)**:
     - Deploy **4 Bn REME Live Group Chat Receiver Web App** (`reme-chat-demonstrator`) to Cloud Run (`europe-west1`, unauthenticated) with tactical military UI, live polling, Google Maps navigation links, and BigQuery persistence.
     - Build `@REME-Artificer` single-agent (`reme_artificer_agent`, `gemini-2.5-flash`, `temperature=0.0`) with two composite tools (`diagnose_and_resolve_grid` and `publish_ticket_to_chat`), pre-warmed client singletons, in-memory cached ADC tokens, single-pass `pageSize: 15` retrieval, snippet-only extraction (`returnSnippet: True`, no `summarySpec`), HTML stripping, and Golden-Path Fallbacks.
     - Deploy to Vertex AI Agent Engine (`agent_runtime`) in `europe-west1` via `agents-cli deploy` (`--min-instances 1`) and publish to `pixel_mobile_demos` (`eu`) via `agents-cli publish gemini`.
   - **R5 (Verification & Definition of Done)**:
     - Unit & integration tests (`pytest`) for tools, schemas, and FastAPI routes passing 100%.
     - `agents-cli run` local smoke test and `agents-cli eval run` evaluation suite passing.
     - Live E2E test of Scene 1 (K60 diagnosis + Sector Bravo-4 grid resolution + Native Structured Markdown Card with 15s Audio Brief & 3 `<details open>` chips) and Scene 2 (Publishing ticket to live Cloud Run Group Chat app & BigQuery `group_chat_tickets`).
     - Browser verification of deployed Cloud Run Group Chat Web App with screenshot confirmation showing the published REME ticket card and clickable Google Maps link (`https://www.google.com/maps/search/?api=1&query={lat},{lng}` or `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving`).

2. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/AGENTS.md` (lines 1–25)**:
   - Lines 3–6 state `Framework: Next.js 14 (App Router)`, `Database: PostgreSQL via Prisma ORM`, `Runtime: Node.js v20`.
   - Line 9 states: `Primary Architecture & Design Reference: [Solutions Architecture Guide](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/docs/architecture/Demo%201%20-%20SA.md)`.
   - Lines 11–14 state: Always import modern `google-genai` (Python) or `@google/genai` (TS/JS) SDKs; never use legacy `google-generativeai`.
   - Lines 16–19 state: Type-safe database operations, explicit error boundaries for all routes, strict types (no `any`).
   - Lines 21–25 state: Run scripts locally in sandbox to test changes, use built-in browser tool to serve/verify UI and take screenshots, and generate companion unit and integration tests.

3. **`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/Demo 1 - SA.md` (lines 1–336) & `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md` (lines 1–328)**:
   - Document ID `SDD-DEMO1-ADK2-003` specifies the complete 7-phase implementation plan and reference Python code for:
     - Phase 1: IAM & Service Account (`sa-reme-demo@antig-dave.iam.gserviceaccount.com`) + Reasoning Engine Service Agent roles.
     - Phase 2: BigQuery dataset `ukd_reme_demo` (`scripts/seed_demo1_bigquery.py`) + PDF generation (`scripts/generate_demo1_pdfs.py`) + Discovery Engine OCR datastore `ukd-reme-aesp-ds` (`scripts/setup_demo1_discovery_engine.py`).
     - Phase 3: Cloud Run Group Chat Receiver (`cloud_run_chat_app/main.py`, `templates/index.html`, `Dockerfile`, `requirements.txt`).
     - Phase 4: ADK 2.0 scaffold (`app/schemas.py`, `app/tools.py`, `app/agent.py`, `app/fast_api_app.py`).
     - Phase 5: Unit tests (`tests/unit/test_tools_and_schemas.py`, `tests/unit/test_chat_app.py`), `agents-cli run` smoke tests, and `agents-cli eval run` (`tests/eval/eval_config.yaml`, `tests/eval/datasets/basic-dataset.json`).
     - Phase 6: `agents-cli deploy` to `europe-west1` and `agents-cli publish gemini` to `pixel_mobile_demos` (`eu`).
     - Phase 7: Live E2E verification and browser UI verification.

4. **7 Domain Skills & Local `agents-cli` v1.12.0 Source Probed**:
   - Read all 7 skills from `/usr/local/google/home/edwardsda/.agents/skills/` (`google-agents-cli-workflow`, `google-agents-cli-scaffold`, `google-agents-cli-adk-code`, `google-agents-cli-eval`, `google-agents-cli-deploy`, `google-agents-cli-publish`, `discovery-engine-adk-integration`) plus their `references/` files (`commands.md`, `flags.md`, `adk-python.md`, `dataset_schema.md`, `metrics-guide.md`, `agent-runtime.md`).
   - Executed `agents-cli info` and `--help` on `run`, `eval run`, `deploy`, and `publish gemini` (`task-29`, exit code 0), and inspected `/usr/local/google/home/edwardsda/.local/share/uv/tools/google-agents-cli/lib/python3.13/site-packages/google/agents/cli/publish/cmd_publish.py`.

---

## 2. Logic Chain

### 2.1 Reconciling `AGENTS.md` with `Demo 1 - SA.md` and `implementation-plan.md`
1. **Observation**: `AGENTS.md` contains template lines referencing Next.js 14 / Prisma / Jest (lines 3–6, 17–19), while simultaneously pointing to `docs/architecture/Demo 1 - SA.md` as the **Primary Architecture & Design Reference** (line 9) and requiring `google-genai` (Python) SDK usage (line 13).
2. **Inference**: The workspace was initialized with a generic repository `AGENTS.md` template before the Solutions Architecture (`Demo 1 - SA.md`, `SDD-DEMO1-ADK2-003`) and `implementation-plan.md` were authored for the Python ADK 2.0 REME Field Artificer system.
3. **Rule Application**:
   - Per `ORIGINAL_REQUEST.md` R1 ("preserving `docs/` and `AGENTS.md`") and `google-agents-cli-workflow` Principle 2 ("Never overwrite existing files when copying template structure"), **do NOT edit or delete `AGENTS.md`**. Pass `--agent-guidance-filename AGENTS.md` to `agents-cli scaffold`.
   - Satisfy every applicable engineering requirement from `AGENTS.md` in Python:
     - **SDK constraint**: Import only `google-genai` (`from google.genai import types`) and `google-adk>=2.0.0` (`from google.adk.agents import LlmAgent`, `from google.adk.tools import ToolContext`); never import legacy `google-generativeai`.
     - **Type-safe DB & strict types**: Use parameterized BigQuery queries (`bigquery.ScalarQueryParameter`) and strict Pydantic v2 models (`ActiveTicketState`, `TicketPayload` in `app/schemas.py`) with complete Python type annotations.
     - **Explicit error boundaries**: Wrap all Discovery Engine REST calls, BigQuery queries/inserts, and HTTP POST calls in `try/except` blocks with deterministic Golden-Path Fallbacks (`GOLDEN_FALLBACK_K60`, `GOLDEN_FALLBACK_JACKAL`, `GOLDEN_FALLBACK_GRID`) and FastAPI exception handling.
     - **Verification playbook**: Run unit and integration tests via `uv run pytest tests/unit/ -v` (`test_tools_and_schemas.py` and `test_chat_app.py` with `fastapi.testclient.TestClient`), and verify the Group Chat web UI using the browser tool with screenshots.

### 2.2 Extracting ADK 2.0 Performance & Latency Guardrails
From `adk-2.0-performance-guardrails.md` and `Demo 1 - SA.md` (§2, §3.3, §5.2):
1. **Pre-Warm Connection Singletons & In-Memory ADC Token Caching (Guardrails 1 & 9)**:
   - In `app/tools.py`, initialize `_BQ_CLIENT = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)` and `_CREDENTIALS, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])` at **module import time**.
   - Implement `_get_access_token() -> str` using `_CREDENTIALS.refresh(_AUTH_REQUEST)` in-memory when `not _CREDENTIALS.valid or _CREDENTIALS.expired`.
   - **NEVER** call `subprocess.check_output(["gcloud", "auth", "print-access-token"])` inside a tool handler (eliminates 1.5–2.0s subprocess overhead per call).
2. **Single-Pass Multi-Document Retrieval (Guardrail 2)**:
   - Set `"pageSize": 15` in the Discovery Engine `:search` payload so all chunks across both AESP manuals are retrieved in a single <0.3s REST call, preventing multi-turn ReAct pagination loops.
3. **Omit Backend `summarySpec` (Guardrail 3)**:
   - Set `"contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}` only. Never request `summarySpec` from Discovery Engine (saves ~3.0s of redundant backend LLM synthesis).
4. **Clean String Formatting & HTML Stripping (Guardrail 4)**:
   - Strip `<b>` and `</b>` tags and collapse whitespace (`re.sub(r"</?b>", "", raw_snippet); re.sub(r"\s+", " ", cleaned).strip()`) before returning snippets to the agent.
5. **Single-Agent Topology & Curated Tool Density (Guardrail 9)**:
   - Use 1 root `LlmAgent` (`reme_artificer_agent`) with exactly 2 composite tools (`diagnose_and_resolve_grid` and `publish_ticket_to_chat`). Do NOT split into sequential sub-agents.
6. **Deterministic Generation Config**:
   - Configure `LlmAgent` with `model="gemini-2.5-flash"`, `generate_content_config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=1024)`.
7. **ADK Function Tool Signature Rules (`google-agents-cli-adk-code`)**:
   - Every tool parameter must have an explicit type annotation (`fault_query: str, spoken_sector_grid: str, tool_context: ToolContext`).
   - Do **not** use default parameter values in tool signatures (ADK schema generator does not support defaults cleanly).
   - Do **not** document `tool_context` in the function docstring (since `tool_context` is injected by ADK and must not be exposed to the LLM as a tool argument).
   - Always return a `dict` from every tool.

### 2.3 Exact `agents-cli` (v1.12.0) Command Syntax, Flags & Gotchas
1. **Scaffold (`scaffold create` & `scaffold enhance`)**:
   - Because `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` already exists and has spaces/capitals in its directory name, run two-step scaffolding:
     ```bash
     agents-cli scaffold create reme-artificer-agent \
       --output-dir /tmp \
       --agent adk \
       --deployment-target agent_runtime \
       --region europe-west1 \
       --agent-guidance-filename AGENTS.md \
       --prototype
     ```
   - Copy `/tmp/reme-artificer-agent/` files into workspace root **without** overwriting `AGENTS.md` or `docs/`, then run:
     ```bash
     agents-cli scaffold enhance . \
       --deployment-target agent_runtime \
       --region europe-west1 \
       --agent-guidance-filename AGENTS.md
     ```
   - Note: Do not pass `--session-type` when `--deployment-target agent_runtime` is used. Ensure `App(name="app", root_agent=root_agent)` in `app/fast_api_app.py` has `name="app"` matching the `app/` package directory.
2. **Local Run (`agents-cli run`)**:
   - Single-turn smoke test:
     ```bash
     GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli run \
       "Cpl MacDonald at Sector Bravo-4. Wait-One, looking at a FV432 K60 engine with low oil pressure—suspect the relief valve spring is fatigued. What are the AESP limits and NSN?" \
       --start-server
     ```
   - Multi-turn Scene 2 test against the warm server using the returned `<SESSION_ID>`:
     ```bash
     GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli run \
       "Publish to Group Chat" \
       --session-id <SESSION_ID>
     ```
   - Stop the local server when finished:
     ```bash
     agents-cli run --stop-server
     ```
3. **Evaluation (`agents-cli eval run`) & Dataset Schema Requirements**:
   - **Dataset Schema (`tests/eval/datasets/basic-dataset.json`)**:
     - Top-level JSON object MUST contain `"eval_cases": [ ... ]`.
     - Each `EvalCase` requires `"eval_case_id": "<str>"` and EITHER `"prompt"` (single-turn input) OR `"agent_data"` (pre-populated or multi-turn trace), never both.
     - Single-turn `prompt` structure:
       ```json
       {
         "eval_case_id": "scene1_k60_diagnosis_bravo4",
         "prompt": {
           "role": "user",
           "parts": [
             {
               "text": "Cpl MacDonald at Sector Bravo-4. Wait-One, looking at a FV432 K60 engine with low oil pressure—suspect the relief valve spring is fatigued. What are the AESP limits and NSN?"
             }
           ]
         },
         "reference": {
           "response": {
             "role": "model",
             "parts": [
               {
                 "text": "### 🛠️ @REME-Artificer — Grounded AESP Diagnostic Card\n🔊 **15s Audio Brief:** AESP 2350-T-250-523 Para 17.4: fatigued K60 oil pressure relief valve spring. Renew if under 79.4mm free length or outside 14.3 to 16.2kg at 54.6mm. Do not pack with washers. NSN 5360-99-812-1740. Coordinates locked at Salisbury Plain (SPTA) — Sector Bravo-4 (51.2185° N, 1.7925° W)."
               }
             ]
           }
         }
       }
       ```
   - **Eval Config Schema (`tests/eval/eval_config.yaml`) & Metric Compatibility Rule**:
     - If `basic-dataset.json` contains **only single-turn `prompt` cases** (e.g., Case 1 = Scene 1 diagnosis; Case 2 = Scene 2 `"Publish to Group Chat"` where `publish_ticket_to_chat` uses its Golden-Path Fallback when `active_ticket` is absent), then `eval_config.yaml` can safely use single-turn managed metrics:
       ```yaml
       dataset_path: tests/eval/datasets/basic-dataset.json
       metrics:
         - final_response_quality
         - tool_use_quality
         - hallucination
         - safety
       ```
     - If `basic-dataset.json` includes any **multi-turn case** (2+ turns in `agent_data.turns`), you MUST NOT include single-turn managed metrics (`final_response_quality`, `tool_use_quality`, `hallucination`, `safety`, `final_response_match`), or Vertex Evaluation Service will fail with `400 FAILED_PRECONDITION: Single-turn metric '<name>_v1' received agent_eval_data with 2 turns, expected 1`. For multi-turn datasets, use `multi_turn_task_success`, `multi_turn_trajectory_quality`, `multi_turn_tool_use_quality`, and/or local `custom_metrics` (`custom_function`).
     - **Command**:
       ```bash
       GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli eval run \
         --config tests/eval/eval_config.yaml \
         --project antig-dave
       ```
     - Note: Do NOT pass `--region europe-west1` to `agents-cli eval run` because Vertex Evaluation Service grading runs in `global` (default) while local trace generation automatically uses `GOOGLE_CLOUD_LOCATION=europe-west1` from `.env`. Always inspect the printed score table and `artifacts/grade_results/results_<timestamp>.json` because `eval run` exits `0` regardless of metric scores.
4. **Deployment (`agents-cli deploy`)**:
   - **Critical v1.12.0 Flag Correction**: `implementation-plan.md` line 251 shows `--no-confirm-project`, which does **not** exist in `agents-cli` v1.12.0 (`task-29` `agents-cli deploy --help`). Use this exact command instead:
     ```bash
     GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli deploy \
       --project antig-dave \
       --region europe-west1 \
       --service-account sa-reme-demo@antig-dave.iam.gserviceaccount.com \
       --min-instances 1 \
       --env-vars "GOOGLE_CLOUD_PROJECT=antig-dave,GCP_PROJECT_ID=antig-dave,GOOGLE_CLOUD_LOCATION=europe-west1,GOOGLE_API_USE_CLIENT_CERTIFICATE=false,BQ_DATASET=ukd_reme_demo,BQ_LOCATION=europe-west1,DISCOVERY_ENGINE_LOCATION=eu,VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds,CLOUD_RUN_CHAT_URL=${CLOUD_RUN_CHAT_URL}"
     ```
   - If the command times out waiting for the 5–10 minute Agent Engine container build, poll with `GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli deploy --status` until `deployment_metadata.json` is written.
   - Verify Agent Registry registration via:
     ```bash
     gcloud agent-registry agents list --project antig-dave --location europe-west1
     ```
5. **Publishing (`agents-cli publish gemini`)**:
   - Read `AGENT_ENGINE_ID=$(jq -r '.remote_agent_engine_id' deployment_metadata.json)` and run:
     ```bash
     GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli publish gemini \
       --agent-runtime-id "${AGENT_ENGINE_ID}" \
       --gemini-enterprise-app-id "projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos" \
       --display-name "REME-Artificer" \
       --description "British Army REME Light Role Field Artificer Assistant — Grounded AESP 2350-T-250-523 & 2320-J-100 Diagnostics, IPC NSN Lookup & 4 Bn REME Group Chat Ticket Dispatch"
     ```
   - Verified in `cmd_publish.py`: `agents-cli publish gemini` automatically parses `locations/eu` from `--gemini-enterprise-app-id`, routes to `https://eu-discoveryengine.googleapis.com/v1alpha`, and performs a non-destructive upsert (`_upsert_agent`) that matches by `reasoningEngine` resource name without touching any other agents on `pixel_mobile_demos`.

### 2.4 Discovery Engine (`eu`) Integration Rules & Shared Engine Safety
From `discovery-engine-adk-integration/SKILL.md`, `Demo 1 - SA.md` (§4.2), and `ORIGINAL_REQUEST.md` (R2, R3):
1. **Unstructured Datastore with Layout/OCR Parser (`ukd-reme-aesp-ds`)**:
   - Create via `POST https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores?dataStoreId=ukd-reme-aesp-ds` with:
     - `"industryVertical": "GENERIC"`
     - `"solutionTypes": ["SOLUTION_TYPE_SEARCH"]`
     - `"contentConfig": "CONTENT_REQUIRED"`
     - `"documentProcessingConfig": {"defaultParsingConfig": {"ocrParsingConfig": {"useNativeText": True}}}`
2. **JSONL Metadata Envelope (`metadata.jsonl`)**:
   - Upload `FV432_K60_Engine_AESP.pdf`, `Jackal2_Coyote_Suspension_AESP.pdf`, and `metadata.jsonl` to `gs://antig-dave-reme-aesp-eu/`.
   - Each line in `metadata.jsonl` uses:
     ```json
     {"id": "doc-aesp-k60", "structData": {"title": "AESP 2350-T-250-523 FV432 K60 Engine Manual", "equipment": "FV432 Powerpack Rolls-Royce K60", "security_classification": "OFFICIAL-SENSITIVE"}, "content": {"mimeType": "application/pdf", "uri": "gs://antig-dave-reme-aesp-eu/FV432_K60_Engine_AESP.pdf"}}
     ```
   - Trigger import via `POST .../dataStores/ukd-reme-aesp-ds/branches/0/documents:import` with `"reconciliationMode": "INCREMENTAL"` and `"gcsSource": {"inputUris": ["gs://antig-dave-reme-aesp-eu/metadata.jsonl"], "dataSchema": "document"}`.
3. **Non-Destructive `pixel_mobile_demos` Datastore Binding**:
   - First `GET https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos` to read existing `dataStoreIds` (which currently contains `["jointservicepubs"]`).
   - Append `"ukd-reme-aesp-ds"` if not already present (`updated_ds = list(dict.fromkeys(existing_ds + ["ukd-reme-aesp-ds"]))`).
   - `PATCH https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel_mobile_demos?updateMask=dataStoreIds` with `{"dataStoreIds": updated_ds}`.
4. **Prohibition on Destructive Agent Purge**:
   - Do **NOT** execute the generic `for AGENT_NAME in $AGENTS; do curl -X DELETE ...` snippet from Section 3 of `discovery-engine-adk-integration/SKILL.md` on `pixel_mobile_demos`, as `pixel_mobile_demos` is a shared engine in `antig-dave`. Use `agents-cli publish gemini` (which safely upserts by Reasoning Engine ID).

---

## 3. Caveats

1. **Google Maps URL Format**: `Demo 1 - SA.md` (§5.2) and `implementation-plan.md` (line 138) generate `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving`, whereas `ORIGINAL_REQUEST.md` R5 accepts either `https://www.google.com/maps/search/?api=1&query={lat},{lng}` or the `maps/dir` URL. Using `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving` (or checking for `https://www.google.com/maps/` in tests) satisfies both `Demo 1 - SA.md` and `ORIGINAL_REQUEST.md`.
2. **Discovery Engine OCR Indexing Delay**: Initial OCR ingestion of the two PDFs into `ukd-reme-aesp-ds` can take several minutes to finish background indexing. The Golden-Path Fallbacks in `diagnose_and_resolve_grid` (`GOLDEN_FALLBACK_K60`, `GOLDEN_FALLBACK_JACKAL`, `GOLDEN_FALLBACK_GRID`) ensure deterministic sub-second responses even while indexing completes.

---

## 4. Conclusion

All architectural specifications, ADK 2.0 performance guardrails, `agents-cli` v1.12.0 command/flag contracts, evaluation dataset schemas, Discovery Engine (`eu`) integration patterns, and `AGENTS.md` reconciliation rules have been extracted and verified against the authoritative documents and installed CLI tooling. The implementation phases can proceed directly using the exact commands, schemas, and guardrails documented in this report.

---

## 5. Verification Method

To independently verify the findings in this report:
1. **Verify `agents-cli` v1.12.0 flags and `publish gemini` implementation**:
   ```bash
   agents-cli info
   agents-cli deploy --help
   agents-cli publish gemini --help
   agents-cli eval run --help
   ```
2. **Verify architecture & plan specifications**:
   - Inspect `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/Demo 1 - SA.md` and `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md`.
   - Inspect `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/ORIGINAL_REQUEST.md`.
3. **Invalidation Conditions**:
   - Upgrading `google-agents-cli` from `1.12.0` to a newer version could introduce new CLI flags.
   - Changes to `ORIGINAL_REQUEST.md` or `Demo 1 - SA.md` would supersede these findings.
