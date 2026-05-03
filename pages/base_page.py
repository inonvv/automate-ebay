import re

from playwright.sync_api import Page

from core.network_validator import NetworkValidator

_CAPTCHA_RE = re.compile(r"/splashui/(captcha|challenge)\b", re.I)


def is_captcha_url(url: str) -> bool:
    """eBay's anti-bot redirects to /splashui/captcha or /splashui/challenge."""
    return bool(_CAPTCHA_RE.search(url or ""))


class BasePage:
    def __init__(self, page: Page, validator: NetworkValidator | None = None):
        self.page = page
        self.validator = validator

    def screenshot(self) -> bytes:
        return self.page.screenshot()
