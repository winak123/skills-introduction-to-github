"""Collapse the same lead arriving from several sources.

An obituary feed, a probate docket, and a purchased list will all surface
the same house under slightly different spellings. Mailing the same
grieving family three times is the fastest way to earn a complaint, so
this runs before anything leaves the building.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from . import normalize as nz
from .models import Lead

# Above this similarity on the comparison key, two records are one lead.
DEFAULT_THRESHOLD = 0.88


def blocking_key(lead: Lead) -> str:
    """Cheap key that partitions leads into candidate groups.

    Fuzzy comparison is quadratic, so only records sharing this key get
    compared. State plus the house number keeps groups tiny while almost
    never splitting a true pair.
    """
    addr = nz.normalize_address(lead.property_address or lead.mailing_address,
                               drop_unit=True)
    house_number = addr.split()[0] if addr else ""
    return f"{lead.state.upper()}|{house_number}"


def comparison_key(lead: Lead) -> str:
    """The string actually fuzzy-matched within a block."""
    addr = nz.normalize_address(lead.property_address or lead.mailing_address,
                                drop_unit=True)
    name = nz.normalize_name(lead.subject_name or lead.contact_name).lower()
    return f"{name}|{addr}"


def similarity(a: Lead, b: Lead) -> float:
    return SequenceMatcher(None, comparison_key(a), comparison_key(b)).ratio()


def merge(primary: Lead, other: Lead) -> Lead:
    """Fold `other` into `primary`, keeping whichever value is richer.

    Empty fields lose to populated ones; for dates the earlier filing wins,
    since that is the one the courthouse actually recorded.
    """
    for field_name, value in vars(other).items():
        if field_name in ("raw", "score", "score_reasons", "compliance_flags",
                          "contactable_channels"):
            continue
        current = getattr(primary, field_name)
        if current in (None, "", []) and value not in (None, "", []):
            setattr(primary, field_name, value)

    for field_name in ("filed_date", "event_date"):
        mine, theirs = getattr(primary, field_name), getattr(other, field_name)
        if mine and theirs and theirs < mine:
            setattr(primary, field_name, theirs)

    if (other.heir_count or 0) > (primary.heir_count or 0):
        primary.heir_count = other.heir_count

    # Keep provenance visible - you will want it when a lead looks wrong.
    sources = set(str(primary.source).split("+")) | set(str(other.source).split("+"))
    primary.source = "+".join(sorted(s for s in sources if s))
    primary.raw.setdefault("merged_from", []).append(other.lead_id)
    for key, value in other.raw.items():
        primary.raw.setdefault(key, value)

    return primary


def deduplicate(leads: Iterable[Lead],
                threshold: float = DEFAULT_THRESHOLD) -> tuple[list[Lead], int]:
    """Return (unique leads, number of records merged away)."""
    blocks: dict[str, list[Lead]] = {}
    for lead in leads:
        blocks.setdefault(blocking_key(lead), []).append(lead)

    unique: list[Lead] = []
    merged_count = 0

    for group in blocks.values():
        kept: list[Lead] = []
        for lead in group:
            match = next(
                (k for k in kept if similarity(k, lead) >= threshold), None
            )
            if match is not None:
                merge(match, lead)
                merged_count += 1
            else:
                kept.append(lead)
        unique.extend(kept)

    return unique, merged_count
