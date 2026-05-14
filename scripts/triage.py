import urllib.request, urllib.error, urllib.parse, http.cookiejar, json, base64, sys, re
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
# can't (PerimeterX blocks). Cost: Haiku 4.5 at ~$0.005/property × ~100 quals/day
# = ~$0.50/day. Only runs on qualified properties (post-tier, post-agent-unlock).
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
VISION_MODEL = 'claude-haiku-4-5-20251001'
VISION_PROMPT = '''You are evaluating a residential listing for a creative-finance wholesaler (Richard Taylor's HMHW method). The method works on STANDARD residential listings with individual sellers — NOT REO/auction/bank-owned, not heavily distressed properties needing gut rehab, not commercial buildings.

Given these property photos, return ONLY a single JSON object with these fields:
- condition (int 1-5): 5=move-in ready, 4=light cosmetic only, 3=cosmetic renovation, 2=significant rehab (kitchen/bath/floors), 1=heavy gut / structural / water damage
- reo_or_auction (bool): visible REO sign, auction sign, bank-owned marketing, lockbox-only, completely empty/staged-for-auction look
- commercial_or_unusual (bool): commercial use, warehouse/industrial, vacant lot photos labelled as a house, mobile home on leased lot
- recommended_action (string): "qualify" | "demote_to_ff" | "reject"
  - "qualify" = clean residential, Richard's method applies
  - "demote_to_ff" = condition is 2-3, route to Fix & Flip instead of Seller Finance
  - "reject" = condition 1 OR reo_or_auction OR commercial_or_unusual
- notes (string, max 100 chars): brief reasoning visible to operator

Output ONLY the JSON. No prose, no markdown fences.'''

vision_cache = {}  # PID → analysis dict
vision_calls = 0
vision_skipped = 0

def analyze_property_vision(p):
    """Send up to 2 BBC photos to Claude vision; return analysis dict or None on
    failure. Caches per-PID for the run. Skips if ANTHROPIC_API_KEY missing or
    no images on the listing."""
    global vision_calls
    pid = p.get('pid')
    if not pid or not ANTHROPIC_API_KEY: return None
    if pid in vision_cache: return vision_cache[pid]
    images = p.get('images') or []
    if not images: return None
    # Use top 2 photos — usually exterior + interior — enough for condition + REO assessment
    photo_urls = [img if isinstance(img, str) else img.get('url') for img in images[:2]]
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
    entry = down + 3000 + 5000
    coc = round((cf*12)/entry*100, 1) if entry > 0 else 0
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
        # Tier A: asking + 10%, 10% down, 0%, 30yr, 5-7yr balloon
        creative_cf, creative_offer, creative_down = _sf_cf(1.10, 0.10, 5)
        creative_terms = f"${creative_offer:,} @ 0%, 10% down (${creative_down:,}), 30yr / 5yr balloon"
    elif dt == 'sellerFinance':
        # Tier B: asking + 20%, 12% down, 0%, 30yr, 7yr balloon
        creative_cf, creative_offer, creative_down = _sf_cf(1.20, 0.12, 7)
        creative_terms = f"${creative_offer:,} @ 0%, 12% down (${creative_down:,}), 30yr / 7yr balloon"
    elif dt == 'mortgageTakeover':
        # MT: take over existing loan at existing terms. BBC's monthlyCashFlow
        # already uses the existing loan's payment, which IS the right number.
        creative_cf = round(cf)
        creative_offer = round(lp)
        creative_down = 10000
        creative_terms = f"Take over existing loan, ~${creative_down:,} to seller"
    elif dt == 'fixAndFlip':
        # Cash Course 70% rule. F&F is a flip play — monthly CF is not the metric.
        # We surface the offer math; rental CF is a sanity check from BBC's cf.
        creative_offer = round(lp * 0.70)
        creative_down = 0
        creative_cf = round(cf)  # BBC's rental CF (post-flip-and-rent scenario)
        creative_terms = f"Cash offer ${creative_offer:,} (70% of list — Cash Course rule)"
    else:
        # Cash arb (Tier C): BBC's CF at cash-purchased terms is correct
        creative_offer = round(op or lp)
        creative_down = round(down)
        creative_cf = round(cf)
        creative_terms = "Cash offer / standard"

    # BANK GAP — what a standard 7% bank mortgage would look like vs the creative
    # scenario above. Reuses the same rent + tax + ins + reserve numbers.
    bank_gap = 0
    if monthly_rent > 0 and lp > 0:
        bank_loan = lp * 0.75
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
            'entry_fee': round(entry), 'entry_pct': round(entry/op*100,1) if op>0 else 0,
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
            'creative_terms': creative_terms,
            'beds': int(p.get('bed') or 0),
            'baths': int(float(p.get('bath') or 0)),
            'sqft': int(p.get('sqft') or 0),
            'lat': addr.get('latitude') or '',
            'lng': addr.get('longitude') or '',
            'year_built': int(cd.get('yearBuilt')) if (cd.get('yearBuilt') and str(cd.get('yearBuilt')).isdigit()) else 0,
            'foundation': (cd.get('foundation') or '').strip(),
            'image_count': len(p.get('images') or []),
            'images': [(img if isinstance(img, str) else img.get('url') or '') for img in (p.get('images') or [])[:8] if img],
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
        flags.append('⚠️ Stale + cheap + null cash flow — possibly REO/auction; verify listing status')

    return flags

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
    # 'apartment' = single unit (caught earlier as non-residential); 'multi' = MFH building.
    is_mfh = is_mfh_5plus or is_mfh_24 or 'multi' in pt
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
NON_RESIDENTIAL_TYPES = ('vacant', 'land', 'lot', 'acreage', 'commercial', 'industrial',
                         'condo', 'apartment',       # 'apartment' = single condo-style unit
                         'manufactured', 'mobile')   # manufactured/mobile homes — often on leased
                                                     # land (no real estate to underwrite), depreciate,
                                                     # not lendable conventionally. Per Tim's 7717
                                                     # Arbor Ridge Ct example 2026-05-14.
buckets = {'A':[], 'B':[], 'MT':[], 'FF':[], 'C':[], 'REJECT':[]}
land_skipped = 0
tracked_skipped = 0
new_construction_skipped = 0
this_year = date.today().year  # date imported at module top from datetime
for p in all_leads:
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
    if any(token in pt_lower for token in NON_RESIDENTIAL_TYPES):
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
    t = tier(s)
    s['buyer_matches'] = match_buyers(s, t, buyers) if t != 'REJECT' else []
    s['tz'] = STATE_TZ.get(s['state'], 'America/New_York')
    s['agent'] = None  # set below if unlocked
    buckets[t].append(s)
for t in ('A','B','MT','C'): buckets[t].sort(key=lambda x: (-x['creative_cf'], -x['dom']))
# Fix & Flip: sort by DOM desc (motivation) since CF isn't the relevant metric
buckets['FF'].sort(key=lambda x: -x['dom'])
print(f'\nA={len(buckets["A"])}  B={len(buckets["B"])}  MT={len(buckets["MT"])}  FF={len(buckets["FF"])}  C={len(buckets["C"])}  REJECT={len(buckets["REJECT"])}  Land-skipped={land_skipped}  NewConstruction-skipped={new_construction_skipped}  Tracked-skipped={tracked_skipped}', file=sys.stderr)

# 5b. Surface agent info — cookie-free via BBC's contact-seller endpoint (the one
# behind the Create Offer modal). Cost: $0/unlock. Run on ALL Tier A/B/C deals.
# ALSO: detect REO/auction/foreclosure based on agent name keywords — these
# 'agents' are corporate asset managers (Auction.com, Williams & Williams, etc.),
# NOT individual realtors. Properties they list are bank-owned auctions, which
# Richard's method doesn't address. We REJECT them post-unlock.
AUCTION_AGENT_KEYWORDS = ('auction', 'reo', 'foreclosure', 'bank ', 'asset management',
                          'williams &', 'altisource', 'bidsale', 'hubzu', 'xome',
                          'realty trust', 'asset disposition', 'servicelink')
unlock_targets = buckets['A'] + buckets['B'] + buckets['MT'] + buckets['FF'] + buckets['C']
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
for t in ('A','B','MT','FF','C'):
    buckets[t] = [s for s in buckets[t] if not s.get('_auction_reject')]

# 5b. Vision analysis — Claude looks at BBC's photos and flags REO/condition/distress
# that the data fields don't expose. Closes the detection gap.
vision_rejected = 0
vision_demoted = 0
if ANTHROPIC_API_KEY:
    print(f'\nClaude vision analysis on qualified properties...', file=sys.stderr)
    # Build a lookup: PID → original BBC property dict (for photo URLs)
    p_by_pid = {p.get('pid'): p for p in all_leads if p.get('pid')}
    for tier_name in ('A','B','MT','FF','C'):
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
            elif action == 'demote_to_ff' and tier_name != 'FF':
                vision_demoted += 1
                buckets[tier_name].remove(s)
                # Reroute to FF — change deal_type label and creative_terms
                s['deal_type_raw'] = 'fixAndFlip'
                s['creative_offer'] = round(s['price'] * 0.70) if s.get('price') else 0
                s['creative_down'] = 0
                s['creative_terms'] = f"Cash offer ${s['creative_offer']:,} (vision-demoted — condition {analysis.get('condition','?')}/5)"
                buckets['FF'].append(s)
                print(f"  → {s['address'][:50]}: VISION-DEMOTED {tier_name}→FF (condition {analysis.get('condition','?')}/5): {analysis.get('notes','')[:60]}", file=sys.stderr)
    print(f'Vision: {vision_calls} API calls (~${vision_calls * 0.005:.2f}) · {vision_rejected} rejected · {vision_demoted} demoted to FF', file=sys.stderr)
else:
    print(f'\nClaude vision SKIPPED — ANTHROPIC_API_KEY not set. To enable: export ANTHROPIC_API_KEY=sk-...', file=sys.stderr)

# Re-sort buckets after vision-driven moves
for t in ('A','B','MT','C'): buckets[t].sort(key=lambda x: (-x.get('creative_cf',0), -x.get('dom',0)))
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
        bbc_property_link = f' <a class="zillow" href="https://www.buyboxcartel.com/vip/property/{d["zpid"]}" target="_blank" style="background:#1a4d2e;color:#56d364;padding:3px 8px;border-radius:6px;font-weight:600;border:1px solid #1a4d2e;">🏦 Create Offer in BBC ↗</a>'
    # Grand In Taylor JV submission — Richard Taylor's own wholesale company. Phase-1
    # dispo channel: instead of self-listing on BBC Marketplace, Tim submits the deal
    # here, Richard's team places it with their buyer network, JV split applies. Two
    # forms by deal type: Creative Finance for A/B/MT/SF, Cash Alternative for FF/C.
    # No URL prefill wired yet (Salesmate's hash-route params not verified) — opens
    # clean form, Tim pastes address from triage. Later: add ?prefill[Field]=val once
    # we capture Salesmate's accepted param format from one real submission.
    gt_url = {
        'A':  'https://grandintaylorllc.salesmate.io/webforms/#/5bddb679-43e9-4a91-aca2-ddaff898ff78',
        'B':  'https://grandintaylorllc.salesmate.io/webforms/#/5bddb679-43e9-4a91-aca2-ddaff898ff78',
        'MT': 'https://grandintaylorllc.salesmate.io/webforms/#/5bddb679-43e9-4a91-aca2-ddaff898ff78',
        'FF': 'https://grandintaylorllc.salesmate.io/webforms/#/696ce9d7-457b-44ad-8e6f-a9574197e587',
        'C':  'https://grandintaylorllc.salesmate.io/webforms/#/696ce9d7-457b-44ad-8e6f-a9574197e587',
    }.get(t, '')
    gt_label = 'Creative' if t in ('A','B','MT') else 'Cash'
    gt_link = f' <a class="zillow" href="{gt_url}" target="_blank" style="background:#2a1a44;color:#d2a8ff;padding:3px 8px;border-radius:6px;font-weight:600;border:1px solid #2a1a44;">🤝 Submit to Grand In Taylor ({gt_label}) ↗</a>' if gt_url else ''
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
        'MT': [('Mortgage Takeover', '/tools/mortgage-takeover'), ('Offer Oven', '/tools/offer-oven')],
        'FF': [('Fix & Flip', '/tools/fix-and-flip'), ('Rehab Estimator', '/tools/rehab-estimator')],
        'C':  [('Cash Deal Checker', '/tools/cash-deal-checker')],
    }.get(t, [])
    calc_links_html = ''.join(
        f' <a class="zillow" href="https://www.hmhw.group{path}" target="_blank">🧮 {name} ↗</a>'
        for name, path in hmhw_calcs
    )
    # Clipboard payload — plain-text values, one per line, ready for Tab-key paste.
    # Order matches the Offer Oven field sequence (Purchase Price, Down Payment, Rate,
    # Term, Loan Balance for sub-to, Rental Revenue, Assignment, Closing).
    if t in ('A', 'B', 'MT'):
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
        copy_btn = f' <button class="zillow" type="button" onclick="{copy_handler}" style="background:#1c2128;color:#58a6ff;padding:3px 8px;border-radius:6px;font-weight:600;border:1px solid #30363d;cursor:pointer;font-family:inherit;font-size:12px;">📋 Copy values</button>'
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
    # Sold comps — Zillow ZIP-scoped with tight filters: beds=exact, sqft band ±20%,
    # property type matched. Prior version returned ~2000 results because only ZIP was
    # filtering. We use Zillow's searchQueryState JSON-encoded URL parameter so all
    # filters apply at once (Zillow's slug syntax /3-_beds/ alone is unreliable).
    zip_code = d.get('zip', '')
    beds = d.get('beds', 0)
    sqft_val = d.get('sqft', 0)
    if zip_code:
        # Build searchQueryState — Zillow's canonical filter mechanism on web URLs
        sqs = {
            'pagination': {},
            'filterState': {
                'sortSelection': {'value': 'globalrelevanceex'},
                'isRecentlySold': {'value': True},
                'isAllHomes': {'value': True},
                'isForSaleByAgent': {'value': False},
                'isForSaleByOwner': {'value': False},
                'isNewConstruction': {'value': False},
                'isComingSoon': {'value': False},
                'isAuction': {'value': False},
                'isForSaleForeclosure': {'value': False},
                'doz': {'value': '180'},  # sold within 180 days
            },
            'isListVisible': True,
        }
        if beds:
            sqs['filterState']['beds'] = {'min': max(1, beds - 1), 'max': beds + 1}
        if sqft_val and sqft_val > 200:
            sqs['filterState']['sqft'] = {'min': int(sqft_val * 0.80), 'max': int(sqft_val * 1.20)}
        sqs_q = urllib.parse.quote(json.dumps(sqs, separators=(',', ':')))
        sold_url = f'https://www.zillow.com/{zip_code}/sold/?searchQueryState={sqs_q}'
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
        tel_link = f'<a href="tel:{phone_clean}" style="color:#79c0ff;">📞 {a["phone"]}</a>' if phone_clean else f'<span>📞 {a["phone"]}</span>'
        op_link = f' &nbsp; <a href="openphone://call?number={phone_clean}" style="color:#79c0ff;">via OpenPhone</a>' if phone_clean else ''
        email_link = f' &nbsp; <a href="mailto:{a["email"]}" style="color:#8b949e;">✉ {a["email"]}</a>' if a.get('email') and a['email'] != 'Not Available' else ''
        agent_block = f'<div style="margin-top:8px;padding:8px 10px;background:#161b22;border:1px solid #30363d;border-radius:6px;font-size:13px;"><div style="color:#e6edf3;font-weight:600;margin-bottom:2px;">🔓 {a["name"]}</div><div>{tel_link}{op_link}{email_link}</div></div>'
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
    buyer_pill = ''
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
                buyer_pill = f' <span class="pill" style="background:#0d2818;color:#56d364;border-color:#1a4d2e;font-weight:600;" title="BBC BuyBoxes: this state is currently active for this strategy">🎯 {bucket_label}{s8_bonus} active</span>'
            elif is_active is False:
                buyer_pill = f' <span class="pill" style="background:#3a2418;color:#ffa657;border-color:#3a2418;" title="BBC BuyBoxes: low buyer activity for this strategy in this state — dispo will be harder">⚠️ Low {bucket_label.lower().replace("&amp;","&")} activity</span>'
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
    track_link = f' <a class="zillow" href="{track_url}" target="_blank" style="background:#1e2c44;color:#79c0ff;padding:3px 8px;border-radius:6px;font-weight:600;border:1px solid #1e2c44;">+ Track Property</a>'
    # REJECT button — opens 'Rejected by Tim' Airtable with prefilled context. Each
    # rejection feeds the weekly optimization agent which proposes new filter rules
    # so this category of mistake doesn't repeat. Permanent dedupe by PID.
    reject_params = {
        'prefill_Address': d['address'],
        'prefill_PID': d.get('pid',''),
        'prefill_Tier (was)': tier_label,
        'prefill_List Price': str(int(d['price'])) if d.get('price') else '',
        'prefill_City': city_at,
        'prefill_State': state_at,
        'prefill_Zillow URL': d.get('zillow','') or '',
        'prefill_Agent Name (at reject)': agent_name_at,
        'prefill_Rejected Date': date_iso,
    }
    reject_qs = '&'.join(f'{urllib.parse.quote(k)}={urllib.parse.quote(v)}' for k,v in reject_params.items() if v)
    reject_url = f'https://airtable.com/{AT_BASE}/{RJ_TABLE}?{reject_qs}'
    reject_link = f' <a class="zillow" href="{reject_url}" target="_blank" style="background:#3a1e1e;color:#ff7b72;padding:3px 8px;border-radius:6px;font-weight:600;border:1px solid #3a1e1e;" title="Permanently reject from future triage + feed the optimization agent">✗ Reject</a>'

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
                'balloon': 96,
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
        pipeline_btn = f' <button class="zillow" type="button" onclick="bbcSavePipeline(this, this.dataset.payload)" data-payload="{pipeline_json_attr}" style="background:#1a4d2e;color:#56d364;padding:3px 8px;border-radius:6px;font-weight:600;border:1px solid #1a4d2e;cursor:pointer;font-family:inherit;font-size:12px;">🔑 Save to BBC Pipeline</button>'
    return f'<div class="deal {cls}"><div class="addr">{d["address"]}{pipe}{status_pill if d.get("status_state") != "active" else ""}</div><div class="meta">{d["units"]} units · {d["type"]}</div>{photo_strip}{creative_banner}<div class="nums">{status_pill if d.get("status_state") == "active" else ""}{dt_pill}{pt_pill}<span class="pill">${d["price"]:,.0f}</span><span class="pill">{cf_label} ${d["cf"]:,.0f}/mo</span>{bank_gap_pill}<span class="pill">CoC {d["coc"]}%</span><span class="pill">DOM {d["dom"]} {d["dom_flag"]}</span>{buyer_pill}{tz_pill}</div><a class="play-link" href="{playbook}">Open Tier {t} playbook →</a>{risk_banner}{vision_banner}{track_link}{reject_link}{bbc_property_link}{gt_link}{pipeline_btn}{z}{bbc_link}{bbc_mobile_link}{oven_link}{rent_link}{sold_link}{bl}{agent_block}</div>'

section_a = ('<h2>🎯 TIER A — Multifamily Seller Finance ($200K-$1.4M, 2+ units, DOM 90+; 2-4 units only if NOT retail-desirable)</h2>' + ''.join(render_deal(d,'A') for d in buckets['A'])) if buckets['A'] else ''
section_b = ('<h2>🏘️ TIER B — Cheap SFH Stale Seller Finance (&lt;$150K, SFH, DOM 90+)</h2>' + ''.join(render_deal(d,'B') for d in buckets['B'])) if buckets['B'] else ''
section_mt = ('<h2>🔑 MORTGAGE TAKEOVER — Favorable existing loan (positive CF at assumed rate, DOM 60+)</h2>' + ''.join(render_deal(d,'MT') for d in buckets['MT'])) if buckets['MT'] else ''
section_ff = ('<h2>🔨 FIX &amp; FLIP — Cheap distressed cash plays (Cash Course 70% rule, &lt;$250K, DOM 60+)</h2>' + ''.join(render_deal(d,'FF') for d in buckets['FF'])) if buckets['FF'] else ''
section_c = ('<h2>💵 TIER C — Cash-Comparable SFH (cash arbitrage, NOT seller finance)</h2>' + ''.join(render_deal(d,'C') for d in buckets['C'])) if buckets['C'] else ''
rej_section = ''
if buckets['REJECT']:
    rej_lines = ''.join(f'<div class="rejected">{s["address"]} — CF: ${s["cf"]:,.0f} (DOM {s["dom"]})</div>' for s in buckets['REJECT'][:15])
    rej_section = f'<h2>❌ REJECTED — {pushed} pushed to <a href="https://airtable.com/{AT_BASE}/{WL_TABLE}">Watchlist</a></h2>{rej_lines}'

agent_indicator = f' · 🔓 {unlocks_succeeded} agents captured (free)' if unlocks_succeeded else ''
summary = f'{len(all_leads)} leads · {len(buckets["A"])} Tier A · {len(buckets["B"])} Tier B · {len(buckets["MT"])} MT · {len(buckets["FF"])} FF · {len(buckets["C"])} Tier C · {pushed} → watchlist{agent_indicator}'
CSS = 'body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:12px;font-size:15px;line-height:1.5;}h2{font-size:14px;color:#8b949e;text-transform:uppercase;letter-spacing:0.04em;margin:18px 0 8px;}.summary{background:#1c2128;border:1px solid #30363d;border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:14px;}.deal{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:10px;}.deal .addr{font-weight:600;font-size:15px;margin-bottom:4px;}.deal .meta{font-size:13px;color:#8b949e;margin-bottom:6px;}.deal .nums{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;}.pill{background:#1c2128;border:1px solid #30363d;border-radius:12px;padding:2px 9px;font-size:12px;color:#8b949e;}.play-link{display:inline-block;padding:8px 12px;background:#58a6ff;color:#0d1117;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;margin-top:4px;}.tier-A{border-left:3px solid #ff7b72;}.tier-B{border-left:3px solid #d2a8ff;}.tier-MT{border-left:3px solid #79c0ff;}.tier-FF{border-left:3px solid #f0883e;}.tier-C{border-left:3px solid #56d364;}a.zillow{color:#58a6ff;font-size:12px;margin-left:8px;}.rejected{color:#8b949e;font-size:13px;padding:4px 0;}.date{color:#8b949e;font-size:13px;}.addr-copy{display:inline-block;margin-left:8px;padding:2px 9px;font-size:12px;background:#1c2128;border:1px solid #30363d;color:#58a6ff;border-radius:12px;cursor:pointer;font-family:inherit;}.addr-copy:hover{background:#21262d;}.addr-copy.copied{background:#1a4d2e;color:#56d364;border-color:#1a4d2e;}.deal .photos{display:flex;overflow-x:auto;gap:6px;margin:6px 0 8px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;padding-bottom:4px;}.deal .photos img{height:110px;min-width:150px;max-width:150px;object-fit:cover;border-radius:6px;scroll-snap-align:start;background:#0d1117;}.deal .photos a{flex:0 0 auto;line-height:0;}'
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
html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Triage {date_iso}</title><style>{CSS}</style></head><body><p class="date">📋 {date_human} · TN/TX/GA/OH/MI &nbsp;·&nbsp; <a href="https://www.buyboxcartel.com/vip/lightning-leads" target="_blank" style="color:#58a6ff;">Open BBC Lightning Leads ↗</a></p><div class="summary">{summary}</div>{section_a}{section_b}{section_mt}{section_ff}{section_c}{rej_section}' + PROXY_JS + CLOCK_JS + '</body></html>'

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
