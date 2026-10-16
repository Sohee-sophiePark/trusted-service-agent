"""Build the fictional Tessaline warehouse (Snowflake-style tables) into data/warehouse.duckdb, deterministically."""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
AS_OF = date(2026, 10, 14)

FIRST = [
    "Ava",
    "Liam",
    "Maya",
    "Noah",
    "Zara",
    "Ethan",
    "Priya",
    "Lucas",
    "Amara",
    "Owen",
    "Mei",
    "Jonah",
    "Sofia",
    "Kai",
    "Leila",
    "Marcus",
    "Nadia",
    "Theo",
    "Ines",
    "Ravi",
]
LAST = [
    "Chen",
    "Okafor",
    "Tremblay",
    "Singh",
    "Martin",
    "Haddad",
    "Nguyen",
    "Roy",
    "Kowalski",
    "Mensah",
    "Gagnon",
    "Ali",
    "Fraser",
    "Lopez",
    "Ito",
    "Brennan",
]
POSTAL = [
    "M5V 2T6",
    "M4C 1B5",
    "K1P 5J2",
    "H2X 3Y7",
    "V6B 1A1",
    "T2P 0L4",
    "R3C 4T3",
    "B3J 1P3",
    "L5B 3C2",
    "N2L 3G1",
]
PLANS = {
    "Essential": 45.0,
    "Plus": 60.0,
    "Unlimited": 80.0,
    "Internet 500": 70.0,
    "Internet 1G": 90.0,
}

# Week-1 baseline mined from case history and transcripts (scenario script §3; fictional).
BASELINE = [
    ("Billing & account questions", "account_questions", 0.26, 8.2, 0.61, 0.27, "in_mvp_slice"),
    ("Install / repair ticket status", "ticket_status", 0.18, 5.1, 0.74, 0.21, "in_mvp_slice"),
    ("Outage / service status", "ticket_status", 0.14, 4.0, 0.80, 0.18, "in_mvp_slice"),
    ("Technical troubleshooting", None, 0.15, 11.5, 0.58, 0.30, "out_not_simple"),
    ("Plan & product questions", "product_guidance", 0.12, 7.0, 0.70, 0.14, "in_mvp_slice"),
    ("Moves, changes, cancellations", None, 0.09, 9.8, 0.66, 0.19, "out_money"),
    ("Complaints & disputes", None, 0.06, 13.0, 0.41, 0.33, "out_never"),
]

SCHEMA = """
CREATE SCHEMA servicing;
CREATE TABLE servicing.customer (customer_id VARCHAR PRIMARY KEY, first_name VARCHAR, last_name VARCHAR, postal_code VARCHAR, since DATE);
CREATE TABLE servicing.account (account_number VARCHAR PRIMARY KEY, customer_id VARCHAR, plan VARCHAR, monthly_price DECIMAL(8,2), cycle_day INTEGER, autopay BOOLEAN);
CREATE TABLE servicing.bill (bill_id VARCHAR PRIMARY KEY, account_number VARCHAR, issued DATE, due DATE, total DECIMAL(8,2), status VARCHAR);
CREATE TABLE servicing.bill_line (bill_id VARCHAR, description VARCHAR, amount DECIMAL(8,2));
CREATE TABLE servicing.payment (account_number VARCHAR, paid_on DATE, amount DECIMAL(8,2), method VARCHAR);
CREATE TABLE servicing.service_order (ticket_id VARCHAR PRIMARY KEY, account_number VARCHAR, kind VARCHAR, status VARCHAR, window_date DATE, window_slot VARCHAR, last_update TIMESTAMP);
CREATE TABLE servicing.outage_event (outage_id VARCHAR, area_postal_prefix VARCHAR, service VARCHAR, started TIMESTAMP, est_restore TIMESTAMP, status VARCHAR);
CREATE TABLE servicing.contact_baseline (contact_reason VARCHAR, topic VARCHAR, share DOUBLE, aht_min DOUBLE, fcr DOUBLE, repeat_7d DOUBLE, mvp VARCHAR);
"""


def build(path: Path) -> None:
    """Recreate the warehouse at `path` from the fixed seed."""
    rng = random.Random(18)
    path.unlink(missing_ok=True)
    con = duckdb.connect(str(path))
    con.execute(SCHEMA)
    for i in range(40):
        cid, acct = f"C{1000 + i}", f"TS-{100200 + i}"
        plan = rng.choice(list(PLANS))
        plan = "Unlimited" if i == 3 else plan  # upgraded mid-cycle (prorated line below)
        cycle = rng.choice([1, 8, 15, 22])
        con.execute(
            "INSERT INTO servicing.customer VALUES (?,?,?,?,?)",
            [
                cid,
                rng.choice(FIRST),
                rng.choice(LAST),
                rng.choice(POSTAL),
                AS_OF - timedelta(days=rng.randint(200, 3000)),
            ],
        )
        con.execute(
            "INSERT INTO servicing.account VALUES (?,?,?,?,?,?)",
            [acct, cid, plan, PLANS[plan], cycle, rng.random() < 0.6],
        )
        for k, months_back in enumerate([1, 0]):
            issued = date(2026, 10 - months_back, cycle)
            if issued > AS_OF:
                issued = date(2026, 9 - months_back, cycle)
            total = PLANS[plan] * 1.13
            bill_id = f"B-{acct}-{k}"
            lines = [
                (f"{plan} monthly charge", PLANS[plan]),
                ("Taxes", round(PLANS[plan] * 0.13, 2)),
            ]
            if i == 3 and months_back == 0:  # mid-cycle upgrade → prorated line on the latest bill
                lines.insert(1, ("Unlimited prorated charge, 11 days", 7.33))
                total += 7.33
            paid = months_back == 1 or rng.random() < 0.4
            con.execute(
                "INSERT INTO servicing.bill VALUES (?,?,?,?,?,?)",
                [
                    bill_id,
                    acct,
                    issued,
                    issued + timedelta(days=21),
                    round(total, 2),
                    "paid" if paid else "open",
                ],
            )
            for desc, amt in lines:
                con.execute("INSERT INTO servicing.bill_line VALUES (?,?,?)", [bill_id, desc, amt])
            if paid:
                con.execute(
                    "INSERT INTO servicing.payment VALUES (?,?,?,?)",
                    [
                        acct,
                        issued + timedelta(days=rng.randint(3, 20)),
                        round(total, 2),
                        rng.choice(["pre-authorized debit", "credit card", "online banking"]),
                    ],
                )
    statuses = [
        "Received",
        "Scheduled",
        "Technician en route",
        "In progress",
        "On hold",
        "Completed",
    ]
    for t in range(30):
        acct = f"TS-{100200 + rng.randrange(40)}"
        tid = "44812" if t == 0 else str(44800 + t * 7)
        status = "Scheduled" if t == 0 else rng.choice(statuses)
        last = AS_OF.isoformat() + (
            " 09:40:00"
            if t == 0
            else f" {rng.randint(7, 18):02d}:{rng.choice(['05', '20', '35', '50'])}:00"
        )
        con.execute(
            "INSERT INTO servicing.service_order VALUES (?,?,?,?,?,?,?)",
            [
                tid,
                acct if t else "TS-100201",
                rng.choice(["installation", "repair"]),
                status,
                AS_OF + timedelta(days=rng.randint(0, 4)),
                rng.choice(["8 am-12 pm", "12 pm-4 pm", "4 pm-8 pm"]),
                last,
            ],
        )
    con.execute(
        "INSERT INTO servicing.outage_event VALUES ('OUT-2291','M4C','home internet','2026-10-14 06:10:00','2026-10-14 15:00:00','active')"
    )
    con.execute(
        "INSERT INTO servicing.outage_event VALUES ('OUT-2284','K1P','mobile','2026-10-12 21:00:00','2026-10-13 02:00:00','resolved')"
    )
    con.executemany("INSERT INTO servicing.contact_baseline VALUES (?,?,?,?,?,?,?)", BASELINE)
    con.close()


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "warehouse.duckdb"
    build(out)
    print("wrote", out)
