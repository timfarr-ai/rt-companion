# Seller Finance — Offer Email Template (LAUNCH CANON)

Source of truth for the Offer Oven's "Generate Offer Email" when **otype = Seller Finance**.
Derived from the 13112 Canonbury St deal (bedded down 2026-06-17) + the canonical HMHW
seller-finance deck. Tokens in `{{ }}`. Optional intel uses Mustache-style conditionals
`{{#token}}…{{/token}}` — the block renders only if that token has a value, so the same
template works with full competing-offer intel (Canonbury) or cold (no intel).

---

## Template

```
Subject: Full-price offer (and then some) — {{address}}

Hi {{agent}},

Thanks for your time on the phone — here's my offer in writing.

I'd love to buy this the conventional way, and I'm sure your seller would prefer a clean sale
— but {{#dom}}after {{dom}} on the market{{/dom}}{{^dom}}given how long it's been listed{{/dom}}, we both know that
route isn't landing. There's a structural reason. An investment property only makes sense if
it cash flows, and at this rent it won't support a loan much above {{dscrValue}}. So financing
fails above that{{#fellThrough}} — you saw the {{fellThrough}} offer fall through{{/fellThrough}}.
And cash won't reach your number either: a cash buyer can earn 10%+ in the stock market, so
they'll only buy at a discount steep enough to beat it{{#cashLevel}}, which is why offers are
stuck around {{cashLevel}}{{/cashLevel}}. Either way your client loses equity — it's structural,
not bad luck.

That's why I'm proposing seller financing — not my first choice either, but the only structure
that works here. You're paid your full commission out of my down payment. Your client gets
their full equity — above asking — and defers the tax hit. The premium I pay over list is
their return, and the monthly payment is the lion's share of what the property nets after
taxes, insurance and upkeep. I cover every other closing cost too, and at year {{balloonYrs}}
I refinance or sell them out of the balance.

And your client carries no risk. A deed of trust protects them throughout — miss 60 days and
the property reverts to them, keeping every payment made, no foreclosure. They're not a
landlord either: no tenants, no repairs, no vacancy — just paid like the bank, every month,
occupied or not.

  - Price:      {{price}}
  - Down:       {{down}}
  - Payment:    {{payment}}/month
  - Balloon:    ~{{balloonAmt}} at year {{balloonYrs}}
  - EMD:        {{emd}} non-refundable, submitted after inspection
  - Inspection: {{inspectionDays}} business days
  - COE:        on or before {{coeDays}} days
  - Security:   deed of trust

My proof of funds is attached, I can close fast, and no appraisal is needed. I have
flexibility in the terms depending on your seller's needs.

Regards,
{{you}}
```

---

## Merge fields

| Token | Source | Default |
|---|---|---|
| `{{address}}` | Property section (identity) | — (required) |
| `{{agent}}` | optional color input | `there` |
| `{{dom}}` | optional input (e.g. `120 days`) | falls back to "given how long it's been listed" |
| `{{dscrValue}}` | input / calc-suggested (value the rent supports) | — (required) |
| `{{fellThrough}}` | optional color input (e.g. `$75K`) | *(block hidden)* |
| `{{cashLevel}}` | optional color input (e.g. `$65K`) | *(block hidden)* |
| `{{price}}` | calc | — |
| `{{down}}` | calc | — |
| `{{payment}}` | calc (monthly to seller) | — |
| `{{balloonAmt}}` | calc (outstanding at balloon) | — |
| `{{balloonYrs}}` | calc (balloon term) | `7` |
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
