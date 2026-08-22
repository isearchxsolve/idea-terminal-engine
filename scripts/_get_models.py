"""Fetch the real model catalog from OmniRoute and save it."""
import urllib.request, urllib.error, json, http.cookiejar

BASE = "http://localhost:20128"
PWD  = "omniroute-admin-2026"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# Login
login_req = urllib.request.Request(
    BASE + "/api/auth/login",
    data=json.dumps({"password": PWD}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
opener.open(login_req, timeout=10)

# Fetch models
data = json.loads(opener.open(BASE + "/api/models", timeout=10).read())
models = data["models"]

print(f"Total models in catalog: {len(models)}")
for m in models:
    print(f"  {m['fullModel']:55s}  {m.get('name','')}")

# Save full list
with open("scripts/catalog_models.json", "w") as f:
    json.dump(models, f, indent=2)
print("\nSaved to scripts/catalog_models.json")
