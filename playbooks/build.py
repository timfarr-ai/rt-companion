#!/usr/bin/env python3
"""Convert per-strategy call-playbook markdown files into dashboard HTML pages
matching the existing SOP style. Run from the repo root or this dir."""
import re
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOKS = Path(__file__).resolve().parent

TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="robots" content="noindex, nofollow">
  <title>{TITLE} — RT Deal Desk</title>
  <style>
    :root {{
      --bg:#0e1217; --panel:#161b22; --panel-2:#1b212a; --border:#252b35;
      --text:#e3e9f0; --muted:#9aa6b3; --accent:#6cb6ff; --green:#5bd06a;
      --amber:#d6a542; --red:#f4776e; --script:#11161d;
    }}
    *{{box-sizing:border-box;}}
    html,body{{margin:0;padding:0;}}
    body{{background:var(--bg);color:var(--text);
      font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,sans-serif;
      font-size:17px;font-weight:400;line-height:1.68;-webkit-font-smoothing:antialiased;
      padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
      -webkit-text-size-adjust:100%;}}
    a{{color:var(--accent);text-decoration:none;}}
    a:active{{opacity:0.7;}}
    header{{position:sticky;top:0;background:rgba(14,18,23,0.9);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--border);padding:13px 18px;z-index:10;display:flex;align-items:center;justify-content:space-between;gap:12px;}}
    header h1{{margin:0;font-size:16px;font-weight:600;}}
    header .back{{font-size:14px;color:var(--accent);}}
    main{{padding:18px 18px 8px;max-width:680px;margin:0 auto;}}
    main h1{{display:none;}}
    /* H2 = section label (PROCESS / POLICY etc.) */
    main h2{{margin:36px 0 14px;font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:0.13em;}}
    /* H3 = STEP header — clear separation + breathing room */
    main h3{{margin:34px 0 14px;font-size:20px;font-weight:600;color:#fff;line-height:1.3;padding-top:22px;border-top:1px solid var(--border);}}
    main h3:first-of-type{{border-top:none;padding-top:4px;}}
    main p{{margin:13px 0;}}
    main ul,main ol{{margin:13px 0;padding-left:20px;}}
    main li{{margin-bottom:10px;}}
    main li input[type="checkbox"]{{margin-right:6px;}}
    main strong{{color:#fff;font-weight:600;}}
    main em{{color:var(--muted);font-style:normal;}}
    main hr{{border:0;border-top:1px solid var(--border);margin:30px 0;}}
    /* SCRIPT — words you say. Readable SANS, generous, green = "say this". */
    main blockquote{{margin:16px 0;padding:15px 18px;background:var(--script);border-left:3px solid var(--green);border-radius:10px;color:#eef4fb;font-size:17px;line-height:1.62;}}
    main blockquote p{{margin:9px 0;}}
    main blockquote p:first-child{{margin-top:0;}} main blockquote p:last-child{{margin-bottom:0;}}
    main blockquote strong{{color:#fff;}}
    main code{{background:var(--panel-2);padding:2px 7px;border-radius:5px;font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:14.5px;color:#9ed0ff;}}
    /* PRE = copy-paste templates (emails). Monospace block. */
    main pre{{background:var(--script);border:1px solid var(--border);border-radius:10px;padding:16px;overflow-x:auto;font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:13.5px;line-height:1.62;color:#cdd9e5;margin:16px 0;}}
    main pre code{{background:transparent;padding:0;color:inherit;font-size:13.5px;}}
    main table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:16px;}}
    main th,main td{{border:1px solid var(--border);padding:10px 13px;text-align:left;}}
    main th{{background:var(--panel-2);font-weight:600;color:var(--muted);font-size:14px;}}
    .strategy-pill{{display:inline-block;padding:4px 13px;border-radius:20px;font-size:12px;font-weight:600;margin-bottom:4px;}}
    .pill-a{{background:rgba(91,208,106,0.15);color:#5bd06a;}}
    .pill-b{{background:rgba(210,168,255,0.15);color:#d2a8ff;}}
    .pill-mt{{background:rgba(108,182,255,0.15);color:#6cb6ff;}}
    .pill-ff{{background:rgba(240,136,62,0.15);color:#f0883e;}}
    nav.bottom{{padding:28px 0 34px;text-align:center;color:var(--muted);font-size:13px;border-top:1px solid var(--border);margin-top:32px;}}
    nav.bottom a{{color:var(--muted);margin:0 10px;}}
    @media (min-width:720px){{main{{padding:30px 24px;max-width:720px;}}}}
  </style>
</head>
<body>
  <header>
    <a href="/rt-companion/" class="back">‹ Dashboard</a>
    <h1>{HEADER_TITLE}</h1>
    <a href="/rt-companion/briefings/latest.html" class="back" style="text-align:right;">📋 Briefing</a>
  </header>
  <main>
    <div class="strategy-pill {PILL_CLASS}">{STRATEGY_LABEL}</div>
    {BODY}
    <nav class="bottom">
      <a href="/rt-companion/">Dashboard</a> ·
      <a href="/rt-companion/briefings/latest.html">Today's Briefing</a> ·
      <a href="/rt-companion/playbooks/">All Playbooks</a>
    </nav>
  </main>
</body>
</html>
'''

FILES = [
    # The 5 canonical strategy SOPs (2026-06 rebuild — one source of truth per strategy)
    ('seller-finance',   'Seller Finance',             '🤑 Seller Finance',          'pill-a'),
    ('sub-to',           'Sub-To (Mortgage Takeover)', '🔑 Sub-To',                  'pill-mt'),
    ('hybrid',           'Hybrid',                     '🔀 Hybrid (medium equity)',  'pill-b'),
    ('fix-and-flip',     'Fix & Flip',                 '🔨 Fix & Flip',              'pill-ff'),
    ('cash-arbitrage',   'Cash Arbitrage / Section 8', '💵 Cash Arbitrage',          'pill-ff'),
    ('comps-and-pricing',         'Comps & Pricing',            '📊 Comps & Pricing — validate before offering', 'pill-ff'),
    ('pipeline-timeline',         'Pipeline Timeline',          '📅 Pipeline Timeline (day-by-day)', 'pill-mt'),
    ('risks',                     'Risks & Newbie Mistakes',    '⚠️ Risks & Newbie Mistakes', 'pill-ff'),
    ('_live-call-validation',     'Live-Call Validation Report', '🔬 Live-Call Validation (deltas)', 'pill-a'),
]

def main():
    md = markdown.Markdown(extensions=['extra', 'tables', 'sane_lists'])
    for slug, title, header_title, pill_class in FILES:
        src = PLAYBOOKS / f'{slug}.md'
        if not src.exists():
            print(f'  ✗ missing {src}')
            continue
        text = src.read_text()
        body_html = md.convert(text)
        # Render checkbox list items: `- [ ]` and `- [x]` → ☐ / ☑ glyphs (markdown
        # extension doesn't natively emit task-list checkboxes).
        body_html = re.sub(r'\[ \]', '☐', body_html)
        body_html = re.sub(r'\[x\]', '☑', body_html)
        md.reset()
        # Use slug-with-leading-underscore-stripped for the HTML output filename
        out_slug = slug.lstrip('_').replace('_', '-')
        if slug == '_live-call-validation':
            out_slug = 'live-call-validation'
        out = PLAYBOOKS / f'{out_slug}.html'
        out.write_text(TEMPLATE.format(
            TITLE=title,
            HEADER_TITLE=header_title.replace('🎯 ','').replace('🏘️ ','').replace('🔑 ','').replace('🔨 ','')[:34],
            STRATEGY_LABEL=header_title,
            PILL_CLASS=pill_class,
            BODY=body_html,
        ))
        print(f'  ✓ wrote {out.name} ({len(body_html):,} chars)')
    # Index page listing all four
    index_html = TEMPLATE.format(
        TITLE='Call Playbooks',
        HEADER_TITLE='Call Playbooks',
        STRATEGY_LABEL='📞 Per-Strategy Call Playbooks',
        PILL_CLASS='pill-a',
        BODY='''
        <p>Hyper-focused pre-call + call cheat sheets. Open one before a call block — each is ~1-2 pages, designed for execution not reading.</p>
        <ul style="list-style:none;padding-left:0;">
          <li style="margin-bottom:12px;"><a href="seller-finance.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #56d364;"><strong>🤑 Seller Finance</strong><br><span style="color:var(--muted);font-size:14px;">Free &amp; clear / HIGH equity. Checkmate (MFH) + Stale-SFH. +15%, 10% down, 40%-of-rent, 72mo balloon.</span></a></li>
          <li style="margin-bottom:12px;"><a href="sub-to.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #79c0ff;"><strong>🔑 Sub-To (Mortgage Takeover)</strong><br><span style="color:var(--muted);font-size:14px;">LOW equity / cornered. Take over the debt for $0-lump. Trojan Horse + Trust Acquisition. Exit: investor or live-in.</span></a></li>
          <li style="margin-bottom:12px;"><a href="hybrid.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #c971ff;"><strong>🔀 Hybrid</strong><br><span style="color:var(--muted);font-size:14px;">MEDIUM equity. Assume the loan + carry the equity as a note (negotiated monthly, NOT 40%-of-rent).</span></a></li>
          <li style="margin-bottom:12px;"><a href="fix-and-flip.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #f0883e;"><strong>🔨 Fix &amp; Flip</strong><br><span style="color:var(--muted);font-size:14px;">Cash, distressed. MAO = ARV×0.70 − rehab − fee (70% is the ceiling). $30-50K below list.</span></a></li>
          <li style="margin-bottom:12px;"><a href="cash-arbitrage.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #e3b341;"><strong>💵 Cash Arbitrage / Section 8</strong><br><span style="color:var(--muted);font-size:14px;">Already cash-flows. Section 8 (govt rent ~30% above market) + DSCR buyer. Cash at a discount.</span></a></li>
          <li style="margin-bottom:12px;"><a href="comps-and-pricing.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #f0883e;"><strong>📊 Comps &amp; Pricing — validate before offering</strong><br><span style="color:var(--muted);font-size:14px;">The buttons launch tools, they don't validate. Richard's rent-haircut + sold-comp ARV ritual. SF=rent-led, cash=ARV-led.</span></a></li>
          <li style="margin-bottom:12px;"><a href="video-call-moments.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #e3b341;"><strong>⏱ Call Moments — jump-to index for 4 livestreams</strong><br><span style="color:var(--muted);font-size:14px;">81 segments + 36 🔥 highlights with clickable YouTube timestamps. Skip 7.4 hrs of dead air.</span></a></li>
          <li style="margin-bottom:12px;"><a href="study-library.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #e3b341;"><strong>📺 Study Library — Richard's calls ranked</strong><br><span style="color:var(--muted);font-size:14px;">3 YouTube courses + 20 curated MP3s/MP4s + 14 livestreams (~200hrs).</span></a></li>
          <li style="margin-bottom:12px;"><a href="pipeline-timeline.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #79c0ff;"><strong>📅 Pipeline Timeline</strong><br><span style="color:var(--muted);font-size:14px;">Day-by-day per strategy — first call to close. Set seller expectations, manage Airtable status transitions.</span></a></li>
          <li style="margin-bottom:12px;"><a href="risks.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #f85149;"><strong>⚠️ Risks & Newbie Mistakes</strong><br><span style="color:var(--muted);font-size:14px;">37 documented failure modes — pre-call, during-call, contract, dispo, legal. Skim before your call block.</span></a></li>
          <li style="margin-bottom:12px;"><a href="live-call-validation.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #f0883e;"><strong>🔬 Live-Call Validation Report</strong><br><span style="color:var(--muted);font-size:14px;">Playbook claims tested against 10hrs of Richard's actual live calls. Deltas + clickable YouTube timestamps.</span></a></li>
        </ul>
        ''',
    )
    (PLAYBOOKS / 'index.html').write_text(index_html)
    print(f'  ✓ wrote index.html')

if __name__ == '__main__':
    main()
