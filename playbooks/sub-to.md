# Sub-To (Mortgage Takeover) — Canonical SOP

> Executable SOP — the **3 P's: Process · Policy · Props** + the **Submission/Dispo** steps. Everything
> you need to run a Sub-To from lead to paid is here. Source ledger: `assets/CAPTURED_SOURCES.md`;
> 60+ verbatim templates: `assets/sources/subto-email-templates-and-scripts.md`.
>
> **What it is:** seller has an existing mortgage + **little/no equity**. You take over the existing loan
> (keep paying it), give the seller a small lump (often $0), and the mortgage stays in their name inside a
> trust. NOT Seller Finance — no +15% / 40%-of-rent here.

---

## ① PROCESS  (workflow)

```
 1.FIND ─▶ 2.VERIFY ─▶ 3.COMP ─▶ 4.CALL ─▶ 5.OFFER ─▶ 6.PAPER ─▶ 7.SUBMIT ─▶ 8.TRACK
  BBC ≤20%   PropStream   ARV +     Trojan     Trojan-      Trust       BBC Pipeline   Airtable
  equity,    rate / loan  existing  Horse →     Horse cash   Acquisition + Grand In     Deal Flow
  rank by    type (no     PITI →    pivot to    (bal+4%) OR  contract    Taylor JV      status
  low eq +   HELOC/        decide   the trust   $0-12K lump  (+ trust    (50/50)        → close
  low rate   reverse)      EXIT     pitch       to seller    attorney)
                           (inv vs
                           retail)
                                   └── if cash offer rejected on equity → pivot (that's the Trojan Horse)
```

**Exit fork (set at step 3, drives steps 4-7):** cash-flows at the existing payment (`rent×0.80 − PITI > 0`,
usually cheap <~$130K) → **investor** buyer. Doesn't cash-flow (expensive + 6-7%) → **$0-down, live-in /
retail buyer** (Richard MT L1067-1080). Either way it's a real deal — never drop on cash flow.

---

## ② POLICY  (the rules)

**Determination (who qualifies):** existing mortgage + **equity-after-costs `price − loan − 6% ≤ ~$15K`**
(cornered seller). *MT course L561-562: "less than 15K in equity."*
**Search net (the funnel):** On-market/Active · **Estimated Equity ≤ 20%** (ideal **5-10%**) · any rate ·
SFH + **condo** + **MFH** (MFH uncapped — the $500K cap is SF-only) · **avoid HELOC / reverse mortgage**.
**Sort = lowest equity (motivation) → lowest rate (CoC). Rate & cash flow are SORTS, never gates.**
**Down rule:** 6%+ rate ⇒ **$0 down**; ≤$150K ⇒ $5-12K lump; pricier ⇒ ~5%.
**Sub-To vs Hybrid:** ≤$15K net ⇒ Sub-To (here); real equity + rate ≤6% ⇒ Hybrid; real equity + 7%+ ⇒ no structure.
**Guardrails:** confirm rate/balance/loan-type before contract (mortgage statement) · land trust to beat
due-on-sale · deed-back clause if 2 payments missed · sign as **your own LLC, NEVER Grand In Taylor**.

---

## ③ PROPS + STEPS  (do this, with this)

**Step 1 — FIND.** Pull low-equity leads; rank lowest-equity-first.
▸ **Props:** [Today's Call Sheet](/rt-companion/briefings/latest.html) (Sub-To section, pre-ranked) · [BBC Lightning Leads](https://www.buyboxcartel.com/vip/lightning-leads) · PropStream filter: On-market, Estimated Equity ≤20%, Interest ≤5%.

**Step 2 — VERIFY (before you call).** BBC gives rate/balance/equity%; confirm loan **type** (no HELOC/reverse) + 2nd liens.
▸ **Props:** PropStream (manual — no API) · [Propwire](https://propwire.com/search) (free, partial) · the card's "verify rate/balance/loan-type in PropStream" pill.

**Step 3 — COMP.** Load-bearing = **ARV** (confirm equity is thin) + **existing PITI**. Decide the **exit** (investor vs retail).
▸ **Props:** Zillow SOLD comps (card "Sold comps ↗") · [Comps & Pricing SOP](/rt-companion/playbooks/comps-and-pricing.html) · the card's exit-channel tag.

**Step 4 — CALL.** Homeowner-direct, or the **Trojan Horse** via the agent.
- **Broach the loan (verbatim):** *"If you've got a mortgage, I'd be happy to take over your payments — a third-party servicing company pays it so you don't worry. If a payment's ever missed, the property returns to your name and you keep everything paid so far. Since I'd run it as a rental, I need the rate/terms to make sure it cash-flows — can you confirm them so my offer is valid?"*
- **Trojan Horse:** make a cash offer that nets the seller **~$0** (`balance + 4% of asking`), *intending it to be rejected* → the agent reveals the equity → you act surprised and **pivot** to the takeover/trust pitch. Best on 5-10% equity.
- **Objections (cheat-sheet):** *"Subto is illegal"* → **HUD-1 line 203** ("existing loan(s) taken subject to") + Modern Real Estate Practice Unit 12. *"Due-on-sale"* → land trust; banks don't call performing loans. *"What if you stop paying?"* → property reverts after 2 missed payments, seller keeps everything paid. *"Can my seller get a new loan after?"* → yes — trust certificate + occupancy agreement (VA-loan angle); partner originator **Andrew**.
▸ **Props:** full 60+ scripts/objections → [`assets/sources/subto-email-templates-and-scripts.md`](https://github.com/timfarr-ai/rt-companion/blob/main/assets/sources/subto-email-templates-and-scripts.md) · OpenPhone click-to-call (card).

**Step 5 — OFFER.** Cash-to-seller lump (rate/price-scaled), assume the loan; run the numbers + suitability check.
▸ **Props:** [Offer Oven Calculator (Subto mode)](/rt-companion/playbooks/offer-oven-calculator.html?otype=Subto) — the card auto-fills it per deal (price/balance/rate/rent); it returns the **PROCEED / COUNTER / KILL** suitability verdict (the Closer-eval criteria).

**Step 6 — EMAIL the offer.** Send after the call, referencing the conversation. Verbatim TRUST email pattern:
```
Good Evening [Name], thank you for your time today. My lender won't budge much on $[X]; your seller would
still lose $5-10k on a sale. I could just take over their debt instead and let them qualify for a new loan:
I'd take over whatever's owed on the mortgage, pay you $[8,500] and your seller $[7,000] cash, and cover all
closing costs. The loan isn't assumable, but here's the loophole — your client puts the property into a trust
created by an attorney and sells me the trust. This completely resets their DTI and is a legal sale. Can we
present this so they walk with $[7k]? My portfolio + proof of funds are in your texts. Regards, [You]
```
▸ **Props:** [Sub-To email deck (60+)](https://docs.google.com/presentation/d/1faQLOfVvmOvZ5Yl4K9k6_wUvGCfbTwyMs2J6x7Mr7Kw/edit) · the card's "Copy values" + email autofill.

**Step 7 — PAPER (contract).** **Trust Acquisition:** house → revocable living trust (trust attorney); deed in, mortgage stays in seller's name; buyer assigned **90-95% beneficial interest**, seller keeps **5-10%**; buyer/trust pays the mortgage. + **Assignment Disclosure Addendum** for the wholesale assignment.
▸ **Props:** editable [Mortgage-Takeover / Seller-Finance contract (.docx)](https://docs.google.com/document/d/19sgM1zTQSvDYbiCvEYjYsBUfb1bouPZA/edit) · Assignment Disclosure Addendum (Drive) · Gold Key TC for transaction coordination.

**Step 8 — SUBMIT / DISPO.** Get it under contract, then disposition:
- **Save to BBC Pipeline** — the card's 🔑 button (HMAC-signed → BBC pipeline/add). Or [Create Offer in BBC](https://www.buyboxcartel.com/vip/lightning-leads).
- **Submit to Grand In Taylor (JV)** — Richard's company places it with their buyer network, **50/50 split**: [Creative JV webform](https://grandintaylorllc.salesmate.io/webforms/#/5bddb679-43e9-4a91-aca2-ddaff898ff78) (the card's 🤝 button).
- **Closer eval** — confirm the deal meets the Closer criteria first (the calculator's suitability panel; min CF, max equity 15%, balloon ≥5yr) if you want Closer help.
▸ **Props:** card buttons (Save to Pipeline · Submit to Grand In Taylor · Create Offer in BBC).

**Step 9 — TRACK.** Log to Airtable **Deal Flow** (status: Contacted → Accepted → Pushed to TC → Buyer Found → Paid). Tracked PIDs auto-drop from the next day's call sheet.
▸ **Props:** Airtable Deal Flow (card "Track" button auto-prefills the record).

---
## Sources
MT course L399-409, L561-562, L738, L793-795, L1067-1080 · Discord *Mortgage Takeover* (Trust Acquisition
doc, 60-template deck, PropStream slide) · Steve Ward §3 (loan script) · `comps-sop.md` · BBC live data ·
`triage.py` (classify, submission wiring). See also [Hybrid](/rt-companion/playbooks/hybrid.html) (medium equity).
