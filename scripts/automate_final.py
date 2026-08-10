"""
OmniRoute Provider Automation - FINAL
=======================================
Uses discovered URL paths: /dashboard/providers, /dashboard/discovery, etc.
Logs in, navigates via direct URLs, interacts with provider cards.
"""
import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:20128"
PWD = "omniroute-admin-2026"
BASE = f"{URL}/dashboard"


def w(s=2):
    time.sleep(s)


def snap(page, name):
    p = f"scripts/final_{name}.png"
    page.screenshot(path=p, full_page=True)
    print(f"  [snap] {p}")


def goto(page, path):
    """Navigate to a dashboard path using the correct URL structure."""
    full = f"{BASE}/{path}"
    page.goto(full, wait_until="domcontentloaded", timeout=15000)
    w(4)
    # Dismiss any modal overlays
    page.keyboard.press("Escape")
    w(1)
    print(f"  [+] {full}")


def dismiss_overlays(page):
    """Press Escape to close any open modals/search."""
    page.keyboard.press("Escape")
    w(1)


def dump_interactive(page):
    """Dump interactive elements."""
    items = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('button, a[href], input, select, [role=button], [role=tab]').forEach(el => {
            if (el.offsetParent !== null) {
                const t = el.textContent.trim().substring(0, 70);
                const tag = el.tagName;
                const href = el.getAttribute('href') || '';
                const type = el.getAttribute('type') || '';
                const ph = el.getAttribute('placeholder') || '';
                if (t || ph) r.push(`${tag}|href=${href}|type=${type}|ph=${ph}|${t}`);
            }
        });
        return [...new Set(r)].slice(0, 100);
    }""")
    for item in items:
        print(f"    {item}")
    return items


def find_provider_rows(page):
    """Find all provider connection rows on the page."""
    rows = page.evaluate("""() => {
        const results = [];
        // Look for table rows or card elements with provider info
        document.querySelectorAll('tr, [class*="row"], [class*="card"], [class*="item"], [class*="connection"]').forEach(el => {
            const text = el.textContent.trim();
            const buttons = Array.from(el.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim().substring(0, 40),
                title: b.getAttribute('title') || b.getAttribute('aria-label') || ''
            })).filter(b => b.text || b.title);
            const links = Array.from(el.querySelectorAll('a')).map(a => ({
                text: a.textContent.trim().substring(0, 40),
                href: a.getAttribute('href') || ''
            })).filter(a => a.text);

            if (text.length > 3 && text.length < 400 && (buttons.length > 0 || links.length > 0)) {
                results.push({
                    tag: el.tagName,
                    text: text.substring(0, 200),
                    buttons: buttons,
                    links: links,
                    cls: el.className.substring(0, 80)
                });
            }
        });
        // Deduplicate
        const seen = new Set();
        return results.filter(r => {
            const key = r.text.substring(0, 60);
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        }).slice(0, 30);
    }""")
    return rows


def main():
    print("=" * 60)
    print("OmniRoute Provider Automation - FINAL")
    print("=" * 60)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # --- LOGIN ---
        page.goto(URL, wait_until="domcontentloaded", timeout=15000)
        w(2)
        pwd_field = page.locator('input[type="password"]')
        if pwd_field.count() > 0:
            print("[*] Logging in...")
            pwd_field.fill(PWD)
            pwd_field.press("Enter")
            w(5)
            print("[+] Logged in")
        snap(page, "01_home")

        # --- PROVIDERS PAGE ---
        print("\n[1] Providers page...")
        goto(page, "providers")
        dismiss_overlays(page)
        snap(page, "02_providers")

        print("\n[*] Interactive elements:")
        dump_interactive(page)

        print("\n[*] Provider rows/cards:")
        rows = find_provider_rows(page)
        print(f"  Found {len(rows)} rows:")
        for r in rows:
            btns = [b['text'] or b['title'] for b in r.get('buttons', [])]
            lnks = [l['text'] for l in r.get('links', [])]
            print(f"    {r['tag']:5s} | btns={btns} | lnks={lnks} | {r['text'][:80]}")

        # --- Try clicking on a specific provider (OpenRouter) ---
        print("\n[2] Looking for OpenRouter...")
        # Use the text locator with force to bypass overlays
        try:
            or_link = page.locator('a[href*="openrouter"], :text("openrouter")').first
            if or_link.is_visible(timeout=3000):
                or_link.click(force=True)
                w(3)
                print("  [+] Opened OpenRouter")
                snap(page, "03_openrouter")

                print("\n  [*] OpenRouter detail elements:")
                dump_interactive(page)

                # Look for API key input
                inputs = page.locator('input:visible')
                for i in range(inputs.count()):
                    try:
                        ph = inputs.nth(i).get_attribute("placeholder") or ""
                        val = inputs.nth(i).input_value()
                        typ = inputs.nth(i).get_attribute("type") or ""
                        print(f"    input[{i}]: type={typ} placeholder='{ph}' value='{val[:40]}'")
                    except Exception:
                        pass
            else:
                print("  [-] OpenRouter not visible")
        except Exception as e:
            print(f"  [-] Error: {e}")

        # Go back to providers list
        goto(page, "providers")
        dismiss_overlays(page)

        # --- DISCOVERY PAGE ---
        print("\n[3] Discovery page...")
        goto(page, "discovery")
        dismiss_overlays(page)
        snap(page, "04_discovery")

        print("\n[*] Interactive elements on Discovery:")
        dump_interactive(page)

        # Look for scan/connect buttons
        scan_btn = page.locator('button:has-text("Scan"), button:has-text("Discover"), button:has-text("Start")')
        if scan_btn.count() > 0:
            print(f"\n  [*] Found {scan_btn.count()} scan buttons")
            scan_btn.first.click()
            w(10)
            snap(page, "05_discovery_scanning")
            print("  [+] Scan started")

        # --- COMBOS PAGE ---
        print("\n[4] Combos page...")
        goto(page, "combos")
        dismiss_overlays(page)
        snap(page, "06_combos")

        print("\n[*] Interactive elements on Combos:")
        dump_interactive(page)

        # --- Save full HTML of providers page for analysis ---
        print("\n[5] Saving providers page HTML...")
        goto(page, "providers")
        dismiss_overlays(page)
        w(2)
        html = page.content()
        with open("scripts/final_providers.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [*] Saved {len(html)} chars to scripts/final_providers.html")

        print("\n" + "=" * 60)
        print("Exploration complete!")
        print("Browser stays open 180s for manual work.")
        print("Screenshots: scripts/final_*.png")
        print("HTML: scripts/final_providers.html")
        print("=" * 60)
        w(180)
        browser.close()


if __name__ == "__main__":
    main()
