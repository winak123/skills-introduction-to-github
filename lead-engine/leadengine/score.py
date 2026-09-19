"""Explainable lead scoring.

Every point a lead earns comes with a sentence saying why. That matters
more than raw accuracy here: you are deciding who to approach after a
death or a divorce, and "the model said 87" is not a reason you would
want to defend. Weights live in config/scoring.yml so you can tune them
against your own closed deals rather than trusting these defaults.

The signals are the ones that actually separate a listing from a dead
end - authority to sell, timing, absentee ownership, and equity - not
demographic guesswork.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

DEFAULT_WEIGHTS: dict[str, Any] = {
    "authority": 25,       # contact can actually sign a listing agreement
    "timing": 20,          # inside the useful window after filing
    "has_property": 15,    # record names real property at all
    "absentee": 15,        # contact lives out of state
    "equity": 15,          # enough equity for a sale to make sense
    "vacant": 10,          # carrying an empty house is expensive
    "multiple_heirs": 5,   # co-owners usually liquidate rather than split
    "reachable": 5,        # we have a way to make contact
    "no_property_penalty": -30,
}

DEFAULT_TIMING = {
    # Before this, the estate usually has no authority to sell and the
    # approach reads as predatory. After it, the property is typically
    # already listed or transferred.
    "probate": {"open_days": 30, "peak_start": 45, "peak_end": 180, "close_days": 365},
    "divorce": {"open_days": 0, "peak_start": 0, "peak_end": 120, "close_days": 270},
    "obituary": {"open_days": 45, "peak_start": 60, "peak_end": 210, "close_days": 365},
}

# Roles that can sign, versus roles that can only introduce you.
_AUTHORITY = {
    "executor": 1.0,
    "administrator": 1.0,
    "party": 0.9,      # a divorcing spouse on title
    "heir": 0.5,
    "attorney": 0.4,   # a gatekeeper, but a durable referral source
    "unknown": 0.2,
}


@dataclass
class ScoreResult:
    score: int
    reasons: list[str]
    tier: str

    def __str__(self) -> str:
        return f"{self.score} ({self.tier})"


def load_scoring_config(path: Optional[str | Path]) -> dict[str, Any]:
    """Load weights from YAML, falling back to the built-in defaults."""
    weights = dict(DEFAULT_WEIGHTS)
    timing = {k: dict(v) for k, v in DEFAULT_TIMING.items()}

    if path and Path(path).expanduser().exists():
        with Path(path).expanduser().open(encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        weights.update(cfg.get("weights", {}) or {})
        for lead_type, window in (cfg.get("timing", {}) or {}).items():
            timing.setdefault(lead_type, {}).update(window or {})

    return {"weights": weights, "timing": timing}


def score_lead(lead, config: Optional[dict[str, Any]] = None,
               today: Optional[date] = None) -> ScoreResult:
    """Score one lead 0-100 and explain every contribution."""
    config = config or load_scoring_config(None)
    weights = config["weights"]
    timing = config["timing"]
    today = today or date.today()

    points = 0.0
    possible = 0.0
    reasons: list[str] = []

    # --- Authority to sell ------------------------------------------------
    w = weights["authority"]
    possible += w
    factor = _AUTHORITY.get(lead.contact_role, _AUTHORITY["unknown"])
    points += w * factor
    if factor >= 0.9:
        reasons.append(f"{lead.contact_role} can sign a listing agreement")
    elif factor >= 0.5:
        reasons.append(f"{lead.contact_role} - influences the sale but may not control it")
    else:
        reasons.append(f"contact role '{lead.contact_role}' has unclear authority")

    # --- Timing -----------------------------------------------------------
    w = weights["timing"]
    possible += w
    window = timing.get(lead.lead_type, timing["probate"])
    elapsed = lead.days_since_filing(today)
    if elapsed is None:
        elapsed = lead.days_since_event(today)

    if elapsed is None:
        reasons.append("no filing or event date - timing unknown")
    elif elapsed < window["open_days"]:
        reasons.append(
            f"only {elapsed} days since filing - too early to approach "
            f"(window opens at {window['open_days']})"
        )
    elif window["peak_start"] <= elapsed <= window["peak_end"]:
        points += w
        reasons.append(f"{elapsed} days since filing - inside the prime window")
    elif elapsed <= window["close_days"]:
        points += w * 0.5
        reasons.append(f"{elapsed} days since filing - workable but off-peak")
    else:
        reasons.append(f"{elapsed} days since filing - likely already resolved")

    # --- Is there a house at all? -----------------------------------------
    w = weights["has_property"]
    possible += w
    if lead.property_address or lead.apn:
        points += w
        reasons.append("record names real property")
    else:
        points += weights["no_property_penalty"]
        reasons.append("no property identified - needs assessor lookup before working")

    # --- Absentee ownership -----------------------------------------------
    w = weights["absentee"]
    possible += w
    if lead.is_absentee:
        points += w
        reasons.append(
            f"contact is in {lead.mailing_state}, property is in {lead.property_state}"
            " - remote owners sell"
        )
    elif lead.mailing_state and lead.property_state:
        reasons.append("contact is local to the property")

    # --- Equity -----------------------------------------------------------
    w = weights["equity"]
    possible += w
    equity = lead.estimated_equity
    if equity is None:
        reasons.append("no valuation on record - equity unknown")
    elif lead.assessed_value:
        ratio = equity / lead.assessed_value
        if ratio >= 0.5:
            points += w
            reasons.append(f"strong equity position (~{ratio:.0%})")
        elif ratio >= 0.2:
            points += w * 0.5
            reasons.append(f"moderate equity (~{ratio:.0%})")
        else:
            reasons.append(f"thin equity (~{ratio:.0%}) - a sale may not clear costs")

    # --- Vacancy ----------------------------------------------------------
    w = weights["vacant"]
    possible += w
    if lead.property_vacant:
        points += w
        reasons.append("property reported vacant - carrying cost pressure")

    # --- Co-owners --------------------------------------------------------
    w = weights["multiple_heirs"]
    possible += w
    if (lead.heir_count or 0) > 1:
        points += w
        reasons.append(f"{lead.heir_count} heirs - co-owned property usually gets sold")

    # --- Reachability -----------------------------------------------------
    w = weights["reachable"]
    possible += w
    if lead.phone or lead.email or lead.mailing_address:
        points += w
    else:
        reasons.append("no contact information - needs skip tracing")

    score = int(round(max(0.0, min(100.0, (points / possible) * 100)))) if possible else 0
    return ScoreResult(score=score, reasons=reasons, tier=tier_for(score))


def tier_for(score: int) -> str:
    if score >= 75:
        return "A"
    if score >= 55:
        return "B"
    if score >= 35:
        return "C"
    return "D"
