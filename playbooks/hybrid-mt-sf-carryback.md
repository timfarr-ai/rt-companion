# Call Playbook — Hybrid (Mortgage Takeover + SF Carry-back)

## Trigger / When to use this script

Hybrid is the play when the property has **BOTH** a favorable existing mortgage AND significant seller equity. Neither pure MT nor pure SF fits:

- **Pure MT fails** → Seller has too much equity to just take $5-10K cash and walk
- **Pure SF fails** → Why finance the whole price when there's already a 3% loan on it?

**Hybrid = assume the existing loan + carry back the equity gap on SF terms.**

### Triage criteria (auto-classified to HY tier)
- BBC tagged as `mortgageTakeover` (so loan data is available)
- Existing rate **≤ 5.5%** (favorable enough to assume)
- Existing balance **≥ $20K** (loan is meaningful)
- Seller equity (price − balance) **≥ $20K** (worth doing hybrid vs pure MT)
- DOM **≥ 60 days**, Creative CF **≥ $100/mo**

### Live recordings
- [Hybrid Pitch 1 - 1.85m Dollar AirBNB](https://bkmfdmlzkumnsytpztio.supabase.co/storage/v1/object/public/call-recordings/3d3cf27d-39be-4078-813b-1edb74d381da/1777608563442-3.mp3) (20:01)
- [Hybrid Pitch 2](https://bkmfdmlzkumnsytpztio.supabase.co/storage/v1/object/public/call-recordings/3d3cf27d-39be-4078-813b-1edb74d381da/1777608567085-4.mp3) (24:38)
- [Hybrid — Restructuring Seller Finance to Hybrid](https://bkmfdmlzkumnsytpztio.supabase.co/storage/v1/object/public/call-recordings/3d3cf27d-39be-4078-813b-1edb74d381da/1777608553277-0.mp3) (8:27)

---

## Pre-call checklist (60 seconds)

- [ ] **Briefing card open:** Note the 4 key numbers from the Hybrid banner — existing balance, existing rate, equity gap (carry-back amount), target carry-back monthly.
- [ ] **Verify on Zillow:** Confirm price, photos, agent name. PropStream optional for verifying existing loan if you have it.
- [ ] **Mental check:** "This seller can't take pure cash (they'd lose to the realtor 6%) and pure MT (they want money). Hybrid splits the difference."
- [ ] **Down payment range:** Plan $5-10K cash to seller at close (matches MT). Carry-back covers the rest of equity.
- [ ] **Rent estimate:** Hybrid's payment math = 40% of rent MINUS existing PITI. You need the rent number to compute the carry-back monthly.

---

## The opener — VOICEMAIL

Length target: ~30 sec. Don't lead with "hybrid" — lead with creative.

```
"Hi [agent], my name's [you]. I'm calling about [address]. I work with 
investors looking at creative deal structures — specifically I think 
this one might be a great fit. I noticed your seller has an existing 
loan they're probably paying down — I have a way to take this off their 
plate, take over their loan, and pay them out the equity over time so 
they're not eating realtor fees or capital-gains hits. I'd love to hop 
on a quick call. Talk soon."
```

Key elements:
- "Take over their loan" (MT side)
- "Pay them out the equity over time" (SF carry-back side)
- "Not eating realtor fees" (motivation hook for seller with equity)

---

## The opener — LIVE call

First 20 seconds:

```
You:    "Hi [agent], my name's [you]. I'm calling about [address]. I work 
         with investors on creative deal structures. Looking at this one, 
         I noticed your seller probably has an existing loan they're 
         paying down — what can you tell me about their situation? 
         Are they sitting on a low rate they got a few years back?"
```

If agent confirms favorable existing loan → you're in. Move to qualifying.

---

## Qualifying questions (in order)

1. **"Roughly what's the balance on their existing loan, and what rate are they paying?"** — Confirms BBC's data. If rate > 5.5% hybrid is less attractive; consider pivoting.
2. **"What's the seller's situation — what's driving the sale?"** — Listen for: relocation, DTI concerns, tired-landlord. These are hybrid-friendly motivators.
3. **"Has the property been rented? What's the rent?"** — Critical for the 40%-rule carry-back math.
4. **"How much do they need to walk away with at close?"** — Anchors the cash-to-seller portion. Aim for $5-10K.
5. **"Is the seller open to a structured deal where they receive monthly payments after closing?"** — Surfaces the carry-back concept softly.

---

## The pitch (the math)

After qualifying, present the structure:

```
"Here's what I'd propose. You guys are asking $[price]. Seller has about 
$[balance] left on their loan at [rate]% — that's a great rate, way better 
than anything I could get at the bank today. 

So here's the deal: [cash_to_seller] cash to your seller at closing. 
I assume the existing loan and keep making the payments — they're 
completely off the mortgage. The remaining equity, about $[carry_back_amount], 
I carry back to them on seller-finance terms: 
[carry_back_monthly]/mo for 7 years, balloon at year 7.

Total monthly cost to me ends up around 40% of what the property rents 
for, so it cash flows for me — and your seller walks with cash now, 
monthly income, and the full balloon payoff in 7 years. They get the 
full asking price, just spread over time. No realtor commission gap, 
no capital gains hit at once."
```

### Why the numbers work

```
Rent (e.g. $1,500/mo)
─ Existing PITI to bank:     $X    (set by their loan — favorable rate keeps this low)
─ Carry-back monthly to seller: $Y    (40% of rent − X — what's left of the "40% allocation")
─ Reserves:                  20% of rent
─ End-buyer CF:              remaining

Total "to seller side" = X + Y = 40% of rent (Richard's standard split)
```

The end-buyer pays the same total monthly payment as pure SF (40% of rent), but it's split between bank and seller. Seller benefits because they get cash at close AND monthly carry-back AND a balloon payoff.

---

## Top 5 objections + verbatim rebuttals

### 1. **"Due-on-sale clause — won't the bank call the loan?"**
- This is the classic MT objection. In practice the bank rarely calls performing loans (they got their rate locked).
- **Rebuttal:** *"Due-on-sale is a right the bank has, not an obligation. As long as the loan keeps performing — and I'll be paying it on time, that's the whole basis of my offer — they have no incentive to call it. I've never seen one called on a performing loan in my deals."*
- Optional escalation: structure the closing through a land trust to avoid even triggering the lender's awareness.

### 2. **"Why not just take cash?"**
- **Rebuttal:** *"Sure — let's compare. At [asking $X], your seller nets [asking − 6% realtor − closing − loan payoff] which is roughly [X − 0.06X − $balance]. That's [equity − 6%]. With my hybrid offer, they get [cash_to_seller] now, [monthly] every month for 7 years, and the [balloon] balloon at the end. Total over 7 years works out to the full asking, without the realtor cut. Plus they pay capital gains in installments instead of all at once."*

### 3. **"What if you stop paying the existing mortgage?"**
- Same as the MT version. Frame the equity-protection clause:
- *"If I miss payments for two months at any point, whether year one or year ten, the property reverts to your seller — they sign a document saying that's okay. They keep all my carry-back payments plus the property. I have zero incentive to default."*

### 4. **"My seller wants more cash at close."**
- This is where hybrid is FLEXIBLE. Negotiate the cash-to-seller portion higher, offset by reducing the carry-back balloon:
- *"What if I bump the cash at close to [higher amount] and trim the balloon to [lower amount]? Same total over the term."*

### 5. **"This is complicated. My seller won't understand it."**
- **Rebuttal:** *"It really comes down to three numbers: cash now, monthly income, balloon at year 7. Just like a rental — except they don't have to manage it, and the property is off their books. I can put it all in writing and send a summary they can show their attorney."*
- Then offer: *"If you want, I'll send a one-page summary right now so you can walk them through it."*

---

## The close — verbal yes

What counts as a verbal yes that progresses to contract:

- Agent says some version of: *"Let me run this by my seller, but the structure makes sense."*
- Or seller (if you get them on the line): *"That actually sounds workable — send me the numbers."*

**Then immediately:** "Yeah is it cool if I text you the proposal right now? I'll send the breakdown — you can review with your seller tonight and call me back tomorrow." → Send the text within 60 seconds of ending the call.

---

## Success metric

A "good call" for Hybrid:
- Confirmed the existing loan terms verbally (rate + balance match what BBC said)
- Confirmed seller has some equity motivation (not just walking away with $0)
- Got permission to send the structured offer in writing
- Scheduled a callback within 24-48 hours

Time to verbal yes is typically longer than pure MT — seller takes a day to process the structure with their attorney. That's normal.

---

## Common mistakes to avoid

1. **Calling it "subject-to" or "hybrid" out loud** — Use "take over the loan + carry back the equity." Plain language beats jargon.
2. **Pitching before qualifying the existing rate** — If the loan is at 7%+, hybrid loses its edge. Always confirm rate first.
3. **Quoting the carry-back balloon as a single big number** — It feels scary. Break it down: "monthly income + final payoff."
4. **Forgetting reserves** — End-buyer's PITI + reserves + carry-back must equal 80% of rent max. If the math doesn't leave 20% CF, the deal won't sell to your end-buyer.
5. **Ignoring partner/co-decisionmaker** — Same as Tier B/SF: ask early. "Anyone else need to weigh in?"

---

## Sources

- Live recordings (linked above)
- Validation report: [Hybrid mentioned as partial coverage in MT validation](_live-call-validation.md)
- Tier classification logic: `triage.py` `tier()` function — HY tier (added 2026-05-16)
- Related: [40%-rent-rule explanation](40-percent-rent-rule.md), [Pure MT playbook](mortgage-takeover.html), [Pure SF Tier A](tier-a-mfh-seller-finance.html)
