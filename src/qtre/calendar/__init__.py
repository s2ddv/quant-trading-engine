"""Formation dates in a supplied, versioned synthetic calendar."""

from datetime import datetime
from qtre.data.snapshot import Snapshot


def formation_sessions(snapshot: Snapshot, decision_at: datetime, formation_session: str | None = None):
    """Select a completed month end; an explicit date permits late decisions."""
    snapshot.check_as_of(decision_at)
    sessions = snapshot.payload["calendar"]["sessions"]
    completed = [r for r in sessions if datetime.fromisoformat(r["close_at"].replace("Z", "+00:00")) < decision_at]
    if not completed:
        raise ValueError("decision precedes every complete session")
    day = formation_session or completed[-1]["session"]
    if day not in {r["session"] for r in completed}:
        raise ValueError("formation_session must be completed before decision")
    following = next((r["session"] for r in sessions if r["session"] > day), None)
    if following is None or following[:7] == day[:7]:
        raise ValueError("formation must be the last session of a month")
    return tuple(r for r in completed if r["session"] <= day)
