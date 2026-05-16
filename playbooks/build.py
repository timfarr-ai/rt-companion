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
      --bg:#0d1117; --panel:#161b22; --panel-2:#1c2128; --border:#30363d;
      --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --green:#56d364;
      --amber:#d29922; --red:#f85149; --gold:#e3b341;
    }}
    *{{box-sizing:border-box;}}
    html,body{{margin:0;padding:0;}}
    body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,sans-serif;font-size:16px;line-height:1.55;padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);-webkit-text-size-adjust:100%;}}
    a{{color:var(--accent);text-decoration:none;}}
    a:active{{opacity:0.7;}}
    header{{position:sticky;top:0;background:rgba(13,17,23,0.95);backdrop-filter:saturate(180%) blur(10px);-webkit-backdrop-filter:saturate(180%) blur(10px);border-bottom:1px solid var(--border);padding:14px 16px;z-index:10;display:flex;align-items:center;justify-content:space-between;gap:12px;}}
    header h1{{margin:0;font-size:17px;font-weight:600;}}
    header .back{{font-size:14px;color:var(--accent);}}
    main{{padding:14px;max-width:760px;margin:0 auto;}}
    main h1{{display:none;}}
    /* H2 = section header — boxed panel start */
    main h2{{margin:18px 0 10px;font-size:13px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;border-bottom:1px solid var(--border);padding-bottom:8px;}}
    main h3{{margin:14px 0 6px;font-size:15px;font-weight:600;color:var(--text);}}
    main p{{margin:8px 0;}}
    main ul,main ol{{margin:8px 0;padding-left:22px;}}
    main li{{margin-bottom:6px;}}
    main li input[type="checkbox"]{{margin-right:6px;}}
    main strong{{color:var(--text);font-weight:600;}}
    main em{{color:var(--muted);font-style:normal;}}
    main hr{{border:0;border-top:1px solid var(--border);margin:24px 0;}}
    main blockquote{{margin:10px 0;padding:10px 14px;background:var(--panel-2);border-left:3px solid var(--accent);border-radius:6px;color:var(--text);font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:14px;line-height:1.5;white-space:pre-wrap;}}
    main code{{background:var(--panel-2);padding:1px 6px;border-radius:4px;font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:13.5px;color:var(--accent);}}
    main pre{{background:#0b0f15;border:1px solid var(--border);border-radius:8px;padding:12px;overflow-x:auto;font-size:13px;line-height:1.5;}}
    main pre code{{background:transparent;padding:0;color:var(--text);}}
    main table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:14px;}}
    main th,main td{{border:1px solid var(--border);padding:6px 10px;text-align:left;}}
    main th{{background:var(--panel-2);font-weight:600;}}
    /* Source-call refs styled */
    .strategy-pill{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;margin-bottom:8px;}}
    .pill-a{{background:rgba(255,123,114,0.15);color:#ff7b72;}}
    .pill-b{{background:rgba(210,168,255,0.15);color:#d2a8ff;}}
    .pill-mt{{background:rgba(121,192,255,0.15);color:#79c0ff;}}
    .pill-ff{{background:rgba(240,136,62,0.15);color:#f0883e;}}
    nav.bottom{{padding:18px 0 24px;text-align:center;color:var(--muted);font-size:13px;}}
    nav.bottom a{{color:var(--muted);margin:0 10px;}}
    @media (min-width:720px){{body{{font-size:17px;}}main{{padding:24px;max-width:860px;}}}}
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
    ('tier-a-mfh-seller-finance', 'Tier A MFH Seller Finance', '🎯 Tier A — Multifamily SF', 'pill-a'),
    ('tier-b-cheap-sfh-stale',   'Tier B Cheap SFH Stale',    '🏘️ Tier B — Cheap SFH SF',  'pill-b'),
    ('mortgage-takeover',         'Mortgage Takeover',         '🔑 Mortgage Takeover',       'pill-mt'),
    ('fix-and-flip-cash',         'Fix & Flip / Cash',          '🔨 Fix & Flip / Cash',       'pill-ff'),
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
          <li style="margin-bottom:12px;"><a href="tier-a-mfh-seller-finance.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #ff7b72;"><strong>🎯 Tier A — Multifamily SF</strong><br><span style="color:var(--muted);font-size:14px;">The Checkmate Pitch — DSCR fails, you're the only path.</span></a></li>
          <li style="margin-bottom:12px;"><a href="tier-b-cheap-sfh-stale.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #d2a8ff;"><strong>🏘️ Tier B — Cheap SFH SF</strong><br><span style="color:var(--muted);font-size:14px;">Stale &lt;$150K SFH — 20% over-asking, 12-14% down.</span></a></li>
          <li style="margin-bottom:12px;"><a href="mortgage-takeover.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #79c0ff;"><strong>🔑 Mortgage Takeover</strong><br><span style="color:var(--muted);font-size:14px;">"Get OUT not PAID" — assume the favorable existing loan.</span></a></li>
          <li style="margin-bottom:12px;"><a href="fix-and-flip-cash.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #f0883e;"><strong>🔨 Fix &amp; Flip / Cash</strong><br><span style="color:var(--muted);font-size:14px;">70% rule. Fast cash, no negotiation, win on purchase price.</span></a></li>
          <li style="margin-bottom:12px;margin-top:18px;"><a href="study-library.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #e3b341;"><strong>📺 Study Library — Richard's calls ranked</strong><br><span style="color:var(--muted);font-size:14px;">3 YouTube courses + 20 curated MP3s/MP4s + 14 livestreams (~200hrs).</span></a></li>
          <li style="margin-bottom:12px;"><a href="live-call-validation.html" style="display:block;padding:12px 14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;border-left:3px solid #f0883e;"><strong>🔬 Live-Call Validation Report</strong><br><span style="color:var(--muted);font-size:14px;">Playbook claims tested against 10hrs of Richard's actual live calls. Deltas + clickable YouTube timestamps.</span></a></li>
        </ul>
        ''',
    )
    (PLAYBOOKS / 'index.html').write_text(index_html)
    print(f'  ✓ wrote index.html')

if __name__ == '__main__':
    main()
