"""Pure-core tests for Shamba Steward tools — no network, no GCP needed."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from shamba_steward import tools  # noqa: E402


def test_parse_due_hint():
    assert tools.parse_due_hint("today", "2026-08-12") == "2026-08-12"
    assert tools.parse_due_hint("tomorrow", "2026-08-12") == "2026-08-13"
    assert tools.parse_due_hint("in 5 days", "2026-08-12") == "2026-08-17"
    # month boundary
    assert tools.add_days("2026-08-30", 5) == "2026-09-04"


def test_plan_puts_spray_before_harvest_and_off_rain():
    events = [
        {"kind": "spray", "crop": "beans", "due_hint": "tomorrow", "pre_harvest_days": 7},
        {"kind": "harvest", "crop": "beans", "due_hint": "in 10 days"},
    ]
    plan = tools.plan_actions(events, "2026-08-12", rain_days=["2026-08-15"])
    spray = next(a for a in plan["actions"] if a["kind"] == "spray")
    harvest = next(a for a in plan["actions"] if a["kind"] == "harvest")
    assert spray["date"] < harvest["date"]           # treatment precedes harvest
    assert spray["date"] not in ["2026-08-15"]        # never on a rain day


def test_verify_flags_pre_harvest_interval():
    plan = {"actions": [
        {"id": "spray-0", "kind": "spray", "crop": "maize", "date": "2026-08-20", "pre_harvest_days": 7},
        {"id": "harvest-1", "kind": "harvest", "crop": "maize", "date": "2026-08-24"},
    ]}
    v = tools.verify_plan(plan, "2026-08-12")
    assert any("pre-harvest" in x["reason"] for x in v)


def test_verify_allows_safe_gap():
    plan = {"actions": [
        {"id": "spray-0", "kind": "spray", "crop": "maize", "date": "2026-08-12", "pre_harvest_days": 7},
        {"id": "harvest-1", "kind": "harvest", "crop": "maize", "date": "2026-08-24"},
    ]}
    assert tools.verify_plan(plan, "2026-08-12") == []


def test_calendar_and_message():
    plan = {"actions": [{"id": "sale-0", "kind": "sale", "crop": "maize", "date": "2026-08-20", "reason": "r"}]}
    ics = tools.make_calendar(plan)
    assert ics.startswith("BEGIN:VCALENDAR") and "BEGIN:VEVENT" in ics and "DTSTART" in ics
    msg = tools.draft_market_message([{"kind": "sale", "crop": "maize", "quantity": 3, "unit": "bags"}])
    assert "3" in msg and "maize" in msg
