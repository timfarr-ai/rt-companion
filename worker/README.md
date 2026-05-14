# rt-companion BBC Proxy Worker

Solves the iPhone problem: no userscript = no one-tap Save-to-BBC-Pipeline from the briefing on mobile. This Worker handles the auth + HTTP plumbing server-side.

## Deploy

```bash
cd worker

# 1. Install wrangler if you haven't
npm install -g wrangler

# 2. Login to Cloudflare (one-time)
wrangler login

# 3. Create KV namespace for BBC session caching
wrangler kv:namespace create BBC_SESSION
# Copy the returned `id` into wrangler.jsonc (replace REPLACE_WITH_KV_ID)

# 4. Set secrets
wrangler secret put BBC_EMAIL        # paste timfarr@me.com
wrangler secret put BBC_PASS         # paste BBC password
wrangler secret put SHARED_SECRET    # generate one — e.g. `openssl rand -hex 32`

# 5. Deploy
wrangler deploy

# Worker URL printed at end, e.g.:
#   https://rt-companion-bbc-proxy.<your-subdomain>.workers.dev
```

## Configure the dashboard to use it

After deploy, set two env vars in the cloud routine that runs `triage.py`:

```bash
export BBC_PROXY_URL="https://rt-companion-bbc-proxy.<your-subdomain>.workers.dev"
export BBC_PROXY_SECRET="<same SHARED_SECRET as the Worker>"
```

The briefing render embeds these so each card has a working "Save to Pipeline" button that fires one POST to the Worker.

## How it works

```
iPhone briefing card → POST /pipeline with HMAC sig
                       ↓
                     Worker (Cloudflare)
                       ↓ (cached session OR fresh login)
                     BBC /api/auth/login
                       ↓
                     BBC /api/lightning-leads/pipeline/add
                       ↓
                     201 Created → property auto-disappears from BBC search
```

Session cookie cached in KV for 25 min — first request ~700ms, subsequent ~300ms.

## Security

- HMAC-SHA256 signature on every request; anyone hitting the URL without the secret gets 401
- BBC creds stored as Worker secrets (encrypted at rest)
- CORS locked to `https://timfarr-ai.github.io`
- No PII logged

## Endpoints

- `GET /health` — liveness check
- `POST /pipeline` — save property; body = same shape BBC's `/pipeline/add` expects
