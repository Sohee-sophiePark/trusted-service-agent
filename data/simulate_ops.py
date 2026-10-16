"""Write data/ops/simulated_ops.json: fictional post-go-live operations for the dashboard (seeded, labelled)."""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ops" / "simulated_ops.json"


def weekly(rng: random.Random) -> list[dict]:
    """13 weeks after go-live: weeks 1–4 at 10% of in-scope chat, widened from week 5 (phase 3)."""
    rows = []
    for w in range(1, 14):
        widened = w >= 5
        drift = w == 6  # plan catalogue changed with the campaign; re-indexed in week 7
        contacts = rng.randint(24000, 26500) if widened else rng.randint(2300, 2700)
        rows.append(
            {
                "week": w,
                "traffic_share": 1.0 if widened else 0.10,
                "agent_contacts": contacts,
                "vrr": round(min(0.31 + 0.004 * w + rng.uniform(-0.008, 0.008), 0.37), 3),
                "csat_agent": round(0.77 + 0.002 * w + rng.uniform(-0.01, 0.01), 3),
                "csat_control": round(0.76 + rng.uniform(-0.01, 0.01), 3),
                "escalation_rate": round(0.58 - 0.005 * w + rng.uniform(-0.01, 0.01), 3),
                "false_containment": round(
                    (0.017 if drift else 0.011) + rng.uniform(-0.002, 0.002), 4
                ),
                "sampled_accuracy": round((0.91 if drift else 0.955) + rng.uniform(-0.01, 0.01), 3),
                "groundedness": round((0.94 if drift else 0.975) + rng.uniform(-0.005, 0.005), 3),
                "escalation_handle_time_delta": round(
                    -0.12 - 0.003 * w + rng.uniform(-0.01, 0.01), 3
                ),
                "compliance_incidents": 0,
                "billing_repeat_7d": round(max(0.27 - 0.007 * w, 0.19), 3),
            }
        )
    return rows


def monthly_cprc() -> list[dict]:
    """Cost per resolved contact, monthly (human control: chat cost ÷ first-contact resolution)."""
    return [{"month": m, "agent": a, "control": 4.43} for m, a in [(1, 3.62), (2, 3.50), (3, 3.41)]]


def build() -> dict:
    rng = random.Random(18)
    return {
        "label": "Simulated operations history — fictional company and data, for demonstration",
        "weekly": weekly(rng),
        "cprc_monthly": monthly_cprc(),
        "intents": [
            {
                "slice": "Ticket & outage status",
                "topic": "ticket_status",
                "vrr": 0.46,
                "escalation": 0.41,
                "false_containment": 0.008,
            },
            {
                "slice": "Balance, due date, last payment",
                "topic": "account_questions",
                "vrr": 0.38,
                "escalation": 0.55,
                "false_containment": 0.011,
            },
            {
                "slice": "Plan & policy how-to",
                "topic": "product_guidance",
                "vrr": 0.29,
                "escalation": 0.63,
                "false_containment": 0.014,
            },
            {
                "slice": "Why did my bill go up",
                "topic": None,
                "vrr": None,
                "escalation": 1.0,
                "false_containment": 0.0,
            },
        ],
    }


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1))
    print("wrote", OUT)
