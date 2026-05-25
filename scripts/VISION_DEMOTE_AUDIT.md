# Vision Condition-Demote Audit & Fix — 2026-05-25

## Background

`triage.py` runs Claude **Haiku 4.5** vision (`analyze_property_vision`) on every
qualified BBC listing's photos to score condition 1–5 and optionally reclassify a
Seller-Finance deal to Fix & Flip (`demote_to_ff`) or drop it (`reject`).

## The problem

On the **2026-05-25** run, vision demoted **42 of 75 cards (56%)** out of the
Seller-Finance lane into Fix & Flip. **32** of those demotes were at **condition 3**.

A 7-property sample of the condition-3 demotes was eyeballed against the actual
listing photos. **All 7 were false demotes.**

| Property | Photos showed | Vision said | Reality |
|---|---|---|---|
| 1710 Gratiot Ave, Saginaw MI | 1 exterior; sound brick colonial | 3/5 "paint, porch, landscaping" | rentable, exterior-cosmetic only |
| 8525 Dosia St, Houston TX | 1 photo; freshly renovated, new siding | 3/5 "roof damage, foundation" | move-in ready (4–5) |
| 4919 Holt Peterson Rd, Tuscaloosa AL | interior; dated but clean/functional | 3/5 "kitchen/bath updates required" | rentable as-is |
| 3005 Sunrise St, Memphis TN | fully renovated — new floors/paint/kitchen | 3/5 "new flooring, roof repairs" | condition 5 (egregious) |
| 16284 Coram St, Detroit MI | intact siding; clean renovated room | 3/5 "worn siding, foundation" | rent-ready |
| 1708 Northview Dr, Greenville MS | 4 photos, **all exterior**; sound brick ranch | 3/5 "dated interior, worn flooring" | **interior hallucinated** — no interior photo exists |
| 423 W Sycamore St, Boonville IN | occupied/furnished, livable | 3/5 "porch foundation, paint" | rentable; someone lives there |

### Two root-cause failure modes

1. **Wrong question.** Vision graded *"does this need any cosmetic work?"* and
   demoted if yes. But the HMHW play is **buy-and-hold rental** — the real test is
   *"rentable to a tenant as-is?"* Dated, tired, or even freshly-renovated houses
   are fine rentals, yet all got demoted.
2. **Interior hallucination.** With only the first 2 photos (`images[:2]`, usually
   exteriors), vision invented interior condition it could not see (Northview is the
   clearest case).

## The fix (applied 2026-05-25)

1. **Stop demoting on condition 3.** Code hard-floor in the vision-apply loop:
   `action == 'demote_to_ff' and tier_name != 'FF' and (condition or 3) <= 2`.
   Condition 3 (dated/cosmetic but rentable) stays in its Seller-Finance lane; the
   vision notes still render on the card for the operator's Zillow check.
2. **Send ALL photos**, not just the first 2 — `images[:MAX_VISION_PHOTOS]`
   (`MAX_VISION_PHOTOS = 20`). Interior photos are what determine rentable-vs-rehab.
3. **Reframed `VISION_PROMPT`** around *"rentable to a tenant as-is vs needs rehab
   before move-in,"* with an explicit instruction to judge only what the photos show
   and lean *qualify* (never invent interior wear) when only the exterior is visible.

**Intentionally NOT done** (per Tim): a Sonnet two-pass / confidence gate — speed to
an accurate call list matters more than squeezing out the last few percent.

Cost impact: ~$0.005 → ~$0.02 per property (more photos), ≈ $2/day. Negligible.

## Still open

- The **10 condition-2 demotes** were not audited — they may be legitimately
  rehab-grade, so they still demote. Worth a future photo spot-check.
- Effect applies to the **next** triage run; already-published briefings are static.
