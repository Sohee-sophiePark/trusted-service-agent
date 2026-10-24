import { useEffect, useMemo, useState } from "react";
import { Light, Panel } from "../components/Status";
import { QUEUE_LABEL, REASON_LABEL, pct } from "../lib/format";
import { source, surveys } from "../lib/source";
import type { Control, QueuedCard, Recent } from "../lib/types";

export const TOPIC_LABEL: Record<string, string> = { account_questions: "Account questions", ticket_status: "Ticket & outage status", product_guidance: "Product guidance" };

/** Evenly spread 0–1 value for simulated contact i: any dial share is met to within one contact. */
const spread = (i: number) => (i * 0.6180339887498949) % 1;

function Controls({ ctl, set }: { ctl: Control; set: (c: Control) => void }) {
  return (
    <Panel title="Control plane" kicker="read before every customer turn">
      <div className="space-y-4">
        <label className="flex items-center justify-between gap-3">
          <span><span className="block text-sm font-semibold">Kill switch</span><span className="block text-xs text-muted">Layer 3 · everything to human agents, no model call</span></span>
          <button role="switch" aria-label="Kill switch" aria-checked={ctl.kill_switch} onClick={() => set({ ...ctl, kill_switch: !ctl.kill_switch })}
            className={`h-9 w-20 rounded-md border-2 font-mono text-xs font-semibold ${ctl.kill_switch ? "border-bad bg-bad/20 text-bad" : "border-line bg-panel-2 text-muted hover:border-muted hover:text-ink"}`}>
            {ctl.kill_switch ? "■ ON" : "○ OFF"}
          </button>
        </label>
        <label className="block">
          <span className="flex justify-between text-sm font-semibold">Traffic dial <span className="num text-signal">{pct(ctl.traffic_share)}</span></span>
          <span className="text-xs text-muted">Layer 2 · share of contacts the agent handles</span>
          <input type="range" min={0} max={1} step={0.05} value={ctl.traffic_share} aria-label="Traffic share"
            onChange={(e) => set({ ...ctl, traffic_share: Number(e.target.value) })} className="mt-1 w-full accent-[#F5B83D]" />
        </label>
        <fieldset>
          <legend className="text-sm font-semibold">Topics <span className="text-xs font-normal text-muted">· layer 1 · narrow the scope</span></legend>
          {Object.entries(ctl.topics).map(([t, on]) => (
            <label key={t} className="mt-1 flex items-center justify-between text-sm">
              {TOPIC_LABEL[t]}
              <input type="checkbox" aria-label={TOPIC_LABEL[t]} checked={on} onChange={() => set({ ...ctl, topics: { ...ctl.topics, [t]: !on } })} className="h-4 w-4 accent-[#F5B83D]" />
            </label>
          ))}
        </fieldset>
      </div>
    </Panel>
  );
}

function Incoming({ ctl }: { ctl: Control }) {
  const n = 1000;
  const agent = useMemo(() => (ctl.kill_switch ? 0 : Array.from({ length: n }, (_, i) => spread(i)).filter((b) => b < ctl.traffic_share).length), [ctl]);
  return (
    <Panel title="Incoming contacts" kicker="simulated batch of 1,000 · moves with the dial">
      <div className="grid grid-cols-2 gap-2 text-center">
        <div className="rounded border border-line p-2"><div className="num text-2xl text-agent">{agent}</div><div className="text-xs text-muted">to the agent</div></div>
        <div className="rounded border border-line p-2"><div className="num text-2xl text-control">{n - agent}</div><div className="text-xs text-muted">to human agents</div></div>
      </div>
    </Panel>
  );
}

function Queue({ cards }: { cards: QueuedCard[] }) {
  return (
    <Panel title="Human queue" kicker={`${cards.length} handoff${cards.length === 1 ? "" : "s"} · a refusal is a successful outcome`}>
      {cards.length ? (
        <ul className="space-y-2">
          {cards.map((c) => (
            <li key={c.ts + c.customer_text} className="rounded-md border border-line bg-panel-2 p-3 text-xs">
              <div className="flex items-center justify-between gap-2"><span className="font-semibold text-signal">{QUEUE_LABEL[c.queue] ?? c.queue} queue</span><span className="text-muted">{REASON_LABEL[c.reason] ?? c.reason}</span></div>
              <p className="mt-1 text-muted">“{c.customer_text}”</p>
              {c.summary ? (
                <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5">
                  <dt className="text-muted">Goal</dt><dd>{c.summary.customer_goal}</dd>
                  <dt className="text-muted">Done</dt><dd>{c.summary.already_done.join(" · ") || "—"}</dd>
                  <dt className="text-muted">To resolve</dt><dd>{c.summary.open_question}</dd>
                  <dt className="text-muted">Sentiment</dt><dd>{c.summary.sentiment}{c.summary.vulnerability_flag && <span className="ml-2 text-warn">◐ vulnerability flag</span>}</dd>
                  {c.summary.do_not_repeat.length > 0 && <><dt className="text-muted">Don't ask again</dt><dd>{c.summary.do_not_repeat.join(" · ")}</dd></>}
                </dl>
              ) : <p className="mt-2 text-muted">No summary: the agent never handled this contact.</p>}
            </li>
          ))}
        </ul>
      ) : <p className="text-xs text-muted">Handoffs from the customer chat appear here with their summary.</p>}
    </Panel>
  );
}

function RecentTurns({ rows, csat }: { rows: Recent[]; csat: { score: number }[] }) {
  const agent = rows.filter((r) => r.reason !== "kill_switch" && r.reason !== "traffic_share");
  const tiles = [
    ["Customer turns", String(rows.length)], ["Resolved by the agent", String(agent.filter((r) => r.outcome === "resolved").length)],
    ["Handed to human agents", String(rows.filter((r) => r.outcome === "handoff").length)], ["Model calls", String(rows.reduce((a, r) => a + r.model_calls, 0))],
    ["CSAT (4–5)", csat.length ? `${Math.round((100 * csat.filter((c) => c.score >= 4).length) / csat.length)}% of ${csat.length}` : "—"],
  ];
  return (
    <Panel title={source.live ? "Recent turns" : "Your demo session"} kicker={`${source.live ? "last 50 turns from the event log" : "your clicks in this browser only"} · refusals count as successes`}>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        {tiles.map(([k, v]) => <div key={k} className="rounded border border-line p-2"><div className="text-xs text-muted">{k}</div><div className="num text-xl font-semibold text-signal">{v}</div></div>)}
      </div>
      <table className="mt-3 w-full text-xs">
        <thead className="text-left text-muted"><tr><th className="py-1">Time</th><th>Outcome</th><th>Topic</th><th>Why</th><th className="text-right">Model calls</th></tr></thead>
        <tbody>
          {rows.slice(0, 12).map((r) => (
            <tr key={r.ts + r.contact_id + r.outcome} className="border-t border-line">
              <td className="num py-1 text-muted">{r.ts.slice(11, 19)}</td>
              <td><Light ok={r.outcome === "identity_requested" ? null : true} label={r.outcome === "handoff" ? "handed off" : r.outcome.replace("_", " ")} /></td>
              <td>{r.topic ? TOPIC_LABEL[r.topic] : "—"}</td><td className="text-muted">{r.reason ? REASON_LABEL[r.reason] ?? r.reason : r.cited ? "cited answer" : "lookup"}</td>
              <td className="num text-right">{r.model_calls}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

export default function Live() {
  const [ctl, setCtl] = useState<Control | null>(null);
  const [cards, setCards] = useState<QueuedCard[]>([]);
  const [rows, setRows] = useState<Recent[]>([]);
  const [csat, setCsat] = useState<{ score: number }[]>([]);
  useEffect(() => {
    const refresh = () => { source.control().then(setCtl); source.queue().then(setCards); source.recent().then(setRows); setCsat(surveys()); };
    refresh();
    const id = setInterval(refresh, 2000);
    window.addEventListener("storage", refresh);
    return () => { clearInterval(id); window.removeEventListener("storage", refresh); };
  }, []);
  const update = async (c: Control) => setCtl(await source.setControl(c));
  if (!ctl) return <p className="text-muted">Loading…</p>;
  return (
    <div className="grid gap-3 lg:grid-cols-[2fr_3fr]">
      <div className="space-y-3"><Controls ctl={ctl} set={update} /><Incoming ctl={ctl} /></div>
      <div className="space-y-3"><RecentTurns rows={rows} csat={csat} /><Queue cards={cards} /></div>
    </div>
  );
}
