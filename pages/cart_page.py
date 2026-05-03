import re
from urllib.parse import urlparse

import allure

from pages.base_page import BasePage, is_captcha_url


def _is_live_cart_url(u: str) -> bool:
    """Path-segment-aware check for the live-cart view (excludes Saved Cart `/sc/...`)."""
    parsed = urlparse(u)
    if not (
        parsed.netloc.endswith("cart.ebay.com")
        or parsed.netloc.endswith("cart.payments.ebay.com")
    ):
        return False
    if re.match(r"/sc(/|$)", parsed.path):
        return False
    return parsed.path == "/" or parsed.path.startswith("/cart")


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
            self.page.wait_for_url(_is_live_cart_url, timeout=30000)
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

    @staticmethod
    def parse_total(text: str) -> float:
        """Parse a money string into a float.

        Locale heuristic — assumes one of:
          - US/UK: ``$220.00`` or ``£220.00`` — comma is thousands, dot is decimal.
          - EU: ``€220,00`` — comma is decimal when followed by exactly 2 digits.
          - Mixed: ``1.234,56`` (EU thousands+decimal) — last separator wins.
        Refuses ranges (``$220 to $250``) loudly rather than silently picking the lower bound.
        """
        tokens = re.findall(r"\d[\d.,]*", text)
        if len(tokens) > 1 or " to " in text.lower():
            raise ValueError(f"Cart total looks like a range, refusing to guess: {text!r}")
        if not tokens:
            raise ValueError(f"No numeric token in cart total text: {text!r}")
        digits = tokens[0]
        if "." in digits and "," in digits:
            if digits.rfind(".") > digits.rfind(","):
                digits = digits.replace(",", "")
            else:
                digits = digits.replace(".", "").replace(",", ".")
        elif "," in digits:
            if len(digits.rsplit(",", 1)[-1]) == 2:
                digits = digits.replace(",", ".")
            else:
                digits = digits.replace(",", "")
        return float(digits)
