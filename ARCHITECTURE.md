# RT Companion — Architecture (rethink, 2026-06-17)

> **STATUS: PARKED — revisit after the first sale.** Git-as-deal-store is the known ceiling,
> but the rebuild is deferred until a closed deal proves the playbook. Current static
> tooling (triage call sheet + locked templates) is sufficient to make and work offers.

## The core loop (MVP)

**An offer = address + numbers → strategy + terms → offer email → saved deal record.**

Everything below serves that one loop. To make an offer you need an **address** and the
**numbers**; the system picks/uses the **strategy**, computes the **terms**, renders the
**email**, and stores it as a **living deal record** you can reopen to negotiate.

---

## The one rule that drives the rebuild

**Deal data → database. Code & templates → git.**

- *Living, mutable, per-property records* (offer state, status, notes) do **not** belong in
  git markdown — that's why bedding down one email cost ~15 commits. They go in a database you
  edit in place.
- *Versioned artifacts* (Worker, app, triage.py, SOPs, the offer-email templates) stay in git.

This is not "git vs database." It's **data in the DB, code in git** — each tool doing what
it's good at.

---

## Three layers

```
  FEEDERS                 APP (static SPA, git)           API (Worker, git)        DATA (Airtable)
  ───────                 ────────────────────            ─────────────────        ──────────────
  Triage  ─┐                                          ┌─ GET  /deal?address  ─┐
  Manual  ─┼──▶  Offer Oven / "Deal Workspace"  ◀────▶┤  POST /deal (upsert)  ├──▶  Deals table
  Recall  ─┘     address+numbers→strategy→calc        │  GET  /deals          │     (1 row / property)
                 →email→save/recall                   └─ /bbc /openphone ─────┘
```

1. **Data = Airtable `Deals` table** — single source of truth for deal records. Already in
   use (Deal Flow + Track button); it ships a grid/kanban/forms UI for free. Right-sized for a
   solo desk. Upgrade path = Cloudflare D1 *only if* volume/queries ever outgrow it.
2. **API = Cloudflare Worker** (exists) — the only thing that touches Airtable. Holds secrets,
   HMAC-signed like the BBC relay. Browser never sees a token.
3. **App = the Offer Oven, evolved into the Deal Workspace** — static SPA served from git
   (Cloudflare Pages). Talks only to the Worker. Stays lightweight (no heavy framework /
   build step unless we outgrow it).

**Feeders** all land in the same store: triage writes lead stubs, manual entry creates rows,
recall reopens them. No matter the origin, one property = one row.

---

## Data model — Airtable `Deals` (one row per property)

| Group | Fields |
|---|---|
| Identity | **Address** (primary key, normalized) · Agent Name · Agent Phone · BBC PID (opt) · Source (Triage/Manual/Recall) |
| Pipeline | Status (Lead→Contacted→Offer Sent→Negotiating→Accepted→Contract→Paid→Dead) · Strategy (SF/Sub-To/Hybrid/Cash/F&F) · Created · Last Updated |
| Numbers | List Price · Offer Price · Rent · Down · Monthly Payment · Balloon Amount · Balloon Years · EMD · Inspection Days · COE Days · Taxes · Insurance · Rehab · Assignment |
| Loan (Sub-To/Hybrid) | Loan Balance · Loan Rate · Loan Payment |
| Intel | DSCR Value · Competing Cash · Fell-Through Offer · Notes (negotiation log) |
| Generated | Offer Email · **Offer Oven Link** (encoded state for one-click recall) |

`Track Deal` (triage) and the Oven's `Save` both **upsert this same row by Address** — Track
creates the stub, the Oven enriches it. No duplicates.

---

## What gets retired vs kept

- **Retire:** `deals/*.md` (deal docs) and any per-deal generated HTML. Canonbury becomes a
  *row*, not a document.
- **Keep in git:** the Worker, the app, `triage.py`, the SOPs, and the tokenized offer
  templates (`playbooks/templates/*`). These are code/content — versioning is correct here.

---

## Build sequence

1. **Airtable `Deals` schema** — create the table/fields above (can do via MCP now).
2. **Worker API** — `GET /deal?address`, `POST /deal` (upsert), `GET /deals`; HMAC-secured.
   Converge the existing Track `/pipeline` onto the same upsert.
3. **Deal Workspace** — evolve the calculator: Property (address+identity) → Numbers (by
   strategy) → Result (terms+verdict) → Offer (generate email from templates) → Save/Recall
   (read/write via Worker, lookup-on-open by address).
4. **Wire feeders** — triage cards link to the Workspace (`?address=`); lookup flags
   already-tracked properties.
5. **Migrate Canonbury** as the first row; retire its markdown.

Deferred (parked): listing-capture bookmarklet (Zillow `__NEXT_DATA__`, PropStream DOM),
RentCast address enrichment. Revisit once the DB loop is real — address + numbers is enough
to make an offer today.
