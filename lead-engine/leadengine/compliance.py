"""Channel gating - decides how, or whether, a lead may be contacted.

This runs before outreach, not after. Probate and divorce prospecting is
lawful, but it is the most heavily regulated corner of lead generation:
the TCPA carries $500-$1,500 per violation, several states impose a
statutory waiting period after a death before heirs may be solicited, and
some bar-adjacent solicitation rules reach real estate licensees too.

The default posture here is conservative: a channel is closed unless a
rule opens it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Optional

import yaml

CHANNELS = ("mail", "phone", "sms", "email")

# TCPA restricts telephone solicitation to 8am-9pm in the CALLED party's
# local time. Some states narrow it further; state_rules.yml can override.
DEFAULT_CALL_WINDOW = (time(8, 0), time(21, 0))


@dataclass
class Flag:
    """One compliance finding attached to a lead."""

    code: str
    severity: str  # "block" or "warn"
    channel: str   # affected channel, or "all"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}:{self.channel}] {self.code}: {self.message}"


@dataclass
class ComplianceResult:
    allowed_channels: list[str] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return not self.allowed_channels

    def flag_strings(self) -> list[str]:
        return [str(f) for f in self.flags]


class SuppressionList:
    """Phone numbers and addresses that must never be contacted.

    Holds three things: your internal do-not-call list (required by the
    TCPA, and you must retain entries for five years), the output of a
    national/state DNC scrub, and anyone who has asked you to stop.
    """

    def __init__(self, phones=None, emails=None, addresses=None):
        self.phones = set(phones or ())
        self.emails = set(emails or ())
        self.addresses = set(addresses or ())

    @classmethod
    def from_csv(cls, path: str | Path) -> "SuppressionList":
        """Load from a CSV with any of: phone, email, address columns."""
        import csv

        from . import normalize as nz

        phones, emails, addresses = set(), set(), set()
        p = Path(path).expanduser()
        if not p.exists():
            return cls()

        with p.open(newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                lower = {(k or "").strip().lower(): v for k, v in row.items()}
                if phone := nz.normalize_phone(lower.get("phone", "") or ""):
                    phones.add(phone)
                if email := nz.normalize_email(lower.get("email", "") or ""):
                    emails.add(email)
                if addr := lower.get("address", ""):
                    addresses.add(nz.normalize_address(addr, drop_unit=True))
        return cls(phones, emails, addresses)

    def __len__(self) -> int:
        return len(self.phones) + len(self.emails) + len(self.addresses)


def load_rules(path: str | Path) -> dict[str, Any]:
    with Path(path).expanduser().open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def rules_for_state(rules: dict[str, Any], state: str) -> dict[str, Any]:
    """Merge the default rule block with any state-specific overrides."""
    merged = dict(rules.get("defaults", {}))
    merged.update((rules.get("states", {}) or {}).get(state.upper(), {}) or {})
    return merged


def evaluate(
    lead,
    rules: dict[str, Any],
    suppression: Optional[SuppressionList] = None,
    today: Optional[date] = None,
) -> ComplianceResult:
    """Return the channels this lead may be contacted on, and why not others."""
    today = today or date.today()
    suppression = suppression or SuppressionList()
    state_rules = rules_for_state(rules, lead.property_state or lead.state)

    flags: list[Flag] = []
    allowed = set(CHANNELS)

    # --- Statutory waiting period after a death -------------------------
    wait_days = int(state_rules.get("mourning_period_days", 0) or 0)
    if lead.lead_type in ("probate", "obituary") and wait_days:
        elapsed = lead.days_since_event(today)
        if elapsed is None:
            elapsed = lead.days_since_filing(today)
        if elapsed is None:
            flags.append(Flag(
                "unknown_event_date", "block", "all",
                f"{lead.state} imposes a {wait_days}-day waiting period after "
                "death and this record has no date to measure from",
            ))
            allowed.clear()
        elif elapsed < wait_days:
            remaining = wait_days - elapsed
            mail_ok = bool(state_rules.get("mail_allowed_during_wait", False))
            blocked = {"phone", "sms", "email"} if mail_ok else set(CHANNELS)
            allowed -= blocked
            flags.append(Flag(
                "mourning_period", "block", "all" if not mail_ok else "phone/sms/email",
                f"{remaining} day(s) left in {lead.state}'s {wait_days}-day "
                f"post-death waiting period"
                + (" (mail permitted)" if mail_ok else ""),
            ))

    # --- Divorce filings: contact the wrong side of a pending case and you
    # --- are interfering with litigation. Wait for the decree.
    if lead.lead_type == "divorce":
        decree_wait = int(state_rules.get("divorce_wait_days", 0) or 0)
        elapsed = lead.days_since_event(today)
        if elapsed is None:
            flags.append(Flag(
                "divorce_not_final", "warn", "all",
                "no decree date on record - confirm the case is final before "
                "discussing a sale; both parties usually must consent",
            ))
        elif elapsed < decree_wait:
            allowed -= {"phone", "sms"}
            flags.append(Flag(
                "divorce_pending", "block", "phone/sms",
                f"only {elapsed} day(s) since decree; {decree_wait} required "
                "by local policy before calling",
            ))

    # --- Channel availability -------------------------------------------
    if not lead.phone:
        allowed -= {"phone", "sms"}
        flags.append(Flag("no_phone", "warn", "phone/sms", "no phone number on record"))
    elif lead.phone in suppression.phones:
        allowed -= {"phone", "sms"}
        flags.append(Flag(
            "suppressed_phone", "block", "phone/sms",
            "number is on a do-not-call or suppression list",
        ))

    if not lead.email:
        allowed -= {"email"}
    elif lead.email in suppression.emails:
        allowed -= {"email"}
        flags.append(Flag("suppressed_email", "block", "email", "email is suppressed"))

    mail_key = ""
    if lead.mailing_address:
        from . import normalize as nz

        mail_key = nz.normalize_address(lead.mailing_address, drop_unit=True)
    if not mail_key:
        allowed -= {"mail"}
        flags.append(Flag("no_mailing_address", "warn", "mail", "no mailing address"))
    elif mail_key in suppression.addresses:
        allowed -= {"mail"}
        flags.append(Flag("suppressed_address", "block", "mail", "address is suppressed"))

    # --- Cold SMS ---------------------------------------------------------
    # The TCPA requires prior express written consent for marketing texts to
    # a mobile number. A court record is not consent. This stays closed
    # unless the lead opted in through your own form.
    if "sms" in allowed and not lead.raw.get("sms_consent"):
        allowed -= {"sms"}
        flags.append(Flag(
            "no_sms_consent", "block", "sms",
            "cold texting requires prior express written consent (TCPA)",
        ))

    # --- Standing warnings on the channels that survive -------------------
    if "phone" in allowed and not state_rules.get("dnc_scrubbed", False):
        flags.append(Flag(
            "dnc_scrub_required", "warn", "phone",
            "scrub against the national and state DNC registries before dialing",
        ))
    if "email" in allowed:
        flags.append(Flag(
            "can_spam", "warn", "email",
            "CAN-SPAM requires a working opt-out and your physical address",
        ))

    ordered = [c for c in CHANNELS if c in allowed]
    return ComplianceResult(allowed_channels=ordered, flags=flags)


def within_call_window(
    rules: dict[str, Any], state: str, now: Optional[datetime] = None
) -> bool:
    """True if `now` falls inside the permitted calling hours for a state.

    `now` must already be in the called party's local time - this function
    does not do timezone conversion for you.
    """
    now = now or datetime.now()
    state_rules = rules_for_state(rules, state)
    start, end = DEFAULT_CALL_WINDOW

    from . import normalize as nz  # noqa: F401  (kept for symmetry)

    if raw_start := state_rules.get("call_window_start"):
        start = _parse_time(raw_start, start)
    if raw_end := state_rules.get("call_window_end"):
        end = _parse_time(raw_end, end)

    return start <= now.time() <= end


def _parse_time(raw: Any, fallback: time) -> time:
    try:
        hh, _, mm = str(raw).partition(":")
        return time(int(hh), int(mm or 0))
    except (ValueError, TypeError):
        return fallback
