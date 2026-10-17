from fastapi.testclient import TestClient

from trusted_service_agent import api, control

BODY = {"session_id": "s1", "account_number": "TS-100201", "postal_code": "M4C 1B5"}
client = TestClient(api.app, base_url="http://localhost")
KILL = control.Admission(False, "kill_switch")
ADMIT = control.Admission(True, "admitted")


def test_verify_returns_no_account_data_under_kill_switch(monkeypatch):
    monkeypatch.setattr(control, "admit", lambda cid, path=None: KILL)
    r = client.post("/api/verify", json=BODY).json()
    assert r == {"verified": True, "overview": None}


def test_verify_returns_overview_when_admitted(monkeypatch):
    monkeypatch.setattr(control, "admit", lambda cid, path=None: ADMIT)
    monkeypatch.setattr(control, "topic_enabled", lambda t, path=None: t == "ticket_status")
    r = client.post("/api/verify", json=BODY).json()
    assert r["overview"]["tickets"][0]["id"] == "44812" and r["overview"]["bill"] is None
