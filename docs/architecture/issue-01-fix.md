# Issue Fix: Data Store Import and Indexing

## Current Symptoms
- **Observed Behavior:** Data Store Imported with Issues (`failureCount: "1"` on operation `import-documents-3049921257174640810` and `import-documents-837954655152656941`).
- **Error Query for Cloud Logs:**
```text
jsonPayload.importPayload.operation="projects/284046449012/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/branches/0/operations/import-documents-3049921257174640810"
resource.labels.service="discoveryengine.googleapis.com"
```
- **Live LRO Error Payload (`code: 14` / `UNAVAILABLE`):**
```json
{
  "code": 14,
  "message": "Document(\"name\": \"projects/284046449012/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/branches/0/documents/aesp-2350-t-250-523\", \"content_uri\": \"gs://remedata/2350-T-250-523.pdf\", \"mime_type\": \"application/pdf\") was previously imported but not yet indexed. Document segmentation has finished. Document indexing is working in progress. Resource is temporarily exhausted. Processing will be retried later when resource is available.",
  "details": [
    {
      "@type": "type.googleapis.com/google.rpc.ResourceInfo",
      "resourceName": "gs://remedata/documents.jsonl:1"
    }
  ]
}
```

- **Reproduction Steps:**
  1. Run `uv run python scripts/setup_reme_datastore.py` when `ukd-reme-aesp-ds` is configured with `ocrParsingConfig.useNativeText = True` on the 139-page (6.49 MB) `gs://remedata/2350-T-250-523.pdf` in the `eu` multi-region (`import-documents-9833928226501887993` started at `11:57:02Z` and took ~68 minutes due to `eu` Document AI OCR quota/resource limits).
  2. Because `import_documents()` in `scripts/setup_reme_datastore.py` defaulted to `poll_timeout_seconds=30` (`raise_on_timeout=False`) and did not check for active in-flight LROs on `branches/0/operations`, re-running `scripts/setup_reme_datastore.py` (at `11:57:42Z` and `12:07:11Z`) fired overlapping `documents:import` operations (`import-documents-837954655152656941` and `import-documents-3049921257174640810`) for the same document (`aesp-2350-t-250-523`) while segmentation/indexing was still in progress, causing Discovery Engine to reject the duplicate imports with `code: 14` (`failureCount: "1"`) and marking the datastore as **"Data Store Imported with Issues"**.

## Expected Behavior
- Fully Indexed and Searchable: Vertex AI Search and Conversation Datastore (`ukd-reme-aesp-ds` in `eu`) completes its latest `documents:import` operation in `<60 seconds` with `failureCount == 0`, `successCount >= 1`, and live `servingConfigs/default_search:search` returning grounded AESP 2350-T-250-523 snippets (`79.4 mm`, `54.6 mm`, `5360-99-812-1740`, `409`).

## Root Cause Analysis
1. **Heavy `eu` Document AI OCR Parsing on a 139-Page PDF (`scripts/setup_reme_datastore.py:255-261`):**
   - `create_datastore()` initialized `ukd-reme-aesp-ds` with `ocrParsingConfig: {"useNativeText": True}` and did not update `documentProcessingConfig` to `digitalParsingConfig` when the datastore already existed (`HTTP 409`). In `eu`, OCR parsing of `gs://remedata/2350-T-250-523.pdf` takes ~68 minutes and exhausts regional OCR resources (`code: 14: Resource is temporarily exhausted`).
2. **Missing Active-LRO Concurrency Guard & Silent `failureCount` Ignore (`scripts/setup_reme_datastore.py:278-326`):**
   - `import_documents()` unconditionally POSTed a new `/branches/0/documents:import` request without checking `GET /branches/0/operations` for an already-running `import-documents-*` LRO.
   - `import_documents()` only checked for a top-level `"error"` key on the LRO response, ignoring `metadata.failureCount` and `response.errorSamples` (which is how Discovery Engine reports per-document `code: 14` import failures when `done: true`).

## Target Files
- [scripts/setup_reme_datastore.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/scripts/setup_reme_datastore.py)
- [tests/e2e/test_tier1_features.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/e2e/test_tier1_features.py)
- [tests/e2e/test_tier2_boundaries.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/e2e/test_tier2_boundaries.py)
- [tests/e2e/test_tier4_scenarios.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/e2e/test_tier4_scenarios.py)
- [docs/architecture/issue-01-fix.md](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/docs/architecture/issue-01-fix.md)

## File-by-File Fix Plan
1. **[scripts/setup_reme_datastore.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/scripts/setup_reme_datastore.py)**:
   - **Never delete `ukd-reme-aesp-ds`**: Preserve the existing datastore in `eu`.
   - **Patch `documentProcessingConfig` to `digitalParsingConfig`**: Add `patch_datastore_processing_config()` to `PATCH` the singleton resource `ukd-reme-aesp-ds/documentProcessingConfig` with `{"name": ".../documentProcessingConfig", "defaultParsingConfig": {"digitalParsingConfig": {}}}` so Discovery Engine uses fast digital parsing instead of `eu` Document AI OCR quota.
   - **Enrich `gs://remedata/documents.jsonl` with pre-extracted AESP text & metadata**: Keep the canonical `aesp-2350-t-250-523` record (`gs://remedata/2350-T-250-523.pdf`) enriched with `extracted_text` in `jsonData`, and include a companion pre-extracted text document (`aesp-2350-t-250-523-extracted-text` with base64 `content.rawBytes` and `mimeType: "text/plain"`) so incremental imports complete in `<60 seconds` with zero OCR quota usage and full snippet retrieval.
   - **Add Active-LRO Concurrency Guard & `failureCount` Validation in `import_documents()`**:
     - Before starting a new `documents:import`, check `list_active_import_operations()` on `/branches/0/operations`; if an `import-documents-*` LRO is already in flight (`done != True`), attach to and poll that operation instead of firing a conflicting duplicate import.
     - Increase default `poll_timeout_seconds` to `180` seconds and support `--force-import` CLI flag / `force_import` parameter.
     - When `done == True`, inspect `metadata.failureCount` and `response.errorSamples`; raise a `RuntimeError` if `int(failure_count) > 0` or `errorSamples` is non-empty.
2. **[tests/e2e/test_tier1_features.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/e2e/test_tier1_features.py), [tests/e2e/test_tier2_boundaries.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/e2e/test_tier2_boundaries.py), and [tests/e2e/test_tier4_scenarios.py](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/tests/e2e/test_tier4_scenarios.py)**:
   - Add unit/integration assertions (`test_scenario_13_issue_01_datastore_import_concurrency_guard_and_failure_validation`) verifying `patch_datastore_processing_config()`, active LRO attachment, and `failureCount > 0` / `errorSamples` error detection while preserving all 295 existing test assertions (`296/296` total passing).

## Live Resolution Verification (`2026-10-29T15:21:46Z`)
- **Operation:** `projects/284046449012/locations/eu/collections/default_collection/dataStores/ukd-reme-aesp-ds/branches/0/operations/import-documents-266522232145944738`
- **Import Result:** `done=True, successCount=2, failureCount=0`
- **Indexed Branch 0 Documents:** `['aesp-2350-t-250-523', 'aesp-2350-t-250-523-extracted-text']`
- **Live Search Verification (`servingConfigs/default_search:search`):** `HTTP 200, results_count=2`
- **Gemini Enterprise Engine (`pixel-mobile-demos_1793177711952`) Bound Datastores:** `['jointservicepubs_1793177321711', 'ukd-reme-aesp-ds']`

## Reference & Audit Reports
- **Sentinel Handoff:** [.agents/teamwork/handoff.md](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/.agents/teamwork/handoff.md)
- **Orchestrator Handoff:** [.agents/teamwork/teamwork_orchestrator_r1/handoff.md](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/.agents/teamwork/teamwork_orchestrator_r1/handoff.md)
- **Victory Audit Report:** [.agents/teamwork/teamwork_victory_auditor_r1/handoff.md](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/.agents/teamwork/teamwork_victory_auditor_r1/handoff.md)

## Context Validation Rules
- Do Not Delete the Datastore, try importing and indexing the unstructured document once more
- If `antig-dave` has a strict cap on `eu` OCR/Layout parsing quota, updating `gs://remedata/documents.jsonl` to include pre-extracted text content (`content.rawBytes` or `structData` text chunks) or configuring `ukd-reme-aesp-ds` with standard digital PDF parsing (instead of `ocrParser` / `layoutParser`) allows Discovery Engine to index the AESP manual in under 60 seconds without consuming Document AI OCR quota.
