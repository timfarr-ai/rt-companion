/**
 * rt-companion BBC Proxy Worker
 *
 * Proxies privileged calls from the rt-companion briefing dashboard to:
 *  - BBC's /api/lightning-leads/pipeline/add endpoint (Save to Pipeline)
 *  - OpenPhone's /v1/contacts endpoint (Create-contact-on-call)
 *
 * Solves the iPhone problem: the BBC autosearch userscript doesn't run on iOS
 * Safari. This Worker handles the auth + HTTP plumbing server-side; the
 * briefing card just POSTs a signed payload.
 *
 * Endpoints:
 *   GET  /                health check
 *   POST /pipeline        save property to BBC Pipeline
 *   POST /openphone-call  create-or-update OpenPhone contact with property as
 *                          company field, then return so browser can fire
 *                          openphone://call?number=... URL scheme
 *
 * Security: requests must include an HMAC-SHA256 signature in `X-Signature`
 * computed from the body using the shared secret. The same secret is baked into
 * the briefing JS at render time. Prevents random attackers from spamming BBC
 * with this URL.
 *
 * BBC auth: full login flow done lazily, session cookie cached in KV with 30min
 * TTL. First request per ~30min pays ~700ms; subsequent are ~300ms.
 *
 * Deploy:
 *   wrangler kv:namespace create BBC_SESSION
 *   (update wrangler.jsonc with returned id)
 *   wrangler secret put BBC_EMAIL
 *   wrangler secret put BBC_PASS
 *   wrangler secret put SHARED_SECRET
 *   wrangler secret put OPENPHONE_API_KEY  ← optional, only for /openphone-call
 *   wrangler deploy
 */

const BBC = 'https://www.buyboxcartel.com';
const BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

async function hmacVerify(body, signature, secretStr) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secretStr),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']
  );
  const sigBytes = new Uint8Array(signature.match(/.{2}/g).map(b => parseInt(b, 16)));
  return crypto.subtle.verify('HMAC', key, sigBytes, encoder.encode(body));
}

async function loginBBC(env) {
  // Try cached session first
  const cached = await env.BBC_SESSION.get('session', { type: 'json' });
  if (cached && cached.expiresAt > Date.now()) return cached;

  // Fresh login
  const resp = await fetch(`${BBC}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'User-Agent': BROWSER_UA },
    body: JSON.stringify({ email: env.BBC_EMAIL, password: env.BBC_PASS })
  });
  if (!resp.ok) {
    const errBody = await resp.text();
    throw new Error(`BBC login failed: ${resp.status} ${errBody.slice(0,120)}`);
  }
  const data = await resp.json();
  const token = data.accessToken || data.token || (data.user && data.user.token);
  const cookies = resp.headers.get('set-cookie') || '';
  const session = {
    token,
    cookieHeader: cookies.split(',').map(c => c.split(';')[0]).join('; '),
    expiresAt: Date.now() + 25 * 60 * 1000  // 25min TTL
  };
  await env.BBC_SESSION.put('session', JSON.stringify(session), { expirationTtl: 1800 });
  return session;
}

async function saveToPipeline(env, pipelineData) {
  const session = await loginBBC(env);
  const resp = await fetch(`${BBC}/api/lightning-leads/pipeline/add`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': BROWSER_UA,
      'Authorization': `Bearer ${session.token}`,
      'Cookie': session.cookieHeader,
      'Accept': 'application/json'
    },
    body: JSON.stringify({ pipelineData })
  });
  return { status: resp.status, body: await resp.text() };
}

/**
 * Look up the OpenPhone custom-field keys we care about, cached in KV for 1 hour.
 * The API only exposes GET (no POST) for custom-fields — Tim defines them in
 * the OpenPhone UI, then this code discovers them by name and uses their keys.
 *
 * Fields we look for (by name, case-insensitive):
 *   "Property Address"  (preferred type: address)
 *   "Tier"              (string or multi-select)
 *   "DOM"               (number) — matches "DOM", "DOM at Lead", "DOM at first contact"
 *   "BBC PID"           (string)
 *   "First Seen"        (date) — matches "First Seen", "First Seen Date"
 *
 * Returns { propertyAddress?: key, tier?: key, dom?: key, pid?: key, firstSeen?: key }
 * Any field Tim hasn't created yet is simply absent — the contact-create code
 * falls back gracefully (puts unfilled context into `company`).
 */
async function getOpenPhoneCustomFieldKeys(env) {
  // KV cache: 1 hour TTL
  const cached = await env.BBC_SESSION.get('op_custom_fields', { type: 'json' });
  if (cached && cached.expiresAt > Date.now()) return cached.keys;
  const resp = await fetch('https://api.openphone.com/v1/contact-custom-fields', {
    headers: { 'Authorization': env.OPENPHONE_API_KEY },
  });
  if (!resp.ok) return {};
  const data = await resp.json();
  const fields = data.data || [];
  const keys = {};
  for (const f of fields) {
    const n = (f.name || '').toLowerCase();
    // Property-address matching: accept Tim's actual field name "Listed Properties"
    // plus other reasonable variants. Verified 2026-05-18: Tim's field is
    // "Listed Properties" type=address key=6a0a9a23c3b59be3b9b27d3c.
    if (n === 'property address' || n === 'listed properties' || n === 'listed property' ||
        n === 'address' || n === 'properties')
      keys.propertyAddress = f.key;
    else if (n === 'tier' || n === 'rt tier') keys.tier = f.key;
    else if (n === 'dom' || n.startsWith('dom ')) keys.dom = f.key;
    else if (n === 'bbc pid' || n === 'pid') keys.pid = f.key;
    else if (n === 'first seen' || n.startsWith('first seen')) keys.firstSeen = f.key;
  }
  await env.BBC_SESSION.put('op_custom_fields',
    JSON.stringify({ keys, expiresAt: Date.now() + 60*60*1000 }),
    { expirationTtl: 3700 });
  return keys;
}

/**
 * Create-or-update an OpenPhone contact for a property-call workflow.
 *
 * Two-tier filling strategy:
 *  1. If Tim has defined custom fields in OpenPhone (Property Address, Tier,
 *     DOM, BBC PID, First Seen) — we fill them properly via customFields[].
 *     This is the clean view.
 *  2. As a SAFETY NET, we ALSO stuff a compact summary into `company` so the
 *     property context is visible even before custom fields are defined.
 *     Format: "RT · 123 Main St · Tier B · DOM 156"
 *
 * Uses externalId (BBC PID) for cross-system de-dup. Re-clicks update the
 * contact rather than duplicate.
 *
 * @param {Object} env  Worker env (needs OPENPHONE_API_KEY)
 * @param {Object} payload  { phone, name, email, address, tier, dom, pid, briefing_url }
 */
async function createOpenPhoneContact(env, payload) {
  if (!env.OPENPHONE_API_KEY) {
    return { status: 0, skipped: 'OPENPHONE_API_KEY not configured' };
  }
  const nameParts = (payload.name || 'Unknown Agent').trim().split(/\s+/);
  const firstName = nameParts[0] || 'Unknown';
  const lastName = nameParts.slice(1).join(' ') || '';
  // Look up custom-field keys by name (Tim defines them in OpenPhone UI;
  // this discovers them and starts filling automatically once they exist).
  const fieldKeys = await getOpenPhoneCustomFieldKeys(env);
  const customFields = [];
  if (fieldKeys.propertyAddress && payload.address)
    customFields.push({ key: fieldKeys.propertyAddress, value: payload.address });
  if (fieldKeys.tier && payload.tier)
    customFields.push({ key: fieldKeys.tier, value: payload.tier });
  if (fieldKeys.dom && payload.dom)
    customFields.push({ key: fieldKeys.dom, value: Number(payload.dom) });
  if (fieldKeys.pid && payload.pid)
    customFields.push({ key: fieldKeys.pid, value: payload.pid });
  if (fieldKeys.firstSeen)
    customFields.push({ key: fieldKeys.firstSeen, value: new Date().toISOString().slice(0, 10) });
  // Company field shows the brokerage when known — matches OpenPhone's intent
  // for "company" (the business this contact represents). Falls back to address
  // routing string if brokerage wasn't resolved (e.g. property not in BBC's
  // searchProperty cache yet).
  let company = '';
  if (payload.brokerage) {
    company = `Listed By: ${payload.brokerage}`;
  } else {
    const companyParts = [];
    if (payload.address) companyParts.push(payload.address);
    if (payload.tier)    companyParts.push(`Tier ${payload.tier}`);
    if (payload.dom)     companyParts.push(`DOM ${payload.dom}`);
    company = 'RT · ' + companyParts.join(' · ');
  }
  // De-dupe by phone — one agent (one phone) = one OpenPhone contact, regardless
  // of how many properties they list. Subsequent clicks update Listed Properties
  // (custom field) + company to reflect the most recent property Tim called about.
  const dedupKey = `rt-${payload.phone || payload.pid || 'unknown'}`;
  const baseFields = {
    firstName,
    lastName,
    company,
    ...(payload.phone ? { phoneNumbers: [{ name: 'Mobile', value: payload.phone }] } : {}),
    ...(payload.email && payload.email !== 'Not Available'
        ? { emails: [{ name: 'Work', value: payload.email }] }
        : {}),
  };

  // 1. Lookup existing contact by externalId
  const lookupResp = await fetch(`https://api.openphone.com/v1/contacts?externalIds=${encodeURIComponent(dedupKey)}&maxResults=1`, {
    headers: { 'Authorization': env.OPENPHONE_API_KEY },
  });
  let existingId = null;
  if (lookupResp.ok) {
    const lookupData = await lookupResp.json();
    if (lookupData.data && lookupData.data.length > 0) existingId = lookupData.data[0].id;
  }

  let resp;
  let action;
  if (existingId) {
    // PATCH the existing contact — keeps history of prior properties only via
    // updatedAt; current state shows the latest property. (Future: append to a
    // 'properties_history' custom field if Tim wants the chain visible.)
    action = 'updated';
    resp = await fetch(`https://api.openphone.com/v1/contacts/${existingId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': env.OPENPHONE_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        defaultFields: baseFields,
        ...(customFields.length ? { customFields } : {}),
        ...(payload.briefing_url ? { sourceUrl: payload.briefing_url } : {}),
      }),
    });
  } else {
    // First contact for this phone — create
    action = 'created';
    resp = await fetch('https://api.openphone.com/v1/contacts', {
      method: 'POST',
      headers: {
        'Authorization': env.OPENPHONE_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        defaultFields: baseFields,
        ...(customFields.length ? { customFields } : {}),
        externalId: dedupKey,
        source: 'rt-companion',
        ...(payload.briefing_url ? { sourceUrl: payload.briefing_url } : {}),
      }),
    });
  }

  const respBody = await resp.text();
  // 200/201/204 = success (200 for PATCH, 201 for POST); 409/422 = duplicate fallback
  const ok = resp.status === 200 || resp.status === 201 || resp.status === 204 || resp.status === 409 || resp.status === 422;
  return {
    status: resp.status,
    ok,
    action,
    contact_id: existingId,
    dedup_key: dedupKey,
    custom_fields_filled: customFields.map(c => c.key),
    custom_fields_available: Object.keys(fieldKeys),
    body: respBody,
  };
}

function corsHeaders(env) {
  return {
    'Access-Control-Allow-Origin': env.ALLOWED_ORIGIN || '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Signature',
    'Access-Control-Max-Age': '86400'
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders(env) });
    }

    if (url.pathname === '/' || url.pathname === '/health') {
      return new Response('rt-companion BBC proxy OK\n', {
        headers: { ...corsHeaders(env), 'Content-Type': 'text/plain' }
      });
    }

    if (url.pathname === '/pipeline' && request.method === 'POST') {
      const body = await request.text();
      const sig = request.headers.get('X-Signature') || '';
      // Verify HMAC
      const verified = await hmacVerify(body, sig, env.SHARED_SECRET).catch(() => false);
      if (!verified) {
        return new Response(JSON.stringify({ error: 'invalid signature' }),
          { status: 401, headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } });
      }
      let payload;
      try { payload = JSON.parse(body); }
      catch { return new Response(JSON.stringify({ error: 'invalid json' }),
        { status: 400, headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } }); }
      try {
        const result = await saveToPipeline(env, payload);
        return new Response(JSON.stringify(result),
          { status: result.status === 201 ? 200 : 502,
            headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }),
          { status: 500, headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } });
      }
    }

    if (url.pathname === '/openphone-call' && request.method === 'POST') {
      const body = await request.text();
      const sig = request.headers.get('X-Signature') || '';
      const verified = await hmacVerify(body, sig, env.SHARED_SECRET).catch(() => false);
      if (!verified) {
        return new Response(JSON.stringify({ error: 'invalid signature' }),
          { status: 401, headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } });
      }
      let payload;
      try { payload = JSON.parse(body); }
      catch { return new Response(JSON.stringify({ error: 'invalid json' }),
        { status: 400, headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } }); }
      try {
        const result = await createOpenPhoneContact(env, payload);
        return new Response(JSON.stringify(result),
          { status: result.ok || result.skipped ? 200 : 502,
            headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }),
          { status: 500, headers: { ...corsHeaders(env), 'Content-Type': 'application/json' } });
      }
    }

    return new Response('not found', { status: 404, headers: corsHeaders(env) });
  }
};
