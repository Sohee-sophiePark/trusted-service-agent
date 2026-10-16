"""Route a message: never-do signals in code first (no model call), then the model picks a topic."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from trusted_service_agent.llm.gateway import Gateway
from trusted_service_agent.paths import CONFIG, ROOT

TOPICS = ("account_questions", "ticket_status", "product_guidance")


class Classification(BaseModel):
    destination: Literal["account_questions", "ticket_status", "product_guidance", "out_of_scope"]
    confidence: float = Field(ge=0, le=1)


@dataclass(frozen=True)
class Route:
    topic: str | None  # None means hand off
    queue: str | None
    reason: str  # never-do id, "low_confidence", "out_of_scope" or "in_scope"
    confidence: float | None = None


@lru_cache
def never_do() -> list[dict]:
    return yaml.safe_load((CONFIG / "out_of_scope.yaml").read_text(encoding="utf-8"))[
        "out_of_scope"
    ]


def rule_hit(text: str) -> dict | None:
    """First never-do entry with a signal in the message; any hit hands off."""
    low = " ".join(text.lower().split())
    return next((e for e in never_do() if any(s in low for s in e["signals"])), None)


async def route(text: str, gw: Gateway) -> Route:
    if hit := rule_hit(text):
        return Route(None, hit["handoff_queue"], hit["id"])
    system = (ROOT / "prompts" / "router.md").read_text(encoding="utf-8")
    c = await gw.ask("router", system, f"<message>{text}</message>", Classification)
    if c.destination == "out_of_scope":
        return Route(None, "servicing", "out_of_scope", c.confidence)
    if c.confidence < gw.settings.router["low_confidence_threshold"]:
        return Route(None, "servicing", "low_confidence", c.confidence)
    return Route(c.destination, None, "in_scope", c.confidence)
