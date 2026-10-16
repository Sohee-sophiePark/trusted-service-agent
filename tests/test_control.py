from pathlib import Path

import yaml

from trusted_service_agent import control


def write(tmp_path: Path, **over) -> Path:
    cfg = {
        "kill_switch": False,
        "traffic_share": 0.10,
        "auto_pause_on_compliance_incident": True,
        "topics": {"account_questions": True, "ticket_status": True, "product_guidance": True},
    }
    cfg.update(over)
    p = tmp_path / "control.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return p


def test_kill_switch_sends_everything_to_humans(tmp_path):
    p = write(tmp_path, kill_switch=True, traffic_share=1.0)
    gates = [control.admit(f"c{i}", p) for i in range(50)]
    assert all(not g.agent for g in gates) and {g.reason for g in gates} == {"kill_switch"}


def test_traffic_share_matches_setting_within_tolerance(tmp_path):
    p = write(tmp_path, traffic_share=0.10)
    admitted = sum(control.admit(f"contact-{i}", p).agent for i in range(5000))
    assert 0.08 <= admitted / 5000 <= 0.12


def test_traffic_assignment_is_stable_per_contact(tmp_path):
    p = write(tmp_path, traffic_share=0.5)
    first = [control.admit(f"x{i}", p).agent for i in range(100)]
    assert first == [control.admit(f"x{i}", p).agent for i in range(100)]


def test_topic_toggle_off_routes_that_topic_to_humans(tmp_path):
    topics = {"account_questions": True, "ticket_status": True, "product_guidance": False}
    p = write(tmp_path, topics=topics)
    assert not control.topic_enabled("product_guidance", p)
    assert control.topic_enabled("ticket_status", p)


def test_config_is_reread_every_call(tmp_path):
    p = write(tmp_path, traffic_share=1.0)
    assert control.admit("same", p).agent
    write(tmp_path, kill_switch=True)
    assert not control.admit("same", p).agent
