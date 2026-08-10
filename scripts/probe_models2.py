"""Probe agy/antigravity/no-think variants that might work."""
import json, urllib.request, urllib.error

secrets = json.loads(open("config/secrets.json").read())
base = secrets.get("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
key = secrets.get("OMNIROUTE_API_KEY", "omni")

# Get all model IDs and filter to promising prefixes
resp = urllib.request.urlopen(base.rstrip("/") + "/models",
                              timeout=10)
all_ids = sorted([m["id"] for m in json.loads(resp.read())["data"]])

test_models = [m for m in all_ids if m.startswith(("agy/", "antigravity/", "no-think/agy", "no-think/antigravity", "ddgw/"))]

for model_id in test_models:
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
        "max_tokens": 16, "stream": False,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        payload = json.loads(resp.read().decode())
        text = payload["choices"][0]["message"]["content"].strip()
        print(f"  OK   {model_id:55s} -> {text[:50]!r}")
    except urllib.error.HTTPError as e:
        print(f"  FAIL {model_id:55s} -> HTTP {e.code}")
    except Exception as e:
        err = str(e)[:30]
        print(f"  FAIL {model_id:55s} -> {err}")
