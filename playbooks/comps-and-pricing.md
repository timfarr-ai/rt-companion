# Comps & Pricing — Validate Price + Rent BEFORE You Offer

## ⚠ Read this first — what the dashboard comps buttons actually are

The comps controls on every card — **`Sold comps ↗`**, **`📊 Comps (Propwire) ↗`**, and the **🏠 Rent / 💳 PITI / 💰 Tax** pills — are a **link-launcher, not a validator.** They open a pre-filtered Zillow Sold search, open Propwire with the address copied to your clipboard, and re-display **BBC's own** rent/PITI/tax numbers. **Nothing is computed or checked for reasonableness.**

> The dashboard launches the tools. **You** make the judgment. The ritual below IS the validation — that's why a number on a card alone shouldn't make you confident.

Source: triage.py render_deal (Sold-comps URL builder + Propwire link + BBC pills)

---

## Rule zero — which comp matters depends on the deal type

Doing the wrong comp work for the deal is the #1 confidence-killer. Decide this first:

| Deal | Lives or dies on | Does asking price matter? |
|---|---|---|
| **Tier A / B — Seller Finance** | **RENT** (CF = rent × 0.80 − PITI) | **Less** — you knowingly pay +10–20% over market in exchange for 0% terms. Rent is what makes the deal real. |
| **Tier C / Fix & Flip — Cash** | **ARV from SOLD comps** (70% rule) | **Everything** — your offer = a % of value, not of list. |
| **Mortgage Takeover / Hybrid** | ARV (to size real equity = price − loan balance) **+** rent (assumed-loan CF) | Need ARV to know if the equity gap is real. |

**If you remember one thing: SF deals live or die on RENT. Cash/FF deals live or die on ARV.**

---

## RITUAL 1 — Rent comp (every SF / Tier B / MT deal) — ~30 sec

**Richard's method & source (verbatim):** read the Zillow rent, then **discount the asking rent to the real average.**

> *"They're asking 1,700. Doesn't mean they're getting 1,700. I bet it's on average maybe $1,400 — you have a tenant from the past still paying $950, a new one at $1,700, a handful at $1,300… averages out to 1,400."*
> 🎬 **Watch him do it:** [Seller Finance Course @ 20:40 ↗](https://www.youtube.com/watch?v=WXVfSBu-bAc&t=1240s)

For Section 8 / cheap-SFH rent his source is the **Section 8 Fair Market Rent site** → state → county → ZIP → **bedroom count** (more beds = materially more rent), and he assumes they lowball:

> *"they kind of like to lowball us… you will be making more than normal rent with section 8."*
> 🎬 **Watch him build the rent comp:** [Cash Course @ 27:20 ↗](https://www.youtube.com/watch?v=KGXI134QiaM&t=1640s)

**Steps:**

- [ ] Tap the **Zillow** link on the card → read the **Rent Zestimate**.
- [ ] Compare to the card's **🏠 Rent** pill (BBC's number). **If they disagree by >20%, the LOWER one wins** (Richard's "asking ≠ getting" rule).
- [ ] Section 8 estimates online are *"sometimes exaggerated or inflated"* (quiz) — **haircut them.**
- [ ] If Zillow rent is null / zero / outlier → run a **Rentometer** check. *(Rentometer is our tech-stack fallback for missing data — NOT Richard's method; he only uses Zillow + the Section 8 site.)*
- [ ] Re-run the gut check: **CF = (chosen rent × 0.80) − PITI.** If that goes negative or thin, the listing rent was carrying a bad deal → kill or re-tier.

Source: Seller Finance Course L604–618 ("asking ≠ getting") | Cash Course L757–775 (Section 8 site, lowball) | quiz-cash L274–277 (online estimates inflated)

---

## RITUAL 2 — Value / ARV comp (every Cash / FF / MT / Hybrid deal) — ~60 sec

**Richard's gold-standard checklist — Cash Course L716–895:**

> *"You can list a property for any price… **Doesn't mean it's worth that price. Sales mean it's worth that price. So let's click on sold.**"*
> 🎬 **Watch him build the valuation comp:** [Cash Course @ 26:10 ↗](https://www.youtube.com/watch?v=KGXI134QiaM&t=1570s)

**Steps, in his order:**

- [ ] **Click SOLD on Zillow** — never trust active list prices. The card's `Sold comps ↗` link already pre-filters: sold ≤180 days, beds ±1, sqft ±20%, type-matched.
- [ ] **Draw a tight radius** around the subject. *"the closer the better… literally my neighbor's house, a block and a half away — that's a comp."*
- [ ] **Match the property type** — duplex ≠ quadplex (*"definitely not what we are"*).
- [ ] **Year built within 10 years, 15 max.** *"You got a comp within 10 years, 15 years max."*
- [ ] **Adjust for beds / baths / sqft + condition.** A retail-finish flip sells higher than your investor product — don't comp your as-is duplex to a renovated owner-occupant home.
- [ ] **Triangulate — it's not exact.** *"Just not an exact science, guys."* Bracket it: *"you've got a 170k sale and a 180k sale and a plethora of 120s, and we're bigger than the 120s with more beds — hence 140 is what I think my ARV is."*
- [ ] **Cross-check owner / equity + a second comp set in Propwire** (the `📊 Comps (Propwire)` link copies the address — paste it). Use it to confirm ARV before any cash/FF offer.

**Then apply the rule:**

- Cash opening offer ≈ **70% of list** (loose anchor; the 70% rule is the **CEILING** — offer below it).
- Deal grades: **60% of value = excellent · 70% = good · 90% = weak/pass.**
- Fix & Flip go/no-go: **ARV − purchase − rehab = profit.** Need a real spread (good-deal examples clear ~$35–50K profit on ~$140–200K ARV; ~$10K profit = bad).

Source: Cash Course L716–895 (sold-comp walkthrough + ARV triangulation) | quiz-cash L283–295, L500–501 (70/60/90 grades) | fix-and-flip-cash.html (70% = ceiling)

---

## The 60-second pre-offer checklist (paste into the deal note)

```
DEAL: ____________________   TIER: A / B / C / FF / MT / HY
[ ] Pulled SOLD comps on Zillow (not active) — radius tight, type match, yr ±15
[ ] ARV estimate (triangulated): $______  | List: $______  | List ÷ ARV = ____%
[ ] Rent: Zillow Zestimate $______ vs BBC $______ → chosen (lower if >20% gap): $______
[ ] Section 8 / Rentometer cross-check if rent was null/outlier
[ ] CF = (rent × 0.80) − PITI = $______/mo   → still qualifies? Y / N
[ ] Propwire: owner equity / liens checked (MT / HY / Cash)
[ ] Offer math: SF = asking +10–20% terms | Cash ≈ 70% list | FF = ARV − rehab − profit
VERDICT: PROCEED / COUNTER / KILL     (it's not exact — bracket it)
```

---

## Honest framing — say it to yourself every time

The dashboard **launches the tools**; it does not validate price. The rituals above are the validation. Richard himself calls ARV *"not an exact science"* — your confidence comes from running the **sold-comp + rent-haircut ritual every time**, not from a single number on a card.
