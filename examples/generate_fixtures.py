"""Generate the two deliberately small, deterministic F0 synthetic snapshots."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SESSIONS = ("2025-01-30", "2025-01-31", "2025-02-03")
AS_OF = "2025-02-04T00:00:00Z"


def provenance(snapshot_id: str, observed: str, available: str, ingested: str) -> dict:
    return dict(source_id="synthetic-fixture", source_version="1", snapshot_id=snapshot_id,
                observed_at=observed, available_at=available, ingested_at=ingested)


def make_snapshot(adverse: bool) -> dict:
    name = "synthetic-adverse-v1" if adverse else "synthetic-normal-v1"
    sessions = [dict(session=day, open_at=f"{day}T13:00:00Z", close_at=f"{day}T20:00:00Z") for day in SESSIONS]
    root = dict(schema_version=1, snapshot_id=name, as_of=AS_OF,
                calendar=dict(calendar_id="synthetic-calendar-v1", timezone="America/Sao_Paulo", sessions=sessions),
                bars=[], opens=[], actions=[], memberships=[], symbols=[])
    for instrument, ticker, base in (("SYN-001", "SYN1", 10), ("SYN-002", "SYN2", 20)):
        p = provenance(name, "2025-01-01T00:00:00Z", "2025-01-01T00:01:00Z", "2025-01-01T00:02:00Z")
        root["memberships"].append(dict(instrument_id=instrument, valid_from="2025-01-01", valid_to=None,
                                         status="listed", reason="synthetic listing", **p))
        root["symbols"].append(dict(instrument_id=instrument, ticker=ticker, valid_from="2025-01-01", valid_to=None, **p))
        for index, day in enumerate(SESSIONS):
            if adverse and instrument == "SYN-002" and day == "2025-02-03":
                # Suspension: no complete bar; the opening says it is untradable.
                root["opens"].append(dict(instrument_id=instrument, session=day, open_price=base,
                                          currency="BRL", tradable=False,
                                          **provenance(name, f"{day}T13:00:00Z", f"{day}T13:00:00Z", f"{day}T13:01:00Z")))
                continue
            opening = base + index
            closing = opening + 0.2
            root["opens"].append(dict(instrument_id=instrument, session=day, open_price=opening,
                                      currency="BRL", tradable=True,
                                      **provenance(name, f"{day}T13:00:00Z", f"{day}T13:00:00Z", f"{day}T13:01:00Z")))
            root["bars"].append(dict(instrument_id=instrument, session=day, open=opening,
                                     high=opening + 0.4, low=opening - 0.2, close=closing,
                                     volume_shares=10000, volume_brl=10000 * closing,
                                     currency="BRL", adjustment_basis="raw",
                                     **provenance(name, f"{day}T20:00:00Z", f"{day}T20:05:00Z", f"{day}T20:06:00Z")))
    if adverse:
        root["actions"].extend([
            dict(action_id="A-SPLIT", instrument_id="SYN-001", kind="split", ratio=2,
                 announced_at="2025-01-30T18:00:00Z", ex_session="2025-02-03",
                 **provenance(name, "2025-01-30T18:00:00Z", "2025-01-30T18:01:00Z", "2025-01-30T18:02:00Z")),
            dict(action_id="A-DIV", instrument_id="SYN-002", kind="dividend", cash_per_share=0.5,
                 announced_at="2025-01-30T18:00:00Z", ex_session="2025-01-31", pay_session="2025-02-03",
                 **provenance(name, "2025-01-30T18:00:00Z", "2025-01-30T18:01:00Z", "2025-01-30T18:02:00Z")),
        ])
    return root


if __name__ == "__main__":
    for is_adverse in (False, True):
        payload = make_snapshot(is_adverse)
        path = HERE / ("synthetic_adverse_v1.json" if is_adverse else "synthetic_normal_v1.json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
