#!/usr/bin/env bash
# Deploy Shamba Steward (ADK agent) to Google Cloud Run with the ADK web UI.
# Prereqs: gcloud auth login && gcloud auth application-default login;
#          a GCP project with Vertex AI, Cloud Run, Firestore, Cloud Build enabled;
#          a Firestore (Native mode) database created.
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?set GOOGLE_CLOUD_PROJECT to your project id}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE="${SERVICE_NAME:-shamba-steward}"

# Use Gemini via Vertex AI (no API key; auth via the project).
export GOOGLE_GENAI_USE_VERTEXAI=1

adk deploy cloud_run \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$REGION" \
  --service_name "$SERVICE" \
  --with_ui \
  ./shamba_steward

echo
echo "Deployed. The command above prints the Cloud Run URL."
echo "Cost control: 'gcloud run services update $SERVICE --min-instances=0 --region $REGION' (scale to zero),"
echo "and after recording your demo: 'gcloud run services delete $SERVICE --region $REGION'."
