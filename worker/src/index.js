/**
 * rt-companion BBC Proxy Worker
 *
 * Proxies "Save to Pipeline" calls from the rt-companion briefing dashboard to
 * BBC's /api/lightning-leads/pipeline/add endpoint. Solves the iPhone problem:
 * the BBC autosearch userscript doesn't run on iOS Safari, so Tim couldn't
 * one-tap Save-to-Pipeline from his phone. This Worker handles the auth +
 * HTTP plumbing server-side; the briefing card just POSTs a property payload.
 *
 * Endpoints:
 *   GET  /           → health check
 *   POST /pipeline   → save property to BBC Pipeline
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

    return new Response('not found', { status: 404, headers: corsHeaders(env) });
  }
};
