# Strategy Bed-Down #1 — SELLER FINANCE (Creative · Free & Clear)

**Purpose:** lock the full vertical slice for ONE strategy before touching the next — *criteria →
math → script → template* — with (a) what I think it must be on the build, (b) a validation pass
against primary sources, (c) every source cited. This doc is the spec the SOP + template rewrite
will implement. Nothing here is committed to the live SOP yet.

> **One-line definition (Steve Ward, 2026-06-05):** *"It's all seller finance — just variations of
> terms, sorted by how much equity the seller has."* Seller Finance **strict** = the **free & clear
> / ~100% equity** end of that spectrum: no loan to take over, the **seller carries the whole note.**
> (Existing-loan variants = Mortgage Takeover, bedded down separately.)

---

---

## ⚠ CANONICAL CORRECTIONS (2026-06-12 — from Tim's Drive capture of *Discord › Seller Finance*)
These **supersede** the numbers in §§1–3 below where they conflict. Source: "CHECK MATE PITCH" doc,
"Seller Finance Discord Content" (FAQ + pitch process + terminology), SF email deck. **Canonical HMHW.**

1. **Checkmate offer formula (verbatim):** `offer = asking + 15%` · `down = 10% of offer` ·
   **`monthly to seller = 40% of rent`** · **`72-month (6-year) balloon`**. *(Supersedes the earlier
   +10% / 5-yr Tier-A and +20% / 7-yr figures.)*
2. **40%-of-rent IS the seller's monthly payment** — the actual offer mechanic, stated in the pitch and
   every email example. **This overturns Decision D2** (which kept it as a "pitch anchor only"). Keep
   BOTH on the card, correctly labelled: the **offer** monthly = 40%×rent; the **underwriting** check =
   `CF = rent×0.80 − PITI` (and buyer cash-CoC = `(rent×0.8 − PITI)×12 / price`). Different jobs.
3. **SFH price ceiling ≈ $500K, NOT $150K** (FAQ: "no hard price limit… for SFH tend to stay under
   $500,000"). $150K is *not* a cap — it's the line below which you switch to the **interest variant**:
   sub-~$140K → offer ~$5K over asking, **6.5% interest**, ~$15K down, **5-yr balloon**, secured by deed
   of trust. *(Supersedes the Stale-SFH `<$150K` gate — it was silently rejecting valid SF deals.)*
4. **Standard terms:** EMD **$1,000–1,500 or 1% of price**, submitted **after the contractor walk /
   post-inspection** · **inspection 5 business days** · **COE 30 days** · down **5–10% + agent
   commission paid from the down** · closing-attorney field "TBD at escrow" · **sign as own name/LLC,
   NEVER Grandin Taylor**.
5. **Contract:** a single editable **"Mortgage Takeover OR Seller Finance" .docx** serves SF *and*
   Sub-To (in `1 - Seller Finance/`). SF contract gap → effectively closed.
6. **Sourcing theory (Checkmate):** tenant-occupied, listed **>$300K**, where **mortgage > rent** →
   un-sellable to investor/cash/retail → SF is the only exit. Small MFH **>$1M, 4–12 units, free &
   clear** = capital-gains-motivated sweet spot.
7. **Offer-Oven "commit → template" (clarified by Tim):** the Offer Oven populates the **numbers into the
   correct corresponding EMAIL/OFFER template** — it does **NOT** fill the legal contract. The contract
   is a separate artifact. → feature is gated on the email/offer templates (which we now have), not on
   contracts.

---

## 1. CRITERIA — who lands here, and the determination test

**The routing test (Step 2 of `classify_strategy`):** `loan_balance ≈ 0` → Seller Finance group.
Signalled by the BBC `sellerFinance` tag or a Propwire "free & clear" flag. Then split into two
sub-types:

| Sub-type | Was | Test | Why it's the SF exit |
|---|---|---|---|
| **Checkmate** | Tier A | MFH **5+ units**, OR **2–4plex that is NOT retail-desirable**; **$200K–$1.4M**; DOM **90+**; pencils at settle terms | 5+ units can't use FHA → investor must use DSCR → DSCR fails at 7%+ → **SF is the only way it closes** |
| **Stale-SFH** | Tier B | **SFH < $150K**; DOM **90+** (150+ ideal); free & clear | Cheap, long-DOM sellers accept terms when nothing else moves |

**What I think it must be on the build:**
- **Price floor $200K, not $350K.** The course underwrites duplex/triplex/quadplex SF from ~$190K
  upward, not just the 5+ unit $350K–$1.4M band. *(The deployed code already uses $200K; `deal-criteria.md`
  still says $350K — that doc is stale and must be reconciled.)*
- **2–4 units only count as Checkmate if NOT retail-desirable.** A clean, owner-occupiable duplex has
  a retail/FHA buyer pool, so the DSCR-wall logic doesn't apply — it's not a Checkmate. Operator confirms
  "not retail-desirable" via the photo check.
- **Equity-unverified pill.** Free & clear is *inferred* from the tag, not confirmed. Card must carry
  "equity unverified — confirm via Propwire/PropStream before calling" (Steve's rule). No scraping.
- **Down-payment scaling** (drives the offer, not the gate): ≤~$80K tolerates ~15%; $80–150K → 10–12%;
  $150K+ → **10% strict** (more down kills the end-buyer's CoC).

**Validation:**
- ✅ "2–4plex only if not retail-desirable" — SF Course **L958–982** verbatim: *"if it's a duplex…
  they're looking for a retail buyer… 'I want to live in this duplex'… that stops [it]… retail desirable.
  This bathroom is nicer."*
- ✅ Down-scaling — SF Course **L135–148**: ~$80K property tolerates >10% down; *"as it starts to get
  higher than that, putting down more than 10% is"* discouraged.
- ✅ DSCR-wall Checkmate frame — `deal-criteria.md` §Tier-A; live calls Pitch 9 ($2.1M) / Pitch 13 ($1.7M MF).
- ⚠ **Stale claim to fix:** `deal-criteria.md` Tier-A says **$350K–$1.4M** and the old entry formula
  (`Down + $3,000 + $5,000`). Both are superseded (see §2). The SOP rewrite must update them.

---

## 2. MATH — TWO layers, deliberately different numbers (the core insight)

The single biggest source of card confusion is conflating these. They are **not** the same number and
**should not** agree:

### Layer A — Underwriting math (decides qualify + rank + CoC; the number Tim trusts)
This is the Offer Oven sheet, now reproduced exactly by the script (reconciliation fixes A/E):
```
offer       = list × 1.10 (Checkmate) or list × 1.20 (Stale-SFH)   ← premium for 0%
down        = offer × 10% (Checkmate) / 12% (Stale-SFH)
P&I         = (offer − down) / 360          ← 0% interest, 30yr amort → pure principal
PITI        = P&I + tax + insurance + HOA
reserves    = rent × 0.20                    ← CapEx 5% + Mgmt 5% + Vacancy 10%
CF          = rent − PITI − reserves   ( ≡ rent × 0.80 − PITI when reserves load = 20% )
entry fee   = down + (offer × 2% closing) + $5,000 assignment        ← matches the sheet
CoC         = CF × 12 / entry
```
✅ **Validated end-to-end:** McCormick fixture ($75K list, Tier B) → offer $90,000, down $10,800,
CF $703/mo, **entry $17,600, CoC 47.9%** — reproduces the Offer Oven sheet's own outputs ($703 / $17,600 /
48.0%). Source: `scripts/TRIAGE_OFFEROVEN_RECONCILIATION.md`.

### Layer B — Pitch anchor (what Tim SAYS on the call; NOT the underwriting number)
```
monthly to seller ≈ 40% of gross rent
```
- This is **Richard's verbal shorthand**, not the load-bearing math. It **overstates** the seller's
  real monthly vs the amortized P&I (e.g. ~$600 spoken vs ~$200 amortized on an $80K deal). That gap is
  intentional — it sounds meaningful to the seller and is mental-math-able on a live call.
- **Validation / honesty flag:** mining 63,238 Discord messages found "40%-of-rent" only **4×** and
  **0× in the `Deal Check` channel** where deals are actually vetted. The community underwrites with
  Layer-A mechanics. **Conclusion: keep 40%-of-rent as a clearly-labelled "pitch anchor" on the card,
  never as the CF/CoC math.** Source: `playbooks/40-percent-rent-rule.md` (2026-05-23 re-grade);
  live verbatim `c2hNH6u7D0k @ 1:11:34` & `@ 2:27:52`.

### Load-bearing comp = RENT (not ARV)
SF deals live or die on rent. Haircut **asking** rent to the **real average** before trusting CF.
✅ SF Course **L604–606**: *"They're asking 1,700. Doesn't mean they're getting 1,700. I bet it's on
average maybe $1,400."* Ritual: Zillow Rent Zestimate vs BBC pill, lower wins if >20% gap; re-run
`CF = rent × 0.80 − PITI`. Source: `comps-sop.md` Ritual 1.

**What I think it must be on the build:** the card shows **both** numbers, explicitly labelled —
the **Underwriting CoC/CF** (the trust number, top of the Creative Outcome) and a separate **"💬 Pitch
anchor (40% of rent)"** line. Never let the 40% figure feed CoC.

---

## 3. OFFER LADDER — open vs settle (the #1 confidence fix)

The deal must **underwrite at the settle terms** (conservative), but Tim should **open softer** and
ladder toward them. Tim's live-deal mistake (per Steve): he *opened* at his settle.

| Lever | OPEN at | Ladder toward | SETTLE / underwrite at | Source |
|---|---|---|---|---|
| **Down payment** | **6.5–7%** | → up | **10%** (12% cheap-SFH) | Steve §2 |
| **Price** | **at asking** | → over only if needed | asking **+10–20%** | Steve §2 / `deal-criteria` |
| **Balloon** | **15 yr** | → 10 | **floor 7** (5 for MFH) | Steve §2 / SF L-structure |
| **Interest** | 0% (premium covers it) | bake rate into price; or extend amort 35–40yr | 0% | tier-a playbook (`u-ov-X0Cc68 @ 19:56`) |

**Hard rules (validated):**
- **Never give the seller BOTH an inflated price AND an interest rate** — pick one. (`deal-criteria.md`).
- **3rd lever** when the seller fixates on rate: *extend amortization to 35–40yr* so the payment
  "disappears to interest" while keeping down low — `tier-a-mfh-seller-finance.md` (live `u-ov-X0Cc68 @ 0:19:56`).

**What I think it must be on the build:** each SF card carries a one-line **open→settle ladder**
("Open 7% down · at asking · 15yr → settle 10% · +10% · 7yr") so Tim never blurts his settle. This is
the piece the realignment plan promised and the card does **not** yet have.

---

## 4. SCRIPT — the call (Checkmate / Stale-SFH)

**Opener — conversational, NOT DSCR-first** (live-call refinement; in ~30K caption lines Richard never
opens with DSCR): *"What can you tell me about this?"* → listen → drop the SF formula when the door
opens. The **DSCR-wall walkthrough is the Checkmate** *explanation* you reach for when the agent asks
"why propose this?" — not the lead. Source: `tier-a-mfh-seller-finance.md` §live-call refinements
(`CzUeF6SASGA @ 36:56`, `c2hNH6u7D0k @ 1:08:27`).

**The one-liner (verbatim):** *"I'll give you [asking], 10% down, 40% of whatever it rents out for in
monthly payments, 7-year term."* (`c2hNH6u7D0k @ 1:11:34`). ← but per §3, **open** softer than this.

**Objection rebuttals (Tier-A specific, verbatim in playbook):** cash-only → "how vs what they get
paid"; other offers → "are they clearing DSCR at 7.25%?"; 0% too low → "premium IS the interest,
effective 8–9%"; default risk → "deed reverts to them, mutual skin in the game"; too busy → lower
urgency for them, raise it for the property. Source: `tier-a-mfh-seller-finance.md` §Objections 1–5.

**Definition of "verbal yes":** *"Let me run it by my seller"* + agent forwards your contract +
follow-up booked. NOT acceptance. Don't push for a deal commitment — push for the decision opportunity.

---

## 5. TEMPLATE — post-call follow-up

**Rule (Steve §6):** email after **every** call, **reference the actual conversation**, offer an LOI.
Personable not salesy — *"they get a lot of [salesy]; stand out."* Skeleton:
```
Subject: [Address] — the seller-finance structure we discussed
Great talking today, [name] — I loved how you described [specific thing about the property].
Here's the structure I'd put in writing:
  • Purchase price: [asking (+premium if laddered there)]
  • Down: [laddered] at closing · commission paid from down at closing
  • 0% · 30yr amortization · [balloon] balloon
  • Monthly to your seller: ~[40%-of-rent $] (≈ what it rents for, minus the bank)
If your seller wants it formalised, I'll send a one-page LOI + the contract today.
Reach me at [phone / text / email].
```
**Current state of templates:** the SF assets that exist are **43 call recordings** (audio,
`hmhw-call-library-seller-finance.md`) + script text in `outreach-scripts.md`. The realignment's
per-group **`templates/seller-finance/{email,contract,terminology}`** folder **does not exist yet** —
it needs scaffolding, and the canonical email/LOI/contract come from the HMHW Discord `seller-finance`
group's `email-templates` + `contracts` channels (Tim pastes those; no scraping). Each SF card should
deep-link its matching email + contract, auto-filled with the deal numbers + a line referencing the call.

---

## 6. Net build changes this bed-down implies (for the SOP + template phases)

1. **`deal-criteria.md`** — reconcile to: $200K Checkmate floor; **entry = down + 2%×offer + $5K**
   (drop the `$3,000 + $5,000` formula); 3-group framing; add the open→settle ladder + down-scaling.
2. **Card (triage.py)** — already has the determination line + reconciled CoC. STILL TO ADD: the
   open→settle **offer-ladder line**; the **equity-unverified pill**; relabel the 40% banner explicitly
   as "pitch anchor" (it's gated to SF but the label should say *anchor*, not *the math*).
3. **Templates** — scaffold `templates/seller-finance/{email,contract,terminology}/`; wire each SF card
   to its email + contract with deal-number autofill.

---

## 7. Open decisions for Tim (need your call before I write the SOP)

- **D1 — Open at Steve's soft ladder (7% down / at-asking / 15yr) or the course's 10%/+premium/7yr?**
  My rec: **underwrite at 10%/7yr (conservative), script the OPEN at Steve's soft ladder.** Confirm.
- **D2 — Keep the 40%-of-rent line on the card at all?** My rec: **keep, relabelled "pitch anchor,"
  never feeding CoC.** Alternative: drop it and show only amortized seller-monthly.
- **D3 — Checkmate price floor $200K** (code) **vs $350K** (old doc). My rec: **$200K** (matches the
  course's duplex examples). Confirm so I reconcile `deal-criteria.md` to it.

---

## Sources used (Seller Finance bed-down)
- **Primary transcript:** `hmhw-transcript-seller-finance-course.txt` — L135–148 (down-scaling),
  L604–606 (rent "asking ≠ getting"), L779–782 & L958–982 (duplex/retail-desirable).
- **Playbooks:** `playbooks/40-percent-rent-rule.md` (anchor + 2026-05-23 re-grade), 
  `playbooks/tier-a-mfh-seller-finance.md` (live-call refinements, objections, structure),
  `playbooks/tier-b-cheap-sfh-stale.md`.
- **Criteria / comps:** `references/deal-criteria.md`, `references/comps-sop.md` (Ritual 1 rent).
- **Coaching:** `references/steve-ward-coaching-notes.md` (unifying model §1, offer ladder §2, template §6).
- **Math reconciliation:** `scripts/TRIAGE_OFFEROVEN_RECONCILIATION.md` (Offer Oven sheet formulas + McCormick).
- **Live-call verbatims:** `c2hNH6u7D0k @ 1:08:27 / 1:11:34 / 2:27:52`, `CzUeF6SASGA @ 36:56`,
  `u-ov-X0Cc68 @ 0:19:56`. Call recordings: `hmhw-call-library-seller-finance.md` (43 SF calls).
- **Code as-built:** `scripts/triage.py` `classify_strategy()` / `score()` `_sf_cf()`.
