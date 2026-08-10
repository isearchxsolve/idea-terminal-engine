"""Extract the full provider list from OmniRoute dashboard frontend."""
import requests, re, json

BASE = "http://localhost:20128"
PWD = "omniroute-admin-2026"

s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"password": PWD}, timeout=5)
token = r.cookies.get("auth_token")
c = {"auth_token": token}

# Get dashboard HTML
r = s.get(f"{BASE}/dashboard/providers", cookies=c, timeout=8)
html = r.text

# Find JS bundles
js_files = re.findall(r'/_next/static/[^"]+\.js', html)
print(f"Found {len(js_files)} JS bundles")

# Check __NEXT_DATA__
next_data = re.findall(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if next_data:
    data = json.loads(next_data[0])
    print(f"\n__NEXT_DATA__ keys: {list(data.keys())}")
    pp = data.get("props", {}).get("pageProps", {})
    print(f"pageProps keys: {list(pp.keys())}")
    for k, v in pp.items():
        if isinstance(v, list):
            print(f"  {k}: list[{len(v)}]")
        elif isinstance(v, dict):
            print(f"  {k}: dict keys={list(v.keys())[:10]}")
        else:
            print(f"  {k}: {str(v)[:100]}")

# Now fetch each JS bundle and look for provider definitions
print("\n--- Searching JS bundles for provider definitions ---")
all_provider_names = set()

for js_path in js_files:
    url = f"{BASE}{js_path}"
    try:
        r = s.get(url, cookies=c, timeout=10)
        if r.status_code != 200:
            continue
        content = r.text

        # Look for provider ID patterns like "providerId" or provider lists
        # Common patterns: "openrouter","opencode","nvidia", etc.
        # Search for arrays of provider strings
        patterns = [
            r'"providerId"\s*:\s*"([^"]+)"',
            r'"id"\s*:\s*"([a-z][-a-z0-9]+)"\s*,\s*"name"',
            r'name:"([^"]+)",\s*(?:description|icon|url):',
        ]

        for pat in patterns:
            matches = re.findall(pat, content)
            for m in matches:
                if len(m) > 2 and len(m) < 40:
                    all_provider_names.add(m)

        # Also look for large arrays of provider-like strings
        # Pattern: ["provider1","provider2",...]
        array_matches = re.findall(r'\["([a-z][-a-z0-9]+)(?:","([a-z][-a-z0-9]+)){5,}"\]', content)
        if array_matches:
            for group in array_matches:
                for item in group:
                    if item and len(item) > 2:
                        all_provider_names.add(item)

    except Exception as e:
        pass

print(f"\nFound {len(all_provider_names)} potential provider names:")
for name in sorted(all_provider_names):
    print(f"  {name}")

# Also try: look for the specific pattern of provider registry
print("\n--- Searching for provider registry in JS ---")
for js_path in js_files:
    url = f"{BASE}{js_path}"
    try:
        r = s.get(url, cookies=c, timeout=10)
        if r.status_code != 200:
            continue
        content = r.text

        # Look for provider registry/config objects
        # Pattern: {id:"openrouter",name:"OpenRouter",...}
        registry = re.findall(r'\{[^{}]*id:"([a-z][-a-z0-9]+)"[^{}]*name:"([^"]+)"[^{}]*\}', content)
        if registry:
            print(f"\n  Provider registry in {js_path.split('/')[-1]}:")
            for pid, pname in registry:
                print(f"    {pid:25s} => {pname}")
                all_provider_names.add(pid)
    except Exception:
        pass

# Save the full list
with open("scripts/discovered_providers.json", "w") as f:
    json.dump(sorted(all_provider_names), f, indent=2)
print(f"\nSaved {len(all_provider_names)} providers to scripts/discovered_providers.json")
