# Strategy Realignment Plan — Aligned to HMHW's 3 Strategy Groups

**Goal:** SOP **and** triage share ONE structure that mirrors HMHW's official Discord groups; triage
**output is grouped** by those strategies; and the **method of determination** (why a lead lands in a
group) is explicit on every card and in the SOP. Plan only — no code until approved.
Order: **triage → SOP → templates.** Call sheet = **20 + overflow**. Thresholds = **Richard's rules**
(extracted below from the MT course). Delivery = **triage fully, then review**.

---

## 0. The canonical taxonomy = HMHW's 3 Discord groups

From the server structure (each group has its own `email-templates`, `contracts`, `terminology`,
`faq`, `extra-info`):

```
🏚️ CASH DEALS              → Fix & Flip / Cash arbitrage
🤑 SELLER FINANCE (Creative) → Free & Clear (no mortgage)
🏛️ MORTGAGE TAKEOVER (Creative) → existing mortgage; channel: trust-acquisition
       ├─ Sub-To   (low / no equity — pay a small lump to take over the debt)
       └─ Hybrid   (meaningful equity + LOW rate — assume loan + carry equity as a note)
```

So there are **3 top-level groups**; Hybrid & Sub-To are **sub-types inside Mortgage Takeover**
(not separate strategies). Triage buckets, SOP sections, and template folders all use these 3 names.

| Group | Equity / loan | Seller-payout numbers | Pitch |
|---|---|---|---|
| **Seller Finance** | No loan (free & clear) | **40%-of-rent → seller** (valid ONLY here) | Checkmate (MFH/non-retail) · Stale-SFH (cheap) |
| **Mortgage Takeover · Sub-To** | Loan, **low/neg** equity-after-costs | Small lump to seller ($5–12K / scaled down); ~no monthly | Trojan Horse → Sub-To |
| **Mortgage Takeover · Hybrid** | Loan, **high** equity, **low** rate | Assume loan + carry equity as a note; seller monthly ≈ `40%·rent − existing PITI` | Trojan Horse → Hybrid |
| **Cash Deals** | Cash | 70%-of-ARV (F&F) or cash arb | Trojan Horse open → Cash |

**Why 40%-of-rent is Seller-Finance-only (Tim's correction):** it assumes the seller has no mortgage to
service. With an existing loan (MT group) *we* cover that PITI, so the seller's realizable monthly drops
by exactly that — MT uses lump/assume math, not 40%-of-rent.

---

## 1. The determination method — Richard's actual rules (made explicit)

This is the part the user wants crystal-clear. Each lead is routed by a transparent test; the card shows
the test result ("why it's here"). Rules quoted/derived from the **Mortgage Takeover course transcript**.

### Step 1 — Cash vs Creative
- BBC tag `fixAndFlip`, OR distress signals (pre-1940 + <$80K, heavy-rehab vision) → **CASH DEALS**.

### Step 2 — Free & Clear vs Existing Mortgage
- `loan_balance ≈ 0` (BBC `sellerFinance` tag / Propwire "free & clear") → **SELLER FINANCE**.
  - Sub-label: **Checkmate** if MFH 5+ or non-retail 2–4plex (FHA fails → DSCR fails → SF is the only
    exit); else **Stale-SFH** if cheap + long DOM.
- Loan present → **MORTGAGE TAKEOVER** group → Step 3.

### Step 3 — Sub-To vs Hybrid (inside Mortgage Takeover)
The deciding test is **equity-after-costs**, not raw equity (MT course L341–410, L538–566):
```
seller_net_at_sale = likely_sale_price − loan_balance − (likely_sale_price × 0.06 realtor)
```
- **Sub-To** when `seller_net_at_sale` is **low or negative** ("they can't make money on the sale" —
  the cornered seller). You give a **small lump to take over the debt**, scaled by price:
  - ≤ $150K → up to **10% down** · > $150K → **~5% down** · often just a flat **$5–12K** lump
    (L744–793: "10K works, 12K works, 9K works"; "above 150K, probably 5% down").
- **Hybrid** when there's **meaningful equity** AND the **rate is low**: assume the loan and **carry the
  equity as a seller note** (they want their equity, not a tiny lump).
- **REJECT (or pass)** when **high equity + high rate** — L860–905: "$100K equity and a 7% interest
  rate… I can't give him a down payment because of that 7% interest" → no workable structure.

### Step 4 — The universal MT gate: it must CASH FLOW at the existing payment
MT course L686–693: *"in mortgage takeover deals, cash flow is the name of the game. If your house
isn't cash flowing, it's hard to find a buyer."* So:
- **CF = rent·0.80 − existing PITI must be > 0** to qualify any MT lead.
- **Rate → down-payment rule** (NOT a hard 5.5% cutoff — replace the current code's gate):
  - Low rate (≤~3%) = no-brainer, supports a down payment.
  - **6% rate → $0 down only** (L789–795: "if it has a 6% interest rate, you can do $0 down").
  - 7%+ → only if cheap enough to still cash flow; usually pass.
  - Cheap (<~$130K) cash-flows almost regardless of rate; expensive needs an "insanely low" rate
    (L660–685).

> **Net effect on the code:** the current `tier()` gates Hybrid on a flat `rate ≤ 5.5%` + `equity ≥ $20K`.
> Replace with: (a) cash-flow-positive-at-existing-payment gate for the whole MT group; (b)
> equity-after-costs to split Sub-To vs Hybrid; (c) rate-driven down-payment (6% ⇒ $0 down) instead of a
> binary rate cutoff.

---

## 2. TRIAGE changes (`scripts/triage.py`)

- **Data linchpin:** `loan_balance`/`interest_rate` (L807–808) are reliable only on BBC
  `mortgageTakeover`-tagged leads. Free-&-clear is inferred for `sellerFinance` tags → card carries an
  **"equity unverified — confirm via PropStream/Propwire before calling"** pill (Steve's rule). No scraping.
- **Replace `tier()` → `classify_strategy()`** returning the group + subtype:
  `CASH | SF(Checkmate|StaleSFH) | MT_SUBTO | MT_HYBRID | REJECT`, using the Step 1–4 logic above.
- **Fix numbers per group** in `score()`:
  - SF → 40%-of-rent (keep). MT_SUBTO → lump-to-seller (scaled) + CF at existing PITI; seller monthly ≈ 0.
    MT_HYBRID → seller note = `max(0, 0.40·rent − existing PITI)`, equity residual → balloon; verify the
    L1717 HY block subtracts existing PITI (fix if not). CASH → 70% ARV (keep).
- **Each card shows the determination** ("Existing loan $94K @3%, seller nets ~$8K at sale ≤10% ⇒ Sub-To;
  CF +$310 at existing payment ✓") so the *method is visible*, not hidden.
- **Pitch name + Steve's open→settle ladder** per card (down: open 6.5–7% → settle 10–12%; price: open at
  asking; balloon: open 15 → floor 7; prefer interest baked into price).
- **Output grouped by the 3 strategies**, each subtotaled; a **"📞 Today's Call Sheet — 20 best"** ranked
  across all groups on top (overflow listed below per group). Rank = `fee_potential × motivation × fit`.

## 3. SOP changes (skill references) — mirror the SAME 3 groups
- Rewrite **`deal-criteria.md`** and **`strategy-selector.md`** so the top-level sections are exactly
  **Cash Deals / Seller Finance / Mortgage Takeover (Sub-To, Hybrid)** — identical names & order to triage
  and Discord. Embed the Step 1–4 determination method verbatim.
- **`comps-sop.md`:** add the equity-verify step; keep comp-per-group (SF→rent, MT→ARV+rent, Cash→ARV).
- Cross-link **`steve-ward-coaching-notes.md`** as the offer-ladder source.

## 4. Templates per group (rt-dashboard) — sourced from each Discord group's channels
Folder per group: `templates/{cash,seller-finance,mortgage-takeover}/{email,contract,terminology}`.
Each triage card links the matching `email-templates` + `contracts` by group, auto-filled with the deal
numbers + conversation reference (Steve's rule).
- **In local archive already (samples):** MFH LOI, "Dear Jean" offer letter, cash-offer email, Section-8
  email, DSCR offer, LOI-vs-offer explainer.
- **Tim to paste the canonical ones manually** (no live scraping) from each group's `email-templates` &
  `contracts` channels: SF first-contact + LOI; MT/Sub-To Trojan-Horse follow-up + trust-acquisition
  contract; Hybrid carry-back language. I slot them in by group.

---

## Confirmed decisions
- Call sheet: **20 + overflow.** Delivery: **triage fully → review.**
- Hybrid/Sub-To split = **equity-after-costs** (Step 3). Rate rule = **6% ⇒ $0 down**, cash-flow gate
  (Step 4) — Richard's rules, not a flat 5.5% cutoff.
- Taxonomy = **3 Discord groups**, Hybrid+Sub-To nested under Mortgage Takeover.
