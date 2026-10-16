import re
from pathlib import Path

import pytest
import yaml
from conftest import reply

from trusted_service_agent import actions, agent, grounding, identity
from trusted_service_agent.identity import NotVerified, Session
from trusted_service_agent.paths import ROOT
from trusted_service_agent.warehouse import Warehouse

SRC = ROOT / "src" / "trusted_service_agent"


@pytest.fixture(scope="module")
def wh():
    return Warehouse()


def ctl(tmp_path: Path, **over) -> Path:
    cfg = {
        "kill_switch": False,
        "traffic_share": 1.0,
        "auto_pause_on_compliance_incident": True,
        "topics": {"account_questions": True, "ticket_status": True, "product_guidance": True},
    }
    cfg.update(over)
    p = tmp_path / "control.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return p


def verified(wh) -> Session:
    postal = wh.rows(
        "SELECT c.postal_code FROM servicing.account a JOIN servicing.customer c "
        "USING (customer_id) WHERE account_number = 'TS-100201'",
        [],
    )[0]["postal_code"]
    return identity.verify(wh, "ts-100201", postal.lower())


def test_identity_gate(wh):
    assert verified(wh).account_number == "TS-100201"
    assert identity.verify(wh, "TS-100201", "X0X 0X0").account_number is None
    with pytest.raises(NotVerified):
        actions.account_summary(wh, Session())


def test_no_write_path_exists_in_the_code():
    code = "\n".join(p.read_text() for p in SRC.rglob("*.py"))
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|MERGE)\b", code)
    assert "read_only=True" in (SRC / "warehouse.py").read_text()


def test_transcripts_never_reach_the_answer_path():
    assert not any("transcripts" in p.read_text() for p in SRC.rglob("*.py"))


def test_quote_must_be_verbatim():
    s = next(x for x in grounding.sections() if x.id.endswith("late-fees.md#amount"))
    assert grounding.verified("The late payment charge is 2% of the overdue balance", s)
    assert not grounding.verified("The late payment charge is 1% of the balance", s)


async def test_kill_switch_makes_no_model_call(tmp_path, wh, gw):
    t = await agent.turn(
        "c1",
        "how do late payment fees work",
        Session(),
        wh,
        gw,
        ctl(tmp_path, kill_switch=True),
        tmp_path / "t.jsonl",
    )
    assert (t.outcome, t.card.reason, t.model_calls) == ("handoff", "kill_switch", 0)


async def test_dispute_hands_off_with_summary(tmp_path, wh, gw, scripted):
    scripted.add(
        "writer",
        reply(
            customer_goal="Remove a charge",
            already_done=["identity not verified"],
            open_question="Is the charge valid?",
            sentiment="frustrated",
            vulnerability_flag=False,
            do_not_repeat=[],
        ),
    )
    t = await agent.turn(
        "c2",
        "I want a refund for a charge I didn't make",
        Session(),
        wh,
        gw,
        ctl(tmp_path),
        tmp_path / "t.jsonl",
    )
    assert (t.outcome, t.card.queue, t.model_calls) == ("handoff", "disputes", 1)


async def test_ticket_status_needs_identity_then_looks_up(tmp_path, wh, gw, scripted):
    scripted.add(
        "router",
        reply(destination="ticket_status", confidence=0.95),
        reply(destination="ticket_status", confidence=0.95),
    )
    q = "what's the status of ticket 44812"
    t1 = await agent.turn("c3", q, Session(), wh, gw, ctl(tmp_path), tmp_path / "t.jsonl")
    assert t1.outcome == "identity_requested"
    t2 = await agent.turn("c3", q, verified(wh), wh, gw, ctl(tmp_path), tmp_path / "t.jsonl")
    assert t2.outcome == "resolved" and "44812" in t2.answer and t2.model_calls == 1


async def test_product_answer_carries_a_verified_citation(tmp_path, wh, gw, scripted):
    scripted.add("router", reply(destination="product_guidance", confidence=0.9))
    scripted.add(
        "writer",
        reply(
            supported=True,
            answer="It is 2% of the overdue balance, $5 to $25.",
            quote="The late payment charge is 2% of the overdue balance, with a "
            "minimum of $5 and a maximum of $25 per bill.",
            section_id="policies/late-fees.md#amount",
        ),
    )
    t = await agent.turn(
        "c4",
        "how much is the late payment fee",
        Session(),
        wh,
        gw,
        ctl(tmp_path),
        tmp_path / "t.jsonl",
    )
    assert t.outcome == "resolved" and t.citation["id"] == "policies/late-fees.md#amount"


async def test_unverifiable_quote_hands_off(tmp_path, wh, gw, scripted):
    scripted.add("router", reply(destination="product_guidance", confidence=0.9))
    scripted.add(
        "writer",
        reply(
            supported=True,
            answer="It is 1%.",
            quote="The fee is 1%.",
            section_id="policies/late-fees.md#amount",
        ),
        reply(
            customer_goal="Know the late fee",
            already_done=[],
            open_question="Fee amount",
            sentiment="calm",
            vulnerability_flag=False,
            do_not_repeat=[],
        ),
    )
    t = await agent.turn(
        "c5",
        "how much is the late payment fee",
        Session(),
        wh,
        gw,
        ctl(tmp_path),
        tmp_path / "t.jsonl",
    )
    assert (t.outcome, t.card.reason) == ("handoff", "no_citation")


async def test_topic_toggled_off_routes_to_a_human(tmp_path, wh, gw, scripted):
    scripted.add("router", reply(destination="product_guidance", confidence=0.9))
    scripted.add(
        "writer",
        reply(
            customer_goal="Late fee",
            already_done=[],
            open_question="Fee",
            sentiment="calm",
            vulnerability_flag=False,
            do_not_repeat=[],
        ),
    )
    topics = {"account_questions": True, "ticket_status": True, "product_guidance": False}
    t = await agent.turn(
        "c6",
        "how much is the late payment fee",
        Session(),
        wh,
        gw,
        ctl(tmp_path, topics=topics),
        tmp_path / "t.jsonl",
    )
    assert (t.outcome, t.card.reason) == ("handoff", "topic_off")
