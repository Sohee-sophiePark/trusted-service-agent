"""Today's tiles from the telemetry log; refusals and handoffs count as successful outcomes."""

import json
from pathlib import Path

from trusted_service_agent.telemetry import SINK


def today(sink: Path = SINK) -> dict:
    rows = [json.loads(x) for x in sink.read_text().splitlines()] if sink.exists() else []
    agent = [r for r in rows if r.get("reason") not in ("kill_switch", "traffic_share")]
    handoffs = [r for r in agent if r["outcome"] == "handoff"]
    return {
        "contacts": len(rows),
        "agent_contacts": len(agent),
        "resolved": sum(r["outcome"] == "resolved" for r in agent),
        "handoffs": len(handoffs),
        "never_do_handoffs": sum(
            r.get("reason")
            not in ("low_confidence", "out_of_scope", "no_citation", "topic_off", "no_open_ticket")
            for r in handoffs
        ),
        "escalation_rate": len(handoffs) / len(agent) if agent else None,
        "to_humans_by_control": len(rows) - len(agent),
        "model_calls": sum(r.get("model_calls", 0) for r in rows),
    }
