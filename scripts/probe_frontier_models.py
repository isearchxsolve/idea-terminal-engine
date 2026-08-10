"""
Frontier model health check.
Tests all high-capability models across all connected providers.
Checks for: timeout, connection refused, port denied, 401/403/429/500/502 errors.
"""
import json, urllib.request, urllib.error, time, socket

BASE = "http://localhost:20128/v1"
KEY = json.loads(open("config/secrets.json").read())["OMNIROUTE_API_KEY"]

# Frontier + notable models from every provider
models = [
    # === AGY (OAuth, working) ===
    "agy/claude-opus-4-6-thinking",
    "agy/claude-sonnet-4-6",
    "agy/gemini-3.6-flash-high",
    "agy/gemini-3-pro",
    "agy/gemini-3-flash",

    # === ANTIGRAVITY (OAuth, working) ===
    "antigravity/claude-opus-4-6-thinking",
    "antigravity/claude-sonnet-4-6",
    "antigravity/gemini-3.6-flash-high",
    "antigravity/gemini-3-pro",
    "antigravity/gemini-3-flash",

    # === OPENROUTER (free tier) ===
    "openrouter/openrouter/free",
    "openrouter/free",

    # === AUTO/COMBO ===
    "auto/coding:free",
    "auto/best-coding",
    "auto/free",

    # === NVIDIA ===
    "nvidia/llama-3.1-nemotron-ultra-253b",
    "nvidia/nemotron-3-ultra-free",

    # === OPENCODE ===
    "opencode/deepseek-v4-flash-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/big-pickle",
    "opencode/gpt-5.6-sol",
    "opencode/claude-sonnet-5",
    "opencode/claude-opus-4-8",
    "opencode/glm-5.2",

    # === CODEX (OAuth) ===
    "codex/gpt-5.6-sol",
    "codex/o3",
    "codex/o4-mini",

    # === AMAZON-Q (OAuth) ===
    "amazon-q/claude-opus-4-8",
    "amazon-q/claude-sonnet-5",
    "amazon-q/gpt-5.6-sol",
    "amazon-q/gemini-3.6-flash-high",

    # === KIMI-CODING (OAuth) ===
    "kimi-coding/kimi-k2",
    "kimi-coding/k1.5",

    # === KILOCODE (OAuth) ===
    "kilocode/claude-opus-4-8",
    "kilocode/gpt-5.6-sol",
    "kilocode/gemini-3.6-flash-high",

    # === XAI ===
    "xai/grok-4.5",
    "xai/grok-3",
    "xai/grok-code-fast",

    # === BLACKBOX ===
    "blackbox/blackbox",
    "blackbox/blackbox-pro",

    # === SAMBANOVA ===
    "sambanova/llama-3.3-70b",
    "sambanova/deepseek-r1",

    # === NOVITA ===
    "novita/deepseek-r1",
    "novita/llama-3.3-70b",

    # === FRIENDLIAI ===
    "friendliai/meta-llama-3.1-70b-instruct",
    "friendliai/meta-llama-3.1-8b-instruct",

    # === AINATIVE ===
    "ainative/ainative-pro",

    # === Brave/bazaarlink/airforce ===
    "brave-search/brave-search",
    "bazaarlink/bazaarlink",
    "api-airforce/llama-3.3-70b",
    "api-airforce/gpt-4o-mini",

    # === Old prefix (likely dead) ===
    "cl/openai/gpt-5.6-sol",
]

print(f"Testing {len(models)} frontier models...")
print(f"{'='*80}")
print(f"{'Model':50s} {'Status':6s} {'Time':>6s}  {'Detail'}")
print(f"{'='*80}")

results = {"ok": [], "fail": [], "timeout": [], "dead_prefix": []}

for m in models:
    body = json.dumps({
        "model": m,
        "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
        "max_tokens": 16,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        BASE.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"].strip()
        dt = time.time() - t0
        status = "OK"
        detail = text[:40]
        results["ok"].append((m, dt))
        print(f"  {m:50s} {status:6s} {dt:5.1f}s  {detail}")
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        status = f"HTTP{e.code}"
        detail = e.reason
        results["fail"].append((m, f"HTTP {e.code}", dt))
        print(f"  {m:50s} {status:6s} {dt:5.1f}s  {detail}")
    except urllib.error.URLError as e:
        dt = time.time() - t0
        reason = str(e.reason)
        if "refused" in reason.lower():
            status = "REFUSED"
        elif "timeout" in reason.lower():
            status = "TIMEOUT"
        else:
            status = "URLERR"
        results["timeout"].append((m, reason[:60], dt))
        print(f"  {m:50s} {status:6s} {dt:5.1f}s  {reason[:60]}")
    except socket.timeout:
        dt = time.time() - t0
        results["timeout"].append((m, "socket timeout", dt))
        print(f"  {m:50s} {'TIMEOUT':6s} {dt:5.1f}s  socket timeout")
    except TimeoutError:
        dt = time.time() - t0
        results["timeout"].append((m, "timeout", dt))
        print(f"  {m:50s} {'TIMEOUT':6s} {dt:5.1f}s  timeout")
    except Exception as e:
        dt = time.time() - t0
        status = "ERR"
        detail = str(e)[:60]
        results["fail"].append((m, detail, dt))
        print(f"  {m:50s} {status:6s} {dt:5.1f}s  {detail}")

# Summary
print(f"\n{'='*80}")
print(f"SUMMARY: {len(results['ok'])} OK, {len(results['fail'])} FAIL, {len(results['timeout'])} TIMEOUT")
print(f"{'='*80}")

if results["ok"]:
    print(f"\n  WORKING MODELS (sorted by speed):")
    for m, dt in sorted(results["ok"], key=lambda x: x[1]):
        print(f"    {dt:5.1f}s  {m}")

if results["fail"]:
    print(f"\n  FAILED (HTTP errors):")
    for m, reason, dt in results["fail"]:
        print(f"    {dt:5.1f}s  {m:45s}  {reason}")

if results["timeout"]:
    print(f"\n  TIMEOUT/REFUSED:")
    for m, reason, dt in results["timeout"]:
        print(f"    {dt:5.1f}s  {m:45s}  {reason[:50]}")

# Save
with open("scripts/frontier_model_status.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
