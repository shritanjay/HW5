// Typed client for the FastAPI routes in backend/main.py.

export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export interface ProposedAction {
  kind: string;
  summary: string;
  amount?: number | null;
  ref_id?: number | null;
  needs_human_approval: boolean;
}

export interface BossDecision {
  ticket_id: number;
  assigned_to: AgentName[];
  final_call: string;
  actions: ProposedAction[];
  status: string;
}

export interface LastRun {
  status: "running" | "done" | "error";
  run_id: string;
  ticket_status?: string;
  decision?: BossDecision;
  error?: string;
}

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: string;
  state: "open" | "resolved";
  notes: string | null;
  created_at: string;
  last_run: LastRun | null;
}

export interface Approval {
  id: number;
  ticket_id: number;
  kind: "pay_invoice" | "pay_rent" | "purchase_order";
  ref_id: number;
  sku: string | null;
  size: string | null;
  qty: number | null;
  amount: number;
  reason: string | null;
  requested_by: string;
  status: string;
  decided_by: string | null;
  created_at: string;
}

export interface Draft {
  id: number;
  ticket_id: number;
  audience: string;
  message: string;
  written_by: string;
  created_at: string;
}

export interface TicketDetail extends Omit<Ticket, "state"> {
  drafts: Draft[];
  approvals: Approval[];
}

export interface ToolCall { tool: string; args: Record<string, unknown> }
export interface ToolResult { tool: string; result: string }

export interface AgentEvent {
  seq: number;
  ts: string;
  run_id: string;
  ticket_id: number;
  agent: AgentName;
  chain: string;
  step: "agent_start" | "model_request" | "model_response" | "delegate" | "agent_output" | "error";
  said: string | null;
  to_agent: AgentName | null;
  refused: string | null;
  tool_calls: ToolCall[] | null;
  tool_results: ToolResult[] | null;
  output: Record<string, unknown> | null;
  usage: { requests: number; tool_calls: number; input_tokens: number; output_tokens: number } | null;
}

export interface Cash { name: string; balance: number; date: string }

// The FastAPI backend. The browser calls it directly; the backend's CORS allows this page's origin.
export const API_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  return body as T;
}

export const api = {
  tickets: () => call<{ shop_today: string; tickets: Ticket[] }>("/tickets"),
  ticket: (id: number) => call<TicketDetail>(`/tickets/${id}`),
  run: (id: number, human_note?: string) =>
    call<{ run_id: string }>(`/tickets/${id}/run`, {
      method: "POST",
      body: JSON.stringify(human_note ? { human_note } : {}),
    }),
  events: (since: number, ticketId?: number) =>
    call<{ events: AgentEvent[]; next_since: number }>(
      `/events?since=${since}${ticketId ? `&ticket_id=${ticketId}` : ""}&limit=500`,
    ),
  approvals: (status = "pending") => call<{ approvals: Approval[] }>(`/approvals?status=${status}`),
  decide: (id: number, decision: "approve" | "reject", human: string) =>
    call<{ ok?: boolean; cash: Cash; ticket_status?: string }>(`/approvals/${id}`, {
      method: "POST",
      body: JSON.stringify({ decision, human }),
    }),
  cash: () => call<Cash>("/cash"),
  reset: () => call<{ ok: boolean; cash: Cash }>("/reset", { method: "POST" }),
};
