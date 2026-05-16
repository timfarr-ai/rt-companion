#!/usr/bin/env python3
"""Render the per-video call-moment JSON indexes as a single navigable HTML
page with clickable YouTube ?t= jumps. Reads from /tmp/playbooks/video-indexes/."""
import json, html
from pathlib import Path

SRC = Path('/Users/timfarr/Code/rt-companion/playbooks/video-indexes')
OUT = Path('/Users/timfarr/Code/rt-companion/playbooks/video-call-moments.html')

# Copy JSONs into repo for source-of-truth
SRC.mkdir(exist_ok=True)
import shutil
for p in Path('/tmp/playbooks/video-indexes').glob('*'):
    dst = SRC / p.name
    if not dst.exists() or p.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy(p, dst)

VIDS = sorted([f for f in SRC.glob('*.json')], key=lambda p: p.name)

STRATEGY_COLOR = {
    'SF': '#d2a8ff', 'MT': '#79c0ff', 'HY': '#c971ff',
    'Cash': '#56d364', 'FF': '#f0883e', 'Coaching': '#8b949e',
    'Q&A': '#6e7681', 'Chat': '#444', 'Setup': '#6e7681',
}
TYPE_ICON = {
    'call': '📞', 'Coaching': '🎓', 'Q&A': '❓',
    'Chat': '💬', 'Setup': '🔍',
}

def render_segment(vid, seg):
    sec = seg.get('start_seconds', 0)
    yt_url = f"https://youtu.be/{vid}?t={sec}"
    start = seg.get('start', '?')
    dur = seg.get('duration', '')
    typ = seg.get('type', 'call')
    strat = seg.get('strategy', '')
    who = seg.get('who', '')
    summary = html.escape(seg.get('summary', ''))
    highlight = seg.get('highlight', False)
    icon = TYPE_ICON.get(typ, '·')
    color = STRATEGY_COLOR.get(strat, '#444')
    star = ' 🔥' if highlight else ''
    return (
        f'<a href="{yt_url}" target="_blank" rel="noopener" '
        f'class="seg{" seg-hl" if highlight else ""}">'
        f'<span class="seg-time">▶ {start}</span> '
        f'<span class="seg-dur">{dur}</span> '
        f'<span class="seg-strat" style="background:{color}33;color:{color};">{icon} {strat}</span> '
        f'<span class="seg-who">{who}</span>{star}'
        f'<div class="seg-summary">{summary}</div>'
        f'</a>'
    )

def render_video(p):
    d = json.loads(p.read_text())
    vid = d['video_id']
    title = html.escape(d['title'])
    duration = d['duration']
    url = d['url']
    summary = html.escape(d.get('summary', ''))
    segs = d.get('segments', [])
    n_hl = sum(1 for s in segs if s.get('highlight'))
    segments_html = ''.join(render_segment(vid, s) for s in segs)
    return f'''
    <section class="video-section">
      <h2>🎬 {title} <span class="dur">{duration}</span></h2>
      <p class="video-summary">{summary}</p>
      <p class="video-meta">{len(segs)} segments · <strong>{n_hl} highlights 🔥</strong> · <a href="{url}" target="_blank">open on YouTube ↗</a></p>
      <div class="segs">
        {segments_html}
      </div>
    </section>
    '''

CSS = '''
:root{--bg:#0d1117;--panel:#161b22;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--green:#56d364;--gold:#e3b341;}
*{box-sizing:border-box;}html,body{margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:15px;line-height:1.5;}
a{color:var(--accent);text-decoration:none;}
header{position:sticky;top:0;background:rgba(13,17,23,0.95);backdrop-filter:blur(10px);border-bottom:1px solid var(--border);padding:14px 16px;z-index:10;display:flex;align-items:center;justify-content:space-between;gap:12px;}
header h1{margin:0;font-size:17px;}
header .back{font-size:14px;color:var(--accent);}
main{padding:14px;max-width:920px;margin:0 auto;}
.intro{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:18px;font-size:14px;line-height:1.55;}
.video-section{margin-bottom:32px;}
.video-section h2{margin:24px 0 8px;font-size:18px;border-bottom:1px solid var(--border);padding-bottom:8px;display:flex;align-items:baseline;justify-content:space-between;gap:10px;}
.video-section .dur{font-size:13px;color:var(--muted);font-weight:400;}
.video-summary{color:var(--text);margin:8px 0;}
.video-meta{font-size:13px;color:var(--muted);margin:4px 0 14px;}
.segs{display:flex;flex-direction:column;gap:6px;}
.seg{display:block;padding:10px 12px;background:var(--panel);border:1px solid var(--border);border-radius:8px;color:var(--text);transition:border-color 0.1s;}
.seg:hover{border-color:var(--accent);}
.seg-hl{border-left:3px solid var(--gold);background:#1a1814;}
.seg-time{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12.5px;color:var(--accent);font-weight:600;}
.seg-dur{font-size:11.5px;color:var(--muted);margin-left:6px;}
.seg-strat{display:inline-block;font-size:11px;padding:1px 7px;border-radius:8px;margin-left:8px;font-weight:600;}
.seg-who{font-size:11.5px;color:var(--muted);margin-left:6px;}
.seg-summary{margin-top:4px;font-size:13.5px;color:var(--text);line-height:1.4;}
nav.bottom{padding:18px 0 24px;text-align:center;color:var(--muted);font-size:13px;}
nav.bottom a{color:var(--muted);margin:0 10px;}
.stats{display:flex;flex-wrap:wrap;gap:14px;padding:12px;background:var(--panel-2,#1c2128);border:1px solid var(--border);border-radius:8px;margin:14px 0;font-size:13.5px;}
.stat{flex:1;min-width:140px;}
.stat-label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:0.06em;}
.stat-val{font-size:18px;font-weight:600;color:var(--text);}
@media (min-width:720px){main{padding:24px;}}
'''

intro_html = '''
<div class="intro">
  <p><strong>Skip the dead air. Hit the gold.</strong> Each segment links to the exact second in the YouTube video. 🔥 = highlight worth listening to (36 total across 4 videos).</p>
  <p>11.3 hours of footage → 3.9 hours of actual call audio → ~1 hour of must-listen highlights. <strong>If you only have 50 min:</strong> Video 4 from 0:24-1:02 (San Diego MT arc) + Video 3 from 0:02-0:15 (Birmingham portfolio underwrite) + Video 3 from 1:59-2:04 (cash-on-cash formula).</p>
  <p style="margin:0;font-size:13px;color:var(--muted);">Source: 4 auto-captioned livestreams, ~30K caption lines analyzed.</p>
</div>
<div class="stats">
  <div class="stat"><div class="stat-label">Total footage</div><div class="stat-val">11.3 hrs</div></div>
  <div class="stat"><div class="stat-label">Indexed content</div><div class="stat-val">8.8 hrs</div></div>
  <div class="stat"><div class="stat-label">Actual call audio</div><div class="stat-val">3.9 hrs</div></div>
  <div class="stat"><div class="stat-label">🔥 highlights</div><div class="stat-val">36</div></div>
</div>
'''

# Assemble all videos
vids_html = '\n'.join(render_video(p) for p in VIDS)

html_out = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="robots" content="noindex, nofollow">
  <title>Livestream Call Moments — Navigable Index</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <a href="/rt-companion/playbooks/" class="back">‹ Playbooks</a>
    <h1>Call Moments — Jump Index</h1>
    <a href="/rt-companion/" class="back" style="text-align:right;">🏠</a>
  </header>
  <main>
    {intro_html}
    {vids_html}
    <nav class="bottom">
      <a href="/rt-companion/playbooks/study-library.html">Study Library</a> ·
      <a href="/rt-companion/playbooks/live-call-validation.html">Validation Report</a> ·
      <a href="/rt-companion/">Dashboard</a>
    </nav>
  </main>
</body>
</html>
'''
OUT.write_text(html_out)
print(f'✓ wrote {OUT.name} ({len(html_out):,} chars, {sum(1 for p in VIDS):d} videos rendered)')
