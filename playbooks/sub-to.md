# Sub-To (Mortgage Takeover) — Canonical SOP

> **Canonical, single source of truth for the Sub-To play.** Replaces the old `mortgage-takeover.md`
> + scattered correction blocks. Every claim is sourced. Provenance ledger:
> `assets/CAPTURED_SOURCES.md`. Verbatim email templates: `assets/sources/subto-email-templates-and-scripts.md`.
> One of 5 strategies: **Seller Finance · Sub-To · Hybrid · Fix & Flip · Cash Arbitrage.**

**What it is:** the seller has an existing mortgage and **little/no equity**. You take over the existing
loan (keep making its payment), pay the seller a small lump (often $0), and the mortgage stays in the
seller's name inside a trust. *Not* Seller Finance — there is **no +15% / 40%-of-rent here.**

---

## 1. CRITERIA — who lands here
- **Determination:** existing mortgage present + **low equity-after-costs** (`price − loan − 6% ≤ ~$15K`)
  ⇒ cornered seller ⇒ Sub-To. *(Source: MT course L561-562 "less than 15K in equity"; L535 "going to
  make any money on the sale.")*
- **Search net (PropStream / BBC):** On-market, Active, **Estimated Equity ≤ 20%** (ideal **5–10%**),
  interest rate any. Property types: **SFH · condo · MFH** (MFH can run well above the $500K SF-SFH
  ceiling). Avoid HELOC / reverse mortgage. *(HMHW PropStream slide, `CAPTURED_SOURCES.md` #1.)*
- **Triage sort = lowest equity (motivation) → lowest rate (CoC opportunity) = CALL FIRST.** Rate and
  cash flow are **sorts, never gates** (committed 2026-06-12).
- **Data:** BBC carries balance/rate/equity% at 100% on MT leads → triage ranks on BBC. **PropStream has
  no API** → manual pre-call verify only (loan TYPE for HELOC/reverse, 2nd liens, AVM, owner skip-trace).

## 2. COMPS — what to verify
- **Load-bearing = ARV** (to confirm the equity is really thin) **+ existing PITI** (the payment you
  inherit). Pull SOLD comps (Cash Course L716-895 ritual, see `comps-sop.md`).
- Rent only matters to set the **exit** (below), and BBC populates it ~40% of the time — verify on Zillow.

## 3. MATH — the offer + the exit
- **The lump (cash to seller):** rate/price-scaled. **6%+ rate ⇒ $0 down** (MT L793-795 "6% interest
  rate, you can do $0 down"); ≤$150K ⇒ up to a **$5–12K** lump (L738 "$12,000 down… 10K works"); pricier
  ⇒ ~5%. Seller monthly ≈ $0 (you pay the *bank*, not the seller).
- **Trojan-Horse pivot offer:** `cash offer = loan balance + 4% of asking` → nets the seller ~$0 → make
  it **to be rejected** → the agent reveals the equity → you pivot to the takeover/trust pitch. Best on
  5–10% equity. *(CAPTURED_SOURCES.md #2.)*
- **EXIT CHANNEL (cash flow tags it, never gates):**
  - **Cash-flows** at the existing payment (`rent×0.80 − PITI > 0`, typically cheap < ~$130K) ⇒ sell to an
    **investor**.
  - **Doesn't cash-flow** (expensive + 6–7%) ⇒ **$0 down, sell to a live-in / retail buyer** (a homeowner
    who can't get traditional financing). *(MT L1067-1080 verbatim: "you're only selling those to somebody
    who wants to live in the property.")* These are real deals — never reject them.

## 4. SCRIPT — the call
- **Homeowner-direct** (low-equity Lightning Leads), not listing agents (MT L21-11). Or the Trojan-Horse
  via the agent.
- **Broach the loan (Steve Ward script):** *"If you've got a mortgage, I'd be happy to take over your
  payments — a servicing company pays it so you don't worry. If a payment's ever missed, the property
  returns to you and you keep everything paid so far. Since I'd run it as a rental, I need the rate/terms
  to make sure it cash-flows."*
- **Top objections** (full scripts in the email deck): "subto is illegal" → **HUD-1 line 203** + Modern
  Real Estate Practice Unit 12; "due-on-sale" → land trust, banks don't call performing loans; "what if
  you stop paying" → **deed-back after 2 missed payments**; "can my seller get a new loan after?" → trust
  certificate + occupancy agreement (VA-loan angle), partner originator "Andrew."

## 5. EMAIL TEMPLATES
- **60+ verbatim Richard templates** at `assets/sources/subto-email-templates-and-scripts.md` (TRUST
  emails, Trojan-Horse email + post-call text, cash-offer, "LOW EQUITY EMAIL THAT GOT ME 5 DEALS IN 1
  CALL", objection scripts). Source: Discord › Mortgage Takeover › Email Templates.
- Canonical "latest TRUST email" pattern: take over the debt + small lump + cover closing + frame the
  trust as a capital-gains/sale workaround, referencing your portfolio + proof of funds.
- *(Integration TODO: the Offer Oven "commit → template" feature will pick the right one by subtype and
  fill the numbers — email/offer template only, NOT the contract.)*

## 6. CONTRACT — Trust Acquisition
- **The Sub-To contract = Trust Acquisition** (a sub-category of subject-to). House → **revocable living
  trust** via a trust attorney; deed transfers in, **mortgage stays in the seller's name**; buyer assigned
  **90–95% beneficial interest**, seller keeps **5–10%**; buyer/trust pays the mortgage. Lender not
  notified (not a "sale") → lowers due-on-sale risk. *(CAPTURED_SOURCES.md #2.)*
- Legal basis: **HUD-1 Settlement Statement line 203** ("existing loan(s) taken subject to") + Modern
  Real Estate Practice Unit 12.
- Doc: the editable **"Mortgage Takeover OR Seller Finance" .docx** (in Drive `1 - Seller Finance/`) +
  the **Assignment Disclosure Addendum** for the wholesale assignment. *(Contract .docx body not yet read
  — ingest before relying on clause-level detail.)*

## 7. TERMINOLOGY
Subject-to · Trust Acquisition · beneficial interest · revocable living trust · due-on-sale clause ·
deed-back · HUD-1 line 203 · land trust · existing PITI · equity-after-costs. *(Full FAQ:
CAPTURED_SOURCES.md #2 + the MT reference doc.)*

---

## Sources
MT course transcript L21-11, L399-409, L535, L561-562, L738, L793-795, L1067-1080 · HMHW Discord
*Mortgage Takeover* group (Trust Acquisition doc, 60-template email deck, PropStream slide) ·
`comps-sop.md` · Steve Ward coaching §3 · BBC live data pull (2026-06-12) · `triage.py classify_strategy`.
