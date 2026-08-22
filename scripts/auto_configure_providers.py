"""
OmniRoute Full Provider Automation
====================================
Two-phase approach:
  Phase 1 (API): Enable all disabled connections, refresh expired OAuth tokens,
                  test every connection, collect health status.
  Phase 2 (Playwright): For providers needing OAuth re-auth or special setup
                         (e.g. OpenRouter free-tier account import).

Discovered API endpoints:
  GET    /api/providers              - list all connections
  POST   /api/providers              - add new connection (name, provider, apiKey)
  PUT    /api/providers/{id}         - update connection (isActive, priority, etc.)
  DELETE /api/providers/{id}         - delete connection
  POST   /api/providers/{id}/test    - test connection health
  POST   /api/providers/{id}/refresh - refresh OAuth token
"""
import json, requests, time, sys
from datetime import datetime, timezone

BASE = "http://localhost:20128"
PWD = "omniroute-admin-2026"


def session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"password": PWD}, timeout=5)
    r.raise_for_status()
    token = r.cookies.get("auth_token")
    if not token:
        print("[!] Login failed - no auth_token cookie")
        sys.exit(1)
    print(f"[+] Logged in (token: {token[:20]}...)")
    return s, {"auth_token": token}


def api_get(s, cookies, path):
    r = s.get(f"{BASE}{path}", cookies=cookies, timeout=8)
    r.raise_for_status()
    return r.json()


def api_put(s, cookies, path, body):
    r = s.put(f"{BASE}{path}", json=body, cookies=cookies,
              headers={"Content-Type": "application/json"}, timeout=8)
    return r.status_code, r.json()


def api_post(s, cookies, path, body=None):
    r = s.post(f"{BASE}{path}", json=body or {}, cookies=cookies,
               headers={"Content-Type": "application/json"}, timeout=15)
    return r.status_code, r.text[:300]


def now_utc():
    return datetime.now(timezone.utc)


def is_expired(conn):
    """Check if an OAuth connection's token has expired."""
    exp = conn.get("expiresAt") or conn.get("tokenExpiresAt")
    if not exp:
        return False
    try:
        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        return now_utc() > exp_dt
    except Exception:
        return False


def phase1_api(s, cookies):
    """Phase 1: Use the API to manage all connections."""
    print(f"\n{'='*60}")
    print("PHASE 1: API-based provider management")
    print(f"{'='*60}")

    # 1. List all connections
    data = api_get(s, cookies, "/api/providers")
    conns = data.get("connections", [])
    print(f"\n[*] Found {len(conns)} connections")

    results = {"active": [], "inactive": [], "expired": [], "refreshed": [], "tested": []}

    for conn in conns:
        cid = conn["id"]
        name = conn["provider"]
        active = conn.get("isActive", False)
        expired = is_expired(conn)
        auth_type = conn.get("authType", "unknown")
        email = conn.get("email", conn.get("name", ""))

        print(f"\n  --- {name} ({cid[:8]}...) ---")
        print(f"      auth={auth_type}  active={active}  expired={expired}  email={email}")

        # 2. Enable if disabled
        if not active:
            print("      [>] Enabling...")
            status, resp = api_put(s, cookies, f"/api/providers/{cid}", {"isActive": True})
            print(f"      [{'OK' if status == 200 else 'FAIL'}] {status} {str(resp)[:100]}")
            if status == 200:
                results["active"].append(name)

        # 3. Refresh expired OAuth tokens
        if expired and auth_type == "oauth":
            print("      [>] Refreshing expired token...")
            status, resp = api_post(s, cookies, f"/api/providers/{cid}/refresh")
            print(f"      [{'OK' if status == 200 else 'FAIL'}] {status} {str(resp)[:100]}")
            if status == 200:
                results["refreshed"].append(name)
            results["expired"].append(name)

        # 4. Test connection
        print("      [>] Testing...")
        status, resp = api_post(s, cookies, f"/api/providers/{cid}/test")
        try:
            test_data = json.loads(resp) if isinstance(resp, str) else resp
        except Exception:
            test_data = {"raw": resp}
        valid = test_data.get("valid", False) if isinstance(test_data, dict) else False
        diagnosis = test_data.get("diagnosis", {}) if isinstance(test_data, dict) else {}
        diag_type = diagnosis.get("type", "unknown")
        print(f"      [{'OK' if valid else 'FAIL'}] test={valid}  diagnosis={diag_type}")
        results["tested"].append({"name": name, "id": cid, "valid": valid, "diagnosis": diag_type})

    # Summary
    print(f"\n{'='*60}")
    print("PHASE 1 SUMMARY")
    print(f"{'='*60}")
    print(f"  Enabled:    {len(results['active'])} - {results['active']}")
    print(f"  Expired:    {len(results['expired'])} - {results['expired']}")
    print(f"  Refreshed:  {len(results['refreshed'])} - {results['refreshed']}")
    print(f"  Tested:     {len(results['tested'])}")
    for t in results["tested"]:
        mark = "OK" if t["valid"] else "FAIL"
        print(f"    [{mark:4s}] {t['name']:20s} diagnosis={t['diagnosis']}")

    return results


def phase2_playwright(results):
    """Phase 2: Use Playwright for OAuth flows and UI-only operations."""
    print(f"\n{'='*60}")
    print("PHASE 2: Playwright-based OAuth/UI automation")
    print(f"{'='*60}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Playwright not available, skipping Phase 2")
        return

    failed = [t for t in results["tested"] if not t["valid"]]
    if not failed:
        print("[*] All connections healthy, no UI intervention needed")
        return

    print(f"[*] {len(failed)} failed connections need UI attention:")
    for f in failed:
        print(f"    - {f['name']} ({f['diagnosis']})")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Login
        page.goto(BASE, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        pwd_field = page.locator('input[type="password"]')
        if pwd_field.count() > 0:
            pwd_field.fill(PWD)
            pwd_field.press("Enter")
            time.sleep(4)
            print("[+] Logged in via Playwright")

        # Go to providers page
        page.goto(f"{BASE}/dashboard/providers", wait_until="domcontentloaded", timeout=15000)
        time.sleep(4)
        page.keyboard.press("Escape")
        time.sleep(1)

        # Find and click "Test All" buttons
        print("\n[*] Looking for 'Test All' buttons...")
        test_all_btns = page.locator('button:has-text("Test All")')
        count = test_all_btns.count()
        print(f"  Found {count} 'Test All' buttons")
        for i in range(count):
            try:
                if test_all_btns.nth(i).is_visible():
                    test_all_btns.nth(i).click()
                    time.sleep(5)
                    print(f"  [+] Clicked Test All #{i+1}")
            except Exception as e:
                print(f"  [-] Error: {e}")

        # Take screenshot of current state
        page.screenshot(path="scripts/auto_providers.png", full_page=True)
        print("\n[+] Screenshot saved: scripts/auto_providers.png")

        # Look for any "Enable" or "Reconnect" buttons for disabled providers
        print("\n[*] Looking for enable/reconnect buttons...")
        enable_btns = page.locator('button:has-text("Enable"), button:has-text("Reconnect"), button:has-text("Refresh")')
        ecount = enable_btns.count()
        print(f"  Found {ecount} enable/reconnect/refresh buttons")
        for i in range(ecount):
            try:
                btn = enable_btns.nth(i)
                if btn.is_visible():
                    txt = btn.text_content().strip()
                    print(f"  [+] Clicking: {txt}")
                    btn.click()
                    time.sleep(3)
            except Exception as e:
                print(f"  [-] Error: {e}")

        # Wait for user to manually handle OAuth if needed
        print(f"\n{'='*60}")
        print("Phase 2 complete. Browser stays open 120s for manual OAuth.")
        print("Check scripts/auto_providers.png for current state.")
        print(f"{'='*60}")
        time.sleep(120)
        browser.close()


def main():
    print(f"{'='*60}")
    print("OmniRoute Full Provider Automation")
    print(f"{'='*60}")

    s, cookies = session()
    results = phase1_api(s, cookies)
    phase2_playwright(results)

    # Final status
    print(f"\n{'='*60}")
    print("ALL DONE")
    print(f"{'='*60}")
    print("Next steps:")
    print("  1. Run probe_new_providers.py to check model availability")
    print("  2. Update config/models.json with working models")
    print("  3. Add fallback chains for resilience")


if __name__ == "__main__":
    main()
