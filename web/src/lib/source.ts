import type { Control, Dashboard, Overview, QueuedCard, Recent, Turn } from "./types";

export interface Source {
  live: boolean;
  dashboard(): Promise<Dashboard>;
  session(): Promise<string>;
  verify(session: string, account: string, postal: string): Promise<Overview | null>;
  chat(session: string, text: string, verified: boolean): Promise<Turn>;
  control(): Promise<Control>;
  setControl(c: Control): Promise<Control>;
  queue(): Promise<QueuedCard[]>;
  recent(): Promise<Recent[]>;
  demoAccount(): Promise<{ account: string; postal: string } | null>;
  /** Public demo only: forget this browser's clicks (control plane, queue, session log). */
  reset(): void;
}

const json = async (url: string, init?: RequestInit) => {
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
};
const send = (method: string, url: string, body: unknown) =>
  json(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

/** Live mode: FastAPI on the laptop, real model calls. */
export const liveSource: Source = {
  live: true,
  dashboard: () => json("/api/dashboard"),
  session: async () => (await json("/api/session")).session_id,
  verify: async (session, account_number, postal_code) =>
    (await send("POST", "/api/verify", { session_id: session, account_number, postal_code })).overview,
  chat: (session, text) => send("POST", "/api/chat", { session_id: session, text }),
  control: () => json("/api/control"),
  setControl: (c) => send("PUT", "/api/control", c),
  queue: () => json("/api/queue"),
  recent: () => json("/api/recent"),
  demoAccount: async () => null,
  reset: () => {},
};

interface StaticData { dashboard: Dashboard; turns: Record<string, Turn>; control: Control; accounts: { account: string; postal: string; overview: Overview } }
let data: Promise<StaticData> | null = null;
const ROOT = document.body.classList.contains("console") ? "../" : "./";
const load = () => (data ??= fetch(`${ROOT}data/static-data.json`, { cache: "no-cache" }).then((r) => r.json()));
const norm = (t: string) => t.toLowerCase().replace(/[^a-z0-9 ]/g, "").replace(/\s+/g, " ").trim();
export const turnKey = (text: string, guidance: boolean, verified: boolean) => `${norm(text)}|pg:${guidance ? 1 : 0}|v:${verified ? 1 : 0}`;

/** Browser storage shared by the customer page and the console (public demo only). */
const KEY = { control: "tsa.control", queue: "tsa.queue", recent: "tsa.recent" };
const read = <T,>(k: string, fallback: T): T => JSON.parse(localStorage.getItem(k) ?? "null") ?? fallback;
const push = <T,>(k: string, item: T) => localStorage.setItem(k, JSON.stringify([item, ...read<T[]>(k, [])].slice(0, 50)));

/** Public demo: recorded turns replayed; the control plane is applied here before any recording is used. */
export const staticSource: Source = {
  live: false,
  dashboard: async () => (await load()).dashboard,
  session: async () => "public-demo",
  verify: async (_s, account, postal) => {
    const a = (await load()).accounts;
    return account.trim().toUpperCase() === a.account && postal.replace(/\s/g, "").toUpperCase() === a.postal.replace(/\s/g, "") ? a.overview : null;
  },
  async chat(_s, text, verified) {
    const control = await staticSource.control();
    const handoff = (reason: string): Turn => ({ outcome: "handoff", topic: null, answer: null, citation: null, model_calls: 0,
      card: { queue: "servicing", reason, summary: null, customer_text: text } });
    let t: Turn | undefined = control.kill_switch ? handoff("kill_switch") : undefined;
    if (!t) {
      t = (await load()).turns[turnKey(text, control.topics.product_guidance, verified)];
      if (!t) throw new Error("not-recorded");
      if (t.topic && t.outcome !== "handoff" && !control.topics[t.topic]) t = { ...handoff("topic_off"), topic: t.topic };
    }
    const ts = new Date().toISOString();
    if (t.card) push(KEY.queue, { ...t.card, ts, contact_id: "public-demo" });
    push(KEY.recent, { ts, contact_id: "public-demo", outcome: t.outcome, topic: t.topic, queue: t.card?.queue ?? null,
      reason: t.card?.reason ?? null, model_calls: t.model_calls, cited: !!t.citation });
    return t;
  },
  control: async () => read(KEY.control, (await load()).control),
  setControl: async (c) => { localStorage.setItem(KEY.control, JSON.stringify(c)); return c; },
  queue: async () => read(KEY.queue, []),
  recent: async () => read(KEY.recent, []),
  demoAccount: async () => (await load()).accounts,
  reset: () => { Object.values(KEY).forEach((k) => localStorage.removeItem(k)); },
};

export const source: Source = import.meta.env.VITE_STATIC ? staticSource : liveSource;
