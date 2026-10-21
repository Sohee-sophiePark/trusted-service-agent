"""Score routing and golden sets through the pipeline; false containment first; PASS/FAIL."""

import asyncio
import json
import re
import sys

import yaml

from trusted_service_agent import grounding, router
from trusted_service_agent.config import settings
from trusted_service_agent.llm.cassette import CassetteClient
from trusted_service_agent.llm.gateway import Gateway
from trusted_service_agent.llm.limiter import RateLimiter
from trusted_service_agent.paths import CONFIG, ROOT

EVAL = ROOT / "eval"
CASSETTE = ROOT / "cassettes" / "eval.jsonl"
RED, GREEN, RESET = "\033[31m", "\033[32m", "\033[0m"


def gateway() -> Gateway:
    s = settings()
    if s.run_mode == "replay":
        client = CassetteClient(CASSETTE, "replay")
    else:
        from trusted_service_agent.llm.gemini import GeminiClient

        inner = GeminiClient()
        client = CassetteClient(CASSETTE, "record", inner) if s.run_mode == "record" else inner
    return Gateway(s, client, RateLimiter(s.rate_limits, s.retry, s.timeout_seconds))


async def score(gw: Gateway) -> dict:
    routing = json.loads((EVAL / "routing_set.json").read_text())
    golden = json.loads((EVAL / "golden_set.json").read_text())
    rows, kept_should_escalate = [], 0
    for c in routing:
        r = await router.route(c["q"], gw)
        got = r.topic or f"handoff:{r.queue}"
        exp_h, got_h = c["expect"].startswith("handoff"), r.topic is None
        kept_should_escalate += exp_h and not got_h
        rows.append(
            {
                "q": c["q"],
                "expect": c["expect"],
                "got": got,
                "ok": got == c["expect"],
                "expect_handoff": exp_h,
                "got_handoff": got_h,
            }
        )
    tp = sum(x["expect_handoff"] and x["got_handoff"] for x in rows)
    answers = []
    for c in golden:
        dr = await grounding.draft(c["q"], gw)
        g = grounding.gate(*dr) if dr else None
        cited = next((s for s in dr[1] if s.id == dr[0].section_id), None) if dr else None
        text = g.answer if g else ""
        answers.append(
            {
                "q": c["q"],
                "answered": g is not None,
                "source_ok": bool(g) and g.section.id == c["expect_source"],
                "facts_ok": bool(g)
                and all(
                    any(_has(text, alt) for alt in f.lower().split("|")) for f in c["must_include"]
                ),
                "drafted": bool(cited) and dr[0].supported,
                "grounded": bool(cited)
                and grounding.verified(dr[0].quote, cited)
                and grounding.numbers_supported(dr[0].answer, dr[1]),
            }
        )
    answered = [a for a in answers if a["answered"]]
    drafted = [a for a in answers if a["drafted"]]
    n_ans = max(len(answered), 1)
    return {
        "false_containment_rate": kept_should_escalate
        / max(sum(x["expect_handoff"] for x in rows), 1),
        "routing_accuracy": sum(x["ok"] for x in rows) / len(rows),
        "escalation_precision": tp / max(sum(x["got_handoff"] for x in rows), 1),
        "escalation_recall": tp / max(sum(x["expect_handoff"] for x in rows), 1),
        "golden_set_accuracy": sum(a["source_ok"] and a["facts_ok"] for a in answers)
        / len(answers),
        "groundedness": sum(a["grounded"] for a in drafted) / max(len(drafted), 1),
        "citation_accuracy": sum(a["source_ok"] for a in answered) / n_ans,
        "answered_share": len(answered) / len(answers),
        "routing_cases": len(rows),
        "golden_cases": len(answers),
        "routing_rows": rows,
        "golden_rows": answers,
    }


def _has(text: str, fact: str) -> bool:
    """Fact present on token boundaries, so "$2" does not match "$25"."""
    return re.search(rf"(?<![\w$.]){re.escape(fact)}(?![\d%])", text.lower()) is not None


def gate(m: dict) -> dict:
    """Release check: each evaluation threshold from thresholds.yaml (phase_1_to_2)."""
    t = yaml.safe_load((CONFIG / "thresholds.yaml").read_text())["phase_1_to_2"]
    return {
        "golden_set_accuracy": m["golden_set_accuracy"] >= t["golden_set_accuracy"],
        "groundedness": m["groundedness"] >= t["groundedness"],
        "routing_accuracy": m["routing_accuracy"] >= t["routing_accuracy"],
        "false_containment_rate": m["false_containment_rate"] <= t["false_containment_rate"],
    }


def main() -> int:
    gw = gateway()
    m = asyncio.run(score(gw))
    checks = gate(m)
    fc = m["false_containment_rate"]
    fc_mark = f"{GREEN}pass{RESET}" if checks["false_containment_rate"] else f"{RED}FAIL{RESET}"
    print(
        f"{RED}FALSE CONTAINMENT RATE  {fc:.1%}{RESET}  {fc_mark}  "
        "(kept a case it should have escalated · limit 2%)"
    )
    for k in (
        "routing_accuracy",
        "escalation_precision",
        "escalation_recall",
        "golden_set_accuracy",
        "groundedness",
        "citation_accuracy",
        "answered_share",
    ):
        mark = {True: f"{GREEN}pass{RESET}", False: f"{RED}FAIL{RESET}"}.get(checks.get(k), "")
        print(f"{k:24s}{m[k]:7.1%}  {mark}")
    ok = all(checks.values())
    calls_label = "recorded calls replayed" if settings().run_mode == "replay" else "model calls"
    print(
        f"\nRelease check, gate phase_1_to_2 (automated thresholds; draft acceptance and"
        f" SME sign-off are recorded by people): {GREEN + 'PASS' if ok else RED + 'FAIL'}{RESET}  "
        f"[{m['routing_cases']} routing · {m['golden_cases']} golden · "
        f"{calls_label} {gw.calls}]"
    )
    report = {k: v for k, v in m.items()} | {"gate": checks, "pass": ok, "model_calls": gw.calls}
    (EVAL / "report.json").write_text(json.dumps(report, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
