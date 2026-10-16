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
                "phase": "3 · widen" if widened else "2 · controlled live",
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
        "label": "Simulated operations — fictional company and data, for demonstration",
        "go_live": "Week 7 of the engagement",
        "target_window": "90 days after go-live",
        "readiness": [
            {
                "check": "Ownership",
                "finding": "Data owner and policy owner named; case-note use approved",
                "status": "pass",
            },
            {
                "check": "PII",
                "finding": "Transcripts partially redacted → used for mining and tests only",
                "status": "pass_with_limit",
            },
            {
                "check": "Freshness",
                "finding": "Field status lands hourly → answers show 'last updated'",
                "status": "pass_with_limit",
            },
            {
                "check": "Approved versions",
                "finding": "~30% of policy docs outdated → MVP uses 8 approved docs",
                "status": "pass_with_limit",
            },
        ],
        "phases": [
            {
                "id": "baseline",
                "name": "Discovery & sign-off",
                "when": "Week 1",
                "passed": True,
                "evidence": {"scope_and_kpis_signed": "yes", "approval_map": "yes"},
            },
            {
                "id": "readiness",
                "name": "Readiness & golden set",
                "when": "Weeks 2–3",
                "passed": True,
                "evidence": {"golden_set_signed": "yes", "readiness_checks": "4/4"},
            },
            {
                "id": "phase1",
                "name": "1 · Agent-assist",
                "when": "Weeks 4–6",
                "passed": True,
                "gate": {
                    "draft_acceptance_rate": [0.82, ">=", 0.75],
                    "golden_set_accuracy": [0.93, ">=", 0.90],
                    "groundedness": [0.97, ">=", 0.95],
                    "routing_accuracy": [0.95, ">=", 0.92],
                    "false_containment_rate": [0.012, "<=", 0.02],
                    "sme_signoff": ["yes", "==", "yes"],
                },
            },
            {
                "id": "phase2",
                "name": "2 · Controlled live",
                "when": "Weeks 7–8 go-live",
                "passed": True,
                "gate": {
                    "verified_resolution_rate": [0.34, ">=", 0.30],
                    "csat_vs_control": [0.02, ">=", 0.0],
                    "cost_per_resolved_contact_delta": [-0.21, "<=", -0.15],
                    "compliance_incidents": [0, "==", 0],
                    "escalation_handle_time_delta": [-0.14, "<=", 0.0],
                    "min_contacts_observed": [2400, ">=", 2000],
                },
            },
            {
                "id": "phase3",
                "name": "3 · Widen",
                "when": "To +90 days",
                "passed": True,
                "evidence": {
                    "in_scope_chat_share": "100%",
                    "billing_repeat_7d": "27% → 19%",
                    "peak_abandonment": "11% → 6%",
                },
            },
        ],
        "weekly": weekly(rng),
        "cprc_monthly": monthly_cprc(),
        "intents": [
            {
                "slice": "Ticket & outage status",
                "topic": "ticket_status",
                "vrr": 0.46,
                "escalation": 0.41,
                "false_containment": 0.008,
                "decision": "Widen to voice next",
            },
            {
                "slice": "Balance, due date, last payment",
                "topic": "account_questions",
                "vrr": 0.38,
                "escalation": 0.55,
                "false_containment": 0.011,
                "decision": "Hold scope; add statement copy",
            },
            {
                "slice": "Plan & policy how-to",
                "topic": "product_guidance",
                "vrr": 0.29,
                "escalation": 0.63,
                "false_containment": 0.014,
                "decision": "Hold; expand approved docs first",
            },
            {
                "slice": "Why did my bill go up",
                "topic": None,
                "vrr": None,
                "escalation": 1.0,
                "false_containment": 0.0,
                "decision": "Out of MVP (fails 'Solved'); rewrite the explanation policy",
            },
        ],
        "review_log": [
            {
                "week": 2,
                "type": "golden_case",
                "detail": "12 escalations about roaming caps added to the golden set",
            },
            {
                "week": 3,
                "type": "topic_edit",
                "detail": "'Outage credit' questions moved from ticket_status to product_guidance",
            },
            {
                "week": 6,
                "type": "retrieval_miss",
                "detail": "New plan prices (campaign) not in the index; sampled accuracy 91%",
            },
            {
                "week": 7,
                "type": "hypercare",
                "detail": "Plans policy re-approved and re-indexed; accuracy back to 96%",
            },
            {
                "week": 9,
                "type": "golden_case",
                "detail": "Bereavement phrasings from escalations added to never-do signals",
            },
            {
                "week": 12,
                "type": "topic_edit",
                "detail": "Ticket answers now include 'last updated' for every status",
            },
        ],
        "releases": [
            {
                "version": "1.0",
                "week": 0,
                "change": "Go-live on 10% of in-scope chat",
                "pass": True,
                "eval": {
                    "routing_accuracy": 0.95,
                    "golden_set_accuracy": 0.93,
                    "false_containment_rate": 0.012,
                },
            },
            {
                "version": "1.1",
                "week": 3,
                "change": "Outage-credit routing; 12 roaming golden cases",
                "pass": True,
                "eval": {
                    "routing_accuracy": 0.96,
                    "golden_set_accuracy": 0.94,
                    "false_containment_rate": 0.010,
                },
            },
            {
                "version": "1.2-rc",
                "week": 6,
                "change": "Shorter router prompt",
                "pass": False,
                "eval": {
                    "routing_accuracy": 0.95,
                    "golden_set_accuracy": 0.93,
                    "false_containment_rate": 0.024,
                },
                "note": "Blocked: false containment above 2%",
            },
            {
                "version": "1.2",
                "week": 7,
                "change": "Prompt reverted; plans policy re-indexed",
                "pass": True,
                "eval": {
                    "routing_accuracy": 0.96,
                    "golden_set_accuracy": 0.95,
                    "false_containment_rate": 0.011,
                },
            },
            {
                "version": "1.3",
                "week": 9,
                "change": "New bereavement signals from escalations",
                "pass": True,
                "eval": {
                    "routing_accuracy": 0.97,
                    "golden_set_accuracy": 0.95,
                    "false_containment_rate": 0.008,
                },
            },
        ],
    }


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1))
    print("wrote", OUT)
