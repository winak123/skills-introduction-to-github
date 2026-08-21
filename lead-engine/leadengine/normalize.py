"""Field cleanup so records from different counties compare as equals.

County clerks export wildly inconsistent data. Names arrive as "SMITH,
JOHN A JR", addresses as "123 N. Main Street Apt 4B", dates in any of a
half-dozen formats. Everything downstream assumes normalized input.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

# Suffixes and courtesy titles that carry no identifying information.
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq", "dds"}
_TITLES = {"mr", "mrs", "ms", "miss", "dr", "rev", "hon"}

# Probate exports routinely tack an estate marker onto the decedent's name.
_ESTATE_MARKERS = re.compile(
    r"\b(estate of|in re:?|deceased|dec'?d|the estate)\b", re.IGNORECASE
)

_STREET_ABBREV = {
    "street": "st", "avenue": "ave", "boulevard": "blvd", "drive": "dr",
    "road": "rd", "lane": "ln", "court": "ct", "circle": "cir",
    "place": "pl", "parkway": "pkwy", "highway": "hwy", "terrace": "ter",
    "trail": "trl", "square": "sq", "north": "n", "south": "s",
    "east": "e", "west": "w", "northeast": "ne", "northwest": "nw",
    "southeast": "se", "southwest": "sw",
}

# Secondary unit designators - dropped when building a dedupe key, since
# one county writes "Apt 4B" and the next writes "#4B" for the same door.
_UNIT_RE = re.compile(
    r"\s+(?:apt|apartment|unit|ste|suite|#|bldg|building|fl|floor|rm|room)\.?"
    r"\s*[\w-]+\s*$",
    re.IGNORECASE,
)

_DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%b %d, %Y",
    "%B %d, %Y", "%Y/%m/%d", "%m-%d-%Y", "%Y%m%d",
)


def normalize_name(raw: str) -> str:
    """Return a person's name as "First Middle Last", title-cased.

    Handles the "LAST, FIRST MIDDLE" convention that most court systems
    use, and strips estate markers, titles, and generational suffixes.
    """
    if not raw:
        return ""

    name = _ESTATE_MARKERS.sub(" ", raw)
    name = re.sub(r"[^\w\s,'-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        return ""

    # "SMITH, JOHN A" -> "JOHN A SMITH"
    if "," in name:
        last, _, rest = name.partition(",")
        if rest.strip():
            name = f"{rest.strip()} {last.strip()}"
        else:
            name = last.strip()

    parts = []
    for token in name.split():
        bare = token.strip(".'-").lower()
        if bare in _SUFFIXES or bare in _TITLES:
            continue
        parts.append(token)

    return " ".join(_titlecase(p) for p in parts)


def _titlecase(token: str) -> str:
    """Capitalize a name token, respecting O'Brien and Smith-Jones."""
    if not (token.islower() or token.isupper()):
        return token  # already mixed case - the source knew what it meant
    return re.sub(r"[A-Za-z]+", lambda m: m.group(0).capitalize(), token.lower())


def normalize_address(raw: str, *, drop_unit: bool = False) -> str:
    """Lowercase, de-punctuate, and abbreviate an address consistently.

    Set `drop_unit` when building a comparison key: two records for the
    same building should collide even if only one names the unit.
    """
    if not raw:
        return ""

    addr = raw.lower()
    addr = re.sub(r"[.,]", " ", addr)
    addr = re.sub(r"\s+", " ", addr).strip()

    if drop_unit:
        addr = _UNIT_RE.sub("", addr).strip()

    tokens = [_STREET_ABBREV.get(t, t) for t in addr.split()]
    return " ".join(tokens)


def normalize_phone(raw: str) -> str:
    """Return 10 digits of a US phone number, or "" if it isn't one.

    Anything that fails to normalize is deliberately dropped rather than
    guessed at - a wrong number is a compliance problem, not a typo.
    """
    if not raw:
        return ""

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    # Area codes and exchanges never start with 0 or 1.
    if digits[0] in "01" or digits[3] in "01":
        return ""
    return digits


def format_phone(digits: str) -> str:
    if len(digits) != 10:
        return digits
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def normalize_email(raw: str) -> str:
    if not raw:
        return ""
    email = raw.strip().lower()
    return email if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email) else ""


def normalize_state(raw: str) -> str:
    if not raw:
        return ""
    state = re.sub(r"[^A-Za-z]", "", raw).upper()
    return state if len(state) == 2 else state[:2]


def normalize_zip(raw: str) -> str:
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw))
    return digits[:5].zfill(5) if digits else ""


def parse_date(raw) -> Optional[date]:
    """Parse the date formats county exports actually use, else None."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, date):
        return raw
    if isinstance(raw, datetime):
        return raw.date()

    text = str(raw).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_money(raw) -> Optional[float]:
    """Parse "$412,000.00" and friends into a float."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    cleaned = re.sub(r"[^\d.\-]", "", str(raw))
    if not cleaned or cleaned in {"-", ".", "-."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_bool(raw) -> Optional[bool]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"y", "yes", "true", "t", "1"}:
        return True
    if text in {"n", "no", "false", "f", "0"}:
        return False
    return None


def parse_int(raw) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw).strip()))
    except ValueError:
        return None
