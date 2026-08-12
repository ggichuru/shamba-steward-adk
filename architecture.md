# Shamba Steward — Architecture

```mermaid
flowchart TD
    F["Farmer<br/>(one messy field note)"] -->|HTTP| CR

    subgraph GCP["Google Cloud"]
      CR["Cloud Run<br/>ADK agent service (+ web UI)"]
      subgraph AGENT["ADK LlmAgent: shamba_steward"]
        REASON["Gemini 2.5 Flash<br/>(Vertex AI) — reasons &amp; routes"]
        T1["plan_actions()"]
        T2["verify_plan()<br/>pre-harvest-interval SAFETY"]
        T3["make_calendar() → .ics"]
        T4["draft_market_message()"]
        T5["recall_history / remember_note"]
      end
      VX["Vertex AI<br/>Gemini API"]
      FS[("Firestore<br/>Memory Bank<br/>cross-session farm context")]
    end

    CR --> AGENT
    REASON -.calls.-> T1 & T2 & T3 & T4 & T5
    REASON <-->|generateContent| VX
    T5 <--> FS
    AGENT -->|verified plan · .ics · market msg| F

    classDef safe fill:#FFC83C,stroke:#8a6d1a,color:#1a1400;
    class T2 safe;
```

## The decoupling (why this scores on Architectural Discipline)

- **Gemini reasons; it does not compute.** The model extracts events and decides *which*
  tool to call and *when*. The load-bearing computations — scheduling and the agrochemical
  **pre-harvest-interval safety check** — are pure, deterministic Python (`tools.py`),
  unit-tested independently of the model. An LLM cannot "hallucinate" a safe plan past the
  verifier.
- **State is external.** Cross-session memory lives in **Firestore**, not in the model
  context, so the agent personalises over weeks and survives restarts. Memory failures
  degrade gracefully (the agent still runs; memory becomes a no-op with an honest note).
- **Runtime scales to zero.** Cloud Run holds no state and idles at zero cost between runs.
- **Credentials.** Gemini is reached through **Vertex AI** using the project's own
  identity (ADC) — no API key in code or image.

## Data flow (one run)

1. Farmer note → Cloud Run → ADK agent.
2. Agent (Gemini) extracts events → `recall_history` (Firestore) → `plan_actions`.
3. `verify_plan` runs the safety checks; violations are surfaced, not hidden.
4. `make_calendar` + `draft_market_message` produce the artifacts.
5. `remember_note` writes the note back to the Memory Bank.
