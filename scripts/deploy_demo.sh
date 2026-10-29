#!/usr/bin/env bash
set -euo pipefail

export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
export PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-antig-dave}"
export REGION="europe-west1"
export SERVICE_ACCOUNT="sa-reme-demo@antig-dave.iam.gserviceaccount.com"
export CHAT_SERVICE_NAME="reme-chat-demonstrator"
export TICKET_IMAGES_BUCKET="antig-dave-reme-ticket-images-eu"
export GEMINI_APP_ID="projects/antig-dave/locations/eu/collections/default_collection/engines/pixel-mobile-demos_1793177711952"

echo "============================================================"
echo "1. Verifying Active GCP Identity (Must be admin@edwardsda.altostrat.com)"
echo "============================================================"
ACTIVE_ACCOUNT=$(gcloud config get-value account)
if [[ "${ACTIVE_ACCOUNT}" != "admin@edwardsda.altostrat.com" ]]; then
  echo "Switching active account to admin@edwardsda.altostrat.com..."
  gcloud config set account admin@edwardsda.altostrat.com
fi
gcloud config set project "${PROJECT_ID}"

echo "============================================================"
echo "2. Provisioning Ticket Image Bucket, Vertex AI Search & Seeding BigQuery"
echo "============================================================"
if ! gcloud storage buckets describe "gs://${TICKET_IMAGES_BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${TICKET_IMAGES_BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
fi
gcloud storage buckets add-iam-policy-binding "gs://${TICKET_IMAGES_BUCKET}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.objectAdmin" \
  --project="${PROJECT_ID}" >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://${TICKET_IMAGES_BUCKET}" \
  --member="principal://agents.global.org-137541019652.system.id.goog/resources/aiplatform/projects/284046449012/locations/europe-west1/reasoningEngines/6397856951400660992" \
  --role="roles/storage.objectAdmin" \
  --project="${PROJECT_ID}" >/dev/null || true
uv run python scripts/setup_reme_datastore.py
uv run python scripts/seed_demo1_bigquery.py

echo "============================================================"
echo "3. Deploying Sustainment Group Chat Web App to Cloud Run (${REGION})"
echo "============================================================"
gcloud run deploy "${CHAT_SERVICE_NAME}" \
  --source ./cloud_run_chat_app \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --service-account "${SERVICE_ACCOUNT}" \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=5 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},BQ_DATASET=ukd_reme_demo,BQ_LOCATION=${REGION},TICKET_IMAGES_BUCKET=${TICKET_IMAGES_BUCKET}" \
  --quiet

CHAT_URL=$(gcloud run services describe "${CHAT_SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(status.url)")
echo "✅ Cloud Run Sustainment Group Chat Live URL: ${CHAT_URL}"

# Update CLOUD_RUN_CHAT_URL in .env so the deployed ADK agent points to live Cloud Run
if grep -q "^CLOUD_RUN_CHAT_URL=" .env; then
  sed -i "s|^CLOUD_RUN_CHAT_URL=.*|CLOUD_RUN_CHAT_URL=${CHAT_URL}|" .env
else
  echo "CLOUD_RUN_CHAT_URL=${CHAT_URL}" >> .env
fi

echo "============================================================"
echo "4. Deploying ADK 2.0 Agent to Vertex AI Agent Engine (${REGION})"
echo "============================================================"
uv lock --default-index https://pypi.org/simple --no-config
GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli deploy \
  --deployment-target agent_runtime \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --env-vars="GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_API_USE_CLIENT_CERTIFICATE=false,BQ_DATASET=ukd_reme_demo,BQ_LOCATION=${REGION},DISCOVERY_ENGINE_LOCATION=eu,VERTEX_SEARCH_DATASTORE_ID=ukd-reme-aesp-ds,GCS_SOURCE_BUCKET=remedata,TICKET_IMAGES_BUCKET=${TICKET_IMAGES_BUCKET},CLOUD_RUN_CHAT_URL=${CHAT_URL}"

echo "============================================================"
echo "5. Non-Destructively Publishing Agent to Gemini Enterprise"
echo "============================================================"
GOOGLE_API_USE_CLIENT_CERTIFICATE=false agents-cli publish gemini \
  --gemini-app-id "${GEMINI_APP_ID}" \
  --display-name "REME-Artificer" \
  --description "British Army REME Master Artificer agent for AESP fault diagnosis, NSN inventory lookup, and FRT Sustainment Group Chat dispatch." \
  --tool-description "Diagnose vehicle faults against AESP manuals, query NSN inventory and MGRS grids in BigQuery, and publish recovery tickets to the 4 Bn REME Sustainment Group Chat." \
  --project "${PROJECT_ID}"

echo "============================================================"
echo "🎉 Deployment & Gemini Enterprise Registration Complete!"
echo "Cloud Run Chat URL: ${CHAT_URL}"
echo "============================================================"
