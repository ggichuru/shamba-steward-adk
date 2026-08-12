# Shamba Steward — an autonomous farm-operations agent (Google ADK + Gemini + Cloud Run)

**Track:** The Taskmaster · **Built for:** All Things Agentic Hackathon

A smallholder farmer types **one messy field note** — *"North plot maize is tasseling.
Aphids on the beans in the east plot. Rain expected Thursday. Need to sell 3 bags of
maize."* — and Shamba Steward runs a real, autonomous workflow, not a chat:

1. **Extract** the note into structured field-events (Gemini 2.5 Flash via Vertex AI).
2. **Recall** the farm's prior context from the Firestore Memory Bank.
3. **Plan** — schedule each action; treatments precede harvest; never spray on a rain day.
4. **Verify** — the honest safety layer: it flags any spray inside its agrochemical
   **pre-harvest interval** before a same-crop harvest, and refuses to present an unsafe plan.
5. **Deliver** — a calendar (`.ics`) of the scheduled work and a ready-to-send market message.

## Architecture

See `architecture.md`. In short: **Cloud Run** hosts the **ADK agent**; the agent reasons
with **Gemini 2.5 Flash on Vertex AI** and calls typed tools to take action; **Firestore**
is the cross-session Memory Bank. The safety verifier and calendar/message builders are
pure, deterministic Python (unit-tested) — the LLM decides *when* to call them, not what
they compute.

## Run it locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest

# prove the deterministic safety core (no cloud needed):
python -m pytest tests/ -q

# run the agent locally against Vertex AI (needs gcloud auth below):
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=<your-project-id>
export GOOGLE_CLOUD_LOCATION=us-central1
adk web            # opens the ADK dev UI; pick "shamba_steward"
```

## Deploy to Google Cloud Run

```bash
# 1. one-time auth
gcloud auth login
gcloud auth application-default login

# 2. enable the APIs (once per project)
gcloud services enable aiplatform.googleapis.com run.googleapis.com \
  firestore.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  --project <your-project-id>

# 3. create a Firestore (Native mode) database in us-central1 (once)
gcloud firestore databases create --location=us-central1 --project <your-project-id>

# 4. deploy (wraps the agent in a FastAPI service + ADK web UI)
export GOOGLE_CLOUD_PROJECT=<your-project-id>
bash deploy.sh
```

The deploy prints your Cloud Run URL. For the demo, show the Cloud Run console + Vertex AI
logs, then scale to zero or delete the service to keep costs near zero (see `deploy.sh`).

## Why it fits the judging

- **Innovation & Operational Utility (40%)** — it *acts*: a verified schedule + artifacts
  from one note, catching an agronomic safety error a chatbot would miss.
- **Architectural Discipline (30%)** — decoupled agent/tools/memory; Gemini reasons,
  deterministic tools compute, Firestore persists; graceful degrade when memory is offline.
- **Demo & Production Readiness (30%)** — reproducible setup (this README), an architecture
  diagram, and a live agent on Cloud Run + Vertex AI.
