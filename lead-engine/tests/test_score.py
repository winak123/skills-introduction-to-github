from datetime import date

from leadengine.models import Lead
from leadengine.score import load_scoring_config, score_lead, tier_for

TODAY = date(2026, 8, 20)
CONFIG = load_scoring_config(None)


def make_lead(**kwargs):
    base = dict(
        lead_type="probate", source="test", county="Williamson", state="TX",
        contact_name="David Holland", contact_role="executor",
        property_address="412 Oak Ridge Dr", property_state="TX",
        mailing_state="TX", filed_date=date(2026, 4, 1),
    )
    base.update(kwargs)
    return Lead(**base)


def score(**kwargs) -> int:
    return score_lead(make_lead(**kwargs), CONFIG, today=TODAY).score


def test_absentee_executor_outscores_a_local_heir():
    absentee_executor = score(contact_role="executor", mailing_state="MA")
    local_heir = score(contact_role="heir", mailing_state="TX")
    assert absentee_executor > local_heir


def test_a_record_with_no_property_scores_near_zero():
    result = score_lead(
        make_lead(property_address="", apn=""), CONFIG, today=TODAY
    )
    assert result.score < 20
    assert any("no property" in r for r in result.reasons)


def test_filing_too_recent_loses_the_timing_points():
    too_soon = score(filed_date=date(2026, 8, 15))   # 5 days
    in_window = score(filed_date=date(2026, 4, 1))   # ~141 days
    assert in_window > too_soon


def test_stale_filing_loses_the_timing_points():
    stale = score(filed_date=date(2024, 1, 1))
    fresh = score(filed_date=date(2026, 4, 1))
    assert fresh > stale


def test_vacancy_and_equity_raise_the_score():
    plain = score()
    loaded = score(property_vacant=True, assessed_value=400000.0,
                   estimated_mortgage=40000.0)
    assert loaded > plain


def test_thin_equity_is_called_out_rather_than_rewarded():
    result = score_lead(
        make_lead(assessed_value=300000.0, estimated_mortgage=290000.0),
        CONFIG, today=TODAY,
    )
    assert any("thin equity" in r for r in result.reasons)


def test_every_lead_gets_a_reason_for_its_score():
    """Explainability is a hard requirement, not a nice-to-have here."""
    result = score_lead(make_lead(), CONFIG, today=TODAY)
    assert len(result.reasons) >= 4
    assert all(isinstance(r, str) and r for r in result.reasons)


def test_scores_stay_in_range_for_extreme_inputs():
    best = score_lead(
        make_lead(contact_role="executor", mailing_state="CA",
                  property_vacant=True, heir_count=5, phone="5125550100",
                  assessed_value=500000.0, estimated_mortgage=0.0),
        CONFIG, today=TODAY,
    )
    worst = score_lead(
        Lead(lead_type="probate", source="t", county="X", state="TX"),
        CONFIG, today=TODAY,
    )
    assert 0 <= worst.score <= best.score <= 100


def test_missing_dates_do_not_crash_the_scorer():
    result = score_lead(
        make_lead(filed_date=None, event_date=None), CONFIG, today=TODAY
    )
    assert result.score >= 0
    assert any("timing unknown" in r for r in result.reasons)


def test_tiers():
    assert tier_for(90) == "A"
    assert tier_for(60) == "B"
    assert tier_for(40) == "C"
    assert tier_for(10) == "D"
