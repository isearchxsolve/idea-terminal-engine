"""
OmniRoute Provider Automation v5
==================================
Uses Ctrl+K search to navigate in the SPA.
Expands sidebar sections to find provider cards.
"""
import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:20128"
PWD = "omniroute-admin-2026"


def w(s=2):
    time.sleep(s)


def snap(page, name):
    p = f"scripts/v5_{name}.png"
    page.screenshot(path=p, full_page=True)
    print(f"  [snap] {p}")


def search_navigate(page, term):
    """Use Ctrl+K search to navigate to a page."""
    print(f"  [*] Searching for: {term}")
    # Press Ctrl+K to open search
    page.keyboard.press("Control+k")
    w(1)

    # Type the search term
    search_input = page.locator('input[role="combobox"], input[type="search"], input[placeholder*="Search" i]')
    if search_input.count() == 0:
        # Try any visible input
        search_input = page.locator('input:visible')
    if search_input.count() > 0:
        search_input.first.fill(term)
        w(1.5)

        # Look for the result and click it
        result = page.locator(f'[role="option"]:has-text("{term}"), a:has-text("{term}"), [class*="result"]:has-text("{term}")')
        if result.count() > 0:
            result.first.click()
            w(3)
            print(f"  [+] Navigated via search: {term}")
            return True
        else:
            # Try pressing Enter
            search_input.first.press("Enter")
            w(3)
            print(f"  [+] Submitted search for: {term}")
            return True

    print(f"  [-] Search input not found")
    return False


def expand_sidebar(page):
    """Expand all collapsed sidebar sections."""
    print("  [*] Expanding sidebar sections...")
    # Click all "expand_more" buttons in the sidebar
    expand_btns = page.locator('button:has-text("expand_more")')
    count = expand_btns.count()
    print(f"  [*] Found {count} expand buttons")
    for i in range(count):
        try:
            if expand_btns.nth(i).is_visible():
                expand_btns.nth(i).click()
                w(0.5)
        except Exception:
            pass
    w(2)
    print(f"  [+] Sidebar expanded")


def main():
    print("=" * 60)
    print("OmniRoute Automation v5")
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

        # Expand sidebar
        print("\n[1] Expanding sidebar...")
        expand_sidebar(page)
        snap(page, "02_sidebar_expanded")

        # Now try to find and click Providers link
        print("\n[2] Clicking Providers link...")
        providers_link_found = False
        links = page.locator('a')
        for i in range(links.count()):
            try:
                txt = links.nth(i).text_content() or ""
                if "providers" in txt.lower() and "manage" in txt.lower():
                    links.nth(i).click()
                    w(3)
                    providers_link_found = True
                    print(f"  [+] Clicked Providers link")
                    break
            except Exception:
                continue

        if not providers_link_found:
            # Try Ctrl+K search
            search_navigate(page, "Providers")

        snap(page, "03_providers_page")

        # Dump visible elements
        print("\n[*] Visible elements on Providers page:")
        items = page.evaluate("""() => {
            const r = [];
            document.querySelectorAll('button, a, input, [role=button], [role=tab], h1, h2, h3, td, [class*=card], [class*=row], [class*=item]').forEach(el => {
                if (el.offsetParent !== null && el.textContent.trim()) {
                    const t = el.textContent.trim().substring(0, 80);
                    r.push(`${el.tagName}|${t}`);
                }
            });
            return [...new Set(r)].slice(0, 150);
        }""")
        for item in items:
            print(f"    {item}")

        # Look for provider connection cards
        print("\n[*] Looking for provider connections...")
        connections = page.evaluate("""() => {
            const results = [];
            // Find elements that contain provider names and have action buttons
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                const text = el.textContent || '';
                const directText = Array.from(el.childNodes)
                    .filter(n => n.nodeType === 3)
                    .map(n => n.textContent.trim())
                    .join(' ');

                // Check if this looks like a provider row
                if (el.querySelectorAll('button').length > 0 && text.length < 300 && text.length > 3) {
                    const btns = Array.from(el.querySelectorAll('button')).map(b => b.textContent.trim()).filter(Boolean);
                    if (btns.length > 0 && btns.length < 8) {
                        results.push({
                            tag: el.tagName,
                            text: text.substring(0, 150),
                            btns: btns,
                            cls: el.className.substring(0, 60)
                        });
                    }
                }
            }
            // Deduplicate by text
            const seen = new Set();
            return results.filter(r => {
                const key = r.text.substring(0, 50);
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            }).slice(0, 25);
        }""")
        print(f"  Found {len(connections)} connection-like elements:")
        for c in connections:
            print(f"    {c['tag']} | cls={c['cls'][:40]} | btns={c['btns']} | {c['text'][:80]}")

        # Try clicking on OpenRouter
        print("\n[3] Looking for OpenRouter...")
        or_found = False
        for i in range(links.count()):
            try:
                txt = (links.nth(i).text_content() or "").lower()
                if "openrouter" in txt:
                    links.nth(i).click()
                    w(3)
                    or_found = True
                    print(f"  [+] Clicked OpenRouter")
                    snap(page, "04_openrouter")

                    # Dump the detail view
                    print("  [*] OpenRouter detail elements:")
                    detail_items = page.evaluate("""() => {
                        const r = [];
                        document.querySelectorAll('button, input, select, [role=button], [role=tab]').forEach(el => {
                            if (el.offsetParent !== null) {
                                const t = el.textContent.trim().substring(0, 60);
                                const type = el.type || '';
                                const ph = el.placeholder || '';
                                const val = el.value || '';
                                r.push(`${el.tagName}|type=${type}|ph=${ph}|val=${val.substring(0,30)}|${t}`);
                            }
                        });
                        return r.slice(0, 50);
                    }""")
                    for d in detail_items:
                        print(f"    {d}")
                    break
            except Exception:
                continue

        if not or_found:
            print("  [-] OpenRouter not found")

        # Save HTML
        html = page.content()
        with open("scripts/v5_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n[*] Saved page HTML ({len(html)} chars) to scripts/v5_page.html")

        print("\n" + "=" * 60)
        print("Done. Browser open 180s for manual work.")
        print("=" * 60)
        w(180)
        browser.close()


if __name__ == "__main__":
    main()
