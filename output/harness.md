# Campus Customs Agent Harness

The complete harness for the Campus Customs agent team: the database it works on, the MCP tools that are its only way to touch shop data, the five agents, the API routes, the dashboard a human supervises from, and the safety rules around money and customers.

**Contents:** Database tables · MCP server and all MCP tools · Agent team (5 agents, delegation, agent loop) · Audit trail · Safety guardrails and token limits · Backend routes · Dashboard · Run results

**How the pieces connect:** React dashboard (:5173) → FastAPI backend (:8000) → agent team (PydanticAI) → campus-customs MCP server → `data/campus_customs_new.db`. The backend's own reads and the human's approvals also go through the MCP server; nothing touches the database directly.

Database: `data/campus_customs_new.db` (working copy). Original `data/campus_customs.db` is never modified; copy it over the working copy to reset.

## Database tables

### desk
- Fields: `date_today`, `notes`
- Why it matters: the shop's clock. Every overdue and due-soon decision uses `date_today`, not the real date.

### tickets
- Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`
- Why it matters: the board. The Boss reads each ticket and routes it, and its links (sku/size, lease_id, invoice_id) point agents to the right records.

### inventory
- Fields: `sku`, `name`, `size`, `qty`, `location` (key: sku + size)
- Why it matters: Inventory checks stock by SKU and size here to spot shortfalls.

### pricing
- Fields: `sku`, `unit_cost`, `list_price`
- Why it matters: Accounting checks margins and discount floors (never below cost) and prices restock POs.

### vendors
- Fields: `id`, `name`, `specialty`, `lead_days`
- Why it matters: Inventory picks the restock vendor by specialty and uses `lead_days` to estimate arrival dates.

### leases
- Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
- Why it matters: Facilities tracks rent amount and due date. `next_due` advances after rent is paid.

### cash_accounts
- Fields: `name`, `balance`, `date`
- Why it matters: the cash limit. The pay tool refuses any payment that would push a balance below zero (cash only goes out).

### payments
- Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
- Why it matters: the payment record. A row is written only after human approval, and `approved_by` records who approved it.

### invoices
- Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`
- Why it matters: shows what the shop owes. An open, unpaid invoice blocks that vendor from shipping new product, and `due_date` vs `date_today` flags overdue bills.

### Workflow tables (added by the MCP server, working copy only)
- `approvals`: `id, ticket_id, kind, ref_id, sku, size, qty, amount, reason, requested_by, status, decided_by, created_at`. Payments the agents request, waiting on a human. The amount is read from the DB, never from the model.
- `drafts`: `id, ticket_id, audience, message, written_by, created_at`. Customer Service messages that stay on the board and are never sent.

## MCP server (`mcp_server/server.py`, FastMCP)

Every agent uses the tools on this one server. It reads `data/campus_customs_new.db` (the working copy). Tools return only values stored in the database (or computed directly from them, like days overdue against `desk.date_today`). If a record is missing, the tool returns an error instead of guessing. The first three tools below (Problem 3) map one-to-one to the open tickets; Problem 5 grew the server (full list in "All MCP tools").

### 1. `check_stock_and_pricing(sku, size, qty_needed)`
- Reads: `inventory` (qty and location for that SKU + size) and `pricing` (unit_cost, list_price).
- Unlocks: **Ticket 103**, Yale AI Club wants 20 × CC-HOOD-NAVY size M at a bulk discount.
- Why it's the right tool: ticket 103 needs both answers at once: can we fill 20 size M (8 on hand, so 12 short) and how low can a discount go before it falls under the $22 unit cost against the $58 list price.

### 2. `check_vendor_invoice(invoice_id)`
- Reads: `invoices` (amount, due_date, status), `vendors` (name, lead_days), `desk` (date_today).
- Unlocks: **Ticket 101**, Tauhid Zaman's CC-TEE-WHITE size S order, linked to invoice 501.
- Why it's the right tool: the tee is out of stock and the only apparel vendor, Bulldog Print Co, has invoice 501 ($840, due 2026-08-28) still open. The tool shows it's 3 days overdue against the shop date of 2026-08-31 and that the vendor is blocked from reprinting until it's paid. It also gives the 5-day lead time for the customer's ETA.

### 3. `check_lease_rent(lease_id)`
- Reads: `leases` (landlord, monthly_rent, next_due), `desk` (date_today), `cash_accounts` (balance).
- Unlocks: **Ticket 102**, Elm City Properties' rent notice for lease 1.
- Why it's the right tool: it confirms the landlord's email against the lease ($2,400 due 2026-09-02, 2 days out, so not overdue yet) and shows the $3,400 checking balance, so Facilities and Accounting can tell whether paying rent on time leaves enough cash for the other tickets.

## Agent team (`backend/`, PydanticAI)

| File | Contents |
|---|---|
| `backend/prompts/boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md` | One file per agent: its role section, then the shared scenario + shop rules every agent gets |
| `backend/models.py` | `AgentName`, `ProposedAction`, `AgentReport`, `BossDecision`, `TraceEvent` |
| `backend/main.py` §1 Agent team | Model (Portkey, `gpt-5.6-luna`), the five agents, `delegate`, per-role tool filter (`ROLE_TOOLS`), audit trail, `run_team()` |
| `backend/main.py` §2 API routes | The FastAPI routes the dashboard calls (see Backend routes) |

### Agents

| Agent | Job | Tables it owns | MCP tools it can call |
|---|---|---|---|
| **boss** | Runs the shop: reads each ticket, delegates, weighs reports against cash and priorities, makes the final call, sets ticket status | all (for spot checks) | every agent-safe tool except `save_customer_draft` (and the human-only ones) |
| **inventory** | Stock by SKU/size, shortfalls, restock vendor, lead time, ETA | inventory, vendors (+ invoices to see if a vendor is blocked) | check_stock_and_pricing, list_vendors, check_vendor_invoice, quote_purchase_order, request_payment_approval (PO) |
| **accounting** | Cash, invoices, **margins**; prepares payments/POs for human approval | cash_accounts, invoices, payments, pricing | check_cash_and_obligations, check_vendor_invoice, check_lease_rent, check_stock_and_pricing, check_discount_margin, quote_purchase_order, request_payment_approval |
| **facilities** | Leases, rent, landlord notices | leases | check_lease_rent, request_payment_approval (rent) |
| **customer_service** | Drafts for customers/requesters; never sent | tickets, drafts | get_ticket, save_customer_draft |

Every agent also has `delegate(to_agent, task)` (full connectivity). Tool access is enforced in code (`ROLE_TOOLS`, `HUMAN_ONLY`, `CUSTOMER_SERVICE_ONLY` in backend/main.py), not just in prompts.

**Agent loop:** Boss gets the ticket, then repeats model request, tool calls (MCP and/or delegate), model request, until it returns a `BossDecision`. A delegate runs the target agent's own loop and returns its `AgentReport` as JSON. Guards: no self-delegation, no cycles (A -> B -> A refused), max depth 3.

## All MCP tools (`mcp_server/server.py`)

All shop facts come from this server over `data/campus_customs_new.db`. There is no second tools layer: agents and the dashboard both go through MCP. Two workflow tables (`approvals`, `drafts`) are created on the working copy; the shop tables keep their original schema.

| Tool | Tables used | Who | Read/Write |
|---|---|---|---|
| check_stock_and_pricing | inventory, pricing | boss, inventory, accounting | read |
| check_vendor_invoice | invoices, vendors, desk | boss, inventory, accounting | read |
| check_lease_rent | leases, desk, cash_accounts | boss, accounting, facilities | read |
| list_tickets | tickets, desk | boss, dashboard | read |
| list_open_tickets | tickets, desk | boss | read |
| list_approvals | approvals | boss, dashboard | read |
| get_cash_balance | cash_accounts | boss, dashboard | read |
| get_ticket | tickets, drafts, approvals | boss, customer_service | read |
| update_ticket_status | tickets (status, notes), desk | boss | write |
| list_vendors | vendors, invoices, desk | boss, inventory | read |
| quote_purchase_order | inventory, pricing, vendors, invoices, cash_accounts, desk | boss, inventory, accounting | read |
| check_cash_and_obligations | cash_accounts, invoices, vendors, leases, approvals, payments, desk | boss, accounting | read |
| check_discount_margin | pricing | boss, accounting | read |
| request_payment_approval | invoices / leases / pricing+vendors, approvals | boss, inventory, accounting, facilities | write (`approvals` row, status pending; pays nothing) |
| save_customer_draft | tickets, drafts | customer_service only | write (`drafts` row; never sent) |
| decide_approval | approvals, payments, cash_accounts, invoices / leases / vendors, desk | **human only** (dashboard) | write (the only way money moves) |
| reset_database | whole file (copies original over working copy) | **human only** | write |

New tools by ticket:
- **101 (tee):** list_vendors confirms Bulldog Print is the apparel vendor and is blocked. request_payment_approval(pay_invoice, 501) puts the $840 on the board. save_customer_draft holds Tauhid's ETA note.
- **102 (rent):** check_cash_and_obligations shows what's left after rent. request_payment_approval(pay_rent, 1) queues the $2,400.
- **103 (hoodies):** check_discount_margin tests the club's discount against the $22 cost. quote_purchase_order prices the 12-unit restock and shows it's blocked or unaffordable.
- **All:** list_open_tickets / get_ticket let the Boss read the board, and update_ticket_status records the final call.

## Audit trail (`output/audit_trail.json`)

Every agent-loop step is **appended** to a JSON array (read, append, atomic replace). The file is never wiped between runs, and a damaged file is renamed aside instead of overwritten.

Each entry: `ts`, `run_id` (one per ticket run), `ticket_id`, `agent`, `chain` (e.g. `boss -> accounting`), `depth`, `model`, `step`, plus step detail and `usage_so_far` (requests, tool calls, input/output tokens).

| step | Detail recorded |
|---|---|
| agent_start | the prompt/task the agent received |
| model_request | tool results fed back to the model, and validation retries |
| model_response | tool calls with arguments, any text, tokens for that response |
| delegate | target agent, task, and refusal reason if blocked |
| agent_output | the agent's final structured output (AgentReport / BossDecision) |
| human_decision | a human's approve/reject click on a payment: who, which approval, amount, and the result (payment id, balance) or the refusal. Chain is `human`. The two approvals from the graded run were clicked before this step existed, so they're backfilled from the approvals + payments tables and marked `source: BACKFILLED`. Discount decisions appear as the human-decision text in the follow-up run's `agent_start` prompt. |
| error | exception type and message |

Long tool results are clipped to 1,500 chars. No API keys are logged.

## Safety guardrails

What a real business would want before agents touch real customers and real money, and what this build does:

- **Humans approve all money.** Agents can only *request* (`request_payment_approval`). Only `decide_approval`, which no agent is given, pays. It rejects agent names as the approver.
- **Amounts come from the database, not the model.** The approval amount is read from the invoice, lease, or pricing row, so an agent can't inflate or invent a figure.
- **No negative cash.** Payments refuse if checking can't cover them, and cash only goes out.
- **Vendor rule in code.** A PO to a vendor with an open invoice is refused at payment time.
- **Atomic payments.** The payment row, cash debit, and invoice/lease update commit together or not at all. Double payment is refused (status checks, duplicate-approval check).
- **No outbound contact.** There is no email or vendor tool at all. Drafts sit on the board (`sent: false`) for a human.
- **Least privilege.** Each role sees only the tools for its tables. Customer Service can't see cash or pay anything. **Only Customer Service can write customer drafts.** The Boss lost `save_customer_draft` after its own draft on ticket 103 leaked vendor, cash, cost, and margin details, and the Customer Service prompt now bans internal details in drafts.
- **No invented facts.** Prompts forbid it, tools return errors instead of guesses, and the audit trail lets a human check every number against a tool result.
- **Reversible test runs.** The original DB is never written. `reset_database` (human only) restores it.
- **Audit everything.** It's append-only, per step, with who/what/when/tokens.

### Token and cost limits

| Limit | Value | Where |
|---|---|---|
| Model requests per ticket (all agents combined) | 30 | `UsageLimits.request_limit` |
| Tool calls per ticket | 40 | `UsageLimits.tool_calls_limit` |
| Total tokens per ticket | 120,000 | `UsageLimits.total_tokens_limit` |
| Max tokens per model reply | 1,500 | `max_tokens` model setting |
| Delegation depth | 3 | `MAX_DEPTH` |
| Cycles | refused | `delegate()` chain check |
| Tool outputs | short JSON, only needed fields | MCP server |
| Prompts | one shared rules file + short role file | `backend/prompts/` |

Usage is shared across delegated runs (`usage=ctx.usage`), so the caps cover the whole team, not each agent separately. Hitting a cap stops the run with an error that lands in the audit trail.

## Backend routes (`backend/main.py`, FastAPI)

Base URL `http://localhost:8000`. Start with `cd backend && uvicorn main:app --reload --port 8000`. CORS allows the dashboard at `localhost:5173`. Every route goes through the MCP server; none opens the database directly.

- `GET /api/tickets`: returns all 3 tickets and whether each is open or resolved, plus the last agent run's result.
- `GET /api/tickets/{id}`: one ticket with its saved drafts and approval requests.
- `POST /api/tickets/{id}/run`: runs the agent team on that ticket in the background (optional `human_note` for a second pass after a human decision).
- `GET /api/events?since=&ticket_id=&run_id=`: returns recent agent-loop steps (who said what, which tools ran) from the audit trail so the board can refresh.
- `GET /api/approvals?status=pending`: lists the payments and purchase orders the agents prepared that are waiting on a human.
- `POST /api/approvals/{id}`: the human approves or rejects a prepared payment. This is the only route that changes cash.
- `GET /api/cash`: returns the current checking balance from cash_accounts.
- `POST /api/reset`: resets the working database to the original values for a fresh run.
- `GET /api/health`: confirms the server is up and shows the model and database in use.

MCP tools added for these routes: `list_tickets` (tickets, desk), `list_approvals` (approvals), `get_cash_balance` (cash_accounts). All read-only.

## Dashboard (`frontend/`, React + Vite + TypeScript)

Run: `cd frontend && npm install && npm run dev`, then open http://localhost:5173. The browser calls the backend directly at `http://localhost:8000` (`API_BASE` in `src/api.ts`, override with `VITE_API_URL`). The backend's CORS allows the Vite origin (`DASHBOARD_ORIGINS`, default `http://localhost:5173,http://127.0.0.1:5173`).

| Area | What it shows / does | Route(s) |
|---|---|---|
| Header | Shop date, **checking balance** (flashes the change after a payment), count awaiting approval, Reset DB | `/api/cash`, `/api/approvals`, `/api/reset` |
| Ticket desk (table) | All 3 tickets as clickable table rows: #, type, subject, requester, details (SKU/size/qty, lease, invoice), received, status (open / running / needs approval / **resolved**). Click or Enter opens the ticket below. | `/api/tickets` |
| Ticket header | Request text and key facts; **Run agent team** button | `POST /api/tickets/{id}/run` |
| The Boss needs your decision | When the Boss leaves a ticket blocked or waiting with no payment pending (e.g. 103's discount): its recommendation, an optional "change the terms" box, and **Approve recommendation** / Reject, which send the human's decision back to the Boss as a follow-up run | `POST /api/tickets/{id}/run` with `human_note` |
| Needs your approval | Each payment or PO the agents prepared: amount, reason, who asked, balance after. Name field plus **Approve & pay** / Reject. | `/api/approvals`, `POST /api/approvals/{id}` |
| Boss's final call | The Boss's decision, actions, and who worked the ticket | `/api/tickets` (last_run) |
| What each agent did | One card per agent: idle / working / waiting / done, who it asked, MCP tools it used, its findings | `/api/events` |
| Live activity | Step-by-step feed, indented by delegation depth: delegations, tool calls with args, tool results, reports, refusals, running token count | `/api/events?since=` (polls every 1.2s while running) |
| Drafts on the board | Customer Service drafts (marked not sent) | `/api/tickets/{id}` |
| Follow-up for the Boss | Sends the human's decision back to the Boss for a second pass (ticket 103) | `POST /api/tickets/{id}/run` with `human_note` |
| Payment history | Approved or rejected payments for the ticket | `/api/tickets/{id}` |

**Resolved rule:** a ticket is **resolved** only when no approval on it is pending *and* the Boss didn't leave it `blocked` / `waiting_approval` (e.g. 103's discount still needs the human). After the human decides the last approval, the ticket resolves. A Boss-blocked ticket resolves after the human's follow-up run. Last-run results are rebuilt from the audit trail when the backend restarts.

## Run results (Problem 9)

Full run on 2026-10-13 from a fresh reset (start **$3,400**):

| Ticket | Outcome | Human decision | Cash |
|---|---|---|---|
| 101 | Tee out of stock; invoice 501 paid to unblock Bulldog Print Co; draft to Tauhid (no date) | Approved pay invoice 501 | −$840 |
| 102 | Lease verified; rent paid before it was due; next_due 2026-10-02 | Approved pay rent | −$2,400 |
| 103 | 20% bulk discount ($46.40 × 20 = $928, above cost); 8 on hand; $264 restock not funded | Approved the discount | $0 |

Ending checking **$160**, matching `cash_accounts`. Details: `output/desk_tickets.html` (Expected vs Actual + Cash tab), `output/resolved_tickets.json`, `output/resolved_board.html`, `output/audit_trail.json`.

Lessons fed back into the harness: the Boss lost `save_customer_draft` (its draft leaked internal details); discounts now wait for the human before any customer draft; ticket status respects a Boss "blocked" call; last-run state is rebuilt from the audit trail on restart; human approval clicks are now audited.
