"""Quant Trading Research Engine: research contracts, not live trading."""

from .data.snapshot import Snapshot, SnapshotError, load_snapshot

__all__ = ["Snapshot", "SnapshotError", "load_snapshot"]
