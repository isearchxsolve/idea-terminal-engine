"""
OmniRoute Provider Automation v4 (final)
==========================================
Clicks sidebar links for SPA navigation.
Interacts with provider cards to fix connections.
"""
import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:20128"
PWD = "omniroute-admin-2026"


def w(s=2):
    time.sleep(s)


def snap(page, name):
    p = f"scripts/s_{name}.png"
    page.screenshot(path=p, full_page=True)
    print(f"  [snap] {p}")


def click_sidebar(page, label):
    """Click sidebar link containing the given label text."""
    # The sidebar links are <a> elements with icon+label+description
    # Use get_by_role to find links, then filter by text content
    links = page.locator('a')
    count = links.count()
    for i in range(count):
        try:
            txt = links.nth(i).text_content() or ""
            if label.lower() in txt.lower():
                links.nth(i).click()
                w(3)
                print(f"  [+] Clicked sidebar: {label}")
                return True
        except Exception:
            continue
    print(f"  [-] Sidebar link not found: {label}")
    return False


def dump_page(page):
    """Dump all visible interactive elements."""
    items = page.evaluate("""() => {
        const r = [];
        document.querySelectorAll('button, a, input, [role=button], [role=tab], [role=menuitem]').forEach(el => {
            if (el.offsetParent !== null) {
                const t = el.textContent.trim().substring(0, 60);
                const tag = el.tagName;
                const type = el.type || '';
                const href = el.href || '';
                if (t) r.push(`${tag}|${type}|${href}|${t}`);
            }
        });
        return [...new Set(r)].slice(0, 120);
    }""")
    for item in items:
        print(f"    {item}")
    return items


def main():
    print("=" * 60)
    print("OmniRoute Automation v4")
    print("=" * 60)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Login
        page.goto(URL, wait_until="networkidle")
        w(2)
        pwd_field = page.locator('input[type="password"]')
        if pwd_field.count() > 0:
            print("[*] Logging in...")
            pwd_field.fill(PWD)
            pwd_field.press("Enter")
            page.wait_for_load_state("networkidle")
            w(3)
            print("[+] Logged in")
        snap(page, "01_home")

        # Navigate to Providers via sidebar click
        print("\n[1] Navigating to Providers...")
        click_sidebar(page, "Providers")
        snap(page, "02_providers")

        # Dump all interactive elements on the providers page
        print("\n[*] Interactive elements on Providers page:")
        dump_page(page)

        # Look for provider connection cards/rows
        print("\n[*] Looking for provider cards...")
        cards = page.evaluate("""() => {
            const cards = [];
            // Look for elements that look like provider connection items
            document.querySelectorAll('[class*="provider"], [class*="connection"], tr, [data-id]').forEach(el => {
                const text = el.textContent.trim().substring(0, 200);
                const btns = Array.from(el.querySelectorAll('button')).map(b => b.textContent.trim().substring(0, 40)).filter(Boolean);
                if (text.length > 3 && btns.length > 0) {
                    cards.push({text, btns, id: el.getAttribute('data-id') || ''});
                }
            });
            return cards.slice(0, 20);
        }""")
        print(f"  Found {len(cards)} cards with buttons:")
        for c in cards:
            print(f"    [{c.get('id','')}] {c['text'][:80]} | btns: {c['btns']}")

        # Try clicking on OpenRouter to fix it
        print("\n[2] Trying to open OpenRouter settings...")
        # Find any element containing "openrouter" text and click it
        or_el = page.locator(':text("openrouter")').first
        if or_el.count() > 0:
            or_el.click()
            w(3)
            snap(page, "03_openrouter_detail")
            print("  [+] Clicked OpenRouter")

            # Dump elements in the detail view
            print("\n  [*] Elements in OpenRouter detail:")
            dump_page(page)

            # Look for API key field
            key_fields = page.locator('input[type="password"], input[type="text"]')
            print(f"\n  [*] Found {key_fields.count()} input fields")
            for i in range(key_fields.count()):
                try:
                    ph = key_fields.nth(i).get_attribute("placeholder") or ""
                    nm = key_fields.nth(i).get_attribute("name") or ""
                    val = key_fields.nth(i).input_value()
                    print(f"    input[{i}]: placeholder='{ph}' name='{nm}' value='{val[:30]}'")
                except Exception:
                    pass

            # Try to find and click Save/Update
            save_btn = page.locator('button:has-text("Save"), button:has-text("Update"), button:has-text("Connect")')
            if save_btn.count() > 0:
                print(f"  [*] Found {save_btn.count()} save/update buttons")

            # Go back to providers list
            page.go_back()
            w(2)
        else:
            print("  [-] OpenRouter not found on page")

        # Navigate to Discovery
        print("\n[3] Navigating to Discovery...")
        click_sidebar(page, "Discovery")
        snap(page, "04_discovery")

        print("\n[*] Interactive elements on Discovery page:")
        dump_page(page)

        # Final: go back to providers and dump full page HTML
        print("\n[4] Back to Providers for full HTML dump...")
        click_sidebar(page, "Providers")
        w(2)

        # Save full page HTML for analysis
        html = page.content()
        with open("scripts/dashboard_providers.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [*] Saved full HTML ({len(html)} chars) to scripts/dashboard_providers.html")

        print("\n" + "=" * 60)
        print("Exploration complete. Browser open 180s for manual work.")
        print("Check scripts/s_*.png screenshots and scripts/dashboard_providers.html")
        print("=" * 60)
        w(180)
        browser.close()


if __name__ == "__main__":
    main()
