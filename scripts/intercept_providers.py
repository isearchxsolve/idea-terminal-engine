"""
Use Playwright to intercept network requests and find the full provider list
from the OmniRoute dashboard.
"""
import time, json
from playwright.sync_api import sync_playwright

URL = "http://localhost:20128"
PWD = "omniroute-admin-2026"

captured = []

def on_response(response):
    url = response.url
    if "/api/" in url or "provider" in url.lower():
        try:
            body = response.text()
            captured.append({"url": url, "status": response.status, "body": body[:2000]})
        except:
            captured.append({"url": url, "status": response.status, "body": ""})

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, slow_mo=200)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.on("response", on_response)

    # Login
    page.goto(URL, wait_until="domcontentloaded", timeout=15000)
    time.sleep(2)
    pwd = page.locator('input[type="password"]')
    if pwd.count() > 0:
        pwd.fill(PWD)
        pwd.press("Enter")
        time.sleep(4)
    print("[+] Logged in")

    # Navigate to providers
    captured.clear()
    page.goto(f"{URL}/dashboard/providers", wait_until="domcontentloaded", timeout=15000)
    time.sleep(5)
    page.keyboard.press("Escape")
    time.sleep(2)

    print(f"\n[*] Captured {len(captured)} API responses:")
    for c in captured:
        print(f"  {c['status']} {c['url'][:100]}")
        if c['body'] and len(c['body']) > 50:
            # Check if it contains a provider list
            try:
                data = json.loads(c['body'])
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, list) and len(v) > 10:
                            print(f"    -> {k}: list of {len(v)} items")
                            if len(v) > 0:
                                print(f"       first: {str(v[0])[:150]}")
                elif isinstance(data, list) and len(data) > 10:
                    print(f"    -> list of {len(data)} items")
                    if len(data) > 0:
                        print(f"       first: {str(data[0])[:150]}")
            except:
                pass

    # Now look for "Add Provider" or similar button to see available providers
    print("\n[*] Looking for 'Add' or 'Connect' buttons...")
    page.screenshot(path="scripts/providers_51.png", full_page=True)

    # Find all buttons
    buttons = page.evaluate("""() => {
        const btns = [];
        document.querySelectorAll('button, a[role=button], [class*=button]').forEach(el => {
            if (el.offsetParent !== null) {
                const t = el.textContent.trim().substring(0, 60);
                if (t) btns.push({text: t, tag: el.tagName});
            }
        });
        return btns;
    }""")
    print(f"  Found {len(buttons)} buttons:")
    for b in buttons:
        print(f"    [{b['tag']}] {b['text']}")

    # Look for a provider selection dropdown or "Add" button
    add_btn = page.locator('button:has-text("Add"), button:has-text("Connect"), button:has-text("New")')
    if add_btn.count() > 0:
        print(f"\n[+] Found {add_btn.count()} add/connect buttons, clicking first...")
        add_btn.first.click()
        time.sleep(3)
        page.screenshot(path="scripts/add_provider_dialog.png")

        # Check for new captured requests
        print(f"  After click: {len(captured)} captured responses")

        # Look for dropdown/select with provider names
        dialog_elements = page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('select option, [role=option], [role=menuitem], [class*=option], [class*=item], li').forEach(el => {
                if (el.offsetParent !== null) {
                    const t = el.textContent.trim().substring(0, 80);
                    if (t && t.length > 2) items.push(t);
                }
            });
            return [...new Set(items)].slice(0, 300);
        }""")
        print(f"\n  Dialog items ({len(dialog_elements)}):")
        for item in dialog_elements[:50]:
            print(f"    {item}")

        # Save all dialog items
        with open("scripts/dialog_items.json", "w") as f:
            json.dump(dialog_elements, f, indent=2)
        print(f"\n  Saved {len(dialog_elements)} items to scripts/dialog_items.json")

    print("\n[*] Browser open 60s for manual inspection...")
    time.sleep(60)
    browser.close()
