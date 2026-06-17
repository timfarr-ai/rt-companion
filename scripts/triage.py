import urllib.request, urllib.error, urllib.parse, http.cookiejar, json, base64, sys, re, time
from datetime import datetime, date, timedelta

import os

BBC_EMAIL = os.environ['BBC_EMAIL']
BBC_PASS  = os.environ['BBC_PASS']
AT_TOKEN  = os.environ['AT_TOKEN']
AT_BASE   = os.environ.get('AT_BASE', 'appv6jhEzhGaAITcs')
KB_TABLE  = os.environ.get('KB_TABLE', 'tblh40Mq2rHwfe1I2')
WL_TABLE  = os.environ.get('WL_TABLE', 'tbluV0qAWYNAFkD5S')
DF_TABLE  = os.environ.get('DF_TABLE', 'tblk9fSDyWjpftLwm')  # Deal Flow — tracked deals
RJ_TABLE  = os.environ.get('RJ_TABLE', 'tblMewF15iP58sJHm')  # Rejected by Tim — feedback loop
BBC_PROXY_URL = os.environ.get('BBC_PROXY_URL', '')  # Cloudflare Worker URL (Save-to-BBC-Pipeline)
BBC_PROXY_SECRET = os.environ.get('BBC_PROXY_SECRET', '')  # HMAC secret shared with Worker
GH_PAT    = os.environ['GH_PAT']
GH_REPO   = os.environ.get('GH_REPO', 'timfarr-ai/rt-companion')

def clean_image_urls(raw, limit=8):
    """Extract up to `limit` string photo URLs from BBC image entries, DROPPING any
    Google Street View Static URLs (maps.googleapis.com). Those arrive from the
    upstream provider pre-signed with THEIR Maps API key embedded in the URL — and
    this briefing is published to a PUBLIC GitHub Pages repo, so republishing them
    trips GitHub secret scanning (and exposes a third-party key). The keyless
    '📍 Street View ↗' map link still covers Richard's neighborhood eye-check.
    See secret-scanning remediation 2026-06-01."""
    out = []
    for img in (raw or []):
        u = img if isinstance(img, str) else (img.get('url') or '')
        if u and 'maps.googleapis.com' not in u:
            out.append(u)
            if len(out) >= limit:
                break
    return out
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

BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

def http_req(url, method='GET', headers=None, json_body=None, use_opener=False):
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers = (headers or {}) | {'Content-Type': 'application/json'}
    headers = (headers or {}) | {'User-Agent': BROWSER_UA}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with (opener.open if use_opener else urllib.request.urlopen)(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

# BBC relay: when BBC_PROXY_URL is set and BBC blocks direct access (e.g. Anthropic
# cloud sandbox IPs), route BBC API calls through the Cloudflare Worker which has
# allowed IPs.  The relay endpoint /bbc-relay accepts HMAC-signed requests and
# proxies them to BBC using the Worker's own cached BBC session.
if BBC_PROXY_URL and BBC_PROXY_SECRET:
    import hmac as _hmac_mod, hashlib as _hash_mod
    _BBC_BASE = 'https://www.buyboxcartel.com'
    _RELAY_URL = BBC_PROXY_URL.rstrip('/') + '/bbc-relay'
    _http_req_orig = http_req
    def http_req(url, method='GET', headers=None, json_body=None, use_opener=False):
        if url.startswith(_BBC_BASE + '/api/'):
            path = url[len(_BBC_BASE):]
            relay_payload = {'path': path, 'method': method}
            if json_body is not None:
                relay_payload['body'] = json_body
            if headers:
                passthrough = {k: v for k, v in headers.items()
                               if k.lower() == 'accept'}
                if passthrough:
                    relay_payload['headers'] = passthrough
            body_bytes = json.dumps(relay_payload).encode()
            sig = _hmac_mod.new(BBC_PROXY_SECRET.encode(), body_bytes,
                                _hash_mod.sha256).hexdigest()
            req = urllib.request.Request(
                _RELAY_URL, data=body_bytes, method='POST',
                headers={'Content-Type': 'application/json',
                         'X-Signature': sig,
                         'User-Agent': BROWSER_UA})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()
            except Exception as e:
                return 0, str(e).encode()
        return _http_req_orig(url, method=method, headers=headers,
                              json_body=json_body, use_opener=use_opener)

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

# 3. Existing watchlist — PAGINATED. Was a single 100-row page, which silently
# capped dedup once the watchlist grew past 100 'Watching' rows → the reject-push
# (step 6) then re-POSTed hundreds of already-watched addresses every run (the
# multi-minute grind). Now walks all pages like the Deal Flow / Rejected fetches.
existing_addrs = set()
_wl_base = f'https://api.airtable.com/v0/{AT_BASE}/{WL_TABLE}?filterByFormula=%7BStatus%7D%3D%27Watching%27&pageSize=100'
url = _wl_base
while url:
    code, body = http_req(url, headers={'Authorization': f'Bearer {AT_TOKEN}'})
    if code != 200: break
    data = json.loads(body)
    for r in data.get('records', []):
        a = r['fields'].get('Address', '').strip().lower()
        if a: existing_addrs.add(a)
    offset = data.get('offset')
    url = f'{_wl_base}&offset={offset}' if offset else None
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

# 3c. Fetch rejected PIDs from 'Rejected by Tim' — Tim's manual filter feedback.
# Existence = permanent exclude. Reasons collected feed the weekly optimization agent.
rejected_pids = set()
url = f'https://api.airtable.com/v0/{AT_BASE}/{RJ_TABLE}?pageSize=100&fields%5B%5D=PID'
while url:
    code, body = http_req(url, headers={'Authorization': f'Bearer {AT_TOKEN}'})
    if code != 200: break
    data = json.loads(body)
    for r in data.get('records', []):
        pid = (r.get('fields') or {}).get('PID', '').strip()
        if pid: rejected_pids.add(pid)
    offset = data.get('offset')
    url = f'https://api.airtable.com/v0/{AT_BASE}/{RJ_TABLE}?pageSize=100&fields%5B%5D=PID&offset={offset}' if offset else None
print(f'Rejected by Tim: {len(rejected_pids)} PIDs permanently excluded', file=sys.stderr)

# 3d. Fetch BBC BuyBoxes — state×strategy buyer-activity signal. Used as a dispo-
# confidence pill on each card. NOT actual buyer contacts (those live in /vip/buyerslist);
# this is the market signal: "is BBC's buyer network active for {strategy} in {state}?"
# Returns 3 buckets: fixFlipBuyer / creativeBuyer / sectionEightBuyer; each row has
# bbname (state, lowercase) + is_activeBuyer (bool). One call per run, ~1KB response.
STATE_CODE_TO_NAME = {
    'AL':'alabama','AK':'alaska','AZ':'arizona','AR':'arkansas','CA':'california',
    'CO':'colorado','CT':'connecticut','DE':'delaware','FL':'florida','GA':'georgia',
    'HI':'hawaii','ID':'idaho','IL':'illinois','IN':'indiana','IA':'iowa','KS':'kansas',
    'KY':'kentucky','LA':'louisiana','ME':'maine','MD':'maryland','MA':'massachusetts',
    'MI':'michigan','MN':'minnesota','MS':'mississippi','MO':'missouri','MT':'montana',
    'NE':'nebraska','NV':'nevada','NH':'new hampshire','NJ':'new jersey','NM':'new mexico',
    'NY':'new york','NC':'north carolina','ND':'north dakota','OH':'ohio','OK':'oklahoma',
    'OR':'oregon','PA':'pennsylvania','RI':'rhode island','SC':'south carolina',
    'SD':'south dakota','TN':'tennessee','TX':'texas','UT':'utah','VT':'vermont',
    'VA':'virginia','WA':'washington','WV':'west virginia','WI':'wisconsin','WY':'wyoming',
    'DC':'washington, d.c.',
}
buyer_signals = {'creative': {}, 'fixflip': {}, 'section8': {}}
code, body = http_req('https://www.buyboxcartel.com/api/buyBox/get-info?state=',
                      headers={'Authorization': f'Bearer {bbc_token}'}, use_opener=True)
if code == 200:
    try:
        bb_data = json.loads(body)
        for row in bb_data.get('creativeBuyer') or []:
            buyer_signals['creative'][(row.get('bbname') or '').lower()] = bool(row.get('is_activeBuyer'))
        for row in bb_data.get('fixFlipBuyer') or []:
            buyer_signals['fixflip'][(row.get('bbname') or '').lower()] = bool(row.get('is_activeBuyer'))
        for row in bb_data.get('sectionEightBuyer') or []:
            buyer_signals['section8'][(row.get('bbname') or '').lower()] = bool(row.get('is_activeBuyer'))
        a_cr = sum(1 for v in buyer_signals['creative'].values() if v)
        a_ff = sum(1 for v in buyer_signals['fixflip'].values() if v)
        a_s8 = sum(1 for v in buyer_signals['section8'].values() if v)
        print(f'BuyBoxes: {a_cr} creative + {a_ff} fix-flip + {a_s8} section-8 active states', file=sys.stderr)
    except Exception as e:
        print(f'BuyBoxes parse failed: {e}', file=sys.stderr)
else:
    print(f'BuyBoxes fetch failed ({code})', file=sys.stderr)

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

# 4a. SECOND PASS — Off-market MT only. Per Richard's MT Course L1011-1024, the
# $9K-style takeover deals tend to be on REMOVED listings (seller couldn't profit
# at retail, pulled the listing). Active-only search misses these.
print(f'\nOff-market MT pass...', file=sys.stderr)
om_count_before = len(all_leads)
for state in STATES:
    payload = {'search_query': state,
               'deal_type': ['mortgageTakeover'],
               'market_status': 'Off Market', 'page': 1, 'limit': 25,
               'sort_field': 'daysOnMarket', 'sort_order': 'desc',
               'price_range': {'max': 1_400_000}}
    code, body = http_req('https://www.buyboxcartel.com/api/lightning-leads/search-property',
                          method='POST', json_body=payload,
                          headers={'Accept': 'text/event-stream',
                                   'Authorization': f'Bearer {bbc_token}'},
                          use_opener=True)
    if code != 200:
        print(f'{state} (off-market): HTTP {code} — skipping', file=sys.stderr); continue
    text = body.decode(errors='ignore')
    state_before = len(all_leads)
    for block in text.split('\n\n'):
        if 'event: complete' in block:
            for line in block.split('\n'):
                if line.startswith('data:'):
                    try:
                        d = json.loads(line[5:])
                        for p in d.get('propertyDetails', []):
                            p['_off_market'] = True  # tag for later filtering / labeling
                            all_leads.append(p)
                    except: pass
            break
    delta = len(all_leads) - state_before
    if delta:
        print(f'  {state} (off-market): +{delta}', file=sys.stderr)
print(f'Off-market MT pass: +{len(all_leads) - om_count_before} listings added', file=sys.stderr)

# 4c. DEDICATED MFH PASS — Richard's bread-and-butter (Tier A). The blind primary
# pull is DOM-sorted and capped at 75/state, so genuine multi-family (5+ unit AND
# 2-4 unit plexes) gets crowded out by cheap stale SFH — empirically only 1-7 of 75
# slots were MFH. BBC's /search-property accepts `property_type` ONLY as an ARRAY of
# lowercase codes; the value for multi-family is "multi" (the display string
# "Multi Family" is silently ignored — confirmed live 2026-05-30 against OH/TN, where
# ["multi"] returned 75/75 MFH vs 7 and 1 in the blind pull). deal_type kept broad so
# MFH that BBC tagged MT/FF also enters and gets routed by tier(). Overlap with the
# primary pull is removed by the pid-dedupe in the scoring loop below.
print(f'\nDedicated MFH pass (property_type=["multi"])...', file=sys.stderr)
mfh_count_before = len(all_leads)
for state in STATES:
    payload = {'search_query': state,
               'deal_type': ['sellerFinance', 'mortgageTakeover', 'fixAndFlip'],
               'property_type': ['multi'],
               'market_status': 'Active', 'page': 1, 'limit': 75,
               'sort_field': 'daysOnMarket', 'sort_order': 'desc',
               'price_range': {'max': 1_400_000}}
    code, body = http_req('https://www.buyboxcartel.com/api/lightning-leads/search-property',
                          method='POST', json_body=payload,
                          headers={'Accept': 'text/event-stream',
                                   'Authorization': f'Bearer {bbc_token}'},
                          use_opener=True)
    if code != 200:
        print(f'{state} (mfh): HTTP {code} — skipping', file=sys.stderr); continue
    text = body.decode(errors='ignore')
    state_before = len(all_leads)
    for block in text.split('\n\n'):
        if 'event: complete' in block:
            for line in block.split('\n'):
                if line.startswith('data:'):
                    try:
                        d = json.loads(line[5:])
                        for p in d.get('propertyDetails', []):
                            p['_mfh_pass'] = True  # tag for later labeling
                            all_leads.append(p)
                    except: pass
            break
    delta = len(all_leads) - state_before
    if delta:
        print(f'  {state} (mfh): +{delta}', file=sys.stderr)
print(f'Dedicated MFH pass: +{len(all_leads) - mfh_count_before} listings added (pre-dedupe)', file=sys.stderr)

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

# Claude vision — analyze BBC property photos for REO/condition/distress signals
# that BBC's API doesn't expose. Closes the detection gap that scraping Zillow
# can't (PerimeterX blocks). Cost: Haiku 4.5, ~$0.02/property (all photos) × ~100
# quals/day = ~$2/day. Only runs on qualified properties (post-tier, post-agent-unlock).
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
VISION_MODEL = 'claude-haiku-4-5-20251001'
VISION_PROMPT = '''You are evaluating a residential listing for a creative-finance wholesaler (Richard Taylor's HMHW method). This is a SELLER-FINANCE / BUY-AND-HOLD method: the property will be rented to a tenant, NOT flipped. So the ONE question that matters is: can this house be rented to a tenant roughly as-is, or does it need real rehab BEFORE a tenant could move in?

A dated, cosmetically tired, or freshly-renovated house is FINE — tenants live in dated houses every day. Only properties that genuinely need rehab before they are habitable should leave the seller-finance lane.

CRITICAL: Judge ONLY what the photos actually show. If you can see only the exterior, do NOT assume or invent interior condition — base your score on visible evidence and lean toward "qualify" when the interior is not shown. Never describe interior wear you cannot see.

Given these property photos, return ONLY a single JSON object with these fields:
- condition (int 1-5): 5=move-in / rent-ready; 4=minor cosmetic (paint, landscaping) but rentable as-is; 3=dated or needs a cosmetic refresh but still rentable to a tenant without major work; 2=needs real rehab before a tenant could move in (kitchen/bath/floors/systems gutted or missing); 1=heavy gut / structural / fire / water damage / uninhabitable
- reo_or_auction (bool): visible REO sign, auction sign, bank-owned marketing, lockbox-only, completely empty/staged-for-auction look
- commercial_or_unusual (bool): commercial use, warehouse/industrial, vacant lot photos labelled as a house, mobile home on leased lot
- recommended_action (string): "qualify" | "demote_to_ff" | "reject"
  - "qualify" = rentable as-is or with only cosmetic work (condition 3-5) — Richard's seller-finance method applies
  - "demote_to_ff" = needs real rehab before it can be rented (condition 2) — route to Fix & Flip
  - "reject" = condition 1, OR reo_or_auction, OR commercial_or_unusual
- notes (string, max 100 chars): brief reasoning visible to operator; state what you actually saw

Output ONLY the JSON. No prose, no markdown fences.'''

vision_cache = {}  # PID → analysis dict
vision_calls = 0
vision_skipped = 0

MAX_VISION_PHOTOS = 8  # enough to include interior shots (kills exterior-only hallucination)
                        # without the 10x latency/cost blowup of sending every photo. Most BBC
                        # listings have <=8 photos, so this is effectively "all photos" for them.

def analyze_property_vision(p):
    """Send the listing's photos to Claude vision; return analysis dict or None on
    failure. Caches per-PID for the run. Skips if ANTHROPIC_API_KEY missing or
    no images on the listing.

    Sends ALL available photos (capped at MAX_VISION_PHOTOS), not just the first 2 —
    the first 2 are usually exteriors, which led vision to hallucinate interior
    condition and over-demote rentable houses (see false-demote audit 2026-05-25).
    Interior photos are what actually determine 'rentable as-is vs needs rehab'."""
    global vision_calls
    pid = p.get('pid')
    if not pid or not ANTHROPIC_API_KEY: return None
    if pid in vision_cache: return vision_cache[pid]
    images = p.get('images') or []
    if not images: return None
    photo_urls = [img if isinstance(img, str) else img.get('url') for img in images[:MAX_VISION_PHOTOS]]
    photo_urls = [u for u in photo_urls if u]
    if not photo_urls: return None
    content = []
    for url in photo_urls:
        content.append({'type': 'image', 'source': {'type': 'url', 'url': url}})
    content.append({'type': 'text', 'text': VISION_PROMPT})
    body = {
        'model': VISION_MODEL,
        'max_tokens': 200,
        'messages': [{'role': 'user', 'content': content}]
    }
    code, resp = http_req('https://api.anthropic.com/v1/messages', method='POST',
                          json_body=body,
                          headers={'x-api-key': ANTHROPIC_API_KEY,
                                   'anthropic-version': '2023-06-01'})
    vision_calls += 1
    if code != 200:
        return None
    try:
        data = json.loads(resp)
        text = data['content'][0]['text'].strip()
        # Strip markdown fences if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        analysis = json.loads(text)
        vision_cache[pid] = analysis
        return analysis
    except Exception as e:
        print(f'  vision parse error for {pid}: {e}', file=sys.stderr)
        return None

def fetch_property_history(zpid):
    """Fetch full Zillow-equivalent property detail (including priceHistory) for a
    given zpid via BBC's /api/searchProperty?zpid endpoint. Returns dict with
    last-sold price/date + flip markup analysis, or None on failure.

    Used to detect 'investor flip relist' pattern: property was bought cheap recently,
    renovated, and relisted with a 30%+ markup. These sellers want cash to roll into
    the next flip — NOT receptive to seller finance, despite BBC's stale-DOM signal
    (BBC's DOM is cumulative across relists; doesn't differentiate).

    Returns:
      {
        'last_sold_price': int | None,
        'last_sold_date': 'YYYY-MM-DD' | None,
        'months_since_sale': int | None,
        'flip_markup_pct': float | None,   # 0.389 = 38.9% markup over last sold
        'is_recent_flip': bool,             # True if markup >= 35% AND sold within 24mo
      }"""
    if not zpid: return None
    code, body = http_req(f'https://www.buyboxcartel.com/api/searchProperty?zpid={zpid}',
                          method='GET', use_opener=True,
                          headers={'Authorization': f'Bearer {bbc_token}'})
    if code != 200: return None
    try:
        data = json.loads(body)
    except: return None
    current_price = float(data.get('price') or 0)
    price_history = data.get('priceHistory') or []
    # Find most recent 'Sold' event (Public Record or similar)
    sold_events = [e for e in price_history if (e.get('event') or '').lower() == 'sold' and (e.get('price') or 0) >= 20000]
    if not sold_events or current_price <= 0:
        return {'last_sold_price': None, 'last_sold_date': None,
                'months_since_sale': None, 'flip_markup_pct': None, 'is_recent_flip': False}
    most_recent = max(sold_events, key=lambda e: e.get('time') or 0)
    last_sold_price = float(most_recent.get('price') or 0)
    last_sold_date = most_recent.get('date') or ''
    # Compute months since sale
    months_since = None
    try:
        sale_dt = datetime.strptime(last_sold_date, '%Y-%m-%d').date()
        today = date.today()
        months_since = (today.year - sale_dt.year) * 12 + (today.month - sale_dt.month)
    except Exception:
        pass
    markup = (current_price - last_sold_price) / last_sold_price if last_sold_price > 0 else None
    is_flip = bool(markup and markup >= 0.35 and months_since is not None and months_since <= 24)
    # Brokerage + official listing-agent attribution (used by OpenPhone contact
    # save → contact.company shows the brokerage Tim's calling).
    attrib = data.get('attributionInfo') or {}
    return {'last_sold_price': int(last_sold_price), 'last_sold_date': last_sold_date,
            'months_since_sale': months_since, 'flip_markup_pct': markup, 'is_recent_flip': is_flip,
            'description': data.get('description') or '',
            'brokerage': (data.get('brokerageName') or attrib.get('brokerName') or '').strip(),
            'mls_name': (attrib.get('mlsName') or '').strip(),
            'mls_agent_name': (attrib.get('agentName') or '').strip(),
            'mls_agent_email': (attrib.get('agentEmail') or '').strip()}

# Description-keyword filters — terminal disqualifiers + flip-vocab signals
# discovered 2026-05-15 from 9904 Aetna Rd Cleveland OH listing that had
# "****NO ASSIGNMENT CONTRACTS****" in description (which mechanically breaks
# HMHW assignment-wholesale model) plus "Freshly Updated... move-in-ready
# updates completed recently" (clear flip language). These signals fire when
# BBC's priceHistory has no Sold event (so the markup-based flip detector misses).
TERMINAL_DESC_KEYWORDS = [
    'no assignment',          # explicit method disqualifier
    'no assignments',
    'no wholesalers', 'no wholesaler', 'no wholesale',
    'no investors', 'no investor offers',
    'principal buyers only',
    'end buyers only',
    'owner-occupants only', 'owner occupants only',
    'no double close', 'no double-close',
    # POST-foreclosure / institutional auction — bank is the seller, cash-only,
    # no contingencies. Distinct from PRE-auction (owner still on title, auction
    # date set) which is a top-priority MT/subject-to lead (see risks.md #20).
    # Each phrase below describes a state only possible AFTER foreclosure, or is
    # terminology only auction houses use — none fire on pre-auction MLS text.
    # Caught 3849 E Antisdale (Cleveland REO auction surfaced 2026-05-26).
    'foreclosure deed', 'foreclosure has been recorded',
    'bank owned', 'bank-owned',
    'reo property', 'reo sale', 'is reo',  # avoid bare 'reo' (matches 'stereo')
    'no buyer premium', 'buyer premium', "buyer's premium",
    'starting bid',
    'auction property', 'live auction', 'public auction', 'online auction',
    'no inspection or financing contingencies',
    'sold as-is, where-is', 'as-is, where-is', 'as is, where is', 'as-is/where-is',
]
FLIP_DESC_KEYWORDS = [
    'freshly updated', 'newly updated', 'recently updated',
    'completely renovated', 'fully renovated', 'totally renovated',
    'move-in ready', 'move in ready',
    'turnkey rental', 'turn-key rental', 'turn key rental',
    'updates completed recently', 'just renovated', 'just completed',
    'brand new', 'brand-new',
    'fresh paint', 'new flooring', 'new kitchen', 'new bathroom',
    'portfolio package',  # investor offloading multiple — Tacoma + Aetna pattern
]

def desc_terminal_match(description):
    """Returns the first terminal keyword found in description, or None.
    Case-insensitive whole-substring match."""
    if not description: return None
    desc_lower = description.lower()
    for kw in TERMINAL_DESC_KEYWORDS:
        if kw in desc_lower: return kw
    return None

def desc_flip_signals(description):
    """Returns list of flip-vocab keywords found. 3+ = strong flip signal."""
    if not description: return []
    desc_lower = description.lower()
    return [kw for kw in FLIP_DESC_KEYWORDS if kw in desc_lower]

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
def potential_assignment_fee(tier_letter, creative_offer, price):
    """Richard's per-tier assignment-fee estimate (gross, before any JV split).

    Based on primary-source examples from the HMHW transcripts:
      - Tier A (MFH SF):  SF L1134 — $100K+ on multifamily ($1.3M/72-bed). SF L22:
                           "every assignment fee above $50K comes from seller financing."
                           Estimate: 7.5% of offer, floor $25K, cap $200K.
      - Tier B (cheap SFH SF): SF L96 — $25K assignment on $325K SF SFH.
                           Estimate: 7.5% of offer, floor $5K, cap $25K.
      - MT (Mortgage Takeover): typical $5-10K spread on takeover. Fixed $7.5K.
      - FF (Cash flip): Cash L335 — $5K Offer Oven default. Cash L1000 — $11K Orlando.
                           Estimate: 5% of offer, floor $5K, cap $15K.
      - C (Cash arbitrage): Similar to FF but smaller. Floor $3K, cap $10K.

    Returns gross fee (solo dispo). If user goes through Grand In Taylor JV,
    typical 50/50 split — Tim's net is ~half. The card surfaces gross + Tim
    mentally halves for JV scenarios.
    """
    offer = creative_offer or price or 0
    if tier_letter == 'A':
        return max(25000, min(int(offer * 0.075), 200000))
    elif tier_letter == 'B':
        return max(5000, min(int(offer * 0.075), 25000))
    elif tier_letter == 'MT':
        return 7500
    elif tier_letter == 'FF':
        return max(5000, min(int(offer * 0.05), 15000))
    elif tier_letter == 'C':
        return max(3000, min(int(offer * 0.04), 10000))
    return 5000

def units(p):
    """Return unit count for the property. Trust explicit numbers and named plexes
    (duplex/triplex/quadplex). For generic 'Multi Family' with NO explicit count,
    do a dimensional sanity check — BBC frequently mislabels SFH listings as MFH
    (verified 2026-05-14: 1001 Starboard Dr Greensboro = 3bd/2ba/1784sqft SFH but
    BBC propertyType='Multi Family'). Old code blindly defaulted to 4 units."""
    for k in ('numberOfUnits','units','unitCount','totalUnits'):
        v = p.get(k) or (p.get('calculatedData') or {}).get(k)
        if v:
            try: return int(v)
            except: pass
    pt = (p.get('address') or {}).get('propertyType','').lower()
    # Named plexes — trust the count baked into the type label
    if 'duplex' in pt: return 2
    if 'triplex' in pt: return 3
    if 'fourplex' in pt or 'quadplex' in pt or 'quadruplex' in pt: return 4
    # Generic 'Multi Family' or 'plex' without an explicit count → dimensional check.
    # Real 4-unit MFH typically has 6-8+ bedrooms and 2800+ sqft total. Below that,
    # BBC's 'Multi Family' label is almost certainly a misclassified SFH/Townhouse.
    if 'multi' in pt or 'plex' in pt:
        bed = int(p.get('bed') or 0)
        sqft = int(p.get('sqft') or 0)
        if bed >= 8 or sqft >= 3500: return 4
        if bed >= 6 or sqft >= 2800: return 3
        if bed >= 4 or sqft >= 2000: return 2
        return 1  # 1001 Starboard-style: BBC says MFH but data is SFH-shaped
    return 1

def score(p):
    cd = p.get('calculatedData', {})
    cf = float(cd.get('monthlyCashFlow') or 0)
    lp = float(cd.get('listPrice') or 0)
    op = float(cd.get('offerPrice') or lp * 1.10)
    down = float(cd.get('downPayment') or op * 0.10)
    dom = int(p.get('daysOnMarket') or 0)
    addr = p.get('address', {})
    dt = cd.get('dealType', 'sellerFinance')
    pt_lower = (addr.get('propertyType') or '').lower()
    # 'apartment' (singular) is BBC's label for individual condo-style units, NOT
    # whole apartment buildings — those are 'Multi Family'. So we don't count
    # 'apartment' as MFH here; individual apartments get filtered earlier via
    # NON_RESIDENTIAL_TYPES (alongside condos).
    is_mfh = (cd.get('numberOfUnits') and int(cd.get('numberOfUnits')) >= 5) or 'multi' in pt_lower or 'plex' in pt_lower or 'duplex' in pt_lower or 'triplex' in pt_lower
    # BBC fields verified via API probe 2026-05-13: monthlyRent NOT in payload, but
    # piti (full PITI) and monthlyPayment (P&I only) are. Back-calc rent from CF:
    #   cf = rent − piti − (rent × 0.20)   →   rent = (cf + piti) / 0.80
    piti = float(cd.get('piti') or 0)
    monthly_payment = float(cd.get('monthlyPayment') or 0)
    expense_total = piti or (monthly_payment + lp * 0.005)  # P&I + ~taxes/ins fallback
    monthly_rent = round((cf + expense_total) / 0.80) if expense_total > 0 else 0

    # BBC also exposes per-property tax + insurance (monthly amounts) and rent.
    # Prefer these over derived/back-calc values when present.
    tax_m = float(cd.get('tax') or 0)
    ins_m = float(cd.get('insurance') or 0)
    hoa_m = float(cd.get('monthlyHoaFee') or 0)
    rent_bbc = float(cd.get('rent') or 0)
    if rent_bbc > 0:
        monthly_rent = round(rent_bbc)  # BBC's explicit rent is the source of truth

    # CREATIVE CF + TERMS — recomputed per tier using Richard's actual offer/down
    # structure (not BBC's blanket assumptions). BBC's monthlyCashFlow uses BBC's
    # offer terms (e.g. +12% premium, ~8% down) regardless of strategy — those
    # don't match Richard's tier-specific terms. We use BBC's rent + tax + insurance
    # (per-property) and apply Richard's terms to produce a faithful creative_cf.
    def _sf_cf(offer_mult, down_pct, balloon_yr):
        if monthly_rent <= 0 or lp <= 0: return 0, 0, 0
        offer = lp * offer_mult
        down = offer * down_pct
        loan = offer - down
        pi = loan / 360  # 0% rate, 30yr amort. P&I = pure principal.
        ti = (tax_m + ins_m) if (tax_m + ins_m) > 0 else (lp * 0.015 / 12)
        piti_per_month = pi + ti + hoa_m
        reserves = monthly_rent * 0.20  # CapEx 5% + Mgmt 5% + Vacancy 10% (Offer Oven defaults)
        cf_val = monthly_rent - piti_per_month - reserves
        return round(cf_val), round(offer), round(down)

    if dt == 'sellerFinance' and is_mfh:
        # Checkmate (MFH SF) — CANONICAL (CHECK MATE PITCH, 2026-06-12): asking +15%, 10% down,
        # 0%, monthly to seller = 40% of rent, 72-month (6yr) balloon. creative_cf below is the
        # END-BUYER underwriting CF (rent×0.80 − amortized PITI); the seller's OFFER monthly is the
        # 40%-of-rent figure (richards_monthly_to_seller).
        creative_cf, creative_offer, creative_down = _sf_cf(1.15, 0.10, 6)
        sf_balloon_years = 6
        creative_terms = f"${creative_offer:,} @ 0%, 10% down (${creative_down:,}), 40%-of-rent/mo, 72mo balloon"
    elif dt == 'sellerFinance':
        # Stale-SFH (cheap SFH SF) — same canonical formula (+15% / 10% down / 40%-of-rent / 72mo).
        # SFH ceiling is ~$500K (not $150K). Sub-$140K → interest variant (handled as a card note).
        creative_cf, creative_offer, creative_down = _sf_cf(1.15, 0.10, 6)
        sf_balloon_years = 6
        creative_terms = f"${creative_offer:,} @ 0%, 10% down (${creative_down:,}), 40%-of-rent/mo, 72mo balloon"
    elif dt == 'mortgageTakeover':
        # MT: take over the existing loan at its current payment (BBC's monthlyCashFlow
        # already reflects that payment → the right CF). The cash-to-seller "lump" is
        # rate- and price-scaled per Richard's MT course (L744-795): 6% band ⇒ $0 down;
        # ≤$150K ⇒ a $5-12K lump (cap 10%); pricier ⇒ ~5% down. Sub-To vs Hybrid is
        # decided downstream in classify_strategy(); this sets the base Sub-To lump.
        ex_rate = float(cd.get('interestRate') or 0)
        if ex_rate >= 5.5:   mt_lump = 0
        elif lp <= 150_000:  mt_lump = min(int(lp * 0.10), 12000)
        elif lp > 0:         mt_lump = int(lp * 0.05)
        else:                mt_lump = 7500
        creative_cf = round(cf)
        creative_offer = round(lp)
        creative_down = mt_lump
        sf_balloon_years = 0  # N/A — assume existing terms
        creative_terms = (f"Take over existing loan · ${mt_lump:,} to seller" if mt_lump
                          else "Take over existing loan · $0 down (6% rate band)")
    elif dt == 'fixAndFlip':
        # Cash Course 70% rule. F&F is a flip play — monthly CF is not the metric.
        # We surface the offer math; rental CF is a sanity check from BBC's cf.
        creative_offer = round(lp * 0.70)
        creative_down = 0
        sf_balloon_years = 0  # N/A
        creative_cf = round(cf)  # BBC's rental CF (post-flip-and-rent scenario)
        creative_terms = f"~${creative_offer:,} rough anchor (70% of LIST) — real MAO = ARV×0.70 − rehab − fee, compute via ARV comps"
    else:
        # Cash arb (Tier C): BBC's CF at cash-purchased terms is correct
        creative_offer = round(op or lp)
        creative_down = round(down)
        sf_balloon_years = 0  # N/A
        creative_cf = round(cf)
        creative_terms = "Cash offer / standard"

    # CARD ENTRY FEE + CoC — reconciled to Richard's canonical Offer Oven Google Sheet
    # (TRIAGE_OFFEROVEN_RECONCILIATION.md root-cause A + E). The sheet's Buyer Entry Fee
    # = Down + Rehab + Assignment(full) + Closing(2% of price); CoC = annual creative CF
    # ÷ entry. We do NOT use BBC's blanket monthlyCashFlow/downPayment (those assume BBC's
    # generic +12%/8% terms regardless of strategy → that was the source of the bogus 22%).
    # Standard $5K assignment + 0 rehab matches the sheet's validated default; the tier-
    # aware potential_fee (Tim's actual upside) is surfaced separately on the card.
    CLOSING_PCT = 0.02
    STD_ASSIGNMENT = 5000
    entry = round(creative_down + creative_offer * CLOSING_PCT + STD_ASSIGNMENT)
    coc = round(creative_cf * 12 / entry * 100, 1) if (entry > 0 and creative_cf > 0) else 0

    # 40%-OF-RENT RULE — Richard's verbatim live-call formula for SF (Tier A & B).
    # From caption validation: c2hNH6u7D0k @ 1:11:34 + 2:27:52. The monthly payment
    # the SELLER receives is 40% of expected rent; remaining 60% covers end-buyer
    # PITI (~20%) + reserves (~20%) + cash flow (~20%). The seller balloon at term
    # end = creative_offer − creative_down − (monthly × 12 × balloon_years).
    # Only computed for SF tiers; MT/FF/Cash get None.
    richards_monthly_to_seller = None
    richards_balloon_residual = None
    richards_pitch_line = None
    if dt == 'sellerFinance' and monthly_rent > 0:
        richards_monthly_to_seller = round(monthly_rent * 0.40)
        financed_amount = creative_offer - creative_down
        total_paid_during_term = richards_monthly_to_seller * 12 * sf_balloon_years
        richards_balloon_residual = max(0, financed_amount - total_paid_during_term)
        down_pct = int(round(creative_down / creative_offer * 100)) if creative_offer else 0
        richards_pitch_line = (
            f"${creative_offer:,} · {down_pct}% down (${creative_down:,}) · "
            f"${richards_monthly_to_seller:,}/mo to seller · "
            f"{sf_balloon_years}yr balloon (${richards_balloon_residual:,} residual)"
        )

    # BANK GAP — what a standard 7% bank mortgage would look like vs the creative
    # scenario above. Reuses the same rent + tax + ins + reserve numbers.
    # Assumptions per primary source (Cash Course L300-302):
    #   20% down ("I'm going to be required to put down 20%")
    #   7% interest rate ("probably a 7% interest rate right now")
    #   30-year amortization ("30-year amortization. This should always be 30.")
    #   Principal+Interest payment structure (Richard never mentions interest-only;
    #   DSCR loans require positive CF at amortized terms — SF Course L190-225).
    bank_gap = 0
    if monthly_rent > 0 and lp > 0:
        bank_loan = lp * 0.80  # 20% down per Richard's standard (was 0.75 = 25% down)
        r = 0.07 / 12
        bank_pi = bank_loan * r / (1 - (1 + r) ** -360)
        bank_ti = (tax_m + ins_m) if (tax_m + ins_m) > 0 else (lp * 0.015 / 12)
        bank_piti = bank_pi + bank_ti + hoa_m
        bank_cf = monthly_rent - bank_piti - (monthly_rent * 0.20)
        bank_gap = round(max(0, creative_cf - bank_cf))

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
            'entry_fee': round(entry), 'entry_pct': round(entry/creative_offer*100,1) if creative_offer>0 else 0,
            'equity': int(float(cd.get('equity') or 0)), 'zillow': p.get('zillowUrl'), 'pid': p.get('pid',''), 'zpid': (p.get('zpid') or p.get('propertyId') or (re.search(r'(\d+)_zpid', p.get('zillowUrl') or '').group(1) if re.search(r'(\d+)_zpid', p.get('zillowUrl') or '') else '')), 'in_pipeline': bool(p.get('isPropertyAlreadyInPipeline')),
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
            # Buyer-side creative cash-on-cash — Richard's own deal metric (SF Course
            # ~L759-775: annual CF ÷ (down + ~$5K closing); his go/no-go = "beats the
            # stock market", target 14-20%). Entry = creative_down + $8K closing.
            'creative_coc': (round(creative_cf * 12 / (creative_down + 8000) * 100, 1)
                             if (creative_down + 8000) > 0 and creative_cf > 0 else 0),
            'creative_terms': creative_terms,
            'sf_balloon_years': sf_balloon_years,
            'richards_monthly_to_seller': richards_monthly_to_seller,
            'richards_balloon_residual': richards_balloon_residual,
            'richards_pitch_line': richards_pitch_line,
            'beds': int(p.get('bed') or 0),
            'baths': int(float(p.get('bath') or 0)),
            'sqft': int(p.get('sqft') or 0),
            'lat': addr.get('latitude') or '',
            'lng': addr.get('longitude') or '',
            'year_built': int(cd.get('yearBuilt')) if (cd.get('yearBuilt') and str(cd.get('yearBuilt')).isdigit()) else 0,
            'foundation': (cd.get('foundation') or '').strip(),
            'image_count': len(p.get('images') or []),
            'images': clean_image_urls(p.get('images')),  # drops keyed maps.googleapis streetview URLs — see clean_image_urls
            # NEW: BBC fields previously dropped — closes the data gap on MT motivation
            # signals + PITI breakdown. The big one is `balance` (loan owed) for MT.
            'loan_balance': int(float(cd.get('balance') or cd.get('loanAmount') or 0)),
            # Trojan-Horse cash-pivot offer (Richard): balance + 4% of asking → nets seller ~$0;
            # made to be rejected, then pivot to the takeover/trust pitch. MT leads only.
            'trojan_horse_offer': (int(float(cd.get('balance') or cd.get('loanAmount') or 0) + lp * 0.04)
                                   if dt == 'mortgageTakeover' and (cd.get('balance') or cd.get('loanAmount')) else 0),
            'interest_rate': float(cd.get('interestRate') or 0),
            'monthly_payment_actual': int(float(cd.get('monthlyPayment') or 0)),
            'tax_monthly': int(float(cd.get('tax') or 0)),
            'insurance_monthly': int(float(cd.get('insurance') or 0)),
            'hoa_monthly': int(float(cd.get('monthlyHoaFee') or 0)),
            'bbc_offer_price': int(float(cd.get('offerPrice') or 0)),
            'bbc_down_payment': int(float(cd.get('downPayment') or 0)),
            'bbc_balloon_months': int(cd.get('balloon') or 0),
            'lot_size_sqft': int(cd.get('lotSize') or 0),
            'garage': (cd.get('garage') or '').strip().lower() == 'yes',
            'piti_breakdown': cd.get('breakdown_of_PITI') or {},
            'is_zillow_active': bool(p.get('is_zillow_active'))}

def condition_risk_flags(s):
    """Heuristic signals that a listing is likely a heavy-rehab / REO / auction
    rather than a clean seller-finance candidate. BBC's API doesn't expose
    condition or REO status, so we infer from indirect indicators. This is
    HEURISTIC — operator MUST verify on Zillow before tracking.

    Returns list of warning strings to surface on the card. Empty list = clean."""
    flags = []
    foundation = (s.get('foundation') or '').upper()
    year_built = s.get('year_built') or 0
    sqft_val = s.get('sqft') or 0
    img_count = s.get('image_count') or 0
    dom = s.get('dom') or 0
    price = s.get('price') or 0

    # Foundation 'N/A' + old build year = data is missing / property may have foundation issues
    if foundation in ('N/A', '', 'NONE') and year_built and year_built < 1960:
        flags.append('⚠️ Old build + foundation unrecorded — verify condition on Zillow')

    # Pre-1940 + very cheap = likely needs significant work
    if year_built and year_built > 0 and year_built < 1940 and price > 0 and price < 80_000:
        flags.append('⚠️ Pre-1940 + <$80K = likely heavy rehab — consider F&F not SF')

    # Very low image count for a long-stale listing = under-marketed / poor condition
    if img_count > 0 and img_count < 4 and dom > 365:
        flags.append('⚠️ Only ' + str(img_count) + ' photos despite ' + str(dom) + ' DOM — verify on Zillow')

    # 100% equity + very stale + cheap urban (Detroit, Highland Park MI, Memphis) = REO or distress
    if dom > 500 and price > 0 and price < 100_000 and (s.get('cf') or 0) == 0:
        flags.append('⚠️ Stale + cheap + null cash flow — check listing status on Zillow. '
                     'If owned by the bank / Auction.com → REJECT. But if an individual still '
                     'owns it with a foreclosure/auction date NOT yet passed → top-priority '
                     'Mortgage-Takeover lead (built-in deadline); pursue, don\'t reject.')

    return flags

# ── Strategy determination thresholds — Richard's MT course rules, made explicit ──
# (STRATEGY_REALIGNMENT_PLAN.md §1; MT course L341-410, L538-566, L744-795, L860-905)
SELLER_NET_CORNERED = 15_000   # equity-after-costs ≤ this ⇒ cornered seller ⇒ Sub-To
HYBRID_MAX_RATE     = 6.0      # existing rate ≤ this ⇒ assumable ⇒ Hybrid workable;
                               #   above (7%+) WITH real equity ⇒ no structure ⇒ REJECT
MT_CF_FLOOR         = 100      # creative CF at the existing payment must clear this (Step 4)

def _existing_piti(s):
    """Existing monthly PITI on the in-place loan (MT group). Prefer BBC's
    monthlyPayment; else estimate P&I from balance+rate at ~25yr remaining amort,
    + 1.5%/yr of price for taxes+insurance. Mirrors the hybrid-banner fallback."""
    piti = s.get('monthly_payment_actual') or 0
    if piti > 0:
        return piti
    bal = s.get('loan_balance') or 0
    if bal <= 0:
        return 0
    rate = s.get('interest_rate') or 0
    price = s.get('price') or 0
    r = (rate / 100) / 12
    pi = int(bal * r / (1 - (1 + r) ** -300)) if r > 0 else int(bal / 300)
    ti = int(price * 0.015 / 12)
    return pi + ti

def classify_strategy(s):
    """Route a lead into HMHW's 3-group taxonomy via Richard's explicit Step 1-4 test
    (Mortgage Takeover course). MUTATES s with:
       s['strategy_group']   — 'Cash Deals' | 'Seller Finance' | 'Mortgage Takeover' | None
       s['strategy_subtype'] — 'Fix & Flip' | 'Cash Arb' | 'Checkmate' | 'Stale-SFH'
                               | 'Sub-To' | 'Hybrid' | None
       s['determination']    — human 'why it's here' line, shown on the card
    Returns the internal bucket letter (A/B/HY/MT/FF/C/REJECT) the section machinery
    still keys on. See STRATEGY_REALIGNMENT_PLAN.md §0-1."""
    pt = s['type'].lower()
    is_mfh_5plus = s['units'] >= 5
    is_mfh_24 = (2 <= s['units'] <= 4) or any(t in pt for t in ('duplex','triplex','fourplex','quadplex','quadruplex','plex'))
    # 'apartment' = single unit (caught earlier as non-residential); 'multi' = MFH building.
    is_mfh = is_mfh_5plus or is_mfh_24 or 'multi' in pt
    dt = s.get('deal_type', 'sellerFinance')
    cf_creative = s.get('creative_cf', 0)
    price = s.get('price') or 0
    dom = s.get('dom') or 0

    # ── STEP 1 — Cash vs Creative ─────────────────────────────────────────────
    # BBC fixAndFlip tag, or the upstream distress demotion (pre-1940 + <$80K) which
    # rewrote deal_type to 'fixAndFlip'. Cash Course 70%-of-list rule; CF isn't the metric.
    if dt == 'fixAndFlip':
        if dom >= 60 and price < 250_000:
            s['strategy_group'] = 'Cash Deals'; s['strategy_subtype'] = 'Fix & Flip'
            s['determination'] = f"Cash/distress tag · DOM {dom} · ${price:,} <$250K ⇒ Fix & Flip (70%-of-list)"
            return 'FF'
        s['strategy_group'] = 'Cash Deals'; s['strategy_subtype'] = None
        s['determination'] = f"Fix&Flip tag but DOM {dom}/${price:,} fails $250K·DOM60 gate ⇒ no play"
        return 'REJECT'

    # ── STEP 2 — Free & Clear (Seller Finance) vs Existing Mortgage ───────────
    if dt == 'sellerFinance':
        # Free & clear: no loan to service ⇒ 40%-of-rent SF math is valid here only.
        #   Checkmate = MFH 5+ or non-retail 2-4plex (FHA fails → DSCR fails → SF is the exit).
        #   Stale-SFH = cheap SFH on a long DOM.
        if is_mfh and 200_000 <= price <= 1_400_000 and dom >= 90 and cf_creative >= 100:
            s['strategy_group'] = 'Seller Finance'; s['strategy_subtype'] = 'Checkmate'
            unit_lbl = f"{s['units']}u" if s['units'] else "2-4u"
            s['determination'] = (f"Free & clear · MFH {unit_lbl} · ${price:,} · DOM {dom} "
                                  f"⇒ FHA+DSCR fail ⇒ Checkmate (Seller Finance)")
            return 'A'
        if (not is_mfh) and price < 500_000 and dom >= 90 and cf_creative >= 100:
            s['strategy_group'] = 'Seller Finance'; s['strategy_subtype'] = 'Stale-SFH'
            _var = " (sub-$140K → interest variant)" if price < 140_000 else ""
            s['determination'] = f"Free & clear · SFH ${price:,} <$500K · DOM {dom} ⇒ Stale-SFH (Seller Finance){_var}"
            return 'B'
        # Tagged SF but doesn't pencil — say why.
        s['strategy_group'] = 'Seller Finance'; s['strategy_subtype'] = None
        reasons = []
        if cf_creative < 100: reasons.append("creative CF <$100")
        if dom < 90: reasons.append(f"DOM {dom}<90")
        if is_mfh and not (200_000 <= price <= 1_400_000): reasons.append(f"${price:,} outside $200K-1.4M")
        if (not is_mfh) and price >= 500_000: reasons.append(f"SFH ${price:,} ≥$500K")
        s['determination'] = "Seller Finance gate fails: " + (", ".join(reasons) or "no fit")
        return 'REJECT'

    # ── STEP 3+4 — Mortgage Takeover: Sub-To vs Hybrid via equity-after-costs ──
    if dt == 'mortgageTakeover':
        loan_balance = s.get('loan_balance') or 0
        rate = s.get('interest_rate') or 0
        # ONE canonical existing-PITI figure (fix F): prefer score's full-PITI estimate
        # (BBC `piti` incl taxes+ins), else estimate from balance+rate. Used by the CF
        # gate here AND surfaced verbatim on the card + Airtable so the card never shows
        # three different "PITI" numbers.
        existing_piti = s.get('monthly_piti') or _existing_piti(s)
        s['existing_piti'] = existing_piti
        rent = s.get('monthly_rent') or 0
        rate_str = f"{rate:.2f}%" if rate else "rate n/a"
        # CASH FLOW AT EXISTING PAYMENT — a TAG, not a gate (committed 2026-06-12; Richard
        # MT course L1055-1080). Cash flow only decides the DISPOSITION EXIT: it cash-flows ⇒
        # sell to an INVESTOR; it doesn't ⇒ $0-down sale to a LIVE-IN / RETAIL buyer (a
        # homeowner who can't get traditional financing). Non-cash-flowing MT deals are REAL
        # opportunities, so we NEVER reject on cash flow — we tag s['exit_channel'].
        mt_cf = (rent * 0.80 - existing_piti) if (rent > 0 and existing_piti > 0) else None
        if mt_cf is None:
            s['exit_channel'] = 'investor?'; cf_str = "CF n/a (rent unverified)"
        elif mt_cf > 0:
            s['exit_channel'] = 'investor'; cf_str = f"CF +${int(mt_cf):,}/mo ✓ → investor buyer"
        else:
            s['exit_channel'] = 'retail/live-in'; cf_str = f"CF ${int(mt_cf):,}/mo → $0-down, live-in/retail buyer"
        # DOM freshness still applies (recency/motivation). Cash flow NEVER gates.
        if dom < 60:
            s['strategy_group'] = 'Mortgage Takeover'; s['strategy_subtype'] = None
            s['determination'] = f"MT lead but DOM {dom}<60 (too fresh) ⇒ skip"
            return 'REJECT'
        # Rate-driven down-payment language (6% ⇒ $0 down; not a flat cutoff). Rate is a SORT,
        # not a gate — it never excludes an MT lead from the call sheet.
        if rate >= 6.5:   down_rule = "$0 down (rate ≥6.5%)"
        elif rate >= 5.5: down_rule = "$0 down (6% band)"
        elif rate > 0:    down_rule = ("≤10% down if <$150K, ~5% if more" if price else "scaled down")
        else:             down_rule = "down TBD (rate n/a)"
        # No reliable loan data on this MT lead → default Sub-To, flag for verification.
        if loan_balance <= 0:
            s['strategy_group'] = 'Mortgage Takeover'; s['strategy_subtype'] = 'Sub-To'
            s['determination'] = f"MT tag, loan unverified — confirm via PropStream ⇒ Sub-To (default) · {cf_str}"
            return 'MT'
        # STEP 3 — equity-after-costs is the deciding test (not raw equity).
        seller_net = price - loan_balance - price * 0.06
        if seller_net <= SELLER_NET_CORNERED:
            # Cornered seller: can't profit on a sale ⇒ small lump to take over the debt.
            s['strategy_group'] = 'Mortgage Takeover'; s['strategy_subtype'] = 'Sub-To'
            s['determination'] = (f"Loan ${loan_balance:,} @{rate_str} · nets ~${int(seller_net):,} at sale "
                                  f"(≤${SELLER_NET_CORNERED//1000}K) ⇒ cornered ⇒ Sub-To · {down_rule} · {cf_str}")
            return 'MT'
        # Meaningful equity → Hybrid if the existing rate is assumable.
        if 0 < rate <= HYBRID_MAX_RATE:
            s['strategy_group'] = 'Mortgage Takeover'; s['strategy_subtype'] = 'Hybrid'
            s['determination'] = (f"Loan ${loan_balance:,} @{rate_str} (assumable) · ~${int(seller_net):,} equity "
                                  f"⇒ assume + carry note ⇒ Hybrid · {cf_str}")
            return 'HY'
        # Real equity + high rate (7%+): seller can sell conventionally and a 7%+ loan isn't
        # worth assuming → no takeover structure (Richard, MT L860-905). The one true MT pass.
        s['strategy_group'] = 'Mortgage Takeover'; s['strategy_subtype'] = None
        s['determination'] = (f"~${int(seller_net):,} equity + {rate_str} — seller can sell conventionally, "
                              f"7%+ loan not worth assuming ⇒ no MT structure")
        return 'REJECT'

    # ── Cash arbitrage (Tier C) — non-SF/MT/FF with strong standalone CF ──────
    if cf_creative > 300 and dom >= 60:
        s['strategy_group'] = 'Cash Deals'; s['strategy_subtype'] = 'Cash Arb'
        s['determination'] = f"Cash-arb · CF +${cf_creative:,}/mo · DOM {dom} ⇒ Cash"
        return 'C'

    s['strategy_group'] = None; s['strategy_subtype'] = None
    s['determination'] = "No Richard play for this profile ⇒ REJECT"
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
NON_RESIDENTIAL_TYPES = ('vacant', 'land', 'lot', 'acreage', 'commercial', 'industrial',
                         'condo', 'apartment',       # 'apartment' = single condo-style unit
                         'manufactured', 'mobile')   # manufactured/mobile homes — often on leased
                                                     # land (no real estate to underwrite), depreciate,
                                                     # not lendable conventionally. Per Tim's 7717
                                                     # Arbor Ridge Ct example 2026-05-14.
buckets = {'A':[], 'B':[], 'HY':[], 'MT':[], 'FF':[], 'C':[], 'REJECT':[]}
land_skipped = 0
tracked_skipped = 0
new_construction_skipped = 0
dup_skipped = 0
seen_pids = set()  # cross-pass dedupe — the dedicated MFH pass overlaps the primary pull
this_year = date.today().year  # date imported at module top from datetime
for p in all_leads:
    # Cross-pass pid-dedupe — same property can be returned by both the primary pull
    # and the dedicated MFH pass (and the off-market pass). First occurrence wins;
    # the property object is identical regardless of which search surfaced it.
    _pid = p.get('pid')
    if _pid:
        if _pid in seen_pids:
            dup_skipped += 1
            continue
        seen_pids.add(_pid)
    # Deal Flow dedupe — if Tim has tracked this property at any status, drop from daily.
    # He manages it via Airtable Deal Flow kanban from here.
    if p.get('pid') in tracked_pids:
        tracked_skipped += 1
        continue
    # 'Rejected by Tim' dedupe — permanent exclude. The reason captured in that
    # table will be reviewed by the weekly optimization agent to propose new
    # filter rules.
    if p.get('pid') in rejected_pids:
        tracked_skipped += 1  # counts toward same bucket for summary
        continue
    # New construction / planned development filter — Richard's method targets
    # distressed EXISTING listings with stale DOM; new builds have a builder-seller
    # (different motivation profile) and no rental history. Signals:
    #   - sqft = 0 (no structure built yet — e.g. 517 Prospect St Indianapolis IN)
    #   - yearBuilt > current year (under construction or planned)
    sqft_val = int(p.get('sqft') or 0)
    cd_p = p.get('calculatedData') or {}
    yb = cd_p.get('yearBuilt')
    yb_int = int(yb) if (yb and str(yb).isdigit()) else 0
    if sqft_val == 0 or (yb_int and yb_int > this_year):
        new_construction_skipped += 1
        continue
    s = score(p)
    if s['cf'] == 0 and s['price'] == 0: continue
    pt_lower = (s.get('type') or '').lower()
    # Condo/apartment carve-out for Mortgage Takeover (2026-06-12): the HMHW PropStream slide
    # explicitly targets "condos, single family AND multi family" for MT (esp. FL retirement
    # condos), so condos are valid MT leads — only default-exclude them for the NON-MT plays.
    _is_mt = s.get('deal_type') == 'mortgageTakeover'
    _hard_excl = ('vacant','land','lot','acreage','commercial','industrial','manufactured','mobile')
    if _is_mt:
        if any(tok in pt_lower for tok in _hard_excl):
            land_skipped += 1; continue
    elif any(token in pt_lower for token in NON_RESIDENTIAL_TYPES):
        land_skipped += 1
        continue
    # Condition / REO risk heuristic — heuristic flags computed once, surfaced on
    # card AND used to demote heavy-rehab-flavored SF candidates into Fix & Flip path
    s['risk_flags'] = condition_risk_flags(s)
    # If a listing looks like heavy-rehab (pre-1940 + cheap), demote SF → FF candidate
    if (s.get('deal_type') == 'sellerFinance'
        and s.get('year_built') and s['year_built'] < 1940
        and s.get('price') and s['price'] < 80_000):
        s['deal_type'] = 'fixAndFlip'  # reroute through tier()
        s['deal_type_raw'] = 'fixAndFlip'
    t = classify_strategy(s)
    s['buyer_matches'] = match_buyers(s, t, buyers) if t != 'REJECT' else []
    s['tz'] = STATE_TZ.get(s['state'], 'America/New_York')
    s['agent'] = None  # set below if unlocked
    buckets[t].append(s)
for t in ('A','B','HY','C'): buckets[t].sort(key=lambda x: (-x['creative_cf'], -x['dom']))
# MT/Sub-To: committed sort = lowest equity (motivation) then lowest rate (CoC opportunity) → call first.
buckets['MT'].sort(key=lambda x: (x.get('equity') or 0, x.get('interest_rate') or 999))
# Fix & Flip: sort by DOM desc (motivation) since CF isn't the relevant metric
buckets['FF'].sort(key=lambda x: -x['dom'])
print(f'\nA={len(buckets["A"])}  B={len(buckets["B"])}  HY={len(buckets["HY"])}  MT={len(buckets["MT"])}  FF={len(buckets["FF"])}  C={len(buckets["C"])}  REJECT={len(buckets["REJECT"])}  Land-skipped={land_skipped}  NewConstruction-skipped={new_construction_skipped}  Tracked-skipped={tracked_skipped}  Dup-skipped={dup_skipped}', file=sys.stderr)

# 5b. Surface agent info — cookie-free via BBC's contact-seller endpoint (the one
# behind the Create Offer modal). Cost: $0/unlock. Run on ALL Tier A/B/C deals.
# ALSO: detect REO/auction/foreclosure based on agent name keywords — these
# 'agents' are corporate asset managers (Auction.com, Williams & Williams, etc.),
# NOT individual realtors. Properties they list are bank-owned auctions, which
# Richard's method doesn't address. We REJECT them post-unlock.
AUCTION_AGENT_KEYWORDS = ('auction', 'reo', 'foreclosure', 'bank ', 'asset management',
                          'williams &', 'altisource', 'bidsale', 'hubzu', 'xome',
                          'realty trust', 'asset disposition', 'servicelink')
unlock_targets = buckets['A'] + buckets['B'] + buckets['HY'] + buckets['MT'] + buckets['FF'] + buckets['C']
unlocks_attempted = 0
unlocks_succeeded = 0
auction_rejected = 0
captured_agents = []  # for Airtable persistence
if unlock_targets:
    print(f'\nFetching agent info for {len(unlock_targets)} Tier A/B/C deals (cookie-free)...', file=sys.stderr)
    for s in unlock_targets:
        unlocks_attempted += 1
        agent = unlock_agent(s['pid'])
        if agent:
            agent_name_lower = (agent.get('name') or '').lower()
            is_auction = any(kw in agent_name_lower for kw in AUCTION_AGENT_KEYWORDS)
            if is_auction:
                # Move from its qualified tier to REJECT bucket — this is an REO/auction listing
                s['agent'] = agent
                s['_auction_reject'] = True
                auction_rejected += 1
                print(f"  ✗ {s['address'][:50]}: REJECTED — agent '{agent['name']}' looks like auction/REO", file=sys.stderr)
                continue
            s['agent'] = agent
            unlocks_succeeded += 1
            captured_agents.append({**agent, 'pid': s['pid'], 'address': s['address'], 'state': s['state']})
            phone_str = agent['phone'] or '(no phone)'
            print(f"  ✓ {s['address'][:50]}: {agent['name']} / {phone_str}", file=sys.stderr)
        else:
            print(f"  · {s['address'][:50]}: no agent record in BBC", file=sys.stderr)
    print(f'Agents captured: {unlocks_succeeded}/{unlocks_attempted} (auction-rejected: {auction_rejected})', file=sys.stderr)

# Strip auction-rejected from their tier buckets (they shouldn't appear in briefing)
for t in ('A','B','HY','MT','FF','C'):
    buckets[t] = [s for s in buckets[t] if not s.get('_auction_reject')]

# 5b. Vision analysis — Claude looks at BBC's photos and flags REO/condition/distress
# that the data fields don't expose. Closes the detection gap.
vision_rejected = 0
vision_demoted = 0
if ANTHROPIC_API_KEY:
    print(f'\nClaude vision analysis on qualified properties...', file=sys.stderr)
    # Build a lookup: PID → original BBC property dict (for photo URLs)
    p_by_pid = {p.get('pid'): p for p in all_leads if p.get('pid')}
    for tier_name in ('A','B','HY','MT','FF','C'):
        for s in list(buckets[tier_name]):
            pid = s.get('pid')
            orig_p = p_by_pid.get(pid)
            if not orig_p: continue
            analysis = analyze_property_vision(orig_p)
            if not analysis: continue
            s['vision'] = analysis
            action = (analysis.get('recommended_action') or '').lower()
            if action == 'reject':
                vision_rejected += 1
                buckets[tier_name].remove(s)
                print(f"  ✗ {s['address'][:50]}: VISION-REJECTED — {analysis.get('notes','')[:80]}", file=sys.stderr)
            elif action == 'demote_to_ff' and tier_name != 'FF' and (analysis.get('condition') or 3) <= 2:
                # Hard floor: only condition 1-2 (needs rehab before a tenant) demotes to FF.
                # Condition 3 (dated/cosmetic but rentable) STAYS in its seller-finance lane —
                # the vision notes still surface on the card for the operator's Zillow check.
                # Reverses the 2026-05-25 over-demote (32/75 cards demoted, ~all false on a sample).
                vision_demoted += 1
                buckets[tier_name].remove(s)
                # Reroute to FF — change deal_type label and creative_terms
                s['deal_type_raw'] = 'fixAndFlip'
                s['creative_offer'] = round(s['price'] * 0.70) if s.get('price') else 0
                s['creative_down'] = 0
                s['creative_terms'] = f"Cash offer ${s['creative_offer']:,} (vision-demoted — condition {analysis.get('condition','?')}/5)"
                s['strategy_group'] = 'Cash Deals'; s['strategy_subtype'] = 'Fix & Flip'
                s['determination'] = f"Vision-demoted {tier_name}→F&F (condition {analysis.get('condition','?')}/5, needs rehab) ⇒ Cash 70%-of-list"
                buckets['FF'].append(s)
                print(f"  → {s['address'][:50]}: VISION-DEMOTED {tier_name}→FF (condition {analysis.get('condition','?')}/5): {analysis.get('notes','')[:60]}", file=sys.stderr)
    print(f'Vision: {vision_calls} API calls (~${vision_calls * 0.02:.2f}, all-photo) · {vision_rejected} rejected · {vision_demoted} demoted to FF', file=sys.stderr)
else:
    print(f'\nClaude vision SKIPPED — ANTHROPIC_API_KEY not set. To enable: export ANTHROPIC_API_KEY=sk-...', file=sys.stderr)

# 5b2. Recent-flip detection — calls BBC's per-property detail endpoint for each
# A/B/MT card to fetch priceHistory + lastSoldPrice. Properties bought cheap in
# the last 24 months and relisted with 35%+ markup are investor flips: seller
# wants cash to roll into the next deal, NOT receptive to SF. Detected real-world
# 2026-05-15 on 16031 Tacoma St Detroit MI (sold $54K Dec 2024, relisted $75K =
# +38.9% — described as 'beautifully renovated... part of 20 unit portfolio package').
# BBC's cumulative DOM (644 days) was masking this; Zillow's reset DOM (48 days)
# would have caught it but Richard says ignore Zillow DOM. This closes the gap.
flip_detected = 0
desc_rejected = 0
desc_flip_demoted = 0
print(f'\nProperty-history + description-keyword pass on Tier A/B/MT properties...', file=sys.stderr)
for tier_name in ('A','B','HY','MT'):
    for s in list(buckets[tier_name]):
        zpid = s.get('zpid')
        if not zpid: continue
        history = fetch_property_history(zpid)
        if not history: continue
        s['flip_markup_pct'] = history.get('flip_markup_pct')
        s['last_sold_price'] = history.get('last_sold_price')
        s['last_sold_date'] = history.get('last_sold_date')
        s['months_since_sale'] = history.get('months_since_sale')
        s['brokerage'] = history.get('brokerage') or ''
        s['mls_agent_name'] = history.get('mls_agent_name') or ''
        s['mls_agent_email'] = history.get('mls_agent_email') or ''
        description = history.get('description') or ''
        s['description'] = description[:500]  # truncate for storage
        # 1. TERMINAL description keywords — auto-reject. "No assignment" etc.
        # mechanically break the HMHW assignment-wholesale model.
        terminal_kw = desc_terminal_match(description)
        if terminal_kw:
            desc_rejected += 1
            buckets[tier_name].remove(s)
            print(f"  ✗ {s['address'][:50]}: DESC-REJECTED — found '{terminal_kw}' in listing description", file=sys.stderr)
            continue  # skip flip checks for rejected
        # 2. RECENT FLIP via sold-event + markup — same as before
        if history.get('is_recent_flip'):
            flip_detected += 1
            buckets[tier_name].remove(s)
            markup_pct = round((history.get('flip_markup_pct') or 0) * 100, 1)
            s['deal_type_raw'] = 'fixAndFlip'
            s['creative_offer'] = round(s['price'] * 0.70) if s.get('price') else 0
            s['creative_down'] = 0
            s['creative_terms'] = f"Cash offer ${s['creative_offer']:,} (flip relist — +{markup_pct}% over ${history['last_sold_price']:,} sold {history['last_sold_date']})"
            s['strategy_group'] = 'Cash Deals'; s['strategy_subtype'] = 'Fix & Flip'
            s['determination'] = f"Flip relist +{markup_pct}% over ${history['last_sold_price']:,} ({history['months_since_sale']}mo ago) — seller wants cash ⇒ Cash 70%-of-list"
            buckets['FF'].append(s)
            print(f"  → {s['address'][:50]}: FLIP-DEMOTED {tier_name}→FF (+{markup_pct}% over ${history['last_sold_price']:,}, {history['months_since_sale']}mo ago)", file=sys.stderr)
            continue
        # 3. SUSPECTED FLIP via description vocab (when no sold-event signal) —
        # 3+ flip keywords = strong investor-flip signal even without priceHistory sale.
        # Catches the 9904 Aetna Rd case (no Sold record but description gushes
        # "Freshly Updated", "move-in-ready", "Instant Income Potential").
        flip_kws = desc_flip_signals(description)
        s['desc_flip_keywords'] = flip_kws
        if len(flip_kws) >= 3:
            desc_flip_demoted += 1
            buckets[tier_name].remove(s)
            s['deal_type_raw'] = 'fixAndFlip'
            s['creative_offer'] = round(s['price'] * 0.70) if s.get('price') else 0
            s['creative_down'] = 0
            s['creative_terms'] = f"Cash offer ${s['creative_offer']:,} (suspected flip — description signals: {', '.join(flip_kws[:3])})"
            s['strategy_group'] = 'Cash Deals'; s['strategy_subtype'] = 'Fix & Flip'
            s['determination'] = f"Suspected investor flip ({len(flip_kws)} description signals) ⇒ Cash 70%-of-list"
            buckets['FF'].append(s)
            print(f"  → {s['address'][:50]}: DESC-FLIP-DEMOTED {tier_name}→FF ({len(flip_kws)} flip keywords: {', '.join(flip_kws[:4])})", file=sys.stderr)
print(f'History+desc: {desc_rejected} rejected (terminal kw) · {flip_detected} demoted (sold-event flip) · {desc_flip_demoted} demoted (desc-flip ≥3 kw)', file=sys.stderr)

# Re-sort buckets after vision-driven moves
for t in ('A','B','HY','C'): buckets[t].sort(key=lambda x: (-x.get('creative_cf',0), -x.get('dom',0)))
# MT/Sub-To: lowest equity then lowest rate (committed 2026-06-12) — re-applied after vision moves.
buckets['MT'].sort(key=lambda x: (x.get('equity') or 0, x.get('interest_rate') or 999))
# Tier A is the flood — rank it by Richard's CoC metric instead of raw CF, so the
# highest-return deals surface first regardless of deal size.
buckets['A'].sort(key=lambda x: (-x.get('creative_coc',0), -x.get('creative_cf',0)))
buckets['FF'].sort(key=lambda x: -x.get('dom',0))

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

# 6. Push rejects — BATCHED. Airtable accepts up to 10 records/request; this was
# one POST per reject (O(rejects) sequential round-trips), which the MFH flood +
# the broken dedup above turned into a multi-minute grind. Now: dedupe against the
# (now-complete) watchlist, then write in batches of 10, paced under Airtable's
# 5 req/s limit, with a single 429 retry per batch.
today = date.today().isoformat()
watch_until = (date.today() + timedelta(days=180)).isoformat()
to_push = []
for s in buckets['REJECT']:
    if s['cf'] <= 0: continue
    addr_only = s['address'].split(',')[0].strip()
    if not addr_only or addr_only.lower() in existing_addrs: continue
    existing_addrs.add(addr_only.lower())
    to_push.append({'fields': {
        'Address': addr_only,
        'City State': ', '.join(s['address'].split(',')[1:]).strip(),
        'Original Asking': s['price'], 'Original CF': s['cf'],
        'Current Asking': s['price'], 'Current CF': s['cf'],
        'Rejection Reason': 'CF Below $200' if s['cf'] < 200 else 'Untiered (motivation/structure)',
        'DOM at Rejection': s['dom'], 'Current DOM': s['dom'],
        'Zillow URL': s['zillow'] or None,
        'First Seen': today, 'Last Checked': today, 'Watch Until': watch_until,
        'Status': 'Watching'}})
pushed = 0
for i in range(0, len(to_push), 10):
    batch = to_push[i:i+10]
    payload = {'records': batch}
    code, body = http_req(f'https://api.airtable.com/v0/{AT_BASE}/{WL_TABLE}',
                          method='POST', json_body=payload,
                          headers={'Authorization': f'Bearer {AT_TOKEN}'})
    if code == 429:  # rate limited — brief backoff + one retry
        time.sleep(0.5)
        code, body = http_req(f'https://api.airtable.com/v0/{AT_BASE}/{WL_TABLE}',
                              method='POST', json_body=payload,
                              headers={'Authorization': f'Bearer {AT_TOKEN}'})
    if code in (200, 201): pushed += len(batch)
    time.sleep(0.21)  # stay under Airtable's 5 req/s
print(f'Pushed {pushed} to watchlist ({len(to_push)} new, batched in {(len(to_push)+9)//10} requests)', file=sys.stderr)

# 7. Render HTML
date_iso = today
date_human = datetime.now().strftime('%a %b %d, %Y')
# Tier A CoC display bands (Richard's framing): floor 10% = "beats the stock
# market" (anything below folds into a collapsed backlog); 16% = the data knee +
# inside his 14-20% target band = the 🔴 CALL FIRST shortlist. Both tunable here.
TIER_A_FLOOR_COC = 10
CALLFIRST_COC = 16

def render_deal(d, t):
    cls = {'A':'tier-A','B':'tier-B','HY':'tier-HY','MT':'tier-MT','FF':'tier-FF','C':'tier-C'}[t]
    playbook = {'A':'/rt-companion/playbooks/seller-finance.html',
                'B':'/rt-companion/playbooks/seller-finance.html',
                'HY':'/rt-companion/playbooks/hybrid.html',
                'MT':'/rt-companion/playbooks/sub-to.html',
                'FF':'/rt-companion/playbooks/fix-and-flip.html',
                'C':'/rt-companion/playbooks/cash-arbitrage.html'}[t]
    bl = f'<div style="color:#e3b341;font-size:13px;margin-top:6px;font-weight:600;">⭐ BUYER MATCH: {", ".join(d["buyer_matches"])}</div>' if d['buyer_matches'] else ''
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
    # BBC search URL with #auto: hash — userscript on BBC side auto-fills + searches.
    # Works on desktop browsers with Tampermonkey/Userscripts installed.
    bbc_search = f'https://www.buyboxcartel.com/vip/lightning-leads#auto:{urllib.parse.quote(bbc_hash_payload)}'
    bbc_link = f' <a class="zillow" href="{bbc_search}" target="_blank">🔍 Search BBC (desktop) ↗</a>'
    # iPhone/Safari fallback — no userscript dependency. Copies "City, State" to
    # clipboard (BBC's search box only accepts that format) and opens BBC; Tim
    # pastes and scrolls. One tap on mobile, zero install requirements.
    bbc_copy_payload = bbc_query.replace("'", "\\'")  # escape for inline JS
    bbc_copy_handler = (
        f"navigator.clipboard.writeText('{bbc_copy_payload}');"
        f"this.style.background='#1a4d2e';this.style.color='#56d364';"
        f"this.dataset.orig=this.textContent;this.textContent='✓ Copied · BBC opening';"
        f"setTimeout(()=>{{this.style.background='';this.style.color='';this.textContent=this.dataset.orig;}},1500);"
    )
    bbc_mobile_link = f' <a class="zillow" href="https://www.buyboxcartel.com/vip/lightning-leads" target="_blank" onclick="{bbc_copy_handler}">📋 Copy &quot;{bbc_query}&quot; + open BBC ↗</a>'
    # Direct deep-link to BBC's property page — confirmed pattern /vip/property/{zpid}
    # where zpid is Zillow's numeric ID (extracted from zillowUrl). This page IS the
    # Create Offer flow: lands on Offer Type → Property Details → Buyer Type → Numbers
    # → Buyer's Offer, with Save to Pipeline + Submit JV buttons inside. Replaces the
    # search-and-scroll workflow with a one-tap deep-link. Falls back to search link
    # only if BBC didn't include a zpid (rare — most Lightning Leads have one).
    bbc_property_link = ''
    if d.get('zpid'):
        bbc_property_link = f' <a class="btn" href="https://www.buyboxcartel.com/vip/property/{d["zpid"]}" target="_blank">🏦 Create Offer in BBC ↗</a>'
    # Grand In Taylor JV submission — Richard's dispo pipeline. THREE forms (verified from the
    # dispo-announcements 2026-06-17): Cash · Creative/Hybrid · Multi-Family/Portfolio. Route by
    # cash-vs-creative AND multi-family: cash deals → Cash; creative MFH/portfolio → MultiFam;
    # creative single-family → Creative/Hybrid. (Prior map was missing HY entirely and sent MFH
    # creative to the SFH Creative form.)
    GT_CASH     = 'https://grandintaylorllc.salesmate.io/webforms/#/696ce9d7-457b-44ad-8e6f-a9574197e587'
    GT_CREATIVE = 'https://grandintaylorllc.salesmate.io/webforms/#/5bddb679-43e9-4a91-aca2-ddaff898ff78'
    GT_MULTIFAM = 'https://grandintaylorllc.salesmate.io/webforms/#/f38acae6-368f-4660-aa74-fc48afaa99ca'
    _gt_mfh = (d.get('units') or 0) >= 2 or any(x in (d.get('type','') or '').lower()
                  for x in ('multi','plex','duplex','triplex','fourplex','quad'))
    if t in ('FF', 'C'):
        gt_url, gt_label = GT_CASH, 'Cash'
    elif _gt_mfh:
        gt_url, gt_label = GT_MULTIFAM, 'Multi-Family / Portfolio'
    else:
        gt_url, gt_label = GT_CREATIVE, 'Creative / Hybrid'
    gt_link = f' <a class="btn" href="{gt_url}" target="_blank">🤝 Submit to Grand In Taylor ({gt_label}) ↗</a>' if gt_url else ''
    # HMHW calculator deep-links — tier-routed to the right calculator. The previous
    # #prefill={JSON} hash was a speculative no-op: HMHW's Vite app has zero URL-prefill
    # mechanism (verified 2026-05-14 — no useSearchParams, no hashParams, no localStorage
    # state, no URL↔state sync; only `prefill` references in the bundle are inside an
    # embedded address-autocomplete library). So we ship clean per-tier deep-links plus
    # a 📋 Copy values button that puts the SAME numbers (rendered in the creative_banner
    # above) onto clipboard formatted for paste-by-line into the calculator. Saves 30s
    # of arithmetic per property; user paste-tabs through the form.
    balloon_yr = 7 if t == 'B' else 5
    rent_annual = round((d.get('monthly_rent') or 0) * 12)
    creative_offer_v = d.get('creative_offer', 0) or 0
    creative_down_v = d.get('creative_down', 0) or 0
    closing_v = round(creative_offer_v * 0.01)
    # Tier-routed calculators (8 confirmed in HMHW bundle):
    #   A/B → seller-finance (SF-specific) + offer-oven (universal creative builder)
    #   MT  → mortgage-takeover
    #   FF  → fix-and-flip + rehab-estimator
    #   C   → cash-deal-checker
    hmhw_calcs = {
        'A':  [('Seller Finance', '/tools/seller-finance'), ('Offer Oven', '/tools/offer-oven')],
        'B':  [('Seller Finance', '/tools/seller-finance'), ('Offer Oven', '/tools/offer-oven')],
        'HY': [('Mortgage Takeover', '/tools/mortgage-takeover'), ('Seller Finance', '/tools/seller-finance'), ('Offer Oven', '/tools/offer-oven')],
        'MT': [('Mortgage Takeover', '/tools/mortgage-takeover'), ('Offer Oven', '/tools/offer-oven')],
        'FF': [('Fix & Flip', '/tools/fix-and-flip'), ('Rehab Estimator', '/tools/rehab-estimator')],
        'C':  [('Cash Deal Checker', '/tools/cash-deal-checker')],
    }.get(t, [])
    calc_links_html = ''.join(
        f' <a class="zillow" href="https://www.hmhw.group{path}" target="_blank">🧮 {name} ↗</a>'
        for name, path in hmhw_calcs
    )
    # OUR hosted Offer Oven calculator — mirrors Richard's Google Sheet, auto-fills
    # from the card via URL params. Separate from the legacy hmhw.group web-calc
    # links above (those are left in place). FF tier opens the 70%-rule mode.
    import urllib.parse as _up
    _otype = 'Subto' if t == 'MT' else ('Hybrid' if t == 'HY' else 'Seller Finance')
    _calc_params = {
        'price': creative_offer_v or d.get('price', 0),
        'list': d.get('price', 0),
        'down': creative_down_v,
        'rate': d.get('interest_rate', 0) if t in ('MT', 'HY') else 0,
        'rent': d.get('monthly_rent', 0) or 0,
        'balloon': (d.get('sf_balloon_years') or 7),
        'otype': _otype,
        # Fix C (TRIAGE_OFFEROVEN_RECONCILIATION.md) — pass the per-property tax/ins/HOA
        # + standard $5K assignment + 0 rehab so the calculator reproduces the card/sheet
        # instead of loading its generic defaults ($100 tax / $100 ins / $0 assign / $1K rehab).
        'tax': d.get('tax_monthly', 0) or 0,
        'ins': d.get('insurance_monthly', 0) or 0,
        'hoa': d.get('hoa_monthly', 0) or 0,
        'assign': 5000,
        'rehab': 0,
    }
    if t in ('MT', 'HY'):
        _calc_params['subbal'] = d.get('loan_balance', 0) or 0
        _calc_params['subpay'] = d.get('monthly_payment_actual', 0) or 0
    if t == 'FF':
        _calc_params = {'mode': 'ff', 'arv': d.get('price', 0), 'ffassign': 5000}
    _calc_qs = _up.urlencode({k: v for k, v in _calc_params.items() if v not in (None, '')})
    our_calc_link = (f' <a class="zillow" href="/rt-companion/playbooks/offer-oven-calculator.html?{_calc_qs}" '
                     f'target="_blank">🧮 Calculator (auto-filled) ↗</a>')
    # Clipboard payload — plain-text values, one per line, ready for Tab-key paste.
    # Order matches the Offer Oven field sequence (Purchase Price, Down Payment, Rate,
    # Term, Loan Balance for sub-to, Rental Revenue, Assignment, Closing).
    if t in ('A', 'B', 'HY', 'MT'):
        copy_payload = (
            f'Purchase Price: ${creative_offer_v:,}\\n'
            f'Down Payment: ${creative_down_v:,}\\n'
            f'Interest Rate: 0%\\n'
            f'Term: 30 years\\n'
            f'Balloon: {balloon_yr} years\\n'
            f'Rental Revenue (Annual): ${rent_annual:,}\\n'
            f'Assignment Fee: $5,000\\n'
            f'Closing Costs (1%): ${closing_v:,}'
        )
        copy_handler = (
            f"navigator.clipboard.writeText(`{copy_payload}`);"
            f"this.style.background='#1a4d2e';this.style.color='#56d364';"
            f"this.dataset.orig=this.textContent;this.textContent='✓ Copied — paste into HMHW';"
            f"setTimeout(()=>{{this.style.background='';this.style.color='';this.textContent=this.dataset.orig;}},2000);"
        )
        copy_btn = f' <button class="btn" type="button" onclick="{copy_handler}">📋 Copy values</button>'
    else:
        copy_btn = ''
    oven_link = calc_links_html + copy_btn
    pipe = ' <span class="pill" style="background:#1a4d2e;color:#56d364;">in pipeline</span>' if d.get('in_pipeline') else ''
    # Deal type pill (human readable from BBC's dealType field)
    dt_map = {'sellerFinance': 'Seller Finance', 'mortgageTakeover': 'Mortgage Takeover', 'section8': 'Section 8', 'fixAndFlip': 'Fix & Flip', 'cash': 'Cash'}
    dt_label = dt_map.get(d.get('deal_type',''), d.get('deal_type','') or '')
    dt_pill = f' <span class="pill" style="background:#1e2c44;color:#79c0ff;border-color:#1e2c44;">{dt_label}</span>' if dt_label else ''
    pt_pill = f' <span class="pill" style="background:#1c2128;color:#8b949e;border-color:#30363d;">{d["type"]}</span>' if d.get('type') and d['type']!='Unknown' else ''
    # Status pill — surfaces relist history. Richard treats relisted/removed as a MOTIVATION
    # signal (mortgage-takeover course ~9:15): a fell-through deal means seller is now more
    # motivated and agent has lost a commission once. These are HIGH-priority calls, not skips.
    status_styles = {
        'active':    ('#1c2128', '#8b949e', '✓ Active'),
        'paused':    ('#2c2a14', '#e3b341', f'◐ Paused {d.get("relisted_gap",0)}d gap'),
        'relisted':  ('#3a2418', '#ffa657', f'🔥 RELISTED {d.get("relisted_gap",0)}d gap — motivated seller, call first'),
        'off-zillow':('#2c2c2c', '#8b949e', '✗ Off Zillow (removed — call anyway)'),
    }
    bg, fg, label = status_styles.get(d.get('status_state','active'), status_styles['active'])
    status_pill = f' <span class="pill" style="background:{bg};color:{fg};border-color:{bg};font-weight:600;">{label}</span>'
    cf_label = 'Cash Flow' if t == 'C' else 'Cash Flow'
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
    bank_gap_pill = f' <span class="pill" style="background:#3a2418;color:#ffa657;border-color:#3a2418;font-weight:600;" title="Bank Gap: how much LESS monthly cash flow a conventional investor (DSCR, 20% down, 7%, 30yr P&amp;I) would get vs the creative restructure. The pitch hook — bigger gap = bigger reason the listing fails at standard financing.">🏦 {bg_label} −${bg_amount:,}/mo</span>' if bg_amount > 0 else ''
    # Sold comps — Zillow searchQueryState JSON-encoded URL so all filters apply at once.
    # HOME-TYPE AWARE: a multi-unit property comps ONLY to multifamily sales, never to
    # single-family homes. Richard, Cash Course: "let's comp similar properties...
    # multifamily... that quadplex is definitely not what we are." The prior version
    # used isAllHomes for every card, so duplex/triplex/MFH cards linked to comps that
    # mixed in SFHs — wrong, and useless in low-volume markets. We also emit a WIDE
    # fallback (radius + longer window) because rural/low-volume ZIPs — and rare MFH —
    # return nothing on the tight search.
    zip_code = d.get('zip', '')
    beds = d.get('beds', 0)
    sqft_val = d.get('sqft', 0)
    units_n = d.get('units', 1) or 1
    is_mfh = units_n >= 2 or (d.get('type', '') or '').lower() in (
        'multifamily', 'multi-family', 'multi family', 'duplex', 'triplex',
        'fourplex', 'quadplex', 'quadruplex')
    try:
        lat_f = float(d.get('lat')) if d.get('lat') not in (None, '') else None
        lng_f = float(d.get('lng')) if d.get('lng') not in (None, '') else None
    except (TypeError, ValueError):
        lat_f = lng_f = None

    def _sold_comp_url(wide):
        fs = {
            'sortSelection': {'value': 'globalrelevanceex'},
            'isRecentlySold': {'value': True},
            'isForSaleByAgent': {'value': False},
            'isForSaleByOwner': {'value': False},
            'isNewConstruction': {'value': False},
            'isComingSoon': {'value': False},
            'isAuction': {'value': False},
            'isForSaleForeclosure': {'value': False},
        }
        if is_mfh:
            # Multifamily ONLY — exclude SFH/condo/townhouse/land/manufactured.
            fs.update({'isSingleFamily': {'value': False}, 'isMultiFamily': {'value': True},
                       'isTownhouse': {'value': False}, 'isCondo': {'value': False},
                       'isLotLand': {'value': False}, 'isApartment': {'value': False},
                       'isManufactured': {'value': False}})
        else:
            fs['isAllHomes'] = {'value': True}
        # Sold window: MFH sales are rare → 3yr always; SFH 6mo tight / 1yr wide.
        fs['doz'] = {'value': ('1095' if is_mfh else ('365' if wide else '180'))}
        # Beds/sqft bands only make sense for SFH (per-unit beds + building sqft of an
        # MFH aren't comparable across properties); never on the wide net.
        if beds and not is_mfh:
            fs['beds'] = {'min': max(1, beds - 1), 'max': beds + 1}
        if sqft_val and sqft_val > 200 and not is_mfh and not wide:
            fs['sqft'] = {'min': int(sqft_val * 0.80), 'max': int(sqft_val * 1.20)}
        sqs = {'filterState': fs, 'isListVisible': True}
        if wide and lat_f is not None and lng_f is not None:
            pad = 0.45 if is_mfh else 0.27  # ~25-30mi for rare MFH, ~15mi for SFH
            sqs['mapBounds'] = {'west': lng_f - pad, 'east': lng_f + pad,
                                'south': lat_f - pad, 'north': lat_f + pad}
            sqs['isMapVisible'] = True
            q = urllib.parse.quote(json.dumps(sqs, separators=(',', ':')))
            return f'https://www.zillow.com/homes/recently_sold/?searchQueryState={q}'
        if not zip_code:
            return ''
        q = urllib.parse.quote(json.dumps(sqs, separators=(',', ':')))
        return f'https://www.zillow.com/{zip_code}/sold/?searchQueryState={q}'

    sold_url = _sold_comp_url(wide=False)
    wide_url = _sold_comp_url(wide=True)
    comp_label = 'MFH sold comps' if is_mfh else 'Sold comps'
    sold_link = f' <a class="zillow" href="{sold_url}" target="_blank">{comp_label} ↗</a>' if sold_url else ''
    # Wide fallback — never a dead end. Use when the tight search is empty (rural /
    # low-volume markets, rare multifamily). Re-apply Richard's weighting by hand:
    # closest + same type + year built ±15 win.
    wide_link = (f' <a class="zillow" href="{wide_url}" target="_blank" '
                 f'title="Wider radius + longer sold window. Use when the tight comp search comes back empty (rural / low-volume markets, rare multifamily). Weight the nearest, most-similar 2-3 by hand.">'
                 f'🔭 Wide comps ↗</a>') if wide_url else ''
    # GOOGLE STREET VIEW — closes the gap on Richard's livestream eye-check step 3b.
    # He opens Street View on every property in 5 sec to read the neighborhood +
    # exterior condition before committing to dial. Uses Maps Search API URL with
    # map_action=pano which lands directly in Street View mode when imagery exists,
    # or falls back to address pin if not. Mobile-safe (opens Google Maps app on iOS).
    sv_lat = d.get('lat')
    sv_lng = d.get('lng')
    if sv_lat and sv_lng:
        street_view_url = f'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={sv_lat},{sv_lng}'
    else:
        # Address-fallback when lat/lng missing
        addr_q = urllib.parse.quote(d.get('address',''))
        street_view_url = f'https://www.google.com/maps?q={addr_q}&layer=c'
    street_view_link = f' <a class="zillow" href="{street_view_url}" target="_blank">📍 Street View ↗</a>'
    # PROPWIRE COMPS — community's #1 free comp + owner/equity tool. Propwire has NO
    # per-property deep link (verified 2026-05-23: property view is SPA state, URL
    # stays on /search), so this opens Propwire search AND copies the address to the
    # clipboard for a one-paste lookup (address autocompletes instantly when pasted).
    # Use: confirm ARV before cash/FF offers; check owner equity/lien before MT/HY.
    pw_addr = (d.get('address','') or '').replace("'", "\\'")
    propwire_copy = (
        f"navigator.clipboard.writeText('{pw_addr}');"
        f"this.dataset.o=this.textContent;this.textContent='📋 Address copied — paste in Propwire';"
        f"setTimeout(()=>{{this.textContent=this.dataset.o;}},1800);"
    )
    propwire_link = (f' <a class="zillow" href="https://propwire.com/search" target="_blank" '
                     f'onclick="{propwire_copy}" title="Opens Propwire + copies the address. Paste it in the search box for comps + owner/equity.">'
                     f'📊 Comps (Propwire) ↗</a>')
    rent_link = ''  # Zillow Rent Zestimate on the property page (already linked) covers this
    # Local time pill — updated live by JS (data-tz = IANA timezone)
    tz_pill = f' <span class="pill local-time" data-tz="{d["tz"]}">--:-- local</span>'
    # MT-specific pills — existing-mortgage rate + actual PITI (the numbers Richard
    # eyeballs on the BBC card in his MT walkthroughs). Only render when meaningful.
    mt_rate_pill = ''
    if (t == 'MT' or d.get('deal_type_raw') == 'mortgageTakeover') and d.get('interest_rate'):
        rate_v = d['interest_rate']
        rate_class = 'background:#0d2818;color:#56d364;border-color:#1a4d2e;' if rate_v <= 5.0 else 'background:#1c2128;color:#8b949e;border-color:#30363d;'
        mt_rate_pill = f' <span class="pill" style="{rate_class}font-weight:600;" title="Existing mortgage interest rate — sub-5% is the MT gold mine">📉 {rate_v:.2f}% existing mortgage rate</span>'
    actual_pmt_pill = ''
    if d.get('monthly_payment_actual') and (t == 'MT' or d.get('deal_type_raw') == 'mortgageTakeover'):
        actual_pmt_pill = f' <span class="pill" title="BBC-reported actual seller PITI — Principal + Interest + Taxes + Insurance">💳 Seller PITI ${d["monthly_payment_actual"]:,}/mo</span>'
    # Rent pill — every tier where BBC has a rent estimate. The "what does it rent
    # for" number Richard eyeballs before deciding to dial. Tier B / FF cards depend
    # on it; SF / MT cards too (CF math relies on it).
    rent_pill = ''
    if d.get('monthly_rent'):
        rent_pill = f' <span class="pill" title="BBC rent estimate (used in CF + bank gap calcs)">🏠 Rent ${d["monthly_rent"]:,}/mo</span>'
    # Bank-rate PITI pill — shown on non-MT cards (MT already has 💳 actual PITI).
    # This is OUR computed PITI at market rate (price × 0.8 @ ~7%, with tax + ins),
    # the number an investor would actually pay if they got a conventional loan.
    # Helps non-MT cards show "this is what a normal cash-with-loan would cost".
    bank_piti_pill = ''
    if d.get('monthly_piti') and not (t == 'MT' or d.get('deal_type_raw') == 'mortgageTakeover'):
        bank_piti_pill = f' <span class="pill" title="Computed PITI (Principal + Interest + Taxes + Insurance) at conventional bank rate — 20% down, 7%, 30yr">💳 Bank PITI ${d["monthly_piti"]:,}/mo</span>'
    # Tax + Insurance + HOA pills — re-added 2026-05-16 with FULL LABELS per Tim's
    # feedback (saving a few letters via "T$80 + I$35" wasn't worth the confusion).
    # BBC's cd.tax / cd.insurance fields are nominally monthly but data quality is
    # mixed across properties. Render only when value is in a sane range so we
    # don't surface obvious nonsense (e.g., $0.01 or $99999/mo).
    tax_v = d.get('tax_monthly') or 0
    ins_v = d.get('insurance_monthly') or 0
    hoa_v = d.get('hoa_monthly') or 0
    tax_pill = f' <span class="pill" title="BBC reported monthly property tax">💰 Tax ${tax_v:,}/mo</span>' if 0 < tax_v < 5000 else ''
    ins_pill = f' <span class="pill" title="BBC reported monthly homeowners insurance">🛡 Insurance ${ins_v:,}/mo</span>' if 0 < ins_v < 2000 else ''
    hoa_pill = f' <span class="pill" title="BBC reported monthly HOA fee">🏘 HOA ${hoa_v:,}/mo</span>' if 0 < hoa_v < 2000 else ''
    tax_ins_pill = tax_pill + ins_pill + hoa_pill
    # Agent block — call-action buttons. Three click-targets:
    #   1. Primary green "📞 OpenPhone" — `openphone://call?number=+...` URL scheme.
    #      Registers on Mac (OpenPhone desktop app) + iOS (OpenPhone iOS app).
    #      If app not installed, falls back gracefully (nothing happens — user clicks
    #      next button). Verified scheme per OpenPhone docs 2026-05-18.
    #   2. Secondary "📱 Phone app" — `tel:+...` URL scheme. Works EVERYWHERE:
    #      iPhone Safari → iOS picker (Phone, FaceTime, OpenPhone if installed)
    #      Mac Safari → FaceTime call dialog
    #      Effectively the universal fallback.
    #   3. Tertiary "📋 Copy" — clipboard copy of formatted phone number for
    #      cases where neither URL scheme works (e.g., other browsers/devices).
    agent_block = ''
    if d.get('agent'):
        a = d['agent']
        phone_clean = ''.join(c for c in a['phone'] if c.isdigit() or c == '+')
        if phone_clean and not phone_clean.startswith('+'): phone_clean = '+1' + phone_clean.lstrip('1')
        phone_display = (a.get('phone') or '').replace("'", "\\'")
        if phone_clean:
            # OpenPhone primary button — two modes:
            #   - If Worker configured (BBC_PROXY_URL): JS-driven button that POSTs
            #     contact-create payload to Worker FIRST (creates OpenPhone contact
            #     with property address in `company` field), THEN fires the
            #     openphone://call URL to dial. Contact-create is fire-and-forget
            #     with 2s timeout so the call never blocks on Worker latency.
            #   - If Worker NOT configured: plain <a href="openphone://"> link as
            #     before. No contact create — just dial.
            if BBC_PROXY_URL and BBC_PROXY_SECRET:
                # Worker-routed: JS handler creates contact, then dials.
                import html as _html_mod_op
                op_payload = {
                    'phone': phone_clean,
                    'name': a.get('name', ''),
                    'email': a.get('email', '') if a.get('email') != 'Not Available' else (d.get('mls_agent_email') or ''),
                    'address': d.get('address', ''),
                    'tier': t,
                    'dom': d.get('dom', 0),
                    'pid': d.get('pid', ''),
                    'brokerage': d.get('brokerage', ''),
                    'briefing_url': f'https://timfarr-ai.github.io/rt-companion/briefings/{date_iso}.html',
                }
                op_json_attr = _html_mod_op.escape(json.dumps(op_payload), quote=True)
                op_btn = (f'<button type="button" '
                          f'onclick="rtOpenPhoneCall(this, this.dataset.payload, \'{phone_clean}\')" '
                          f'data-payload="{op_json_attr}" '
                          f'class="btn btn-call-primary" '
                          f'style="background:#1a4d2e;color:#56d364;padding:8px 14px;border-radius:8px;'
                          f'font-weight:600;font-family:inherit;font-size:13.5px;border:1px solid #1a4d2e;'
                          f'cursor:pointer;min-height:38px;display:inline-flex;align-items:center;gap:6px;">'
                          f'📞 OpenPhone + save contact</button>')
            else:
                # No Worker: plain dial-only link
                op_btn = (f'<a href="openphone://call?number={phone_clean}" class="btn btn-call-primary" '
                          f'style="background:#1a4d2e;color:#56d364;padding:8px 14px;border-radius:8px;'
                          f'font-weight:600;text-decoration:none;font-size:13.5px;border:1px solid #1a4d2e;'
                          f'min-height:38px;display:inline-flex;align-items:center;gap:6px;">'
                          f'📞 OpenPhone</a>')
            # tel: secondary (universal fallback)
            tel_btn = (f' <a href="tel:{phone_clean}" class="btn btn-call-secondary" '
                       f'style="background:#1e2c44;color:#79c0ff;padding:8px 14px;border-radius:8px;'
                       f'font-weight:600;text-decoration:none;font-size:13.5px;border:1px solid #1e2c44;'
                       f'min-height:38px;display:inline-flex;align-items:center;gap:6px;">'
                       f'📱 Phone app</a>')
            # Copy-to-clipboard tertiary
            copy_phone_handler = (
                f"navigator.clipboard.writeText('{phone_display}');"
                f"this.style.background='#1a4d2e';this.style.color='#56d364';"
                f"this.dataset.orig=this.textContent;this.textContent='✓ Copied';"
                f"setTimeout(()=>{{this.style.background='';this.style.color='';this.textContent=this.dataset.orig;}},1500);"
            )
            copy_btn = (f' <button type="button" onclick="{copy_phone_handler}" '
                        f'style="background:#1c2128;color:#8b949e;padding:8px 12px;border-radius:8px;'
                        f'font-weight:500;font-size:12.5px;border:1px solid #30363d;cursor:pointer;'
                        f'min-height:38px;display:inline-flex;align-items:center;gap:5px;font-family:inherit;">'
                        f'📋 Copy {a["phone"]}</button>')
            call_btns = op_btn + tel_btn + copy_btn
        else:
            call_btns = f'<span style="color:#8b949e;">📞 {a["phone"]}</span>'
        # Email button if available
        email_btn = ''
        if a.get('email') and a['email'] != 'Not Available':
            email_btn = (f' <a href="mailto:{a["email"]}" '
                         f'style="background:#1c2128;color:#8b949e;padding:8px 12px;border-radius:8px;'
                         f'font-weight:500;text-decoration:none;font-size:12.5px;border:1px solid #30363d;'
                         f'min-height:38px;display:inline-flex;align-items:center;gap:5px;">'
                         f'✉ {a["email"]}</a>')
        # Brokerage line — surfaces the listing office below the agent name so Tim
        # knows which company the agent represents before dialing. Falls back to
        # MLS-attribution agent name if BBC's contact-seller name disagrees with MLS.
        brokerage_line = ''
        if d.get('brokerage'):
            mls_agent = d.get('mls_agent_name', '')
            mls_disagree = (mls_agent and a['name'] and mls_agent.lower() != a['name'].lower())
            mls_note = f' <span style="color:#6e7681;">· MLS attribution: {mls_agent}</span>' if mls_disagree else ''
            brokerage_line = (
                f'<div style="color:#8b949e;font-size:12px;margin-bottom:8px;">'
                f'🏢 <span style="color:#79c0ff;">{d["brokerage"]}</span>{mls_note}'
                f'</div>'
            )
        agent_block = (
            f'<div style="margin-top:10px;padding:10px 12px;background:#161b22;border:1px solid #30363d;border-radius:8px;">'
            f'<div style="color:#e6edf3;font-weight:600;margin-bottom:4px;font-size:14px;">🔓 {a["name"]}</div>'
            f'{brokerage_line}'
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">{call_btns}{email_btn}</div>'
            f'</div>'
        )
    # PHOTO STRIP — horizontal scroll of all BBC photos (up to 8). Mirrors Richard's
    # livestream eye-check: condition + neighborhood read happens here, inline,
    # before the operator commits to dialing. Lazy-loaded so briefing HTML stays light.
    photo_strip = ''
    photos = d.get('images') or []
    if photos:
        photo_tags = ''.join(
            f'<a href="{u}" target="_blank" rel="noopener"><img src="{u}" loading="lazy" alt=""></a>'
            for u in photos
        )
        photo_strip = f'<div class="photos">{photo_tags}</div>'
    # BUYER SIGNAL pill — BBC BuyBoxes is_activeBuyer for this tier×state. NOT a buyer
    # count or contacts — just "is BBC's network demanding this strategy in this state?"
    # Tier mapping: A/B/MT → creative; FF/C → fixflip. Tier B also peeks section8 as bonus.
    state_name_lc = STATE_CODE_TO_NAME.get((d.get('state') or '').upper(), '')
    status_line = ''  # BBC buyer-demand signal, rendered as a quiet colored status line
    if state_name_lc:
        bucket = {'A':'creative','B':'creative','MT':'creative','FF':'fixflip','C':'fixflip'}.get(t)
        if bucket:
            is_active = buyer_signals.get(bucket, {}).get(state_name_lc)
            bucket_label = {'creative':'Creative buyers','fixflip':'Fix&amp;Flip buyers'}[bucket]
            if is_active is True:
                # Tier B bonus: also show section8 if active (rental-investor crossover)
                s8_bonus = ''
                if t == 'B' and buyer_signals.get('section8', {}).get(state_name_lc):
                    s8_bonus = ' + Sec8'
                status_line = f'<div class="status good" title="BBC BuyBoxes: this state is currently active for this strategy">● {bucket_label}{s8_bonus} active</div>'
            elif is_active is False:
                status_line = f'<div class="status warn" title="BBC BuyBoxes: low buyer activity for this strategy in this state — dispo will be harder">⚠ Low {bucket_label.lower().replace("&amp;","&")} activity</div>'
    # CREATIVE CF BANNER — the call hook. Reads: "After restructuring, this deal
    # cash-flows $X/mo. Pitch to seller: $OFFER at 0%, $DOWN down, 30yr."
    cc = d.get('creative_cf', 0)
    coc_v = d.get('coc', 0)
    entry_v = d.get('entry_fee', 0)
    # HYBRID BANNER — CANONICAL (2026-06-12, "Hybrid Multi Family Email Template"). NOT the SF
    # 40%-of-rent method. Hybrid = three parts: (1) cash/down at close, (2) ASSUME the existing
    # mortgage (pay the bank its PITI), (3) carry back the SELLER'S EQUITY as a note:
    #     carry-back = price − down − loan balance   (the equity, NOT 40% of rent, NOT the whole price)
    # The carry-back monthly is NEGOTIATED (e.g. $400/mo in the canonical example), bounded by the
    # cash-flow headroom (rent×0.80 − existing PITI). Balloon pays the remaining carry-back balance.
    hybrid_banner = ''
    if t == 'HY' and d.get('loan_balance') and d.get('price'):
        rent_v = d.get('monthly_rent') or 0
        ex_balance = d['loan_balance']
        ex_rate = d.get('interest_rate') or 0
        ex_piti = d.get('existing_piti') or d.get('monthly_payment_actual') or 0
        if ex_piti == 0:
            r = (ex_rate / 100) / 12
            ex_pi = int(ex_balance * r / (1 - (1 + r) ** -300)) if r > 0 else int(ex_balance / 300)
            ex_piti = ex_pi + int((d['price'] or 0) * 0.015 / 12)
        cash_to_seller = 7500  # cash/down at close — negotiable
        carry_back_amount = max(0, (d.get('price') or 0) - cash_to_seller - ex_balance)  # the equity gap
        headroom = max(0, int(rent_v * 0.80 - ex_piti)) if rent_v else 0
        balloon_years = 5
        _rate_txt = f"@ {ex_rate:.2f}% " if ex_rate else ""
        _headroom_txt = (f" · keep payment ≤ ~${headroom:,}/mo so it still cash-flows" if headroom
                         else " · verify rent for cash-flow headroom")
        hybrid_pitch = (
            f"<strong>${cash_to_seller:,}</strong> cash/down at close · "
            f"assume <strong>${ex_balance:,}</strong> existing loan {_rate_txt}"
            f"(~${ex_piti:,}/mo to bank) · "
            f"carry back <strong>${carry_back_amount:,}</strong> equity as a note over a "
            f"{balloon_years}yr balloon · monthly to seller <strong>negotiated</strong>{_headroom_txt}"
        )
        hybrid_banner = (
            f'<div style="margin:8px 0;padding:10px 12px;background:#1c1a2e;'
            f'border:1px solid #d2a8ff;border-radius:6px;font-size:13.5px;line-height:1.45;">'
            f'<div style="color:#d2a8ff;font-weight:700;margin-bottom:4px;">💬 Hybrid pitch (assume loan + carry the equity)</div>'
            f'<div style="color:#e6edf3;">{hybrid_pitch}</div>'
            f'<div style="font-size:11px;color:#6e7681;margin-top:6px;">Carry-back = price − down − loan balance (the equity). '
            f'Monthly is negotiated, NOT rent-based. '
            f'<a href="/rt-companion/playbooks/hybrid.html" target="_blank" style="color:#58a6ff;">Hybrid playbook ↗</a></div>'
            f'</div>'
        )
    # 40%-OF-RENT RULE BANNER — Richard's verbatim live-call formula for SF tiers.
    # Only renders for Tier A and B (SF deals). MT inherits existing payment; FF/Cash
    # have no monthly payment. The rent_split visualization is a tiny bar chart that
    # shows where rent goes: 40% to seller / 20% PITI / 20% reserves / 20% buyer CF.
    richards_banner = ''
    if t in ('A', 'B') and d.get('richards_pitch_line'):
        rent_v = d.get('monthly_rent') or 0
        to_seller = d.get('richards_monthly_to_seller') or 0
        # End-buyer cash flow estimate: rent − payment to seller − PITI − reserves
        # PITI for the end buyer here is just T+I (no P since they're paying seller, not bank)
        # Use a simplified 1.5% of price/yr for T+I, plus 20% rent for reserves
        tax_ins_mo = int((d.get('price') or 0) * 0.015 / 12)
        reserves_mo = int(rent_v * 0.20)
        buyer_cf_mo = max(0, rent_v - to_seller - tax_ins_mo - reserves_mo)
        # Rent split percentages (visual bar)
        def pct(x): return int(round(x / rent_v * 100)) if rent_v else 0
        p_seller, p_ti, p_res, p_cf = pct(to_seller), pct(tax_ins_mo), pct(reserves_mo), pct(buyer_cf_mo)
        # Mini stacked bar via inline divs
        bar = (
            f'<div style="display:flex;height:14px;border-radius:7px;overflow:hidden;margin:6px 0 4px;border:1px solid #30363d;">'
            f'<div style="flex:{p_seller};background:#56d364;" title="To seller: ${to_seller:,}/mo ({p_seller}%)"></div>'
            f'<div style="flex:{p_ti};background:#79c0ff;" title="End-buyer T+I: ~${tax_ins_mo:,}/mo ({p_ti}%)"></div>'
            f'<div style="flex:{p_res};background:#d2a8ff;" title="Reserves: ${reserves_mo:,}/mo ({p_res}%)"></div>'
            f'<div style="flex:{p_cf};background:#e3b341;" title="End-buyer cash flow: ${buyer_cf_mo:,}/mo ({p_cf}%)"></div>'
            f'</div>'
            f'<div style="font-size:11px;color:#8b949e;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;">'
            f'<span><span style="color:#56d364;">●</span> Seller ${to_seller:,}</span>'
            f'<span><span style="color:#79c0ff;">●</span> T+I ${tax_ins_mo:,}</span>'
            f'<span><span style="color:#d2a8ff;">●</span> Reserves ${reserves_mo:,}</span>'
            f'<span><span style="color:#e3b341;">●</span> Buyer CF ${buyer_cf_mo:,}</span>'
            f'</div>'
        )
        richards_banner = (
            f'<div style="margin:8px 0;padding:10px 12px;background:#0d1f24;'
            f'border:1px solid #1a4d2e;border-radius:6px;font-size:13.5px;line-height:1.4;">'
            f'<div style="color:#e3b341;font-weight:700;margin-bottom:4px;">💬 Richard\'s pitch (40% of rent rule)</div>'
            f'<div style="color:#e6edf3;">{d.get("richards_pitch_line","")}</div>'
            f'{bar}'
            f'<div style="font-size:11px;color:#6e7681;margin-top:2px;">Rent ${rent_v:,}/mo split. <a href="/rt-companion/playbooks/seller-finance.html" target="_blank" style="color:#58a6ff;">Why 40%? ↗</a></div>'
            f'</div>'
        )
    # 70% rule target — surfaced prominently on FF cards (Cash Course L295-340).
    # Richard's rule: cash offer = list price × 0.70. Anything above is over-priced
    # for a flipper. This makes the target offer obvious without operator math.
    target_70_banner = ''
    if t == 'FF' and d.get('price'):
        target_70 = int(d['price'] * 0.70)
        spread = int(d['price']) - target_70
        target_70_banner = (
            f'<div style="margin:6px 0 8px;padding:8px 12px;background:#2a1a44;'
            f'border:1px solid #d2a8ff;border-radius:6px;font-size:13px;line-height:1.4;color:#d2a8ff;">'
            f'<strong style="color:#d2a8ff;">🎯 70% rule target offer: ${target_70:,}</strong> '
            f'<span style="color:#8b949e;">— ${spread:,} below asking · Cash Course rule for distressed cash plays</span>'
            f'</div>'
        )
    # Potential assignment fee per Richard's per-tier math. Surface ABOVE the CF
    # number because it's the headline takeaway ("what's the $ to me?") not the
    # operating numbers. Solo dispo fee — JV through Grand In Taylor splits ~50/50.
    potential_fee = potential_assignment_fee(t, d.get('creative_offer'), d.get('price'))
    d['potential_fee'] = potential_fee  # capture for Airtable
    coc_part = f'<span class="k" title="Cash-on-Cash return: annual cash flow divided by total cash invested">Cash-on-Cash</span> {coc_v}%' if coc_v else ''
    entry_part = f'<span class="k" title="Total cash to close: down payment + closing costs + assignment fee">Entry fee</span> ${entry_v:,}' if entry_v else ''
    sub_sep = ' &nbsp;·&nbsp; ' if (coc_part and entry_part) else ''
    sub_line = f'<div class="sub">{coc_part}{sub_sep}{entry_part}</div>' if (coc_part or entry_part) else ''
    terms_line = f'<div class="terms">{d.get("creative_terms","")}</div>' if d.get('creative_terms') else ''
    creative_banner = (
        f'<div class="pitch">'
        f'<div class="cf">+${cc:,}<small>/mo</small></div>'
        f'{sub_line}{terms_line}'
        f'</div>'
    )
    fee_line = f'<div class="fee">💰 Potential assignment fee <b>${potential_fee:,}</b> (solo — JV splits ~50/50)</div>' if potential_fee else ''
    # RISK FLAGS — heuristic warnings about heavy rehab / REO / data issues
    # BBC's API doesn't expose condition or REO status, so these are inferred from
    # year/foundation/imagery/DOM signals. Operator MUST verify on Zillow.
    risk_flags = d.get('risk_flags') or []
    risk_banner = ''
    if risk_flags:
        risk_lines = '<br>'.join(risk_flags)
        risk_banner = (
            f'<div style="margin:6px 0 8px;padding:8px 12px;background:#3a2418;'
            f'border:1px solid #d29922;border-radius:6px;font-size:13px;line-height:1.5;color:#ffa657;">'
            f'<strong style="color:#ffa657;">CONDITION RISK — VERIFY ZILLOW BEFORE TRACKING:</strong><br>{risk_lines}'
            f'</div>'
        )
    # OWE-VS-ASK MT MOTIVATION BANNER — closes the gap on Richard's Step 5 (the
    # seller-motivation gate he runs in his head on every MT walkthrough). Richard's
    # rule from MT Course L440-520: subtract realtor commission (6%) from asking, then
    # compare to loan balance. If seller's NET is < $10K (or negative), they're stuck
    # and would say yes to a takeover. We surface 3 numbers: balance owed, asking,
    # net-to-seller-after-realtor. Color-coded by motivation level.
    owe_banner = ''
    bal = d.get('loan_balance') or 0
    rate = d.get('interest_rate') or 0
    if (t == 'MT' or d.get('deal_type_raw') == 'mortgageTakeover') and bal > 0 and d.get('price'):
        seller_net = int(d['price'] * 0.94) - bal  # asking minus 6% realtor minus what they owe
        rate_str = f"{rate:.2f}% rate" if rate else ""
        if seller_net <= 5000:
            # Very motivated — seller is stuck, would say yes
            motivation = '🔥 STUCK SELLER — high "yes" probability'
            bg, fg, border = '#3a1e1e', '#ff7b72', '#f85149'
        elif seller_net <= 15000:
            # Motivated — barely above water
            motivation = '⚠️ Barely profitable — motivated'
            bg, fg, border = '#2d2418', '#ffa657', '#d29922'
        elif seller_net <= 30000:
            # Some motivation
            motivation = 'Some equity — possibly negotiable'
            bg, fg, border = '#1c2128', '#8b949e', '#30363d'
        else:
            # Not motivated — seller has cushion
            motivation = '💰 High equity — seller has cushion, harder to motivate'
            bg, fg, border = '#1c2128', '#8b949e', '#30363d'
        owe_banner = (
            f'<div style="margin:6px 0 8px;padding:8px 12px;background:{bg};'
            f'border:1px solid {border};border-radius:6px;font-size:13px;line-height:1.4;color:{fg};">'
            f'<strong style="color:{fg};">🏠 Owe vs Ask:</strong> '
            f'owes <strong>${bal:,}</strong> @ {rate_str} · '
            f'asking <strong>${int(d["price"]):,}</strong> · '
            f'seller net after 6% realtor = <strong>${seller_net:,}</strong> &nbsp;·&nbsp; '
            f'<span style="font-weight:600;">{motivation}</span>'
            f'</div>'
        )
    # DESC-FLIP BANNER — listing description contained 3+ flip-vocab keywords.
    # Shows on FF cards that were demoted from A/B/MT via the desc-keyword pass
    # (cases where BBC's priceHistory had no Sold event so the markup detector missed).
    desc_flip_kws = d.get('desc_flip_keywords') or []
    desc_flip_banner = ''
    if len(desc_flip_kws) >= 3:
        desc_flip_banner = (
            f'<div style="margin:6px 0 8px;padding:8px 12px;background:#3a1e1e;'
            f'border:1px solid #f85149;border-radius:6px;font-size:13px;line-height:1.4;color:#ff7b72;">'
            f'<strong style="color:#ff7b72;">🔥 SUSPECTED FLIP (description):</strong> '
            f'{len(desc_flip_kws)} flip-vocab keywords in listing — '
            f'<em>{", ".join(desc_flip_kws[:4])}</em>'
            f'</div>'
        )
    # FLIP-RELIST BANNER — surfaces when property was bought cheap recently and
    # relisted with markup. Seller wants cash, not SF. Banner shows even for cards
    # that weren't demoted (e.g. markup 20-34%) so operator has the context.
    flip_banner = ''
    markup = d.get('flip_markup_pct')
    if markup is not None and markup >= 0.20 and d.get('last_sold_price') and d.get('last_sold_date'):
        markup_pct = round(markup * 100, 1)
        mo_ago = d.get('months_since_sale') or 0
        if markup >= 0.35 and mo_ago <= 24:
            flip_banner = (
                f'<div style="margin:6px 0 8px;padding:8px 12px;background:#3a1e1e;'
                f'border:1px solid #f85149;border-radius:6px;font-size:13px;line-height:1.4;color:#ff7b72;">'
                f'<strong style="color:#ff7b72;">🔥 INVESTOR FLIP RELIST:</strong> '
                f'sold ${d["last_sold_price"]:,} on {d["last_sold_date"]} ({mo_ago}mo ago) → relisted +{markup_pct}% — '
                f'seller wants cash to roll into next deal, NOT receptive to SF'
                f'</div>'
            )
        elif markup >= 0.20:
            # Soft warning for 20-34% markup — could be flip or legit equity gain
            flip_banner = (
                f'<div style="margin:6px 0 8px;padding:6px 10px;background:#2d2418;'
                f'border:1px solid #d29922;border-radius:6px;font-size:12px;color:#ffa657;">'
                f'⚠️ Markup vs last sale: ${d["last_sold_price"]:,} → ${d["price"]:,.0f} (+{markup_pct}%) {mo_ago}mo ago'
                f'</div>'
            )
    # VISION VERDICT — Claude's photo-based assessment surfaced inline
    vision = d.get('vision') or {}
    vision_banner = ''
    if vision:
        cond = vision.get('condition', '?')
        notes = (vision.get('notes') or '').replace('<','').replace('>','')[:120]
        cond_emoji = {5:'🟢',4:'🟢',3:'🟡',2:'🟠',1:'🔴'}.get(cond, '⚪')
        vision_banner = (
            f'<div style="margin:6px 0 8px;padding:6px 10px;background:#161b22;'
            f'border:1px solid #30363d;border-radius:6px;font-size:12px;color:#8b949e;">'
            f'{cond_emoji} <strong style="color:#e6edf3;">Claude vision:</strong> condition {cond}/5 · {notes}'
            f'</div>'
        )
    # TRACK PROPERTY button — prefilled Airtable link. Tapping creates a Deal Flow
    # record so the property drops out of tomorrow's daily. Tim manages it through
    # the Airtable kanban from here. Uses Airtable's URL prefill (?prefill_Field=val).
    tier_label = {'A':'A (MFH SF)','B':'B (Cheap SFH SF)','HY':'HY (Hybrid: MT + SF carry-back)','MT':'MT (Mortgage Takeover)','FF':'FF (Fix & Flip)','C':'C (Cash)'}.get(t, '')
    dt_label_at = {'sellerFinance':'Seller Finance','mortgageTakeover':'Mortgage Takeover','fixAndFlip':'Fix & Flip','cash':'Cash'}.get(d.get('deal_type',''), '')
    addr_parts = [p.strip() for p in d['address'].split(',') if p.strip()]
    city_at = addr_parts[1] if len(addr_parts) >= 2 else ''
    state_at = (addr_parts[2].split()[0] if len(addr_parts) >= 3 else d.get('state',''))
    agent_name_at = (d.get('agent') or {}).get('name', '')
    agent_phone_at = (d.get('agent') or {}).get('phone', '')
    agent_email_at = (d.get('agent') or {}).get('email', '')
    # Build the FULL data-capture prefill payload — every signal we surface on the
    # card should land in the Airtable record. Updated 2026-05-15 to capture all 25
    # new fields (MT loan data, vision verdict, flip signals, buyer signal, etc.)
    # plus the existing 15. Percent fields use decimal (Airtable convention: 0.235).
    vision_d = d.get('vision') or {}
    buyer_signal_label = 'N/A'
    bs_bucket = {'A':'creative','B':'creative','MT':'creative','FF':'fixflip','C':'fixflip'}.get(t)
    if bs_bucket and state_name_lc:
        bs_active = buyer_signals.get(bs_bucket, {}).get(state_name_lc)
        if bs_active is True: buyer_signal_label = 'Active'
        elif bs_active is False: buyer_signal_label = 'Low Activity'
    first_photo = (d.get('images') or [''])[0] if d.get('images') else ''
    creative_offer_v = d.get('creative_offer') or 0
    creative_down_v = d.get('creative_down') or 0
    # Common payload — same shape for Track + Reject (both tables share these fields)
    common_capture = {
        'prefill_Address': d['address'],
        'prefill_PID': d.get('pid',''),
        'prefill_State': state_at,
        'prefill_City': city_at,
        'prefill_ZIP': d.get('zip',''),
        'prefill_List Price': str(int(d['price'])) if d.get('price') else '',
        'prefill_Zillow URL': d.get('zillow','') or '',
        'prefill_Beds': str(d.get('beds','')) if d.get('beds') else '',
        'prefill_Baths': str(d.get('baths','')) if d.get('baths') else '',
        'prefill_Sqft': str(d.get('sqft','')) if d.get('sqft') else '',
        'prefill_Year Built': str(d.get('year_built','')) if d.get('year_built') else '',
        'prefill_Lot Size Sqft': str(d.get('lot_size_sqft','')) if d.get('lot_size_sqft') else '',
        'prefill_Property Type': d.get('type','') or '',
        'prefill_Loan Balance': str(d.get('loan_balance','')) if d.get('loan_balance') else '',
        # Airtable percent fields: send the literal percent number (6.25 for 6.25%)
        # NOT decimal (0.0625). Verified 2026-05-15 via CDP form prefill test.
        'prefill_Existing Rate': str(d.get('interest_rate', 0)) if d.get('interest_rate') else '',
        'prefill_Existing PITI': str(d.get('existing_piti') or d.get('monthly_payment_actual','')) if (d.get('existing_piti') or d.get('monthly_payment_actual')) else '',
        'prefill_Bank Gap': str(d.get('bank_gap','')) if d.get('bank_gap') else '',
        'prefill_Monthly Rent': str(d.get('monthly_rent','')) if d.get('monthly_rent') else '',
        'prefill_CoC %': str(d.get('coc', 0)) if d.get('coc') else '',
        'prefill_Equity %': str(d.get('equity', 0)) if d.get('equity') else '',
        'prefill_Creative Offer': str(int(creative_offer_v)) if creative_offer_v else '',
        'prefill_Creative Down': str(int(creative_down_v)) if creative_down_v else '',
        'prefill_Creative Terms': (d.get('creative_terms','') or '')[:200],
        'prefill_Potential Fee': str(d.get('potential_fee','')) if d.get('potential_fee') else '',
        'prefill_Vision Condition': str(vision_d.get('condition','')) if vision_d.get('condition') else '',
        'prefill_Vision Notes': (vision_d.get('notes','') or '')[:200],
        'prefill_Buyer Signal': buyer_signal_label,
        'prefill_Status State': d.get('status_state',''),
        'prefill_Last Sold Price': str(d.get('last_sold_price','')) if d.get('last_sold_price') else '',
        'prefill_Last Sold Date': d.get('last_sold_date','') or '',
        'prefill_Agent Email': agent_email_at,
        'prefill_First Photo URL': first_photo,
    }
    track_params = {**common_capture,
        'prefill_Status': 'Triage',
        'prefill_Tier': tier_label,
        'prefill_Deal Type': dt_label_at,
        'prefill_Creative CF': str(int(cc)) if cc else '',
        'prefill_DOM': str(d.get('dom','')),
        'prefill_Agent Name': agent_name_at,
        'prefill_Agent Phone': agent_phone_at,
        'prefill_Briefing Date': date_iso,
        'prefill_First Tracked': date_iso,
    }
    track_qs = '&'.join(f'{urllib.parse.quote(k)}={urllib.parse.quote(v)}' for k,v in track_params.items() if v)
    # Use the published Form share URL — same fix as the Reject button. Bare Grid
    # URL prefill is unreliable, especially on mobile. Form view: viwLacCnkkZZF59Ko,
    # share token: shrccLE11iM5TsWa2 (created 2026-05-15 via CDP).
    track_url = f'https://airtable.com/{AT_BASE}/shrccLE11iM5TsWa2?{track_qs}'
    track_link = f' <a class="btn primary" href="{track_url}" target="_blank">＋ Track Property</a>'
    # REJECT button — opens 'Rejected by Tim' Airtable with prefilled context. Each
    # rejection feeds the weekly optimization agent which proposes new filter rules
    # so this category of mistake doesn't repeat. Permanent dedupe by PID.
    # Extra reject-only fields: flip markup %, description snippet, risk flags.
    flip_markup_v = d.get('flip_markup_pct')
    risk_flags_v = d.get('risk_flags') or []
    reject_params = {**common_capture,
        'prefill_Tier (was)': tier_label,
        'prefill_Agent Name (at reject)': agent_name_at,
        'prefill_Rejected Date': date_iso,
        'prefill_Flip Markup %': str(round(flip_markup_v * 100, 1)) if flip_markup_v else '',
        'prefill_Description Snippet': (d.get('description','') or '')[:400],
        'prefill_Risk Flags': '\n'.join(risk_flags_v) if risk_flags_v else '',
    }
    reject_qs = '&'.join(f'{urllib.parse.quote(k)}={urllib.parse.quote(v)}' for k,v in reject_params.items() if v)
    # Use the published Form share URL (shrHDH8RyCB4xXCTZ) — confirmed working with
    # ?prefill_FieldName=value across mobile + desktop. The bare table URL didn't
    # reliably open a Create Record modal (especially on mobile Safari).
    # Form view: viwValWHCe30R9EOS, created 2026-05-15 via CDP UI.
    reject_url = f'https://airtable.com/{AT_BASE}/shrHDH8RyCB4xXCTZ?{reject_qs}'
    reject_link = f' <a class="btn danger" href="{reject_url}" target="_blank" title="Permanently reject from future triage + feed the optimization agent">✕ Reject</a>'

    # SAVE TO BBC PIPELINE button — only renders when Cloudflare Worker is configured
    # via BBC_PROXY_URL + BBC_PROXY_SECRET env vars. Hits the Worker which calls
    # BBC's /pipeline/add server-side, bypassing iPhone's no-userscript problem.
    pipeline_btn = ''
    if BBC_PROXY_URL and BBC_PROXY_SECRET:
        # Build the pipelineData payload BBC's API expects (mirrors what the
        # Save to Pipeline button in BBC's Create Offer modal sends).
        pipeline_payload = {
            'address': d['address'],
            'pid': d.get('pid', ''),
            'creative_contract_details': {
                'listPrice': str(d['price']),
                'rent': str(d.get('monthly_rent', 0)),
                'monthlyCashFlow': str(d.get('creative_cf', 0)),
                'offerPrice': str(d.get('creative_offer', d['price'])),
                'downPayment': str(d.get('creative_down', 0)),
                # Fix G — balloon in MONTHS, matching the card's displayed term (Tier A 5yr,
                # B/MT/HY 7yr) instead of the old hardcoded 96 (8yr) the card never showed.
                'balloon': (d.get('sf_balloon_years') or 7) * 12,
                'dealType': d.get('deal_type_raw', 'sellerFinance'),
            },
            'email_data': {
                'address': d['address'],
                'offerPrice': str(d.get('creative_offer', d['price'])),
                'downPayment': str(d.get('creative_down', 0)),
            },
            'property_info_details': {
                'street': addr_parts[0] if addr_parts else d['address'],
                'city': city_at, 'state': state_at,
                'zip': d.get('zip', ''),
                'latitude': d.get('lat', ''), 'longitude': d.get('lng', ''),
                'property_type': d.get('type', ''),
                'beds': d.get('beds', 0), 'baths': d.get('baths', 0),
                'sqft': d.get('sqft', 0),
                'daysOnMarket': d.get('dom', 0),
            }
        }
        # JSON-encode + escape for embedding in onclick attribute
        import html as _html_mod
        pipeline_json_attr = _html_mod.escape(json.dumps(pipeline_payload), quote=True)
        pipeline_btn = f' <button class="btn" type="button" onclick="bbcSavePipeline(this, this.dataset.payload)" data-payload="{pipeline_json_attr}">🔑 Save to BBC Pipeline</button>'
    # CARD STRUCTURE — redesigned 2026-05-15 from wall-of-links to logical sections.
    # 4 sections mirror Richard's livestream workflow:
    #   ① CURRENT STATE   = BBC card facts (price, DOM, mortgage data, signals)
    #   ② CREATIVE OUTCOME = Pitch math + risk banners
    #   ③ RESEARCH        = Buttons for passive verification (Street View, Zillow, calcs)
    #   ④ ACTION          = SOP-ordered: open playbook → copy values → call → commit → dispo
    physical_meta = f'{d["units"]} units · {d["type"]}'
    extras = []
    if d.get('beds') or d.get('baths'):
        bb = f"{d.get('beds',0)}bd/{d.get('baths',0)}ba"
        if d.get('sqft'): bb += f"/{d['sqft']:,}sqft"
        extras.append(bb)
    if d.get('year_built'): extras.append(f"built {d['year_built']}")
    if d.get('lot_size_sqft'): extras.append(f"lot {d['lot_size_sqft']:,}sqft")
    if extras: physical_meta += ' · ' + ' · '.join(extras)
    # ── ① CURRENT STATE layout (2026-05-26 redesign) ────────────────────────
    # Three hero stat boxes carry the decision numbers (asking / rent / DOM);
    # everything else collapses into one quiet grey spec line. Color is reserved
    # for meaning only — see the new CSS. Replaces the old 12-pill flat row where
    # the list price was lost among tax/insurance/local-time pills.
    rent_hero = d.get('monthly_rent') or 0
    rent_hero_html = (f'${rent_hero:,}<small>/mo</small>') if rent_hero else '—'
    dom_disp = f'{d["dom"]} {d["dom_flag"]}'.strip()
    hero_html = (
        f'<div class="heroRow">'
        f'<div class="hero"><div class="v">${d["price"]:,.0f}</div><div class="l">Asking</div></div>'
        f'<div class="hero"><div class="v">{rent_hero_html}</div><div class="l">Market Rent</div></div>'
        f'<div class="hero"><div class="v">{dom_disp}</div><div class="l">Days on Market</div></div>'
        f'</div>'
    )
    is_mt_like = (t == 'MT' or d.get('deal_type_raw') == 'mortgageTakeover')
    spec_bits = []
    if d.get('type') and d['type'] != 'Unknown': spec_bits.append(d['type'])
    # Multi-unit caution — the Asking/Market-Rent heroes can be a PACKAGE (multiple
    # parcels / all units) stapled to one address. Confirm the rent is COMBINED gross
    # for every unit and that price/sqft isn't a multi-property bundle before trusting
    # the CF. Comp to multifamily sales only. See briefing package mis-attribution.
    _units_n = d.get('units', 1) or 1
    if _units_n >= 2:
        spec_bits.append(
            f'<b style="color:#ffa657;">⚠ {_units_n} units</b> '
            f'<span style="color:#8b949e;">— verify rent is COMBINED &amp; price isn\'t a multi-parcel package</span>')
    ex_rate_v = d.get('interest_rate') or 0
    if is_mt_like and ex_rate_v: spec_bits.append(f'<b>Existing rate</b> {ex_rate_v:.2f}%')
    # Single canonical existing-PITI on MT cards (fix F) — the full obligation the buyer
    # assumes, computed once in classify_strategy(). Falls back to the P&I figure if needed.
    if is_mt_like:
        _exp = d.get('existing_piti') or d.get('monthly_piti') or d.get('monthly_payment_actual')
        if _exp: spec_bits.append(f'<b>Existing PITI (assume)</b> ${_exp:,}/mo')
        # Exit-channel tag (committed 2026-06-12): cash-flows ⇒ investor; doesn't ⇒ $0-down live-in/retail.
        _exit = d.get('exit_channel')
        if _exit == 'investor':
            spec_bits.append('<b style="color:#56d364;">Exit</b> Investor (cash-flows)')
        elif _exit == 'retail/live-in':
            spec_bits.append('<b style="color:#d2a8ff;">Exit</b> Live-in/retail ($0 down)')
        elif _exit == 'investor?':
            spec_bits.append('<b style="color:#e3b341;">Exit</b> verify rent (BBC ~40% fill)')
        if d.get('trojan_horse_offer'):
            spec_bits.append(f'<b>Trojan-Horse cash offer</b> ${d["trojan_horse_offer"]:,} <span style="color:#6e7681;">(balance + 4%, nets seller ~$0 → pivot)</span>')
    if (not is_mt_like) and d.get('monthly_piti'): spec_bits.append(f'<b>Bank PITI</b> ${d["monthly_piti"]:,}/mo')
    if 0 < tax_v < 5000: spec_bits.append(f'<b>Tax</b> ${tax_v:,}')
    if 0 < ins_v < 2000: spec_bits.append(f'<b>Ins</b> ${ins_v:,}')
    if 0 < hoa_v < 2000: spec_bits.append(f'<b>HOA</b> ${hoa_v:,}')
    if bg_amount > 0: spec_bits.append(f'<b>{bg_label}</b> −${bg_amount:,}/mo')
    tag_html = f'<span class="tag">{dt_label}</span>' if dt_label else ''
    spec_line = f'<div class="specline">{tag_html}{" &nbsp;·&nbsp; ".join(spec_bits)}</div>' if (tag_html or spec_bits) else ''
    # 🔴 CALL FIRST badge — Tier A deals at/above the CoC shortlist threshold.
    _coc = d.get('creative_coc', 0)
    callfirst_badge = (
        f'<div style="display:inline-block;background:#c0392b;color:#fff;font-size:11px;'
        f'font-weight:700;letter-spacing:.6px;padding:3px 9px;border-radius:3px;margin-bottom:8px;">'
        f'🔴 CALL FIRST · {_coc:.0f}% CoC</div>'
    ) if (t == 'A' and _coc >= CALLFIRST_COC) else ''
    # DETERMINATION LINE — the explicit "why this strategy" test result from
    # classify_strategy() (STRATEGY_REALIGNMENT_PLAN.md §1). Makes the routing method
    # visible on every card instead of hidden in the code.
    _grp = d.get('strategy_group') or ''
    _sub = d.get('strategy_subtype') or ''
    _grp_label = (f'{_grp} · {_sub}' if (_grp and _sub) else (_grp or 'Strategy'))
    _determ = d.get('determination') or ''
    determination_banner = (
        f'<div style="margin:0 0 8px;padding:8px 11px;background:#161b22;border:1px solid #30363d;'
        f'border-left:3px solid #58a6ff;border-radius:5px;font-size:12.5px;line-height:1.45;">'
        f'<span style="color:#58a6ff;font-weight:700;">{_grp_label}</span>'
        f'<span style="color:#6e7681;"> — why it\'s here: </span>'
        f'<span style="color:#c9d1d9;">{_determ}</span>'
        f'</div>'
    ) if _determ else ''
    return (
        f'<div class="deal {cls}" id="deal-{d.get("pid","")}">'
        # HEADER
        f'<div class="deal-header">'
        f'{callfirst_badge}'
        f'<div class="addr">{d["address"]}{pipe}{status_pill if d.get("status_state") != "active" else ""}</div>'
        f'<div class="meta">{physical_meta}</div>'
        f'</div>'
        # ① CURRENT STATE — hero decision numbers, then quiet spec line + buyer
        # status, THEN photos (so the numbers hit before the operator scrolls the
        # photo strip), then warning banners (owe-vs-ask, flip history, vision, risk).
        f'<div class="card-section">'
        f'<div class="section-label">① Current State</div>'
        f'{hero_html}'
        f'{spec_line}'
        f'{status_line}'
        f'{photo_strip}'
        f'{owe_banner}'
        f'{flip_banner}{desc_flip_banner}'
        f'{risk_banner}{vision_banner}'
        f'</div>'
        # ② CREATIVE OUTCOME — what the deal looks like AFTER our restructure.
        # Just the creative_banner (CF + CoC + entry + terms) and buyer match.
        # FF cards also get the 70% rule target offer banner (Richard's Cash Course).
        f'<div class="card-section">'
        f'<div class="section-label">② Creative Outcome (the pitch)</div>'
        f'{determination_banner}'
        f'{target_70_banner}'
        f'{creative_banner}'
        f'{fee_line}'
        f'{hybrid_banner}'
        f'{richards_banner}'
        f'{bl}'
        f'</div>'
        # ③ RESEARCH BUTTONS
        f'<div class="card-section">'
        f'<div class="section-label">③ Research (verify before dialing)</div>'
        f'<div class="btn-row">{street_view_link}{z}{sold_link}{wide_link}{propwire_link}{our_calc_link}{oven_link}{bbc_link}{bbc_mobile_link}</div>'
        f'</div>'
        # ④ ACTION SEQUENCE — SOP-ordered
        f'<div class="card-section">'
        f'<div class="section-label">④ Action Sequence (SOP flow)</div>'
        f'{agent_block}'
        f'<div class="btn-row btn-row-actions">'
        f'<a class="btn btn-script" href="{playbook}">📖 {(d.get("strategy_subtype") or d.get("strategy_group") or "Strategy")} playbook</a>'
        f'{track_link}{reject_link}'
        f'{bbc_property_link}{gt_link}{pipeline_btn}'
        f'</div>'
        f'</div>'
        f'</div>'
    )

def _build_section_a():
    if not buckets['A']: return ''
    # already sorted by creative_coc desc above
    cf   = [d for d in buckets['A'] if d.get('creative_coc',0) >= CALLFIRST_COC]
    std  = [d for d in buckets['A'] if TIER_A_FLOOR_COC <= d.get('creative_coc',0) < CALLFIRST_COC]
    back = [d for d in buckets['A'] if d.get('creative_coc',0) < TIER_A_FLOOR_COC]
    rend = lambda lst: ''.join(render_deal(d,'A') for d in lst)
    out = ['<h2>🎯 TIER A — Multifamily Seller Finance ($200K-$1.4M, 2+ units, DOM 90+; 2-4 units only if NOT retail-desirable)</h2>']
    if cf:
        out.append(f'<h3 style="color:#c0392b;margin:18px 0 8px;">🔴 CALL FIRST — CoC ≥ {CALLFIRST_COC}% ({len(cf)})</h3>')
        out.append(rend(cf))
    if std:
        out.append(f'<h3 style="color:#1a2332;margin:22px 0 8px;">CoC {TIER_A_FLOOR_COC}–{CALLFIRST_COC}% ({len(std)})</h3>')
        out.append(rend(std))
    if back:
        out.append(
            f'<details style="margin-top:22px;background:#f4f6f9;border-radius:6px;padding:10px 14px;">'
            f'<summary style="cursor:pointer;font-weight:700;color:#5a7a99;">'
            f'⚪ Below {TIER_A_FLOOR_COC}% CoC — backlog ({len(back)}) — sub-stock-market return, click to expand</summary>'
            f'<div style="margin-top:12px;">{rend(back)}</div></details>')
    return ''.join(out)
section_a = _build_section_a()
section_b = ('<h2>🏘️ TIER B — Cheap SFH Stale Seller Finance (&lt;$150K, SFH, DOM 90+)</h2>' + ''.join(render_deal(d,'B') for d in buckets['B'])) if buckets['B'] else ''
section_hy = ('<h2>🔀 HYBRID — Assume existing favorable loan + carry-back the seller equity gap (SF terms on the gap)</h2>' + ''.join(render_deal(d,'HY') for d in buckets['HY'])) if buckets['HY'] else ''
section_mt = ('<h2>🔑 MORTGAGE TAKEOVER — Favorable existing loan, LOW equity (positive CF at assumed rate, DOM 60+)</h2>' + ''.join(render_deal(d,'MT') for d in buckets['MT'])) if buckets['MT'] else ''
section_ff = ('<h2>🔨 FIX &amp; FLIP — Cheap distressed cash plays (Cash Course 70% rule, &lt;$250K, DOM 60+)</h2>' + ''.join(render_deal(d,'FF') for d in buckets['FF'])) if buckets['FF'] else ''
section_c = ('<h2>💵 TIER C — Cash-Comparable SFH (cash arbitrage, NOT seller finance)</h2>' + ''.join(render_deal(d,'C') for d in buckets['C'])) if buckets['C'] else ''
rej_section = ''
if buckets['REJECT']:
    rej_lines = ''.join(f'<div class="rejected">{s["address"]} — CF: ${s["cf"]:,.0f} (DOM {s["dom"]})</div>' for s in buckets['REJECT'][:15])
    rej_section = f'<h2>❌ REJECTED — {pushed} pushed to <a href="https://airtable.com/{AT_BASE}/{WL_TABLE}">Watchlist</a></h2>{rej_lines}'

# ── 3-GROUP DISPLAY + CROSS-GROUP CALL SHEET (STRATEGY_REALIGNMENT_PLAN.md §0,§2) ──
# The 6 internal buckets roll up to HMHW's 3 Discord groups. Each group is subtotaled;
# a single ranked "Today's Call Sheet" sits on top, overflow stays in the groups below.
_GROUP_COLOR = {'Seller Finance':'#56d364','Mortgage Takeover':'#79c0ff','Cash Deals':'#f0883e'}

def _group_block(emoji, title, subtitle, count, inner_html):
    if not inner_html: return ''
    accent = {'🤑':'#56d364','🏛️':'#79c0ff','🏚️':'#f0883e'}.get(emoji, '#58a6ff')
    return (
        f'<div style="margin:28px 0 4px;padding:13px 15px;background:#11161d;border:1px solid #30363d;'
        f'border-radius:10px;border-left:4px solid {accent};">'
        f'<div style="font-size:17px;font-weight:800;color:#e6edf3;">{emoji} {title} '
        f'<span style="color:{accent};">({count})</span></div>'
        f'<div style="font-size:12px;color:#8b949e;margin-top:3px;">{subtitle}</div>'
        f'</div>' + inner_html
    )

# Cross-group ranked call sheet — rank = fee_potential × motivation(DOM) × fit(CoC + buyer).
_all_deals = [(letter, d) for letter in ('A','B','HY','MT','FF','C') for d in buckets[letter]]
def _cs_rank(letter, d):
    fee = d.get('potential_fee') or potential_assignment_fee(letter, d.get('creative_offer') or d.get('price') or 0, d.get('price') or 0)
    motivation = 1.0 + min(d.get('dom') or 0, 400) / 200.0          # 1.0–3.0 by staleness
    fit = 1.0 + (d.get('creative_coc') or 0) / 100.0 + (0.5 if d.get('buyer_matches') else 0.0)
    return fee * motivation * fit
_ranked = sorted(_all_deals, key=lambda x: _cs_rank(*x), reverse=True)
_top20 = _ranked[:20]

def _build_call_sheet():
    if not _top20: return ''
    rows = []
    for i, (letter, d) in enumerate(_top20, 1):
        grp = d.get('strategy_group') or ''
        sub = d.get('strategy_subtype') or ''
        gl = f'{grp} · {sub}' if sub else (grp or 'Strategy')
        fee = d.get('potential_fee') or potential_assignment_fee(letter, d.get('creative_offer') or d.get('price') or 0, d.get('price') or 0)
        cc = d.get('creative_cf') or 0
        coc = d.get('coc') or 0
        dom = d.get('dom') or 0
        pid = d.get('pid', '')
        gcolor = _GROUP_COLOR.get(grp, '#8b949e')
        street = d['address'].split(',')[0]
        locale = d['address'].split(',', 1)[1].strip() if ',' in d['address'] else ''
        rows.append(
            f'<a href="#deal-{pid}" style="display:flex;gap:9px;align-items:baseline;flex-wrap:wrap;'
            f'padding:9px 11px;border-bottom:1px solid #21262d;text-decoration:none;color:#e6edf3;">'
            f'<span style="color:#6e7681;font-weight:700;min-width:24px;">#{i}</span>'
            f'<span style="font-weight:700;">{street}</span>'
            f'<span style="color:#8b949e;font-size:12px;">{locale}</span>'
            f'<span style="color:{gcolor};font-size:12px;font-weight:600;">{gl}</span>'
            f'<span style="color:#56d364;font-size:12.5px;">CF ${cc:,}/mo</span>'
            f'<span style="color:#8b949e;font-size:12px;">CoC {coc}% · DOM {dom} · fee ~${fee:,}</span>'
            f'</a>'
        )
    return (
        f'<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:4px 4px 6px;margin:8px 0 8px;">'
        f'<div style="font-size:16px;font-weight:800;padding:11px 11px 7px;">📞 Today\'s Call Sheet — {len(_top20)} best '
        f'<span style="color:#6e7681;font-size:12px;font-weight:600;">(ranked fee × motivation × fit · tap to jump)</span></div>'
        + ''.join(rows) + f'</div>'
    )
call_sheet = _build_call_sheet()

_n_sf, _n_mt, _n_cash = len(buckets['A'])+len(buckets['B']), len(buckets['MT'])+len(buckets['HY']), len(buckets['FF'])+len(buckets['C'])
group_sf   = _group_block('🤑', 'SELLER FINANCE', 'Free &amp; clear (no loan) → 40%-of-rent math. Checkmate (MFH / non-retail) · Stale-SFH (cheap, long DOM).', _n_sf, section_a + section_b)
group_mt   = _group_block('🏛️', 'MORTGAGE TAKEOVER', 'Existing loan stays in place. Sub-To (cornered seller, small lump) · Hybrid (real equity + low rate → assume + carry note).', _n_mt, section_mt + section_hy)
group_cash = _group_block('🏚️', 'CASH DEALS', 'Fix &amp; Flip (70%-of-list) · cash arbitrage.', _n_cash, section_ff + section_c)

agent_indicator = f' · 🔓 {unlocks_succeeded} agents captured (free)' if unlocks_succeeded else ''
summary = f'{len(all_leads)} leads · 🤑 {_n_sf} Seller Finance · 🏛️ {_n_mt} Mortgage Takeover · 🏚️ {_n_cash} Cash · {pushed} → watchlist{agent_indicator}'
CSS = '''
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:12px;font-size:15px;line-height:1.5;}
h2{font-size:14px;color:#8b949e;text-transform:uppercase;letter-spacing:0.04em;margin:18px 0 8px;}
.summary{background:#1c2128;border:1px solid #30363d;border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:14px;}
.deal{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin-bottom:14px;}
.deal-header{margin-bottom:8px;}
.deal .addr{font-weight:600;font-size:16px;margin-bottom:4px;}
.deal .meta{font-size:13px;color:#8b949e;}
.card-section{margin-top:12px;padding-top:10px;border-top:1px dashed #30363d;}
.card-section:first-of-type{border-top:none;padding-top:8px;}
.section-label{font-size:11px;color:#6e7681;text-transform:uppercase;letter-spacing:0.07em;font-weight:600;margin:16px 0 8px;display:flex;align-items:center;gap:7px;}
.section-label::after{content:"";flex:1;height:1px;background:#30363d;}
.card-section:first-of-type .section-label{margin-top:4px;}
/* ① hero stat trio — the decision numbers */
.heroRow{display:flex;gap:8px;margin:10px 0;}
.hero{flex:1;background:#1c2128;border:1px solid #30363d;border-radius:10px;padding:10px 12px;}
.hero .v{font-size:21px;font-weight:800;line-height:1.1;}
.hero .v small{font-size:12px;font-weight:700;color:#8b949e;}
.hero .l{font-size:10px;color:#6e7681;text-transform:uppercase;letter-spacing:0.05em;margin-top:3px;font-weight:600;}
.hero.good{background:#0d2818;border-color:#1a4d2e;}.hero.good .v{color:#56d364;}
/* quiet spec line + status */
.specline{color:#8b949e;font-size:13px;line-height:1.7;}
.specline b{color:#e6edf3;font-weight:600;}
.tag{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:10px;margin-right:6px;background:#1e2c44;color:#79c0ff;}
.status{font-size:13px;font-weight:600;margin-top:7px;}
.status.good{color:#56d364;}.status.warn{color:#ffa657;}
/* ② the pitch panel */
.pitch{background:#0d2818;border:1px solid #1a4d2e;border-radius:10px;padding:13px 14px;margin-top:4px;}
.pitch .cf{font-size:23px;font-weight:800;color:#56d364;line-height:1;}.pitch .cf small{font-size:13px;}
.pitch .sub{color:#e6edf3;font-size:14px;margin-top:6px;}.pitch .sub .k{color:#8b949e;}
.pitch .terms{color:#8b949e;font-size:13px;margin-top:7px;}
.fee{color:#8b949e;font-size:13px;margin-top:9px;}.fee b{color:#e3b341;}
.pill{background:#1c2128;border:1px solid #30363d;border-radius:12px;padding:3px 10px;font-size:12px;color:#8b949e;}
.btn-row{display:flex;flex-wrap:wrap;gap:7px;margin-top:4px;}
.btn-row-actions{margin-top:8px;}
/* unified button system — neutral by default; color only for primary (go) + danger (stop) */
.btn,a.btn,button.btn,a.zillow,button.zillow{display:inline-flex;align-items:center;gap:5px;padding:7px 12px;background:#1c2128;border:1px solid #30363d;border-radius:8px;font-size:12.5px;font-weight:600;color:#e6edf3;text-decoration:none;cursor:pointer;font-family:inherit;line-height:1.2;min-height:34px;}
.btn:active,a.zillow:active{opacity:0.7;}
.btn:hover,a.zillow:hover{border-color:#8b949e;}
.btn-script{}
.btn.primary{background:#1a4d2e;border-color:#1a4d2e;color:#d6ffe0;}
.btn.danger{background:transparent;border-color:#5c2626;color:#f85149;}
.play-link{display:inline-flex;align-items:center;padding:9px 16px;background:#58a6ff;color:#0d1117;border-radius:8px;font-size:13px;font-weight:600;text-decoration:none;margin-top:4px;min-height:36px;}
.tier-A{border-left:3px solid #ff7b72;}.tier-B{border-left:3px solid #d2a8ff;}.tier-HY{border-left:3px solid #c971ff;}.tier-MT{border-left:3px solid #79c0ff;}.tier-FF{border-left:3px solid #f0883e;}.tier-C{border-left:3px solid #56d364;}
.rejected{color:#8b949e;font-size:13px;padding:4px 0;}
.date{color:#8b949e;font-size:13px;}
.addr-copy{display:inline-block;margin-left:8px;padding:2px 9px;font-size:12px;background:#1c2128;border:1px solid #30363d;color:#58a6ff;border-radius:12px;cursor:pointer;font-family:inherit;}
.addr-copy:hover{background:#21262d;}
.addr-copy.copied{background:#1a4d2e;color:#56d364;border-color:#1a4d2e;}
.deal .photos{display:flex;overflow-x:auto;gap:6px;margin:6px 0 8px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;padding-bottom:4px;}
.deal .photos img{height:110px;min-width:150px;max-width:150px;object-fit:cover;border-radius:6px;scroll-snap-align:start;background:#0d1117;}
.deal .photos a{flex:0 0 auto;line-height:0;}
@media (min-width:720px){.deal{padding:16px;}.deal .photos img{height:130px;min-width:180px;max-width:180px;}}
'''.replace('\n','').strip()
PROXY_JS = ''
if BBC_PROXY_URL and BBC_PROXY_SECRET:
    PROXY_JS = '''<script>
const BBC_PROXY_URL = ''' + json.dumps(BBC_PROXY_URL) + ''';
const BBC_PROXY_SECRET = ''' + json.dumps(BBC_PROXY_SECRET) + ''';
async function hmacHex(message, secret) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret),
    {name:'HMAC', hash:'SHA-256'}, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2,'0')).join('');
}
async function bbcSavePipeline(btn, payloadJson) {
  const body = JSON.stringify(JSON.parse(payloadJson));
  btn.disabled = true;
  const origText = btn.textContent;
  btn.textContent = '⏳ Sending…';
  try {
    const sig = await hmacHex(body, BBC_PROXY_SECRET);
    const resp = await fetch(BBC_PROXY_URL + '/pipeline', {
      method: 'POST', body, headers: {'Content-Type':'application/json', 'X-Signature':sig}
    });
    const result = await resp.json();
    if (resp.ok && (result.status === 201 || result.status === 200)) {
      btn.style.background = '#1a4d2e'; btn.style.color = '#56d364';
      btn.textContent = '✓ Saved to BBC Pipeline';
    } else {
      btn.style.background = '#3a1e1e'; btn.style.color = '#ff7b72';
      btn.textContent = '✗ Failed (' + (result.status || resp.status) + ')';
    }
  } catch (e) {
    btn.style.background = '#3a1e1e'; btn.style.color = '#ff7b72';
    btn.textContent = '✗ Error: ' + e.message.slice(0, 40);
  }
}

/* Click-to-call via OpenPhone:
 *   1. POST contact-create payload to Worker /openphone-call (with HMAC).
 *      Worker calls OpenPhone API to upsert contact with property in `company`.
 *      Idempotent via externalId (BBC PID).
 *   2. Regardless of contact-create success/failure, fire openphone://call URL
 *      to initiate the actual call. Contact-create is best-effort; the call
 *      always proceeds so a Worker outage / missing API key doesn't block dialing.
 *   3. Brief visual confirmation on the button: ⏳ → ✓ Contact + dialing.
 */
async function rtOpenPhoneCall(btn, payloadJson, phone) {
  const body = JSON.stringify(JSON.parse(payloadJson));
  const origText = btn.textContent;
  btn.textContent = '⏳ Saving contact…';
  // Use tel: URL — Quo (formerly OpenPhone) registers tel: scheme and accepts
  // numbers via this standard format. The openphone://call?number= format
  // launches Quo but Quo's renderer doesn't parse the query param (verified
  // 2026-05-18 with Tim). tel: works on iPhone too (iOS routes to Quo if
  // installed, otherwise iOS phone picker).
  const dialUrl = 'tel:' + phone;
  // Fire-and-forget the contact create; don't block the dial on its outcome.
  // Use a 2-second timeout so user isn't stuck waiting if Worker is slow.
  try {
    const sig = await hmacHex(body, BBC_PROXY_SECRET);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);
    fetch(BBC_PROXY_URL + '/openphone-call', {
      method: 'POST', body,
      headers: {'Content-Type':'application/json', 'X-Signature':sig},
      signal: controller.signal,
    }).then(r => r.json()).then(result => {
      clearTimeout(timeoutId);
      if (result && result.ok) {
        btn.style.background = '#1a4d2e'; btn.style.color = '#56d364';
        btn.textContent = '✓ Contact saved · dialing';
      } else if (result && result.skipped) {
        btn.textContent = '☏ Dialing (OpenPhone API not configured)';
      } else {
        btn.textContent = '☏ Dialing (contact-save: ' + (result.status || '?') + ')';
      }
    }).catch(() => { btn.textContent = '☏ Dialing'; });
  } catch (e) {
    btn.textContent = '☏ Dialing';
  }
  // Fire the call URL via an anchor click — this is treated as user-gesture
  // navigation by macOS Chrome/Safari and reliably triggers the OpenPhone Mac
  // app. `window.location.href = ...` for custom protocols is silently dropped
  // on desktop browsers in many cases.
  const a = document.createElement('a');
  a.href = dialUrl;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => a.remove(), 100);
  // Reset the button text after 4 seconds so it can be tapped again
  setTimeout(() => { btn.textContent = origText; btn.style.background = ''; btn.style.color = ''; }, 4000);
}
</script>'''

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
html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Triage {date_iso}</title><style>{CSS}</style></head><body><p class="date">📋 {date_human} · TN/TX/GA/OH/MI &nbsp;·&nbsp; <a href="https://www.buyboxcartel.com/vip/lightning-leads" target="_blank" style="color:#58a6ff;">Open BBC Lightning Leads ↗</a></p><div class="summary">{summary}</div>{call_sheet}{group_sf}{group_mt}{group_cash}{rej_section}' + PROXY_JS + CLOCK_JS + '</body></html>'

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
