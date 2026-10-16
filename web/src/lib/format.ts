export const pct = (v: number | null | undefined, d = 0) => (v == null ? "—" : `${(v * 100).toFixed(d)}%`);
export const signedPct = (v: number, d = 0) => `${v > 0 ? "+" : ""}${(v * 100).toFixed(d)}%`;
export const money = (v: number) => `$${v.toFixed(2)}`;
export const QUEUE_LABEL: Record<string, string> = {
  disputes: "Disputes", complaints: "Complaints", servicing: "Servicing", specialist: "Specialist care", advice: "Advice",
};
export const REASON_LABEL: Record<string, string> = {
  kill_switch: "Kill switch on — no model call", traffic_share: "Outside the traffic dial — no model call",
  topic_off: "Topic switched off", dispute: "Never-do: billing dispute", complaint: "Never-do: complaint",
  account_change: "Never-do: account change", vulnerable: "Never-do: vulnerable customer",
  advice: "Never-do: plan-suitability advice", unsafe_input: "Never-do: instructions aimed at the agent",
  out_of_scope: "Out of scope (MVP)", low_confidence: "Low routing confidence", no_citation: "No citation, no answer",
  no_open_ticket: "No open ticket found",
};
