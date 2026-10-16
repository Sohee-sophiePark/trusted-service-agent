"""Handoff card: queue and reason from code; summary from the model only when admitted."""

from typing import Literal

from pydantic import BaseModel, Field

from trusted_service_agent.llm.gateway import Gateway
from trusted_service_agent.paths import ROOT


class Summary(BaseModel):
    customer_goal: str = Field(max_length=120)
    already_done: list[str]
    open_question: str
    sentiment: Literal["calm", "frustrated", "distressed"]
    vulnerability_flag: bool
    do_not_repeat: list[str]


class HandoffCard(BaseModel):
    queue: str
    reason: str
    summary: (
        Summary | None
    )  # None when the agent never handled the contact (kill switch, traffic dial)
    customer_text: str


async def card(queue: str, reason: str, text: str, facts: dict, gw: Gateway | None) -> HandoffCard:
    """Build the card; `gw=None` means no model call is allowed for this contact."""
    if gw is None:
        return HandoffCard(queue=queue, reason=reason, summary=None, customer_text=text)
    system = (ROOT / "prompts" / "handoff.md").read_text(encoding="utf-8")
    user = f"<conversation>{text}</conversation>\n<facts>{facts}</facts>"
    s = await gw.ask("writer", system, user, Summary)
    return HandoffCard(queue=queue, reason=reason, summary=s, customer_text=text)
