"""Auto-connect all free-tier providers via OmniRoute dashboard API, then test them."""
import requests
import json

# Your OmniRoute local gateway configuration
BASE_URL = "http://localhost:20128"
PASSWORD = "omniroute-admin-2026"


def get_auth_token():
    """Logs into the local dashboard to get a session cookie."""
    login_url = f"{BASE_URL}/api/auth/login"
    payload = {"password": PASSWORD}
    try:
        response = requests.post(login_url, json=payload)
        response.raise_for_status()
        # Auth token is returned as an HttpOnly cookie, not in the JSON body
        token = response.cookies.get("auth_token")
        if token:
            return token
        # Fallback: check JSON body for a token field
        return response.json().get("token")
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to OmniRoute. Is it running? Error: {e}")
        return None


def configure_all_free_providers():
    token = get_auth_token()
    if not token:
        return

    headers = {
        "Content-Type": "application/json"
    }
    cookies = {"auth_token": token}

    # Fetch the catalog of available free tier system modules
    catalog_url = f"{BASE_URL}/api/providers/catalog/free-tiers"
    try:
        catalog_res = requests.get(catalog_url, headers=headers, cookies=cookies)
        catalog_res.raise_for_status()
        free_providers = catalog_res.json().get("providers", [])
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch provider catalog: {e}")
        return

    print(f"Found {len(free_providers)} free providers. Starting automated setup...")

    # Loop through each provider and enable them natively
    for provider in free_providers:
        provider_id = provider.get("id")
        provider_name = provider.get("name")

        connect_url = f"{BASE_URL}/api/providers/connect"
        # Free tier endpoints bypass external API key parameters natively
        payload = {
            "providerId": provider_id,
            "config": {}
        }

        try:
            res = requests.post(connect_url, json=payload, headers=headers, cookies=cookies)
            if res.status_code in [200, 201]:
                print(f"  OK   Linked: {provider_name} ({provider_id})")
            else:
                print(f"  SKIP {provider_name}: {res.text}")
        except Exception as e:
            print(f"  FAIL Error linking {provider_name}: {e}")

    # Trigger system validation test across all newly registered streams
    print("\nSetup complete. Initializing multi-provider latency test...")
    try:
        test_res = requests.post(f"{BASE_URL}/api/providers/test-all", headers=headers, cookies=cookies)
        print(f"Test response: {test_res.status_code}")
        try:
            print(json.dumps(test_res.json(), indent=2))
        except Exception:
            print(test_res.text[:500])
    except Exception as e:
        print(f"Could not automatically trigger health test: {e}")


if __name__ == "__main__":
    configure_all_free_providers()
