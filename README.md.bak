# rt-companion

Operator dashboard for the Richard Taylor / HMHW creative-finance deal desk.

**Live site:** https://timfarr-ai.github.io/rt-companion/

## What this is

A phone-first dashboard rendering Tim's HMHW skill content into a single coherent surface:

- **Strategy playbooks** — one page per play (Tier A / B / C / Objections / Contract) with TL;DR, when-to-use, step-by-step how-to, scripts (copy buttons), reference audio (Richard's actual recordings), and links to sources
- **Daily briefing** — published by the cloud routine at 8am AEST weekdays
- **Buyer one-pagers** — per-deal HTML pages with unguessable URLs for sharing with out-of-network buyers

Read-only intentionally. All content is generated from local skill markdown + `data/strategies.yaml`.

## Architecture

```
~/.claude/skills/richard-taylor-underwrite/references/*.md   ← source of truth (Tim's Mac)
                          │
                          ▼
              data/strategies.yaml      ← structure (this repo)
                          │
                          ▼
                     publish.py
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
   strategy/*.html               briefings/latest.html
   index.html                    (cloud routine writes daily)
```

Cloud routine `trig_01DXdZ22PfZsyJjmTkiWPanC` commits the daily briefing to `briefings/YYYY-MM-DD.html` via the GitHub Contents API, using a fine-grained PAT scoped to this repo.

## How to update content

### Edit a strategy script
1. Edit `~/.claude/skills/richard-taylor-underwrite/references/outreach-scripts.md` on Mac
2. Run from Claude Code: `publish dashboard` (or directly: `python ~/Code/rt-companion/publish.py`)
3. Dashboard rebuilds in ~30-60 seconds

### Edit a strategy's structure (when, how-to, sources)
1. Edit `~/Code/rt-companion/data/strategies.yaml`
2. Run `python publish.py`

### Generate a buyer one-pager
1. In Claude Code on Mac: `generate buyer one-pager for [address]`
2. The Dispo Agent fills `templates/buyer-summary.html.j2` and commits to `deals/[slug]-[nonce].html`
3. URL returned for DM-sharing to out-of-network buyers

## Local setup

```bash
cd ~/Code/rt-companion
pip install -r requirements.txt
python publish.py --no-push   # build only, no commit
python publish.py             # build + commit + push to GitHub Pages
```

Python 3.10+. No Node, no build pipeline.

## Privacy

- No PII in the dashboard (no agent contact info, no seller motivation, no buyer list)
- Addresses + financial calcs are derivable from public MLS data
- Buyer one-pagers use 12-char nonces in URLs — unguessable in practice
- If a future feature adds sensitive content, gate with Cloudflare Access then

## PAT rotation

The `RT_COMPANION_PAT` for the cloud routine is a fine-grained GitHub PAT scoped to this repo only, `Contents: Read+Write`, 1-year expiry. **Rotate annually.**

## Out of scope (intentionally not built)

See [`/Users/timfarr/.claude/plans/new-project-create-hashed-patterson.md`](plan) — the dashboard does NOT rebuild what BBC, hmhw.group, or claude.ai already provide.
