"""Command line entry point: python -m leadengine <command>."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

from .compliance import within_call_window
from .models import Lead
from .outreach import AgentProfile, draft_outreach
from .pipeline import ingest, load_all, load_config, process
from .storage import Store

DEFAULT_CONFIG = "config/counties.yml"
DEFAULT_DB = "leads.db"


def _base_dir(config_path: str) -> Path:
    """Config files are resolved relative to the config's own directory."""
    return Path(config_path).expanduser().resolve().parent.parent


def cmd_ingest(args) -> int:
    config = load_config(args.config)
    base = _base_dir(args.config)
    rules, scoring = load_all(config, base)

    print(f"Reading sources from {args.config} ...")
    leads = ingest(config)
    print(f"  {len(leads)} raw record(s)")

    with Store(args.db) as store:
        suppression = store.suppression_list()
        if len(suppression):
            print(f"  {len(suppression)} suppression entr(ies) loaded")

        leads, merged = process(
            leads, rules=rules, scoring=scoring, suppression=suppression
        )
        if merged:
            print(f"  {merged} duplicate(s) merged")

        new, updated = store.upsert_many(leads)
        print(f"  {new} new, {updated} updated -> {args.db}")

        blocked = [l for l in leads if not l.contactable_channels]
        gated = [l for l in leads
                 if l.contactable_channels
                 and any(f.startswith("[block") for f in l.compliance_flags)]
        open_now = len(leads) - len(blocked) - len(gated)

        print(f"\n{open_now} lead(s) fully open, {len(gated)} partially gated, "
              f"{len(blocked)} blocked entirely")
        if gated or blocked:
            print("Run `show <lead_id>` to see which rule applies.")
    return 0


def cmd_list(args) -> int:
    with Store(args.db) as store:
        rows = store.rows(min_score=args.min_score, lead_type=args.type,
                          limit=args.limit)
        if not rows:
            print("No leads match. Run `ingest` first.")
            return 0

        print(f"{'SCORE':>5}  {'TIER':4} {'TYPE':9} {'NAME':22} "
              f"{'PROPERTY':30} CHANNELS")
        print("-" * 100)
        for row in rows:
            score = row["score"] if row["score"] is not None else 0
            tier = "A" if score >= 75 else "B" if score >= 55 else "C" if score >= 35 else "D"
            channels = ",".join(json.loads(row["contactable_channels"] or "[]")) or "-blocked-"
            print(
                f"{score:>5}  {tier:4} {row['lead_type'][:9]:9} "
                f"{(row['contact_name'] or '?')[:22]:22} "
                f"{(row['property_address'] or '-')[:30]:30} {channels}"
            )
    return 0


def cmd_show(args) -> int:
    with Store(args.db) as store:
        row = store.get(args.lead_id)
        if row is None:
            print(f"No lead with id {args.lead_id}", file=sys.stderr)
            return 1

        print(f"Lead {row['lead_id']}  (score {row['score']}, {row['lead_type']})")
        print(f"  Contact   : {row['contact_name']} ({row['contact_role']})")
        print(f"  Property  : {row['property_address']}, {row['property_city']} "
              f"{row['property_state']}")
        print(f"  Case      : {row['case_number']}  filed {row['filed_date']}")
        print(f"  Channels  : {', '.join(json.loads(row['contactable_channels'] or '[]')) or 'none'}")

        print("\n  Why this score:")
        for reason in json.loads(row["score_reasons"] or "[]"):
            print(f"    - {reason}")

        flags = json.loads(row["compliance_flags"] or "[]")
        if flags:
            print("\n  Compliance:")
            for flag in flags:
                print(f"    - {flag}")
    return 0


def cmd_draft(args) -> int:
    profile = AgentProfile.from_dict(load_config(args.profile))

    with Store(args.db) as store:
        rows = ([store.get(args.lead_id)] if args.lead_id
                else store.rows(min_score=args.min_score, limit=args.limit))
        rows = [r for r in rows if r is not None]
        if not rows:
            print("No leads to draft for.", file=sys.stderr)
            return 1

        written = skipped = 0
        for row in rows:
            channels = json.loads(row["contactable_channels"] or "[]")
            channel = args.channel or (channels[0] if channels else None)

            if channel is None:
                skipped += 1
                continue
            if channel not in channels and not args.force:
                print(f"  skip {row['lead_id']}: compliance does not allow "
                      f"{channel} (use --force to override)")
                skipped += 1
                continue

            lead = _row_to_lead(row)
            text, generator = draft_outreach(lead, profile, channel)
            store.log_outreach(row["lead_id"], channel, text, outcome="drafted")

            print("\n" + "=" * 72)
            print(f"{row['contact_name']}  [{row['lead_id']}]  "
                  f"channel={channel}  via={generator}")
            print("=" * 72)
            print(text)
            written += 1

        print(f"\n{written} draft(s) written to the outreach log, {skipped} skipped.")
    return 0


def cmd_suppress(args) -> int:
    with Store(args.db) as store:
        store.suppress(phone=args.phone or "", email=args.email or "",
                       address=args.address or "", reason=args.reason)
        print("Added to the suppression list. It is honored on the next run "
              "and retained permanently.")
    return 0


def cmd_export(args) -> int:
    with Store(args.db) as store:
        rows = store.rows(min_score=args.min_score, lead_type=args.type,
                          limit=args.limit)
        if not rows:
            print("Nothing to export.")
            return 0

        columns = [
            "lead_id", "score", "lead_type", "contact_name", "contact_role",
            "phone", "email", "mailing_address", "mailing_city",
            "mailing_state", "mailing_zip", "property_address",
            "property_city", "property_state", "property_zip", "apn",
            "assessed_value", "case_number", "filed_date", "county", "state",
            "contactable_channels",
        ]
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([
                    ",".join(json.loads(row[c] or "[]"))
                    if c == "contactable_channels" else row[c]
                    for c in columns
                ])
        print(f"Exported {len(rows)} lead(s) to {args.out}")
    return 0


def cmd_stats(args) -> int:
    with Store(args.db) as store:
        stats = store.stats()
    print(f"Total leads          : {stats['total_leads']}")
    print(f"Leads contacted      : {stats['leads_contacted']}")
    print(f"Suppression entries  : {stats['suppression_entries']}")
    if stats["by_type"]:
        print("By type              : " + ", ".join(
            f"{k} {v}" for k, v in sorted(stats["by_type"].items())))
    if stats["by_tier"]:
        print("By tier              : " + ", ".join(
            f"{k} {v}" for k, v in sorted(stats["by_tier"].items())))
    return 0


def cmd_callcheck(args) -> int:
    base = _base_dir(args.config)
    rules, _ = load_all(load_config(args.config), base)
    ok = within_call_window(rules, args.state)
    print(f"{'OK to call' if ok else 'OUTSIDE calling hours'} in {args.state.upper()} "
          f"right now (local time on this machine).")
    return 0 if ok else 2


def _row_to_lead(row) -> Lead:
    """Rebuild a Lead from a database row for the drafting stage."""
    from . import normalize as nz

    return Lead(
        lead_type=row["lead_type"],
        source=row["source"] or "",
        county=row["county"] or "",
        state=row["state"] or "",
        contact_name=row["contact_name"] or "",
        contact_role=row["contact_role"] or "unknown",
        mailing_address=row["mailing_address"] or "",
        mailing_city=row["mailing_city"] or "",
        mailing_state=row["mailing_state"] or "",
        phone=row["phone"] or "",
        email=row["email"] or "",
        subject_name=row["subject_name"] or "",
        case_number=row["case_number"] or "",
        filed_date=nz.parse_date(row["filed_date"]),
        event_date=nz.parse_date(row["event_date"]),
        property_address=row["property_address"] or "",
        property_city=row["property_city"] or "",
        property_state=row["property_state"] or "",
        apn=row["apn"] or "",
        assessed_value=row["assessed_value"],
        property_vacant=bool(row["property_vacant"]) if row["property_vacant"] is not None else None,
        heir_count=row["heir_count"],
        score=row["score"],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leadengine",
        description="Public-records lead pipeline for real estate agents.",
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="read sources, score, and store leads")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("list", help="list stored leads by score")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--type", choices=("probate", "divorce", "obituary"))
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show one lead with its full reasoning")
    p.add_argument("lead_id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("draft", help="draft outreach for leads")
    p.add_argument("--profile", default="config/agent_profile.yml")
    p.add_argument("--lead-id")
    p.add_argument("--channel", choices=("mail", "email", "phone"))
    p.add_argument("--min-score", type=int, default=55)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--force", action="store_true",
                   help="draft even on a channel compliance has blocked")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("suppress", help="add a contact to the do-not-contact list")
    p.add_argument("--phone")
    p.add_argument("--email")
    p.add_argument("--address")
    p.add_argument("--reason", default="requested")
    p.set_defaults(func=cmd_suppress)

    p = sub.add_parser("export", help="export leads to CSV for your CRM")
    p.add_argument("--out", default="leads_export.csv")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--type", choices=("probate", "divorce", "obituary"))
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("stats", help="pipeline summary")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("callcheck", help="is it legal to call in a state right now")
    p.add_argument("state")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.set_defaults(func=cmd_callcheck)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
