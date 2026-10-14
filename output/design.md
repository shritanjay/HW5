# Campus Customs Ops Desk: Dashboard Design

The dashboard (`frontend/`, React + Vite + TypeScript) is where a human watches the agent team work the shop's tickets and approves anything that spends money. This file records the look we chose together and why.

## Starting principles

- **Black and grey, minimal, modern.** This is the workspace default: a near-black background (`#09090b`), stacked grey panels, one bright neutral (white) for primary actions. Colour is kept for *meaning*, not decoration (see "Colour has a job").
- **Typography and layout first.** Hierarchy comes from size, weight, spacing, and alignment, so the page reads well before any image loads.
- **A desk, not a chat log.** The human's job is to *supervise*: see the board, open a ticket, follow the team, and approve money. The page is ordered that way.

## Layout (top to bottom)

| Area | Why it's there |
|---|---|
| **Sticky header**: shop mark, "Campus Customs · Ops Desk", shop date, idle/working, *N awaiting approval*, **checking balance**, Reset DB | Cash and pending decisions are what a manager checks first, so they stay visible while you scroll. The shop date is shown because every overdue call uses it, not today's real date. |
| **Ticket desk (table)** | You asked for desks that look like tables with clickable tickets. A table lets you scan all tickets at once: type, subject, requester, details (SKU/size/qty, lease, invoice), received time, status. |
| **Ticket hero card** | The opened ticket: a large illustration, the subject as a heading, fact chips, the requester's words in italics, and the **Run agent team** button. |
| **Needs your approval** (only when something is pending) | Placed *above* the agents' work so money decisions are never buried. |
| **Boss's final call** | The Boss runs the shop and makes the judgement, so its decision gets its own card in plain sentences. |
| **What each agent did** | One card per agent: the at-a-glance summary of a ticket. |
| **Live activity** | The step-by-step feed for watching (or auditing) the run as it happens. |
| **Drafts on the board · Follow-up for the Boss · Payment history** | Supporting detail: what Customer Service wrote (never sent), the second-pass box for ticket 103, and what was paid by whom. |

## The ticket desk

- **Rows are the click target.** The whole row is clickable, with a pointer cursor, hover highlight, and a `›` chevron that nudges right on hover. Rows also work by keyboard (Tab + Enter).
- **The selected ticket** gets a white bar on its left edge, like a tab pulled out of a filing drawer, so you always know which ticket the page below is about.
- **Each row has a small illustration tile** (tee, storefront, hoodie with a % tag), so the three ticket types can be told apart without reading.
- **Header line:** "3 open · 0 resolved · click a ticket to open it". The board's progress and the one instruction a new user needs.
- Cells don't wrap. On narrow screens the table scrolls sideways instead of squashing.

## How the agents read differently

Each agent has its own **line-art avatar** that hints at its role:

| Agent | Avatar | Role line |
|---|---|---|
| Boss | crown (brighter avatar than the others) | Routes tickets · final call |
| Inventory | box | Stock · restock vendor |
| Accounting | calculator | Cash · invoices · margins |
| Facilities | key | Leases · rent |
| Customer Service | chat bubble | Drafts · never sent |

- **State is shown by colour and a word:** *idle* (dimmed), *working* (blue glow with a pulsing dot), *waiting* (amber, has started but not reported), *done* (green). You can see who is busy without reading the feed.
- **Each card answers "what did you do?"**: who it asked ("Asked → Inventory, Accounting"), the **MCP tools it called** as monospace chips, and its findings or the Boss's final call. This is the short per-agent summary the brief asked for.
- **In the live feed**, every line starts with the agent's mini avatar and name, and lines are **indented by delegation depth** (Boss → Accounting → …), so the team structure is visible as the conversation unfolds.
- **The feed uses a different type style for each kind of step:** spoken text in normal type; tool calls (`⚙ check_stock_and_pricing(sku=…)`) in monospace; tool results (`↳ …`) in muted grey; delegations (`→ asks Accounting: …`) in blue; reports (`✓ Reported: …`) in green; refusals and errors in red. It reads like a script, not a log dump.

## How resolved tickets show up

- **Status pills** in the desk: *open* (grey), *running* (blue with a pulsing dot), *needs approval* (amber), *resolved* (green with a small seal icon), *error* (red).
- **When a ticket counts as resolved:** when its run finishes and nothing on it waits on a human. If a payment is pending, it parks at *needs approval* and turns resolved the moment the human decides the last approval. "Resolved" never means "the agents stopped talking while money is still pending."
- The desk header counts open vs resolved, so progress is visible from the top.

## How cash shows up

- **Checking balance is the biggest number on the page**, top right, with a wallet icon, in tabular numerals so digits don't jump.
- **After an approved payment, the balance changes and a red `−$840.00` flashes under it** for a few seconds. The human sees the consequence of their click right away.
- **Every approval card shows the balance *after* paying**, and turns it red if cash wouldn't cover it, before you click. (The backend refuses negative balances anyway; the UI tells you first.)
- **Payment history** on each ticket lists what was paid, who approved it, and the amount as a negative.
- The *Cash* and *Reflection* tabs in `output/desk_tickets.html` are placeholders for later problems.

## Approvals: making the human's job clear

- The approval card has an **amber tint**, the only warm-coloured block on the page, so it's what you notice.
- It says *what* (Pay invoice #501, Pay rent, Purchase order with SKU/size/qty), *why* (the agent's reason), *who asked*, *how much*, and *what's left after*.
- **Approve & pay** is the primary white button and **Reject** is the quiet one. A **name field** is required (and remembered), because every payment records `approved_by`, and agent names are refused.

## Images

We chose **hand-drawn line-art SVGs** (in `src/icons.tsx`) over photos or generated images:

- They match the monochrome theme and take the text colour, so they glow blue or green with an agent's state.
- No image files, so nothing heavy and nothing that can't go in the public repo. (The HW4 product photos stay local by your rule.)
- The illustrations are specific to Campus Customs: a size **S** tee for Tauhid's order, a striped-awning **storefront** for the rent notice, a **hoodie with a % tag** for the bulk discount.

## Colour has a job

| Colour | Meaning |
|---|---|
| White | The one primary action on screen (Run agent team, Approve & pay) |
| Blue | Something is happening now (running, working, delegating) |
| Amber | A human needs to decide |
| Green | Done or resolved |
| Red | Money leaving, refusals, errors |
| Greys | Everything else |

Because colour is rare, it always means something.

## Small touches that make it nice to use

- **Live without refreshing:** the board polls every 1.2 s while a run is active and every 4 s when idle. The feed keeps itself scrolled to the newest step *inside its own box*, so the page doesn't jump.
- **A running token count** in the feed header shows how much the run is costing as it goes.
- **Friendly empty states:** before a run, the feed shows a pulse illustration and "Run the agent team on this ticket. Each step shows up here as it happens."
- **Nothing blanks the page:** each panel sits in an error boundary. If one breaks, you get a small "click to retry" note instead of a white screen (added after the first real run exposed a crash).
- **Glass header:** the sticky header blurs the content scrolling under it, so it feels layered and calm.
- **Safe reset:** Reset DB asks for confirmation, is disabled while agents run, and keeps the audit trail.
- **Follow-up box:** after the Boss's first pass on ticket 103, the human can write their decision ("approve 10% off, fill 8 now") and the Boss continues the ticket with it. It reads like briefing a manager, not filling in a form.

## Why this feels good to use

The page follows the order a real shop manager thinks in: *what's on my desk → what's this one about → what do I need to decide → what did my team do → show me the details if I care*. The agents feel like a team rather than a log, because each has a face, a role, and a visible state. And every money moment (the amber card, the balance-after preview, the red flash when cash drops) makes the human feel in control of what the agents are allowed to do.
