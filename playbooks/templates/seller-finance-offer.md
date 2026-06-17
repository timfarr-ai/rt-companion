# Seller Finance — Offer Email Template (LAUNCH CANON)

Source of truth for the Offer Oven's "Generate Offer Email" when **otype = Seller Finance**.
Derived from the 13112 Canonbury St deal (bedded down 2026-06-17) + the canonical HMHW
seller-finance deck. Tokens in `{{ }}`. Optional intel uses Mustache-style conditionals
`{{#token}}…{{/token}}` — the block renders only if that token has a value, so the same
template works with full competing-offer intel (Canonbury) or cold (no intel).

---

## Template

```
Subject: Full-price offer (and then some) on {{address}}

Hi {{agent}},

Thanks for your time on the phone. Here's my offer in writing. I have flexibility in the terms
depending on your seller's needs{{#portfolio}}, and the means to take down multiple properties from
your seller's portfolio, but let's strike terms on this one first{{/portfolio}}.

  - Price:      {{price}}
  - Down:       {{down}}
  - Payment:    {{payment}}/month
  - Balloon:    ~{{balloonAmt}} at month {{balloonMonths}}
  - EMD:        {{emd}} non-refundable, submitted after inspection
  - Inspection: {{inspectionDays}} business days
  - COE:        on or before {{coeDays}} days
  - Security:   deed of trust / quit claim deed

My proof of funds is attached, I can close fast, and no appraisal is needed.

Here's the reasoning, so you can walk your seller through it:

I'd love to buy this the conventional way, and I'm sure your seller would prefer a clean sale.
But {{#dom}}after {{dom}} on the market{{/dom}}{{^dom}}given how long it's been listed{{/dom}}, we both know that
route isn't landing. There's a structural reason: an investment property only makes sense if it
cash flows, and at this rent it won't support a loan much above {{dscrValue}}.

So financing fails above that{{#fellThrough}}, which is why the {{fellThrough}} offer fell through{{/fellThrough}}.
And cash won't reach your number either: a cash buyer can earn 10%+ in the stock market, so
they'll only buy at a discount steep enough to beat it{{#cashLevel}}, which is why offers are
stuck around {{cashLevel}}{{/cashLevel}}. Either way your client loses equity. It's a structural
problem, with interest rates the highest they've been in 25 years.

That's why I'm proposing seller financing. It's not my first choice either, but it's the only
structure that works here. You're paid your full commission out of my down payment, and your
client gets their full equity, above asking, while deferring the tax hit. The premium I pay over
list is their return, and the monthly payment is the lion's share of what the property nets after
taxes, insurance and upkeep. I cover every other closing cost too.

At the end of the term I refinance or sell them out of the balance. I set that term deliberately:
the property needs time to appreciate so I can refinance and pay your client in full. A shorter
balloon would risk leaving them short. And your client carries no risk. A deed of trust protects
them throughout: if I miss 60 days the property reverts to them, and they keep every payment
made, with no foreclosure.

They cease to be the landlord: no tenants, no repairs, no vacancy. Just paid like the bank, every
month, occupied or not.

Regards,
{{you}}
```

---

## Merge fields

| Token | Source | Default |
|---|---|---|
| `{{address}}` | Property section (identity) | — (required) |
| `{{agent}}` | optional color input | `there` |
| `{{portfolio}}` | optional flag — seller owns multiple properties | *(block hidden)* |
| `{{dom}}` | optional input (e.g. `120 days`) | falls back to "given how long it's been listed" |
| `{{dscrValue}}` | input / calc-suggested (value the rent supports) | — (required) |
| `{{fellThrough}}` | optional color input (e.g. `$75K`) | *(block hidden)* |
| `{{cashLevel}}` | optional color input (e.g. `$65K`) | *(block hidden)* |
| `{{price}}` | calc | — |
| `{{down}}` | calc | — |
| `{{payment}}` | calc (monthly to seller) | — |
| `{{balloonAmt}}` | calc (outstanding at balloon) | — |
| `{{balloonMonths}}` | calc (balloon term, in months) | `72` |
| `{{emd}}` | calc: `max(1000, round(price·1%))` | ~1% of price, floor $1,000 |
| `{{inspectionDays}}` | constant (contract §1.10) | `7` |
| `{{coeDays}}` | constant | `30` |
| `{{you}}` | your-signature setting | — |

Defaults backed by the creative PSA (§1.10 inspection = 7 business days; §1.5 EMD ≈ 1%
submitted after inspection) and the SF deck.

---

## Renders

**Full-intel (Canonbury):** `agent=there`, `dscrValue=~$65K`, `fellThrough=$75K`, `cashLevel=$65K`
→ "…doesn't support a loan much above ~$65K. So financing fails above that (you saw the $75K
offer fall through), and cash won't reach your number either … hence the offers stuck around $65K."

**Cold (no competing-offer intel):** `fellThrough`/`cashLevel` empty
→ "…doesn't support a loan much above ~$65K. So financing fails above that, and cash won't
reach your number either: a cash buyer can earn 10%+ in the stock market, so they only buy
here at a discount that beats it. Either way, your client gives up equity. It's structural,
not bad luck."

---

## Open decision (EMD)

Template default is **1% of price, floor $1,000** (matches PSA §1.5 ≈ $900 and scales with
deal size). For Canonbury (~$85K) that renders **$1,000**. The current Canonbury draft shows
**$1,500** — confirm which to lock and the renders/deal file align to it.
