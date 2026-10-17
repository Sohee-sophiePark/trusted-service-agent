"""One turn: control → router → topic toggle → identity → lookup or cited answer → telemetry."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from trusted_service_agent import actions, control, grounding, handoff, router, telemetry
from trusted_service_agent.handoff import HandoffCard
from trusted_service_agent.identity import Session
from trusted_service_agent.llm.gateway import Gateway
from trusted_service_agent.warehouse import Warehouse


@dataclass
class Turn:
    outcome: str  # "resolved" | "handoff" | "identity_requested"
    topic: str | None = None
    answer: str | None = None
    citation: dict | None = None
    data: dict = field(default_factory=dict)
    card: HandoffCard | None = None
    model_calls: int = 0


def ticket_text(t: dict, gw: Gateway) -> str:
    age = (gw.settings.demo_now - t["last_update"]).total_seconds() / 60
    text = (
        f"Ticket {t['ticket_id']} ({t['kind']}) is {t['status']}, "
        f"booked for {t['window_date']:%b %d}, {t['window_slot']}."
    )
    if age > gw.settings.stale_after_minutes:
        text += (
            f" Last updated {t['last_update']:%H:%M}; that may not reflect the technician's latest "
            "progress."
        )
    return text


async def turn(
    contact_id: str,
    text: str,
    session: Session,
    wh: Warehouse,
    gw: Gateway,
    control_file: Path = control.CONTROL_FILE,
    sink: Path = telemetry.SINK,
) -> Turn:
    start = gw.calls
    try:
        result = await _turn(contact_id, text, session, wh, gw, control_file)
    except Exception:  # a failed turn is a handoff, never a dropped customer; it is still logged
        card = HandoffCard(
            queue="servicing", reason="agent_error", summary=None, customer_text=text
        )
        result = Turn("handoff", card=card)
    result.model_calls = gw.calls - start
    if result.card:
        telemetry.emit(
            sink.with_name("queue.jsonl"), contact_id=contact_id, **result.card.model_dump()
        )
    telemetry.emit(
        sink,
        contact_id=contact_id,
        outcome=result.outcome,
        topic=result.topic,
        queue=result.card.queue if result.card else None,
        reason=result.card.reason if result.card else None,
        model_calls=result.model_calls,
        cited=bool(result.citation),
    )
    return result


async def _turn(
    contact_id: str, text: str, session: Session, wh: Warehouse, gw: Gateway, control_file: Path
) -> Turn:
    adm = control.admit(contact_id, control_file)
    if not adm.agent:
        return Turn("handoff", card=await handoff.card("servicing", adm.reason, text, {}, None))
    facts = {"identity_verified": bool(session.account_number)}
    r = await router.route(text, gw)
    if r.topic is None:
        return Turn("handoff", card=await handoff.card(r.queue, r.reason, text, facts, gw))
    if not control.topic_enabled(r.topic, control_file):
        return Turn(
            "handoff", r.topic, card=await handoff.card("servicing", "topic_off", text, facts, gw)
        )
    if r.topic == "product_guidance":
        g = await grounding.answer(text, gw)
        if g is None:
            card = await handoff.card("servicing", "no_citation", text, facts, gw)
            return Turn("handoff", r.topic, card=card)
        cite = {
            "id": g.section.id,
            "title": g.section.title,
            "heading": g.section.heading,
            "effective": g.section.effective,
            "quote": g.quote,
        }
        return Turn("resolved", r.topic, g.answer, cite)
    if not session.account_number:
        return Turn(
            "identity_requested",
            r.topic,
            "To look that up, please share your account number and the postal code of your "
            "service address.",
        )
    if r.topic == "account_questions":
        s = actions.account_summary(wh, session)
        b = s["latest_bill"]
        ans = (
            f"Your plan is {s['plan']['plan']}. Your latest bill of ${b['total']} was issued "
            f"{b['issued']:%b %d} and is due {b['due']:%b %d}; balance due ${s['balance_due']:.2f}."
        )
        return Turn("resolved", r.topic, ans, data=s)
    wanted = m.group(0) if (m := re.search(r"\b\d{5}\b", text)) else None
    tickets, outs = actions.ticket_status(wh, session, wanted), actions.outages(wh, session)
    if not tickets and not outs:
        card = await handoff.card("servicing", "no_open_ticket", text, facts, gw)
        return Turn("handoff", r.topic, card=card)
    lines = [ticket_text(t, gw) for t in tickets]
    lines += [
        f"There is an active {o['service']} outage in your area; estimated restoration "
        f"{o['est_restore']:%H:%M}."
        for o in outs
    ]
    return Turn("resolved", r.topic, " ".join(lines), data={"tickets": tickets, "outages": outs})
