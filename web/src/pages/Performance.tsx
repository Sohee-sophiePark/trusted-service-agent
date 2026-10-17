import { Bar, BarChart, CartesianGrid, LabelList, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Light, Panel } from "../components/Status";
import { money, pct, signedPct } from "../lib/format";
import type { Dashboard, Today, Week } from "../lib/types";

const AXIS = { stroke: "#9AA1AC", fontSize: 11, tickLine: false, axisLine: { stroke: "#2E333D" } };
const GRID = <CartesianGrid stroke="#2E333D" strokeDasharray="2 4" vertical={false} />;
const TIP = { contentStyle: { background: "#252932", border: "1px solid #2E333D", borderRadius: 6, color: "#E6E8EB", fontSize: 12 }, cursor: { stroke: "#9AA1AC", strokeWidth: 1 } };
const endLabel = (name: string, n: number) => (p: { x?: number | string; y?: number | string; index?: number }) =>
  p.index === n - 1 ? <text x={Number(p.x) + 6} y={Number(p.y) + 4} fill="#E6E8EB" fontSize={10}>{name}</text> : null;
const LINE = { strokeWidth: 2, dot: { r: 4, strokeWidth: 2, stroke: "#1C1F26" }, activeDot: { r: 6 }, isAnimationActive: false } as const;

const TODAY_KICKER = import.meta.env.VITE_STATIC ? "recorded demo session · this system's own telemetry, not simulated" : "live telemetry · today · not simulated";

function TodayStrip({ t }: { t: Today }) {
  const cells: [string, string][] = [
    ["Contacts", String(t.contacts)],
    ["Agent-handled", String(t.agent_contacts)],
    ["Resolved", String(t.resolved)],
    ["Handoffs (never-do)", `${t.handoffs} (${t.never_do_handoffs})`],
    ["Escalation rate", t.escalation_rate == null ? "—" : pct(t.escalation_rate)],
    ["To humans by control", String(t.to_humans_by_control)],
    ["Model calls", String(t.model_calls)],
  ];
  return (
    <Panel title="Today" kicker={TODAY_KICKER}>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs md:grid-cols-4 xl:grid-cols-7">
        {cells.map(([k, v]) => (
          <div key={k}><dt className="text-muted">{k}</dt><dd className="num text-lg font-semibold text-ink">{v}</dd></div>
        ))}
      </dl>
    </Panel>
  );
}

function Tiles({ d }: { d: Dashboard }) {
  const last = d.ops.weekly.at(-1) as Week;
  const cprc = d.ops.cprc_monthly.at(-1)!;
  const incidents = d.ops.weekly.reduce((a, w) => a + w.compliance_incidents, 0);
  const tiles: { k: string; v: string; sub: string; ok: boolean }[] = [
    { k: "Verified resolution", v: pct(last.vrr), sub: "absolute · target 30%", ok: last.vrr >= 0.3 },
    { k: "Cost per resolved contact", v: money(cprc.agent), sub: `vs control ${money(cprc.control)} (${signedPct(cprc.agent / cprc.control - 1)})`, ok: cprc.agent < cprc.control },
    { k: "CSAT (% scoring 4–5)", v: pct(last.csat_agent), sub: `vs control ${pct(last.csat_control)}`, ok: last.csat_agent >= last.csat_control },
    { k: "Escalation rate", v: pct(last.escalation_rate), sub: "handoffs ÷ agent contacts", ok: true },
    { k: "False containment", v: pct(last.false_containment, 1), sub: "kept what it should have escalated · max 2%", ok: last.false_containment <= 0.02 },
    { k: "Compliance incidents", v: String(incidents), sub: "absolute · one → operator pauses via kill switch", ok: incidents === 0 },
  ];
  return (
    <section aria-label="Key measures" className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
      {tiles.map((t) => (
        <div key={t.k} className="rounded-lg border border-line bg-panel p-3">
          <div className="flex items-start justify-between gap-1"><span className="text-xs text-muted">{t.k}</span><Light ok={t.ok} label={t.ok ? "on track" : "watch"} /></div>
          <div className="num mt-1 text-2xl font-semibold text-signal">{t.v}</div>
          <div className="mt-0.5 text-[11px] text-muted">{t.sub}</div>
        </div>
      ))}
    </section>
  );
}

function Trends({ d }: { d: Dashboard }) {
  const w = d.ops.weekly.map((x) => ({ ...x, label: `W${x.week}` }));
  return (
    <Panel title="Trends" kicker="13 weeks · weekly (VRR with a 7-day lag) · cost monthly · simulated history">
      <div className="grid gap-4 lg:grid-cols-3">
        <figure>
          <figcaption className="mb-1 text-xs text-muted">Verified resolution rate (absolute)</figcaption>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={w} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
              {GRID}<XAxis dataKey="label" {...AXIS} /><YAxis {...AXIS} domain={[0.25, 0.4]} tickFormatter={(v) => pct(v)} />
              <Tooltip {...TIP} formatter={(v) => pct(Number(v), 1)} />
              <ReferenceLine y={0.3} stroke="#9AA1AC" strokeDasharray="4 4" label={{ value: "target 30%", fill: "#9AA1AC", fontSize: 10, position: "insideBottomRight" }} />
              <ReferenceLine x="W5" stroke="#2E333D" label={{ value: "widen", fill: "#9AA1AC", fontSize: 10, position: "insideTopLeft" }} />
              <Line dataKey="vrr" name="Agent" stroke="var(--color-agent)" fill="var(--color-agent)" {...LINE} />
            </LineChart>
          </ResponsiveContainer>
        </figure>
        <figure>
          <figcaption className="mb-1 text-xs text-muted">CSAT, % scoring 4–5 — agent vs human control</figcaption>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={w} margin={{ top: 8, right: 44, left: -16, bottom: 0 }}>
              {GRID}<XAxis dataKey="label" {...AXIS} /><YAxis {...AXIS} domain={[0.7, 0.85]} tickFormatter={(v) => pct(v)} />
              <Tooltip {...TIP} formatter={(v) => pct(Number(v), 1)} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#9AA1AC" }} />
              <Line dataKey="csat_agent" name="Agent" stroke="var(--color-agent)" fill="var(--color-agent)" {...LINE}><LabelList content={endLabel("Agent", w.length)} /></Line>
              <Line dataKey="csat_control" name="Control" stroke="var(--color-control)" fill="var(--color-control)" {...LINE}><LabelList content={endLabel("Control", w.length)} /></Line>
            </LineChart>
          </ResponsiveContainer>
        </figure>
        <figure>
          <figcaption className="mb-1 text-xs text-muted">Cost per resolved contact, monthly — agent vs control</figcaption>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={d.ops.cprc_monthly.map((m) => ({ ...m, label: `M${m.month}` }))} margin={{ top: 8, right: 12, left: -10, bottom: 0 }} barGap={2}>
              {GRID}<XAxis dataKey="label" {...AXIS} /><YAxis {...AXIS} tickFormatter={(v) => `$${v}`} />
              <Tooltip {...TIP} cursor={{ fill: "#252932" }} formatter={(v) => money(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#9AA1AC" }} />
              <Bar dataKey="agent" name="Agent" fill="var(--color-agent)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="control" name="Control" fill="var(--color-control)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </figure>
      </div>
    </Panel>
  );
}

function Guardrails({ d }: { d: Dashboard }) {
  const w = d.ops.weekly.map((x) => ({ ...x, label: `W${x.week}` }));
  const small = (key: keyof Week, title: string, limit: number, dom: [number, number], ticks: number[], d1 = 0) => (
    <figure key={key}>
      <figcaption className="mb-1 text-xs text-muted">{title}</figcaption>
      <ResponsiveContainer width="100%" height={130}>
        <LineChart data={w} margin={{ top: 6, right: 10, left: -16, bottom: 0 }}>
          {GRID}<XAxis dataKey="label" {...AXIS} interval={2} /><YAxis {...AXIS} domain={dom} ticks={ticks} tickFormatter={(v) => pct(v, d1)} />
          <Tooltip {...TIP} formatter={(v) => pct(Number(v), 1)} />
          <ReferenceLine y={limit} stroke="#9AA1AC" strokeDasharray="4 4" />
          <Line dataKey={key} name={title} stroke="var(--color-agent)" fill="var(--color-agent)" {...LINE} dot={{ r: 3, strokeWidth: 1.5, stroke: "#1C1F26" }} />
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
  const last = d.ops.weekly.at(-1)!;
  const incidents = d.ops.weekly.reduce((a, w) => a + w.compliance_incidents, 0);
  return (
    <Panel title="Guardrails" kicker="dashed line = limit · simulated history">
      <div className="grid gap-4 md:grid-cols-3">
        {small("sampled_accuracy", "Weekly sampled accuracy (≥ 95%)", 0.95, [0.85, 1], [0.85, 0.9, 0.95, 1])}
        {small("groundedness", "Groundedness (≥ 95%)", 0.95, [0.9, 1], [0.9, 0.95, 1])}
        {small("false_containment", "False containment (≤ 2%)", 0.02, [0, 0.03], [0, 0.01, 0.02, 0.03], 1)}
      </div>
      <p className="mt-3 text-xs text-muted">
        Escalation handle time <span className="num text-ink">{signedPct(last.escalation_handle_time_delta)}</span> vs today ·
        compliance incidents <span className="num text-ink">{incidents}</span> (any incident: operator pauses via the kill switch) · week 6 dip: new plan prices were missing from the index, re-indexed in week 7.
      </p>
    </Panel>
  );
}

function Intents({ d }: { d: Dashboard }) {
  return (
    <Panel title="By intent" kicker="simulated history">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="text-left text-muted"><tr><th className="py-1 pr-2">Slice</th><th>VRR</th><th>Escalation</th><th>False containment</th></tr></thead>
          <tbody>
            {d.ops.intents.map((i) => (
              <tr key={i.slice} className="border-t border-line">
                <td className="py-1.5 pr-2">{i.slice}</td><td className="num">{pct(i.vrr)}</td><td className="num">{pct(i.escalation)}</td>
                <td className="num">{pct(i.false_containment, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export default function Performance({ d }: { d: Dashboard }) {
  return (
    <div className="space-y-3">
      <TodayStrip t={d.today} />
      <p className="text-xs text-muted">{d.ops.label}</p>
      <Tiles d={d} />
      <Trends d={d} />
      <div className="grid gap-3 xl:grid-cols-2"><Guardrails d={d} /><Intents d={d} /></div>
    </div>
  );
}
