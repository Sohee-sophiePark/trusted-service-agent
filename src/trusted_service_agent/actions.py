"""Deterministic, read-only lookups. Every function needs a verified session; none writes."""

from trusted_service_agent.identity import NotVerified, Session
from trusted_service_agent.warehouse import Warehouse


def _acct(s: Session) -> str:
    if not s.account_number:
        raise NotVerified("identity must be verified before account data")
    return s.account_number


def account_summary(wh: Warehouse, s: Session) -> dict:
    acct = _acct(s)
    plan = wh.rows(
        "SELECT plan, monthly_price, autopay FROM servicing.account WHERE account_number = ?",
        [acct],
    )[0]
    bill = wh.rows(
        "SELECT issued, due, total, status FROM servicing.bill WHERE account_number = ? ORDER BY issued DESC LIMIT 1",
        [acct],
    )[0]
    pay = wh.rows(
        "SELECT paid_on, amount, method FROM servicing.payment WHERE account_number = ? ORDER BY paid_on DESC LIMIT 1",
        [acct],
    )
    return {
        "plan": plan,
        "latest_bill": bill,
        "last_payment": pay[0] if pay else None,
        "balance_due": float(bill["total"]) if bill["status"] == "open" else 0.0,
    }


def ticket_status(wh: Warehouse, s: Session, ticket_id: str | None = None) -> list[dict]:
    """The account's open tickets (or one ticket), each with how old its last update is."""
    acct = _acct(s)
    sql = (
        "SELECT ticket_id, kind, status, window_date, window_slot, last_update FROM servicing.service_order "
        "WHERE account_number = ? AND status <> 'Completed'"
    )
    params = [acct]
    if ticket_id:
        sql, params = sql + " AND ticket_id = ?", [acct, ticket_id]
    return wh.rows(sql + " ORDER BY window_date", params)


def outages(wh: Warehouse, s: Session) -> list[dict]:
    acct = _acct(s)
    return wh.rows(
        "SELECT o.outage_id, o.service, o.started, o.est_restore FROM servicing.outage_event o "
        "JOIN servicing.customer c ON left(replace(c.postal_code, ' ', ''), 3) = o.area_postal_prefix "
        "JOIN servicing.account a ON a.customer_id = c.customer_id "
        "WHERE a.account_number = ? AND o.status = 'active'",
        [acct],
    )


def overview(wh: Warehouse, s: Session) -> dict:
    """What the verified customer has open now: tickets, area outages, latest bill (display-ready)."""
    a = account_summary(wh, s)
    return {
        "tickets": [
            {
                "id": t["ticket_id"],
                "kind": t["kind"],
                "status": t["status"],
                "window": f"{t['window_date']:%b %d}, {t['window_slot']}",
            }
            for t in ticket_status(wh, s)
        ],
        "outages": [
            {"service": o["service"], "restore": f"{o['est_restore']:%H:%M}"}
            for o in outages(wh, s)
        ],
        "bill": {
            "plan": a["plan"]["plan"],
            "autopay": a["plan"]["autopay"],
            "issued": f"{a['latest_bill']['issued']:%b %d}",
            "total": float(a["latest_bill"]["total"]),
            "status": a["latest_bill"]["status"],
            "due": a["balance_due"],
        },
    }
