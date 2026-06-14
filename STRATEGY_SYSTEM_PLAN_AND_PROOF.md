# RT Deal Desk — System Plan & Proof (5-Strategy Spine)

**Mandate (Tim, 2026-06-11):** every layer — triage, SOP, assets — is organised around **five
standalone strategies** (duplication across assets accepted). Each component of each strategy must
trace to **defensible proof** (a document, a transcript line, or a recording). Then the built-in
Offer Oven must (1) reach field+function parity with the spreadsheet, (2) add the spreadsheet's
suitability validation, (3) commit calcs into the correct offer template, (4) recall saved figures.
This doc is **plan + proof only — no implementation until approved.**

## The five strategies (canonical spine)
1. **Seller Finance** — free & clear; seller carries the whole note *(profiles: Checkmate MFH · Stale-SFH)*
2. **Sub-To** — existing loan, cornered seller (≤$15K equity-after-costs), small lump
3. **Hybrid** — existing loan + real equity + assumable rate; assume loan **and** carry equity as a note
4. **Fix & Flip** — cash, distressed, win on the buy (70%-ARV ceiling − rehab)
5. **Cash Arbitrage** — already cash-flows; wholesale at a cash discount

---

# PART 1 — THE PROOF MATRIX

Verdict key: **🟢 STRONG** (primary source w/ line refs or recordings) · **🟡 PARTIAL** (some
evidence, incomplete) · **🔴 GAP** (no defensible source document in our possession).

| Strategy | Criteria | Comps | Script | Email | Contract | Terminology |
|---|---|---|---|---|---|---|
| **Seller Finance** | 🟢 | 🟢 | 🟢 | 🟡 | 🔴 | 🟡 |
| **Sub-To** | 🟢 | 🟢 | 🟢 | 🟡 | 🔴 | 🟡 |
| **Hybrid** | 🟢 | 🟢 | 🟢 | 🟡 | 🔴 | 🟡 |
| **Fix & Flip** | 🟢 | 🟢 | 🟢 | 🟡 | 🔴 | 🟡 |
| **Cash Arbitrage** | 🟢 | 🟢 | 🟡 | 🔴 | 🔴 | 🟡 |

### CRITERIA — 🟢 STRONG (every routing rule traces to a transcript line, now validated)
- **Seller Finance:** SF Course **L135–148** (down-scaling), **L604–606** (rent "asking ≠ getting"),
  **L958–982** (2-4plex Checkmate only if NOT retail-desirable). `deal-criteria.md`, `deal-types.md`.
- **Sub-To:** MT Course **L561–562** *"less than 15K in equity"* ⇒ **validates the $15K cornered cutoff
  verbatim**; **L793–795** *"6% interest rate, you can do $0 [down]"* ⇒ validates 6%⇒$0-down;
  **L27/85/107/738** ($10–12K lump); **L399–409** (must cash-flow at existing payment).
- **Hybrid:** MT Course (equity + assumable rate); `hybrid-mt-sf-carryback.md`; Steve Ward §1 (assume
  loan + seller carries equity gap).
- **Fix & Flip:** Cash Course **L700–900** (70% rule), `fix-and-flip-cash.md`; `c2hNH6u7D0k @ 1:12:32`
  (70% is the *ceiling* — Richard offered $72K where the rule allowed $95K).
- **Cash Arb:** Cash Course (cash-comparable), `deal-criteria.md` Tier C.
- **As-built:** `triage.py › classify_strategy()` — Step 1-4, all thresholds source-backed.

### COMPS — 🟢 STRONG (`comps-sop.md`, every rule cited to a transcript)
- **SF / Sub-To / Hybrid (rent leg):** rent ritual, haircut asking → real average — SF Course **L604–618**.
- **Fix & Flip / Cash / Sub-To / Hybrid (ARV leg):** sold-comp ritual — Cash Course **L716–895**
  (*"sales mean it's worth that price… click sold"*); grades 60/70/90% of value.
- Load-bearing rule: **SF lives/dies on RENT; Cash/FF lives/dies on ARV.**

### SCRIPT — 🟢 STRONG (playbooks live-validated vs ~10 hrs of recordings)
- **SF:** `tier-a-mfh-seller-finance.md` + `tier-b-cheap-sfh-stale.md`; **43 SF call recordings**
  (`hmhw-call-library-seller-finance.md`); live verbatims `c2hNH6u7D0k`, `CzUeF6SASGA`, `u-ov-X0Cc68`.
- **Sub-To:** `mortgage-takeover.md` (492 lines) + MT call library; Steve §3 loan-data script.
- **Hybrid:** `hybrid-mt-sf-carryback.md` + 3 hybrid recordings (Pitch 1 $1.85M, Pitch 2, SF→Hybrid).
- **Fix & Flip:** `fix-and-flip-cash.md` + cash recordings; finality verbatim `c2hNH6u7D0k @ 0:21:13`.
- **Cash Arb:** 🟡 shares the F&F cash script + Section-8 angle; no dedicated cash-arb recording set.
- All in `outreach-scripts.md` (voicemails, objections, counters) — but still in OLD Tier A/B/C framing.

### EMAIL — 🟡 PARTIAL (no formal per-strategy templates exist as documents)
- **What we have:** Steve Ward §6 email *skeleton* (reference-the-call + offer LOI); `outreach-scripts.md`
  §"CONTRACT CUSTOMIZATION" and objection-reply fragments.
- **What's missing:** no per-strategy **first-contact email**, **follow-up email**, or **LOI cover**
  as committed template documents. The realignment plan assumed these come from Discord
  `email-templates` channels — **those channels do not exist in the archive** (see Part 2).

### CONTRACT — 🔴 GAP (no contract documents anywhere)
- **Searched:** rt-companion, the skill, and the 63,235-message Discord archive. Found **zero** contract /
  LOI / purchase-agreement / trust-acquisition documents. `strategy/contract-close.html` is a *playbook
  page about closing*, not a contract. Discord "contract" hits are conversational; the only contract
  *service* is **Gold Key TC** (a paid transaction-coordinator ad in `🔑gold-key-tc-service`).
- **Implication:** we cannot defensibly attach a contract to any strategy today. Must be obtained
  (HMHW course platform · Gold Key TC · Richard/Steve · BBC-generated offer docs).

### TERMINOLOGY — 🟡 PARTIAL
- **What we have:** `hmhw-quiz-{seller-finance,mortgage-takeover,cash}.md`, `deal-types.md`, course
  transcripts (definitions in context).
- **What's missing:** no consolidated per-strategy glossary (due-on-sale, land trust, DSCR, balloon,
  assignment, wrap, etc.) as a single defensible reference.

---

# PART 2 — THE HONEST GAPS (what proof we do NOT have)

1. **Contracts — 🔴 hard gap.** No documents. The realignment plan's premise ("each Discord group has
   `email-templates` + `contracts` channels") is **false for this archive** — the archived channels are
   Deal Check, negotiation-assistance, gold-key-tc-service, Casual, etc. *No per-strategy template/contract
   channels were ever exported (or exist).* **Action needed: you source the canonical contracts** (Gold
   Key TC / HMHW platform / Richard) and I scaffold them in.
2. **Emails — 🟡 partial gap.** Only a skeleton + fragments. Same root cause (no Discord template channels).
3. **Cash-Arb script — 🟡.** Rides on the F&F cash script; no dedicated recordings/playbook.
4. **Terminology — 🟡.** Scattered; no consolidated glossary.
5. **`deal-criteria.md` / `outreach-scripts.md` — stale.** Still Tier A/B/C, $350K floor, old
   `Down+$3,000+$5,000` entry formula. Must be re-spun to the 5 strategies + reconciled math.

> Bottom line: **criteria, comps, and scripts are defensibly sourced and validated. Emails and
> contracts are not — and no local source exists for them.** That gap is the realignment plan's blind
> spot, surfaced.

---

# PART 3 — OFFER OVEN: PARITY GAP ANALYSIS (built calculator vs the spreadsheet)

Source of truth = Richard's *Creative Offer Oven* Google Sheet
(`docs.google.com/.../1Se8bNXjryiWgFWAridq_b9uxAzZai7vJS7GFThbANGk`). Built calc =
`playbooks/offer-oven-calculator.html`. Canonical formulas reverse-engineered in
`scripts/TRIAGE_OFFEROVEN_RECONCILIATION.md`.

### Confirmed divergences (calc ≠ sheet)
| # | Calc behaviour | Sheet (truth) | Status |
|---|---|---|---|
| **B** | Entry fee = down + rehab + **`assign×0.6`** + closing (`offer-oven-calculator.html:194`) | Entry uses the **FULL** assignment | 🔴 known bug, deferred |
| **Appr** | `apprVal` year-handling bug (L207-209); uses `list` not `price` | sheet K17/K18 | 🟡 minor |
| **Validation** | only colour-codes CF/CoC; **no PASS/COUNTER/KILL verdict** | sheet has a **suitability check** | 🔴 missing feature |
| **Commit** | none — figures are ephemeral | (sheet is the doc) | 🔴 missing feature |
| **Recall** | none — URL-params in, nothing persisted out | n/a | 🔴 missing feature |

### Parity I can't fully verify without the live sheet
The calc carries 21 inputs (price, list, otype, down, rate, amort, io, balloon, rehab, assign, subbal,
subpay, rent, ins, tax, hoa, other, capex, mgmt, vac, appr) + a FF tab. **A true field-by-field /
function-by-function audit requires reading the actual sheet** (its tab list, every input cell, every
formula, the validation rules). **Proposed method:** open the authenticated sheet via the Chrome
DevTools MCP (Tim is logged in) and dump each tab's cells/formulas — OR Tim does *File → Download →
.xlsx* and I diff it. Until then, "no parity" is asserted but not itemised.

---

# PART 4 — OFFER OVEN: THE FOUR FEATURES (design)

**① Field + function parity.** Fix B (`×0.6` → full assignment) + the appreciation bug immediately.
Then run the sheet audit (Part 3 method) and add any missing input cells / output formulas / tabs so the
calc is a 1:1 mirror. Keep the cell-ref comments so it stays maintainable when Richard iterates the sheet.

**② Suitability validation (the sheet's go/no-go).** Add a **verdict panel**: `PROCEED / COUNTER / KILL`
computed from per-strategy thresholds (mirroring the sheet's conditional formatting + `deal-criteria.md`:
CF > $200/mo, CoC ≥ 10% (≥20% strong), entry ≤ 15% of price, balloon ≥ 5yr, MT must cash-flow at the
existing payment, F&F needs a real ARV spread). *Requires confirming the sheet's exact validation rules
during the Part-3 audit.*

**③ Commit calc → populate the correct EMAIL/OFFER template.** A **"Commit offer"** action that freezes
the figures and merges the **numbers into the strategy-correct email/offer template** (the deal-terms
email Tim sends the realtor). **Clarified by Tim 2026-06-12: this populates the email/offer template
ONLY — NOT the legal contract.** The contract is a separate artifact, filled on its own. → therefore
this feature is **gated on the email/offer templates (which we now HAVE** — 60+ Sub-To/MT/Hybrid templates +
the SF email deck**), not on contracts.** Picks the right template by `strategy_subtype`, fills offer
price / down / monthly (40%×rent for SF) / balloon / EMD / COE. Also writes to the Airtable Deal-Flow
record + BBC pipeline payload (already wired in `triage.py`).

**④ Recall saved figures.** Persist each committed calc keyed by property `pid` (Airtable Deal-Flow
record is the natural store — already the pipeline-of-record), with a recall UI on the calculator
("Load saved deal") and a deep-link from the card. Lets Tim re-open the exact numbers he committed.

---

# PART 5 — IMPLEMENTATION PLAN (phased, after approval)

**Phase A — Re-spine triage output on 5 strategies.** `classify_strategy()` already emits the 5
subtypes; change the *display* from 3 group wrappers to **5 flat strategy sections** + keep the Top-20
call sheet. (Reverses the 3-group output built earlier today.)

**Phase B — Re-spine the SOP/assets on 5 strategies (duplication OK).** Rewrite `deal-criteria.md`,
`strategy-selector.md`, `comps-sop.md`, and the playbooks so each strategy is self-contained:
*criteria · comps · script · email · contract · terminology*, each with its proof citations inline.
Reconcile the stale math ($200K floor, 2% closing entry).

**Phase C — Offer Oven parity + validation** (features ① ②): bug-fixes now; full audit + suitability
once the sheet is dumped.

**Phase D — Templates + commit/recall** (features ③ ④): **blocked on Part-2 gap** — needs you to supply
canonical emails + contracts. Then scaffold `assets/<strategy>/{email,contract,terminology}`, wire commit
→ template, persist + recall via Airtable Deal-Flow.

---

# PART 6 — WHAT I NEED FROM YOU TO CLOSE THE GAPS
1. **Contracts** (🔴): the canonical SF LOI, Sub-To/Trust-Acquisition, Hybrid carry-back, and cash-offer
   docs — from Gold Key TC, the HMHW platform, or Richard. *Nothing defensible exists locally.*
2. **Emails** (🟡): the real first-contact + follow-up + LOI-cover templates (or confirm we author them
   from Steve's skeleton and tag them "house-built, not HMHW-canonical").
3. **The Offer Oven sheet** (for parity ①/validation ②): either let me open it via the authenticated
   browser, or drop an `.xlsx` export in the repo.

---

## Sources used (this document)
- **Transcripts (validated this session):** SF Course L135-148, L604-606, L958-982 · MT Course L399-409,
  L561-562, L738, L793-795 · Cash Course L700-900 (via `comps-sop.md`/`fix-and-flip-cash.md` citations).
- **Playbooks:** `tier-a-mfh-seller-finance.md`, `tier-b-cheap-sfh-stale.md`, `mortgage-takeover.md`,
  `hybrid-mt-sf-carryback.md`, `fix-and-flip-cash.md`, `40-percent-rent-rule.md`.
- **References:** `deal-criteria.md`, `comps-sop.md`, `steve-ward-coaching-notes.md`,
  `outreach-scripts.md`, `hmhw-call-library-seller-finance.md`, `deal-types.md`, the quizzes.
- **Offer Oven:** `playbooks/offer-oven-calculator.html`, `scripts/TRIAGE_OFFEROVEN_RECONCILIATION.md`.
- **Discord archive:** `hmhw_discord.db` (63,235 msgs, 21 channels — no template/contract channels).
- **Code as-built:** `scripts/triage.py` (`classify_strategy`, `score/_sf_cf`, calc auto-fill, pipeline payload).
- **Companion docs:** `STRATEGY_BEDDOWN_SELLER_FINANCE.md`, `STRATEGY_REALIGNMENT_PLAN.md`.
