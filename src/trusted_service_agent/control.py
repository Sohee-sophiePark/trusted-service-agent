"""Control plane: kill switch, traffic dial and topic toggles, re-read on every call."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from trusted_service_agent.paths import CONFIG

CONTROL_FILE = CONFIG / "control.yaml"


@dataclass(frozen=True)
class Admission:
    agent: bool
    reason: str  # "kill_switch" | "traffic_share" | "admitted"


def load(path: Path = CONTROL_FILE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def bucket(contact_id: str) -> float:
    """Stable value in [0, 1) per contact: it always lands on the same side of the dial."""
    return int(hashlib.sha256(contact_id.encode()).hexdigest()[:8], 16) / 0x100000000


def admit(contact_id: str, path: Path = CONTROL_FILE) -> Admission:
    """Decide before any routing or model call whether the agent may handle this contact."""
    cfg = load(path)
    if cfg["kill_switch"]:
        return Admission(False, "kill_switch")
    if bucket(contact_id) >= cfg["traffic_share"]:
        return Admission(False, "traffic_share")
    return Admission(True, "admitted")


def topic_enabled(topic: str, path: Path = CONTROL_FILE) -> bool:
    return bool(load(path)["topics"].get(topic, False))


def save(cfg: dict, path: Path = CONTROL_FILE) -> None:
    """Write the switches back with their explanations, so the file still reads as the policy."""
    t = cfg["topics"]
    path.write_text(
        "# Three layers of rollback. Read before every single turn.\n"
        f"kill_switch: {str(cfg['kill_switch']).lower()}          # layer 3 — everything to humans, no model call\n"
        f"traffic_share: {cfg['traffic_share']:.2f}         # layer 2 — fraction of contacts the agent handles\n"
        "topics:                     # layer 1 — narrow the scope\n"
        + "".join(f"  {k}: {str(v).lower()}\n" for k, v in t.items()),
        encoding="utf-8",
    )
