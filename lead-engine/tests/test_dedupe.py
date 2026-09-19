from datetime import date

from leadengine.dedupe import deduplicate, similarity
from leadengine.models import Lead


def make_lead(**kwargs):
    base = dict(lead_type="probate", source="test", county="Williamson", state="TX")
    base.update(kwargs)
    return Lead(**base)


def test_same_lead_from_two_sources_collapses():
    """An obituary feed and a probate docket describing one house are one lead."""
    a = make_lead(
        source="obituary", subject_name="Margaret E Holland",
        property_address="412 Oak Ridge Drive", property_state="TX",
        filed_date=date(2026, 2, 20),
    )
    b = make_lead(
        source="probate", subject_name="HOLLAND, MARGARET E",
        property_address="412 Oak Ridge Dr", property_state="TX",
        filed_date=date(2026, 2, 10), phone="5125550100",
    )

    unique, merged = deduplicate([a, b])

    assert merged == 1
    assert len(unique) == 1
    # The merge keeps the richer field and the earlier courthouse date.
    assert unique[0].phone == "5125550100"
    assert unique[0].filed_date == date(2026, 2, 10)
    assert "obituary" in unique[0].source and "probate" in unique[0].source


def test_different_properties_stay_separate():
    a = make_lead(subject_name="Ana Ruiz", property_address="1907 Pecan Ln")
    b = make_lead(subject_name="Ana Ruiz", property_address="4400 Ridgepoint Dr")

    unique, merged = deduplicate([a, b])

    assert merged == 0
    assert len(unique) == 2


def test_unit_differences_do_not_split_a_lead():
    a = make_lead(subject_name="Wei Chen", property_address="88 Beacon St Apt 12")
    b = make_lead(subject_name="Wei Chen", property_address="88 Beacon Street #12")

    assert similarity(a, b) >= 0.88
    unique, merged = deduplicate([a, b])
    assert merged == 1 and len(unique) == 1


def test_merge_prefers_the_larger_heir_count():
    a = make_lead(subject_name="Pat Walsh", property_address="770 Meadowlark Ln",
                  heir_count=1)
    b = make_lead(subject_name="Pat Walsh", property_address="770 Meadowlark Ln",
                  heir_count=4)

    unique, _ = deduplicate([a, b])
    assert unique[0].heir_count == 4
