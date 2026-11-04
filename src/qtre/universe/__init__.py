"""Dated, point-in-time universe membership."""

from datetime import datetime

from qtre.data.snapshot import Snapshot


def listed_members(snapshot: Snapshot, session: str, *, as_of: datetime) -> tuple[str, ...]:
    """Return known listed instruments valid on a session date."""
    rows = snapshot.available("memberships", as_of)
    return tuple(sorted(row["instrument_id"] for row in rows
                        if row["status"] == "listed" and row["valid_from"] <= session
                        and (row["valid_to"] is None or session <= row["valid_to"])))
