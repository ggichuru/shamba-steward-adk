"""Deterministic farm-ops tools for the Shamba Steward ADK agent.

These are pure, side-effect-free functions the LLM agent CALLS to take action.
The safety verifier is the honest core: it refuses to hand back a plan that
sprays a crop inside its agrochemical pre-harvest interval. No network here.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any


# ---- date helpers (epoch-correct; no getDate()-N month bugs) ----
def _d(ymd: str) -> date:
    y, m, dd = (int(x) for x in ymd.split("-"))
    return date(y, m, dd)


def add_days(ymd: str, n: int) -> str:
    return (_d(ymd) + timedelta(days=n)).isoformat()


def parse_due_hint(hint: str | None, today: str) -> str | None:
    """Resolve 'today'/'tomorrow'/weekday/'in N days'/'next week' to a date."""
    if not hint:
        return None
    h = hint.strip().lower()
    if h == "today":
        return today
    if h == "tomorrow":
        return add_days(today, 1)
    if h == "next week":
        return add_days(today, 7)
    weekdays = {"mon": 0, "monday": 0, "tue": 1, "tuesday": 1, "wed": 2, "wednesday": 2,
                "thu": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5,
                "sun": 6, "sunday": 6}
    if h in weekdays:
        cur = _d(today).weekday()
        delta = (weekdays[h] - cur + 7) % 7 or 7
        return add_days(today, delta)
    if h.startswith("in ") and h.endswith(("day", "days")):
        try:
            n = int(h.split()[1])
            return add_days(today, n)
        except (ValueError, IndexError):
            return None
    return None


# ---- planning ----
_ORDER = {"plant": 0, "spray": 1, "harvest": 2, "sale": 3}


def plan_actions(events: list[dict], today: str, rain_days: list[str] | None = None) -> dict:
    """Schedule each field-event onto a date. Treatments precede harvest;
    a spray is pulled to `pre_harvest_days` before its crop's harvest and is
    never dated on a forecast rain day. Returns {"actions": [...]}."""
    rain_days = rain_days or []
    evs = sorted(events, key=lambda e: _ORDER.get(e.get("kind", ""), 9))
    harvest_by_crop = {}
    for e in evs:
        if e.get("kind") == "harvest" and e.get("crop"):
            harvest_by_crop[e["crop"]] = parse_due_hint(e.get("due_hint"), today) or add_days(today, 14)

    actions = []
    for i, e in enumerate(evs):
        kind = e.get("kind", "note")
        d = parse_due_hint(e.get("due_hint"), today) or today
        reason = ""
        if kind == "spray" and e.get("crop") in harvest_by_crop:
            phi = int(e.get("pre_harvest_days", 7) or 7)
            hv = harvest_by_crop[e["crop"]]
            d = add_days(hv, -phi)
            reason = f"scheduled {phi} days before {e['crop']} harvest ({hv}) to clear the pre-harvest interval"
        # never spray on a rain day: step backward
        if kind == "spray":
            guard = 0
            while d in rain_days and guard < 30:
                d = add_days(d, -1)
                guard += 1
            if not reason:
                reason = "moved off a forecast rain day" if e.get("due_hint") else "next dry working day"
        if d < today:
            d = today
        actions.append({
            "id": f"{kind}-{i}", "kind": kind, "crop": e.get("crop"), "plot": e.get("plot"),
            "issue": e.get("issue"), "quantity": e.get("quantity"), "unit": e.get("unit"),
            "pre_harvest_days": e.get("pre_harvest_days"), "date": d,
            "reason": reason or "as noted",
        })
    return {"actions": actions}


# ---- verification (the honest safety layer) ----
def verify_plan(plan: dict, today: str, rain_days: list[str] | None = None,
                window_start: str | None = None, window_end: str | None = None) -> list[dict]:
    """Return a list of {action_id, reason} violations. Flags: a spray inside
    its pre-harvest interval before a same-crop harvest; an action outside the
    season window; a past-dated action; a spray on a rain day."""
    rain_days = rain_days or []
    v: list[dict] = []
    actions = plan.get("actions", [])
    for a in actions:
        d = a["date"]
        if d < today:
            v.append({"action_id": a["id"], "reason": f"{a['kind']} on {d} is in the past"})
        if window_start and window_end and (d < window_start or d > window_end):
            v.append({"action_id": a["id"],
                      "reason": f"{a['kind']} on {d} is outside the {window_start}…{window_end} window"})
        if a["kind"] == "spray":
            if d in rain_days:
                v.append({"action_id": a["id"], "reason": f"spray on {d} falls on a forecast rain day"})
            if a.get("crop"):
                phi = int(a.get("pre_harvest_days") or 7)
                for h in actions:
                    if h["kind"] == "harvest" and h.get("crop") == a["crop"]:
                        if a["date"] <= h["date"] <= add_days(a["date"], phi):
                            v.append({"action_id": a["id"],
                                      "reason": (f"spray on {d} is within its {phi}-day pre-harvest "
                                                 f"interval before {a['crop']} harvest on {h['date']}")})
    return v


# ---- delivery (take action) ----
def make_calendar(plan: dict) -> str:
    """Emit a valid VCALENDAR (.ics) with one VEVENT per scheduled action."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Shamba Steward//EN", "CALSCALE:GREGORIAN"]
    for a in plan.get("actions", []):
        stamp = a["date"].replace("-", "")
        summ = f"{a['kind'].title()}"
        if a.get("crop"):
            summ += f" {a['crop']}"
        if a.get("plot"):
            summ += f" ({a['plot']})"
        lines += ["BEGIN:VEVENT", f"UID:{a['id']}@shamba-steward", f"DTSTART;VALUE=DATE:{stamp}",
                  f"SUMMARY:{summ}", f"DESCRIPTION:{a.get('reason','')}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def draft_market_message(events: list[dict]) -> str | None:
    """A ready-to-send market message when a sale event exists."""
    for e in events:
        if e.get("kind") == "sale":
            qty = e.get("quantity")
            unit = e.get("unit", "units")
            crop = e.get("crop", "produce")
            q = f"{qty} {unit} of " if qty else ""
            return f"For sale: {q}{crop}, harvested fresh. Reply to arrange pickup at the local market."
    return None
