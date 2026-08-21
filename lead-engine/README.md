# Lead Engine

A public-records lead pipeline for real estate agents working probate and
divorce listings. It ingests county court records, deduplicates them,
scores them on the signals that actually predict a listing, gates every
lead through compliance rules, and uses Claude to draft the first touch.

---

## Read this before you read the code

You asked for the best way to use AI to find people whose relatives just
died or who just got divorced. Two honest things up front, because they
shape everything below.

**First: AI is not the hard part, and it is not where the leverage is.**
The records you want are public. Probate filings, divorce decrees, and
obituaries are published by county clerks precisely so that anyone can
read them. The hard parts are *getting the data on a schedule*, *not
mailing the same family three times*, and *not saying something
appalling to someone in the worst month of their life*. This pipeline
spends most of its code on those three problems. Claude is used in
exactly one place - drafting outreach - because that is the one place a
language model genuinely beats a template.

Be skeptical of any tool that sells you "AI-powered lead generation" for
this niche. What almost all of them sell is a scraped list. The list is
a commodity; the follow-through is not.

**Second: this niche is legal, and it is the most heavily regulated
corner of lead generation.** Probate and divorce prospecting is a
long-established practice that plenty of good agents build a career on.
It is also where the TCPA bites hardest ($500-$1,500 per violation),
where several states impose a statutory waiting period after a death
before heirs may be solicited, and where a single tone-deaf letter
becomes a complaint to your commission. The pipeline is built so the
compliance step is not something you can forget - a lead comes out of it
with an explicit list of channels you may use, and every block is
explained.

Nothing here is legal advice. Take `config/state_rules.yml` to your
broker before your first mailing.

---

## What this actually does

```
county CSV exports
        |
        v
   [ ingest ]      map their column names onto a normal schema
        |
        v
   [ dedupe ]      collapse the same house arriving from three sources
        |
        v
   [ score  ]      0-100, with a written reason for every point
        |
        v
[ compliance ]     which channels may I use, and why not the others
        |
        v
   [ draft  ]      Claude writes the letter; you read it before it goes
```

Each stage is a module you can run, test, and replace independently.

---

## Quickstart

```bash
cd lead-engine
pip install -r requirements.txt

# Start from the worked example (real column names, fake people)
cp config/counties.example.yml config/counties.yml
cp config/agent_profile.example.yml config/agent_profile.yml
$EDITOR config/agent_profile.yml        # your name, license, brokerage

python -m leadengine ingest             # read, score, and store
python -m leadengine list                # ranked, with allowed channels
python -m leadengine show <lead_id>      # why this score, why these blocks
python -m leadengine draft --limit 3     # first-touch drafts
```

Out of the box this runs against `samples/`, eight invented records that
exercise every branch. It works with no API key - drafting falls back to
a plain template so you can see the whole pipeline before spending
anything.

Ranked output looks like this:

```
SCORE  TIER TYPE      NAME                   PROPERTY                  CHANNELS
   91  A    probate   David R Holland        412 Oak Ridge Dr          mail,phone
   82  A    probate   Sean O'Brien           905 Limestone Trl         mail,phone
   55  B    probate   Thomas Walsh           770 Meadowlark Ln         mail
    7  D    probate   Lily Chen              -                         mail,phone
```

Holland scores 91 because an out-of-state executor with a vacant house
and 89% equity, filed four months ago, is the most listable record a
probate docket produces. Walsh is mail-only because the death was 15
days ago. Chen scores 7 because the filing names no property, so there
is nothing to sell yet.

---

## The part nobody tells you: getting the data

This is the real work, and it is unglamorous.

**Ask the clerk.** Most county clerks either publish bulk probate and
civil dockets or will run an export on request, often for a small fee.
Ask for "bulk data" or file a public records request. A documented
export delivered on a schedule beats scraping a docket search page - it
does not break when they redesign the site, and it keeps you clear of
the portal's terms of use. That is why this pipeline is CSV-first.

**You will need two more lookups.** Court records name people, not
houses. To get from a decedent to a property you need the county
assessor (parcel, assessed value, mailing address) and, for phone
numbers, a skip-tracing service. Both are per-county decisions; the
`sources/` interface is where you plug them in.

**Buying a list is a legitimate shortcut** — it is how most agents
start. Feed a purchased CSV in through the same `csv` source by writing
a mapping for its columns, and it gets the same dedupe, scoring, and
compliance treatment as anything else.

Adding a county is a config change, not a code change:

```yaml
sources:
  - type: csv
    lead_type: probate
    county: Travis
    state: TX
    path: data/travis-probate-2026-08.csv
    mapping:            # left: pipeline field, right: their column heading
      case_number: "CAUSE NO"
      filed_date: "FILE DATE"
      subject_name: "DECEDENT NAME"
      contact_name: "APPLICANT"
```

---

## How scoring works

Weights live in `config/scoring.yml`. The defaults are priors, not
findings — **retune them against your own closed deals.** After 20-30
outcomes you will know which signals actually preceded a listing in your
market, and that beats anyone's defaults.

| Signal | Default | Why |
|---|---|---|
| Authority to sell | 25 | An executor can sign a listing agreement. An heir often cannot. |
| Timing | 20 | Probate has a window: too early and there is no authority, too late and it is already listed. |
| Names real property | 15 | A filing with no property is not a lead yet. |
| Absentee contact | 15 | The strongest motivation signal there is. Nobody wants to manage a house from three states away. |
| Equity | 15 | A sale that will not clear costs does not happen. |
| Vacant | 10 | An empty house costs money every month. |
| Multiple heirs | 5 | Co-owners liquidate; you cannot split a house four ways. |
| Reachable | 5 | Everything else is theoretical without contact info. |

Every lead carries its reasoning, which is the point:

```
$ python -m leadengine show c4b4f9e6516a09f7
  Why this score:
    - executor can sign a listing agreement
    - only 9 days since filing - too early to approach (window opens at 30)
    - strong equity position (~72%)
  Compliance:
    - [block:phone/sms/email] mourning_period: 15 day(s) left in TX's
      30-day post-death waiting period (mail permitted)
```

"The model said 87" is not something you would want to defend. A written
reason is.

---

## Compliance

The default posture is that a channel is **closed unless a rule opens
it**. What the pipeline enforces:

- **Post-death waiting periods.** Configurable per state. Recent deaths
  are mail-only, or fully blocked where mail is not carved out.
- **No date, no contact.** A probate record with no date of death is
  blocked entirely — you cannot prove the waiting period has passed.
- **Pending divorces.** Neither spouse can usually sell alone before the
  decree, and contacting a party mid-litigation is asking for trouble.
- **Cold SMS is always blocked.** The TCPA requires prior express
  written consent for marketing texts. A court record is not consent.
  This is the single most common way agents get sued in this niche.
- **Suppression is permanent.** `suppress` adds a phone, email, or
  address and it is honored on every subsequent run. Nothing is ever
  deleted — the TCPA requires you to retain do-not-call requests for
  five years.
- **Calling hours.** `callcheck TX` tells you whether you are inside the
  8am-9pm window. It exits non-zero when you are not, so you can gate a
  dialer with it.

Two things it does **not** do, which are on you:

1. **DNC scrubbing.** There is a hook (`dnc_scrubbed` in the state
  rules) and a suppression list, but no registry subscription. You need
  to subscribe to the national registry and scrub before you dial.
2. **Verify your state's actual law.** `state_rules.yml` ships with a
  conservative 30-day default across the board and every entry marked
  `verified: false`. Those numbers are a decent-behavior floor, not a
  researched survey. Confirm them and set the flag.

---

## The AI part

`outreach.py` is the only module that calls a model, using
`claude-opus-5` through the Anthropic SDK.

What makes it worth using over a mail merge is the system prompt, which
is written as hard constraints rather than style notes:

- Never acknowledge a death and pivot to business in the same breath.
- Never mention the court filing or how you found them. They know their
  business is public record; saying so reads as surveillance.
- No urgency, no scarcity, no deadline, no "I have a buyer."
- No legal or tax advice, no speculation about probate timelines.
- Don't ask for a meeting in a first letter. Offer information and a way
  to reach you.
- Use only supplied facts. Invent nothing — no guessed names, no
  invented credentials.

The model gets a deliberately narrow brief: the situation, the
recipient's name and role, the property, and whether they live out of
state. Case numbers, filing dates, and scores are withheld, because the
model has no legitimate use for them and they leak into drafts.

Everything is a **draft**. Read it before it goes out — your license
number is on it.

```bash
export ANTHROPIC_API_KEY=sk-...
python -m leadengine draft --lead-id a3aea4a4 --channel mail
```

Without a key it falls back to a template, so the pipeline never breaks
on a missing credential.

---

## Commands

| Command | What it does |
|---|---|
| `ingest` | Read every source, dedupe, score, gate, store |
| `list` | Ranked leads with their allowed channels |
| `show <id>` | One lead: full scoring reasons and compliance flags |
| `draft` | Generate outreach drafts (`--channel mail\|email\|phone`) |
| `suppress` | Add a do-not-contact entry (permanent) |
| `export` | CSV for your CRM |
| `stats` | Pipeline summary by type and tier |
| `callcheck <ST>` | Are you inside legal calling hours right now |

---

## Layout

```
leadengine/
  models.py        Lead schema shared by every stage
  normalize.py     Names, addresses, phones, dates, money
  sources/         Adapters; config-driven CSV importer
  dedupe.py        Blocking + fuzzy match + field-wise merge
  score.py         Explainable 0-100 scoring
  compliance.py    Channel gating, suppression, calling hours
  outreach.py      Claude drafting with an offline fallback
  storage.py       SQLite: leads, outreach log, suppression
  pipeline.py      Stage orchestration
  cli.py           Command line interface
config/            State rules, scoring weights, county mappings
samples/           Invented records that exercise every branch
tests/             55 tests
```

```bash
python -m pytest tests/ -q     # 55 passed
```

---

## What to do first

1. Run the quickstart against the samples. Five minutes, no API key.
2. Call your county clerk and ask how to get the probate docket. This is
   the step that actually determines whether any of this works.
3. Take `config/state_rules.yml` to your broker and fill in the real
   numbers for your state.
4. Write one mapping for your county's export and run `ingest`.
5. Work the A-tier leads by **mail** first. It is the least intrusive
   channel, it has no DNC exposure, and in this niche it outperforms
   calling — because everyone else is calling.

---

## A note on the data you are handling

Every row is a real person having a bad year. `.gitignore` keeps the
database and exports out of git for a reason. Don't commit lead data,
don't resell it, and honor every opt-out on the first request — which is
both the decent thing and, for do-not-call requests, the law.
