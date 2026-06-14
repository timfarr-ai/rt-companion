# Seller Finance — Canonical SOP

> Single source of truth for Seller Finance. Replaces `tier-a-mfh-seller-finance.md` +
> `tier-b-cheap-sfh-stale.md` + `40-percent-rent-rule.md`. Provenance: `assets/CAPTURED_SOURCES.md` #4.
> One of 5 strategies. **Equity spectrum: Seller Finance = HIGH equity / free & clear → Hybrid = medium →
> Sub-To = low.**

**What it is:** seller owns **free & clear (NO mortgage)** → the seller becomes the bank and carries the
whole note. Two entry profiles: **Checkmate** (MFH / non-retail) and **Stale-SFH** (cheap, long DOM).

---

## 1. CRITERIA
- **Determination:** `loan_balance ≈ 0` (free & clear). Find via **Propwire (free) → Free & Clear** or
  **PropStream → Mortgage Info → Free & Clear**. BBC `sellerFinance` tag.
- **Checkmate (MFH SF):** 5+ units, or 2-4plex **not retail-desirable** (owner-occupant can't FHA it);
  **$200K–$1.4M**; DOM 90+. *Why it closes:* FHA fails (5+) → DSCR fails at 7%+ → SF is the only exit.
- **Stale-SFH:** SFH, **< ~$500K** (NOT $150K), DOM 90+ (150+ ideal). Sub-$140K → interest variant.
- **Sourcing theory:** tenant-occupied, listed **>$300K**, where **mortgage payment > rent** → un-sellable
  to investor (DSCR fails) / cash (poor ROI) / retail (tenant in place) → SF is the only path. Small MFH
  **>$1M, 4-12 units, free & clear** = capital-gains-motivated sweet spot.
- **Triage rank:** Checkmate by buyer CoC (CALL FIRST ≥ threshold); Stale-SFH by creative CF / DOM.

## 2. COMPS
- **Load-bearing = RENT** (SF deals live/die on rent). Haircut **asking rent → real average** (SF Course
  L604-606: *"asking 1,700… getting maybe 1,400"*). Zillow Zestimate vs BBC pill, lower wins if >20% gap.
- Gut check: `CF = rent×0.80 − PITI`. If negative/thin, the listing rent was carrying a bad deal — re-tier.

## 3. MATH / OFFER  *(canonical — CHECK MATE PITCH)*
```
offer        = asking + 15%        (default; flexes higher, balloon stretches to 96mo on big premiums)
down         = 10% of offer        (5-10% range; "+ agent commission" paid from the down)
monthly to seller = 40% of rent    ← THE offer (mental-math anchor the seller understands)
balloon      = 72 months (6 years)
balloon payout = offer − down − (monthly × 72)
```
- **40%-of-rent IS the seller's monthly payment** (the offer), not a "verbal anchor." Underwriting check
  is separate: end-buyer `CF = rent×0.80 − PITI`, buyer cash-CoC = `(rent×0.8 − PITI)×12 / price`.
- **Never give BOTH inflated price AND interest** — pick one. 3rd lever if seller wants a rate: extend
  amortization 35-40yr so the payment "disappears to interest."
- **Sub-$140K interest variant:** ≈$5K over asking · 6.5% interest · ~$15K down · 5yr balloon · deed of trust.
- **Reconciled CoC/entry** (Offer Oven sheet): `entry = down + 2%×offer + $5K assignment`; `CoC = CF×12/entry`.
- Terms: EMD **$1-1.5K or 1%** post-inspection · **5-day inspection** · **COE 30 days** · closing attorney
  "TBD at escrow" · sign **own LLC, NEVER Grandin Taylor**.

## 4. SCRIPT
- **Open conversational, NOT DSCR-first:** *"What can you tell me about this?"* → listen → drop the formula.
  DSCR-wall is the Checkmate *explanation* you reach for when asked "why propose this?" — not the lead.
- **One-liner:** *"[asking +15%], 10% down, 40% of whatever it rents for, 6-year balloon."*
- **"Impossible deal" frame (CHECK MATE PITCH):** can't get a loan (DSCR fails), can't cash (poor ROI),
  can't lowball (renovated), can't get a low rate → "so how does this sell? My solution: over asking on a
  short set of payments."
- **Objections:** cash-only → "how vs what they get paid"; other offers → "are they clearing DSCR at
  7.25%?"; 0% too low → "premium IS the interest, effective 8-9%"; default → deed reverts, mutual skin.
- **Verbal yes** = *"let me run it by my seller"* + agent forwards contract + follow-up booked.

## 5. EMAIL TEMPLATES
- "A Slide Show Full of Seller Finance Email Templates" (Drive `1 - Seller Finance/`; orig
  `1GUfmZsoW7Myi…`). Verbatim "SF + Cash" template: Offer Price · Down + commission · Monthly · 6yr
  balloon · Payout at balloon · EMD $1K post-contractor-walk · 5-day inspection. Realtor-army recruitment
  emails (get agents to submit offers for you).
- *(Offer Oven "commit → template" fills the numbers; email only, not the contract.)*

## 6. CONTRACT
- The editable **"Mortgage Takeover OR Seller Finance" .docx** (Drive `1 - Seller Finance/`) — one doc
  serves SF + MT. Plus the **how-to-fill video** ("Creative Contract in an Emergency"). Section 1.7 closing
  attorney = "TBD at escrow." *(Contract .docx body not yet read clause-by-clause.)*

## 7. TERMINOLOGY
Seller finance (owner = the bank) · free & clear · creative finance (umbrella: SF + Sub-To + Hybrid) ·
balloon · monthly payment (P&I only, not PITI) · high equity · cash flow (`rent×0.80 − PITI`) · entry fee
(down + closing + TC fee + assignment) · assignment fee · land contract / contract-for-deed · lease option.

---
## Sources
SF Course transcript L135-148, L580-668, L958-982 · CHECK MATE PITCH doc · "Seller Finance Discord
Content" (FAQ + pitch process + terminology) · SF email deck · `comps-sop.md` · Steve Ward §1-2 ·
`TRIAGE_OFFEROVEN_RECONCILIATION.md` · `STRATEGY_BEDDOWN_SELLER_FINANCE.md` (full spec).
