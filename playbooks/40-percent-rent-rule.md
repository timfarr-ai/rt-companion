# The 40%-of-Rent Rule — Richard's SF Pitch Anchor

## TL;DR

For every Seller Finance deal (Tier A + Tier B), the monthly payment to the seller = **40% of expected gross rent**. This is the verbatim formula Richard uses on live calls — it skips amortization-table math and anchors the conversation to rent reality.

## Verbatim source (live calls)

> *"10% over list, 10% down, 40% of of rent in monthly payments."* — [[c2hNH6u7D0k @ 2:27:52](https://youtu.be/c2hNH6u7D0k?t=8872)]

> *"I'll give you 80,000 on seller finance terms. So 80,000, 10% down, 40% of whatever it rents out for in monthly payments, 7-year term."* — [[c2hNH6u7D0k @ 1:11:34](https://youtu.be/c2hNH6u7D0k?t=4294)]

This is the single highest-value insight from validating the playbooks against 10 hours of Richard's actual live calls. Missing from every source document until 2026-05-16.

---

> **Where this fits in the timeline:** You say this number on Day 0 (the first call). See [pipeline-timeline.html](pipeline-timeline.html) for what happens next.


## Who pays whom

The 40% monthly payment is from the **END BUYER (the investor Tim assigns the contract to)** to the **SELLER**. Tim never makes those payments — he assigns the contract at closing and walks with the assignment fee.

```
   SELLER ──────────► TIM (contracted, then assigns) ──► END BUYER (investor)
      ▲                                                       │
      │                                                       │
      │  Monthly payment = 40% of rent × balloon years        │
      │  Plus: 10-12% down at close                           │
      │  Plus: balloon payoff at year 5 (Tier A) or 7 (Tier B)│
      └───────────────────────────────────────────────────────┘
```

## The economics

For a property with **$1,500/mo rent**, $80K offer, 10% down ($8K), 7-year balloon, 40% of rent:

| Party | Cash in | Cash out | Result |
|---|---|---|---|
| **Seller** | $8K down + $600/mo × 84mo + balloon at month 84 | — | $80K total (= $8K down + $50,400 monthly + $21,600 balloon) |
| **Tim** | $80K contract → assigns for $X fee | $0 ongoing | Exits at close with assignment fee |
| **End buyer** | $8K down + assignment fee + closing | $600/mo seller + ~$300/mo PITI + ~$300/mo reserves | Cash-flows ~$300/mo on $1,500 rent (~20% net CF) |

## The rent split — why 40%

```
Gross rent:                $1,500   100%
─────────────────────────────────────────
─ Payment to seller:       $600     40%   ← the 40% rule
─ End-buyer PITI (T+I):    $300     20%   ← property tax + insurance
─ Reserves:                $300     20%   ← CapEx 5% + Mgmt 5% + Vacancy 10%
─ End-buyer cash flow:     $300     20%   ← what's left = the deal's appeal
```

20% net cash flow is the design target. It gives the end-buyer investor a real return AND leaves Tim a margin to charge a meaningful assignment fee on the side.

## How to USE it on a call

```
Agent picks up.

You:    "Hi [name] — I was told that you were open to some seller financing.
         Is that the case?"

Agent:  "We're open to creative — what are you thinking?"

You:    "Beautiful. Here's what I do: [asking + 10%] purchase price, 10% down,
         and I pay your seller 40% of whatever it rents out for in monthly
         payments, 7-year term."

         (For the $80K example: "I'd give you 80,000 on seller-finance terms.
         8 grand down. 600 a month for 7 years. Balloon at year 7 for 21,600.")

Agent:  "How does that math work for your seller?"

You:    "Total they walk with over 7 years is exactly the asking price, just
         spread out. They get cash now, monthly income, and a final payoff
         when I refinance them out."
```

## What this REPLACES

The original playbooks derived monthly payment from a 30-year amortization at 0% interest:
- $72K loan ÷ 360 months = $200/mo (P&I only)

The amortization-based number is **structurally correct under traditional accounting**, but Richard never uses it on live calls. Why:

1. **It's too low to feel meaningful** to the seller — "$200/mo on a $80K sale" sounds like nothing
2. **It can't be computed in your head** while talking — you'd need a calculator
3. **It anchors to a 30-year term** the seller intuitively rejects ("I'll be dead before this pays off")

The 40%-of-rent number:
1. Anchors to the rent the seller already understands ("I'd get 40% of what this rents for — almost as good as renting it myself")
2. Is mental math — multiply rent × 0.4
3. With a 5-7yr balloon, the seller sees their full payoff inside their planning horizon

## When this DOESN'T apply

| Tier | 40% rule applies? | Why |
|---|---|---|
| **Tier A (MFH SF)** | ✅ Yes — primary | Same SF structure |
| **Tier B (Cheap SFH SF)** | ✅ Yes — verbatim verified | Detroit/Cleveland SFHs |
| **MT (Mortgage Takeover)** | ❌ No | You ASSUME existing P&I; no new monthly to create |
| **HY (Hybrid: MT + SF carry-back)** | ⚠ Partial | Carry-back portion only — see hybrid playbook |
| **FF (Fix & Flip)** | ❌ No | Cash purchase, no monthly |
| **C (Cash)** | ❌ No | Cash purchase, no monthly |

## On the briefing card

Every Tier A and Tier B card now shows the 40%-rule pitch line in the Creative Outcome section, with a rent-split visual:

```
💬 Richard's pitch (40% of rent rule)
   $80,000 · 10% down ($8,000) · $600/mo to seller · 7yr balloon ($21,600 residual)

   [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓]
    Seller $600   T+I $300    Reserves $300    Buyer CF $300

   Rent $1,500/mo split.
```

You read the number off the card, say it to the agent. Don't think — just say.

## Sanity checks before deploying

Use the **amortization check** (the existing `creative_terms` line) as a verification baseline. If the 40%-rule monthly looks WAY off from amortization (e.g., 10x bigger), the rent estimate is probably wrong. Cross-check Zillow Rent Zestimate before committing to a number on the call.

If rent estimate is missing or absurd (e.g., $1/mo or $50K/mo), the rule produces garbage — fall back to amortization-derived monthly.

## Source

- Live-call verbatim: [c2hNH6u7D0k @ 1:11:34](https://youtu.be/c2hNH6u7D0k?t=4294), [@ 2:27:52](https://youtu.be/c2hNH6u7D0k?t=8872)
- Validation report: [live-call-validation.html](live-call-validation.html)
- Tier playbooks where the rule applies: [Tier A](tier-a-mfh-seller-finance.html) · [Tier B](tier-b-cheap-sfh-stale.html)
