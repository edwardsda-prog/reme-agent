# BRIEFING — 2026-10-29T11:12:15Z

## Mission
Perform Phase 0 Survey (Specification Mining Part 2): Extract all architectural requirements, ADK 2.0 performance guardrails, exact `agents-cli` command syntax/flags, eval dataset schemas, and Discovery Engine integration rules from `Demo 1 - SA.md`, `AGENTS.md`, and the 7 ADK / `agents-cli` skills.

## 🔒 My Identity
- Archetype: `teamwork_spec_miner`
- Roles: Specification Miner, External Domain Expert
- Working directory: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/`
- Original parent: `6f912669-38e4-4574-904f-704d623a5d01`
- Milestone: Phase 0 Survey (Specification Mining Part 2 — Architecture, Guardrails & CLI Skills)

## 🔒 Key Constraints
- Read-only specification investigation. Do NOT create or modify any project source code or cloud resources.
- Write all coordination/report files ONLY to `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/`.
- Never copy a skill file listed in the system prompt; read from its listed path.

## Current Parent
- Conversation ID: `6f912669-38e4-4574-904f-704d623a5d01`
- Updated: 2026-10-29T11:12:15Z

## Task Summary
- **What to build**: Comprehensive specification mining report (`handoff.md`) covering architecture (`Demo 1 - SA.md`), `AGENTS.md` reconciliation, ADK 2.0 performance guardrails, `agents-cli` commands/flags/schemas, eval dataset schemas, and Discovery Engine integration rules.
- **Success criteria**: Complete feature & edge-case tables and 5-component handoff report in `handoff.md`.
- **Interface contracts**: `ORIGINAL_REQUEST.md`, `docs/architecture/Demo 1 - SA.md`, `docs/architecture/implementation-plan.md`, `AGENTS.md`
- **Code layout**: `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`

## Loaded Skills
- **google-agents-cli-workflow**:
  - Source: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-workflow/SKILL.md`
  - Local copy: N/A (system prompt skill — read directly from listed path)
  - Core methodology: ADK development lifecycle (scaffold, build, evaluate, deploy, publish, observe) and coding guidelines.
- **google-agents-cli-scaffold**:
  - Source: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-scaffold/SKILL.md`
  - Local copy: N/A (system prompt skill — read directly from listed path)
  - Core methodology: `agents-cli scaffold create/enhance/upgrade` commands, templates, and deployment targets.
- **google-agents-cli-adk-code**:
  - Source: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-adk-code/SKILL.md`
  - Local copy: N/A (system prompt skill — read directly from listed path)
  - Core methodology: ADK API patterns, agent types, tool definitions, callbacks, and state management.
- **google-agents-cli-eval**:
  - Source: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-eval/SKILL.md`
  - Local copy: N/A (system prompt skill — read directly from listed path)
  - Core methodology: `agents-cli eval` dataset schema, metrics, LLM-as-judge scoring, and execution.
- **google-agents-cli-deploy**:
  - Source: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-deploy/SKILL.md`
  - Local copy: N/A (system prompt skill — read directly from listed path)
  - Core methodology: `agents-cli deploy` workflows, Agent Runtime / Cloud Run targets, service accounts, and flags.
- **google-agents-cli-publish**:
  - Source: `/usr/local/google/home/edwardsda/.agents/skills/google-agents-cli-publish/SKILL.md`
  - Local copy: N/A (system prompt skill — read directly from listed path)
  - Core methodology: `agents-cli publish gemini` registration modes, flags, and Agent Registry fleet management.
- **discovery-engine-adk-integration**:
  - Source: `/usr/local/google/home/edwardsda/.agents/skills/discovery-engine-adk-integration/SKILL.md`
  - Local copy: N/A (system prompt skill — read directly from listed path)
  - Core methodology: Discovery Engine unstructured OCR datastores, JSONL metadata ingestion, Gemini Enterprise engine patching, and ADK 2.0 integration.

## Key Decisions Made
- Read all primary documents (`Demo 1 - SA.md`, `AGENTS.md`, `implementation-plan.md`, `ORIGINAL_REQUEST.md`) and all 7 skill files to produce an exhaustive, verified specification inventory.
- Reconciled `AGENTS.md` (legacy Next.js/Prisma boilerplate vs. `Demo 1 - SA.md` primary reference): preserve `AGENTS.md` untouched on disk while implementing the 100% Python ADK 2.0 + FastAPI + BigQuery + Discovery Engine stack and enforcing `AGENTS.md` rules (`google-genai` SDK, explicit error boundaries, strict Pydantic v2 types, `pytest` unit/integration tests, browser UI verification).
- Identified critical `agents-cli` v1.12.0 flag and schema rules: `--no-confirm-project` is removed in v1.12.0 (use `--project antig-dave`), `scaffold create` must run in `/tmp` due to directory name constraints, `eval` single-turn vs multi-turn metric constraints, and `publish gemini` safely auto-detects `eu` and upserts without deleting shared agents on `pixel_mobile_demos`.

## Artifact Index
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/DISPATCH.md` — Dispatch assignment log
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/BRIEFING.md` — Persistent working memory
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/progress.md` — Liveness heartbeat and step tracker
- `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/.agents/teamwork/teamwork_spec_miner_survey_2/handoff.md` — Final specification mining report (complete)
