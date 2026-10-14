"""Typed objects shared by the Campus Customs agent team."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

ActionKind = Literal["pay_invoice", "pay_rent", "purchase_order", "discount_quote", "customer_draft", "note"]


class ProposedAction(BaseModel):
    """Something an agent wants done. Anything that moves money waits for a human."""

    kind: ActionKind
    summary: str = Field(description="One line, e.g. 'Pay invoice 501 to Bulldog Print Co'")
    amount: float | None = Field(None, description="Dollars, only if taken from a tool result")
    ref_id: int | None = Field(None, description="invoice_id, lease_id, or vendor_id the action targets")
    needs_human_approval: bool = Field(description="True for any payment or purchase order")


class AgentReport(BaseModel):
    """What a specialist (or a delegated helper) returns."""

    agent: AgentName
    findings: list[str] = Field(description="Facts from tool results only, each with its number/date")
    proposed_actions: list[ProposedAction] = []
    open_questions: list[str] = []


class BossDecision(BaseModel):
    """The Boss's final call on one ticket, shown on the dashboard."""

    ticket_id: int
    assigned_to: list[AgentName]
    final_call: str = Field(description="2-3 sentences: what happens and why")
    actions: list[ProposedAction] = []
    status: Literal["waiting_approval", "resolved", "blocked", "in_progress"]


class TraceEvent(BaseModel):
    """One step of agent work, streamed to the dashboard."""

    ticket_id: int
    depth: int
    kind: Literal["start", "delegate", "result", "decision", "error"]
    from_agent: AgentName | None = None
    to_agent: AgentName | None = None
    text: str
