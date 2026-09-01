# Selling the Work

**What the business model looks like when operations are run by AI — and which parts are already load-bearing.**

Research compiled September 2026 from web sources and X/Twitter discourse.
Published version: https://claude.ai/code/artifact/08d322dc-4683-4d96-b0d0-eca13e7ef3c3

---

## The short answer

The unit you sell stops being **access** and starts being **completed work**. Seats
measured how many people could log in; agents break that meter, because value now
goes up as the number of logins goes down. Pricing, margins, moats and headcount all
follow from that one change.

Two caveats to hold throughout:

1. The margin structure underneath the new model is **worse** than SaaS, not better.
2. "Outcome pricing" is closer to a talking point than a settled practice — the live
   examples are real but narrow, and buyers are slower than the essays.

---

## 1. The shift: copilots compete for the software budget, autopilots for payroll

The clearest statement is Sequoia partner Julien Bek's March 2026 essay
[Services: The New Software](https://sequoiacap.com/article/services-the-new-software)
(~3M views on X). The argument is arithmetic: for every dollar spent on software,
roughly six go to services and labor. A tool that helps a person work bills against
the small number. A system that does the work bills against the large one.

This reframes the sale. Not a faster way to produce an invoice — the invoice. Not a
CRM for the sales team — the qualified pipeline. The buyer's question moves from "is
this better than our tool" to "is this cheaper than our people."

Markets partially priced this in: early February 2026 took roughly **$1 trillion off
US software stocks in about a week** (the "SaaSpocalypse"), not on bad earnings but on
a structural question — if an agent does the task without opening the interface, what
is the per-seat licence for? The correction deepened through spring. Whether it was
repricing or overshoot is contested; the question's legitimacy is not.

> "AI has reintroduced marginal cost into software. Every prompt costs money. Every
> agent run costs money. Software founders have to think like manufacturing companies
> with COGS now." — M Mohan, on X

---

## 2. How you charge: four meters, and the boring one is winning

Foundry's Joanne Chen laid out the four live options on X, with the finding that
matters most: reality is messier than "everything goes outcome-based." Vendors love
outcome pricing because it captures more dollars per customer. Buyers resist because
they need a number they can hand a CFO.

| Model | Unit | Favors | Where it breaks |
|---|---|---|---|
| Access | Per seat / month | Buyers — predictable | Revenue falls as the product succeeds |
| Usage | Per call / token | Vendors — tracks COGS | Buyer can't forecast; meter anxiety suppresses use |
| Workflow | Per completed workflow | Roughly neutral | Needs a workflow both sides agree is "done" |
| Outcome | Per result delivered | Vendors — captures real value | Attribution fights; no revenue floor; slows the sale |
| **Hybrid** | **Platform fee + variable unit** | **The one actually being adopted** | More complex to explain and bill |

Hybrid is the practical default and gaining share fastest. Bessemer's 2026
[AI pricing and monetization playbook](https://www.bvp.com/atlas/the-ai-pricing-and-monetization-playbook)
puts hybrid at **41% of AI vendors, up from 27%** a year earlier; Kyle Poyar's survey
of 230+ companies shows the same direction (25% → 37%). Structure: a base fee covering
fixed cost, onboarding and the cost of tasks the agent *fails*, plus a variable unit
tied to work the buyer already counts.

### Published outcome price cards, 2026

| Vendor | Unit | Price | Note |
|---|---|---|---|
| Intercom Fin | Resolved support conversation | $0.99 | No resolution, no charge |
| Zendesk | Automated resolution | $1.50 / $2.00 | Committed volume vs. pay-as-you-go |
| HubSpot Breeze | Resolved conversation | $0.50 | Moved to outcome pricing April 2026 |

What these share: a **binary, machine-verifiable outcome inside the vendor's own
system.** A ticket is resolved or it isn't, and the vendor's software is the referee.
That is why support went first and may stay unusual. "Closed deal," "improved
retention," "reduced cost" all have a second party with a motive to dispute the count.
Parloa argued in Forbes (Jan 2026) that outcome-based pricing is
["the most expensive myth in enterprise AI"](https://www.forbes.com/sites/parloa/2026/01/06/outcome-based-pricing-the-most-expensive-myth-in-enterprise-ai/).
The specific objection is worth taking seriously: **if you can't referee the outcome,
you haven't built a pricing model, you've built a future argument.**

---

## 3. The margin: you are running a factory now

Software's 80–90% gross margin came from a marginal cost of ~zero. Inference is not
zero and sits in COGS. Every agent run costs money whether or not the customer pays
for the result — exactly why pure outcome pricing is dangerous without a floor.

| Business type | Gross margin | Basis |
|---|---|---|
| Traditional SaaS | 80–90% | Reported |
| AI-native, 2026 | 50–60% | Reported (Bessemer, Feb 2026) |
| AI-native, 2028 | 70%+ | Projection if token costs keep falling |

Survey averages sit near **52% for 2026, up from 41% in 2024.**

Two forces pull opposite ways:

- **Against you:** ICONIQ's 2026 survey found model inference rising from **20% → 23%
  of total spend** as products mature. COGS grows as a share, because customers find
  more expensive things to ask for.
- **For you:** GPT-4-class inference ran ~$20/M tokens in late 2022 and roughly
  **$0.40 for equivalent capability by early 2026** — a ~1000× drop in three years.

**Practical read: price for today's cost, and let deflation be your margin expansion
rather than your business plan.** A company at 50% today can plausibly drift toward
70% by 2028 without touching its price card. A company that already priced as if
inference were free has no cushion — and this is now a fundraising problem, since 50%
margins read very differently to an investor than 80% ones.

---

## 4. Two different businesses hide inside the same question

### A. You run operations inside a business

Your model doesn't change; your denominator does. Output per person starts governing
decisions, and the spread between median and top is wider than at any point in
software's history.

| Metric | Value | Source |
|---|---|---|
| Median ARR/employee, B2B SaaS | $193K (+29% YoY) | Aleph / Benchmarkit 2026 |
| Public SaaS median | ~$395K | up from ~$327K in 2022 |
| Bessemer AI "Supernova" cohort | $1.13M avg | Cloud 100 benchmarks |
| Emerging supervision ratio | 1 human : 5 agents | Reported operating pattern |

The structural change is **supervision, not speed.** Teams get restructured rather
than merely accelerated — who does the work and who checks it become different roles.
The highest-leverage new hire being described is an **agent owner**: a named person
carrying a P&L for a set of agents, which converts "agentic ROI" from a slide into an
accountable number.

Salesforce is the cleanest public data point: roughly **$300M budgeted on Anthropic
tokens for 2026** alongside a frozen engineering hiring plan and zero net new
engineering hires in FY26, on 30%+ reported productivity gains. Read it as a signal
about where money moves — a payroll line becomes an inference line — not as proof the
trade works everywhere.

### B. You sell AI operations to other businesses

Reported economics are good, but most figures come from practitioners marketing their
own model. Treat as a range to negotiate within, not a benchmark.

| Shape | Reported range | Confidence |
|---|---|---|
| SMB automation retainer | $2,000–$10,000/mo against $200–$1,000 tool+API cost | Vendor blog |
| Embedded US SMB engagement | $8,000–$25,000/mo | Vendor blog |
| Implementation project | $5,000–$50,000 one-time | Vendor blog |
| Fractional Chief AI Officer | $20,000–$80,000/mo at 1–3 days/week | Market survey |
| Fractional COO | $5,000–$12,000/mo, or 1–5% equity early-stage | Market survey |
| **Savings share** | **15–25% of realized savings over 12–24 months** | Market survey |

Three findings recur across every source and agree with each other:

- **Productize or stay poor.** Productized firms reportedly earn ~4× more per hour
  than custom-build firms — 20 clients at 40 hrs/month vs. 20 clients at 200.
- **Go vertical.** Industry-specific automation commands 2–3× horizontal pricing,
  because domain rules and compliance can't be prompted into existence.
- **The savings-share structure is the interesting one.** It's outcome pricing with a
  referee both sides can live with — measurement window, agreed baseline, a percentage
  — and it's how a small operator gets paid like a principal, not a contractor.

The furthest version is already funded: VC-backed AI platforms **buying** services
firms outright — accounting, MSPs, property management, insurance brokerage, HVAC —
and running them AI-native for the margin spread. a16z's Troy Kirwin has framed 2026
as the year venture capital starts acquiring private equity's playbook. Same idea as a
savings share, with the operator taking the whole P&L instead of a slice.

---

## 5. What defends it: the model is not the moat

Foundation models are an API call away for every competitor. The defensibility
literature converges on four things that compound with operating time:

- **Proprietary data with a live feedback loop.** Not a data dump — data your workflow
  generates by running, which sharpens the validation rules that let you run harder
  workflows.
- **Being the system of record.** The switching cost isn't the software; it's that your
  product is where the audit trail, retention schedule and approval live. A model
  provider cannot replicate a regulator considering your output the sanctioned one.
- **Contract rights over derived data.** Least glamorous, most often lost at signature.
  If the customer owns everything your system learns, you built their moat.
- **Encoded tacit rules.** Corner cases that never made it into documentation. This is
  why vertical beats horizontal on both price and retention.

Hard number attached: seat-only billing correlates with roughly **2.3× the churn** of
hybrid or consumption billing.

---

## 6. What breaks it: failure modes are operational, not technical

**Most of this doesn't work yet.** MIT's finding — ~95% of enterprise GenAI pilots
producing no measurable ROI — held through 2026. The 5% that work share a pattern, and
it isn't budget or model quality: agents wired into real institutional data, a baseline
measured *before* the pilot, honest total-cost accounting, and an operating-model
change rather than a tool rollout. Those getting it right are reported at ~$3.70
returned per dollar. The distribution is bimodal, not average.

**The wrapper graveyard.** Estimated failure rates for thin AI wrappers run near 80% by
end of 2026, most never reaching revenue. Jasper is the cautionary example: $131M
raised, $1.5B valuation, ~$120M revenue in 2023, collapse to $35–55M once the
underlying model improved. If your differentiation is the prompt, you're renting your
business from a model provider.

**Nobody is insuring your outcomes.** The quietest and most dangerous item. As of
January 2026 the body writing standard policy language introduced explicit generative-AI
exclusions for general liability, and major carriers followed. When you sign an outcome
guarantee or indemnity, check whether anything funds it — a vendor can promise an
accuracy SLA with no policy behind it, and the customer's Tech E&O likely won't respond
either. Affirmative AI cover exists as a separate endorsement and generally requires
documented governance to bind. **Read this before you sell a guarantee, not after.**

**Buyers move slower than the thesis.** Fewer than one in five enterprise buyers still
prefer classic per-user pricing — but preference is not procurement. Most organizations
will run hybrid stacks another two to three years, and many remain most comfortable
with something simple and predictable.

---

## 7. A migration path (these are sequential)

1. **Find your refereeable unit.** Name one piece of work with a definition both sides
   accept and a count neither can dispute. If you can't referee it inside a system you
   control, price on workflows completed instead and keep looking.
2. **Measure a baseline before you automate anything.** Cost per unit, cycle time,
   error rate, as they are today. This is the single practice separating the 5% from
   the 95%, and it's the evidence a savings-share contract needs. You cannot
   reconstruct it afterwards.
3. **Price hybrid, with a floor that covers failure.** Base fee sized to fixed cost
   plus the inference burned on tasks the agent doesn't complete; variable unit on top.
   Model COGS at today's token prices, not hoped-for ones.
4. **Get the data rights in writing.** Derived-data rights, retention, what you may
   learn across accounts. Settle at first signature — nearly impossible to claw back at
   renewal, and it's most of what makes the business worth more than its revenue.
5. **Then go deeper, not wider.** One vertical, become the system of record for one
   regulated or audited process. Breadth commoditizes; the audit trail doesn't.

---

## 8. How solid is this

**Solid.** Published price cards (Intercom, Zendesk, HubSpot), named VC research
(Bessemer, Sequoia, ICONIQ), the February 2026 software selloff, insurance-exclusion
changes. Checkable primary or near-primary sources.

**Directionally reliable.** Benchmark surveys — revenue per employee, hybrid pricing
adoption, gross margin bands, the MIT pilot failure rate. Real methodology,
self-selected samples, wide error bars.

**Treat as anecdote.** Agency retainer ranges, the 4× productization multiple, the 80%
wrapper failure rate, the 1:5 agent ratio. These circulate mostly through practitioner
blogs and X threads written by people selling the model being described.

One structural bias: nearly everyone publishing on this topic is long the thesis. VCs
are funding it, agencies are selling it, pricing-tool companies need pricing to change.
The genuinely skeptical material — Parloa's critique, the margin-compression analyses,
the MIT failure data — is thinner but has held up better than the forecasts.

---

## Sources

**Primary**
- [Sequoia — Services: The New Software](https://sequoiacap.com/article/services-the-new-software)
- [Bessemer — The AI pricing and monetization playbook](https://www.bvp.com/atlas/the-ai-pricing-and-monetization-playbook)
- [Forbes / Parloa — Outcome-Based Pricing: The Most Expensive Myth](https://www.forbes.com/sites/parloa/2026/01/06/outcome-based-pricing-the-most-expensive-myth-in-enterprise-ai/)
- [Fortune — Sequoia on AI-enabled services](https://fortune.com/2026/04/21/services-are-the-new-software-sequoia-venture-capital-julien-bek-ai-native-eye-on-ai/)

**Market and margin**
- [Forbes — SaaSpocalypse](https://www.forbes.com/sites/petercohan/2026/02/06/saaspocalypse-now-ai-is-disrupting-saas---but-not-all-software-is-doomed/)
- [AllianceBernstein — Software's Big Sell-Off](https://www.alliancebernstein.com/us/en-us/investments/insights/investment-insights/softwares-big-sell-off-structural-risk-or-narrative-noise.html)
- [Avante — AI startup gross margin benchmarks](https://avanteventures.com/en/library/ai-startup-gross-margin-benchmark-2026)
- [The SaaS CFO — ARR per employee benchmarks](https://www.thesaascfo.com/arr-per-employee-benchmarks/)
- [SaaS Mag — The AI COGS problem](https://www.saasmag.com/ai-cogs-saas-gross-margin-compression/)
- [Kyle Poyar / GTM Newsletter — revenue per employee](https://thegtmnewsletter.substack.com/p/revenue-per-employee-boom-not-ai)

**Risk and adoption**
- [Forbes — MIT on GenAI pilot failure](https://www.forbes.com/sites/jasonsnyder/2025/08/26/mit-finds-95-of-genai-pilots-fail-because-companies-avoid-friction/)
- [Honigman — The AI insurance gap](https://www.honigman.com/the-matrix/ai-insurance-gap-what-it-means-for-technology-contracts)
- [Plum — AI liability insurance explained](https://www.plumhq.com/blog/ai-liability-insurance)
- [Stanford Law — Defensible moats for vertical AI](https://law.stanford.edu/wp-content/uploads/2026/06/Defensible-Moats-for-Vertical-AI-Application-Companies-in-a-New-Competitive-Landscape.pdf)
- [Futurum — Buyer pricing preferences](https://futurumgroup.com/press-release/are-outcome-based-and-hybrid-ai-pricing-models-rewriting-the-vendor-playbook/)

**X / Twitter discourse**
- [Joanne Chen](https://x.com/joannezchen/status/2056799656042983708) — the four pricing models
- [M Mohan](https://x.com/mukund/status/2079231643970367928) — marginal cost returns to software
- [Aaron Levie](https://x.com/levie/status/1903588869301481477) — cheaper models vs. costlier use cases
- [Bret Taylor](https://x.com/btaylor/status/1866557946223792516) — outcome pricing for agents
