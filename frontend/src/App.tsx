import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ErrorBoundary from "./ErrorBoundary";
import { AGENT_ICON, CheckSeal, PulseArt, ShopMark, TICKET_ART, WalletIcon } from "./icons";
import { api, type AgentEvent, type AgentName, type Approval, type Cash, type Ticket, type TicketDetail } from "./api";

const AGENTS: { id: AgentName; label: string; role: string }[] = [
  { id: "boss", label: "Boss", role: "Routes tickets · final call" },
  { id: "inventory", label: "Inventory", role: "Stock · restock vendor" },
  { id: "accounting", label: "Accounting", role: "Cash · invoices · margins" },
  { id: "facilities", label: "Facilities", role: "Leases · rent" },
  { id: "customer_service", label: "Customer Service", role: "Drafts · never sent" },
];
const LABEL = Object.fromEntries(AGENTS.map((a) => [a.id, a.label])) as Record<AgentName, string>;
const TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Discount request",
};
const KIND_LABEL: Record<string, string> = {
  pay_invoice: "Pay invoice",
  pay_rent: "Pay rent",
  purchase_order: "Purchase order",
};

const money = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const time = (ts: string) => new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const short = (s: string, n = 220) => (s.length > n ? s.slice(0, n) + "…" : s);
const args = (a: Record<string, unknown>) =>
  Object.entries(a)
    .filter(([k]) => k !== "agent")
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(", ");

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [today, setToday] = useState("");
  const [selected, setSelected] = useState<number>(() => Number(new URLSearchParams(location.search).get("ticket")) || 101);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [pending, setPending] = useState<Approval[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [cashDelta, setCashDelta] = useState<number | null>(null);
  const [human, setHuman] = useState(() => localStorage.getItem("cc-human") ?? "");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const since = useRef(0);

  const anyRunning = tickets.some((t) => t.last_run?.status === "running");

  const refresh = useCallback(async () => {
    try {
      const [board, appr, c, ev] = await Promise.all([api.tickets(), api.approvals(), api.cash(), api.events(since.current)]);
      setTickets(board.tickets);
      setToday(board.shop_today);
      setPending(appr.approvals);
      setCash((prev) => {
        if (prev && c.balance !== prev.balance) setCashDelta(c.balance - prev.balance);
        return c;
      });
      if (ev.next_since < since.current) setEvents([]); // audit file replaced
      if (ev.events.length)
        setEvents((prev) => {
          const seen = new Set(prev.map((e) => e.seq)); // overlapping polls must not duplicate steps
          return [...prev, ...ev.events.filter((e) => !seen.has(e.seq))];
        });
      since.current = ev.next_since;
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const loadDetail = useCallback(async () => {
    try {
      setDetail(await api.ticket(selected));
    } catch {
      setDetail(null);
    }
  }, [selected]);

  useEffect(() => {
    refresh();
  }, [refresh]);
  useEffect(() => {
    const id = setInterval(refresh, anyRunning ? 1200 : 4000);
    return () => clearInterval(id);
  }, [refresh, anyRunning]);
  useEffect(() => {
    loadDetail();
  }, [loadDetail, tickets, pending]);
  useEffect(() => {
    if (cashDelta === null) return;
    const id = setTimeout(() => setCashDelta(null), 4000);
    return () => clearTimeout(id);
  }, [cashDelta]);

  const ticket = tickets.find((t) => t.id === selected);
  const runId = ticket?.last_run?.run_id;
  const runEvents = useMemo(
    () => events.filter((e) => e.ticket_id === selected && (!runId || e.run_id === runId)),
    [events, selected, runId],
  );
  const ticketPending = pending.filter((a) => a.ticket_id === selected);

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const start = (followUp?: string) =>
    act(async () => {
      await api.run(selected, followUp);
      setNote("");
    });

  const decide = (a: Approval, d: "approve" | "reject") =>
    act(async () => {
      if (!human.trim()) throw new Error("Enter your name before approving.");
      localStorage.setItem("cc-human", human.trim());
      await api.decide(a.id, d, human.trim());
    });

  const reset = () =>
    act(async () => {
      if (!confirm("Reset the working database to the original values? Agent history in the audit trail is kept.")) return;
      await api.reset();
    });

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <div className="logo"><ShopMark size={20} /></div>
          <div>
            <div className="title">Campus Customs · Ops Desk</div>
            <div className="muted small">Shop date {today || "…"} · {anyRunning ? "agents working" : "idle"}</div>
          </div>
        </div>
        <div className="top-right">
          {pending.length > 0 && <div className="pill warn">{pending.length} awaiting approval</div>}
          <div className="cash">
            <div className="muted tiny cash-label"><WalletIcon size={13} /> CHECKING</div>
            <div className="cash-amt">{cash ? money(cash.balance) : "…"}</div>
            {cashDelta !== null && <div className={`delta ${cashDelta < 0 ? "down" : "up"}`}>{cashDelta < 0 ? "−" : "+"}{money(Math.abs(cashDelta))}</div>}
          </div>
          <button className="ghost" onClick={reset} disabled={busy || anyRunning}>Reset DB</button>
        </div>
      </header>

      {error && <div className="banner" onClick={() => setError(null)}>{error}</div>}

      <div className="layout">
        {/* ---------- board ---------- */}
        <section className="desk">
          <div className="desk-head">
            <h2>Ticket desk</h2>
            <span className="muted small">
              {tickets.filter((t) => t.state === "open").length} open · {tickets.filter((t) => t.state === "resolved").length} resolved · click a ticket to open it
            </span>
          </div>
          <table className="desk-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Type</th>
                <th>Subject</th>
                <th>Requester</th>
                <th>Details</th>
                <th>Received</th>
                <th>Status</th>
                <th aria-label="open" />
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  className={t.id === selected ? "on" : ""}
                  tabIndex={0}
                  onClick={() => setSelected(t.id)}
                  onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setSelected(t.id)}
                >
                  <td className="tid">{t.id}</td>
                  <td>
                    <div className="type-cell">
                      <span className="thumb">{(TICKET_ART[t.type] ?? TICKET_ART.customer_order)({ size: 28 })}</span>
                      <span className={`type ${t.type}`}>{TYPE_LABEL[t.type] ?? t.type}</span>
                    </div>
                  </td>
                  <td className="tsub">{t.subject}</td>
                  <td>{t.requester}</td>
                  <td className="muted">
                    {t.sku ? `${t.sku} · ${t.size} × ${t.qty}` : t.lease_id ? `Lease #${t.lease_id}` : "—"}
                    {t.invoice_id ? ` · Inv #${t.invoice_id}` : ""}
                  </td>
                  <td className="muted nowrap">{new Date(t.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</td>
                  <td><StatusPill t={t} /></td>
                  <td className="chev">›</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* ---------- selected ticket ---------- */}
        <main className="main">
          {ticket && (
            <>
              <section className="card hero">
                <div className="hero-head">
                  <div className="hero-art">{(TICKET_ART[ticket.type] ?? TICKET_ART.customer_order)({ size: 84 })}</div>
                  <div className="grow">
                    <div className="muted small">#{ticket.id} · {TYPE_LABEL[ticket.type] ?? ticket.type} · {ticket.requester}</div>
                    <h1>{ticket.subject}</h1>
                    <div className="facts">
                      {ticket.sku && <Fact k="Item" v={`${ticket.sku} · ${ticket.size} × ${ticket.qty}`} />}
                      {ticket.invoice_id && <Fact k="Invoice" v={`#${ticket.invoice_id}`} />}
                      {ticket.lease_id && <Fact k="Lease" v={`#${ticket.lease_id}`} />}
                      <Fact k="Status" v={ticket.status.replace("_", " ")} />
                    </div>
                  </div>
                  <div className="hero-actions">
                    {ticket.state === "open" && ticket.last_run?.status !== "running" && !ticket.last_run && (
                      <button className="primary" onClick={() => start()} disabled={busy}>Run agent team</button>
                    )}
                    {ticket.last_run?.status === "running" && <div className="pill live"><span className="dot" />Running</div>}
                    {ticket.last_run && ticket.last_run.status !== "running" && ticket.state === "open" && ticketPending.length === 0 && (
                      <button className="primary" onClick={() => start()} disabled={busy}>Run again</button>
                    )}
                  </div>
                </div>
                <p className="request">“{ticket.notes?.split("\n")[0]}”</p>
                {ticket.last_run?.status === "error" && <div className="banner inline">Run failed: {ticket.last_run.error}</div>}
              </section>

              {ticketPending.length === 0 && ticket.last_run?.status === "done" && ticket.last_run.decision &&
                ["blocked", "waiting_approval"].includes(ticket.status) && (
                <section className="card approvals">
                  <div className="card-head">
                    <h2>The Boss needs your decision</h2>
                    <input className="name" placeholder="Your name" value={human} onChange={(e) => setHuman(e.target.value)} />
                  </div>
                  <p className="call">{ticket.last_run.decision.final_call}</p>
                  {ticket.last_run.decision.actions.filter((a) => !a.needs_human_approval && a.kind !== "note").map((a, i) => (
                    <div key={i} className="muted small">• {a.summary}</div>
                  ))}
                  <div className="row gap" style={{ marginTop: 14 }}>
                    <input className="grow" placeholder="Optional: change the terms (e.g. 15% instead, fill 8 now)…" value={note} onChange={(e) => setNote(e.target.value)} />
                    <button className="ghost" disabled={busy || !human.trim()}
                      onClick={() => start(`${human.trim()} (human) REJECTS the Boss's recommendation.${note.trim() ? " Instead: " + note.trim() : ""} Close the ticket accordingly and have customer_service update the requester's draft.`)}>
                      Reject
                    </button>
                    <button className="primary" disabled={busy || !human.trim()}
                      onClick={() => start(`${human.trim()} (human) APPROVES the Boss's recommendation: "${ticket.last_run!.decision!.final_call}"${note.trim() ? " With this change: " + note.trim() : ""}. Finalize the ticket: make sure the requester's draft matches this decision, then mark it resolved.`)}>
                      Approve recommendation
                    </button>
                  </div>
                  {!human.trim() && <div className="muted tiny" style={{ marginTop: 8 }}>Enter your name to decide.</div>}
                </section>
              )}

              {ticketPending.length > 0 && (
                <section className="card approvals">
                  <div className="card-head">
                    <h2>Needs your approval</h2>
                    <input className="name" placeholder="Your name" value={human} onChange={(e) => setHuman(e.target.value)} />
                  </div>
                  {ticketPending.map((a) => (
                    <div key={a.id} className="approval">
                      <div>
                        <div className="appr-title">{KIND_LABEL[a.kind]} {a.kind === "purchase_order" ? `· ${a.sku} ${a.size} × ${a.qty}` : `#${a.ref_id}`}</div>
                        <div className="muted small">{a.reason} · requested by {LABEL[a.requested_by as AgentName] ?? a.requested_by}</div>
                      </div>
                      <div className="appr-right">
                        <div className="appr-amt">{money(a.amount)}</div>
                        {cash && <div className={`tiny ${cash.balance < a.amount ? "neg" : "muted"}`}>after: {money(cash.balance - a.amount)}</div>}
                        <div className="row gap">
                          <button className="ghost" onClick={() => decide(a, "reject")} disabled={busy}>Reject</button>
                          <button className="primary" onClick={() => decide(a, "approve")} disabled={busy}>Approve & pay</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </section>
              )}

              {ticket.last_run?.decision && <ErrorBoundary label="Final call"><Decision t={ticket} /></ErrorBoundary>}

              <section className="card">
                <div className="card-head"><h2>What each agent did</h2><span className="muted small">{runId ? `run ${runId}` : "not run yet"}</span></div>
                <ErrorBoundary label="Agent summary"><AgentSummary events={runEvents} running={ticket.last_run?.status === "running"} /></ErrorBoundary>
              </section>

              <section className="card">
                <div className="card-head">
                  <h2>Live activity</h2>
                  <span className="muted small">{runEvents.length} steps{runEvents.at(-1)?.usage ? ` · ${(runEvents.at(-1)!.usage!.input_tokens + runEvents.at(-1)!.usage!.output_tokens).toLocaleString()} tokens` : ""}</span>
                </div>
                <ErrorBoundary label="Live activity"><Feed events={runEvents} /></ErrorBoundary>
              </section>

              {detail && detail.drafts.length > 0 && (
                <section className="card">
                  <div className="card-head"><h2>Drafts on the board</h2><span className="muted small">not sent</span></div>
                  {detail.drafts.map((d) => (
                    <div key={d.id} className="draft">
                      <div className="muted small">To {d.audience} · by {LABEL[d.written_by as AgentName] ?? d.written_by}</div>
                      <p>{d.message}</p>
                    </div>
                  ))}
                </section>
              )}

              {ticket.last_run && ticket.last_run.status !== "running" && (
                <section className="card">
                  <div className="card-head"><h2>Follow-up for the Boss</h2><span className="muted small">e.g. the discount you approved</span></div>
                  <div className="row gap">
                    <input className="grow" placeholder="Tell the Boss your decision, then it continues the ticket…" value={note} onChange={(e) => setNote(e.target.value)} />
                    <button className="primary" disabled={!note.trim() || busy || ticketPending.length > 0} onClick={() => start(note.trim())}>Send & continue</button>
                  </div>
                  {ticketPending.length > 0 && <div className="muted tiny" style={{ marginTop: 8 }}>Decide the pending approvals first.</div>}
                </section>
              )}

              {detail && detail.approvals.some((a) => a.status !== "pending") && (
                <section className="card">
                  <div className="card-head"><h2>Payment history</h2></div>
                  {detail.approvals.filter((a) => a.status !== "pending").map((a) => (
                    <div key={a.id} className="hist">
                      <span>{KIND_LABEL[a.kind]} #{a.ref_id}</span>
                      <span className="muted">{a.status} by {a.decided_by}</span>
                      <span className={a.status === "paid" ? "neg" : "muted"}>{a.status === "paid" ? `−${money(a.amount)}` : money(a.amount)}</span>
                    </div>
                  ))}
                </section>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function StatusPill({ t }: { t: Ticket }) {
  if (t.last_run?.status === "running") return <span className="pill live"><span className="dot" />running</span>;
  if (t.state === "resolved") return <span className="pill ok"><CheckSeal size={12} />resolved</span>;
  if (t.status === "waiting_approval") return <span className="pill warn">needs approval</span>;
  if (t.last_run?.status === "error") return <span className="pill bad">error</span>;
  return <span className="pill">{t.status.replace("_", " ")}</span>;
}

function Fact({ k, v }: { k: string; v: string }) {
  return <div className="fact"><span>{k}</span>{v}</div>;
}

function Decision({ t }: { t: Ticket }) {
  const d = t.last_run!.decision!;
  return (
    <section className="card decision">
      <div className="card-head"><h2>Boss’s final call</h2><span className="pill">{d.status.replace("_", " ")}</span></div>
      <p className="call">{d.final_call}</p>
      {d.actions.length > 0 && (
        <ul className="actions">
          {d.actions.map((a, i) => (
            <li key={i}>
              <span>{a.summary}</span>
              <span className="muted">{a.amount != null ? money(a.amount) : ""}{a.needs_human_approval ? " · needs approval" : ""}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="muted small">Worked by: {d.assigned_to.map((a) => LABEL[a]).join(", ") || "Boss only"}</div>
    </section>
  );
}

function AgentSummary({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const last = events.at(-1);
  return (
    <div className="agents">
      {AGENTS.map((a) => {
        const mine = events.filter((e) => e.agent === a.id);
        const tools = [...new Set(mine.flatMap((e) => e.tool_calls ?? []).map((c) => c.tool).filter((n) => n !== "delegate" && n !== "final_result"))];
        const asked = mine.filter((e) => e.step === "delegate" && !e.output).map((e) => e.to_agent).filter(Boolean) as AgentName[];
        const out = mine.find((e) => e.step === "agent_output")?.output as { findings?: string[]; final_call?: string } | undefined;
        const active = running && last?.agent === a.id;
        const state = active ? "working" : out ? "done" : mine.length ? "waiting" : "idle";
        return (
          <div key={a.id} className={`agent ${state}`}>
            <div className="row">
              <div className="agent-id">
                <span className={`avatar ${a.id}`}>{AGENT_ICON[a.id]({ size: 18 })}</span>
                <div>
                <div className="agent-name">{a.label}</div>
                <div className="muted tiny">{a.role}</div>
                </div>
              </div>
              <span className={`state ${state}`}>{active && <span className="dot" />}{state}</span>
            </div>
            {mine.length === 0 ? (
              <div className="muted small">Not involved{events.length ? "" : " yet"}.</div>
            ) : (
              <>
                {asked.length > 0 && <div className="small">Asked → {[...new Set(asked)].map((x) => LABEL[x]).join(", ")}</div>}
                {tools.length > 0 && <div className="chips">{tools.map((t) => <code key={t} className="chip">{t}</code>)}</div>}
                {out?.final_call && <div className="small summary">{short(out.final_call, 260)}</div>}
                {out?.findings && (
                  <ul className="findings">{out.findings.slice(0, 4).map((f, i) => <li key={i}>{short(f, 160)}</li>)}</ul>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Feed({ events }: { events: AgentEvent[] }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // keep the feed pinned to the newest step (scrolls the feed only, not the page)
    if (box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [events.length]);
  const lines = events.flatMap((e) => describe(e));
  if (!lines.length) return (
      <div className="muted small empty">
        <PulseArt size={52} className="empty-art" />
        <div>Run the agent team on this ticket. Each step shows up here as it happens.</div>
      </div>
    );
  return (
    <div className="feed" ref={box}>
      {lines.map((l, i) => (
        <div key={i} className={`line ${l.kind}`} style={{ paddingLeft: 12 + l.depth * 18 }}>
          <span className="ts">{time(l.ts)}</span>
          <span className={`who ${l.agent}`}><span className={`mini ${l.agent}`}>{AGENT_ICON[l.agent]({ size: 13 })}</span>{LABEL[l.agent]}</span>
          <span className="what">{l.text}</span>
        </div>
      ))}
    </div>
  );
}

type Line = { ts: string; agent: AgentName; depth: number; kind: string; text: string };

function describe(e: AgentEvent): Line[] {
  const depth = e.chain.split(" -> ").length - 1;
  const base = { ts: e.ts, agent: e.agent, depth };
  switch (e.step) {
    case "agent_start":
      return [{ ...base, kind: "start", text: depth === 0 ? "Picked up the ticket" : `Started: ${short(e.said?.replace(/^Ticket \d+\. Request from \w+: /, "") ?? "", 180)}` }];
    case "delegate":
      return [{ ...base, kind: "delegate", text: e.refused ? `✕ ${LABEL[e.to_agent!]}: ${e.refused}` : `→ asks ${LABEL[e.to_agent!]}: ${short(e.said ?? "", 180)}` }];
    case "model_response": {
      const calls = (e.tool_calls ?? []).filter((c) => c.tool !== "delegate" && c.tool !== "final_result");
      const out: Line[] = calls.map((c) => ({ ...base, kind: "tool", text: `⚙ ${c.tool}(${short(args(c.args), 120)})` }));
      if (e.said) out.unshift({ ...base, kind: "say", text: short(e.said, 240) });
      return out;
    }
    case "model_request":
      return (e.tool_results ?? [])
        .filter((r) => r.tool !== "delegate" && r.tool !== "final_result")
        .map((r) => ({ ...base, kind: "result", text: `↳ ${r.tool}: ${short(r.result, 160)}` }));
    case "agent_output":
      return [{ ...base, kind: "done", text: `✓ Reported: ${short(e.said ?? "done", 220)}` }];
    case "error":
      return [{ ...base, kind: "error", text: `Error: ${e.said}` }];
  }
}
