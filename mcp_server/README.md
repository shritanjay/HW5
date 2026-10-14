# Campus Customs MCP Server

The shared toolbox for the Campus Customs agent team. Every agent (Boss, Inventory, Accounting, Facilities, Customer Service) gets shop data through these tools instead of touching the database directly. Built with FastMCP.

**Database:** `../data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is never modified; copy it over the working copy to reset. Override the path with the `CC_DB_PATH` env var.

Tools return only what's in the database. Two workflow tables (`approvals`, `drafts`) are added to the working copy. "Today" is always `desk.date_today`.

## Tools (17)

| # | Tool | Tables | Who can call | What it does |
|---|---|---|---|---|
| 1 | `check_stock_and_pricing(sku, size, qty_needed)` | inventory, pricing | boss, inventory, accounting | On hand, shortfall, unit cost, list price (ticket 103) |
| 2 | `check_vendor_invoice(invoice_id)` | invoices, vendors, desk | boss, inventory, accounting | Days overdue, vendor blocked?, lead time (ticket 101) |
| 3 | `check_lease_rent(lease_id)` | leases, desk, cash_accounts | boss, accounting, facilities | Rent, next due, days until due, cash (ticket 102) |
| 4 | `list_open_tickets()` | tickets, desk | boss | Every unresolved ticket on the board |
| 4b | `list_tickets()` | tickets, desk | boss, dashboard | Every ticket with open/resolved state |
| 4c | `list_approvals(status)` | approvals | boss, dashboard | Payment requests waiting on a human |
| 4d | `get_cash_balance(account)` | cash_accounts | boss, dashboard | Current checking balance |
| 5 | `get_ticket(ticket_id)` | tickets, drafts, approvals | boss, customer_service | One ticket with its drafts and approval requests |
| 6 | `update_ticket_status(ticket_id, status, note, agent)` | tickets, desk | boss | Sets status and appends a dated note |
| 7 | `list_vendors()` | vendors, invoices, desk | boss, inventory | Specialty, lead days, ETA, blocked? |
| 8 | `quote_purchase_order(sku, size, qty, vendor_id)` | inventory, pricing, vendors, invoices, cash_accounts, desk | boss, inventory, accounting | PO cost, ETA, blocked?, cash covers it? (spends nothing) |
| 9 | `check_cash_and_obligations()` | cash_accounts, invoices, vendors, leases, approvals, payments, desk | boss, accounting | Cash vs. open invoices, rent, pending approvals |
| 10 | `check_discount_margin(sku, qty, discount_pct)` | pricing | boss, accounting | Discounted price, margin, below cost?, max discount |
| 11 | `request_payment_approval(ticket_id, kind, ref_id, reason, agent, sku, size, qty)` | invoices / leases / pricing + vendors, approvals | boss, inventory, accounting, facilities | Queues a payment for a human. Amount comes from the DB. Pays nothing. |
| 12 | `save_customer_draft(ticket_id, audience, message, agent)` | tickets, drafts | customer_service only | Saves a draft on the board; never sent |
| 13 | `decide_approval(approval_id, decision, human)` | approvals, payments, cash_accounts, invoices, leases, vendors, desk | **human only** (dashboard) | Approve = pay now; reject = close. The only tool that moves money. |
| 14 | `reset_database()` | whole DB | **human only** | Copies the original over the working copy |

Agents are never given tools 13–14. `decide_approval` refuses agent names as the approver, refuses if cash would go negative, and refuses a purchase order to a vendor with an open invoice.

## Run

```bash
# from the repo root, after creating .venv and installing requirements.txt
.venv/bin/python mcp_server/server.py
```
