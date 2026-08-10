"""Extract provider IDs from OmniRoute - optimized version."""
import requests, re, json

BASE = "http://localhost:20128"
PWD = "omniroute-admin-2026"

s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"password": PWD}, timeout=5)
token = r.cookies.get("auth_token")
c = {"auth_token": token}

# Get dashboard HTML
r = s.get(f"{BASE}/dashboard/providers", cookies=c, timeout=8)
js_files = re.findall(r'/_next/static/[^"]+\.js', r.text)
print(f"Found {len(js_files)} JS bundles, checking largest ones...")

# Get sizes and sort by size descending - provider registry is in a big bundle
bundles = []
for js_path in js_files:
    try:
        r = s.head(f"{BASE}{js_path}", cookies=c, timeout=3)
        size = int(r.headers.get("content-length", 0))
        bundles.append((size, js_path))
    except:
        bundles.append((0, js_path))

bundles.sort(reverse=True)
# Only check top 15 largest bundles
bundles = bundles[:15]
print(f"Checking top {len(bundles)} bundles by size:")
for size, path in bundles:
    print(f"  {size//1024:4d}KB  {path.split('/')[-1]}")

providers = {}

for size, js_path in bundles:
    try:
        r = s.get(f"{BASE}{js_path}", cookies=c, timeout=15)
        if r.status_code != 200:
            continue
        content = r.text
        fname = js_path.split("/")[-1]

        # Pattern 1: {id:"xxx",name:"Xxx",authType:"yyy"}
        matches = re.findall(
            r'id:"([a-z][-a-z0-9]*)"[^}]{0,500}?name:"([^"]+)"[^}]{0,500}?authType:"([^"]+)"',
            content
        )
        for pid, pname, auth in matches:
            providers[pid] = {"name": pname, "authType": auth}

        # Pattern 2: providerId:"xxx"
        for pid in re.findall(r'providerId:"([a-z][-a-z0-9]*)"', content):
            if pid not in providers:
                providers[pid] = {"name": pid, "authType": "unknown"}

        # Pattern 3: provider:"xxx" near connection/setup context
        for pid in re.findall(r'provider:"([a-z][-a-z0-9]*)"', content):
            if pid not in providers and len(pid) > 3:
                providers[pid] = {"name": pid, "authType": "unknown"}

    except Exception as e:
        print(f"  Error with {js_path}: {e}")

# Also check the HTML page itself for inline data
r = s.get(f"{BASE}/dashboard/providers", cookies=c, timeout=8)
# Look for __NEXT_DATA__ or inline provider lists
next_data = re.findall(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
if next_data:
    try:
        data = json.loads(next_data[0])
        pp = data.get("props", {}).get("pageProps", {})
        # Check for providers list in page props
        for key in ["providers", "availableProviders", "providerList", "allProviders"]:
            if key in pp:
                val = pp[key]
                if isinstance(val, list):
                    print(f"\nFound '{key}' in pageProps: {len(val)} items")
                    for item in val[:5]:
                        print(f"  {item}")
    except:
        pass

# Filter noise
noise = {"default", "none", "all", "free", "auto", "test", "main", "primary",
         "enhanced", "fast", "creative", "conservative", "flexible", "machine",
         "fusion", "phoenix", "gen2", "animatediff", "svd", "sketch", "structure",
         "style", "realism", "fluid", "zen", "unknown", "error", "custom"}
providers = {k: v for k, v in providers.items() if k not in noise and len(k) > 3}

print(f"\n{'='*60}")
print(f"Found {len(providers)} unique provider IDs")
print(f"{'='*60}\n")

by_auth = {}
for pid, info in sorted(providers.items()):
    auth = info["authType"]
    by_auth.setdefault(auth, []).append(pid)

for auth, pids in sorted(by_auth.items()):
    print(f"\n  [{auth}] ({len(pids)} providers):")
    for p in sorted(pids):
        name = providers[p].get("name", p)
        print(f"    {p:30s}  {name}")

# Save
with open("scripts/provider_registry.json", "w") as f:
    json.dump(providers, f, indent=2, sort_keys=True)
print(f"\nSaved to scripts/provider_registry.json")
