"""Firestore-backed Memory Bank for Shamba Steward.

Persists a farm's notes across sessions so the agent personalises over time
(the "persistent cross-session memory" the Enterprise/Collaborative tracks reward).
Degrades gracefully when Firestore is unavailable (e.g. local dev without ADC) so
the agent still runs — memory just becomes a no-op with an honest note.
"""
import os
from typing import Any

_COLLECTION = os.environ.get("STEWARD_FS_COLLECTION", "shamba_farms")


def _client():
    """Return a Firestore client, or None if unavailable (honest degrade)."""
    try:
        from google.cloud import firestore  # imported lazily so local dev needn't have it
        return firestore.Client()
    except Exception:
        return None


def remember_note(user_id: str, note: str) -> dict:
    """Append a field note to this farm's history in Firestore. Returns status."""
    db = _client()
    if db is None:
        return {"stored": False, "reason": "memory backend unavailable (running without Firestore)"}
    try:
        from google.cloud import firestore
        ref = db.collection(_COLLECTION).document(user_id)
        ref.set({"notes": firestore.ArrayUnion([note])}, merge=True)
        return {"stored": True, "user_id": user_id}
    except Exception as e:  # never crash the agent on a memory write
        return {"stored": False, "reason": str(e)[:120]}


def recall_history(user_id: str) -> dict:
    """Load this farm's prior notes from Firestore. Returns {notes: [...]}. """
    db = _client()
    if db is None:
        return {"notes": [], "reason": "memory backend unavailable (running without Firestore)"}
    try:
        snap = db.collection(_COLLECTION).document(user_id).get()
        data = snap.to_dict() if snap.exists else {}
        return {"notes": data.get("notes", [])}
    except Exception as e:
        return {"notes": [], "reason": str(e)[:120]}
