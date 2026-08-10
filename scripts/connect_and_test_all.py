"""
Connect remaining providers and test all connections.
Uses short aliases discovered from the model catalog.
"""
import requests, json, time

BASE = "http://localhost:20128"
PWD = "omniroute-admin-2026"

s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"password": PWD}, timeout=5)
token = r.cookies.get("auth_token")
h = {"Content-Type": "application/json"}
c = {"auth_token": token}

# Get currently connected
data = s.get(f"{BASE}/api/providers", headers=h, cookies=c, timeout=5).json()
connected = {conn["provider"] for conn in data.get("connections", [])}
print(f"Currently connected: {len(connected)}")

# Try additional provider IDs (from model catalog aliases + dashboard discovery)
additional = [
    # Short aliases from model catalog
    "ali", "bb", "cl", "ds", "hf", "hyp", "kc", "oc", "ovh", "pplx",
    "samba", "scw", "xao", "kmc",
    # Full names that might differ from what we tried
    "friendli", "friendliai",
    # More from dashboard JS
    "arena-free", "arena", "nanobanana-flash", "nanobanana-pro",
    "9router", "360ai", "ai-horde", "ainative", "alibaba-cloud",
    "alibaba-token", "ant-ling", "api-airforce", "arcee",
    "aws-polly", "baichuan", "baidu-qianfan", "bazaarlink",
    "blacksMinds", "brave-search", "byteplus", "bytez",
    "cartesia", "chutes", "cli-proxy",
    "datarob", "databricks", "dedicated",
    "elevenlabs", "enterprise",
    "google-ai", "google-vertex", "grok",
    "infermatic-ai", "inflection-ai",
    "jina", "kling",
    "lm-studio", "llamafile",
    "mistral", "moonshot-kimi",
    "open-hand", "open-hand-ai",
    "qwen", "qwen-coder",
    "runway", "stability-ai",
    "text-gen", "tgi",
    "upstage",
    "vercel-ai-sdk", "vllm",
    "weights-biases", "wandb",
    "yi", "yi-lightning",
]

to_try = [p for p in additional if p not in connected]
print(f"Trying {len(to_try)} additional providers...\n")

new_connected = []
for pid in to_try:
    body = {"name": pid, "provider": pid, "apiKey": "free"}
    try:
        r = s.post(f"{BASE}/api/providers", json=body, headers=h, cookies=c, timeout=5)
        if r.status_code in (200, 201):
            print(f"  OK   {pid}")
            new_connected.append(pid)
        elif "Invalid provider" in r.text:
            pass  # silently skip invalid providers
        else:
            print(f"  FAIL {pid}: {r.status_code} {r.text[:60]}")
    except Exception as e:
        print(f"  ERR  {pid}: {str(e)[:50]}")

print(f"\nNewly connected: {len(new_connected)} - {new_connected}")

# Get final connections count
data = s.get(f"{BASE}/api/providers", headers=h, cookies=c, timeout=5).json()
conns = data.get("connections", [])
print(f"\nTotal connections now: {len(conns)}")

# Test all connections
print(f"\n{'='*60}")
print("TESTING ALL CONNECTIONS")
print(f"{'='*60}")

ok = []
fail = []
for conn in conns:
    cid = conn["id"]
    name = conn["provider"]
    active = conn.get("isActive", False)

    # Enable if not active
    if not active:
        s.put(f"{BASE}/api/providers/{cid}", json={"isActive": True},
              headers=h, cookies=c, timeout=5)

    # Test
    try:
        r = s.post(f"{BASE}/api/providers/{cid}/test", headers=h, cookies=c, timeout=15)
        td = r.json()
        valid = td.get("valid", False)
        diag = td.get("diagnosis", {}).get("type", "?")
        if valid:
            print(f"  OK   {name}")
            ok.append(name)
        else:
            msg = td.get("diagnosis", {}).get("message", "") or td.get("error", "")
            print(f"  FAIL {name:25s} {diag} {str(msg)[:50]}")
            fail.append({"name": name, "diag": diag, "msg": str(msg)[:80]})
    except Exception as e:
        print(f"  ERR  {name}: {str(e)[:50]}")
        fail.append({"name": name, "diag": "error", "msg": str(e)[:80]})

print(f"\n{'='*60}")
print(f"FINAL SUMMARY: {len(ok)} OK, {len(fail)} FAIL out of {len(conns)} connections")
print(f"{'='*60}")

# Save results
with open("scripts/final_connection_status.json", "w") as f:
    json.dump({"total": len(conns), "ok": ok, "fail": fail}, f, indent=2)
print("Saved to scripts/final_connection_status.json")
