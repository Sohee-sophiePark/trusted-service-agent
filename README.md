# Trusted Service Agent

A customer-servicing agent built as a **control surface, not a chatbot**. It knows what it must not do, answers only
from approved sources with a citation, and can be **turned down before it has to be turned off**.

**Live demo:** [customer chat](https://sohee-sophiepark.github.io/trusted-service-agent/) ·
[operator console](https://sohee-sophiepark.github.io/trusted-service-agent/console/)
(replays recorded conversations; no API key needed)

> Demo only. **Tessaline Communications** is a fictional mobile and home-internet provider. Every customer, account,
> ticket, policy and transcript is made up. The performance history in the console is simulated and labelled.

## What it does

Two surfaces, for two different people:

| Surface | Used by | What it shows |
|---|---|---|
| **Customer chat** (`index.html`) | The end customer | Three things only: account and bill questions, install/repair/outage status, and how plans and policies work. Everything else is a polite handoff to a person. |
| **Operator console** (`console/`) | The service owner in the contact centre | Kill switch, traffic dial and topic toggles · the human queue with a handoff summary for each case · today's outcomes · performance and guardrails · the release check |

## How a customer turn is decided

```
customer message
  │
  ▼
CONTROL PLANE ── kill switch on / outside the traffic dial ──► human queue   (no model call)
  │
  ▼
NEVER-DO RULES (code) ── dispute · complaint · account change · vulnerable · advice · injected instructions
  │                                                                      └──► human queue + summary
  ▼
ROUTER (model) ── out of scope or low confidence ─────────────────────────► human queue + summary
  │ one of three topics (each can be switched off)
  ├─ account questions ┐
  ├─ ticket status     ┴─ IDENTITY GATE (code) → read-only SQL lookup (no model) → answer
  └─ product guidance ── BM25 over approved policy sections → model quotes a sentence
                         → code checks the quote word for word → answer with citation
                           (no verified citation → no answer → human queue)
every turn ─► event log ─► operator console
```

**Design rules enforced in code**

| Rule | How |
|---|---|
| Control plane first | Read before routing on every turn; the kill switch makes zero model calls (tested) |
| No citation, no answer | The quoted sentence must appear verbatim in the cited policy section, or the agent hands off |
| Read-only | There is no write path: a test fails on any `INSERT/UPDATE/DELETE/CREATE` in the source; the warehouse opens read-only |
| Identity before account data | Lookups raise without a verified session (account number + service-address postal code) |
| Transcripts never answer customers | Used only to find contact reasons and build test sets; a test asserts they are unreachable from the answer path |
| A refusal is a success | Every turn, including handoffs, is logged and counted |
| Facts come from code | Balances, due dates, ticket windows and outage times are lookups, never generated |

## The never-do list

Risk draws the line: **R**egulatory · **M**oney · **V**ulnerable · **P**ublicity. Signals are matched in code before
any model call, and any hit hands off (`config/out_of_scope.yaml`).

| Case | Queue |
|---|---|
| Billing dispute or a charge the customer did not make | Disputes |
| Formal complaint | Complaints |
| Any change to the account, plan, payment or service | Servicing |
| Bereavement, hardship, distress or confusion (err toward handoff) | Specialist care |
| Plan-suitability advice | Advice |
| Instructions aimed at the agent instead of a request | Servicing |

## Three layers of rollback

| Layer | Control | Effect |
|---|---|---|
| 1 | Topic toggle | One topic goes to people; the rest keep working |
| 2 | Traffic dial | The share of contacts the agent handles (stable per contact) |
| 3 | Kill switch | Everything to people, no model call |

## Release check (evaluation)

Every change must pass `make eval` before release: the automated thresholds of the phase 1 → 2 gate in `config/thresholds.yaml`
(draft acceptance and SME sign-off in that gate are recorded by people, not by the script). Results on the recorded run:

| Measure | Result | Threshold |
|---|---|---|
| **False containment** (kept a case it should have escalated) | **0.0%** | ≤ 2% |
| Routing accuracy (42 cases) | 97.6% | ≥ 92% |
| Escalation precision / recall | 100% / 100% | — |
| Golden-set accuracy (30 cases: answer + exact source) | 100% | ≥ 90% |
| Groundedness / citation accuracy | 100% / 100% | ≥ 95% |

The one routing miss ("can I get a paper bill" sent to account questions) is kept as found. Demo sets are small;
production would use around 200 SME-signed cases. Models: free-tier Gemini, newest first with fallback on quota,
overload or timeout; the model that served each call is recorded.

## Measures the console reports

| Measure | Definition | Compared with |
|---|---|---|
| Verified resolution rate | Resolved by the agent, no handoff, no repeat contact within 7 days, passed sampled accuracy | Absolute target |
| Cost per resolved contact | (Agent cost + human minutes it still consumes) ÷ resolved contacts | Human control group |
| CSAT | % scoring 4–5 on the post-contact survey | Human control group |
| Guardrails | Sampled accuracy · groundedness · false containment · escalation handle time · compliance incidents (0) | Limits |

## How it would map to Salesforce

The demo has no Salesforce dependency. This is how each part would map onto the platform:

| Demo component | Salesforce equivalent |
|---|---|
| `agent.py` (one agent, one handler per topic) | One Agentforce Service agent, one topic (subagent) per intent, each with its own actions |
| `router.py` (topics + never-do list) | Agentforce topics and instructions |
| `actions.py` (read-only lookups) | Flow / MuleSoft actions |
| `warehouse.py` (Snowflake-style tables) | Data 360 with zero-copy access to Snowflake |
| `grounding.py` (approved sources, citations) | Knowledge grounding over approved articles |
| `identity.py` + control plane | Einstein Trust Layer, least-privilege agent user |
| `handoff.py` (summary for the human agent) | Omni-Channel transfer with a summary |
| `eval/run_eval.py` | Testing Center |
| Operator console metrics | Agentforce analytics and observability |

## Run it

```bash
make setup && make seed        # dependencies + fictional warehouse
make test                      # unit and end-to-end tests, no network
make eval                      # release check from recordings, no key
make dev-api                   # live mode on 127.0.0.1:8018 (needs GEMINI_API_KEY in .env, free tier)
make dev-web                   # customer chat on :5173, operator console on :5173/console/
make build-static              # the public replay build in web/dist
```

## Stack

Python 3.11 · FastAPI · DuckDB · rank-bm25 · google-genai (Gemini, free tier) · React · Vite · TypeScript ·
Tailwind CSS · Recharts · GitHub Actions · GitHub Pages

## Repository

```
config/      control plane, topics, never-do list, release thresholds, model settings
data/        warehouse seed (fictional), 8 approved policy documents, 30 redacted transcript snippets, simulated history
prompts/     router, grounding and handoff prompts
src/         control, router, identity, actions, grounding, handoff, telemetry, agent, API, export
eval/        routing set, golden set, release check
cassettes/   recorded model calls for replay (CI and the public demo)
web/         customer chat and operator console
```

Built with [Claude Code](https://claude.com/claude-code).
