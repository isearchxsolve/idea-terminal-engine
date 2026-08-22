"""
OmniRoute Provider Automation v3
=================================
Uses URL-based navigation + robust element detection.
"""
import time
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://localhost:20128"
PASSWORD = "omniroute-admin-2026"
HEADLESS = False
SLOW_MO = 500


def wait(page, s=2):
    time.sleep(s)


def snap(page, name):
    p = f"scripts/screen_{name}.png"
    page.screenshot(path=p)
    print(f"  [snap] {p}")


def login(page):
    page.goto(DASHBOARD_URL, wait_until="networkidle")
    wait(page)
    pwd = page.locator('input[type="password"]')
    if pwd.count() > 0:
        print("[*] Logging in...")
        pwd.fill(PASSWORD)
        pwd.press("Enter")
        page.wait_for_load_state("networkidle")
        wait(page, 3)
        print("[+] Logged in")
    else:
        print("[+] Already logged in")


def goto(page, path):
    """Navigate to a dashboard path."""
    url = f"{DASHBOARD_URL}{path}"
    page.goto(url, wait_until="networkidle")
    wait(page, 3)
    print(f"[+] Navigated to {path}")


def dump_visible_text(page):
    """Dump all visible text for debugging."""
    text = page.evaluate("""() => {
        const els = [];
        const walk = (el) => {
            if (el.offsetParent === null) return;
            if (el.children.length === 0 && el.textContent.trim()) {
                els.push(el.tagName + ': ' + el.textContent.trim().substring(0, 80));
            }
            for (const child of el.children) walk(child);
        };
        walk(document.body);
        return els.slice(0, 100).join('\\n');
    }""")
    return text


def main():
    print("=" * 60)
    print("OmniRoute Provider Automation v3")
    print("=" * 60)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Login
        login(page)
        snap(page, "01_home")

        # Navigate to providers page
        print("\n[Step 1] Going to /providers...")
        goto(page, "/providers")
        wait(page, 3)

        # Dump what we see
        text = dump_visible_text(page)
        print(f"[*] Visible text on /providers:\n{text[:2000]}")
        snap(page, "02_providers")

        # Try to find provider rows/cards by looking at the page HTML
        html_snippet = page.evaluate("() => document.querySelector('main, [class*=content], [class*=page]')?.innerHTML?.substring(0, 3000) || 'no main found'")
        print(f"\n[*] Main content HTML (first 3000 chars):\n{html_snippet[:3000]}")

        # Navigate to discovery
        print("\n[Step 2] Going to /discovery...")
        goto(page, "/discovery")
        wait(page, 3)
        text = dump_visible_text(page)
        print(f"[*] Visible text on /discovery:\n{text[:2000]}")
        snap(page, "03_discovery")

        # Navigate to combos
        print("\n[Step 3] Going to /combos...")
        goto(page, "/combos")
        wait(page, 3)
        text = dump_visible_text(page)
        print(f"[*] Visible text on /combos:\n{text[:2000]}")
        snap(page, "04_combos")

        print("\n" + "=" * 60)
        print("Exploration complete. Check screenshots.")
        print("Browser stays open 180s for manual work.")
        print("=" * 60)
        time.sleep(180)
        browser.close()


if __name__ == "__main__":
    main()
