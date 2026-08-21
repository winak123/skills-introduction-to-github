"""SQLite persistence. One file, no server, easy to back up and inspect."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from . import normalize as nz
from .models import Lead

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id             TEXT PRIMARY KEY,
    lead_type           TEXT NOT NULL,
    source              TEXT,
    county              TEXT,
    state               TEXT,
    contact_name        TEXT,
    contact_role        TEXT,
    mailing_address     TEXT,
    mailing_city        TEXT,
    mailing_state       TEXT,
    mailing_zip         TEXT,
    phone               TEXT,
    email               TEXT,
    subject_name        TEXT,
    case_number         TEXT,
    filed_date          TEXT,
    event_date          TEXT,
    property_address    TEXT,
    property_city       TEXT,
    property_state      TEXT,
    property_zip        TEXT,
    apn                 TEXT,
    assessed_value      REAL,
    estimated_mortgage  REAL,
    property_vacant     INTEGER,
    heir_count          INTEGER,
    score               INTEGER,
    score_reasons       TEXT,
    compliance_flags    TEXT,
    contactable_channels TEXT,
    raw                 TEXT,
    first_seen          TEXT DEFAULT CURRENT_TIMESTAMP,
    last_updated        TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_type  ON leads(lead_type);

-- Outreach history. The TCPA requires you to honor and retain do-not-call
-- requests for five years, so nothing here is ever deleted.
CREATE TABLE IF NOT EXISTS outreach (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id   TEXT NOT NULL,
    channel   TEXT NOT NULL,
    sent_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    body      TEXT,
    outcome   TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
);

CREATE TABLE IF NOT EXISTS suppression (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phone      TEXT,
    email      TEXT,
    address    TEXT,
    reason     TEXT,
    added_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

_COLUMNS = [
    "lead_id", "lead_type", "source", "county", "state", "contact_name",
    "contact_role", "mailing_address", "mailing_city", "mailing_state",
    "mailing_zip", "phone", "email", "subject_name", "case_number",
    "filed_date", "event_date", "property_address", "property_city",
    "property_state", "property_zip", "apn", "assessed_value",
    "estimated_mortgage", "property_vacant", "heir_count", "score",
    "score_reasons", "compliance_flags", "contactable_channels", "raw",
]


class Store:
    def __init__(self, path: str | Path = "leads.db"):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def upsert(self, lead: Lead) -> bool:
        """Insert or update one lead. Returns True if it was new."""
        d = lead.to_dict()
        d["score_reasons"] = json.dumps(lead.score_reasons)
        d["compliance_flags"] = json.dumps(lead.compliance_flags)
        d["contactable_channels"] = json.dumps(lead.contactable_channels)
        d["raw"] = json.dumps(lead.raw, default=str)
        d["property_vacant"] = (
            None if lead.property_vacant is None else int(lead.property_vacant)
        )

        existing = self.conn.execute(
            "SELECT 1 FROM leads WHERE lead_id = ?", (lead.lead_id,)
        ).fetchone()

        placeholders = ", ".join(f":{c}" for c in _COLUMNS)
        columns = ", ".join(_COLUMNS)
        updates = ", ".join(f"{c} = :{c}" for c in _COLUMNS if c != "lead_id")

        self.conn.execute(
            f"INSERT INTO leads ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(lead_id) DO UPDATE SET {updates}, "
            f"last_updated = CURRENT_TIMESTAMP",
            {c: d.get(c) for c in _COLUMNS},
        )
        self.conn.commit()
        return existing is None

    def upsert_many(self, leads: Iterable[Lead]) -> tuple[int, int]:
        new = updated = 0
        for lead in leads:
            if self.upsert(lead):
                new += 1
            else:
                updated += 1
        return new, updated

    def rows(self, *, min_score: int = 0, lead_type: Optional[str] = None,
             limit: Optional[int] = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM leads WHERE COALESCE(score, 0) >= ?"
        params: list[Any] = [min_score]
        if lead_type:
            sql += " AND lead_type = ?"
            params.append(lead_type)
        sql += " ORDER BY COALESCE(score, 0) DESC, last_updated DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.conn.execute(sql, params).fetchall()

    def get(self, lead_id: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM leads WHERE lead_id = ?", (lead_id,)
        ).fetchone()

    def log_outreach(self, lead_id: str, channel: str, body: str,
                     outcome: str = "drafted") -> None:
        self.conn.execute(
            "INSERT INTO outreach (lead_id, channel, body, outcome) "
            "VALUES (?, ?, ?, ?)",
            (lead_id, channel, body, outcome),
        )
        self.conn.commit()

    def suppress(self, *, phone: str = "", email: str = "", address: str = "",
                 reason: str = "manual") -> None:
        self.conn.execute(
            "INSERT INTO suppression (phone, email, address, reason) "
            "VALUES (?, ?, ?, ?)",
            (
                nz.normalize_phone(phone),
                nz.normalize_email(email),
                nz.normalize_address(address, drop_unit=True),
                reason,
            ),
        )
        self.conn.commit()

    def suppression_list(self):
        from .compliance import SuppressionList

        rows = self.conn.execute(
            "SELECT phone, email, address FROM suppression"
        ).fetchall()
        return SuppressionList(
            phones={r["phone"] for r in rows if r["phone"]},
            emails={r["email"] for r in rows if r["email"]},
            addresses={r["address"] for r in rows if r["address"]},
        )

    def stats(self) -> dict[str, Any]:
        c = self.conn
        total = c.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"]
        by_type = {
            r["lead_type"]: r["n"]
            for r in c.execute(
                "SELECT lead_type, COUNT(*) n FROM leads GROUP BY lead_type"
            )
        }
        by_tier = {
            r["tier"]: r["n"]
            for r in c.execute(
                "SELECT CASE WHEN score >= 75 THEN 'A' WHEN score >= 55 THEN 'B' "
                "WHEN score >= 35 THEN 'C' ELSE 'D' END tier, COUNT(*) n "
                "FROM leads WHERE score IS NOT NULL GROUP BY tier"
            )
        }
        contacted = c.execute(
            "SELECT COUNT(DISTINCT lead_id) n FROM outreach"
        ).fetchone()["n"]
        suppressed = c.execute("SELECT COUNT(*) n FROM suppression").fetchone()["n"]
        return {
            "total_leads": total,
            "by_type": by_type,
            "by_tier": by_tier,
            "leads_contacted": contacted,
            "suppression_entries": suppressed,
        }
