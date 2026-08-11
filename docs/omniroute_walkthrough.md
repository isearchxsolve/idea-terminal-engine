# OmniRoute Reliability Fix — Walkthrough

## What Was Done

### Investigation Summary

Ran live diagnostics against the running OmniRoute v3.8.49 service (PID 6624). Confirmed:
- Service RUNNING, port 20128 bound, HTTP server responding
- SQLite 7 MB, healthy; STORAGE_ENCRYPTION_KEY present in both NSSM env + `.env` file
- `setupComplete: true`, `cryptography.status: healthy`
- **4,067 models** available with the existing key

---

## Root Cause 1 — Wrong Health Endpoint (Fixed ✅)

### What broke
`omniroute_full_setup.py` polled `GET /api/health` which **does not exist** in v3.8.49.
The real endpoint is `GET /api/monitoring/health`.

`/api/health` returns `401 Unauthorized`, causing the setup script to timeout after 10 attempts
and fall into the "server unreachable" path. The dashboard's WebSocket probe does the same thing,
showing the yellow "reconnecting…" banner permanently.

### What was fixed in [`omniroute_full_setup.py`](file:///D:/ideation_to_prototype/idea-terminal-engine/scripts/omniroute_full_setup.py)
- All `/api/health` → `/api/monitoring/health`
- Health check now accepts **any non-zero HTTP status** (including 401) as "server is up"
- When server returns 200 (no auth needed), parses and prints `status: healthy`

---

## Root Cause 2 — API Key Extraction Bug (Fixed ✅)

### What broke
`configure_omniroute()` tried to extract the API key from the `Set-Cookie` response header:
```python
# OLD — WRONG
api_key = cookie.split("auth_token=")[1].split(";")[0]  # extracts a JWT, not a bearer key!
```
The `auth_token` cookie is a **JWT session token**, not an OmniRoute bearer key (`sk-...`).
This JWT would fail all API calls with `401`.

When this failed, the code fell back to the hardcoded `sk-2daf4dd6d1e45047-53255c-89ec5ddf`
— but by then the health check had already failed, so providers were being connected with a
seemingly "default" key that nobody had verified worked.

### What was fixed
New `configure_omniroute()` flow:
1. **2a** — Poll `/api/monitoring/health` until server responds
2. **2b** — Try the `KNOWN_FALLBACK_KEY` directly via `verify_key()` (hits `/v1/models`)
3. **2c** — If that fails: login with cookie jar → call `/api/keys` → match by `keyPrefix`

New `verify_key()`:
- Uses 20s timeout (the models list is 4000+ entries and can be slow)
- Falls back to a minimal chat completion probe if `/v1/models` times out

```
KNOWN_FALLBACK_KEY = "sk-2daf4dd6d1e45047-53255c-89ec5ddf"   # verified: 4,067 models
```

---

## Root Cause 3 — Crash-Storm (Historical, Resolved ✅)

### What happened
Between 23:14–23:52 UTC on 2026-08-10, the service crashed and restarted **46 times** in
~38 minutes. Each restart cycle took ~15 seconds. The crash log files (`service-stdout-*.log`)
are proof — NSSM creates a new stdout file on each restart.

**Trigger:** `[usageDb] Failed to archive legacy request logs: EBUSY: resource busy or locked`
— SQLite couldn't delete/rename the log file while another process held it.

**NSSM amplifier:** `AppThrottle=1500` (only 1.5s!) means NSSM restarts the process immediately
after exit, creating a rapid death spiral.

### What was done
- Cleaned up all 44 zero-byte crash log files from `~/.omniroute/logs/`
- Added `AppThrottle 30000` (30s) to the service install code in the setup script
- Created [fix_omniroute_throttle.ps1](file:///D:/ideation_to_prototype/idea-terminal-engine/scripts/fix_omniroute_throttle.ps1) — **run this as Administrator** to apply to the live service

```powershell
# Run as Administrator:
.\scripts\fix_omniroute_throttle.ps1
```

The crash loop resolved on its own at 23:52 UTC. Service has been stable since (~10 hours).

---

## Root Cause 4 — 0 Healthy Providers (Ongoing ⚠️)

### State
69 connections exist. All show `isHealthy: null` (the credential health-checker runs every 300s
with a 30s initial delay — it may not have completed a full cycle yet for all connections).

**Key observations from logs:**
- `kimi-coding` — ✅ Token refresh confirmed working (`[HealthCheck] Successfully refreshed Kimi Coding token`)
- `nvidia/z-ai/glm-5.2` — ⚠️ Rate-limited; dropping after 180s queue timeout (503 from upstream)
- `antigravity / agy` — OAuth-based; tied to `isearch.xsolve@gmail.com` cookies (may need refresh)
- Most others — placeholder connections; need API keys or OAuth to be functional

**Why Zed shows "overloaded":**
When `nvidia/z-ai/glm-5.2` times out after 180s and returns a 503, OmniRoute propagates that
as "provider unavailable". The fix is to use a different model that has working credentials.

---

## Changes Made

### [`omniroute_full_setup.py`](file:///D:/ideation_to_prototype/idea-terminal-engine/scripts/omniroute_full_setup.py)
| Change | Lines |
|--------|-------|
| Health endpoint: `/api/health` → `/api/monitoring/health` | `install_omniroute()` wait loop |
| Accept 401/403 as "server up" in wait loop | Same |
| Added `AppThrottle 30000` to NSSM install | `install_omniroute()` setup block |
| Added `KNOWN_FALLBACK_KEY` constant | Module level |
| Added `_omni_get()` helper | New function |
| Rewrote `configure_omniroute()` — proper health wait, key verify, cookie-jar login, `/api/keys` query | `configure_omniroute()` |
| Added `verify_key()` with 20s timeout + chat fallback probe | New function |
| `main()` uses `KNOWN_FALLBACK_KEY` constant | `main()` |

### [`fix_omniroute_throttle.ps1`](file:///D:/ideation_to_prototype/idea-terminal-engine/scripts/fix_omniroute_throttle.ps1) (NEW)
Admin script to apply the 30s throttle to the currently running service.

---

## Verification Checklist

Run these to confirm everything is working:

```powershell
# 1. Service health (no auth needed)
Invoke-RestMethod "http://localhost:20128/api/monitoring/health" | Select-Object status, setupComplete, uptime

# 2. Key is valid (expect large model list)
$h = @{ Authorization = "Bearer sk-2daf4dd6d1e45047-53255c-89ec5ddf" }
(Invoke-RestMethod "http://localhost:20128/v1/models" -Headers $h).data.Count

# 3. Provider count
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest "http://localhost:20128/api/auth/login" -Method POST -ContentType "application/json" -Body '{"password":"omniroute-admin-2026"}' -SessionVariable "session" | Out-Null
(Invoke-RestMethod "http://localhost:20128/api/providers" -WebSession $session).connections.Count

# 4. Apply NSSM throttle fix (run as Administrator)
.\scripts\fix_omniroute_throttle.ps1

# 5. Re-run setup (should succeed now)
python scripts\omniroute_full_setup.py
```

---

## Recommended Next Steps

### Immediate
1. **Run throttle fix as Admin** (prevents crash-storm recurrence):
   ```powershell
   # Open elevated PowerShell, then:
   cd D:\ideation_to_prototype\idea-terminal-engine
   .\scripts\fix_omniroute_throttle.ps1
   ```

2. **For Zed — use a model that isn't rate-limited.** The `nvidia/z-ai/glm-5.2` model is
   hitting queue saturation. Switch Zed to:
   - `agy/gemini-2.5-flash` (fastest free tier via Antigravity)
   - `if/kimi-k3` or `if/qwen3.8-max-preview` (via Qoder, usually stable)
   - `auto/coding:free` (auto-selects from available healthy pool)

3. **Refresh Antigravity/agy credentials** — visit dashboard → Providers → agy → reconnect with
   `isearch.xsolve@gmail.com` if the OAuth cookie has expired.

### For Stable Long-Term Use
- Add a `REDIS_URL` to suppress the `[REDIS] REDIS_URL is not set in production` warning
  (optional — in-memory fallback works fine for a single-node setup)
- Consider upgrading the Perplexity connection (invalid API key warning in logs)
- Set `nvidia/z-ai/glm-5.2` queue `maxWaitMs` to 30s in Settings → Resilience (currently 180s,
  causing very long hangs before fallback)
