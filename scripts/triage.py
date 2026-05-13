import urllib.request, urllib.error, urllib.parse, http.cookiejar, json, base64, sys
from datetime import datetime, date, timedelta

import os

BBC_EMAIL = os.environ['BBC_EMAIL']
BBC_PASS  = os.environ['BBC_PASS']
AT_TOKEN  = os.environ['AT_TOKEN']
AT_BASE   = os.environ.get('AT_BASE', 'appv6jhEzhGaAITcs')
KB_TABLE  = os.environ.get('KB_TABLE', 'tblh40Mq2rHwfe1I2')
WL_TABLE  = os.environ.get('WL_TABLE', 'tbluV0qAWYNAFkD5S')
GH_PAT    = os.environ['GH_PAT']
GH_REPO   = os.environ.get('GH_REPO', 'timfarr-ai/rt-companion')
STATES = ['Tennessee', 'Texas', 'Georgia', 'Ohio', 'Michigan']

# Cookie jar + opener that BBC search needs
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def http_req(url, method='GET', headers=None, json_body=None, use_opener=False):
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers = (headers or {}) | {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with (opener.open if use_opener else urllib.request.urlopen)(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

# 1. BBC auth (use opener so cookies persist)
code, body = http_req('https://www.buyboxcartel.com/api/auth/login', method='POST',
                      json_body={'email': BBC_EMAIL, 'password': BBC_PASS}, use_opener=True)
if code != 200:
    print(f'BBC LOGIN FAILED ({code}): {body[:200]}', file=sys.stderr); sys.exit(1)
login_data = json.loads(body)
bbc_token = login_data['accessToken']
# BBC cookie balance for unlock-contact (1 cookie = 1 agent unlock)
bbc_cookie_balance = int(login_data.get('user', {}).get('cookies') or login_data.get('user', {}).get('cookieBalance') or 0)
print(f'BBC: logged in, {len(cj)} session cookies | BBC cookie balance: {bbc_cookie_balance}', file=sys.stderr)

# 2. Buyers
buyers = []
url = f'https://api.airtable.com/v0/{AT_BASE}/{KB_TABLE}?pageSize=100'
code, body = http_req(url, headers={'Authorization': f'Bearer {AT_TOKEN}'})
if code == 200:
    for r in json.loads(body).get('records', []):
        f = r['fields']
        if f.get('Status') != 'Active': continue
        buyers.append({'name': f.get('Name',''),
                       'states': f.get('States Buying In', []),
                       'deal_types': f.get('Deal Types', []),
                       'max_entry': float(f.get('Max Entry Budget') or 0),
                       'min_cf': float(f.get('Min Cash Flow') or 0)})
print(f'Buyers: {len(buyers)} active', file=sys.stderr)

# 3. Existing watchlist
existing_addrs = set()
url = f'https://api.airtable.com/v0/{AT_BASE}/{WL_TABLE}?filterByFormula=%7BStatus%7D%3D%27Watching%27&pageSize=100'
code, body = http_req(url, headers={'Authorization': f'Bearer {AT_TOKEN}'})
if code == 200:
    for r in json.loads(body).get('records', []):
        a = r['fields'].get('Address', '').strip().lower()
        if a: existing_addrs.add(a)
print(f'Watchlist: {len(existing_addrs)} existing', file=sys.stderr)

# 4. Fetch leads per state — uses opener for cookies
all_leads = []
for state in STATES:
    # Richard's method targets STALE listings (motivated sellers), not high-CF ones.
    # BBC's CF on SF cards is at bank rate — high CF means "deal works without
    # creative", which is the opposite of what we want. Sort by DOM desc instead.
    # Include both sellerFinance + mortgageTakeover deal types in the query.
    payload = {'search_query': state, 'deal_type': ['sellerFinance', 'mortgageTakeover'],
               'market_status': 'Active', 'page': 1, 'limit': 25,
               'sort_field': 'daysOnMarket', 'sort_order': 'desc',
               'price_range': {'max': 1_400_000}}
    code, body = http_req('https://www.buyboxcartel.com/api/lightning-leads/search-property',
                          method='POST', json_body=payload,
                          headers={'Accept': 'text/event-stream',
                                   'Authorization': f'Bearer {bbc_token}'},
                          use_opener=True)
    if code != 200:
        print(f'{state}: HTTP {code} — {body[:100]}', file=sys.stderr); continue
    text = body.decode(errors='ignore')
    state_count_before = len(all_leads)
    for block in text.split('\n\n'):
        if 'event: complete' in block:
            for line in block.split('\n'):
                if line.startswith('data:'):
                    try:
                        d = json.loads(line[5:])
                        all_leads.extend(d.get('propertyDetails', []))
                    except: pass
            break
        elif 'event: error' in block:
            for line in block.split('\n'):
                if line.startswith('data:'):
                    print(f'{state}: ERROR event: {line[5:200]}', file=sys.stderr)
    print(f'{state}: +{len(all_leads)-state_count_before} (cumulative {len(all_leads)})', file=sys.stderr)

# 4b. Helpers: agent unlock + timezone lookup
# US state → IANA timezone (covers 99% of triage target states; some states span multiple TZs,
# we pick the dominant metro TZ. East-TN/El-Paso/etc. are slight approximations.)
STATE_TZ = {
    'TN': 'America/Chicago', 'TX': 'America/Chicago', 'GA': 'America/New_York',
    'OH': 'America/New_York', 'MI': 'America/Detroit',
    'AL': 'America/Chicago', 'FL': 'America/New_York', 'IN': 'America/Indiana/Indianapolis',
    'NC': 'America/New_York', 'AZ': 'America/Phoenix',
}

def unlock_agent(pid):
    """Get listing agent contact info via BBC's contact-seller endpoint — the one
    that backs the 'Create Offer' modal. Confirmed cookie-free 2026-05-13 by CDP
    inspection (cookie balance unchanged across multiple calls).
    Returns dict with name/phone/email, or None if BBC has no agent record."""
    code, body = http_req(f'https://www.buyboxcartel.com/api/lightning-leads/contact-seller?pid={pid}',
                          method='GET', use_opener=True,
                          headers={'Authorization': f'Bearer {bbc_token}'})
    try:
        data = json.loads(body)
    except: return None
    info = ((data.get('payload') or {}).get('agent_info')) or {}
    if not info: return None
    name = (info.get('name') or '').strip()
    phone = (info.get('phone') or '').strip()
    email = (info.get('email') or '').strip()
    if not name or name == 'Not Available':
        return None
    # Phone/email may legitimately be "Not Available" even when name is known.
    return {'name': name,
            'phone': '' if phone == 'Not Available' else phone,
            'email': '' if email == 'Not Available' else email}

# 5. Score + tier
def units(p):
    for k in ('numberOfUnits','units','unitCount','totalUnits'):
        v = p.get(k) or (p.get('calculatedData') or {}).get(k)
        if v:
            try: return int(v)
            except: pass
    pt = (p.get('address') or {}).get('propertyType','').lower()
    if 'fourplex' in pt or 'quad' in pt: return 4
    if 'triplex' in pt: return 3
    if 'multi' in pt or 'plex' in pt: return 4
    return 1

def score(p):
    cd = p.get('calculatedData', {})
    cf = float(cd.get('monthlyCashFlow') or 0)
    lp = float(cd.get('listPrice') or 0)
    op = float(cd.get('offerPrice') or lp * 1.10)
    down = float(cd.get('downPayment') or op * 0.10)
    entry = down + 3000 + 5000
    coc = round((cf*12)/entry*100, 1) if entry > 0 else 0
    dom = int(p.get('daysOnMarket') or 0)
    addr = p.get('address', {})
    # Bank gap — use BBC's own monthlyCashFlow. For Seller Finance cards BBC
    # already computes CF at market bank rate on the offer price; for Mortgage
    # Takeover cards CF is at the existing-loan rate (the favorable creative
    # scenario). Either way, a negative CF is the conversation hook.
    # BBC fields used directly — no separate rate/down assumption layered on top.
    monthly_rent = float(cd.get('monthlyRent') or 0)
    monthly_piti = float(cd.get('monthlyPayment') or cd.get('monthlyTotalExpenses') or 0)
    bank_gap = round(-cf) if cf < 0 else 0
    # Listing freshness — BBC's market_status is always "Active" for filtered results,
    # but the gap between last_listed (lifetime days) and daysOnMarket (current spell)
    # reveals if the listing was paused/relisted (typically because it went under contract).
    last_listed = int(p.get('last_listed') or dom)
    relisted_gap = max(0, last_listed - dom)
    is_zillow_active = bool(p.get('is_zillow_active'))
    if not is_zillow_active:
        status_state = 'off-zillow'  # red — listing removed from Zillow
    elif relisted_gap >= 30:
        status_state = 'relisted'    # amber — likely went under contract previously, verify
    elif relisted_gap >= 14:
        status_state = 'paused'      # gentle warning — short paused gap
    else:
        status_state = 'active'      # green — fresh, no pause history
    return {'address': f"{addr.get('street','')}, {addr.get('city','')}, {addr.get('state','')}",
            'state': addr.get('state',''), 'type': addr.get('propertyType','') or 'Unknown',
            'deal_type': cd.get('dealType', 'sellerFinance'),
            'price': lp, 'cf': cf, 'coc': coc, 'dom': dom,
            'dom_flag': '🔥🔥' if dom>=150 else ('🔥' if dom>=90 else ''),
            'entry_fee': round(entry), 'entry_pct': round(entry/op*100,1) if op>0 else 0,
            'equity': int(float(cd.get('equity') or 0)), 'zillow': p.get('zillowUrl'), 'pid': p.get('pid',''), 'in_pipeline': bool(p.get('isPropertyAlreadyInPipeline')),
            'units': units(p),
            'market_status': p.get('market_status', 'Active'),
            'last_listed': last_listed,
            'relisted_gap': relisted_gap,
            'is_zillow_active': is_zillow_active,
            'status_state': status_state,
            'monthly_rent': round(monthly_rent),
            'monthly_piti': round(monthly_piti),
            'bank_gap': bank_gap,
            'deal_type_raw': cd.get('dealType', ''),
            'beds': int(p.get('bedrooms') or cd.get('bedrooms') or 0)}

def tier(s):
    """Richard's method targets DSCR-failing listings on Seller Finance plays.
    BBC's monthlyCashFlow for SF deal_type = CF at market bank rate on offer price,
    so NEGATIVE CF is the qualification signal (proves standard offer can't close).
    For Mortgage Takeover deal_type, CF is at the existing low rate (favorable
    creative scenario) — positive CF means the takeover works as-is.
    For Cash deal_type (Tier C) — positive CF means cash arbitrage works."""
    pt = s['type'].lower()
    is_mfh = s['units'] >= 5 or 'multi' in pt or 'apartment' in pt
    dt = s.get('deal_type', 'sellerFinance')
    # Tier A — MFH Seller Finance Checkmate (DSCR fails at bank rate = negative CF)
    if is_mfh and 350_000 <= s['price'] <= 1_400_000 and s['dom'] >= 90 and dt == 'sellerFinance' and s['cf'] <= 0:
        return 'A'
    # Tier B — cheap stale SFH Seller Finance (negative-CF hook)
    if not is_mfh and s['price'] < 100_000 and s['dom'] >= 90 and dt == 'sellerFinance' and s['cf'] <= 0:
        return 'B'
    # Tier MT — Mortgage Takeover (favorable existing loan → positive CF after assumption)
    if dt == 'mortgageTakeover' and s['cf'] > 0 and s['dom'] >= 60:
        return 'MT'
    # Tier C — cash-comparable SFH arbitrage
    if not is_mfh and s['cf'] > 300 and s['dom'] >= 60:
        return 'C'
    return 'REJECT'

def match_buyers(s, t, buyers):
    matches = []
    for b in buyers:
        if s['state'] not in b['states']: continue
        if t in ('A','B') and 'Seller Finance' not in b['deal_types']: continue
        if t == 'C' and 'Cash' not in b['deal_types']: continue
        if s['entry_fee'] > b['max_entry']: continue
        if s['cf'] < b['min_cf']: continue
        matches.append(b['name'])
    return matches

NON_RESIDENTIAL_TYPES = ('vacant', 'land', 'lot', 'acreage', 'commercial', 'industrial')
buckets = {'A':[], 'B':[], 'MT':[], 'C':[], 'REJECT':[]}
land_skipped = 0
for p in all_leads:
    s = score(p)
    if s['cf'] == 0 and s['price'] == 0: continue
    pt_lower = (s.get('type') or '').lower()
    if any(token in pt_lower for token in NON_RESIDENTIAL_TYPES):
        land_skipped += 1
        continue
    t = tier(s)
    s['buyer_matches'] = match_buyers(s, t, buyers) if t != 'REJECT' else []
    s['tz'] = STATE_TZ.get(s['state'], 'America/New_York')
    s['agent'] = None  # set below if unlocked
    buckets[t].append(s)
for t in ('A','B','MT','C'): buckets[t].sort(key=lambda x: -x['dom'])
print(f'\nA={len(buckets["A"])}  B={len(buckets["B"])}  MT={len(buckets["MT"])}  C={len(buckets["C"])}  REJECT={len(buckets["REJECT"])}  Land-skipped={land_skipped}', file=sys.stderr)

# 5b. Surface agent info — cookie-free via BBC's contact-seller endpoint (the one
# behind the Create Offer modal). Cost: $0/unlock. Run on ALL Tier A/B/C deals.
unlock_targets = buckets['A'] + buckets['B'] + buckets['MT'] + buckets['C']
unlocks_attempted = 0
unlocks_succeeded = 0
captured_agents = []  # for Airtable persistence
if unlock_targets:
    print(f'\nFetching agent info for {len(unlock_targets)} Tier A/B/C deals (cookie-free)...', file=sys.stderr)
    for s in unlock_targets:
        unlocks_attempted += 1
        agent = unlock_agent(s['pid'])
        if agent:
            s['agent'] = agent
            unlocks_succeeded += 1
            captured_agents.append({**agent, 'pid': s['pid'], 'address': s['address'], 'state': s['state']})
            phone_str = agent['phone'] or '(no phone)'
            print(f"  ✓ {s['address'][:50]}: {agent['name']} / {phone_str}", file=sys.stderr)
        else:
            print(f"  · {s['address'][:50]}: no agent record in BBC", file=sys.stderr)
    print(f'Agents captured: {unlocks_succeeded}/{unlocks_attempted}', file=sys.stderr)

# 5c. Persist captured agents to Airtable Known Agents (upsert by phone or by name+state)
KA_TABLE = 'tbl0yOlg317evTwdS'  # Known Agents table created 2026-05-13
def _at_fetch_known_agents():
    url = f'https://api.airtable.com/v0/{AT_BASE}/{KA_TABLE}?pageSize=100'
    out = {}  # key: phone (or name|state if no phone) → record_id, listings_touched, states
    while url:
        code, body = http_req(url, headers={'Authorization': f'Bearer {AT_TOKEN}'})
        if code != 200: break
        data = json.loads(body)
        for r in data.get('records', []):
            f = r.get('fields', {})
            key = f.get('Phone') or f"{f.get('Name','')}|{(f.get('States','') or '').split(chr(10))[0]}"
            out[key] = {'id': r['id'], 'touched': int(f.get('Listings Touched') or 0),
                        'states': set((f.get('States') or '').split('\n')) - {''},
                        'first_seen': f.get('First Seen', '')}
        offset = data.get('offset')
        url = f'https://api.airtable.com/v0/{AT_BASE}/{KA_TABLE}?pageSize=100&offset={offset}' if offset else None
    return out

agents_written = 0
if captured_agents:
    known = _at_fetch_known_agents()
    today_iso = __import__('datetime').date.today().isoformat()
    creates, updates = [], []
    seen_keys = set()
    for a in captured_agents:
        key = a['phone'] or f"{a['name']}|{a['state']}"
        if key in seen_keys: continue  # dedupe within today's batch
        seen_keys.add(key)
        if key in known:
            rec = known[key]
            updates.append({'id': rec['id'], 'fields': {
                'Last Seen': today_iso,
                'Listings Touched': rec['touched'] + 1,
                'Latest Listing': a['address'],
                'Latest PID': a['pid'],
                'States': '\n'.join(sorted(rec['states'] | {a['state']})),
            }})
        else:
            fields = {'Name': a['name'], 'First Seen': today_iso, 'Last Seen': today_iso,
                      'Listings Touched': 1, 'Latest Listing': a['address'],
                      'Latest PID': a['pid'], 'States': a['state']}
            if a['phone']: fields['Phone'] = a['phone']
            if a['email']: fields['Email'] = a['email']
            creates.append({'fields': fields})
    # Airtable: max 10 records/batch
    for batch_list, method in [(creates, 'POST'), (updates, 'PATCH')]:
        for i in range(0, len(batch_list), 10):
            payload = {'records': batch_list[i:i+10], 'typecast': True}
            code, body = http_req(f'https://api.airtable.com/v0/{AT_BASE}/{KA_TABLE}',
                                  method=method,
                                  headers={'Authorization': f'Bearer {AT_TOKEN}'},
                                  json_body=payload)
            if code in (200, 201):
                agents_written += len(batch_list[i:i+10])
            else:
                print(f'  ! Airtable {method} returned {code}: {body[:200]}', file=sys.stderr)
    print(f'Airtable Known Agents: {len(creates)} new, {len(updates)} updated, {agents_written} writes succeeded', file=sys.stderr)

# 6. Push rejects
today = date.today().isoformat()
watch_until = (date.today() + timedelta(days=180)).isoformat()
pushed = 0
for s in buckets['REJECT']:
    if s['cf'] <= 0: continue
    addr_only = s['address'].split(',')[0].strip()
    if not addr_only or addr_only.lower() in existing_addrs: continue
    existing_addrs.add(addr_only.lower())
    rec = {'records': [{'fields': {
        'Address': addr_only,
        'City State': ', '.join(s['address'].split(',')[1:]).strip(),
        'Original Asking': s['price'], 'Original CF': s['cf'],
        'Current Asking': s['price'], 'Current CF': s['cf'],
        'Rejection Reason': 'CF Below $200' if s['cf'] < 200 else 'Untiered (motivation/structure)',
        'DOM at Rejection': s['dom'], 'Current DOM': s['dom'],
        'Zillow URL': s['zillow'] or None,
        'First Seen': today, 'Last Checked': today, 'Watch Until': watch_until,
        'Status': 'Watching'}}]}
    code, body = http_req(f'https://api.airtable.com/v0/{AT_BASE}/{WL_TABLE}',
                          method='POST', json_body=rec,
                          headers={'Authorization': f'Bearer {AT_TOKEN}'})
    if code in (200, 201): pushed += 1
print(f'Pushed {pushed} to watchlist', file=sys.stderr)

# 7. Render HTML
date_iso = today
date_human = datetime.now().strftime('%a %b %d, %Y')
def render_deal(d, t):
    cls = {'A':'tier-A','B':'tier-B','MT':'tier-MT','C':'tier-C'}[t]
    # MT shares the contract/close playbook for now; no dedicated MT strategy page yet.
    playbook = {'A':'/rt-companion/strategy/tier-a-multifamily-checkmate.html',
                'B':'/rt-companion/strategy/tier-b-cheap-sfh-stale.html',
                'MT':'/rt-companion/strategy/contract-close.html',
                'C':'/rt-companion/strategy/tier-c-cash-buyer.html'}[t]
    bl = f'<div style="color:#56d364;font-size:13px;margin-top:6px;">🎯 BUYER MATCH: {", ".join(d["buyer_matches"])}</div>' if d['buyer_matches'] else ''
    z = f' <a class="zillow" href="{d["zillow"]}" target="_blank">Zillow ↗ (agent here)</a>' if d['zillow'] else ''
    city_state = ', '.join(d['address'].split(',')[1:]).strip()
    # BBC search URL with #auto: hash — userscript on BBC side auto-fills + searches
    bbc_search = f'https://www.buyboxcartel.com/vip/lightning-leads#auto:{urllib.parse.quote(city_state)}'
    bbc_link = f' <a class="zillow" href="{bbc_search}" target="_blank">Search BBC ↗</a>'
    # Offer Oven prefill link — userscript on hmhw.group/tools/offer-oven side reads #prefill= and fills inputs
    # Standard Tier A offer: asking+10%, 10% down, 0%, 30yr, 5yr balloon. Tier B: asking+20%, 12% down. Tier C: cash (skip oven).
    offer_price = round(d['price'] * (1.20 if t == 'B' else 1.10), 0) if t in ('A','B') else 0
    down_pct = 0.12 if t == 'B' else 0.10
    down = round(offer_price * down_pct, 0)
    balloon_yr = 7 if t == 'B' else 5
    rent_annual = round((d['cf'] + d['price']*0.005) * 12, 0)  # rough back-calc; user verifies in BBC
    prefill_payload = {
        'price': offer_price, 'down': down, 'rate': 0, 'term': 30, 'balloon': balloon_yr,
        'rent': rent_annual, 'assignment': 5000, 'closing': round(offer_price * 0.01, 0)
    }
    oven_url = f'https://www.hmhw.group/tools/offer-oven#prefill={urllib.parse.quote(json.dumps(prefill_payload))}'
    oven_link = f' <a class="zillow" href="{oven_url}" target="_blank">Verify in Offer Oven ↗</a>' if t in ('A','B') else ''
    pipe = ' <span class="pill" style="background:#1a4d2e;color:#56d364;">in pipeline</span>' if d.get('in_pipeline') else ''
    # Deal type pill (human readable from BBC's dealType field)
    dt_map = {'sellerFinance': 'Seller Finance', 'mortgageTakeover': 'Mortgage Takeover', 'section8': 'Section 8', 'fixAndFlip': 'Fix & Flip', 'cash': 'Cash'}
    dt_label = dt_map.get(d.get('deal_type',''), d.get('deal_type','') or '')
    dt_pill = f' <span class="pill" style="background:#1e2c44;color:#79c0ff;border-color:#1e2c44;">{dt_label}</span>' if dt_label else ''
    pt_pill = f' <span class="pill" style="background:#1a2c1a;color:#7ee787;border-color:#1a2c1a;">{d["type"]}</span>' if d.get('type') and d['type']!='Unknown' else ''
    # Status pill — surfaces relist history. Richard treats relisted/removed as a MOTIVATION
    # signal (mortgage-takeover course ~9:15): a fell-through deal means seller is now more
    # motivated and agent has lost a commission once. These are HIGH-priority calls, not skips.
    status_styles = {
        'active':    ('#1a4d2e', '#56d364', '✓ Active'),
        'paused':    ('#2c2a14', '#e3b341', f'◐ Paused {d.get("relisted_gap",0)}d gap'),
        'relisted':  ('#3a2418', '#ffa657', f'🔥 RELISTED {d.get("relisted_gap",0)}d gap — motivated seller, call first'),
        'off-zillow':('#2c2c2c', '#8b949e', '✗ Off Zillow (removed — call anyway)'),
    }
    bg, fg, label = status_styles.get(d.get('status_state','active'), status_styles['active'])
    status_pill = f' <span class="pill" style="background:{bg};color:{fg};border-color:{bg};font-weight:600;">{label}</span>'
    cf_label = 'Cash CF' if t == 'C' else 'CF'
    # Bank gap pill — Richard's pitch hook. $X/mo the seller LOSES at standard bank financing.
    # Only show when positive (i.e. listing actually fails conventional underwriting).
    # Bank gap — uses BBC's own numbers (monthlyCashFlow). For Seller Finance cards
    # this IS the standard-bank-rate gap (BBC computes CF at offer price + market rate).
    # For Mortgage Takeover cards this is CF at the existing favorable rate (the gap
    # is what you'd lose if you couldn't take over the loan and had to refi).
    bg_amount = d.get('bank_gap', 0)
    bg_piti = d.get('monthly_piti', 0)
    bg_rent = d.get('monthly_rent', 0)
    bg_label = 'Refi gap' if d.get('deal_type_raw') == 'mortgageTakeover' else 'Bank gap'
    bank_gap_title = f'PITI ${bg_piti:,}/mo − Rent ${bg_rent:,}/mo (BBC figures)' if bg_piti and bg_rent else 'From BBC monthlyCashFlow'
    bank_gap_pill = f' <span class="pill" style="background:#3a2418;color:#ffa657;border-color:#3a2418;font-weight:600;" title="{bank_gap_title}">🏦 {bg_label} −${bg_amount:,}/mo</span>' if bg_amount > 0 else ''
    # Comp links — Rentometer for rent validation, Zillow recently-sold for price validation.
    addr_enc = urllib.parse.quote(d['address'])
    beds = d.get('beds', 0)
    rent_url = f'https://www.rentometer.com/quickview/results?address={addr_enc}' + (f'&bedrooms={beds}' if beds else '')
    rent_link = f' <a class="zillow" href="{rent_url}" target="_blank">Rent comps ↗</a>'
    sold_url = f'https://www.zillow.com/homes/recently_sold/{addr_enc}_rb/'
    sold_link = f' <a class="zillow" href="{sold_url}" target="_blank">Sold comps ↗</a>'
    # Local time pill — updated live by JS (data-tz = IANA timezone)
    tz_pill = f' <span class="pill local-time" data-tz="{d["tz"]}">--:-- local</span>'
    # Agent block — only if unlocked
    agent_block = ''
    if d.get('agent'):
        a = d['agent']
        phone_clean = ''.join(c for c in a['phone'] if c.isdigit() or c == '+')
        if phone_clean and not phone_clean.startswith('+'): phone_clean = '+1' + phone_clean.lstrip('1')
        tel_link = f'<a href="tel:{phone_clean}" style="color:#56d364;">📞 {a["phone"]}</a>' if phone_clean else f'<span>📞 {a["phone"]}</span>'
        op_link = f' &nbsp; <a href="openphone://call?number={phone_clean}" style="color:#79c0ff;">via OpenPhone</a>' if phone_clean else ''
        email_link = f' &nbsp; <a href="mailto:{a["email"]}" style="color:#8b949e;">✉ {a["email"]}</a>' if a.get('email') and a['email'] != 'Not Available' else ''
        agent_block = f'<div style="margin-top:8px;padding:8px 10px;background:#0d2818;border:1px solid #1a4d2e;border-radius:6px;font-size:13px;"><div style="color:#7ee787;font-weight:600;margin-bottom:2px;">🔓 {a["name"]}</div><div>{tel_link}{op_link}{email_link}</div></div>'
    return f'<div class="deal {cls}"><div class="addr">{d["address"]}{pipe}{status_pill if d.get("status_state") != "active" else ""}</div><div class="meta">{d["units"]} units · {d["type"]}</div><div class="nums">{status_pill if d.get("status_state") == "active" else ""}{dt_pill}{pt_pill}<span class="pill">${d["price"]:,.0f}</span><span class="pill">{cf_label} ${d["cf"]:,.0f}/mo</span>{bank_gap_pill}<span class="pill">CoC {d["coc"]}%</span><span class="pill">DOM {d["dom"]} {d["dom_flag"]}</span>{tz_pill}</div><a class="play-link" href="{playbook}">Open Tier {t} playbook →</a>{z}{bbc_link}{oven_link}{rent_link}{sold_link}{bl}{agent_block}</div>'

section_a = ('<h2>🎯 TIER A — Multifamily Seller-Finance Checkmate ($350K-$1.4M, 5+ units, DOM 90+, DSCR fails)</h2>' + ''.join(render_deal(d,'A') for d in buckets['A'])) if buckets['A'] else ''
section_b = ('<h2>🏘️ TIER B — Cheap SFH Stale Seller Finance (<$100K, DOM 90+, DSCR fails)</h2>' + ''.join(render_deal(d,'B') for d in buckets['B'])) if buckets['B'] else ''
section_mt = ('<h2>🔑 MORTGAGE TAKEOVER — Favorable existing loan (positive CF at assumed rate, DOM 60+)</h2>' + ''.join(render_deal(d,'MT') for d in buckets['MT'])) if buckets['MT'] else ''
section_c = ('<h2>💵 TIER C — Cash-Comparable SFH (cash arbitrage, NOT seller finance)</h2>' + ''.join(render_deal(d,'C') for d in buckets['C'])) if buckets['C'] else ''
rej_section = ''
if buckets['REJECT']:
    rej_lines = ''.join(f'<div class="rejected">{s["address"]} — CF: ${s["cf"]:,.0f} (DOM {s["dom"]})</div>' for s in buckets['REJECT'][:15])
    rej_section = f'<h2>❌ REJECTED — {pushed} pushed to <a href="https://airtable.com/{AT_BASE}/{WL_TABLE}">Watchlist</a></h2>{rej_lines}'

agent_indicator = f' · 🔓 {unlocks_succeeded} agents captured (free)' if unlocks_succeeded else ''
summary = f'{len(all_leads)} leads · {len(buckets["A"])} Tier A · {len(buckets["B"])} Tier B · {len(buckets["MT"])} MT · {len(buckets["C"])} Tier C · {pushed} → watchlist{agent_indicator}'
CSS = 'body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:12px;font-size:15px;line-height:1.5;}h2{font-size:14px;color:#8b949e;text-transform:uppercase;letter-spacing:0.04em;margin:18px 0 8px;}.summary{background:#1c2128;border:1px solid #30363d;border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:14px;}.deal{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:10px;}.deal .addr{font-weight:600;font-size:15px;margin-bottom:4px;}.deal .meta{font-size:13px;color:#8b949e;margin-bottom:6px;}.deal .nums{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;}.pill{background:#1c2128;border:1px solid #30363d;border-radius:12px;padding:2px 9px;font-size:12px;color:#8b949e;}.play-link{display:inline-block;padding:8px 12px;background:#58a6ff;color:#0d1117;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;margin-top:4px;}.tier-A{border-left:3px solid #ff7b72;}.tier-B{border-left:3px solid #d2a8ff;}.tier-MT{border-left:3px solid #79c0ff;}.tier-C{border-left:3px solid #56d364;}a.zillow{color:#58a6ff;font-size:12px;margin-left:8px;}.rejected{color:#8b949e;font-size:13px;padding:4px 0;}.date{color:#8b949e;font-size:13px;}.addr-copy{display:inline-block;margin-left:8px;padding:2px 9px;font-size:12px;background:#1c2128;border:1px solid #30363d;color:#58a6ff;border-radius:12px;cursor:pointer;font-family:inherit;}.addr-copy:hover{background:#21262d;}.addr-copy.copied{background:#1a4d2e;color:#56d364;border-color:#1a4d2e;}'
CLOCK_JS = '''<script>
function updateLocalTimes(){
  document.querySelectorAll('.local-time').forEach(function(el){
    var tz = el.dataset.tz || 'America/New_York';
    try {
      var t = new Date().toLocaleTimeString('en-US', {timeZone: tz, hour: 'numeric', minute: '2-digit', hour12: true});
      el.textContent = '🕐 ' + t + ' local';
    } catch(e) {
      el.textContent = '🕐 ' + tz.split('/').pop().replace('_',' ');
    }
  });
}
updateLocalTimes();
setInterval(updateLocalTimes, 30000);
</script>'''
html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Triage {date_iso}</title><style>{CSS}</style></head><body><p class="date">📋 {date_human} · TN/TX/GA/OH/MI &nbsp;·&nbsp; <a href="https://www.buyboxcartel.com/vip/lightning-leads" target="_blank" style="color:#58a6ff;">Open BBC Lightning Leads ↗</a></p><div class="summary">{summary}</div>{section_a}{section_b}{section_mt}{section_c}{rej_section}' + CLOCK_JS + '</body></html>'

# 8. Publish
b64 = base64.b64encode(html.encode()).decode()
def gh_put(path, content_b64, msg, sha=None):
    body = {'message': msg, 'content': content_b64}
    if sha: body['sha'] = sha
    return http_req(f'https://api.github.com/repos/{GH_REPO}/contents/{path}',
                    method='PUT', json_body=body,
                    headers={'Authorization': f'Bearer {GH_PAT}'})
def gh_get_sha(path):
    code, body = http_req(f'https://api.github.com/repos/{GH_REPO}/contents/{path}',
                          headers={'Authorization': f'Bearer {GH_PAT}'})
    return json.loads(body).get('sha') if code == 200 else None
c1, _ = gh_put(f'briefings/{date_iso}.html', b64, f'briefing {date_iso}', sha=gh_get_sha(f'briefings/{date_iso}.html'))
c2, _ = gh_put('briefings/latest.html', b64, f'latest {date_iso}', sha=gh_get_sha('briefings/latest.html'))
print(f'GitHub: today={c1}, latest={c2}', file=sys.stderr)

print('\n=========== BRIEFING ===========\n')
print(f'📋 MORNING TRIAGE — {date_human} | HMHW Tier-Based | TN/TX/GA/OH/MI')
print(summary)
for t, name, emoji in [('A','Tier A — Multifamily SF Checkmate','🎯'),
                       ('B','Tier B — Cheap SFH Stale SF','🏘️'),
                       ('MT','Mortgage Takeover','🔑'),
                       ('C','Tier C — Cash Buyer','💵')]:
    if not buckets[t]: continue
    print(f'\n{emoji} {name} ({len(buckets[t])}):')
    for i, d in enumerate(buckets[t], 1):
        bm = f'  🎯 BUYER MATCH: {", ".join(d["buyer_matches"])}' if d['buyer_matches'] else ''
        print(f'{i}. {d["address"]} | {d["units"]}u | ${d["price"]:,.0f} | CF ${d["cf"]:,.0f}/mo | CoC {d["coc"]}% | DOM {d["dom"]} {d["dom_flag"]}{bm}')
        if d['zillow']: print(f'   Zillow: {d["zillow"]}')
        # BBC has no URL deep-link — Tim taps 'Copy address ↗ BBC' button on dashboard and pastes in BBC search
        if d.get('in_pipeline'): print(f'   [already in BBC pipeline]')
if buckets['REJECT']:
    print(f'\n❌ REJECTED — {pushed} pushed to Watchlist (showing 10):')
    for d in buckets['REJECT'][:10]:
        print(f'- {d["address"]} — CF ${d["cf"]:,.0f}/mo, DOM {d["dom"]}')
print(f'\n✅ Briefing: https://timfarr-ai.github.io/rt-companion/briefings/{date_iso}.html')
print(f'🔗 Dashboard: https://timfarr-ai.github.io/rt-companion/')
print(f'📒 Watchlist: https://airtable.com/{AT_BASE}/{WL_TABLE}')
