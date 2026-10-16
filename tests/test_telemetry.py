import json

from trusted_service_agent import telemetry


def test_every_outcome_is_appended_including_refusals(tmp_path):
    sink = tmp_path / "events.jsonl"
    telemetry.emit(sink, contact_id="c1", outcome="handoff", queue="disputes", model_calls=0)
    telemetry.emit(sink, contact_id="c2", outcome="resolved", topic="ticket_status", model_calls=1)
    rows = [json.loads(line) for line in sink.read_text().splitlines()]
    assert [r["outcome"] for r in rows] == ["handoff", "resolved"]
    assert rows[0]["queue"] == "disputes" and "ts" in rows[0]
