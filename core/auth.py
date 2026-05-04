"""Session bootstrap.

`ensure_session` is the single entry point used by conftest:
1. If `.user-data/` already holds a working session (My eBay link visible),
   no-op — tests run against the persisted profile.
2. Otherwise run an automated sign-in once (env-supplied creds), let
   `launch_persistent_context` write cookies/IDB into `.user-data/`,
   and return. From then on path 1 takes over.

Each atomic step in the login is wrapped in NetworkValidator.expect_ok so
silent regressions (form not POSTed, redirect to splashui, 4xx from auth)
fail loudly with Allure attachments instead of selector timeouts.
"""
from pathlib import Path

from playwright.sync_api import Playwright

from core.network_validator import NetworkValidator
from core.schemas import Credentials
from pages.login_page import LoginPage


def _profile_present(user_data_dir: Path) -> bool:
    return user_data_dir.exists() and any(user_data_dir.iterdir())


def _logged_in(page) -> bool:
    try:
        page.get_by_role("link", name="My eBay").first.wait_for(
            state="visible", timeout=5000
        )
        return True
    except Exception:
        return False


def ensure_session(
    playwright: Playwright, user_data_dir: Path, launch_kwargs: dict
) -> None:
    if _profile_present(user_data_dir):
        ctx = playwright.chromium.launch_persistent_context(
            str(user_data_dir), **launch_kwargs
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(
                "https://www.ebay.com/", wait_until="domcontentloaded", timeout=15000
            )
            if _logged_in(page):
                return
        finally:
            ctx.close()

    creds = Credentials.from_env()
    user_data_dir.mkdir(exist_ok=True)
    ctx = playwright.chromium.launch_persistent_context(
        str(user_data_dir), **launch_kwargs
    )
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        validator = NetworkValidator(page)

        with validator.expect_ok(r"www\.ebay\.com/?($|\?)", method="GET"):
            page.goto("https://www.ebay.com/", wait_until="domcontentloaded")

        login = LoginPage(page, validator)
        (
            login
            .goto()
            .submit_username(creds.user)
            .submit_password(creds.password.get_secret_value())
            .skip_interstitials()
        )

        with validator.expect_ok(r"www\.ebay\.com/?($|\?)", method="GET"):
            page.goto("https://www.ebay.com/", wait_until="domcontentloaded")
        if not _logged_in(page):
            raise RuntimeError(
                "Auto-login completed but 'My eBay' link not visible — "
                "session likely blocked by extra-step verification. "
                "Fall back to: python save_auth.py"
            )
    finally:
        ctx.close()
