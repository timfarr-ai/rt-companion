# RT Dashboard — Master Plan (5-Strategy, End-to-End)

**The directive (Tim, 2026-06-12):** the whole rt-dashboard — **site, SOPs, triage, calculator,
templates, training** — is structured around **five strategies, end to end**, with **everything that
supports the process** built on that spine. This doc is the single authoritative plan; the others below
are sub-artifacts under it.

## The five strategies (the spine — everything keys on these)
1. **Seller Finance** — free & clear; seller carries the whole note. *(Profiles: Checkmate MFH · Stale-SFH.)*
2. **Sub-To** — existing loan, low equity (cornered); take over the payment for a small lump / $0.
3. **Hybrid** — existing loan + real equity; assume the loan **and** carry the equity as a note.
4. **Fix & Flip** — cash, distressed; win on the buy (70%-of-ARV − rehab).
5. **Cash Arbitrage** — already cash-flows; wholesale at a cash discount.

> Rule of the rebuild: **no 3-group wrapper, no Tier A/B/C.** Five flat strategies. Duplication across
> per-strategy assets is acceptable and expected. No correction-blocks layered on stale content — each
> doc is rebuilt correct, once.

---

## The end-to-end process (what every strategy needs, in order)
Each stage must exist, per strategy, and be wired together:

```
 ① CAPTURE      Drive "Strategy Assets/<n - strategy>/" → ingest → assets/CAPTURED_SOURCES.md (provenance)
 ② CRITERIA     who qualifies + the determination test  (triage classify_strategy + canonical SOP §1)
 ③ SOURCING     BBC Lightning Leads pull (programmatic) + PropStream manual verify  (per-strategy search net)
 ④ TRIAGE       classify → rank (per-strategy sort) → 📞 Call Sheet  (triage.py → briefing)
 ⑤ COMPS        the load-bearing check before offering (RENT for SF; ARV+PITI for MT/Cash)
 ⑥ THE CALL     script · objections · "verbal yes"  (canonical SOP §script)
 ⑦ THE OFFER    Offer Oven → suitability check → commit numbers → the right EMAIL/OFFER template
 ⑧ THE CONTRACT per-strategy contract (SF/MT trust-acquisition · cash purchase · assignment)
 ⑨ DISPO        exit channel: investor (cash-flows) vs retail/live-in ($0-down) · assignment fee
```

"Everything to support the process" = each of ②–⑨ exists for all 5 strategies, sourced and wired.

---

## Canonical SOP structure (APPROVED pattern — see `playbooks/sub-to.md`)
**One doc per strategy.** Seven sourced sections:
`1 Criteria · 2 Comps · 3 Math/Offer + Exit · 4 Script · 5 Email templates · 6 Contract · 7 Terminology`
+ a Sources footer. Replaces the old playbooks (tier-a, tier-b, mortgage-takeover, hybrid-mt-sf-carryback,
fix-and-flip-cash) and the layered correction blocks. Lives in `playbooks/<strategy>.md`.

## Site / front-end restructure (the dashboard itself)
- **Briefing / call sheet:** already 5-strategy + cross-group Top-20. Each card's "Open playbook" link
  repoints from the old tier playbooks → the new canonical `playbooks/<strategy>.md` (HTML render).
- **Per-strategy template wiring:** each card deep-links its strategy's **email/offer template** (filled
  with the deal numbers) + its **contract** + the Offer Oven.
- **Training pages:** rendered `strategy/*.html` regenerated from the canonical SOPs (one per strategy).
- **Index/nav:** organised by the 5 strategies end-to-end (capture → criteria → call → offer → contract → dispo).

## Offer Oven (the calculator — 4 features, per `STRATEGY_SYSTEM_PLAN_AND_PROOF.md` §4)
1. **Field/function parity** with Richard's sheet (fix `assign×0.6` → full assignment; audit vs live sheet).
2. **Suitability validation** — PASS / COUNTER / KILL verdict per strategy thresholds.
3. **Commit → EMAIL/OFFER template** (numbers only, NOT the contract) — picks the template by strategy.
4. **Recall** saved figures (Airtable Deal-Flow as store).

---

## Committed decisions + corrections (durable — already applied unless noted)
**Seller Finance:** offer = asking **+15%** (default; flexes higher with longer balloon up to 96mo) ·
10% down · **monthly to seller = 40% of rent** (the offer, not an anchor) · **72-mo (6yr) balloon** ·
SFH ceiling **~$500K** (sub-$140K → interest variant) · EMD $1–1.5K/1% post-inspection · COE 30d.
**Mortgage Takeover (Sub-To + Hybrid):**
- **Cash flow + rate are SORTS, not gates.** Sort = **lowest equity → lowest rate = call first.**
- **Cash flow tags the EXIT:** cash-flows ⇒ investor; doesn't ⇒ **$0-down, live-in/retail buyer.** Never reject.
- **Sub-To** = equity-after-costs ≤ ~$15K → small lump/$0; **Trojan-Horse offer = balance + 4% of asking.**
- **Hybrid** = real equity + rate ≤6% → cash + assume loan + **carry the EQUITY as a note** (`carry-back =
  price − down − loan balance`), **monthly NEGOTIATED.** ⚠ **The SF +15%/40%-of-rent method must NEVER be
  applied to MT/Hybrid** (fixed in code 2026-06-12).
- **Contract = Trust Acquisition** (revocable living trust; buyer 90-95% / seller 5-10% beneficial
  interest; mortgage stays in seller's name; HUD-1 line 203).
- **Property types for MT = SFH · condo · MFH** (MFH uncapped — $500K is SF-SFH only).
**Data architecture:** BBC = the programmatic source (rate/balance/equity% 100% on MT leads).
**PropStream has NO API** → manual pre-call verify only (loan TYPE/HELOC/reverse, 2nd liens, AVM,
owner skip-trace). Propwire = partial free fallback (free-&-clear flag; no rates).
**Fix & Flip:** `70% of ARV − rehab` (70% is the CEILING; offer 60-65%). The card's "70% of list" is a
PLACEHOLDER — still wrong in the engine, to be corrected.

---

## Status
**DONE**
- Triage code: 5-strategy `classify_strategy` (Step 1-4); MT exit-channel + (equity,rate) sort + no CF
  gate; SF code aligned to +15%/40%/72mo/$500K; MFH-MT uncapped; condo carve-out for MT; Trojan-Horse
  offer field+pill; Hybrid banner rebuilt (no 40%-rent); 3-group→5-strategy output + Top-20 call sheet;
  Offer-Oven reconciliation fixes A/C/E/F/G. Unit-tested + compiles. *Not committed to git / not deployed.*
- SOP corrected for MT + SF (deal-criteria, strategy-selector, MT + SF playbooks) — **interim correction
  blocks; to be replaced by canonical SOPs.**
- Canonical SOP: **Sub-To done** (`playbooks/sub-to.md`) = the approved pattern.
- Cruft archived → `_archive/` (old 3-group plan, intake/, Drive-doc template).
- Captures ingested: Sub-To/MT (Trust Acquisition, 60+ email templates, PropStream slide), Seller Finance
  folder (criteria/script/contract/email/terminology). Logged in `CAPTURED_SOURCES.md`.

**IN PROGRESS**
- Canonical SOPs: Seller Finance, Hybrid (fixes the wrong 40%-rent prose), then Fix & Flip, Cash Arb.

**PENDING**
- Ingest Drive folders: 3-Hybrid, 4-Fix & Flip, 5-Cash Arbitrage; read SF contract .docx body + SF email deck.
- Retire old playbooks (→ _archive) + repoint front-end card links to canonical SOPs + regenerate `strategy/*.html`.
- Per-card template + contract wiring (front-end integration).
- Offer Oven: the 4 features (parity / validation / commit→template / recall).
- Fix & Flip engine: replace "70% of list" placeholder with `70% ARV − rehab`.
- Full number-by-number dashboard audit (claim → canonical source → verdict) for the un-audited paths.
- Commit + deploy the corrected triage (currently local-only; the daily briefing still runs old code).

---

## Open decisions
- Canonical SOPs **reference** templates/contract vs **embed** them inline. (Current: reference.)
- Premium as a fixed +15% default vs a lever that scales premium↔balloon together.
- 40%-of-rent vs amortized P&I as the SF underwriting-CF basis (unresolved — needs the live Offer Oven sheet).
- Retail/live-in MT deals: rank alongside investor deals on the call sheet, or a separate B-list?

## Document map (single sources of truth)
- **This file** = the master plan.
- `assets/CAPTURED_SOURCES.md` = provenance ledger + committed decisions (audit trail).
- `assets/sources/` = verbatim canonical captures (e.g. the 60+ Sub-To email templates).
- `playbooks/<strategy>.md` = canonical per-strategy SOP (Sub-To done; rest pending).
- `STRATEGY_BEDDOWN_SELLER_FINANCE.md` = the SF spec (→ folds into `playbooks/seller-finance.md`).
- `STRATEGY_SYSTEM_PLAN_AND_PROOF.md` = the proof matrix + Offer Oven feature design (the audit appendix).
- `_archive/` = superseded scaffolding.
- Google Drive `Richard Taylor/Strategy Assets/<n - strategy>/` = Tim's raw capture inbox.
