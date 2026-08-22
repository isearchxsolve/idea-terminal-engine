"""
Probe ALL 150 catalog models — test every single one regardless of assumed auth type.
The server-side OAuth connections may cover kc/kmc/xao/cx without us needing personal keys.
"""
import json, urllib.request, urllib.error, time, socket, http.cookiejar

BASE = "http://localhost:20128/v1"
KEY  = json.loads(open("config/secrets.json").read())["OMNIROUTE_API_KEY"]

# Pull the live catalog fresh
BASE_DASH = "http://localhost:20128"
PWD = "omniroute-admin-2026"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.open(urllib.request.Request(
    BASE_DASH + "/api/auth/login",
    data=json.dumps({"password": PWD}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
), timeout=10)
catalog = json.loads(opener.open(BASE_DASH + "/api/models", timeout=10).read())["models"]
models = [m["fullModel"] for m in catalog]

print(f"Testing ALL {len(models)} catalog models...")
print(f"{'='*85}")
print(f"  {'Model':55s} {'Status':8s} {'Time':>6s}")
print(f"{'='*85}")

results = {"ok": [], "fail": [], "timeout": []}

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
        choice = payload["choices"][0]["message"]
        text = (choice.get("content") or "").strip()
        dt = time.time() - t0
        results["ok"].append((m, dt, text[:40]))
        print(f"  OK     {m:55s} {dt:5.1f}s  {text[:35]}")
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        results["fail"].append((m, f"HTTP {e.code}", dt))
        print(f"  HTTP{e.code} {m:55s} {dt:5.1f}s")
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        dt = time.time() - t0
        reason = str(getattr(e, "reason", e))[:50]
        results["timeout"].append((m, reason, dt))
        print(f"  TIMEOUT {m:55s} {dt:5.1f}s")
    except Exception as e:
        dt = time.time() - t0
        results["fail"].append((m, str(e)[:60], dt))
        print(f"  ERR    {m:55s} {dt:5.1f}s  {str(e)[:40]}")

print(f"\n{'='*85}")
print(f"SUMMARY: {len(results['ok'])} OK  |  {len(results['fail'])} FAIL  |  {len(results['timeout'])} TIMEOUT")
print(f"{'='*85}")

if results["ok"]:
    print(f"\n  WORKING ({len(results['ok'])} models, fastest first):")
    for m, dt, text in sorted(results["ok"], key=lambda x: x[1]):
        print(f"    {dt:5.1f}s  {m}")

if results["fail"]:
    print("\n  FAILED:")
    for m, reason, dt in results["fail"]:
        print(f"    {m:55s}  {reason}")

if results["timeout"]:
    print("\n  TIMEOUT:")
    for m, reason, dt in results["timeout"]:
        print(f"    {m}")

with open("scripts/frontier_model_status.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nSaved → scripts/frontier_model_status.json")
