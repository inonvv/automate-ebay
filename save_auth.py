"""Manual eBay login -> persistent profile at .user-data/ + auth.json snapshot.

WHY persistent context: preserves cookies, localStorage, IndexedDB, service
worker state, and a stable browser fingerprint across runs. Cookie-only
storage_state export would lose IDB/SW state and create a fingerprint
mismatch between the session that logged in and the test runs -- exactly
the signal Akamai flags.

WHY channel="chrome" + AutomationControlled patch: hide the obvious bot
fingerprint of Playwright's bundled chromium.

WHY homepage first + a human-pace browsing pause before Sign In:
cold-profile direct navigation to /signin/ is itself a bot signal (real
users browse around first). The pause lets you do some natural browsing
-- scroll, hover items, click a category -- before triggering eBay's auth
flow, which lowers Akamai's risk score for the session.

Tick "Keep me signed in" when you sign in -- doubles cookie lifetime.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path(".user-data")


def main():
    USER_DATA_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.ebay.com/")
        print(
            "Browse the homepage normally for 20-30 seconds: scroll, hover\n"
            "items, click a category, come back. DO NOT click Sign In yet --\n"
            "let Akamai's risk score settle on a 'real user' baseline.\n"
            "\n"
            "When you're ready: click Sign In, log in (tick 'Keep me signed\n"
            "in'), and once the homepage shows you logged in, press Enter\n"
            "here to save the profile."
        )
        input()
        ctx.close()


if __name__ == "__main__":
    main()
