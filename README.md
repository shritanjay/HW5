# Campus Customs: Multi-Agent Ops Desk (HW5)

An agent team runs the Campus Customs shop. Open tickets (customer orders, rent notices, unpaid bills, discount requests) land on a board. Five PydanticAI agents (**Boss, Inventory, Accounting, Facilities, Customer Service**) work them through an **MCP server**, a **FastAPI backend** runs the team, and a **React dashboard** lets a human watch the agents and approve anything that spends money.

```
React board (:5173)  →  FastAPI backend (:8000)  →  agent team (PydanticAI)  →  MCP server  →  data/campus_customs_new.db
```

## Layout

```
AI_prompts.md          prompts used to build this, by problem
requirements.txt       Python deps (MCP server + backend)
.env.example           copy to .env and add PORTKEY_API_KEY (the real .env is never committed)
.mcp.json              registers the MCP server for Claude Code
data/
  campus_customs.db       original shop database (never modified)
  campus_customs_new.db   working copy the MCP server reads/writes (committed in its resolved state)
mcp_server/            server.py (17 FastMCP tools) + README
backend/               main.py (agent team + API routes), models.py, prompts/ (one per agent)
frontend/              React + Vite + TypeScript dashboard
output/                harness, smoke test, ticket plan vs actual, design, results, audit trail, repo URL
```

## Setup (once)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then put your PORTKEY_API_KEY in .env
cd frontend && npm install && cd ..
```

## 1. Copy the original database to the working copy (clean run)

The MCP server only works on `data/campus_customs_new.db`. `data/campus_customs.db` is the untouched original. For a clean run, copy it over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

(The dashboard's **Reset DB** button and `POST /api/reset` do the same copy through the MCP `reset_database` tool.)

## 2. Start the MCP server

The backend starts the MCP server for you (stdio) when it needs it, so you don't have to run it separately for the dashboard. To run or test it on its own:

```bash
.venv/bin/python mcp_server/server.py
```

Claude Code picks it up from `.mcp.json` when a session starts in this folder.

## 3. Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

Check: http://localhost:8000/api/health · API docs: http://localhost:8000/docs

## 4. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. The board calls the backend at `http://localhost:8000` (CORS allows the Vite origin).

## 5. Reset the database before a full three-ticket run

Always start a full run from the original values:

1. Click **Reset DB** on the board (or run `cp data/campus_customs.db data/campus_customs_new.db` while the backend is stopped). Checking should read **$3,400** and tickets 101, 102, 103 should all be open.
2. Open each ticket and click **Run agent team**.
3. Approve or reject payments in **Needs your approval** (your name is required; agents can never approve). For ticket 103, answer **The Boss needs your decision** on the discount.
4. Watch the cash drop in the header. Every step is appended to `output/audit_trail.json`.

## Shop rules the code enforces

- "Today" is `desk.date_today` (2026-08-31), not the real date.
- A vendor with an open invoice can't ship (purchase orders are refused).
- Every payment needs a human approval; the pay tool refuses if cash would go negative. Cash only goes out.
- Customer messages are drafts on the board; nothing is emailed. Only Customer Service writes drafts.
- Per-ticket caps: 30 model requests, 40 tool calls, 120k tokens; delegation depth 3, no cycles.

## Results of the graded run

Start **$3,400** → invoice 501 paid (−$840) → rent paid (−$2,400) → end **$160**, which matches `cash_accounts` in the committed working copy. All three tickets resolved. See `output/desk_tickets.html` (Expected vs Actual, Cash, Reflection), `output/resolved_tickets.json`, and `output/resolved_board.html`.
