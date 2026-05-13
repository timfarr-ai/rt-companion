import urllib.request, urllib.error, urllib.parse, http.cookiejar, json, base64, sys
from datetime import datetime, date, timedelta

import os

BBC_EMAIL = os.environ['BBC_EMAIL']
BBC_PASS  = os.environ['BBC_PASS']
AT_TOKEN  = os.environ['AT_TOKEN']
AT_BASE   = os.environ.get('AT_BASE', 'appv6jhEzhGaAITcs')
KB_TABLE  = os.environ.get('KB_TABLE', 'tblh40Mq2rHwfe1I2')
WL_TABLE  = os.environ.get('WL_TABLE', 'tbluV0qAWYNAFkD5S')
DF_TABLE  = os.environ.get('DF_TABLE', 'tblk9fSDyWjpftLwm')  # Deal Flow — tracked deals
GH_PAT    = os.environ['GH_PAT']
GH_REPO   = os.environ.get('GH_REPO', 'timfarr-ai/rt-companion')
# 10-state list, each one with primary-source teaching from Richard's courses:
#   AL,TX,GA,TN,IN,OH,MI,FL  — MT course canonical list (lines 1041-1046):
#     "We love Alabama. Texas. Georgia. Tennessee. Indiana. Ohio. Michigan.
#      Midwest and South Florida really, really good."
#   NC  — MT course line 858: "Clayton, North Carolina. My business partner is
#         from Clayton, North Carolina."
#   MS  — MT course line 1203: "Jackson, Mississippi" in market list.
# AR and MO were dropped 2026-05-13 — they appeared empirically but have NO
# primary-source backing across the three captured course transcripts.
STATES = ['Tennessee', 'Texas', 'Georgia', 'Ohio', 'Michigan',
          'Alabama', 'Mississippi', 'Indiana', 'Florida', 'North Carolina']

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

# 3b. Fetch tracked PIDs from Deal Flow — existence = excluded from today's briefing.
# Tim's rule: any property he's added to Deal Flow (any status) drops out of the
# daily; he comes back to it through the Airtable kanban instead.
tracked_pids = set()
url = f'https://api.airtable.com/v0/{AT_BASE}/{DF_TABLE}?pageSize=100&fields%5B%5D=PID'
while url:
    code, body = http_req(url, headers={'Authorization': f'Bearer {AT_TOKEN}'})
    if code != 200: break
    data = json.loads(body)
    for r in data.get('records', []):
        pid = (r.get('fields') or {}).get('PID', '').strip()
        if pid: tracked_pids.add(pid)
    offset = data.get('offset')
    url = f'https://api.airtable.com/v0/{AT_BASE}/{DF_TABLE}?pageSize=100&fields%5B%5D=PID&offset={offset}' if offset else None
print(f'Deal Flow: {len(tracked_pids)} tracked PIDs to exclude from daily', file=sys.stderr)

# 4. Fetch leads per state — uses opener for cookies
all_leads = []
for state in STATES:
    # Richard's full play menu (Cash Course + Seller Finance + Mortgage Takeover):
    # SF/MT for stuck creative deals, Fix & Flip for distressed cheap cash plays.
    # Sort by DOM desc (stale = motivated). Limit 25/state for breadth across plays.
    payload = {'search_query': state,
               'deal_type': ['sellerFinance', 'mortgageTakeover', 'fixAndFlip'],
               'market_status': 'Active', 'page': 1, 'limit': 75,
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
    'MS': 'America/Chicago', 'AR': 'America/Chicago', 'MO': 'America/Chicago',
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
    dt = cd.get('dealType', 'sellerFinance')
    pt_lower = (addr.get('propertyType') or '').lower()
    is_mfh = (cd.get('numberOfUnits') and int(cd.get('numberOfUnits')) >= 5) or 'multi' in pt_lower or 'apartment' in pt_lower
    # BBC fields verified via API probe 2026-05-13: monthlyRent NOT in payload, but
    # piti (full PITI) and monthlyPayment (P&I only) are. Back-calc rent from CF:
    #   cf = rent − piti − (rent × 0.20)   →   rent = (cf + piti) / 0.80
    piti = float(cd.get('piti') or 0)
    monthly_payment = float(cd.get('monthlyPayment') or 0)
    expense_total = piti or (monthly_payment + lp * 0.005)  # P&I + ~taxes/ins fallback
    monthly_rent = round((cf + expense_total) / 0.80) if expense_total > 0 else 0

    # CREATIVE CF — BBC's monthlyCashFlow IS already computed at the deal_type's
    # creative terms (SF: ~0%, 10-12% down; MT: existing loan rate). Verified via
    # probe: 11311 Ardsley Dr S (SF, $558K) shows monthlyPayment $1190 — only
    # explicable at 0%/10%-down on a $558K listing. So we use cf directly as
    # creative_cf and don't recompute.
    creative_cf = round(cf)

    # BANK GAP — what would this deal look like under a STANDARD 7% bank mortgage?
    # We must compute this separately because BBC only shows the creative scenario.
    # 25% down, 7% rate, 30yr, +1.5%/yr taxes & insurance, minus 20% reserves.
    bank_gap = 0
    if monthly_rent > 0 and lp > 0:
        bank_loan = lp * 0.75
        r = 0.07 / 12
        bank_pi = bank_loan * r / (1 - (1 + r) ** -360)
        bank_piti = bank_pi + lp * 0.015 / 12
        bank_cf = monthly_rent * 0.80 - bank_piti  # 20% reserves applied to rent side
        bank_gap = round(max(0, creative_cf - bank_cf))  # how much more creative saves

    # CREATIVE TERMS — the offer structure to pitch (driven by dealType)
    if dt == 'sellerFinance':
        sf_offer = round(lp * (1.10 if is_mfh else 1.20))
        sf_down_pct = 0.10 if is_mfh else 0.12
        sf_down = round(sf_offer * sf_down_pct)
        creative_terms = f"${sf_offer:,} @ 0%, {int(sf_down_pct*100)}% down (${sf_down:,}), 30yr"
        creative_offer = sf_offer
        creative_down = sf_down
    elif dt == 'mortgageTakeover':
        creative_offer = round(lp)
        creative_down = 10000
        creative_terms = f"Take over existing loan, ~${creative_down:,} to seller"
    elif dt == 'fixAndFlip':
        # Richard's Cash Course rule: offer 70% of list price
        creative_offer = round(lp * 0.70)
        creative_down = 0  # cash deal — no down/loan
        creative_terms = f"Cash offer ${creative_offer:,} (70% of list — Cash Course rule)"
    else:
        creative_offer = round(op or lp)
        creative_down = round(down)
        creative_terms = "Cash offer / standard"

    # monthly_piti for the bank-gap pill's tooltip
    monthly_piti = round(expense_total)
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
    # Build full address with ZIP — used for narrow BBC autosearch + Zillow ZIP-filtered sold comps
    zip_code = addr.get('zip') or ''
    full_addr = f"{addr.get('street','')}, {addr.get('city','')}, {addr.get('state','')}"
    if zip_code:
        full_addr = f"{full_addr} {zip_code}"
    return {'address': full_addr,
            'state': addr.get('state',''), 'zip': zip_code,
            'type': addr.get('propertyType','') or 'Unknown',
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
            'deal_type_raw': dt,
            'creative_cf': creative_cf,
            'creative_offer': creative_offer,
            'creative_down': creative_down,
            'creative_terms': creative_terms,
            'beds': int(p.get('bed') or 0),
            'baths': int(float(p.get('bath') or 0)),
            'sqft': int(p.get('sqft') or 0),
            'lat': addr.get('latitude') or '',
            'lng': addr.get('longitude') or ''}

def tier(s):
    """Strict adherence to Richard's tier framework from deal-criteria.md:
    - Tier A: MFH 5+ units, $350K-$1.4M, DOM 90+, Seller Finance, creative pencils
    - Tier B: Cheap SFH <$150K, DOM 90+, Seller Finance, creative pencils
    - Tier MT: Mortgage Takeover (existing favorable loan), DOM 60+
    - Tier FF: Fix & Flip — cheap distressed listings, Cash Course '70% of list' rule
    - Tier C: Cash arbitrage SFH (rare in this search; mostly retired in favor of FF)
    Anything else is REJECT — Richard doesn't have a play for it."""
    pt = s['type'].lower()
    is_mfh_5plus = s['units'] >= 5
    is_mfh_24 = (2 <= s['units'] <= 4) or any(t in pt for t in ('duplex','triplex','fourplex','quadplex','quadruplex','plex'))
    is_mfh = is_mfh_5plus or is_mfh_24 or 'multi' in pt or 'apartment' in pt
    dt = s.get('deal_type', 'sellerFinance')
    cf_creative = s.get('creative_cf', 0)
    # Tier A — MFH Seller Finance Checkmate. Per Seller Finance Course:
    #   - 5+ units → always Tier A (FHA fails → DSCR-only → DSCR fails at 7%+ → SF
    #     is the only path; this is the canonical Checkmate Pitch territory).
    #   - 2-4 units (duplex/triplex/quadplex) → also Tier A IF the retail-buyer
    #     pool is eliminated (i.e., not 'retail desirable'). Per SF Course L957-
    #     L1074, Richard underwrites duplex/triplex/quadplex for SF when they're
    #     'college rental' / 'ugly' style — owner-occupants won't buy them with
    #     FHA, so it's investor-only, same SF logic applies. Operator confirms
    #     'not retail-desirable' via photo-check (added to playbook how_to).
    #   - Price floor lowered to $200K because the SF Course duplex/triplex
    #     examples ranged $190K-$800K, not just the 5+ unit $350K-$1.4M band.
    if is_mfh and 200_000 <= s['price'] <= 1_400_000 and s['dom'] >= 90 \
       and dt == 'sellerFinance' and cf_creative >= 100:
        return 'A'
    # Tier B — Cheap SFH Seller Finance (strict <$150K per deal-criteria.md).
    # SFH-only — 2-4 unit MFH at <$150K rolls up to Tier A, not B.
    if not is_mfh and s['price'] < 150_000 and s['dom'] >= 90 \
       and dt == 'sellerFinance' and cf_creative >= 100:
        return 'B'
    # Tier MT — Mortgage Takeover (existing favorable loan, DOM 60+)
    if dt == 'mortgageTakeover' and cf_creative >= 100 and s['dom'] >= 60:
        return 'MT'
    # Tier FF — Fix & Flip (Cash Course): cheap distressed listings, 70% rule
    # No CF gate (F&F is about ARV-to-MAO spread, not rental CF). Cap at $250K to
    # match Richard's repeated cheap-flip examples (Detroit/MI/OH $99K-$200K range).
    if dt == 'fixAndFlip' and s['dom'] >= 60 and s['price'] < 250_000:
        return 'FF'
    # Tier C — cash arbitrage SFH (Cash Course's section-8/turnkey path, not F&F)
    if cf_creative > 300 and s['dom'] >= 60 and dt not in ('sellerFinance', 'mortgageTakeover', 'fixAndFlip'):
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

# Excluded property types per Richard's primary-source guidance:
#   - vacant/land/lot/acreage/commercial/industrial → no structure to underwrite
#   - condo → Richard MT Course L1095: 'Not really interested in any condos.'
#     Exception (manual): MT plays where seller is underwater, or luxury beachfront.
#     Tim hand-picks those from BBC directly; daily triage default-excludes them.
NON_RESIDENTIAL_TYPES = ('vacant', 'land', 'lot', 'acreage', 'commercial', 'industrial', 'condo')
buckets = {'A':[], 'B':[], 'MT':[], 'FF':[], 'C':[], 'REJECT':[]}
land_skipped = 0
tracked_skipped = 0
for p in all_leads:
    # Deal Flow dedupe — if Tim has tracked this property at any status, drop from daily.
    # He manages it via Airtable Deal Flow kanban from here.
    if p.get('pid') in tracked_pids:
        tracked_skipped += 1
        continue
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
for t in ('A','B','MT','C'): buckets[t].sort(key=lambda x: (-x['creative_cf'], -x['dom']))
# Fix & Flip: sort by DOM desc (motivation) since CF isn't the relevant metric
buckets['FF'].sort(key=lambda x: -x['dom'])
print(f'\nA={len(buckets["A"])}  B={len(buckets["B"])}  MT={len(buckets["MT"])}  FF={len(buckets["FF"])}  C={len(buckets["C"])}  REJECT={len(buckets["REJECT"])}  Land-skipped={land_skipped}  Tracked-skipped={tracked_skipped}', file=sys.stderr)

# 5b. Surface agent info — cookie-free via BBC's contact-seller endpoint (the one
# behind the Create Offer modal). Cost: $0/unlock. Run on ALL Tier A/B/C deals.
unlock_targets = buckets['A'] + buckets['B'] + buckets['MT'] + buckets['FF'] + buckets['C']
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
    cls = {'A':'tier-A','B':'tier-B','MT':'tier-MT','FF':'tier-FF','C':'tier-C'}[t]
    playbook = {'A':'/rt-companion/strategy/tier-a-multifamily-checkmate.html',
                'B':'/rt-companion/strategy/tier-b-cheap-sfh-stale.html',
                'MT':'/rt-companion/strategy/mortgage-takeover.html',
                'FF':'/rt-companion/strategy/fix-and-flip.html',
                'C':'/rt-companion/strategy/tier-c-cash-buyer.html'}[t]
    bl = f'<div style="color:#56d364;font-size:13px;margin-top:6px;">🎯 BUYER MATCH: {", ".join(d["buyer_matches"])}</div>' if d['buyer_matches'] else ''
    z = f' <a class="zillow" href="{d["zillow"]}" target="_blank">Zillow ↗ (agent here)</a>' if d['zillow'] else ''
    # BBC autosearch: BBC's API only accepts City,State (verified 2026-05-13 — full
    # address returns 0 results). Pass street separately so the userscript can scroll
    # to the matching card after results render. Hash: #auto:City,State|street:Street
    parts = [p.strip() for p in d['address'].split(',') if p.strip()]
    # parts = ['51557 Forster Ln', 'Utica', 'MI 48316']  →  city='Utica', state='MI'
    street_part = parts[0] if parts else ''
    city_part = parts[1] if len(parts) >= 2 else ''
    state_part = (parts[2].split()[0] if len(parts) >= 3 and parts[2] else '')  # strip zip from "MI 48316"
    bbc_query = f'{city_part}, {state_part}' if city_part and state_part else d['address']
    bbc_hash_payload = f'{bbc_query}|street:{street_part}' if street_part else bbc_query
    # BBC search URL with #auto: hash — userscript on BBC side auto-fills + searches
    bbc_search = f'https://www.buyboxcartel.com/vip/lightning-leads#auto:{urllib.parse.quote(bbc_hash_payload)}'
    bbc_link = f' <a class="zillow" href="{bbc_search}" target="_blank">Search BBC ↗</a>'
    # Offer Oven prefill — uses the SAME creative_offer/creative_down/rent numbers
    # already computed in score(), so the dashboard pill, the call pitch, and the
    # Offer Oven verification all reconcile to the same restructured deal.
    balloon_yr = 7 if t == 'B' else 5
    rent_annual = round((d.get('monthly_rent') or 0) * 12)
    prefill_payload = {
        'price': d.get('creative_offer', 0), 'down': d.get('creative_down', 0),
        'rate': 0, 'term': 30, 'balloon': balloon_yr,
        'rent': rent_annual, 'assignment': 5000,
        'closing': round((d.get('creative_offer') or 0) * 0.01)
    }
    oven_url = f'https://www.hmhw.group/tools/offer-oven#prefill={urllib.parse.quote(json.dumps(prefill_payload))}'
    oven_link = f' <a class="zillow" href="{oven_url}" target="_blank">Verify in Offer Oven ↗</a>' if t in ('A','B','MT') else ''
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
    # Sold comps — Zillow ZIP-scoped + bedroom-filtered. Tim's prior feedback: area-only
    # search returned too many non-comp results. Filter to same ZIP + ±1 bedroom for real
    # comps. Format: /homes/recently_sold/{zip}/{beds}-_beds/ — uses Zillow's slug filters.
    zip_code = d.get('zip', '')
    beds = d.get('beds', 0)
    if zip_code and beds:
        sold_url = f'https://www.zillow.com/homes/recently_sold/{zip_code}_rb/{beds}-_beds/'
    elif zip_code:
        sold_url = f'https://www.zillow.com/homes/recently_sold/{zip_code}_rb/'
    else:
        sold_url = ''
    sold_link = f' <a class="zillow" href="{sold_url}" target="_blank">Sold comps ↗</a>' if sold_url else ''
    rent_link = ''  # Zillow Rent Zestimate on the property page (already linked) covers this
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
    # CREATIVE CF BANNER — the call hook. Reads: "After restructuring, this deal
    # cash-flows $X/mo. Pitch to seller: $OFFER at 0%, $DOWN down, 30yr."
    cc = d.get('creative_cf', 0)
    creative_banner = (
        f'<div style="margin:6px 0 8px;padding:8px 12px;background:linear-gradient(90deg,#0d2818,#0d1f24);'
        f'border:1px solid #1a4d2e;border-radius:6px;font-size:14px;line-height:1.4;">'
        f'<span style="color:#56d364;font-weight:700;font-size:16px;">✅ Creative CF +${cc:,}/mo</span>'
        f'<span style="color:#8b949e;"> &nbsp;·&nbsp; </span>'
        f'<span style="color:#e6edf3;">{d.get("creative_terms","")}</span>'
        f'</div>'
    )
    # TRACK PROPERTY button — prefilled Airtable link. Tapping creates a Deal Flow
    # record so the property drops out of tomorrow's daily. Tim manages it through
    # the Airtable kanban from here. Uses Airtable's URL prefill (?prefill_Field=val).
    tier_label = {'A':'A (MFH SF)','B':'B (Cheap SFH SF)','MT':'MT (Mortgage Takeover)','FF':'FF (Fix & Flip)','C':'C (Cash)'}.get(t, '')
    dt_label_at = {'sellerFinance':'Seller Finance','mortgageTakeover':'Mortgage Takeover','fixAndFlip':'Fix & Flip','cash':'Cash'}.get(d.get('deal_type',''), '')
    addr_parts = [p.strip() for p in d['address'].split(',') if p.strip()]
    city_at = addr_parts[1] if len(addr_parts) >= 2 else ''
    state_at = (addr_parts[2].split()[0] if len(addr_parts) >= 3 else d.get('state',''))
    agent_name_at = (d.get('agent') or {}).get('name', '')
    agent_phone_at = (d.get('agent') or {}).get('phone', '')
    track_params = {
        'prefill_Address': d['address'],
        'prefill_PID': d.get('pid',''),
        'prefill_Status': 'Triage',
        'prefill_Tier': tier_label,
        'prefill_Deal Type': dt_label_at,
        'prefill_State': state_at,
        'prefill_City': city_at,
        'prefill_List Price': str(int(d['price'])) if d.get('price') else '',
        'prefill_Creative CF': str(int(cc)) if cc else '',
        'prefill_DOM': str(d.get('dom','')),
        'prefill_Agent Name': agent_name_at,
        'prefill_Agent Phone': agent_phone_at,
        'prefill_Zillow URL': d.get('zillow','') or '',
        'prefill_Briefing Date': date_iso,
        'prefill_First Tracked': date_iso,
    }
    track_qs = '&'.join(f'{urllib.parse.quote(k)}={urllib.parse.quote(v)}' for k,v in track_params.items() if v)
    track_url = f'https://airtable.com/{AT_BASE}/{DF_TABLE}?{track_qs}'
    track_link = f' <a class="zillow" href="{track_url}" target="_blank" style="background:#1a4d2e;color:#56d364;padding:3px 8px;border-radius:6px;font-weight:600;border:1px solid #1a4d2e;">+ Track Property</a>'
    return f'<div class="deal {cls}"><div class="addr">{d["address"]}{pipe}{status_pill if d.get("status_state") != "active" else ""}</div><div class="meta">{d["units"]} units · {d["type"]}</div>{creative_banner}<div class="nums">{status_pill if d.get("status_state") == "active" else ""}{dt_pill}{pt_pill}<span class="pill">${d["price"]:,.0f}</span><span class="pill">{cf_label} ${d["cf"]:,.0f}/mo</span>{bank_gap_pill}<span class="pill">CoC {d["coc"]}%</span><span class="pill">DOM {d["dom"]} {d["dom_flag"]}</span>{tz_pill}</div><a class="play-link" href="{playbook}">Open Tier {t} playbook →</a>{track_link}{z}{bbc_link}{oven_link}{rent_link}{sold_link}{bl}{agent_block}</div>'

section_a = ('<h2>🎯 TIER A — Multifamily Seller-Finance Checkmate ($350K-$1.4M, 5+ units, DOM 90+, DSCR fails)</h2>' + ''.join(render_deal(d,'A') for d in buckets['A'])) if buckets['A'] else ''
section_b = ('<h2>🏘️ TIER B — Cheap SFH Stale Seller Finance (<$100K, DOM 90+, DSCR fails)</h2>' + ''.join(render_deal(d,'B') for d in buckets['B'])) if buckets['B'] else ''
section_mt = ('<h2>🔑 MORTGAGE TAKEOVER — Favorable existing loan (positive CF at assumed rate, DOM 60+)</h2>' + ''.join(render_deal(d,'MT') for d in buckets['MT'])) if buckets['MT'] else ''
section_ff = ('<h2>🔨 FIX &amp; FLIP — Cheap distressed cash plays (Cash Course 70% rule, &lt;$250K, DOM 60+)</h2>' + ''.join(render_deal(d,'FF') for d in buckets['FF'])) if buckets['FF'] else ''
section_c = ('<h2>💵 TIER C — Cash-Comparable SFH (cash arbitrage, NOT seller finance)</h2>' + ''.join(render_deal(d,'C') for d in buckets['C'])) if buckets['C'] else ''
rej_section = ''
if buckets['REJECT']:
    rej_lines = ''.join(f'<div class="rejected">{s["address"]} — CF: ${s["cf"]:,.0f} (DOM {s["dom"]})</div>' for s in buckets['REJECT'][:15])
    rej_section = f'<h2>❌ REJECTED — {pushed} pushed to <a href="https://airtable.com/{AT_BASE}/{WL_TABLE}">Watchlist</a></h2>{rej_lines}'

agent_indicator = f' · 🔓 {unlocks_succeeded} agents captured (free)' if unlocks_succeeded else ''
summary = f'{len(all_leads)} leads · {len(buckets["A"])} Tier A · {len(buckets["B"])} Tier B · {len(buckets["MT"])} MT · {len(buckets["FF"])} FF · {len(buckets["C"])} Tier C · {pushed} → watchlist{agent_indicator}'
CSS = 'body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:12px;font-size:15px;line-height:1.5;}h2{font-size:14px;color:#8b949e;text-transform:uppercase;letter-spacing:0.04em;margin:18px 0 8px;}.summary{background:#1c2128;border:1px solid #30363d;border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:14px;}.deal{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:10px;}.deal .addr{font-weight:600;font-size:15px;margin-bottom:4px;}.deal .meta{font-size:13px;color:#8b949e;margin-bottom:6px;}.deal .nums{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;}.pill{background:#1c2128;border:1px solid #30363d;border-radius:12px;padding:2px 9px;font-size:12px;color:#8b949e;}.play-link{display:inline-block;padding:8px 12px;background:#58a6ff;color:#0d1117;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;margin-top:4px;}.tier-A{border-left:3px solid #ff7b72;}.tier-B{border-left:3px solid #d2a8ff;}.tier-MT{border-left:3px solid #79c0ff;}.tier-FF{border-left:3px solid #f0883e;}.tier-C{border-left:3px solid #56d364;}a.zillow{color:#58a6ff;font-size:12px;margin-left:8px;}.rejected{color:#8b949e;font-size:13px;padding:4px 0;}.date{color:#8b949e;font-size:13px;}.addr-copy{display:inline-block;margin-left:8px;padding:2px 9px;font-size:12px;background:#1c2128;border:1px solid #30363d;color:#58a6ff;border-radius:12px;cursor:pointer;font-family:inherit;}.addr-copy:hover{background:#21262d;}.addr-copy.copied{background:#1a4d2e;color:#56d364;border-color:#1a4d2e;}'
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
html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Triage {date_iso}</title><style>{CSS}</style></head><body><p class="date">📋 {date_human} · TN/TX/GA/OH/MI &nbsp;·&nbsp; <a href="https://www.buyboxcartel.com/vip/lightning-leads" target="_blank" style="color:#58a6ff;">Open BBC Lightning Leads ↗</a></p><div class="summary">{summary}</div>{section_a}{section_b}{section_mt}{section_ff}{section_c}{rej_section}' + CLOCK_JS + '</body></html>'

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
                       ('FF','Fix & Flip (70% Rule)','🔨'),
                       ('C','Tier C — Cash Buyer','💵')]:
    if not buckets[t]: continue
    print(f'\n{emoji} {name} ({len(buckets[t])}):')
    for i, d in enumerate(buckets[t], 1):
        bm = f'  🎯 BUYER MATCH: {", ".join(d["buyer_matches"])}' if d['buyer_matches'] else ''
        print(f'{i}. {d["address"]} | {d["units"]}u | List ${d["price"]:,.0f} | ✅ Creative CF +${d.get("creative_cf",0):,}/mo | Bank CF ${d["cf"]:,.0f}/mo | DOM {d["dom"]} {d["dom_flag"]}{bm}')
        print(f'   Pitch: {d.get("creative_terms","")}')
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
