"""Config-driven CSV importer.

One class handles every county because the column mapping lives in YAML
rather than in code. Point it at whatever the clerk exported, describe
which of their columns means what, and it produces normalized leads.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterator

from .. import normalize as nz
from ..models import Lead
from .base import Source, register_source

# Field name -> the parser applied to the mapped raw value.
_PARSERS = {
    "contact_name": nz.normalize_name,
    "subject_name": nz.normalize_name,
    "mailing_address": lambda v: nz.normalize_address(v).title(),
    "property_address": lambda v: nz.normalize_address(v).title(),
    "mailing_city": lambda v: v.strip().title(),
    "property_city": lambda v: v.strip().title(),
    "mailing_state": nz.normalize_state,
    "property_state": nz.normalize_state,
    "mailing_zip": nz.normalize_zip,
    "property_zip": nz.normalize_zip,
    "phone": nz.normalize_phone,
    "email": nz.normalize_email,
    "filed_date": nz.parse_date,
    "event_date": nz.parse_date,
    "assessed_value": nz.parse_money,
    "estimated_mortgage": nz.parse_money,
    "property_vacant": nz.parse_bool,
    "heir_count": nz.parse_int,
    "case_number": lambda v: v.strip(),
    "apn": lambda v: v.strip(),
    "contact_role": lambda v: v.strip().lower() or "unknown",
}


@register_source
class CsvSource(Source):
    """Read a county export, mapping their column names onto `Lead` fields.

    Expected config keys:
        path         - CSV file to read
        lead_type    - one of probate / divorce / obituary
        county, state
        mapping      - {lead_field: csv_column_name}
        defaults     - {lead_field: literal value} applied when unmapped
        encoding     - optional, defaults to utf-8-sig (strips Excel BOMs)
    """

    name = "csv"

    def fetch(self) -> Iterator[Lead]:
        path = Path(self.config["path"]).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"source file not found: {path}")

        lead_type = self.config["lead_type"]
        mapping: dict[str, str] = self.config.get("mapping", {})
        defaults: dict[str, Any] = self.config.get("defaults", {})
        encoding = self.config.get("encoding", "utf-8-sig")

        with path.open(newline="", encoding=encoding) as fh:
            reader = csv.DictReader(fh)
            # Match columns case- and whitespace-insensitively; clerks are
            # inconsistent about header capitalization between exports.
            headers = {(h or "").strip().lower(): h for h in (reader.fieldnames or [])}

            for row in reader:
                lead = self._build(row, headers, lead_type, mapping, defaults)
                if lead is not None:
                    yield lead

    def _build(self, row, headers, lead_type, mapping, defaults) -> Lead | None:
        values: dict[str, Any] = dict(defaults)

        for field_name, column in mapping.items():
            actual = headers.get(str(column).strip().lower())
            if actual is None:
                continue
            raw = row.get(actual)
            if raw is None or str(raw).strip() == "":
                continue
            parser = _PARSERS.get(field_name)
            parsed = parser(str(raw)) if parser else str(raw).strip()
            if parsed not in (None, ""):
                values[field_name] = parsed

        lead = Lead(
            lead_type=lead_type,
            source=self.config.get("source_name", f"csv:{lead_type}"),
            county=self.config["county"],
            state=nz.normalize_state(self.config["state"]),
            raw={k: v for k, v in row.items() if v not in (None, "")},
            **values,
        )

        # A record with nobody to contact and no property is not a lead.
        if not lead.contact_name and not lead.subject_name:
            return None
        return lead
