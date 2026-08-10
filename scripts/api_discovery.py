"""
OmniRoute API Discovery
========================
Probes the OmniRoute dashboard API to find all available endpoints
for provider management (connect, enable, disable, configure, test).
"""
import requests, json

BASE = "http://localhost:20128"
PWD = "omniroute-admin-2026"


def login():
    r = requests.post(f"{BASE}/api/auth/login", json={"password": PWD})
    token = r.cookies.get("auth_token")
    print(f"[+] Login: status={r.status_code}, token={'yes' if token else 'no'}")
    return token


def try_endpoint(method, path, payload=None, label=""):
    """Try an API endpoint and report the result."""
    url = f"{BASE}{path}"
    cookies = {"auth_token": token}
    headers = {"Content-Type": "application/json"}
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, cookies=cookies, timeout=8)
        elif method == "POST":
            r = requests.post(url, json=payload or {}, headers=headers, cookies=cookies, timeout=8)
        elif method == "PUT":
            r = requests.put(url, json=payload or {}, headers=headers, cookies=cookies, timeout=8)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, cookies=cookies, timeout=8)
        else:
            r = requests.patch(url, json=payload or {}, headers=headers, cookies=cookies, timeout=8)

        status = r.status_code
        body = ""
        try:
            body = json.dumps(r.json(), indent=1)[:300]
        except Exception:
            body = r.text[:200]

        marker = "OK" if status < 400 else "ERR"
        print(f"  {marker} {method:5s} {path:55s} {status}  {body[:120]}")
        return status, r
    except Exception as e:
        print(f"  FAIL {method:5s} {path:55s} {str(e)[:80]}")
        return 0, None


token = login()
if not token:
    print("Login failed. Is OmniRoute running?")
    exit(1)

print(f"\n{'='*70}")
print("API DISCOVERY")
print(f"{'='*70}")

# --- Auth & Session ---
print("\n--- Auth & Session ---")
try_endpoint("GET", "/api/auth/session")
try_endpoint("GET", "/api/auth/status")
try_endpoint("GET", "/api/auth/me")

# --- Providers CRUD ---
print("\n--- Providers List/Config ---")
try_endpoint("GET", "/api/providers")
try_endpoint("GET", "/api/providers/list")
try_endpoint("GET", "/api/providers/connected")
try_endpoint("GET", "/api/providers/status")
try_endpoint("GET", "/api/providers/config")
try_endpoint("GET", "/api/providers/health")

# --- Provider Catalog ---
print("\n--- Provider Catalog ---")
try_endpoint("GET", "/api/providers/catalog")
try_endpoint("GET", "/api/providers/catalog/free")
try_endpoint("GET", "/api/providers/catalog/all")
try_endpoint("GET", "/api/catalog")
try_endpoint("GET", "/api/catalog/providers")

# --- Provider Actions ---
print("\n--- Provider Actions ---")
try_endpoint("POST", "/api/providers/test-all")
try_endpoint("POST", "/api/providers/test")
try_endpoint("POST", "/api/providers/enable-all")
try_endpoint("POST", "/api/providers/refresh")
try_endpoint("POST", "/api/providers/reconnect")
try_endpoint("POST", "/api/providers/discover")

# --- Provider Connect/Enable (with sample provider IDs) ---
print("\n--- Provider Connect/Enable (sample) ---")
sample_providers = ["openrouter", "opencode", "nvidia", "agy", "kimi-coding", "cline"]
for pid in sample_providers:
    try_endpoint("POST", f"/api/providers/connect", {"providerId": pid, "config": {}})
    try_endpoint("POST", f"/api/providers/enable", {"providerId": pid})
    try_endpoint("POST", f"/api/providers/{pid}/enable")
    try_endpoint("POST", f"/api/providers/{pid}/connect")
    try_endpoint("POST", f"/api/providers/{pid}/test")

# --- Models ---
print("\n--- Models ---")
try_endpoint("GET", "/api/models")
try_endpoint("GET", "/api/providers/models")
try_endpoint("GET", "/v1/models")

# --- Settings/Config ---
print("\n--- Settings ---")
try_endpoint("GET", "/api/settings")
try_endpoint("GET", "/api/config")
try_endpoint("GET", "/api/config/providers")

# --- Next.js data routes ---
print("\n--- Next.js Data Routes ---")
try_endpoint("GET", "/dashboard/_next/data/providers.json")
try_endpoint("GET", "/_next/data/providers.json")

print(f"\n{'='*70}")
print("Discovery complete.")
