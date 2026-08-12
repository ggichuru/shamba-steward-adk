"""Shamba Steward — a Google ADK Taskmaster agent for smallholder farmers.

The agent takes a farmer's one messy field note and autonomously runs a real
workflow: extract structured events, schedule them, VERIFY the plan against
agrochemical pre-harvest safety intervals, and deliver a calendar + market
message. It refuses to hand back an unsafe plan. Cross-session farm context is
persisted in Firestore (Memory Bank).

Model: Gemini via Vertex AI (set GOOGLE_GENAI_USE_VERTEXAI=1, GOOGLE_CLOUD_PROJECT,
GOOGLE_CLOUD_LOCATION). Deploy: `adk deploy cloud_run` (see README).
"""
import os
from google.adk.agents import Agent

from . import tools
from . import memory

MODEL = os.environ.get("STEWARD_MODEL", "gemini-2.5-flash")

_INSTRUCTION = """\
You are Shamba Steward, an autonomous farm-operations agent for a smallholder farmer.
You do NOT just chat — you take action by calling your tools.

Given the farmer's field note, work through this workflow every time:

1. EXTRACT the events from the note into this shape and remember them:
   {kind: 'plant'|'spray'|'harvest'|'sale', crop?, plot?, issue?, quantity?, unit?,
    due_hint?  (e.g. 'tomorrow', 'thursday', 'in 5 days'),
    pre_harvest_days? (days a spray must clear before harvest; default 7)}.
2. Call recall_history(user_id) to load anything you already know about this farm.
3. Call plan_actions(events, today, rain_days) to schedule the work.
4. Call verify_plan(plan, today, rain_days, window_start, window_end). If it returns
   ANY violations, tell the farmer plainly what is unsafe (e.g. a spray inside its
   pre-harvest interval) and adjust — NEVER present an unsafe plan as if it were fine.
5. Call make_calendar(plan) and draft_market_message(events) to deliver artifacts.
6. Call remember_note(user_id, note) so the farm's context grows across sessions.

Report: the scheduled plan (date · action · why), any safety violations you caught,
and the delivered calendar + market message. Be concise and practical. The current
date and any forecast rain days are provided to you; if not, ask for them once.
"""

root_agent = Agent(
    name="shamba_steward",
    model=MODEL,
    description="Autonomous farm-operations Taskmaster: schedules and safety-verifies "
                "a farmer's work from one messy note, then delivers a calendar + market message.",
    instruction=_INSTRUCTION,
    tools=[
        tools.plan_actions,
        tools.verify_plan,
        tools.make_calendar,
        tools.draft_market_message,
        memory.remember_note,
        memory.recall_history,
    ],
)
