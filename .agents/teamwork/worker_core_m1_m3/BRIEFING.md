# BRIEFING — 2026-10-29T11:44:30Z

## Mission
Implement Milestones M1 and M3 (and M4 configs): Root `agents-cli` ADK 2.0 Scaffolding, Environment Config, `app/*`, `cloud_run_chat_app/*`, Unit Tests `tests/unit/*`, Eval Config `tests/eval/*`, and Deployment Script `scripts/deploy_demo.sh`.

## 🔒 My Identity
- Archetype: teamwork_worker (`worker_core_m1_m3`)
- Roles: implementer, qa, specialist
- Working directory: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_core_m1_m3/`
- Original parent: `6f912669-38e4-4574-904f-704d623a5d01`
- Milestone: M1 & M3 (plus M4 configs `tests/eval/*` & `scripts/deploy_demo.sh`)

## 🔒 Key Constraints
- DO NOT CHEAT. All implementations must be genuine.
- Do NOT modify `AGENTS.md`, `PROJECT.md`, or `docs/`.
- Do NOT write to `scripts/setup_reme_datastore.py`, `scripts/seed_demo1_bigquery.py`, `TEST_INFRA.md`, `TEST_READY.md`, or `tests/e2e/` (owned by parallel agents).
- Always set `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` and use `admin@edwardsda.altostrat.com` (NEVER `edwardsda@google.com`).
- Pre-warm `_BQ_CLIENT` and `_CREDENTIALS` at module import time in `app/tools.py` with zero `gcloud` subprocess calls.
- Filter `TicketPayload` to exact 13 table columns when inserting into `ukd_reme_demo.group_chat_tickets` so `sector_display_name` does not cause a BigQuery unknown field error.

## Current Parent
- Conversation ID: `6f912669-38e4-4574-904f-704d623a5d01`
- Updated: 2026-10-29T11:44:30Z

## Task Summary
- **What to build**: Root ADK 2.0 scaffold (`SPEC.md`, `.env`, `.env.example`, `pyproject.toml`, `Dockerfile`, `.agents.yaml`, `agents-cli-manifest.yaml`), `app/` (`schemas.py`, `tools.py`, `agent.py`, `fast_api_app.py`, `__init__.py`), `cloud_run_chat_app/` (`main.py`, `templates/index.html`, `Dockerfile`, `requirements.txt`), `tests/unit/` (`test_tools.py`, `test_chat_api.py`), `tests/eval/` (`eval_config.yaml`, `datasets/basic-dataset.json`), and `scripts/deploy_demo.sh`.
- **Success criteria**: `agents-cli info` succeeds cleanly; `uv sync` succeeds; `uv run pytest tests/unit/ -v` passes 100% of unit and FastAPI integration tests.
- **Interface contracts**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md`
- **Code layout**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/PROJECT.md` § Code Layout

## Key Decisions Made
- Scaffold in `/tmp/reme-scaffold` first, then selectively copy to workspace root to preserve `AGENTS.md`, `PROJECT.md`, `docs/`, and `.agents/`.
- Use module-level pre-warmed `_BQ_CLIENT` and `_CREDENTIALS` singletons in `app/tools.py` with graceful fallback if ADC/BQ is mocked or offline during unit tests.
- Filter BigQuery `group_chat_tickets` inserts strictly to the 13 table columns (`BQ_TICKET_COLUMNS`) while retaining `sector_display_name` in `TicketPayload` for the Cloud Run UI and agent response.
- Keep `google-adk[gcp,otel-gcp,bigquery-analytics]>=2.12.0,<3.0.0` and `a2a-sdk[http-server]>=1.0,<2` in `pyproject.toml` so `app/fast_api_app.py` and `app/app_utils/a2a.py` (`a2a.server.routes`) import cleanly for `agents-cli deploy` and `agents-cli eval`.

## Change Tracker
- **Files modified**:
  - `SPEC.md`, `.env`, `.env.example`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `.agents.yaml`, `agents-cli-manifest.yaml`
  - `app/__init__.py`, `app/schemas.py`, `app/tools.py`, `app/agent.py`, `app/fast_api_app.py`, `app/app_utils/*`
  - `cloud_run_chat_app/main.py`, `cloud_run_chat_app/templates/index.html`, `cloud_run_chat_app/Dockerfile`, `cloud_run_chat_app/requirements.txt`
  - `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/test_tools.py`, `tests/unit/test_chat_api.py`
  - `tests/eval/eval_config.yaml`, `tests/eval/datasets/basic-dataset.json`
  - `scripts/deploy_demo.sh`
- **Build status**: Passing (`uv sync`, `agents-cli info`, `pytest tests/unit/ -v`)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 8/8 unit & FastAPI integration tests passing in `tests/unit/`
- **Lint status**: Clean
- **Tests added/modified**: `tests/unit/test_tools.py` (7 tests), `tests/unit/test_chat_api.py` (full lifecycle test)

## Loaded Skills
- **Source**: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-scaffold/SKILL.md` — Two-step ADK scaffolding (`scaffold create` in `/tmp` + `scaffold enhance`)
- **Source**: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-adk-code/SKILL.md` — ADK 2.0 `LlmAgent`, `ToolContext`, function tool signature rules
- **Source**: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-eval/SKILL.md` — `eval_config.yaml` and `basic-dataset.json` schema and metric rules
- **Source**: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-deploy/SKILL.md` — `agents-cli deploy` flags for `agent_runtime`
- **Source**: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-publish/SKILL.md` — `agents-cli publish gemini` non-destructive registration

## Artifact Index
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_core_m1_m3/DISPATCH.md` — Dispatch instructions
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_core_m1_m3/progress.md` — Liveness heartbeat & progress log
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/worker_core_m1_m3/handoff.md` — 5-Component Handoff Report
