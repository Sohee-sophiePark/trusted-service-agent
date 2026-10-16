"""Local live API: chat turns, identity check, control plane switches, dashboard data."""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from trusted_service_agent import agent, control, identity, metrics, telemetry
from trusted_service_agent.config import settings
from trusted_service_agent.identity import Session
from trusted_service_agent.llm.gateway import Gateway
from trusted_service_agent.llm.limiter import RateLimiter
from trusted_service_agent.paths import DATA, ROOT
from trusted_service_agent.warehouse import Warehouse

app = FastAPI(title="Trusted Service Agent")
wh = Warehouse()
sessions: dict[str, Session] = {}


def gateway() -> Gateway:
    s = settings()
    from trusted_service_agent.llm.gemini import GeminiClient

    return Gateway(s, GeminiClient(), RateLimiter(s.rate_limits, s.retry, s.timeout_seconds))


gw = gateway() if settings().run_mode == "live" else None


class ChatIn(BaseModel):
    session_id: str
    text: str = Field(max_length=1000)


class VerifyIn(BaseModel):
    session_id: str
    account_number: str = Field(max_length=20)
    postal_code: str = Field(max_length=10)


class ControlIn(BaseModel):
    kill_switch: bool
    traffic_share: float = Field(ge=0, le=1)
    topics: dict[str, bool]


@app.get("/api/session")
def new_session() -> dict:
    """A console session from the admitted cohort: it stays with the agent down to a 5% dial."""
    sid = uuid.uuid4().hex
    while control.bucket(sid) >= 0.05:
        sid = uuid.uuid4().hex
    return {"session_id": sid}


@app.post("/api/chat")
async def chat(body: ChatIn) -> dict:
    session = sessions.get(body.session_id, Session())
    t = await agent.turn(body.session_id, body.text, session, wh, gw)
    return {**t.__dict__, "card": t.card.model_dump() if t.card else None}


@app.post("/api/verify")
def verify(body: VerifyIn) -> dict:
    s = identity.verify(wh, body.account_number, body.postal_code)
    sessions[body.session_id] = s
    return {"verified": bool(s.account_number)}


@app.get("/api/control")
def get_control() -> dict:
    return control.load()


@app.put("/api/control")
def put_control(body: ControlIn) -> dict:
    cfg = control.load() | body.model_dump()
    control.save(cfg)
    return cfg


@app.get("/api/dashboard")
def dashboard() -> dict:
    """Operator console data: simulated performance history, eval release check, today's tiles."""
    report = ROOT / "eval" / "report.json"
    return {
        "ops": json.loads((DATA / "ops" / "simulated_ops.json").read_text()),
        "eval": json.loads(report.read_text()) if report.exists() else None,
        "today": metrics.today(),
    }


def _tail(path: Path, n: int) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines()[-n:]] if path.exists() else []


@app.get("/api/queue")
def queue() -> list[dict]:
    """Handoff cards for human agents, newest first."""
    return _tail(telemetry.SINK.with_name("queue.jsonl"), 50)[::-1]


@app.get("/api/recent")
def recent() -> list[dict]:
    """Latest turn outcomes (no customer text), newest first."""
    return _tail(telemetry.SINK, 50)[::-1]
