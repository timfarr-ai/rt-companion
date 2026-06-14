# Triage Card ⇄ Offer Oven Reconciliation

**Subject:** 19196 McCormick St, Detroit, MI 48224 (Tier B)
**Date:** 2026-06-10
**Source of truth:** Richard's *Creative Offer Oven* Google Sheet
(`docs.google.com/spreadsheets/d/1Se8bNXjryiWgFWAridq_b9uxAzZai7vJS7GFThbANGk`)

The Offer Oven calculator (`playbooks/offer-oven-calculator.html`) is a JS mirror of
that sheet. The sheet — not the calculator, not the triage card — is canonical.

---

## Formula validation (source of truth)

Reverse-engineered the sheet's formulas from its shipped default example and confirmed
an **exact** match against the sheet's own published outputs:

| Sheet default ($120k / $6,500 down / $1,600 rent) | Sheet value | Reproduced |
|---|---|---|
| Buyer Entry Fee | $9,900 | $9,900 ✅ |
| Monthly Cash Flow | $765 | $765 ✅ |
| Cash-on-Cash | 92.69% | 92.69% ✅ |
| Balloon balance @7yr | $87,016.67 | $87,017 ✅ |

**Canonical formulas:**
- `Loan = Purchase Price − Down`
- `Monthly P&I = Loan / (amort×12)` (0% ⇒ pure principal)
- `Closing = 2% × Purchase Price`
- `Buyer Entry Fee = Down + Rehab + Assignment(FULL) + Closing`
- `Operating Expenses = P&I + Ins + Tax + HOA + Other + CapEx(10% rent) + Mgmt(10% rent) + Vacancy + Subto loans`
- `Cash Flow = (Rent×12) − Operating Expenses`
- `CoC = Annual Cash Flow / Buyer Entry Fee`
- `Balloon balance = Loan − P&I × (balloon_yrs×12)` — uses the **amortized P&I**, no 40%-of-rent
- The sheet contains **no 40%-of-rent rule** anywhere.

---

## McCormick — canonical vs the surfaces

Inputs: $90,000 offer · $10,800 down (12%) · 0% · 30yr · 7yr balloon · rent $1,348 ·
tax $129 · ins $26 · $5,000 assignment · no rehab.

| Metric | **Sheet (truth)** | Triage card | Calc *via auto-fill link* | Calc *w/ correct inputs* |
|---|---|---|---|---|
| Monthly CF | **$703** | $702 ✅ | $658 ❌ | $703 ✅ |
| Entry fee | **$17,600** | $17,000 ❌ | $13,600 ❌ | $15,600 ❌ |
| Cash-on-Cash | **48.0%** | 22.3% ❌ | 58.1% ❌ | 54.1% ❌ |
| Balloon @7yr | **$60,720** | $33,924 ❌ | $60,720 ✅ | $60,720 ✅ |
| Closing | **2% = $1,800** | 1% = $900 ❌ | 2% ✅ | 2% ✅ |

Only **cash flow** ($702 ≈ $703) matches end-to-end. **No surface reproduces the sheet's
CoC of 48.0%** — not even the calculator.

---

## Root causes (ranked, each a real fix)

**A. Card CoC & Entry use BBC blanket data, not the creative structure** —
`scripts/triage.py:554-559`. `coc`/`entry` are built from BBC's `monthlyCashFlow`
(~$316/mo) and `downPayment` (~$9,000) + $3k + $5k, then displayed next to the *creative*
CF ($702). That is why 22.3% cannot be derived from the $702 / $17,000 on the same card.
Per the sheet it should be **48.0%**.

**B. The calculator diverges from the sheet** — `playbooks/offer-oven-calculator.html:194`.
It uses `entry = down + rehab + assign*0.6 + closing`, but the sheet adds the **full**
assignment fee. With a $5k assignment that under-counts entry by $2,000 ⇒ calc 54.1% vs
sheet 48.0%. (They agreed in validation only because the sheet default assignment is $0.)

**C. Auto-fill link is lossy** — built in `scripts/triage.py:~1230-1265`. Passes only
`price, list, down, rate, rent, balloon, otype`; **drops `tax`, `ins`, `assign`, `rehab`**,
so the calculator loads defaults (tax $100, ins $100, assign $0, rehab $1,000). Right
formula, wrong inputs ⇒ $658 / $13,600 / 58.1%.

**D. The "40%-of-rent" pitch block has no basis in the sheet.** Seller monthly per sheet =
amortized P&I = **$220/mo** (not $539); balloon residual = **$60,720** (not $33,924). The
40% figure is Richard's verbal sanity anchor — the calculator HTML itself labels it *"not
the core math."* The card presents it as the deal math.

**E. Closing %:** card / Airtable / "Copy values" use **1%**; the sheet uses **2%**.

**F. Three different PITIs** on one card — specline **$763** ≠ Airtable "Existing PITI"
**$606** ≠ the **~$554** used inside `bank_gap` (`scripts/triage.py:666-674`). None is the
sheet's figure.

**G. Balloon term:** the BBC "Save to Pipeline" payload hardcodes `balloon: 96` months
(**8yr**) at `scripts/triage.py:1902` while the card displays **7yr**.

---

## Fixes to make all surfaces equal the sheet ($703 / $17,600 / 48.0% / $60,720)

1. **triage.py** — recompute the card's `coc`/`entry` from creative figures:
   `entry = creative_down + creative_offer*0.02 + 5000`; `coc = creative_cf*12/entry`.
   (22.3% → 48.0%; $17,000 → $17,600.)
2. **triage.py auto-fill URL** — append per-property `&tax=&ins=&assign=5000&rehab=0`.
3. **offer-oven-calculator.html:194** — drop the `*0.6` to match the sheet's full-assignment
   entry. Align closing to 2% across card/Airtable/Copy-values (or change the sheet — pick one).
4. **Decision (not a bug):** keep the 40%-of-rent block as a clearly-labeled "verbal pitch
   anchor," or reconcile it to the sheet's $220/mo + $60,720 balloon.
