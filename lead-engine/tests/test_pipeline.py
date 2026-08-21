"""End-to-end: a county CSV in, scored and gated leads out."""

from pathlib import Path

from leadengine.pipeline import ingest, load_all, load_config, process
from leadengine.storage import Store

BASE = Path(__file__).resolve().parent.parent


def test_sample_config_runs_end_to_end(tmp_path):
    config = load_config(BASE / "config" / "counties.example.yml")
    # Sample paths in the config are relative to the project root.
    for entry in config["sources"]:
        entry["path"] = str(BASE / entry["path"])

    leads = ingest(config)
    assert len(leads) == 8

    rules, scoring = load_all({}, BASE)
    leads, _ = process(leads, rules=rules, scoring=scoring)

    assert all(lead.score is not None for lead in leads)
    assert all(lead.score_reasons for lead in leads)

    db = tmp_path / "test.db"
    with Store(db) as store:
        new, updated = store.upsert_many(leads)
        assert new == len(leads) and updated == 0

        # Re-ingesting the same export must not duplicate anything.
        new2, updated2 = store.upsert_many(leads)
        assert new2 == 0 and updated2 == len(leads)

        assert store.stats()["total_leads"] == len(leads)


def test_suppression_survives_a_reingest(tmp_path):
    config = load_config(BASE / "config" / "counties.example.yml")
    for entry in config["sources"]:
        entry["path"] = str(BASE / entry["path"])
    rules, scoring = load_all({}, BASE)

    db = tmp_path / "test.db"
    with Store(db) as store:
        store.suppress(phone="(617) 555-0188", reason="asked to stop")
        suppression = store.suppression_list()

        leads, _ = process(ingest(config), rules=rules, scoring=scoring,
                           suppression=suppression)
        holland = next(l for l in leads if "Holland" in l.contact_name)

        assert "phone" not in holland.contactable_channels
        assert any("suppressed_phone" in f for f in holland.compliance_flags)
