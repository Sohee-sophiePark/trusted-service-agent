export interface Week {
  week: number; traffic_share: number; agent_contacts: number; vrr: number;
  csat_agent: number; csat_control: number; escalation_rate: number; false_containment: number;
  sampled_accuracy: number; groundedness: number; escalation_handle_time_delta: number;
  compliance_incidents: number; billing_repeat_7d: number;
}
export interface Ops {
  label: string; weekly: Week[]; cprc_monthly: { month: number; agent: number; control: number }[];
  intents: { slice: string; topic: string | null; vrr: number | null; escalation: number; false_containment: number }[];
}
export interface EvalReport {
  false_containment_rate: number; routing_accuracy: number; escalation_precision: number; escalation_recall: number;
  golden_set_accuracy: number; groundedness: number; citation_accuracy: number; answered_share: number;
  routing_cases: number; golden_cases: number; gate: Record<string, boolean>; pass: boolean;
  routing_rows: { q: string; expect: string; got: string; ok: boolean }[];
  golden_rows: { q: string; answered: boolean; source_ok: boolean; facts_ok: boolean; quote_verified: boolean }[];
}
export interface Today {
  contacts: number; agent_contacts: number; resolved: number; handoffs: number; never_do_handoffs: number;
  escalation_rate: number | null; to_humans_by_control: number; model_calls: number;
}
export interface Dashboard { ops: Ops; eval: EvalReport | null; today: Today }
export interface QueuedCard extends Card { ts: string; contact_id: string }
export interface Recent { ts: string; contact_id: string; outcome: string; topic: string | null; queue: string | null; reason: string | null; model_calls: number; cited: boolean }
export interface Summary { customer_goal: string; already_done: string[]; open_question: string; sentiment: string; vulnerability_flag: boolean; do_not_repeat: string[] }
export interface Card { queue: string; reason: string; summary: Summary | null; customer_text: string }
export interface Citation { id: string; title: string; heading: string; effective: string; quote: string }
export interface Turn { outcome: "resolved" | "handoff" | "identity_requested"; topic: string | null; answer: string | null; citation: Citation | null; card: Card | null; model_calls: number }
export interface Control { kill_switch: boolean; traffic_share: number; topics: Record<string, boolean> }
export interface Overview {
  tickets: { id: string; kind: string; status: string; window: string }[];
  outages: { service: string; restore: string }[];
  bill: { plan: string; autopay: boolean; issued: string; total: number; status: string; due: number } | null;
}
