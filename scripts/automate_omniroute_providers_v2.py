"""
OmniRoute Provider Automation v2
=================================
Uses Playwright with actual discovered page selectors.
Navigates the dashboard to connect/fix providers.

Usage:
    python scripts/automate_omniroute_providers_v2.py
    (Use the system Python that has playwright installed)
"""
import time
import json
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://localhost:20128"
PASSWORD = "omniroute-admin-2026"
HEADLESS = False
SLOW_MO = 400


def wait(page, ms=2000):
    time.sleep(ms / 1000)


def screenshot(page, name):
    path = f"scripts/screen_{name}.png"
    page.screenshot(path=path)
    print(f"  [snap] {path}")


def login(page):
    page.goto(DASHBOARD_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    wait(page)

    pwd = page.locator('input[type="password"]')
    if pwd.count() > 0:
        print("[*] Logging in...")
        pwd.fill(PASSWORD)
        # Press Enter to submit
        pwd.press("Enter")
        page.wait_for_load_state("networkidle")
        wait(page, 3000)
        print("[+] Logged in")
    else:
        print("[+] Already logged in")


def get_page_text(page):
    """Get visible text on the page for debugging."""
    return page.evaluate("""() => {
        return Array.from(document.querySelectorAll('button, a, h1, h2, h3, span, div, p, td, th'))
            .filter(el => el.offsetParent !== null && el.textContent.trim())
            .map(el => `${el.tagName}|${el.textContent.trim().substring(0, 100)}`)
            .filter((v, i, a) => a.indexOf(v) === i)
            .slice(0, 80)
            .join('\\n');
    }""")


def navigate_to(page, label):
    """Click a sidebar link by its visible text label."""
    link = page.locator(f'a:has-text("{label}")')
    if link.count() > 0:
        link.first.click()
        page.wait_for_load_state("networkidle")
        wait(page, 2000)
        print(f"[+] Navigated to: {label}")
        return True
    print(f"[-] Could not find sidebar link: {label}")
    return False


def providers_page(page):
    """Go to the Providers page."""
    # The sidebar link text contains "Providers" and "Manage AI providers"
    if navigate_to(page, "Providers"):
        return True
    # Fallback
    page.goto(f"{DASHBOARD_URL}/providers", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    wait(page, 2000)
    return True


def discovery_page(page):
    """Go to the Discovery page to scan for free providers."""
    return navigate_to(page, "Discovery")


def list_provider_cards(page):
    """List all provider cards/rows on the providers page."""
    cards = page.evaluate("""() => {
        const results = [];
        // Look for provider connection cards
        document.querySelectorAll('[class*="provider"], [class*="card"], [class*="connection"], tr, [data-provider]').forEach(el => {
            const text = el.textContent.trim().substring(0, 150);
            if (text && text.length > 5) {
                results.push({
                    tag: el.tagName,
                    cls: el.className.substring(0, 80),
                    text: text,
                    buttons: Array.from(el.querySelectorAll('button')).map(b => b.textContent.trim().substring(0, 50)).filter(Boolean)
                });
            }
        });
        return results.slice(0, 30);
    }""")
    return cards


def click_provider_card(page, provider_name):
    """Click on a specific provider card by name."""
    # Try multiple selector strategies
    selectors = [
        f'text="{provider_name}"',
        f'[data-provider="{provider_name}"]',
        f'text=/{provider_name}/i',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                wait(page, 2000)
                return True
        except Exception:
            continue
    return False


def find_and_click(page, text):
    """Find a button/link by text and click it."""
    for selector in [
        f'button:has-text("{text}")',
        f'a:has-text("{text}")',
        f'[role="button"]:has-text("{text}")',
        f'[role="tab"]:has-text("{text}")',
    ]:
        loc = page.locator(selector)
        if loc.count() > 0 and loc.first.is_visible(timeout=1500):
            loc.first.click()
            wait(page, 1500)
            return True
    return False


def fix_openrouter(page):
    """Fix OpenRouter by setting API key to 'free'."""
    print("\n[=== OpenRouter ===]")
    providers_page(page)
    wait(page)

    # Click on the OpenRouter connection
    if click_provider_card(page, "openrouter"):
        print("[+] Opened OpenRouter settings")
        screenshot(page, "openrouter_opened")

        # Look for API key input
        key_input = page.locator('input[type="password"], input[placeholder*="key" i], input[name*="key" i]')
        if key_input.count() > 0:
            key_input.first.fill("free")
            print("[+] Set API key to 'free'")

        # Look for Save/Connect button
        if find_and_click(page, "Save") or find_and_click(page, "Update") or find_and_click(page, "Connect"):
            wait(page, 3000)
            print("[+] Saved OpenRouter config")

        # Import free models
        if find_and_click(page, "Import") or find_and_click(page, "import"):
            wait(page, 3000)
            print("[+] Imported models")

        screenshot(page, "openrouter_fixed")
    else:
        print("[-] Could not find OpenRouter card")
        screenshot(page, "openrouter_notfound")


def fix_opencode(page):
    """Reconnect OpenCode."""
    print("\n[=== OpenCode ===]")
    providers_page(page)
    wait(page)

    if click_provider_card(page, "opencode"):
        print("[+] Opened OpenCode settings")
        screenshot(page, "opencode_opened")

        # Try reconnecting
        if find_and_click(page, "Reconnect") or find_and_click(page, "Refresh") or find_and_click(page, "Test"):
            wait(page, 5000)
            print("[+] Triggered reconnect/test")

        screenshot(page, "opencode_fixed")
    else:
        print("[-] Could not find OpenCode card")


def run_discovery(page):
    """Use the Discovery page to find and connect free providers."""
    print("\n[=== Discovery ===]")
    if discovery_page(page):
        wait(page, 3000)
        screenshot(page, "discovery_page")

        # Get page content
        text = get_page_text(page)
        print(f"[*] Discovery page content (first 1000 chars):\n{text[:1000]}")

        # Look for scan/start/connect buttons
        if find_and_click(page, "Scan") or find_and_click(page, "Start") or find_and_click(page, "Discover"):
            wait(page, 10000)
            print("[+] Discovery scan started")
            screenshot(page, "discovery_scanning")

        # Look for connect buttons in results
        connect_btns = page.locator('button:has-text("Connect"), button:has-text("Add"), button:has-text("Enable")')
        count = connect_btns.count()
        print(f"[*] Found {count} connect/add buttons in discovery results")

        for i in range(min(count, 10)):
            try:
                btn = connect_btns.nth(i)
                if btn.is_visible():
                    btn_text = btn.text_content().strip()
                    btn.click()
                    wait(page, 2000)
                    print(f"[+] Clicked: {btn_text}")
            except Exception:
                pass

        screenshot(page, "discovery_complete")
    else:
        print("[-] Could not navigate to Discovery")


def test_providers(page):
    """Run tests on all providers from the providers page."""
    print("\n[=== Testing Providers ===]")
    providers_page(page)
    wait(page)

    # Look for individual test buttons per provider
    test_btns = page.locator('button:has-text("Test"), button:has-text("test")')
    count = test_btns.count()
    print(f"[*] Found {count} Test buttons")

    # Also look for a "Test All" or bulk test option
    if find_and_click(page, "Test All") or find_and_click(page, "Test all") or find_and_click(page, "test-all"):
        wait(page, 15000)
        print("[+] Test All completed")
        screenshot(page, "test_all_done")
    else:
        # Try clicking individual test buttons
        for i in range(min(count, 15)):
            try:
                btn = test_btns.nth(i)
                if btn.is_visible():
                    btn.click()
                    wait(page, 3000)
            except Exception:
                pass
        screenshot(page, "test_individual_done")


def main():
    print("=" * 60)
    print("OmniRoute Provider Automation v2")
    print("=" * 60)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Login
        login(page)
        screenshot(page, "01_home")

        # Step 2: Go to Providers and dump card structure
        providers_page(page)
        cards = list_provider_cards(page)
        print(f"\n[*] Found {len(cards)} provider card elements")
        for c in cards[:15]:
            btns = ", ".join(c.get("buttons", []))
            print(f"    {c['tag']:5s} | btns=[{btns}] | {c['text'][:80]}")

        screenshot(page, "02_providers")

        # Step 3: Fix OpenRouter
        fix_openrouter(page)

        # Step 4: Fix OpenCode
        fix_opencode(page)

        # Step 5: Run Discovery
        run_discovery(page)

        # Step 6: Test all providers
        test_providers(page)

        # Final screenshot
        providers_page(page)
        screenshot(page, "99_final")

        print("\n" + "=" * 60)
        print("Done! Browser stays open for 120s for manual checks.")
        print("All screenshots in scripts/screen_*.png")
        print("=" * 60)

        # Keep open for manual intervention
        time.sleep(120)
        browser.close()


if __name__ == "__main__":
    main()
