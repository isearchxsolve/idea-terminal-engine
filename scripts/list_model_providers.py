"""Extract all unique providers from the OmniRoute models API."""
import requests, json
from collections import Counter

BASE = "http://localhost:20128"
PWD = "omniroute-admin-2026"

s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"password": PWD}, timeout=5)
token = r.cookies.get("auth_token")
h = {"Content-Type": "application/json"}
c = {"auth_token": token}

r = s.get(f"{BASE}/api/models", headers=h, cookies=c, timeout=15)
models = r.json().get("models", [])

# Extract unique providers
providers = Counter()
available_models = Counter()
for m in models:
    p = m.get("provider", "unknown")
    providers[p] += 1
    if m.get("available", False):
        available_models[p] += 1

print(f"Total models: {len(models)}")
print(f"Unique providers in model catalog: {len(providers)}")
print()

header = f"{'Provider':30s} {'Total':>6s} {'Avail':>6s}"
print(header)
print("-" * 45)
for p, count in providers.most_common():
    avail = available_models.get(p, 0)
    print(f"{p:30s} {count:6d} {avail:6d}")

# Now check which of these are already connected
r2 = s.get(f"{BASE}/api/providers", headers=h, cookies=c, timeout=5)
connected = {conn["provider"] for conn in r2.json().get("connections", [])}
print(f"\nAlready connected: {len(connected)}")

# Find unconnected providers from the model catalog
unconnected = set(providers.keys()) - connected
print(f"In model catalog but not connected: {len(unconnected)}")
for p in sorted(unconnected):
    print(f"  {p:30s} ({providers[p]} models, {available_models.get(p, 0)} available)")

# Save
with open("scripts/all_model_providers.json", "w") as f:
    json.dump({
        "providers": dict(providers),
        "available": dict(available_models),
        "connected": sorted(connected),
        "unconnected": sorted(unconnected)
    }, f, indent=2)
print("\nSaved to scripts/all_model_providers.json")
