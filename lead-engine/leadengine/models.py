"""Core data model shared by every stage of the pipeline."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Optional

# The three public-record event types this pipeline is built around.
LEAD_TYPES = ("probate", "divorce", "obituary")

# How the person we would contact relates to the underlying event.
CONTACT_ROLES = (
    "executor",       # named personal representative of an estate
    "administrator",  # court-appointed when there is no will
    "heir",           # beneficiary / next of kin
    "attorney",       # estate or family-law counsel
    "party",          # a spouse in a divorce filing
    "unknown",
)


@dataclass
class Lead:
    """One normalized lead, whatever county or format it arrived in.

    Every source adapter produces these, and every later stage (dedupe,
    scoring, compliance, outreach) reads and writes only these fields.
    """

    lead_type: str
    source: str
    county: str
    state: str

    # Who we would actually contact.
    contact_name: str = ""
    contact_role: str = "unknown"
    mailing_address: str = ""
    mailing_city: str = ""
    mailing_state: str = ""
    mailing_zip: str = ""
    phone: str = ""
    email: str = ""

    # The person or filing the record is about.
    subject_name: str = ""       # decedent, or "Smith v. Smith" for divorce
    case_number: str = ""
    filed_date: Optional[date] = None   # date the case hit the docket
    event_date: Optional[date] = None   # date of death / decree date

    # The real estate, if the record names any.
    property_address: str = ""
    property_city: str = ""
    property_state: str = ""
    property_zip: str = ""
    apn: str = ""                       # assessor's parcel number
    assessed_value: Optional[float] = None
    estimated_mortgage: Optional[float] = None
    property_vacant: Optional[bool] = None
    heir_count: Optional[int] = None

    # Filled in by later stages.
    score: Optional[int] = None
    score_reasons: list[str] = field(default_factory=list)
    compliance_flags: list[str] = field(default_factory=list)
    contactable_channels: list[str] = field(default_factory=list)

    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def lead_id(self) -> str:
        """Stable id derived from the record's identifying fields.

        Re-ingesting the same county export produces the same ids, which is
        what lets `ingest` be safely re-run without duplicating rows.
        """
        basis = "|".join(
            [
                self.state.upper(),
                self.county.lower(),
                self.lead_type,
                self.case_number.lower(),
                self.subject_name.lower(),
                self.property_address.lower(),
            ]
        )
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]

    @property
    def estimated_equity(self) -> Optional[float]:
        if self.assessed_value is None:
            return None
        return self.assessed_value - (self.estimated_mortgage or 0.0)

    @property
    def is_absentee(self) -> bool:
        """True when the contact lives in a different state than the property.

        Out-of-state heirs are the single strongest motivation signal in
        probate work: they rarely want to manage a property remotely.
        """
        if not (self.mailing_state and self.property_state):
            return False
        return self.mailing_state.upper() != self.property_state.upper()

    def days_since_filing(self, today: Optional[date] = None) -> Optional[int]:
        if self.filed_date is None:
            return None
        return ((today or date.today()) - self.filed_date).days

    def days_since_event(self, today: Optional[date] = None) -> Optional[int]:
        if self.event_date is None:
            return None
        return ((today or date.today()) - self.event_date).days

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["lead_id"] = self.lead_id
        d["estimated_equity"] = self.estimated_equity
        d["is_absentee"] = self.is_absentee
        for key in ("filed_date", "event_date"):
            if d[key] is not None:
                d[key] = d[key].isoformat()
        return d
