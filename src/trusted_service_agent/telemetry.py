"""Append-only event log: one JSON line per turn, including refusals and handoffs."""

import json
from datetime import UTC, datetime
from pathlib import Path

from trusted_service_agent.paths import RUNS

SINK = RUNS / "telemetry.jsonl"


def emit(sink: Path = SINK, **event) -> dict:
    row = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), **event}
    sink.parent.mkdir(parents=True, exist_ok=True)
    with sink.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row
