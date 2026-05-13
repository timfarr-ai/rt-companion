#!/usr/bin/env python3
"""
Build the rt-companion dashboard from the local skill files + strategies.yaml.

Reads:
  - ~/.claude/skills/richard-taylor-underwrite/references/outreach-scripts.md (via anchor IDs)
  - ~/.claude/skills/richard-taylor-underwrite/references/deal-criteria.md
  - data/strategies.yaml (structure)

Writes:
  - index.html
  - strategy/*.html
  - briefings/index.html (placeholder list, latest is maintained by cloud routine)

Then: git add -A && git commit && git push.

Usage:
  python publish.py            # rebuild + commit + push
  python publish.py --no-push  # rebuild only
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("Missing deps. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
SKILL_REF = Path.home() / ".claude/skills/richard-taylor-underwrite/references"
OUTREACH_MD = SKILL_REF / "outreach-scripts.md"
CRITERIA_MD = SKILL_REF / "deal-criteria.md"


def extract_anchor_section(md_path: Path, anchor_id: str) -> str:
    """Pull the markdown section starting at `<a id="anchor_id"></a>` until the next
    same-or-higher-level heading or the next anchor. Returns the raw markdown body."""
    text = md_path.read_text()
    pat = re.compile(r'<a id="([^"]+)"></a>')

    sections = []  # list of (anchor_id, start_idx)
    for m in pat.finditer(text):
        sections.append((m.group(1), m.end()))

    target = None
    target_end = len(text)
    for i, (aid, start) in enumerate(sections):
        if aid == anchor_id:
            target = start
            # End is the start of the next anchor OR end of file
            if i + 1 < len(sections):
                # Walk forward from `start` to find the next anchor's `<a id...>` start
                # The next anchor's start position is sections[i+1][1] which is end of <a tag>;
                # we want the position of `<a id` itself.
                next_anchor_pos = text.find('<a id="', start)
                if next_anchor_pos != -1:
                    target_end = next_anchor_pos
            break

    if target is None:
        return f"[Section {anchor_id} not found in {md_path.name}]"

    body = text[target:target_end].strip()
    return body


def extract_script_block(section_md: str) -> str:
    """Find the first ``` ... ``` block in a markdown section and return its content."""
    m = re.search(r"```(?:\w*)\n(.*?)\n```", section_md, re.DOTALL)
    if m:
        return m.group(1).strip()
    # No fenced block — return everything after the heading
    lines = section_md.split("\n")
    # Drop the heading line
    body = "\n".join(l for l in lines if not l.startswith("#")).strip()
    return body


def extract_rebuttal(section_md: str) -> str:
    """Same as extract_script_block but for objection rebuttals."""
    return extract_script_block(section_md)


def resolve_audio_url(audio_base: str, file_path: str) -> str:
    return f"{audio_base.rstrip('/')}/{file_path}"


def resolve_source_url(src: dict, sources_lib: dict) -> str:
    if "url" in src:
        return src["url"]
    if "url_key" in src:
        return sources_lib.get(src["url_key"], "#")
    return "#"


def build_strategies(data: dict, key: str = "strategies") -> list:
    """For each entry in `data[key]`, hydrate it with extracted script text + audio URLs.
    Works for both `strategies` and `sops` since they share the same structure."""
    audio_base = data["audio_base"]
    sources_lib = data["sources_lib"]
    out = []

    for s in data.get(key, []):
        strat = dict(s)  # shallow copy

        # Hydrate voicemail
        if "voicemail" in strat and strat["voicemail"]:
            vm = dict(strat["voicemail"])
            anchor = vm["script_section"].split("#")[-1]
            section_md = extract_anchor_section(OUTREACH_MD, anchor)
            vm["script_text"] = extract_script_block(section_md)
            if "audio_file_path" in vm:
                vm["audio_url"] = resolve_audio_url(audio_base, vm["audio_file_path"])
            strat["voicemail"] = vm

        # Hydrate live_call
        if "live_call" in strat and strat["live_call"]:
            lc = dict(strat["live_call"])
            anchor = lc["script_section"].split("#")[-1]
            section_md = extract_anchor_section(OUTREACH_MD, anchor)
            lc["script_text"] = extract_script_block(section_md)
            if "audio_file_path" in lc:
                lc["audio_url"] = resolve_audio_url(audio_base, lc["audio_file_path"])
            strat["live_call"] = lc

        # Hydrate alt_script
        if "alt_script" in strat and strat["alt_script"]:
            alt = dict(strat["alt_script"])
            anchor = alt["script_section"].split("#")[-1]
            section_md = extract_anchor_section(OUTREACH_MD, anchor)
            alt["script_text"] = extract_script_block(section_md)
            if "audio_file_path" in alt:
                alt["audio_url"] = resolve_audio_url(audio_base, alt["audio_file_path"])
            strat["alt_script"] = alt

        # Hydrate top_objections
        if "top_objections" in strat and strat["top_objections"]:
            objs = []
            for obj in strat["top_objections"]:
                o = dict(obj)
                anchor = o["section"].split("#")[-1]
                section_md = extract_anchor_section(OUTREACH_MD, anchor)
                o["rebuttal_text"] = extract_rebuttal(section_md)
                objs.append(o)
            strat["top_objections"] = objs

        # Resolve source URLs
        if "sources" in strat and strat["sources"]:
            srcs = [dict(s, url=resolve_source_url(s, sources_lib)) for s in strat["sources"]]
            strat["sources"] = srcs

        out.append(strat)

    return out


def render_strategy_pages(strategies: list, env: Environment, out_dir: Path, sub_dir: str = "strategy"):
    """Render each strategy/SOP to {sub_dir}/{slug}.html using the strategy template."""
    template = env.get_template("strategy.html.j2")
    dest_dir = out_dir / sub_dir
    dest_dir.mkdir(exist_ok=True)
    for s in strategies:
        html = template.render(
            title=s["title"],
            header_title=f"{s['emoji']} {s['title']}",
            back_link="/rt-companion/",
            strategy=s,
        )
        path = dest_dir / f"{s['slug']}.html"
        path.write_text(html)
        print(f"  → {path.relative_to(ROOT)}")


def render_index(strategies: list, sops: list, env: Environment, out_dir: Path):
    """Render the dashboard root index.html."""
    # The index template lives in the repo (not in templates/), we'll inline a simple one
    # by using base.html.j2 + an index-specific content block.
    template_str = """{% extends "base.html.j2" %}
{% block content %}

<div class="section">
  <h2>📋 Today's Briefing</h2>
  <div class="briefing-wrap">
    <iframe src="/rt-companion/briefings/latest.html" loading="lazy"></iframe>
  </div>
  <p style="margin-top:8px; font-size:13px;">
    Briefing publishes weekday 6am AEST.
    <a href="/rt-companion/briefings/" style="margin-left:6px;">Past briefings →</a>
  </p>
</div>

<div class="grid-2">
  <div class="section">
    <h2>Strategy Playbooks (deal-specific plays)</h2>
    {% for s in strategies %}
    <a class="source-link" href="/rt-companion/strategy/{{ s.slug }}.html">
      <span class="icon">{{ s.emoji }}</span>
      <span class="label">{{ s.title }}</span>
      <span class="arrow">›</span>
    </a>
    {% endfor %}
  </div>

  <div class="section">
    <h2>SOPs (daily workflow)</h2>
    {% for s in sops %}
    <a class="source-link" href="/rt-companion/sop/{{ s.slug }}.html">
      <span class="icon">{{ s.emoji }}</span>
      <span class="label">{{ s.title }}</span>
      <span class="arrow">›</span>
    </a>
    {% endfor %}
  </div>
</div>

<div class="section">
  <h2>External Tools</h2>
  <a class="source-link" href="https://buyboxcartel.com/vip/dashboard" target="_blank" rel="noopener">
    <span class="icon">🏦</span><span class="label">BBC Dashboard</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://buyboxcartel.com/vip/inventory" target="_blank" rel="noopener">
    <span class="icon">📊</span><span class="label">BBC Inventory (pipeline)</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://buyboxcartel.com/vip/marketplace" target="_blank" rel="noopener">
    <span class="icon">📤</span><span class="label">BBC Marketplace (dispo)</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://www.hmhw.group/tools" target="_blank" rel="noopener">
    <span class="icon">🧮</span><span class="label">HMHW Calculators (incl. Offer Oven)</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://www.hmhw.group/education" target="_blank" rel="noopener">
    <span class="icon">🎧</span><span class="label">HMHW Full Recordings (82)</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://grandintaylorllc.salesmate.io/webforms/#/5bddb679-43e9-4a91-aca2-ddaff898ff78" target="_blank" rel="noopener">
    <span class="icon">📋</span><span class="label">Grand In Taylor — Creative Form</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://grandintaylorllc.salesmate.io/webforms/#/696ce9d7-457b-44ad-8e6f-a9574197e587" target="_blank" rel="noopener">
    <span class="icon">📋</span><span class="label">Grand In Taylor — Cash Alt Form</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://claude.ai/code/routines/trig_01DXdZ22PfZsyJjmTkiWPanC" target="_blank" rel="noopener">
    <span class="icon">🤖</span><span class="label">Claude routine runs (briefing transcript)</span><span class="arrow">↗</span>
  </a>
</div>

<div class="section">
  <h2>Airtable Data</h2>
  <a class="source-link" href="https://airtable.com/appv6jhEzhGaAITcs/tblh40Mq2rHwfe1I2" target="_blank" rel="noopener">
    <span class="icon">🤝</span><span class="label">Known Buyers (your network)</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://airtable.com/appv6jhEzhGaAITcs/tbluV0qAWYNAFkD5S" target="_blank" rel="noopener">
    <span class="icon">👀</span><span class="label">Rejected Watchlist (price-drop monitor)</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://airtable.com/appv6jhEzhGaAITcs/tbl0yOlg317evTwdS" target="_blank" rel="noopener">
    <span class="icon">🔓</span><span class="label">Known Agents (auto-captured cookie-free)</span><span class="arrow">↗</span>
  </a>
  <a class="source-link" href="https://airtable.com/appv6jhEzhGaAITcs/tblk9fSDyWjpftLwm" target="_blank" rel="noopener">
    <span class="icon">📋</span><span class="label">Deal Flow (tracked deals — 13 stages)</span><span class="arrow">↗</span>
  </a>
</div>

{% endblock %}
"""
    # Add the inline template to the environment's loader by registering it as a string
    template = env.from_string(template_str)
    html = template.render(
        title="Home",
        header_title="RT Deal Desk",
        back_link=None,
        strategies=strategies,
        sops=sops,
    )
    (out_dir / "index.html").write_text(html)
    print(f"  → index.html")


def render_briefings_index(out_dir: Path):
    """List existing daily briefings."""
    briefings_dir = out_dir / "briefings"
    briefings_dir.mkdir(exist_ok=True)
    files = sorted([f.name for f in briefings_dir.glob("*.html")
                    if f.name not in ("index.html", "latest.html")], reverse=True)
    rows = "\n".join(
        f'  <li><a href="/rt-companion/briefings/{f}">{f.replace(".html","")}</a></li>'
        for f in files
    ) or '  <li style="color:#8b949e;">No briefings yet — first run fires tomorrow 6am AEST.</li>'
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Briefings Archive</title>
<style>body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,sans-serif;padding:16px;}}
h1{{font-size:18px;}}ul{{padding-left:20px;}}a{{color:#58a6ff;text-decoration:none;}}</style>
</head><body>
<a href="/rt-companion/" style="font-size:13px;">‹ Home</a>
<h1>Past Briefings</h1>
<ul>
{rows}
</ul>
</body></html>"""
    (briefings_dir / "index.html").write_text(html)
    print(f"  → briefings/index.html")


def ensure_latest_placeholder(out_dir: Path):
    """Create a placeholder briefings/latest.html if none exists, so iframe doesn't 404."""
    latest = out_dir / "briefings" / "latest.html"
    if latest.exists():
        return
    html = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>body{background:#0d1117;color:#8b949e;font-family:-apple-system,sans-serif;padding:24px;text-align:center;}
.box{padding:24px;background:#161b22;border:1px solid #30363d;border-radius:10px;}</style>
</head><body><div class="box">
<p>📅 First briefing publishes weekday 6am AEST.</p>
<p style="font-size:13px;">Cloud routine: <code>trig_01DXdZ22PfZsyJjmTkiWPanC</code></p>
</div></body></html>"""
    latest.write_text(html)
    print(f"  → briefings/latest.html (placeholder)")


def git_publish(no_push: bool = False):
    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=ROOT
        )
        if result.returncode == 0:
            print("\nNo changes to commit.")
            return
        from datetime import datetime
        msg = f"publish {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
        if no_push:
            print(f"\nCommitted ({msg}). Skipping push (--no-push).")
        else:
            subprocess.run(["git", "push"], cwd=ROOT, check=True)
            print(f"\nPushed: {msg}")
    except subprocess.CalledProcessError as e:
        print(f"git operation failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true", help="Build only, no git commit/push")
    args = ap.parse_args()

    print(f"Reading {OUTREACH_MD.name} + {CRITERIA_MD.name} + strategies.yaml")
    if not OUTREACH_MD.exists():
        print(f"  ERROR: {OUTREACH_MD} not found", file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load((ROOT / "data" / "strategies.yaml").read_text())
    strategies = build_strategies(data, "strategies")
    sops = build_strategies(data, "sops")

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html"]),
        keep_trailing_newline=True,
    )

    print(f"\nRendering {len(strategies)} strategy pages:")
    render_strategy_pages(strategies, env, ROOT, "strategy")
    print(f"\nRendering {len(sops)} SOP pages:")
    render_strategy_pages(sops, env, ROOT, "sop")
    render_index(strategies, sops, env, ROOT)
    render_briefings_index(ROOT)
    ensure_latest_placeholder(ROOT)

    print("\nDone.\n")
    git_publish(no_push=args.no_push)


if __name__ == "__main__":
    main()
