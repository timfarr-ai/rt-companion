# MFH Starvation Diagnosis & Dedicated Search-Pass Fix — 2026-05-30

## Background

Tier A (Multi-Family Seller Finance) is Richard's bread-and-butter — the canonical
"Checkmate" play where FHA fails → DSCR fails at 7%+ → seller finance is the only
path. Yet daily briefings were surfacing almost no MFH.

## The problem

`triage.py` fetched leads with a single per-state pull: `deal_type` across
`sellerFinance + mortgageTakeover + fixAndFlip`, **no property-type filter**, sorted
`daysOnMarket desc`, capped at **75/state**. Because the 75 stalest listings per
state are dominated by cheap SFH, genuine multi-family never entered the funnel.

Measured live (2026-05-30, authenticated probe) on the blind `sellerFinance` pull:

| State | Results | of which MFH |
|---|---|---|
| Ohio | 75 | **7** |
| Tennessee | 75 | **1** |
| Texas | 75 | **1** |

So the starvation was at the **fetch** stage, not the tiering stage — the listings
never arrived to be tiered.

## Root cause: the `property_type` filter contract

BBC's `/api/lightning-leads/search-property` **does** support a `property_type`
filter — but with two non-obvious requirements that made naive attempts no-ops:

1. It must be an **array**, not a scalar — body shape (prod chunk `8224`):
   `property_type: code ? [code] : undefined`.
2. The value is a **lowercase code** (`"multi"`), **not** the display string
   `"Multi Family"`. The display string and the bare scalar are both **silently
   ignored** — the endpoint returns the full unfiltered set with no error.

Tell that pointed to the code: BBC's own UI auto-sets `propertyType:"multi"` whenever
`dealType:sellerFinance` is selected.

Verified by direct comparison (same query, only the filter varied):

| Filter sent | Ohio result mix | Tennessee result mix |
|---|---|---|
| none | 7 MFH / 51 SFH / Condo / Lot … | 1 MFH / 50 SFH / 16 Condo … |
| `["Multi Family"]` | **ignored** — identical to none | **ignored** — identical to none |
| `["multi"]` | **75 / 75 Multi Family** | **75 / 75 Multi Family** |

## The fix (applied 2026-05-30)

1. **Dedicated MFH pass** added after the off-market MT pass — one
   `property_type:["multi"]` search per state, `deal_type` kept broad so MFH that BBC
   tagged MT/FF also enters and is routed by `tier()`. 10–75× more Tier A inventory.
2. **Cross-pass pid-dedupe** in the scoring loop (`seen_pids`) — the MFH pass overlaps
   the primary pull; first occurrence wins, since the property object is identical
   regardless of which search surfaced it.
3. **`Dup-skipped=`** counter added to the summary log to show the overlap.

Branch: `mfh-dedicated-search-pass`. Mechanism verified live; full-pipeline run only
possible in the cloud routine env (local box has BBC creds only, not
`AT_TOKEN`/`GH_PAT`/`ANTHROPIC_API_KEY`).

## Still open (separate follow-ups, intentionally NOT in this change)

- **$1.4M search cap** (`price_range.max`) — excludes larger apartment buildings from
  the pool entirely. Raising/removing it is the next lever for true 5+ unit MFH.
- **$200K Tier A price floor** — a cheap 2-4 unit duplex/triplex tagged seller-finance
  falls through Tier A (price < $200K) AND Tier B (`not is_mfh` fails), landing in
  REJECT. Lowering the floor for 2-4 unit MFH closes that trap.
- Effect applies to the **next** triage run; already-published briefings are static.
- The routine fetches `triage.py` from GitHub raw, so the change must be **merged**
  (or the routine pointed at the branch) before it takes effect.
