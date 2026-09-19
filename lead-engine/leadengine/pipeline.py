"""Wires the stages together: ingest -> dedupe -> score -> compliance."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

from .compliance import SuppressionList, evaluate, load_rules
from .dedupe import deduplicate
from .models import Lead
from .score import load_scoring_config, score_lead
from .sources import get_source


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).expanduser().open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def ingest(config: dict[str, Any]) -> list[Lead]:
    """Run every enabled source in the config and collect its leads."""
    leads: list[Lead] = []
    for entry in config.get("sources", []):
        if entry.get("enabled") is False:
            continue
        source_cls = get_source(entry.get("type", "csv"))
        leads.extend(source_cls(entry).fetch())
    return leads


def process(
    leads: list[Lead],
    *,
    rules: Optional[dict[str, Any]] = None,
    scoring: Optional[dict[str, Any]] = None,
    suppression: Optional[SuppressionList] = None,
    today: Optional[date] = None,
    dedupe: bool = True,
) -> tuple[list[Lead], int]:
    """Dedupe, score, and compliance-gate a batch of leads in place."""
    merged = 0
    if dedupe:
        leads, merged = deduplicate(leads)

    rules = rules if rules is not None else {}
    scoring = scoring or load_scoring_config(None)

    for lead in leads:
        result = score_lead(lead, scoring, today=today)
        lead.score = result.score
        lead.score_reasons = result.reasons

        compliance = evaluate(lead, rules, suppression, today=today)
        lead.compliance_flags = compliance.flag_strings()
        lead.contactable_channels = compliance.allowed_channels

    return leads, merged


def load_all(config: dict[str, Any], base: Path) -> tuple[dict, dict]:
    """Resolve the rules and scoring files a config points at."""
    rules_path = config.get("state_rules", base / "config" / "state_rules.yml")
    scoring_path = config.get("scoring", base / "config" / "scoring.yml")

    rules = load_rules(rules_path) if Path(rules_path).expanduser().exists() else {}
    scoring = load_scoring_config(scoring_path)
    return rules, scoring
