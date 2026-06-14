# Hybrid — Canonical SOP

> Single source of truth for Hybrid. Replaces `hybrid-mt-sf-carryback.md` (which wrongly used the SF
> 40%-of-rent method — **do NOT use that**). Provenance: `assets/CAPTURED_SOURCES.md` #2, #5.
> One of 5 strategies.

**What it is:** the **MEDIUM-equity** middle of the spectrum — **Seller Finance (high equity / no debt)
fused with Mortgage Takeover (low equity)**. Seller has an existing loan **AND** meaningful equity, so
neither pure play fits: pure Sub-To undersells (they want their equity, not a $10K walk); pure SF ignores
the cheap existing loan. **Hybrid = assume the existing loan + carry the seller's equity as a note.**
*(There is no standalone Hybrid course — it's defined by the medium-equity position. Steve Ward §1.)*

---

## 1. CRITERIA
- **Determination:** existing loan present + **medium equity** (real equity, not cornered) + **rate
  assumable (≤ ~6%)**. By equity-after-costs: `seller_net = price − loan − 6%` is meaningfully **> ~$15K**
  (above the Sub-To cornered line) but there's still a loan worth assuming.
- **Real equity + 7%+ rate ⇒ no Hybrid** (seller can sell conventionally; a 7%+ loan isn't worth assuming).
- Property types: SFH · condo · MFH (MFH uncapped). Confirm the existing rate **first** — if 7%+, pivot.
- **Triage:** ranks within the Mortgage Takeover group (lowest equity → lowest rate), tagged Hybrid.

## 2. COMPS
- **Load-bearing = ARV** (to confirm the equity is real) **+ rent** (for the cash-flow headroom on the
  carry-back). Pull SOLD comps (see `comps-sop.md`). Get the mortgage statement to confirm the balance.

## 3. MATH / OFFER  *(canonical — "Hybrid Multi Family Email Template")*
**Three parts. NOT +15%/40%-of-rent. The carry-back is on the EQUITY, the monthly is NEGOTIATED.**
```
Buy price ≈ at/near asking      (e.g. $250,000)
 ├─ Cash / down at close        (e.g. $30,000 — negotiable; Sub-To-style $5-10K also common)
 ├─ Assume the existing loan     (e.g. $144,000 — you pay the bank its PITI; 4+ legal ways to take it over)
 └─ Carry back the EQUITY note:  carry-back = price − down − loan balance   (e.g. $76,000)
        monthly to seller = NEGOTIATED (e.g. $400/mo) — keep ≤ cash-flow headroom (rent×0.80 − existing PITI)
        balloon (5yr typical) payout = carry-back − (monthly × months)      (e.g. $52,000)
```
- **Flexibility is the edge:** seller wants more cash now? Bump the down, trim the balloon — same total.
- Seasonal/negotiated monthlies are fine (canonical $3.8M example: $4K/mo slow season, $15K/mo peak).

## 4. SCRIPT
- **Lead creative, never say "hybrid" or "subject-to" out loud** — say *"take over the loan + carry your
  equity."* Open: *"I noticed your seller probably has an existing loan they're paying down — are they
  sitting on a low rate from a few years back?"* Confirm rate + balance first.
- **Pitch:** *"$[cash] to your seller at close. I take over the existing loan and keep paying it — they're
  off the mortgage. The remaining equity, about $[carry-back], I carry back at $[monthly]/mo for [N]
  years, balloon at year [N]. They get the full asking, just spread out — no realtor cut, no capital-gains
  hit all at once."*
- **Objections:** due-on-sale → land trust, banks don't call performing loans; "why not cash?" → compare:
  cash nets them `equity − 6% realtor`, Hybrid gives cash now + monthly + balloon = full asking; default →
  property reverts, seller keeps all payments; "too complicated" → "three numbers: cash now, monthly,
  balloon — like a rental they don't manage; I'll put it in writing for their attorney."
- **Verbal yes** = *"the structure makes sense, let me run it by my seller"* → text the proposal within 60s.

## 5. EMAIL TEMPLATES
- In the Sub-To deck (`assets/sources/subto-email-templates-and-scripts.md`): **"Hybrid Multi Family
  Email Template"**, "Subto Hybrid Email Template" (rare deals), "Multi Family Subject to Hybrid Email."
  Canonical pattern = state what's owed → what they net at asking after commission → the 3-part
  alternative (buy price / down / term / payout / monthly) with the breakdown.

## 6. CONTRACT
- Same **"Mortgage Takeover OR Seller Finance" .docx** as Sub-To/SF + **Trust Acquisition** (revocable
  living trust; buyer 90-95% / seller 5-10% beneficial interest; mortgage stays in seller's name; HUD-1
  line 203) for the takeover portion, with the carry-back note documenting the equity. Land trust beats
  due-on-sale.

## 7. TERMINOLOGY
Hybrid (assume + carry) · seller carry-back / carry-back note · beneficial interest · trust acquisition ·
due-on-sale · cash-flow headroom · balloon · medium equity.

---
## Sources
"Hybrid Multi Family Email Template" + deck L186 ($3.8M 3-part example) · MT course · Steve Ward §1 (the
equity spectrum) · `assets/CAPTURED_SOURCES.md` #2/#5 · `triage.py` Hybrid banner (canonical, post-fix).
