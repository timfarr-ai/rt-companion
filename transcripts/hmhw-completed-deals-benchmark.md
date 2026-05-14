# Richard Taylor's Completed Deals — Benchmark Dataset

Mined from course transcripts + call library. **Use this to validate the triage filter: would our pipeline have correctly qualified each of these?**

## Cash / Fix & Flip (Cash Course)

| # | Property | Price paid | ARV | Strategy | Source |
|---|---|---|---|---|---|
| 1 | 1618 Katalpa, Cleveland OH | n/a | n/a | Distressed flip ("ship box") | Cash L626-685 |
| 2 | 13605 Tacoma Street, Detroit MI | n/a | n/a | Duplex (converted SFH→duplex) | Cash L633-642 |
| 3 | Park View (Cleveland) | $68K | $140K | Flip (under contract pending) | Cash L955-963 |
| 4 | Wholesale @ $47K | $47K | $140K | Wholesale flip | Cash L949-953 |
| 5 | "Michael's deal" | n/a | n/a | One-call flip; $3K assignment fee | Cash L664-668 |

**Pattern:** Cleveland / Detroit, <$80K cash purchase, 70% of list rule. Heavy rehab acceptable.

## Seller Finance — MFH 5+ (Tier A "Checkmate")

| # | Property | Asking | Offered | Source |
|---|---|---|---|---|
| 6 | Punta Gorda FL (MFH) | $320K | $325K | SF L88-91 |
| 7 | Pitch 9 — "$2.1m Dollar Deal" | $2.1M | (in pitch) | Call library |
| 8 | Pitch 13 — "1.7m Multifam" | $1.7M | (in pitch) | Call library |
| 9 | Pitch 23 — "Offering 100k Above Asking" | n/a | +$100K premium | Call library |
| 10 | Pitch 25 — "4 Deals in One Call" | mixed | mixed | Call library |
| 11 | Pitch 30 — "700k House" | $700K | (in pitch) | Call library |

**Pattern:** $320K–$2.1M, MFH 5+ units, asking + 10% premium with 10% down at 0%.

## Seller Finance — SFH / 2-4 unit MFH (Tier B / Tier A broadened)

| # | Property | Notes | Source |
|---|---|---|---|
| 12 | Pitch 3 — "Condo" | SF on a condo — exception case | Call library |
| 13 | Pitch 31 — "Pivoting to Seller Finance" | Cash → SF pivot during call | Call library |
| 14 | Pitch 34 — "Duplex" | 2-unit SF (broader Tier A) | Call library |
| 15 | Pitch 19 — "Impossible Terms to Best Terms" | Negotiation example | Call library |

**Pattern:** Stale listings, retail-buyer pool eliminated (per SF Course L957), 2-4 unit OK if not "retail desirable."

## Mortgage Takeover

| # | Property | Listing | Owed | MT structure | Source |
|---|---|---|---|---|---|
| 16 | Off-market MT (Clayton NC area) | $91K | $60K | $9K to seller | MT L1007-1024 |
| 17 | Hybrid Pitch 1 — "1.85m Dollar AirBNB" | $1.85M | n/a | MT + SF gap hybrid | Call library |
| 18 | Subject To Pitch 9 — "Off Market" | n/a | n/a | Off-market MT play | Call library |
| 19 | Subject To Pitch 12 — "One of the Best Calls Ever" | n/a | n/a | MT close | Call library |
| 20 | Subject To Pitch 7 — "Portfolio of Properties" | n/a | n/a | Multi-property MT | Call library |
| 21 | Subject To "Accepted Offer 1/2/3" | n/a | n/a | Closed MT deals (3 examples) | Call library |

**Pattern:** Existing favorable loan, often underwater seller, pay $5-15K cash for the assumption. **MANY are off-market** (listing was removed because seller couldn't profit).

---

## How our triage scores against this benchmark

| Benchmark deal pattern | Triage covers? | Notes |
|---|---|---|
| Cleveland/Detroit cheap flips | ✅ Tier FF + condition-risk demote | Pre-1940 + <$80K → routes to FF automatically |
| Duplex/triplex SF (not retail-desirable) | ✅ Tier A | Updated to 2+ units, $200K floor |
| MFH 5+ Checkmate $200K-$1.4M | ✅ Tier A | Original Tier A criteria preserved |
| Cheap SFH SF <$150K | ✅ Tier B | Strict per deal-criteria.md |
| MT with favorable existing loan | ✅ Tier MT | BBC CF already at existing-loan terms |
| **Off-market MT (removed listings)** | ❌ **GAP** | We only query `market_status: 'Active'` — Richard's $9K MT example was on a REMOVED listing |
| **Hybrid SF+MT** | ⚠️ Partial | Falls into MT bucket; no dedicated Hybrid tier yet |
| **Condo SF (Pitch 3)** | ❌ Filtered | We blanket-exclude condos per MT L1095; misses Richard's occasional condo SF |
| **Sub-$200K MFH SF** | ❌ Filtered | Tier A floor is $200K; small MFH below this falls to REJECT |
| REO / auction listings | ✅ Filtered | Detect via agent name "Auction.com" / "Williams &" / "REO" |
| Manufactured / mobile homes | ✅ Filtered | NON_RESIDENTIAL_TYPES |
| New construction / planned dev | ✅ Filtered | sqft==0 OR yearBuilt > current year |

## Identified gaps to address

1. **Off-market MT search** — add a second pass with `market_status: 'Off Market'` filtered to MT deal_type only. This is where Richard's $9K MT examples live.
2. **Hybrid tier** — when a property has both BBC's MT calc (existing favorable loan) AND positive SF creative_cf at +20% premium, surface a "Hybrid" pitch option.
3. **Condo SF exception** — allow Tier A condo if: (a) MT play OR (b) underwater seller (price < balance) per MT L1108. Default-exclude with override path.
4. **Sub-$200K MFH SF** — consider lowering Tier A floor to $150K with the "not retail-desirable" gate.
