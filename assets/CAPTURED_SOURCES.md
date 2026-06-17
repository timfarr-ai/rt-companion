# Captured Sources — running ledger of critical content Tim flags

As Tim works through the HMHW education content he points out the load-bearing pieces. Each entry =
the raw content + source stamp + the build implications it carries. This is defensible-proof material.

> **PROOF-AUDIT CORRECTION (2026-06-12):** `STRATEGY_SYSTEM_PLAN_AND_PROOF.md` reported emails/contracts
> as 🔴 "no source exists" because the local `hmhw_discord.db` archive had no template channels. That
> archive is a **different/incomplete Discord server.** The real HMHW Discord **does** have per-strategy
> groups with `Email Templates` (proven: entry #1 came from *Discord › Mortgage Takeover › Email
> Templates* via a Google Doc). So the email/contract source **exists** — it just wasn't in our archive.
> Tim is pulling it into Drive; once the Google Drive MCP is authed I can read those docs directly.
> Net: emails/contracts move from "🔴 no source" to "🟡 source exists, not yet ingested."

---

## #1 — Sub-To / Mortgage Takeover · SEARCH CRITERIA (PropStream)
**Source:** HMHW course slide *"FILTERS FOR FINDING LOW EQUITY DEALS ON PROPSTREAM"* — provided by Tim 2026-06-12. **Canonical (HMHW education content).**
**Provenance chain (fully traceable):**
- Slide: `docs.google.com/presentation/d/1Y-AR_aPMbelGe-z8Toq385WEwElXM5umJ-m9eybkSbA` (slide `id.g2caf0d453bd_5_0`)
- Attached to doc: `docs.google.com/document/d/1n2OtntFqdhbtWh5KVbSjmEv4LDp4uZ7hImhFPbSurrk`
- Which was **copied from Discord › Mortgage Takeover › Email Templates**.
- ⚠ Both Google URLs are auth-walled (WebFetch 401) → readable once the Google Drive MCP is authed.
**Strategy:** Sub-To / Mortgage Takeover → CRITERIA.

**The search filter (PropStream):**
| Filter | Value |
|---|---|
| On Market | Yes |
| Listing Type | For Sale |
| MLS Status | Active |
| **Estimated Equity %** | **≤ 20%** |
| **Interest Rate % (Est.)** | **≤ 5%** |

**Slide notes (verbatim sense):**
- Higher interest rate is OK **if purchase price < $150,000**; **if < $100,000, interest hardly matters.**
- **Avoid HELOCs (lines of credit) and reverse mortgages.**
- Property types: **condos, single-family, AND multi-family all valid.**
- Good track record with **condos in Florida retirement locations.**

**Tim's design note:** the search is intentionally *broader* than ideal (ideal ≈ **5–10% equity**). In
triage, **rank the results by LOWEST equity first** — lowest equity = greatest seller motivation = the
strongest Sub-To/MT opportunity.

### Build implications (for the triage/SOP re-spine — not yet implemented)
1. **Rank Sub-To/MT by equity ascending** (lowest equity → top). Today the call-sheet "motivation" factor
   keys off DOM only; for MT/Sub-To it should also key off **low equity %**. Surface **equity %** on the
   card so the operator sees the motivation signal. *(This is Tim's explicit refinement — validated.)*
2. **Condos must be ALLOWED for Sub-To/MT.** ⚠ Conflict: `triage.py` `NON_RESIDENTIAL_TYPES` currently
   filters condos out (they fail the SF Checkmate retail-buyer logic). For mortgageTakeover, condos are a
   valid target (esp. FL retirement). → needs a **carve-out: don't drop condos when deal_type = mortgageTakeover.**
3. **Rate tolerance scales with price** — <$150K tolerates higher rate; <$100K rate is irrelevant. This
   *matches* the existing `classify_strategy` rate-scaling logic (6%⇒$0-down; cheap cash-flows regardless).
   The ≤5% search ceiling is the *net*, not the gate — keep the price-aware rate logic.
4. **Equity band:** broad search ≤20%; **ideal 5–10%.** Could tier the card: ≤10% = prime, 10–20% = watch.
5. **Disqualifiers to flag:** HELOC / reverse mortgage. BBC may not expose loan *type* → if unavailable,
   add a "verify no HELOC/reverse mortgage" pill on MT cards rather than auto-excluding.

**Cross-check to as-built:** `classify_strategy` Sub-To cornered test = `seller_net = price − loan − 6% ≤
$15K` (dollar-based). This slide frames motivation as **equity %**. Consider surfacing/ranking on equity %
to match Richard's own framing, while keeping the dollar test for the cornered/Hybrid split.

---

## #2 — Sub-To / Mortgage Takeover · COURSE REFERENCE DOC (Trust Acquisition, Trojan Horse, FAQ)
**Source:** Google Doc `1n2OtntFqdhbtWh5KVbSjmEv4LDp4uZ7hImhFPbSurrk` = *Discord › Mortgage Takeover* group reference. Ingested 2026-06-12. **Canonical HMHW.** Fills Sub-To **contract + terminology + script** gaps.

- **Trust Acquisition = the Sub-To contract structure** (the contract we were missing): house → **revocable living trust** (via trust attorney); deed transfers in, **mortgage stays in seller's name**; buyer assigned **90–95% beneficial interest**, seller keeps **5–10%**; buyer/trust pays the mortgage. Lender not notified (not a "sale") → reduces due-on-sale risk. Legal basis: **HUD-1 Settlement Statement line 203** ("existing loan(s) taken subject to") + *Modern Real Estate Practice, Unit 12*.
- **Trojan Horse pitch (THE MT script + an offer formula):** for a low-equity seller, make a cash offer that nets them **$0 or less**, *intending it to be denied* → realtor reveals the equity position → you pivot to the MT/Trust pitch. **Offer formula: `cash offer = mortgage balance + 4% of asking price`** (covers closing/realtor so seller nets ~$0). Works best **close to list price**, i.e. **5–10% equity**. → BUILD: this is a concrete MT "pivot offer" number for the card/Offer Oven.
- **FAQ** (terminology proof): subject-to legality, due-on-sale avoidance via trust, missed-payment **deed-back after 2 months**, seller re-qualifying for a new loan (trust certificate + occupancy agreement; VA-loan angle), partner loan originator "Andrew" for sellers needing a new loan.

## #3 — Sub-To / Hybrid · EMAIL TEMPLATES TROVE (60+ verbatim) — **EMAIL GAP CLOSED**
**Source:** Google Slides `1Y-AR_aPMbelGe-z8Toq385WEwElXM5umJ-m9eybkSbA` (local copy; orig `1faQLOfVvmOvZ5Yl4K9k6_wUvGCfbTwyMs2J6x7Mr7Kw`) = *Discord › Mortgage Takeover › Email Templates*. **Preserved verbatim → `assets/sources/subto-email-templates-and-scripts.md`.** Ingested 2026-06-12. **Canonical HMHW.**
- ~60 verbatim Richard email/text templates: TRUST emails (many variants), Trojan-Horse email + post-call text, BASIC CASH OFFER, mortgage-takeover/buyout emails, **Hybrid Multi-Family + Subto-Hybrid** templates, "LOW EQUITY EMAIL THAT GOT ME 5 DEALS IN 1 CALL", portfolio trust email.
- **Objection scripts:** "subto is illegal" → HUD line 203 + blank HUD link; "can I qualify for a new loan?" → Fannie Mae Selling Guide + VA-loan detail; vague/attorney-review email variants.
- Also contains the #1 PropStream search-criteria slide (same deck).
→ Sub-To/MT/Hybrid **Email = 🟡→🟢**. Hybrid email templates exist here too (rare-deal note).

## #4 — Seller Finance · FULL FOLDER (criteria/script/email/contract/terminology) — **most gaps CLOSED**
**Source:** Drive `Strategy Assets / 1 - Seller Finance` (Tim's capture from *Discord › Seller Finance*). Ingested 2026-06-12. **Canonical HMHW.** Files: "Seller Finance Discord Content" (Doc), "CHECK MATE PITCH" (Doc), "A Slide Show Full of SF Email Templates" (Slides), **"SAMPLE…Seller Finance Purchase and Sale Contract.docx"** (the contract), 2 training videos (.MOV how-to, .mp4), `archive/`.

### ⚠ CANONICAL CORRECTIONS to the as-built code (`score._sf_cf` / `classify_strategy`) — IMPORTANT
1. **Checkmate offer formula (verbatim CHECK MATE PITCH doc):** `offer = asking +15%` · `down = 10% of offer` · **monthly = 40% of rent** · **72-month (6yr) balloon**. → Code currently uses **+10%, 5yr** (Tier A) / +20%, 7yr (Tier B). **Divergent — reconcile to +15% / 6yr / 40%-of-rent.**
2. **40%-of-rent IS the seller's monthly payment** in the canonical offer (stated in the pitch + every email example) — NOT merely a "verbal anchor." This *overturns* the earlier bed-down decision to treat it as anchor-only. The buyer-side CoC still uses `(rent×0.8 − PITI)×12 / price`; the *seller-facing offer monthly* = 40% of rent. Both are load-bearing, for different jobs.
3. **SFH price cap ≈ $500K, NOT $150K** (FAQ verbatim: "no hard price limit, but for SFH tend to stay under $500,000"). → Code's Stale-SFH `<$150K` gate is **too tight**. $150K isn't a cap; it's the threshold *below which you switch to the interest variant*.
4. **Sub-$140K interest variant:** below ~$140K, *offer interest* (e.g. $5K over asking, **6.5% interest**, $15K down, **5yr balloon**, secured by deed of trust) rather than big-premium 0%.
5. **Deal terms (canonical):** EMD **$1,000–1,500 or 1% of price**, submitted **after contractor walk / post-inspection**; **inspection 5 business days**; **COE 30 days**; down **5–10% + agent commission paid from down**; closing-attorney field = "TBD at escrow"; **sign as own name/LLC, NEVER Grandin Taylor**.
6. **Entry fee (canonical):** Down + Closing + **Transaction-Coordination fee** + Assignment. (Reconciled Offer-Oven entry omits the TC fee — consider adding.)
7. **Determination confirmed:** Seller Finance = **free & clear / NO mortgage**; find via **Propwire (free) / Propstream → Free & Clear**. Creative finance = umbrella (SF + Sub-To + Hybrid).
8. **Sourcing theory (Checkmate):** tenant-occupied, listed **>$300K**, where **mortgage > rent** → impossible to sell to investor/cash/retail → SF is the only exit. Small MFH **>$1M, 4–12 units, free & clear** = capital-gains-motivated sweet spot.
9. **CONTRACT:** one editable **"Mortgage Takeover OR Seller Finance" .docx** serves both strategies (`19sgM1zTQSvDYbiCvEYjYsBUfb1bouPZA`) + a how-to-fill video. → SF + Sub-To **contract gap effectively CLOSED** (pending a read of the docx body).
- SF email deck: `1lt8Gv9lzlgOSZXEw8-pFkDt4i3UNvIZy3helfhM4Qvk` (+ ref to orig `1GUfmZsoW7Myi…`). Verbatim "SF + Cash" email template captured (6yr balloon, down + commission, payout-at-balloon).

## Contract assets spotted in Drive (to ingest)
- **`Assignment Disclosure Addendum.png`** in the Richard Taylor root (`13dQit1P4YXf6rDbe3r5gLWG15RpTgGdi`) — the assignment/wholesale disclosure (relevant to every strategy's assignment step). Image → readable via Drive.

---

## ✅ COMMITTED DECISION — Mortgage Takeover / Sub-To triage sort (Tim, 2026-06-12)
**Sort = lowest equity + lowest rate → "CALL NOW / FIRST".** Two independent signals, both ascending:
- **Equity % (ascending) = MOTIVATION.** Lowest equity = cornered seller = most motivated. Native BBC
  `equity` field (100% populated, = `(list−balance)/list`; list-anchored, so a relative signal).
- **Rate (ascending) = CoC OPPORTUNITY.** Lowest rate = cheapest assumable loan = best cash flow / carry.
- **Rate is a SORT, not a GATE.** Validated by Richard (MT L1067–1080): high-rate (6–7%) expensive deals
  are still done — at **$0 down** — they just get sold to a **live-in / retail buyer**, not an investor.

### Richard's take on rate + rent + the buyer exit (verbatim, MT course)
- **Rent/cash-flow = the DISPOSITION SPLIT, not a kill switch.** Cash-flow depends on price-vs-rent:
  cheap (<~$120–130K) cash-flows even at 6–7% → **investor buyer**; expensive at 6–7% doesn't cash flow →
  **$0 down + live-in/retail buyer** exit (L1055–1080). *(Matches Steve Ward §4 retail-buyer exit + the
  "wrap → retail buyer" structure.)*
- ≤5% rate filter is **optional narrowing** to the cash-flows-for-investor subset (L1140), not a gate.
- Trojan-Horse offer on a cornered seller (L1108): *"asking 109, owes 120… offer them $0 / 10K to take
  over the debt… pay the realtor 3–4K."*

### ⚠ BUILD CORRECTION this forces (to `classify_strategy`)
- Current code has a **CF-at-existing-payment GATE that REJECTs** non-cash-flowing MT. **Per Richard that's
  wrong** — a low-equity non-cash-flowing deal is NOT dead, it routes to the **retail/live-in exit**.
  → Change: **don't reject on CF; TAG the exit channel** — `investor` (cash-flows) vs `retail/live-in`
  ($0-down, expensive, high-rate). Keep low-equity as the motivation rank regardless.
- Rate stops being any kind of gate (the `HYBRID_MAX_RATE`/Sub-To logic still *splits* structure, but
  nothing about rate should *exclude* an MT lead from the call sheet).
- Sort key for MT section/call-sheet: `(equity% asc, rate asc)`.

## #5 — Hybrid / Fix & Flip / Cash folders + Richard's TikTok (2026-06-14)
**Source:** Drive `Strategy Assets/` folders 3/4/5 + Tim. Ingested 2026-06-14.
- **Hybrid (folder empty by design).** ✅ COMMITTED FRAMING (Tim): Hybrid has **no standalone content —
  it's the MEDIUM-EQUITY middle of the spectrum**: Seller Finance = **high equity / free & clear (no
  debt)** → **Hybrid = medium equity** (loan + meaningful equity) → Sub-To = **low equity** (cornered).
  Matches Steve Ward §1. Hybrid canonical SOP is built from: this framing + the canonical Hybrid email
  template (deck "Hybrid Multi Family": buy $250K = assume $144K + $30K down + carry $76K equity note,
  $400/mo × 60mo, balloon $52K) + the corrected code (carry-back = price − down − loan; monthly NEGOTIATED;
  NO 40%-of-rent). *(Code already correct; SOP to be written.)*
- **Fix & Flip folder:** thin — course video `youtube.com/watch?v=wVRe2r22C6U` + **funding contact: Roy /
  Prime Investor Solutions** (hard money + **DSCR** purchase/refi loans + POF; Office-forms apps). F&F
  substance stays the existing `playbooks/fix-and-flip-cash.md` (rich, live-validated). Roy = a PROCESS
  asset (buyer/Tim funding + DSCR — also relevant to the SF end-buyer's loan path).
- **Cash Deals folder:** only course video `youtube.com/watch?v=KGXI134QiaM`. No new content — Cash Arb
  substance stays the existing cash-course transcript + `fix-and-flip-cash.md`.
- **Richard Taylor TikTok:** `tiktok.com/@hold_my_hand_wholesale` — reference resource (esp. $0-down /
  Sub-To demos per MT course). The earlier unresolvable `/t/ZP8eebv6X` share link is likely one of his.
  To ingest a specific clip, need the canonical `/@hold_my_hand_wholesale/video/<id>` URL (then yt-dlp +
  Whisper). Profile-wide scrape not useful.

## #6 — Cash / Fix & Flip / Section 8 — full ingest + COURSE TRANSCRIPTS + CONTRACTS (2026-06-14/15)
**Source:** Drive `4 - Fix & Flip` + `5 - Cash Arbitrage` (updated) + YouTube course captions. Canonical HMHW.

**Course transcripts (NEW — transcribed via yt-dlp captions, preserved in `assets/sources/`):**
- `cash-section8-course-transcript.txt` — the **NEW "Section 8 / Cash Course"** (`KGXI134QiaM`, 43K chars).
  *"Two types of cash deals: Section 8 and Fix & Flip"*; distress vs turnkey Section 8.
- `fix-and-flip-course-transcript.txt` — Richard's **"long-awaited Fix & Flip course"** (`wVRe2r22C6U`,
  50K chars; real flip checks $66K/$44K/$25K). **New primary material** — supersedes the older cash-course
  transcript for F&F.

**Fix & Flip — canonical (Discord FAQ "On-Market Edition"):**
- **Offer formula CONFIRMED: `MAO = (ARV × 0.70) − rehab − assignment fee`** (e.g. ARV $300K − rehab $50K
  − fee $10K → $150K). "Be pessimistic." → the triage card's "70% of LIST" is a PLACEHOLDER; real MAO is
  ARV-based (needs the comp ritual; ARV not in BBC).
- **ARV ritual:** SOLD comps ≤6mo, within **0.3 miles**, match beds/baths/sqft, built within **15-20yr**,
  **fully-renovated comps only**, average **3** by $/sqft, avoid outliers. Confirm condition on Realtor.com.
- **Rehab ranges:** roof $8-13K · kitchen $7.5-10K · garage $9-22K · electrical $3.5K+ · default **$50K** if
  unsure · **round UP** · add 10-20% contingency.
- **Discount rule:** offer **$30-50K below list minimum** ("no discount = no deal"; $10K below adds no value).
- **Realtor approach:** never say "wholesaler" → *"I work with investors buying 2-4 fix & flips/month, close
  fast, pay cash"* + offer **dual agency**. POF + ARV comps + rehab estimate + 7-day inspection + EMD after.
- **Funding:** Roy / Prime Investor Solutions (hard money + DSCR; Office-forms apps).

**Cash / Section 8 — canonical (Discord doc Tab 4 terminology + email templates):**
- **Section 8 = the Cash-Arb buy-&-hold substance:** guaranteed govt rent **~30% ABOVE market**; FL/TN/IN
  high Sec8 rents; buyer uses **DSCR loan** (20% down, best <$150K, need cheap to cash flow at 6%+ rates);
  **FMR** (HUD fair-market-rent, by zip+beds) + **HQS** (annual inspection). Distress vs turnkey Sec8.
- **Email templates:** DSCR offer email + sample cash-offer email (comp-comparison framing) — in the doc.
- **Double close** = non-assignment-clause workaround (lender buys, you take brief title, resell).
- Glossary: MAO, ARV, hard money, assignment, holding costs, SOW, contingency, exit strategy, POF, title co.

**CONTRACTS — gap now CLOSED for Cash/F&F (artifacts in `5 - Cash Arbitrage/`):**
- **CASH PURCHASE AGREEMENT.docx.pdf** ("all seller-finance language removed" — the cash contract).
- **REAL ESTATE PURCHASE AND SALE AGREEMENT_Template.pdf** · **Purchase Contract (1)** (Doc) ·
  **LOI_TEMPLATE_1.pdf** · **Addendum to Contract.pdf** · **Partial Payout Agreement** (Doc) ·
  **TREC Termination Agreement.pdf** + **Termination Agreement 2.pdf**.
- ⚠ **Process rule:** for **traditional deals (Fix & Flip / Section 8) you use the REALTOR'S state-approved
  contract** — ask the agent to draft it; don't bring your own. The above are for assignment/JV/termination/LOI.
- *(PDF bodies not yet read clause-by-clause — read when building the commit→template feature.)*

**TikTok `/t/ZP8eebv6X` resolved (contextually):** it's the **"How to Cancel Your Contracts"** link in the
Cash contracts section → a process/termination video, NOT a strategy demo. Low priority. Richard's profile:
`tiktok.com/@hold_my_hand_wholesale`.

## #7 — Grand In Taylor submission forms (DEFINITIVE — Discord dispo-announcements, 2026-06-17)
Three Salesmate webforms, routed by cash-vs-creative AND multi-family:
- **Cash** (Fix & Flip, Section 8 cash): `696ce9d7-457b-44ad-8e6f-a9574197e587`
- **Creative / Hybrid** (single-family creative: SF, Sub-To, Hybrid): `5bddb679-43e9-4a91-aca2-ddaff898ff78`
- **Multi-Family & Portfolio** (creative MFH/portfolio contracts): `f38acae6-368f-4660-aa74-fc48afaa99ca`
⚠ Prior triage/SOP only had 2 (missing MultiFam) and **was missing HY entirely** + sent MFH creative
deals to the SFH "Creative/Hybrid" form. Fixed in `triage.py gt_url` (route by `_gt_mfh`) + Sub-To SOP.
Also seen: Grand In Taylor emails `cash@grandintaylorproperties.com` / `tc@grandintaylorproperties.com`;
MT-needs-new-loan submission `forms.gle/wjpqMW439noic3j47` (partner lender Andrew).

## DATA-SOURCING NOTES (for triage)
- **Mortgage Takeover / Sub-To loan data:** the canonical fields (interest **rate**, loan **balance**,
  loan **type** to avoid HELOC/reverse) live in **PropStream** — but **PropStream has NO API**
  (Tim, 2026-06-12). **It therefore cannot be an automated triage enrichment — it is a MANUAL operator
  verify step only.** Architecture forced by this:
  - **Programmatic source = BBC Lightning Leads** — already exposes `balance`/`interestRate` for
    `mortgageTakeover`-tagged leads. This is what triage filters/ranks on (equity %, rate band).
  - **PropStream = manual verify** before the call — surface a "verify rate/balance/loan-type in
    PropStream" prompt on the MT card; do **not** attempt to auto-pull it. (Browser-scrape is
    fragile/ToS-risky → not a dependency.)
  - **Propwire (free) = partial fallback** — flags free-&-clear + partial balance, **but is inaccurate
    and shows no interest rates** (SF FAQ). Useful for the SF free-&-clear flag, weak for MT rates.
  - Net: MT equity-% + rate ranking runs entirely on **BBC data**; PropStream/Propwire are human
    double-checks, not pipeline inputs.
- **Seller Finance (free & clear) determination:** **Propwire (free) → Free & Clear** flag, or
  **Propstream → Mortgage Information → Free & Clear → Include**. (SF FAQ.)
