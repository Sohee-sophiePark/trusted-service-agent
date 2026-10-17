/** Status is never colour alone: a shape, a colour and a word. */
export function Light({ ok, label }: { ok: boolean | null; label?: string }) {
  const [icon, cls, word] =
    ok === null ? ["◐", "text-warn", "limited"] : ok ? ["●", "text-good", "pass"] : ["■", "text-bad", "fail"];
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap text-xs font-semibold uppercase tracking-wide ${cls}`}>
      <span aria-hidden>{icon}</span>
      {label ?? word}
    </span>
  );
}

export function Panel({ title, kicker, children, className = "" }: { title: string; kicker?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-line bg-panel p-4 ${className}`}>
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-ink">{title}</h2>
        {kicker && <span className="text-xs text-muted">{kicker}</span>}
      </header>
      {children}
    </section>
  );
}
