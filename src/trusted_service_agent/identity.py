"""Identity gate: account number + service-address postal code, checked before any account data."""

from dataclasses import dataclass

from trusted_service_agent.warehouse import Warehouse


@dataclass(frozen=True)
class Session:
    account_number: str | None = None  # set only after a successful verification


class NotVerified(PermissionError):
    pass


def verify(wh: Warehouse, account_number: str, postal_code: str) -> Session:
    """Return a verified session, or an unverified one when the pair does not match."""
    rows = wh.rows(
        "SELECT a.account_number FROM servicing.account a JOIN servicing.customer c USING (customer_id) "
        "WHERE a.account_number = ? AND replace(upper(c.postal_code), ' ', '') = ?",
        [account_number.strip().upper(), postal_code.replace(" ", "").upper()],
    )
    return Session(rows[0]["account_number"] if rows else None)
