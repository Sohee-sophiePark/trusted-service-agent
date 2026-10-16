import { useEffect, useRef, useState } from "react";
import { source } from "../lib/source";
import type { Turn } from "../lib/types";

interface Msg { who: "customer" | "agent"; text: string; turn?: Turn }

const HANDOFF = "I'm passing you to a member of our team. They'll see what you've told me, so you won't need to repeat yourself.";
const WELCOME = "Hi, I'm Tessaline's virtual assistant. I can help with your account and bill, the status of an installation, repair or outage, and how our plans and policies work.";

/** The end-customer chat: three intents; everything else is handed to a person. */
export default function Customer() {
  const [session, setSession] = useState("");
  const [verified, setVerified] = useState(false);
  const [askId, setAskId] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([{ who: "agent", text: WELCOME }]);
  const [examples, setExamples] = useState<string[]>([]);
  const [demo, setDemo] = useState<{ account: string; postal: string } | null>(null);
  const [text, setText] = useState("");
  const [acct, setAcct] = useState({ account: "", postal: "" });
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLLIElement>(null);

  useEffect(() => { source.session().then(setSession); source.examples().then(setExamples); source.demoAccount().then(setDemo); }, []);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [msgs]);

  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setBusy(true); setText("");
    setMsgs((m) => [...m, { who: "customer", text: q }]);
    try {
      const t = await source.chat(session, q, verified);
      setAskId(t.outcome === "identity_requested");
      setMsgs((m) => [...m, { who: "agent", text: t.outcome === "handoff" ? HANDOFF : t.answer ?? "", turn: t }]);
    } catch {
      setMsgs((m) => [...m, { who: "agent", text: source.live ? HANDOFF : "This demo replays recorded conversations. Please choose one of the suggested questions." }]);
    }
    setBusy(false);
  }

  async function verify() {
    const ok = await source.verify(session, acct.account, acct.postal);
    setVerified(ok); setAskId(!ok);
    setMsgs((m) => [...m, { who: "agent", text: ok ? "Thank you, you're verified. What would you like to know?" : "Those details don't match our records. Please check and try again." }]);
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col px-3 py-4">
      <header className="mb-3 flex items-center justify-between border-b border-c-line pb-3">
        <div><div className="text-lg font-semibold tracking-tight">Tessaline</div><div className="text-xs text-c-muted">Help · chat with our assistant</div></div>
        <a href="./console.html" className="text-xs text-c-muted underline">Operator console</a>
      </header>
      <p role="note" className="mb-3 rounded bg-c-soft px-3 py-1.5 text-xs text-c-muted">Demo: Tessaline is a fictional company; all accounts and policies are made up.</p>
      <ol className="flex-1 space-y-3" aria-live="polite">
        {msgs.map((m, i) => (
          <li key={i} className={m.who === "customer" ? "ml-12 rounded-2xl rounded-br-sm bg-c-ink px-3 py-2 text-sm text-white" : "mr-12 rounded-2xl rounded-bl-sm bg-c-soft px-3 py-2 text-sm"}>
            {m.text}
            {m.turn?.citation && (
              <div className="mt-2 border-t border-c-line pt-1.5 text-xs text-c-muted">
                Source: <span className="text-c-brand">{m.turn.citation.title} › {m.turn.citation.heading}</span> · effective {m.turn.citation.effective}
              </div>
            )}
          </li>
        ))}
        <li ref={end} />
      </ol>
      {askId && !verified && (
        <form onSubmit={(e) => { e.preventDefault(); verify(); }} className="mt-3 rounded-lg border border-c-line p-3 text-sm">
          <div className="mb-2 font-semibold">Verify your account</div>
          <div className="flex flex-wrap gap-2">
            <input value={acct.account} onChange={(e) => setAcct({ ...acct, account: e.target.value })} placeholder="Account number" aria-label="Account number" className="w-36 rounded border border-c-field px-2 py-1.5" />
            <input value={acct.postal} onChange={(e) => setAcct({ ...acct, postal: e.target.value })} placeholder="Postal code" aria-label="Postal code of the service address" className="w-28 rounded border border-c-field px-2 py-1.5" />
            <button className="rounded bg-signal px-3 py-1.5 font-semibold text-c-ink">Verify</button>
          </div>
          {demo && <p className="mt-2 text-xs text-c-muted">Demo account {demo.account} · postal code {demo.postal}</p>}
        </form>
      )}
      <div className="mt-3 flex flex-wrap gap-1.5" aria-label="Suggested questions">
        {examples.map((e) => <button key={e} onClick={() => ask(e)} disabled={busy} className="rounded-full border border-c-line px-2.5 py-1 text-xs text-c-muted hover:border-c-brand hover:text-c-ink">{e}</button>)}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); ask(text); }} className="mt-2 flex gap-2">
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={500} placeholder="Type your question…" aria-label="Your question"
          className="flex-1 rounded-lg border border-c-field px-3 py-2 text-sm" />
        <button disabled={busy} className="rounded-lg bg-signal px-4 text-sm font-semibold text-c-ink">{busy ? "…" : "Send"}</button>
      </form>
    </div>
  );
}
