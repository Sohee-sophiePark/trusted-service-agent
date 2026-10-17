import { Light, Panel } from "../components/Status";
import { pct } from "../lib/format";
import type { EvalReport } from "../lib/types";

const ROWS: [keyof EvalReport, string, string][] = [
  ["routing_accuracy", "Routing accuracy", "≥ 92%"], ["escalation_precision", "Escalation precision", ""],
  ["escalation_recall", "Escalation recall", ""], ["golden_set_accuracy", "Golden-set accuracy", "≥ 90%"],
  ["groundedness", "Groundedness", "≥ 95%"], ["citation_accuracy", "Citation accuracy", ""], ["answered_share", "Answered (rest handed off)", ""],
];

export default function Evaluation({ r }: { r: EvalReport | null }) {
  if (!r) return <p className="text-muted">No release check has been run yet.</p>;
  return (
    <div className="space-y-3">
      <Panel title="Release check" kicker={`gate phase_1_to_2 (automated thresholds) · ${r.routing_cases} routing · ${r.golden_cases} golden cases · every change must pass before release`}>
        <div className="rounded-md border-2 border-bad/60 bg-bad/10 p-3">
          <div className="text-xs font-semibold uppercase tracking-widest text-bad">False containment rate — the dangerous one</div>
          <div className={`num text-3xl font-semibold ${r.gate.false_containment_rate ? "text-ink" : "text-bad"}`}>{pct(r.false_containment_rate, 1)}</div>
          <div className="text-xs text-muted">kept a case it should have escalated · limit 2% · <Light ok={r.gate.false_containment_rate} /></div>
        </div>
        <table className="mt-3 w-full text-sm">
          <tbody>
            {ROWS.map(([k, label, t]) => (
              <tr key={k} className="border-t border-line">
                <td className="py-1.5">{label}</td><td className="num text-right">{pct(r[k] as number, 1)}</td>
                <td className="w-20 text-right text-xs text-muted">{t}</td><td className="w-20 text-right">{k in r.gate ? <Light ok={r.gate[k]} /> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-3 flex items-center gap-2 text-sm">Overall <Light ok={r.pass} label={r.pass ? "PASS" : "FAIL"} />
          <span className="text-xs text-muted">A failed check blocks the release. In production, subject-matter experts sign off the golden set.</span></div>
      </Panel>
      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="Routing set" kicker="question → destination">
          <div className="max-h-96 overflow-y-auto"><table className="w-full text-xs"><tbody>
            {r.routing_rows.map((x) => (
              <tr key={x.q} className="border-t border-line align-top"><td className="py-1 pr-2">{x.q}</td><td className="num text-muted">{x.expect}</td>
                <td className="num">{x.ok ? <Light ok /> : <span className="text-bad">■ {x.got}</span>}</td></tr>))}
          </tbody></table></div>
        </Panel>
        <Panel title="Golden set" kicker="question → answer → the source it must come from">
          <div className="max-h-96 overflow-y-auto"><table className="w-full text-xs"><tbody>
            {r.golden_rows.map((x) => (
              <tr key={x.q} className="border-t border-line align-top"><td className="py-1 pr-2">{x.q}</td>
                <td>{x.answered ? <Light ok={x.source_ok && x.facts_ok} label={x.source_ok && x.facts_ok ? "correct" : !x.source_ok ? "wrong source" : "missing fact"} /> : <Light ok={null} label="handed off" />}</td></tr>))}
          </tbody></table></div>
        </Panel>
      </div>
    </div>
  );
}
