import { useEffect, useState } from "react";
import { source } from "../lib/source";
import type { Dashboard } from "../lib/types";
import Evaluation from "../pages/Evaluation";
import Performance from "../pages/Performance";
import Live from "./Live";

const TABS = ["Live", "Performance", "Release check"] as const;
type Tab = (typeof TABS)[number];

/** The client's service-owner console: run the agent, watch it, check releases. */
export default function ConsoleApp() {
  const [tab, setTab] = useState<Tab>("Live");
  const [d, setD] = useState<Dashboard | null>(null);
  useEffect(() => { source.dashboard().then(setD); }, [tab]);
  return (
    <div className="mx-auto max-w-7xl p-3 md:p-5">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
        <div>
          <h1 className="font-mono text-lg font-semibold tracking-widest text-signal">TRUSTED SERVICE AGENT</h1>
          <p className="text-xs text-muted">Operator console · Tessaline Communications (fictional) · turn it down before you have to turn it off</p>
        </div>
        <div className="flex items-center gap-2">
          <a href="../" target="_blank" className="rounded border border-line px-2 py-1 text-xs text-muted hover:text-ink">Open customer chat ↗</a>
          <span className="rounded border border-line px-2 py-1 font-mono text-xs text-muted">{source.live ? "● LIVE · laptop" : "◐ REPLAY · public demo"}</span>
        </div>
      </header>
      <nav className="mb-3 flex gap-1" aria-label="Sections">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} aria-current={tab === t ? "page" : undefined}
            className={`rounded-md px-3 py-1.5 text-sm ${tab === t ? "bg-signal font-semibold text-bg" : "text-muted hover:text-ink"}`}>{t}</button>
        ))}
      </nav>
      {tab === "Live" ? <Live /> : !d ? <p className="text-muted">Loading…</p> : tab === "Performance" ? <Performance d={d} /> : <Evaluation r={d.eval} />}
    </div>
  );
}
