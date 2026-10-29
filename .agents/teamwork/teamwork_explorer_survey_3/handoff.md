# Phase 0 Survey Handoff Report — `teamwork_explorer_survey_3`

**Core Summary:** The `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` workspace is greenfield (containing only `AGENTS.md` and `docs/architecture/{Demo 1 - SA.md, implementation-plan.md}`), all required CLI tools (`agents-cli 1.12.0`, `uv 0.12.17`, `python3 3.13.15`, `gcloud 591.0.0`) are installed, `gs://remedata/2350-T-250-523.pdf` (`6.19 MiB`) is staged in GCS, and none of the Demo 1 REME cloud targets (`sa-reme-demo`, BigQuery `ukd_reme_demo`, Discovery Engine `ukd-reme-aesp-ds`, Cloud Run `reme-chat-demonstrator`, or REME Reasoning Engine) exist yet. **Critical Discovery Engine Finding:** In `location=eu`, the engine with `displayName: "pixel_mobile_demos"` has actual resource ID `pixel-mobile-demos_1793177711952` (querying `/engines/pixel_mobile_demos` returns HTTP 404) and its existing datastore with `displayName: "jointservicepubs"` has actual resource ID `jointservicepubs_1793177321711`.

---

## 1. Observation

### 1.1 Local Workspace & Git State (`/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`)
- **Directory Listing (`ls -la` & `find`)**:
  ```text
  drwxr-xr-x  4 edwardsda primarygroup 4096 Oct 29 10:56 .
  drwxr-xr-x  3 edwardsda primarygroup 4096 Oct 29 10:56 .agents
  -rw-r--r--  1 edwardsda primarygroup 1590 Oct 29 10:23 AGENTS.md
  drwxr-xr-x  3 edwardsda primarygroup 4096 Oct 29 10:19 docs
  ```
- **Files Present**:
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/AGENTS.md` (25 lines, 1,590 bytes — currently contains template Next.js 14 / Prisma guidelines plus a reference to `docs/architecture/Demo 1 - SA.md` and `@google/genai`/`google-genai` SDK constraints).
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/Demo 1 - SA.md` (335 lines, 32,221 bytes).
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme/docs/architecture/implementation-plan.md` (327 lines, 28,667 bytes).
  - No `app/`, `cloud_run_chat_app/`, `scripts/`, `tests/`, `pyproject.toml`, `Dockerfile`, `agents-cli-manifest.yaml`, `.env`, or `.env.example` exist yet.
- **Git Repository Boundary (`git rev-parse --show-toplevel`)**:
  - `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` does **not** have its own `.git` directory.
  - `git -C "/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme" rev-parse --show-toplevel` returns `/usr/local/google/home/edwardsda` (on branch `main`, commit `78d8d03`).

### 1.2 Installed CLI Tooling & Versions
| Tool | Binary Path | Verbatim Version Output |
|---|---|---|
| `agents-cli` | `/usr/local/google/home/edwardsda/.local/bin/agents-cli` | `agents-cli, version 1.12.0` |
| `uv` | `/usr/local/google/home/edwardsda/.local/bin/uv` | `uv 0.12.17 (x86_64-unknown-linux-gnu)` |
| `python3` | `/usr/bin/python3` | `Python 3.13.15` |
| `gcloud` | `/usr/bin/gcloud` | `Google Cloud SDK 591.0.0` (`bq 2.1.41`, `gsutil 5.38`, `alpha/beta 2026.10.26`) |

### 1.3 GCP Authentication, Configuration & ADC State
- **`gcloud auth list`**:
  ```text
        Credentialed Accounts
  ACTIVE  ACCOUNT
  *       admin@edwardsda.altostrat.com
          edwardsda@google.com
          insecure-cloudtop-shared-user@cloudtop-prod-europe-west.iam.gserviceaccount.com
  ```
- **`gcloud config list`**:
  ```text
  [billing]
  quota_project = antig-dave
  [container]
  use_application_default_credentials = true
  [context_aware]
  certificate_config_file_path = /etc/gcloud/certificate_config.json
  use_client_certificate = true
  use_ecp_http_proxy = true
  use_mtls_for_grpc = true
  [core]
  account = admin@edwardsda.altostrat.com
  custom_ca_certs_file = /etc/ssl/certs/ca-certificates.crt
  disable_usage_reporting = True
  project = antig-dave
  universe_domain = googleapis.com
  ```
  - Project ID: `antig-dave` | Project Number: `284046449012`.
- **Python Application Default Credentials (`google.auth.default()`)**:
  ```text
  ADC type: Credentials project: antig-dave quota_project: None service_account_email: None
  ```
  *(Emits `UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK without a quota project` when `quota_project_id` is not explicitly set on ADC or via `X-Goog-User-Project: antig-dave` header).*

### 1.4 Cloud Storage (`gs://remedata`)
- **Command**: `GOOGLE_API_USE_CLIENT_CERTIFICATE=false gcloud storage ls -l gs://remedata/ --account=admin@edwardsda.altostrat.com --project=antig-dave`
- **Output**:
  ```text
     6490826  2026-10-29T10:42:03Z  gs://remedata/2350-T-250-523.pdf
  TOTAL: 1 objects, 6490826 bytes (6.19MiB)
  ```
- `gs://remedata/2350-T-250-523.pdf` is present (`6,490,826` bytes). `gs://remedata/documents.jsonl` does not exist yet.

### 1.5 IAM Service Accounts (`antig-dave`)
- **Command**: `GOOGLE_API_USE_CLIENT_CERTIFICATE=false gcloud iam service-accounts list --account=admin@edwardsda.altostrat.com --project=antig-dave`
- **Output**:
  ```text
  DISPLAY NAME                                       EMAIL                                                       DISABLED
  Service Account for Royal Navy Notebook Cloud Run  rn-notebook-runner-sa@antig-dave.iam.gserviceaccount.com    False
  Event Portal Service Account                       event-portal-sa@antig-dave.iam.gserviceaccount.com          False
  Military OCR Cloud Run Execution Service Account   military-ocr-runner-sa@antig-dave.iam.gserviceaccount.com   False
  firebase-adminsdk                                  firebase-adminsdk-fbsvc@antig-dave.iam.gserviceaccount.com  False
  Compute Engine default service account             284046449012-compute@developer.gserviceaccount.com          False
  Antigravity Deployer                               antigravity-deployer@antig-dave.iam.gserviceaccount.com     False
  ```
- **`sa-reme-demo@antig-dave.iam.gserviceaccount.com` does NOT exist yet.**

### 1.6 BigQuery (`ukd_reme_demo` in `europe-west1`)
- **Command**: `GOOGLE_API_USE_CLIENT_CERTIFICATE=false bq --location=europe-west1 --project_id=antig-dave ls` and `bq --project_id=antig-dave show --format=prettyjson antig-dave:ukd_reme_demo`
- **Output**:
  ```text
           datasetId          
   -------------------------- 
    edge_wing_forge_cortex    
    edgewing                  
    mission_data              
    model_armor_logs          
    system_logs               
    tri_service_mission_data  
    ukd_welfare_demo          
  BigQuery error in show operation: Not found: Dataset antig-dave:ukd_reme_demo
  ```
- **Dataset `antig-dave:ukd_reme_demo` does NOT exist yet.**

### 1.7 Discovery Engine (`eu` Multi-Region: `https://eu-discoveryengine.googleapis.com/v1alpha/...`)
- **DataStores in `eu` (`GET .../locations/eu/collections/default_collection/dataStores`)**:
  - `ukd-reme-aesp-ds` does **NOT** exist yet.
  - Only one datastore exists in `eu`:
    ```json
    {
      "name": "projects/284046449012/locations/eu/collections/default_collection/dataStores/jointservicepubs_1793177321711",
      "displayName": "jointservicepubs",
      "industryVertical": "GENERIC",
      "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
      "contentConfig": "CONTENT_REQUIRED"
    }
    ```
- **Engines in `eu` (`GET .../locations/eu/collections/default_collection/engines`)**:
  - Querying `.../engines/pixel_mobile_demos` directly returns `HTTP 404 NOT_FOUND` (`Engine with name "projects/284046449012/locations/eu/collections/default_collection/engines/pixel_mobile_demos" does not exist.`).
  - Listing all engines in `eu` reveals the actual engine resource ID is **`pixel-mobile-demos_1793177711952`** (with `displayName: "pixel_mobile_demos"`):
    ```json
    {
      "name": "projects/284046449012/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952",
      "displayName": "pixel_mobile_demos",
      "dataStoreIds": [
        "jointservicepubs_1793177321711"
      ],
      "solutionType": "SOLUTION_TYPE_SEARCH",
      "appType": "APP_TYPE_INTRANET",
      "associatedAgentRegistry": "//agentregistry.googleapis.com/projects/antig-dave/locations/europe-west1"
    }
    ```
- **Agents Currently Attached to `pixel-mobile-demos_1793177711952` (`GET .../engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents`)**:
  1. `projects/284046449012/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents/13073824185441632570`
     - `displayName`: `"British Army - Soldier Self-Service & Welfare Safeguarding Agent"`
     - `state`: `"ENABLED"`
     - `provisionedReasoningEngine`: `"projects/284046449012/locations/europe-west1/reasoningEngines/1537628528537763840"`
  2. `projects/284046449012/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents/deep_research`
     - `displayName`: `"Deep Research"`
     - `state`: `"ENABLED"`

### 1.8 Cloud Run, Vertex AI Reasoning Engines & Agent Registry (`europe-west1`)
- **Cloud Run (`gcloud run services list --region=europe-west1 --project=antig-dave`)**:
  - `reme-chat-demonstrator` does **NOT** exist yet.
  - Only `welfare-chat-app` (`https://welfare-chat-app-284046449012.europe-west1.run.app`) is currently deployed in `europe-west1`.
- **Vertex AI Reasoning Engines (`GET https://europe-west1-aiplatform.googleapis.com/v1beta1/projects/antig-dave/locations/europe-west1/reasoningEngines`)**:
  - No REME reasoning engine exists yet.
  - Only `projects/284046449012/locations/europe-west1/reasoningEngines/1537628528537763840` (`displayName: "demo4-welfare-self-service"`, `agentFramework: "google-adk"`) exists in `europe-west1`.
  - Notably, `demo4-welfare-self-service`'s `deploymentSpec.env` uses:
    - `AGENT_SEARCH_DATASTORE_ID = "jointservicepubs_1793177321711"`
    - `AGENT_SEARCH_ENGINE_ID = "pixel-mobile-demos_1793177711952"`
    - `AGENT_SEARCH_LOCATION = "eu"`
- **Agent Registry (`gcloud agent-registry agents list --location=europe-west1 --project=antig-dave`)**:
  - 2 agents currently listed:
    1. `Workspace Agent` (`agentregistry-00000000-0000-0000-630f-070a9d06e171`, `location: global`)
    2. `demo4-welfare-self-service` (`agentregistry-00000000-0000-0000-a2e9-e0fb8989a29e`, `location: europe-west1`)

---

## 2. Logic Chain

1. **Greenfield Workspace Verification (from Observation 1.1)**: Because `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` only contains `AGENTS.md`, `docs/`, and `.agents/`, Phase 1 scaffolding (`agents-cli` layout, `pyproject.toml`, `app/`, `cloud_run_chat_app/`, `scripts/`, `tests/`) can proceed cleanly without file collisions, provided `AGENTS.md` and `docs/` are preserved.
2. **Git Repository Top-Level Caution (from Observation 1.1)**: Because `Demo 1 - Reme` has no `.git` directory and inherits `/usr/local/google/home/edwardsda` as its parent git repository, running `git` commands or creating git worktrees without awareness of `/usr/local/google/home/edwardsda` would operate on the user's home directory repo.
3. **Mandatory `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` (from Observation 1.3)**: `gcloud config list` shows `context_aware.use_client_certificate = true` and `use_mtls_for_grpc = true`. This directly explains why `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` must be exported in the shell and `.env` for all `gcloud`, `bq`, and Python SDK calls.
4. **Greenfield Demo 1 Cloud Resources (from Observations 1.4, 1.5, 1.6, 1.8)**:
   - Source PDF `gs://remedata/2350-T-250-523.pdf` is already present in GCS (`6,490,826` bytes).
   - `sa-reme-demo@antig-dave.iam.gserviceaccount.com` must be created and bound to IAM roles before deployment.
   - `ukd_reme_demo` BigQuery dataset (`europe-west1`), `ukd-reme-aesp-ds` datastore (`eu`), `reme-chat-demonstrator` Cloud Run service (`europe-west1`), and `reme_artificer_agent` Reasoning Engine (`europe-west1`) will all be net-new creations.
5. **Critical Discovery Engine Resource ID Resolution (from Observation 1.7 & 1.8)**:
   - The Gemini Enterprise engine whose `displayName` is `"pixel_mobile_demos"` has the actual Discovery Engine `engineId` **`pixel-mobile-demos_1793177711952`**.
   - Its pre-existing datastore whose `displayName` is `"jointservicepubs"` has the actual `dataStoreId` **`jointservicepubs_1793177321711`**.
   - Therefore, in `scripts/setup_reme_datastore.py`, attempting to `GET` or `PATCH` `.../engines/pixel_mobile_demos` directly will fail with `404 NOT_FOUND`, and hardcoding `dataStoreIds: ["jointservicepubs", "ukd-reme-aesp-ds"]` would fail or drop `jointservicepubs_1793177321711`.
   - Instead, `scripts/setup_reme_datastore.py` should resolve the engine dynamically (by checking `pixel_mobile_demos` and falling back to listing engines where `displayName == "pixel_mobile_demos"` or ID `pixel-mobile-demos_1793177711952`), read the engine's existing `dataStoreIds` list (`["jointservicepubs_1793177321711"]`), and append `"ukd-reme-aesp-ds"` if not already present (resulting in `["jointservicepubs_1793177321711", "ukd-reme-aesp-ds"]`).
   - Likewise, when publishing the agent in Phase 8 (`agents-cli publish gemini` or Discovery Engine REST API), `--engine-id` / target engine must reference `pixel-mobile-demos_1793177711952` (or handle both display name and engine ID), and must preserve the 2 existing enabled agents (`13073824185441632570` `"British Army - Soldier Self-Service & Welfare Safeguarding Agent"` and `deep_research`).

---

## 3. Caveats

- No caveats. All items in the Phase 0 dispatch were directly inspected and verified via read-only commands.

---

## 4. Conclusion

The environment and workspace are ready for Phase 1–8 execution with the following actionable checklist for downstream agents:

1. **Workspace & Git**: Scaffold the ADK 2.0 project in `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme` preserving `AGENTS.md` and `docs/`. Note that `.git` is at `/usr/local/google/home/edwardsda` unless `git init` is initialized locally inside `/usr/local/google/home/edwardsda/Documents/Demo 1 - Reme`.
2. **Service Account Creation Needed**: `sa-reme-demo@antig-dave.iam.gserviceaccount.com` does not exist yet and must be created and granted IAM roles in `antig-dave`.
3. **GCS & Discovery Engine (`eu`)**:
   - `gs://remedata/2350-T-250-523.pdf` (`6.19 MiB`) is ready. Generate and upload `gs://remedata/documents.jsonl` and create datastore `ukd-reme-aesp-ds` in `location=eu`.
   - When patching the `pixel_mobile_demos` engine in `eu`, target engine ID **`pixel-mobile-demos_1793177711952`** (resolve dynamically from `GET .../engines` by `displayName == "pixel_mobile_demos"` or ID `pixel-mobile-demos_1793177711952`), and **read-modify-write** `dataStoreIds` so the existing `"jointservicepubs_1793177321711"` entry is preserved alongside `"ukd-reme-aesp-ds"`.
   - When calling Discovery Engine REST APIs using user credentials or ADC, include header `"X-Goog-User-Project": "antig-dave"`.
4. **BigQuery (`europe-west1`)**: Dataset `antig-dave.ukd_reme_demo` does not exist yet and is ready to be created and seeded in `europe-west1` by `scripts/seed_demo1_bigquery.py`.
5. **Cloud Run, Agent Engine & Agent Publishing (`europe-west1` / `eu`)**:
   - Deploy `reme-chat-demonstrator` to Cloud Run (`europe-west1`) without touching `welfare-chat-app`.
   - Deploy `reme_artificer_agent` to Vertex AI Agent Engine (`europe-west1`) without touching `demo4-welfare-self-service` (`1537628528537763840`).
   - Publish `"REME-Artificer"` to engine `pixel-mobile-demos_1793177711952` (`displayName: "pixel_mobile_demos"`) while keeping existing agents `13073824185441632570` (`British Army - Soldier Self-Service & Welfare Safeguarding Agent`) and `deep_research` intact.

---

## 5. Verification Method

Any agent can independently verify these findings using the following read-only commands:

```bash
export GOOGLE_API_USE_CLIENT_CERTIFICATE=false

# 1. Verify active account, project, and GCS PDF
gcloud auth list
gcloud storage ls -l gs://remedata/ --account=admin@edwardsda.altostrat.com --project=antig-dave

# 2. Verify IAM service accounts and BigQuery datasets
gcloud iam service-accounts list --account=admin@edwardsda.altostrat.com --project=antig-dave
bq --location=europe-west1 --project_id=antig-dave ls

# 3. Verify Discovery Engine datastores, engine ID, and attached agents in eu
TOKEN=$(gcloud auth print-access-token --account=admin@edwardsda.altostrat.com)
curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: antig-dave" \
  "https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/dataStores" | python3 -m json.tool
curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: antig-dave" \
  "https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines" | python3 -m json.tool
curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: antig-dave" \
  "https://eu-discoveryengine.googleapis.com/v1alpha/projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952/assistants/default_assistant/agents" | python3 -m json.tool

# 4. Verify Cloud Run, Reasoning Engines, and Agent Registry in europe-west1
gcloud run services list --region=europe-west1 --project=antig-dave --account=admin@edwardsda.altostrat.com
gcloud agent-registry agents list --location=europe-west1 --project=antig-dave --account=admin@edwardsda.altostrat.com
```
