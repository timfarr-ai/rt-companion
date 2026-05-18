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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: env.BBC_EMAIL, password: env.BBC_PASS })
  });
  if (!resp.ok) throw new Error(`BBC login failed: ${resp.status}`);
  const data = await resp.json();
  const token = data.token || (data.user && data.user.token);
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
      'Authorization': `Bearer ${session.token}`,
      'Cookie': session.cookieHeader,
      'Accept': 'application/json'
    },
    body: JSON.stringify({ pipelineData })
  });
  return { status: resp.status, body: await resp.text() };
}

/**
 * Create-or-update an OpenPhone contact for a property-call workflow.
 *
 * The OpenPhone API doesn't have a generic "notes" field. We stuff the
 * property context into `company` so it's prominently visible on the
 * contact view inside the OpenPhone app/desktop. Format:
 *   "RT · 123 Main St, City, ST · Tier B SF · DOM 156"
 *
 * Uses externalId for cross-system de-dup (BBC PID). If a contact already
 * exists with the same externalId, OpenPhone may return 409/422 — we treat
 * that as a soft success (call still proceeds).
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
  const companyParts = [];
  if (payload.address) companyParts.push(payload.address);
  if (payload.tier)    companyParts.push(`Tier ${payload.tier}`);
  if (payload.dom)     companyParts.push(`DOM ${payload.dom}`);
  const company = 'RT · ' + companyParts.join(' · ');
  const body = {
    defaultFields: {
      firstName,
      lastName,
      company,
      ...(payload.phone ? { phoneNumbers: [{ name: 'Mobile', value: payload.phone }] } : {}),
      ...(payload.email && payload.email !== 'Not Available'
          ? { emails: [{ name: 'Work', value: payload.email }] }
          : {}),
    },
    externalId: payload.pid || `rt-${payload.phone}`,
    source: 'rt-companion',
    ...(payload.briefing_url ? { sourceUrl: payload.briefing_url } : {}),
  };
  const resp = await fetch('https://api.openphone.com/v1/contacts', {
    method: 'POST',
    headers: {
      'Authorization': env.OPENPHONE_API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  const respBody = await resp.text();
  // 200/201 = created; 409/422 = duplicate (soft success); else = error
  const ok = resp.status === 200 || resp.status === 201 || resp.status === 409 || resp.status === 422;
  return { status: resp.status, ok, body: respBody };
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
