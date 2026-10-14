"""Campus Customs backend: the agent team plus the FastAPI routes for the dashboard.

Section 1. Agent team (PydanticAI)
  The Boss runs the shop: it starts every ticket, delegates to the specialists,
  and returns the final BossDecision. All five agents get shop facts only from
  the campus-customs MCP server (no second tools layer), filtered to their role,
  plus one `delegate` tool so any agent can ask any other for help.
  Agent loop: model request -> tool calls (MCP and/or delegate) -> ... -> output;
  delegate runs the target agent's own loop and returns its AgentReport JSON.
  Guards: no self-delegation, no cycles, MAX_DEPTH, one shared UsageLimits per
  ticket, and human-only MCP tools are never given to any agent.
  Audit: every loop step (and every human approval) is appended to output/audit_trail.json.

Section 2. API routes (FastAPI) for the React dashboard
  GET  /api/tickets                 the board: every ticket, open or resolved, plus last run
  GET  /api/tickets/{id}            one ticket with its drafts and approval requests
  POST /api/tickets/{id}/run        run the agent team on one ticket (background)
  GET  /api/events                  recent agent-loop steps from output/audit_trail.json
  GET  /api/approvals               payment/PO requests the agents prepared
  POST /api/approvals/{id}          human approves or rejects; approving is what moves cash
  GET  /api/cash                    current checking balance
  POST /api/reset                   restore the original database for a fresh run
  Every route goes through the MCP server; none opens the database directly.
  A ticket resolves when no approval on it is pending and the Boss didn't leave it blocked.

Run:  cd backend && uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage, UsageLimits
from pydantic_core import to_jsonable_python

from models import AGENT_NAMES, AgentName, AgentReport, BossDecision, TraceEvent

# =============================================================================
# 1. Agent team
# =============================================================================

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPTS = HERE / "prompts"
SERVER = ROOT / "mcp_server" / "server.py"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")  # workspace-level key

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")

# ---------- token / cost limits ----------
MAX_DEPTH = 3                 # boss -> specialist -> helper -> helper
LIMITS = UsageLimits(         # per ticket, all agents combined
    request_limit=30,
    tool_calls_limit=40,
    total_tokens_limit=120_000,
)
SETTINGS = OpenAIChatModelSettings(max_tokens=1_500)  # cap each model reply
AUDIT_TEXT_MAX = 1_500        # truncate long tool results in the audit file

# ---------- role -> MCP tools (by table ownership) ----------
HUMAN_ONLY = {"decide_approval", "reset_database"}
CUSTOMER_SERVICE_ONLY = {"save_customer_draft"}  # only Customer Service writes to customers
ROLE_TOOLS: dict[AgentName, set[str] | None] = {
    "boss": None,  # every agent-safe tool except save_customer_draft, to check facts and set ticket status
    "inventory": {"check_stock_and_pricing", "list_vendors", "check_vendor_invoice", "quote_purchase_order",
                  "request_payment_approval"},
    "accounting": {"check_cash_and_obligations", "check_vendor_invoice", "check_lease_rent",
                   "check_stock_and_pricing", "check_discount_margin", "quote_purchase_order",
                   "request_payment_approval"},
    "facilities": {"check_lease_rent", "request_payment_approval"},
    "customer_service": {"get_ticket", "save_customer_draft"},
}


@dataclass
class TeamDeps:
    ticket_id: int
    me: AgentName
    chain: list[AgentName]
    run_id: str
    trace: list[TraceEvent] = field(default_factory=list)

    @property
    def depth(self) -> int:
        return len(self.chain) - 1


# ---------- audit trail (append-only JSON array) ----------
_audit_lock = threading.Lock()


def _clip(v: Any) -> Any:
    s = v if isinstance(v, str) else json.dumps(to_jsonable_python(v), default=str)
    return s if len(s) <= AUDIT_TEXT_MAX else s[:AUDIT_TEXT_MAX] + f"... [+{len(s) - AUDIT_TEXT_MAX} chars]"


def audit(deps: TeamDeps, step: str, usage: RunUsage | None = None, **detail: Any) -> None:
    """Append one agent-loop step. Never rewrites earlier entries."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "run_id": deps.run_id,
        "ticket_id": deps.ticket_id,
        "agent": deps.me,
        "chain": " -> ".join(deps.chain),
        "depth": deps.depth,
        "step": step,
        "model": MODEL_NAME,
        **detail,
    }
    if usage is not None:
        entry["usage_so_far"] = {"requests": usage.requests, "tool_calls": usage.tool_calls,
                                 "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
    with _audit_lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            log = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
        except json.JSONDecodeError:  # keep a damaged file instead of overwriting it
            AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{uuid.uuid4().hex[:6]}.json"))
            log = []
        log.append(entry)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(log, indent=1, default=str))
        tmp.replace(AUDIT_PATH)


# ---------- model, tools, agents ----------

def _model() -> OpenAIChatModel:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set (put it in .env).")
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL, default_headers={"x-portkey-api-key": key})
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


@lru_cache(maxsize=1)
def mcp_toolset() -> MCPToolset:
    return MCPToolset(SERVER)


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text() + (  # each role file = role section + shared shop rules
        f"\n\nYou are `{name}`. When a tool asks for `agent`, pass \"{name}\"."
    )


async def run_agent(name: AgentName, prompt: str, deps: TeamDeps, usage: RunUsage | None = None):
    """One agent loop, stepped node by node so each step lands in the audit trail."""
    agent = team()[name]
    audit(deps, "agent_start", prompt=_clip(prompt))
    try:
        async with agent.iter(prompt, deps=deps, usage=usage, usage_limits=LIMITS) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    returns = [{"tool": p.tool_name, "result": _clip(p.content)}
                               for p in node.request.parts if p.part_kind == "tool-return"]
                    retries = [{"tool": getattr(p, "tool_name", None), "error": _clip(p.content)}
                               for p in node.request.parts if p.part_kind == "retry-prompt"]
                    audit(deps, "model_request", run.usage, tool_results=returns or None, retries=retries or None)
                elif Agent.is_call_tools_node(node):
                    resp = node.model_response
                    calls = [{"tool": p.tool_name, "args": p.args_as_dict()}
                             for p in resp.parts if p.part_kind == "tool-call"]
                    text = " ".join(p.content for p in resp.parts if p.part_kind == "text")
                    audit(deps, "model_response", run.usage, tool_calls=calls or None,
                          text=_clip(text) if text else None,
                          tokens={"input": resp.usage.input_tokens, "output": resp.usage.output_tokens})
                elif Agent.is_end_node(node):
                    audit(deps, "agent_output", run.usage, output=to_jsonable_python(node.data.output))
        return run.result
    except Exception as e:
        audit(deps, "error", error=f"{type(e).__name__}: {e}")
        raise


async def delegate(ctx: RunContext[TeamDeps], to_agent: AgentName, task: str) -> str:
    """Ask a teammate (boss, inventory, accounting, facilities, customer_service) to do a task.
    Give them the ticket facts they need. Returns their report as JSON."""
    d = ctx.deps
    refusal = None
    if to_agent == d.me:
        refusal = f"refused: you are {d.me}; do this yourself"
    elif to_agent in d.chain:
        refusal = f"refused: {to_agent} is already in this chain ({' -> '.join(d.chain)}); answer with what you have"
    elif d.depth + 1 > MAX_DEPTH:
        refusal = "refused: delegation depth limit reached; answer with what you have"
    audit(d, "delegate", to_agent=to_agent, task=_clip(task), refused=refusal)
    if refusal:
        return refusal

    d.trace.append(TraceEvent(ticket_id=d.ticket_id, depth=d.depth + 1, kind="delegate",
                              from_agent=d.me, to_agent=to_agent, text=task))
    child = TeamDeps(ticket_id=d.ticket_id, me=to_agent, chain=[*d.chain, to_agent], run_id=d.run_id, trace=d.trace)
    result = await run_agent(to_agent, f"Ticket {d.ticket_id}. Request from {d.me}: {task}", child, ctx.usage)
    out = result.output.model_dump_json(exclude_none=True)
    d.trace.append(TraceEvent(ticket_id=d.ticket_id, depth=d.depth + 1, kind="result",
                              from_agent=to_agent, to_agent=d.me, text=out))
    return out


@lru_cache(maxsize=1)
def team() -> dict[AgentName, Agent]:
    model = _model()
    safe = mcp_toolset().filtered(lambda ctx, t: t.name not in HUMAN_ONLY)
    agents: dict[AgentName, Agent] = {}
    for name in AGENT_NAMES:
        allowed = ROLE_TOOLS[name]
        if allowed is None:  # boss: every agent-safe tool except customer drafting
            role_tools = safe.filtered(lambda ctx, t: t.name not in CUSTOMER_SERVICE_ONLY)
        else:
            role_tools = safe.filtered(lambda ctx, t, a=allowed: t.name in a)
        agents[name] = Agent(
            model,
            name=name,
            deps_type=TeamDeps,
            output_type=BossDecision if name == "boss" else AgentReport,
            instructions=_prompt(name),
            toolsets=[role_tools],
            tools=[delegate],
            model_settings=SETTINGS,
            retries=2,
        )
    return agents


async def run_team(ticket: dict, run_id: str | None = None,
                     human_note: str | None = None) -> tuple[BossDecision, list[TraceEvent]]:
    """Run the whole team on one ticket row; returns the Boss's decision and the trace.
    human_note carries the human's dashboard decision into a second pass (e.g. ticket 103)."""
    deps = TeamDeps(ticket_id=ticket["id"], me="boss", chain=["boss"], run_id=run_id or uuid.uuid4().hex[:12])
    deps.trace.append(TraceEvent(ticket_id=ticket["id"], depth=0, kind="start", to_agent="boss",
                                 text=f"{ticket['type']}: {ticket['subject']}"))
    prompt = f"New ticket from the board:\n{json.dumps(ticket)}"
    if human_note:
        prompt += f"\n\nHuman decision from the dashboard (follow it; don't re-request what's been decided):\n{human_note}"
    async with mcp_toolset():  # one MCP server process for the whole ticket
        result = await run_agent("boss", prompt, deps)
    deps.trace.append(TraceEvent(ticket_id=ticket["id"], depth=0, kind="decision", from_agent="boss",
                                 text=result.output.final_call))
    return result.output, deps.trace


# =============================================================================
# 2. API routes
# =============================================================================
log = logging.getLogger("campus_customs.api")

mcp_client = Client(SERVER)
runs: dict[int, dict[str, Any]] = {}  # ticket_id -> latest run (status, run_id, decision, error)


def _restore_runs() -> None:
    """Rebuild each ticket's latest run from the audit trail, so a server restart keeps the board."""
    try:
        trail = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
    except json.JSONDecodeError:
        return
    for e in trail:
        if e["agent"] == "boss" and e["depth"] == 0:
            if e["step"] == "agent_start":
                runs[e["ticket_id"]] = {"status": "error", "run_id": e["run_id"], "error": "run did not finish"}
            elif e["step"] == "agent_output" and runs.get(e["ticket_id"], {}).get("run_id") == e["run_id"]:
                runs[e["ticket_id"]] = {"status": "done", "run_id": e["run_id"], "decision": e["output"]}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _restore_runs()
    async with mcp_client:
        yield


app = FastAPI(title="Campus Customs Ops", lifespan=lifespan)
# The Vite dashboard's origin(s) the browser may call from. Override with
# DASHBOARD_ORIGINS="http://localhost:5173,http://127.0.0.1:5173".
DASHBOARD_ORIGINS = [o.strip() for o in os.getenv(
    "DASHBOARD_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=DASHBOARD_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp(tool: str, **args: Any) -> Any:
    """Call one MCP tool; tool-level errors become HTTP 400s."""
    res = await mcp_client.call_tool(tool, args, raise_on_error=False)
    data = res.structured_content if res.structured_content is not None else res.data
    if res.is_error or (isinstance(data, dict) and "error" in data):
        msg = data.get("error") if isinstance(data, dict) else str(res.content)
        raise HTTPException(400, msg)
    return data


# ---------- request bodies ----------

class RunRequest(BaseModel):
    human_note: str | None = Field(None, description="Human decision passed to the Boss on a second pass")


class Decision(BaseModel):
    decision: Literal["approve", "reject"]
    human: str = Field(min_length=1, description="Name of the person approving on the dashboard")
    note: str | None = None


# ---------- routes ----------

@app.get("/api/tickets")
async def list_tickets():
    board = await mcp("list_tickets")
    for t in board["tickets"]:
        t["last_run"] = runs.get(t["id"])
    return board


async def _settle(ticket_id: int, why: str, boss_status: str | None = None) -> str:
    """Decide the board status after a run or an approval.
    - any approval still pending            -> waiting_approval
    - Boss said blocked / waiting_approval  -> keep it (a human decision is still owed, e.g. 103's discount)
    - otherwise                             -> resolved
    """
    pending = [a for a in (await mcp("list_approvals", status="pending"))["approvals"] if a["ticket_id"] == ticket_id]
    if pending:
        status = "waiting_approval"
    elif boss_status in ("blocked", "waiting_approval", "in_progress"):
        status = boss_status
    else:
        status = "resolved"
    await mcp("update_ticket_status", ticket_id=ticket_id, status=status, note=why, agent="dashboard")
    return status


async def _run(ticket: dict, run_id: str, human_note: str | None) -> None:
    try:
        decision, _ = await run_team(ticket, run_id=run_id, human_note=human_note)
        status = await _settle(ticket["id"], f"agent run {run_id} finished", decision.status)
        runs[ticket["id"]] = {"status": "done", "run_id": run_id, "ticket_status": status,
                              "decision": decision.model_dump()}
    except Exception as e:  # already in the audit trail; surface it on the board too
        log.exception("run failed for ticket %s", ticket["id"])
        runs[ticket["id"]] = {"status": "error", "run_id": run_id, "error": f"{type(e).__name__}: {e}"}


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int, body: RunRequest | None = None):
    if runs.get(ticket_id, {}).get("status") == "running":
        raise HTTPException(409, f"ticket {ticket_id} is already running")
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    ticket = {k: v for k, v in ticket.items() if k not in ("drafts", "approvals")}
    if ticket["status"] == "resolved" and not (body and body.human_note):
        raise HTTPException(409, f"ticket {ticket_id} is already resolved (send a human_note to run a follow-up)")
    run_id = uuid.uuid4().hex[:12]
    runs[ticket_id] = {"status": "running", "run_id": run_id}
    asyncio.create_task(_run(ticket, run_id, body.human_note if body else None))
    return {"ticket_id": ticket_id, "run_id": run_id, "status": "running"}


@app.get("/api/tickets/{ticket_id}")
async def ticket_detail(ticket_id: int):
    """One ticket with its saved customer drafts and approval requests."""
    t = await mcp("get_ticket", ticket_id=ticket_id)
    t["last_run"] = runs.get(ticket_id)
    return t


def _event_view(i: int, e: dict) -> dict:
    """Trim an audit entry to what the board shows: who, what they said, which tools."""
    out = output = e.get("output")
    said = e.get("text") or e.get("task") or e.get("error") or e.get("refused")
    if output:
        said = output.get("final_call") or "; ".join(output.get("findings", [])) or None
    return {
        "seq": i,
        "ts": e["ts"],
        "run_id": e["run_id"],
        "ticket_id": e["ticket_id"],
        "agent": e["agent"],
        "chain": e["chain"],
        "step": e["step"],
        "said": said,
        "to_agent": e.get("to_agent"),
        "refused": e.get("refused"),
        "tool_calls": e.get("tool_calls"),
        "tool_results": e.get("tool_results"),
        "output": out,
        "usage": e.get("usage_so_far"),
    }


@app.get("/api/events")
async def events(since: int = 0, ticket_id: int | None = None, run_id: str | None = None, limit: int = 200):
    """Audit-trail steps after `since` (a seq number). Poll with the last seq to refresh."""
    try:
        trail = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
    except json.JSONDecodeError:
        trail = []
    rows = [_event_view(i, e) for i, e in enumerate(trail) if i >= since
            and (ticket_id is None or e["ticket_id"] == ticket_id)
            and (run_id is None or e["run_id"] == run_id)]
    rows = rows[-limit:]
    return {"events": rows, "next_since": len(trail)}


@app.get("/api/approvals")
async def approvals(status: str = "pending"):
    return await mcp("list_approvals", status=status)


@app.post("/api/approvals/{approval_id}")
async def decide(approval_id: int, body: Decision):
    """The human's click. Approving calls decide_approval, the only MCP tool that pays."""
    appr = next((a for a in (await mcp("list_approvals", status="all"))["approvals"] if a["id"] == approval_id), None)
    try:
        result = await mcp("decide_approval", approval_id=approval_id, decision=body.decision, human=body.human)
    except HTTPException as e:
        _audit_human(appr, body, {"error": e.detail})
        raise
    _audit_human(appr, body, result)
    if appr:
        last = (runs.get(appr["ticket_id"]) or {}).get("decision") or {}
        boss_status = last.get("status")
        if boss_status == "waiting_approval":  # the approval was what it waited on
            boss_status = None
        result["ticket_status"] = await _settle(appr["ticket_id"], f"{body.human} {body.decision}d approval {approval_id}", boss_status)
    return {**result, "cash": await mcp("get_cash_balance")}


def _audit_human(appr: dict | None, body: Decision, result: dict) -> None:
    """Human approval clicks go in the same append-only audit trail as agent steps."""
    deps = TeamDeps(ticket_id=appr["ticket_id"] if appr else 0, me="boss", chain=["human"],
                           run_id=f"human-{uuid.uuid4().hex[:8]}")
    audit(deps, "human_decision", actor=body.human, decision=body.decision,
                 approval=appr, result=result)


@app.get("/api/cash")
async def cash():
    return await mcp("get_cash_balance", account="checking")


@app.post("/api/reset")
async def reset():
    if any(r.get("status") == "running" for r in runs.values()):
        raise HTTPException(409, "wait for running tickets to finish before resetting")
    result = await mcp("reset_database")
    runs.clear()
    return {**result, "cash": await mcp("get_cash_balance")}


@app.get("/api/health")
async def health():
    return {"ok": True, "model": MODEL_NAME, "database": "data/campus_customs_new.db"}
