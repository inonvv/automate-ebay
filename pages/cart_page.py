import re

import allure

from pages.base_page import BasePage
from utils.url import is_captcha_url, is_live_cart_url


class CartPage(BasePage):
    URL = "https://cart.ebay.com/"

    @allure.step("Open cart page")
    def goto(self) -> "CartPage":
        def _nav():
            try:
                self.page.goto(self.URL, wait_until="commit")
            except Exception as e:
                if "ERR_ABORTED" not in str(e):
                    raise
        if self.validator:
            with self.validator.expect_ok(r"cart\.ebay\.com/(?!sc/)", method="GET"):
                _nav()
        else:
            _nav()
        try:
            self.page.wait_for_url(is_live_cart_url, timeout=30000)
        except Exception:
            if is_captcha_url(self.page.url):
                raise RuntimeError(
                    f"eBay served splashui — wait several minutes and re-run; URL: {self.page.url}"
                )
            raise
        self.page.wait_for_load_state("domcontentloaded", timeout=20000)
        return self

    @allure.step("Clear cart")
    def clear(self) -> "CartPage":
        self.goto()
        for _ in range(20):
            btn = self.page.locator(
                'button[aria-label*="Remove"], button:has-text("Remove")'
            ).first
            if not btn.count() or not btn.is_visible():
                break
            btn.click()
            self.page.wait_for_load_state("domcontentloaded")
        remaining = self.page.locator(
            'button[aria-label*="Remove"], button:has-text("Remove")'
        ).count()
        if remaining:
            raise AssertionError(
                f"Cart not fully cleared after 20 attempts; {remaining} Remove buttons still visible"
            )
        return self

    @allure.step("Read cart subtotal text")
    def get_total_text(self) -> str:
        candidates = [
            '[data-test-id="SUBTOTAL"]',
            '[data-testid="SUBTOTAL"]',
            '[data-test-id="cart-subtotal-amount"]',
            '[data-testid="cart-subtotal-amount"]',
            '[aria-label*="ubtotal"]',
        ]
        for sel in candidates:
            loc = self.page.locator(sel).first
            if loc.count():
                text = (loc.text_content() or "").strip()
                if text:
                    return text
        money_re = re.compile(
            r"(?:US\s*)?\$\s*[\d,]+(?:\.\d+)?"
            r"|ILS\s*[\d,]+(?:\.\d+)?"
            r"|EUR\s*[\d,]+(?:\.\d+)?"
            r"|€\s*[\d,]+(?:\.\d+)?"
            r"|£\s*[\d,]+(?:\.\d+)?"
        )
        label = self.page.get_by_text(re.compile(r"\bSubtotal\b", re.I)).first
        if label.count():
            for ancestor in (label, label.locator("xpath=.."), label.locator("xpath=../..")):
                if ancestor.count():
                    text = (ancestor.text_content() or "").strip()
                    m = money_re.search(text)
                    if m:
                        return m.group(0).strip()
        raise RuntimeError(
            "Cart subtotal not found — selector may have rotated; dispatch selector-scout"
        )
