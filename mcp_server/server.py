"""Campus Customs MCP server (FastMCP).

Every agent on the team uses these tools. They talk only to the working copy
data/campus_customs_new.db; the original data/campus_customs.db is never touched.

Rules:
- "today" is desk.date_today, never the real clock.
- Tools return only what is in the database. Missing records come back as an
  error, never as made-up values.
- A vendor with an open invoice cannot ship new product.
- Money moves only through pay_* tools, and only against an approval a human
  marked "approved" (decide_approval). Agents can request approvals but are
  never given decide_approval or pay_* tools. Payments refuse if cash would go
  negative. Cash only goes out.
- Customer messages are drafts saved on the board; nothing is sent.
"""

import os
import shutil
import sqlite3
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastmcp import FastMCP

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(os.getenv("CC_DB_PATH", DATA_DIR / "campus_customs_new.db"))
ORIGINAL_DB = DATA_DIR / "campus_customs.db"

# Workflow tables the board needs (the shop tables are untouched). Created on
# the working copy only, so a reset from the original simply recreates them.
WORKFLOW_SQL = """
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    kind TEXT NOT NULL,              -- pay_invoice | pay_rent | purchase_order
    ref_id INTEGER NOT NULL,         -- invoice_id | lease_id | vendor_id
    sku TEXT, size TEXT, qty INTEGER, -- purchase orders only
    amount REAL NOT NULL,
    reason TEXT,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | paid
    decided_by TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    audience TEXT NOT NULL,
    message TEXT NOT NULL,
    written_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service", "agent", "system"}

mcp = FastMCP("campus-customs")


def query(sql: str, args: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def shop_today() -> date:
    return date.fromisoformat(query("SELECT date_today FROM desk")[0]["date_today"])


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(WORKFLOW_SQL)
    return conn


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def vendor_block(vendor_id: int) -> list[int]:
    return [r["id"] for r in query("SELECT id FROM invoices WHERE vendor_id=? AND status='open'", (vendor_id,))]


def add_month(d: date) -> date:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, min(d.day, monthrange(y, m)[1]))


@mcp.tool
def check_stock_and_pricing(sku: str, size: str, qty_needed: int) -> dict:
    """Stock on hand for one SKU and size, the shortfall against qty_needed,
    and the SKU's unit_cost and list_price. Reads inventory and pricing."""
    stock = query("SELECT name, qty, location FROM inventory WHERE sku=? AND size=?", (sku, size))
    if not stock:
        return {"error": f"no inventory row for {sku} size {size}"}
    price = query("SELECT unit_cost, list_price FROM pricing WHERE sku=?", (sku,))
    if not price:
        return {"error": f"no pricing row for {sku}"}
    s, p = stock[0], price[0]
    return {
        "sku": sku,
        "name": s["name"],
        "size": size,
        "on_hand": s["qty"],
        "qty_needed": qty_needed,
        "shortfall": max(0, qty_needed - s["qty"]),
        "location": s["location"],
        "unit_cost": p["unit_cost"],
        "list_price": p["list_price"],
    }


@mcp.tool
def check_vendor_invoice(invoice_id: int) -> dict:
    """One invoice with its vendor: amount, due date, status, days overdue
    against the shop date, the vendor's lead_days, and whether the vendor is
    blocked from shipping by any open invoice. Reads invoices, vendors, desk."""
    inv = query(
        "SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, i.description, "
        "v.name AS vendor, v.specialty, v.lead_days "
        "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id=?",
        (invoice_id,),
    )
    if not inv:
        return {"error": f"invoice {invoice_id} not found"}
    inv = inv[0]
    today = shop_today()
    open_ids = [r["id"] for r in query(
        "SELECT id FROM invoices WHERE vendor_id=? AND status='open'", (inv["vendor_id"],)
    )]
    overdue = (today - date.fromisoformat(inv["due_date"])).days
    return {
        **inv,
        "shop_today": today.isoformat(),
        "days_overdue": overdue if inv["status"] == "open" and overdue > 0 else 0,
        "vendor_blocked": bool(open_ids),
        "open_invoice_ids": open_ids,
        "restock_eta_if_unblocked": (today + timedelta(days=inv["lead_days"])).isoformat(),
    }


@mcp.tool
def check_lease_rent(lease_id: int) -> dict:
    """One lease: landlord, monthly rent, next due date, days until due against
    the shop date (negative means overdue), and the checking balance so the
    team can see if rent is affordable. Reads leases, desk, cash_accounts."""
    lease = query("SELECT * FROM leases WHERE id=?", (lease_id,))
    if not lease:
        return {"error": f"lease {lease_id} not found"}
    lease = lease[0]
    today = shop_today()
    cash = query("SELECT name, balance FROM cash_accounts")
    days = (date.fromisoformat(lease["next_due"]) - today).days
    return {
        **lease,
        "shop_today": today.isoformat(),
        "days_until_due": days,
        "overdue": days < 0,
        "cash_accounts": cash,
    }


# ---------- board ----------

@mcp.tool
def list_open_tickets() -> dict:
    """The board: every ticket not yet resolved, plus the shop date. Reads tickets, desk."""
    return {
        "shop_today": shop_today().isoformat(),
        "tickets": query("SELECT * FROM tickets WHERE status != 'resolved' ORDER BY id"),
    }


@mcp.tool
def list_tickets() -> dict:
    """Every ticket with its status and whether it is open or resolved. Reads tickets, desk."""
    tickets = query("SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, "
                    "created_at FROM tickets ORDER BY id")
    for t in tickets:
        t["state"] = "resolved" if t["status"] == "resolved" else "open"
    return {"shop_today": shop_today().isoformat(), "tickets": tickets}


@mcp.tool
def list_approvals(status: str = "pending") -> dict:
    """Payment approval requests by status (pending | approved | rejected | paid | all). Reads approvals."""
    with connect() as conn:
        if status == "all":
            rows_ = conn.execute("SELECT * FROM approvals ORDER BY id")
        else:
            rows_ = conn.execute("SELECT * FROM approvals WHERE status=? ORDER BY id", (status,))
        return {"approvals": [dict(r) for r in rows_]}


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict:
    """Current balance of one cash account. Reads cash_accounts."""
    r = query("SELECT name, balance, date FROM cash_accounts WHERE name=?", (account,))
    return r[0] if r else {"error": f"no cash account '{account}'"}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """One ticket with its saved drafts and approval requests. Reads tickets, drafts, approvals."""
    t = query("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not t:
        return {"error": f"ticket {ticket_id} not found"}
    with connect() as conn:
        drafts = [dict(r) for r in conn.execute("SELECT * FROM drafts WHERE ticket_id=?", (ticket_id,))]
        appr = [dict(r) for r in conn.execute("SELECT * FROM approvals WHERE ticket_id=?", (ticket_id,))]
    return {**t[0], "drafts": drafts, "approvals": appr}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str, agent: str) -> dict:
    """Boss only: set a ticket's status (in_progress | waiting_approval | blocked | resolved) and log a note."""
    if status not in {"open", "in_progress", "waiting_approval", "blocked", "resolved"}:
        return {"error": f"unknown status '{status}'"}
    with connect() as conn:
        cur = conn.execute(
            "UPDATE tickets SET status=?, notes=COALESCE(notes,'') || char(10) || ? WHERE id=?",
            (status, f"[{shop_today()} {agent}] {note}", ticket_id),
        )
    if cur.rowcount == 0:
        return {"error": f"ticket {ticket_id} not found"}
    return {"ok": True, "ticket_id": ticket_id, "status": status}


# ---------- inventory ----------

@mcp.tool
def list_vendors() -> dict:
    """All vendors: specialty, lead_days, restock ETA from the shop date, and whether an open
    invoice blocks them from shipping. Reads vendors, invoices, desk."""
    today = shop_today()
    vendors = query("SELECT * FROM vendors ORDER BY id")
    for v in vendors:
        v["open_invoice_ids"] = vendor_block(v["id"])
        v["blocked"] = bool(v["open_invoice_ids"])
        v["eta_if_ordered_today"] = (today + timedelta(days=v["lead_days"])).isoformat()
    return {"shop_today": today.isoformat(), "vendors": vendors}


@mcp.tool
def quote_purchase_order(sku: str, size: str, qty: int, vendor_id: int) -> dict:
    """Cost and ETA for a restock PO (qty x unit_cost), whether the vendor is blocked, and
    whether checking cash covers it. Spends nothing. Reads pricing, inventory, vendors, invoices, cash_accounts."""
    if not query("SELECT 1 FROM inventory WHERE sku=? AND size=?", (sku, size)):
        return {"error": f"no inventory row for {sku} size {size}"}
    p = query("SELECT unit_cost FROM pricing WHERE sku=?", (sku,))
    v = query("SELECT name, specialty, lead_days FROM vendors WHERE id=?", (vendor_id,))
    if not p or not v:
        return {"error": "unknown sku pricing or vendor"}
    cost = round(p[0]["unit_cost"] * qty, 2)
    cash = query("SELECT balance FROM cash_accounts WHERE name='checking'")[0]["balance"]
    blockers = vendor_block(vendor_id)
    return {
        "sku": sku, "size": size, "qty": qty, "vendor_id": vendor_id, "vendor": v[0]["name"],
        "specialty": v[0]["specialty"], "unit_cost": p[0]["unit_cost"], "cost": cost,
        "eta": (shop_today() + timedelta(days=v[0]["lead_days"])).isoformat(),
        "vendor_blocked": bool(blockers), "open_invoice_ids": blockers,
        "checking_balance": cash, "cash_covers_it": cash >= cost,
    }


# ---------- accounting ----------

@mcp.tool
def check_cash_and_obligations() -> dict:
    """Cash balances, every open invoice (with days overdue), rent coming due, approvals already
    pending, and payments made. Reads cash_accounts, invoices, vendors, leases, approvals, payments, desk."""
    today = shop_today()
    invoices = query(
        "SELECT i.id, i.vendor_id, v.name AS vendor, i.amount, i.due_date, i.description "
        "FROM invoices i JOIN vendors v ON v.id=i.vendor_id WHERE i.status='open' ORDER BY i.due_date"
    )
    for i in invoices:
        i["days_overdue"] = max(0, (today - date.fromisoformat(i["due_date"])).days)
    leases = query("SELECT id, landlord, monthly_rent, next_due FROM leases ORDER BY next_due")
    for l in leases:
        l["days_until_due"] = (date.fromisoformat(l["next_due"]) - today).days
    with connect() as conn:
        pending = [dict(r) for r in conn.execute(
            "SELECT id, ticket_id, kind, ref_id, amount FROM approvals WHERE status IN ('pending','approved')")]
    cash = query("SELECT name, balance FROM cash_accounts")
    committed = round(sum(a["amount"] for a in pending), 2)
    return {
        "shop_today": today.isoformat(),
        "cash_accounts": cash,
        "open_invoices": invoices,
        "rent": leases,
        "pending_approvals": pending,
        "checking_after_pending": round(cash[0]["balance"] - committed, 2) if cash else None,
        "payments": query("SELECT * FROM payments ORDER BY id"),
    }


@mcp.tool
def check_discount_margin(sku: str, qty: int, discount_pct: float) -> dict:
    """Margin check for a proposed discount off list_price: unit price, margin per unit, total,
    and whether it falls below unit_cost. Reads pricing."""
    p = query("SELECT unit_cost, list_price FROM pricing WHERE sku=?", (sku,))
    if not p:
        return {"error": f"no pricing row for {sku}"}
    cost, lst = p[0]["unit_cost"], p[0]["list_price"]
    unit = round(lst * (1 - discount_pct / 100), 2)
    return {
        "sku": sku, "qty": qty, "discount_pct": discount_pct, "list_price": lst, "unit_cost": cost,
        "unit_price": unit, "total_price": round(unit * qty, 2),
        "margin_per_unit": round(unit - cost, 2), "margin_pct": round(100 * (unit - cost) / unit, 1) if unit else None,
        "total_margin": round((unit - cost) * qty, 2), "below_cost": unit < cost,
        "max_discount_pct_at_cost": round(100 * (1 - cost / lst), 1),
    }


@mcp.tool
def request_payment_approval(ticket_id: int, kind: str, ref_id: int, reason: str, agent: str,
                             sku: str = "", size: str = "", qty: int = 0) -> dict:
    """Put a payment on the board for a human to approve. Does NOT pay. kind: pay_invoice
    (ref_id=invoice_id), pay_rent (ref_id=lease_id), purchase_order (ref_id=vendor_id + sku/size/qty).
    The amount is taken from the database, never from the caller."""
    if kind == "pay_invoice":
        r = query("SELECT amount, status FROM invoices WHERE id=?", (ref_id,))
        if not r:
            return {"error": f"invoice {ref_id} not found"}
        if r[0]["status"] != "open":
            return {"error": f"invoice {ref_id} is {r[0]['status']}, nothing to pay"}
        amount = r[0]["amount"]
    elif kind == "pay_rent":
        r = query("SELECT monthly_rent FROM leases WHERE id=?", (ref_id,))
        if not r:
            return {"error": f"lease {ref_id} not found"}
        amount = r[0]["monthly_rent"]
    elif kind == "purchase_order":
        q = quote_purchase_order(sku, size, qty, ref_id)
        if "error" in q:
            return q
        amount = q["cost"]
    else:
        return {"error": "kind must be pay_invoice, pay_rent, or purchase_order"}
    with connect() as conn:
        dup = conn.execute(
            "SELECT id FROM approvals WHERE kind=? AND ref_id=? AND status IN ('pending','approved') "
            "AND COALESCE(sku,'')=? AND COALESCE(size,'')=?", (kind, ref_id, sku, size)).fetchone()
        if dup:
            return {"ok": True, "approval_id": dup["id"], "note": "already on the board"}
        cur = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, ref_id, sku, size, qty, amount, reason, requested_by, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ticket_id, kind, ref_id, sku or None, size or None, qty or None, amount, reason, agent, now()))
    return {"ok": True, "approval_id": cur.lastrowid, "amount": amount, "status": "pending", "paid": False}


# ---------- customer service ----------

@mcp.tool
def save_customer_draft(ticket_id: int, audience: str, message: str, agent: str) -> dict:
    """Save a message draft on the board for a human to review. Nothing is emailed or sent."""
    if not query("SELECT 1 FROM tickets WHERE id=?", (ticket_id,)):
        return {"error": f"ticket {ticket_id} not found"}
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, audience, message, written_by, created_at) VALUES (?,?,?,?,?)",
            (ticket_id, audience, message, agent, now()))
    return {"ok": True, "draft_id": cur.lastrowid, "sent": False}


# ---------- human-only (dashboard), never given to agents ----------

def _spend(conn: sqlite3.Connection, kind: str, ref_id: int, amount: float, approved_by: str) -> dict:
    bal = conn.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()["balance"]
    if bal < amount:
        raise ValueError(f"refused: insufficient cash (checking {bal:.2f}, need {amount:.2f})")
    paid_at = shop_today().isoformat()
    conn.execute("UPDATE cash_accounts SET balance=balance-?, date=? WHERE name='checking'", (amount, paid_at))
    cur = conn.execute(
        "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?,?,?,?,?,?)",
        (kind, ref_id, amount, "checking", paid_at, approved_by))
    after = conn.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()["balance"]
    return {"payment_id": cur.lastrowid, "amount": amount, "checking_after": after}


@mcp.tool
def decide_approval(approval_id: int, decision: str, human: str) -> dict:
    """HUMAN ONLY (dashboard). decision 'approve' pays it now; 'reject' closes it.
    Paying updates payments, cash_accounts, and the invoice/lease. Refuses if cash is short."""
    if human.strip().lower() in AGENT_NAMES or not human.strip():
        return {"error": "refused: approvals must come from a named human"}
    if decision not in {"approve", "reject"}:
        return {"error": "decision must be 'approve' or 'reject'"}
    try:
        with connect() as conn:
            a = conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
            if a is None:
                return {"error": f"approval {approval_id} not found"}
            if a["status"] != "pending":
                return {"error": f"approval {approval_id} is already {a['status']}"}
            if decision == "reject":
                conn.execute("UPDATE approvals SET status='rejected', decided_by=? WHERE id=?", (human, approval_id))
                return {"ok": True, "approval_id": approval_id, "status": "rejected"}
            extra = {}
            if a["kind"] == "pay_invoice":
                inv = conn.execute("SELECT status FROM invoices WHERE id=?", (a["ref_id"],)).fetchone()
                if inv is None or inv["status"] != "open":
                    return {"error": f"invoice {a['ref_id']} is not open"}
                res = _spend(conn, "invoice", a["ref_id"], a["amount"], human)
                conn.execute("UPDATE invoices SET status='paid' WHERE id=?", (a["ref_id"],))
            elif a["kind"] == "pay_rent":
                lease = conn.execute("SELECT next_due FROM leases WHERE id=?", (a["ref_id"],)).fetchone()
                res = _spend(conn, "rent", a["ref_id"], a["amount"], human)
                extra["next_due"] = add_month(date.fromisoformat(lease["next_due"])).isoformat()
                conn.execute("UPDATE leases SET next_due=? WHERE id=?", (extra["next_due"], a["ref_id"]))
            else:  # purchase_order
                blockers = [r["id"] for r in conn.execute(
                    "SELECT id FROM invoices WHERE vendor_id=? AND status='open'", (a["ref_id"],))]
                if blockers:
                    return {"error": f"refused: vendor {a['ref_id']} has open invoice(s) {blockers}; pay those first"}
                res = _spend(conn, "purchase_order", a["ref_id"], a["amount"], human)
                lead = conn.execute("SELECT lead_days FROM vendors WHERE id=?", (a["ref_id"],)).fetchone()["lead_days"]
                extra["eta"] = (shop_today() + timedelta(days=lead)).isoformat()
            conn.execute("UPDATE approvals SET status='paid', decided_by=? WHERE id=?", (human, approval_id))
    except ValueError as e:
        return {"error": str(e)}
    return {"ok": True, "approval_id": approval_id, "status": "paid", **res, **extra}


@mcp.tool
def reset_database() -> dict:
    """HUMAN ONLY. Copy the untouched original over the working copy before a full run."""
    shutil.copyfile(ORIGINAL_DB, DB_PATH)
    return {"ok": True, "reset_at": now()}


if __name__ == "__main__":
    mcp.run()
