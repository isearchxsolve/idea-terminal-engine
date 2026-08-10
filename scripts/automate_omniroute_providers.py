"""
OmniRoute Dashboard Automation Script
======================================
Uses Playwright to automate provider connection & configuration
through the OmniRoute dashboard UI.

Usage:
    python scripts/automate_omniroute_providers.py

Requires: playwright (pip install playwright, python -m playwright install chromium)
"""
import time
import json
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

DASHBOARD_URL = "http://localhost:20128"
PASSWORD = "omniroute-admin-2026"
HEADLESS = False  # Set True for CI; False so you can watch + handle OAuth popups
SLOW_MO = 300     # ms between actions — slow enough to follow visually


def wait_for_dashboard(page, timeout=15000):
    """Wait until the dashboard is fully loaded."""
    page.wait_for_load_state("networkidle", timeout=timeout)
    time.sleep(1)


def login(page):
    """Log into the dashboard with the management password."""
    page.goto(DASHBOARD_URL, wait_until="domcontentloaded")
    wait_for_dashboard(page)

    # Check if we're on the login page
    if "login" in page.url.lower() or page.locator('input[type="password"]').count() > 0:
        print("[*] Login page detected — entering password...")
        pwd_input = page.locator('input[type="password"]')
        if pwd_input.count() == 0:
            # Try any text input as fallback
            pwd_input = page.locator('input[type="text"]').first
        pwd_input.fill(PASSWORD)

        # Click the submit/login button
        submit = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign in"), button:has-text("Unlock")')
        if submit.count() > 0:
            submit.first.click()
        else:
            pwd_input.press("Enter")
        wait_for_dashboard(page)
        print("[+] Logged in successfully")
    else:
        print("[+] Already logged in / no login required")


def navigate_to_providers(page):
    """Go to the Providers page."""
    # Look for a sidebar link to Providers
    providers_link = page.locator('a:has-text("Providers"), [data-testid="providers"], nav >> text=Providers')
    if providers_link.count() > 0:
        providers_link.first.click()
        wait_for_dashboard(page)
        print("[+] Navigated to Providers page")
    else:
        # Fallback: try direct URL
        page.goto(f"{DASHBOARD_URL}/providers", wait_until="domcontentloaded")
        wait_for_dashboard(page)
        print("[+] Navigated to /providers")


def take_screenshot(page, name):
    """Save a debug screenshot."""
    path = f"scripts/debug_{name}.png"
    page.screenshot(path=path)
    print(f"[*] Screenshot saved: {path}")


def discover_page_structure(page):
    """Print the page structure to help with selector discovery."""
    # Get all visible text content of buttons and links
    elements = page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('button, a, [role="button"], [role="tab"], h1, h2, h3, [class*="provider"], [class*="connect"], [class*="add"]').forEach(el => {
            const text = el.textContent.trim().substring(0, 80);
            const tag = el.tagName.toLowerCase();
            const cls = el.className.substring(0, 60);
            if (text) items.push(`${tag} | ${cls} | ${text}`);
        });
        return items.slice(0, 60);
    }""")
    print("\n[*] Page elements discovered:")
    for e in elements:
        print(f"    {e}")
    return elements


def try_connect_openrouter(page):
    """Fix OpenRouter: set API key to 'free' and import free models."""
    print("\n[===] Fixing OpenRouter provider...")
    try:
        # Find the OpenRouter connection card/row
        or_card = page.locator('text=OpenRouter, text=openrouter, [data-provider="openrouter"]').first
        if or_card.count() == 0:
            # Try finding it in the connections list
            or_card = page.locator(':text("openrouter")').first

        # Click on it to open settings
        or_card.click()
        wait_for_dashboard(page)

        # Look for API key field or edit button
        api_key_input = page.locator('input[placeholder*="key"], input[name*="key"], input[type="password"]')
        if api_key_input.count() > 0:
            api_key_input.first.fill("free")
            print("[+] Set OpenRouter API key to 'free'")

        # Save/Update
        save_btn = page.locator('button:has-text("Save"), button:has-text("Update"), button:has-text("Connect")')
        if save_btn.count() > 0:
            save_btn.first.click()
            wait_for_dashboard(page)
            print("[+] OpenRouter configuration saved")

        # Try to import free models
        import_btn = page.locator('button:has-text("Import"), button:has-text("Sync"), button:has-text("Free")')
        if import_btn.count() > 0:
            import_btn.first.click()
            wait_for_dashboard(page)
            print("[+] OpenRouter model import triggered")

    except Exception as e:
        print(f"[-] OpenRouter fix failed: {e}")
        take_screenshot(page, "openrouter_fail")


def try_connect_opencode(page):
    """Check and fix OpenCode provider."""
    print("\n[===] Checking OpenCode provider...")
    try:
        oc_text = page.locator(':text("opencode"), :text("OpenCode")')
        if oc_text.count() > 0:
            oc_text.first.click()
            wait_for_dashboard(page)
            print("[+] Opened OpenCode settings")
            take_screenshot(page, "opencode_settings")

            # Check if there's a reconnect or refresh button
            reconnect = page.locator('button:has-text("Reconnect"), button:has-text("Refresh"), button:has-text("Test")')
            if reconnect.count() > 0:
                reconnect.first.click()
                wait_for_dashboard(page)
                print("[+] OpenCode reconnect/refresh triggered")
    except Exception as e:
        print(f"[-] OpenCode fix failed: {e}")
        take_screenshot(page, "opencode_fail")


def run_test_all(page):
    """Click the Test All button to verify all providers."""
    print("\n[===] Running Test All on providers...")
    try:
        test_btn = page.locator('button:has-text("Test All"), button:has-text("Test all"), button:has-text("test-all")')
        if test_btn.count() > 0:
            test_btn.first.click()
            print("[+] Test All triggered — waiting for results...")
            time.sleep(30)  # Give it time to test all models
            take_screenshot(page, "test_all_results")
            print("[+] Test complete — check dashboard for results")
        else:
            print("[-] Test All button not found")
    except Exception as e:
        print(f"[-] Test All failed: {e}")


def auto_sync_all_providers(page):
    """Click Auto Sync and Test Models for each connected provider."""
    print("\n[===] Auto-syncing all providers...")
    try:
        # Look for auto-sync buttons
        sync_btns = page.locator('button:has-text("Auto Sync"), button:has-text("Autosync"), button:has-text("Sync Models")')
        count = sync_btns.count()
        print(f"[*] Found {count} sync buttons")

        for i in range(count):
            try:
                sync_btns.nth(i).click()
                time.sleep(2)
                print(f"[+] Clicked sync button {i+1}/{count}")
            except Exception:
                pass

        wait_for_dashboard(page)
    except Exception as e:
        print(f"[-] Auto-sync failed: {e}")


def main():
    print("=" * 60)
    print("OmniRoute Provider Automation")
    print("=" * 60)
    print(f"Dashboard: {DASHBOARD_URL}")
    print(f"Mode: {'headless' if HEADLESS else 'headed (visible browser)'}")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
        )
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()

        # Step 1: Login
        print("[Step 1] Logging in...")
        login(page)
        take_screenshot(page, "01_after_login")

        # Step 2: Navigate to Providers
        print("\n[Step 2] Navigating to Providers...")
        navigate_to_providers(page)
        take_screenshot(page, "02_providers_page")

        # Step 3: Discover page structure
        print("\n[Step 3] Discovering page structure...")
        elements = discover_page_structure(page)

        # Step 4: Try to fix OpenRouter
        print("\n[Step 4] Fixing OpenRouter...")
        try_connect_openrouter(page)
        take_screenshot(page, "04_after_openrouter")

        # Step 5: Try to fix OpenCode
        print("\n[Step 5] Fixing OpenCode...")
        try_connect_opencode(page)
        take_screenshot(page, "05_after_opencode")

        # Step 6: Auto-sync all
        print("\n[Step 6] Auto-syncing all providers...")
        auto_sync_all_providers(page)
        take_screenshot(page, "06_after_sync")

        # Step 7: Run Test All
        print("\n[Step 7] Running Test All...")
        run_test_all(page)
        take_screenshot(page, "07_final")

        print("\n" + "=" * 60)
        print("Automation complete!")
        print("Check the dashboard for results.")
        print("Screenshots saved in scripts/debug_*.png")
        print("=" * 60)

        # Keep browser open for manual intervention
        print("\n[*] Browser will stay open for 60 seconds for manual checks...")
        print("    (Set HEADLESS=False and increase this if you need more time)")
        time.sleep(60)

        browser.close()


if __name__ == "__main__":
    main()
