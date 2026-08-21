from datetime import date

import pytest

from leadengine import normalize as nz


@pytest.mark.parametrize("raw,expected", [
    ("SMITH, JOHN A JR", "John A Smith"),
    ("Estate of MARY O'BRIEN, Deceased", "Mary O'Brien"),
    ("garcia-lopez, ana", "Ana Garcia-Lopez"),
    ("IN RE: WALSH, EILEEN", "Eileen Walsh"),
    ("Dr. Susan Reyes", "Susan Reyes"),
    ("", ""),
])
def test_normalize_name(raw, expected):
    assert nz.normalize_name(raw) == expected


def test_normalize_name_preserves_intentional_mixed_case():
    assert nz.normalize_name("McDonald, Ian") == "Ian McDonald"


def test_normalize_address_abbreviates_and_lowercases():
    assert nz.normalize_address("123 North Main Street") == "123 n main st"


def test_normalize_address_drops_unit_only_when_asked():
    full = "412 Oak Ridge Drive Apt 12"
    assert nz.normalize_address(full) == "412 oak ridge dr apt 12"
    assert nz.normalize_address(full, drop_unit=True) == "412 oak ridge dr"


@pytest.mark.parametrize("raw,expected", [
    ("+1 (512) 555-0134", "5125550134"),
    ("512.555.0134", "5125550134"),
    ("15125550134", "5125550134"),
    ("011-555", ""),        # too short
    ("0125550134", ""),     # area code cannot start with 0
    ("5121550134", ""),     # exchange cannot start with 1
    ("", ""),
])
def test_normalize_phone(raw, expected):
    """A number that fails to normalize is dropped, never guessed at."""
    assert nz.normalize_phone(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("2026-03-14", date(2026, 3, 14)),
    ("3/14/2026", date(2026, 3, 14)),
    ("March 14, 2026", date(2026, 3, 14)),
    ("14-Mar-2026", date(2026, 3, 14)),
    ("not a date", None),
    ("", None),
])
def test_parse_date(raw, expected):
    assert nz.parse_date(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("$412,000.00", 412000.0),
    ("412000", 412000.0),
    ("", None),
    ("n/a", None),
])
def test_parse_money(raw, expected):
    assert nz.parse_money(raw) == expected


def test_normalize_email_rejects_malformed():
    assert nz.normalize_email("  Jane@Example.COM ") == "jane@example.com"
    assert nz.normalize_email("not-an-email") == ""
