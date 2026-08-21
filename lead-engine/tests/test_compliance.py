from datetime import date, datetime

from leadengine.compliance import SuppressionList, evaluate, within_call_window
from leadengine.models import Lead

TODAY = date(2026, 8, 20)

RULES = {
    "defaults": {
        "mourning_period_days": 30,
        "mail_allowed_during_wait": True,
        "divorce_wait_days": 30,
        "call_window_start": "08:00",
        "call_window_end": "21:00",
        "dnc_scrubbed": False,
    },
    "states": {
        "NY": {"mourning_period_days": 90, "mail_allowed_during_wait": False},
    },
}


def make_lead(**kwargs):
    base = dict(
        lead_type="probate", source="test", county="Williamson", state="TX",
        contact_name="Thomas Walsh", contact_role="executor",
        mailing_address="770 Meadowlark Ln", property_state="TX",
        phone="5125550121",
    )
    base.update(kwargs)
    return Lead(**base)


def test_recent_death_blocks_calls_but_allows_mail():
    lead = make_lead(event_date=date(2026, 8, 5))  # 15 days ago

    result = evaluate(lead, RULES, today=TODAY)

    assert result.allowed_channels == ["mail"]
    assert any(f.code == "mourning_period" for f in result.flags)


def test_state_override_blocks_every_channel_during_the_wait():
    """NY's longer window here also disallows mail, so nothing is open."""
    lead = make_lead(state="NY", property_state="NY", event_date=date(2026, 8, 5))

    result = evaluate(lead, RULES, today=TODAY)

    assert result.blocked
    assert result.allowed_channels == []


def test_after_the_waiting_period_phone_opens():
    lead = make_lead(event_date=date(2026, 1, 10))

    result = evaluate(lead, RULES, today=TODAY)

    assert "phone" in result.allowed_channels
    assert "mail" in result.allowed_channels


def test_cold_sms_is_always_blocked_without_consent():
    """A court record is not prior express written consent under the TCPA."""
    lead = make_lead(event_date=date(2026, 1, 10))

    result = evaluate(lead, RULES, today=TODAY)

    assert "sms" not in result.allowed_channels
    assert any(f.code == "no_sms_consent" for f in result.flags)


def test_sms_opens_only_with_recorded_consent():
    lead = make_lead(event_date=date(2026, 1, 10), raw={"sms_consent": True})

    result = evaluate(lead, RULES, today=TODAY)

    assert "sms" in result.allowed_channels


def test_suppressed_phone_closes_phone_and_sms():
    lead = make_lead(event_date=date(2026, 1, 10))
    suppression = SuppressionList(phones={"5125550121"})

    result = evaluate(lead, RULES, suppression, today=TODAY)

    assert "phone" not in result.allowed_channels
    assert "sms" not in result.allowed_channels
    assert "mail" in result.allowed_channels
    assert any(f.code == "suppressed_phone" and f.severity == "block"
               for f in result.flags)


def test_suppressed_address_closes_mail():
    lead = make_lead(event_date=date(2026, 1, 10))
    suppression = SuppressionList(addresses={"770 meadowlark ln"})

    result = evaluate(lead, RULES, suppression, today=TODAY)

    assert "mail" not in result.allowed_channels


def test_missing_death_date_blocks_everything():
    """Without a date we cannot prove the waiting period has passed."""
    lead = make_lead(event_date=None, filed_date=None)

    result = evaluate(lead, RULES, today=TODAY)

    assert result.blocked
    assert any(f.code == "unknown_event_date" for f in result.flags)


def test_pending_divorce_blocks_calls():
    lead = make_lead(lead_type="divorce", contact_role="party",
                     event_date=date(2026, 8, 10))  # decree 10 days ago

    result = evaluate(lead, RULES, today=TODAY)

    assert "phone" not in result.allowed_channels
    assert any(f.code == "divorce_pending" for f in result.flags)


def test_divorce_without_a_decree_date_warns():
    lead = make_lead(lead_type="divorce", contact_role="party", event_date=None)

    result = evaluate(lead, RULES, today=TODAY)

    assert any(f.code == "divorce_not_final" and f.severity == "warn"
               for f in result.flags)


def test_dnc_warning_rides_along_on_every_open_phone_channel():
    lead = make_lead(event_date=date(2026, 1, 10))

    result = evaluate(lead, RULES, today=TODAY)

    assert any(f.code == "dnc_scrub_required" for f in result.flags)


def test_call_window_respects_tcpa_hours():
    assert within_call_window(RULES, "TX", datetime(2026, 8, 20, 10, 0))
    assert not within_call_window(RULES, "TX", datetime(2026, 8, 20, 7, 59))
    assert not within_call_window(RULES, "TX", datetime(2026, 8, 20, 21, 30))
