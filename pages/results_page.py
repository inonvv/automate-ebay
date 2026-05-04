from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import allure
from playwright.sync_api import Page

from core.network_validator import NetworkValidator
from core.schemas import Currency
from pages.base_page import BasePage
from utils.money import parse_total
from utils.url import canonical_item_url


class ResultsPage(BasePage):
    def __init__(self, page: Page, validator: NetworkValidator | None = None):
        super().__init__(page, validator)
        self._seen: set[str] = set()
        self._max_price: float | None = None
        self._max_currency: Currency | None = None

    @allure.step("Apply max price filter: {max_price} {currency}")
    def apply_price_filter(self, max_price: float, currency: Currency = "USD") -> "ResultsPage":
        self._max_price = max_price
        self._max_currency = currency
        price_str = str(int(max_price)) if max_price == int(max_price) else str(max_price)
        max_input = self.page.locator('input[aria-label^="Maximum Value"]').first
        if max_input.count() == 0:
            # Spec says "if a price filter exists" — some categories don't render
            # the Maximum-Value input. Force the filter via URL query string instead.
            self._goto_with_udhi(price_str)
            return self
        max_input.scroll_into_view_if_needed()
        max_input.fill(price_str)
        if self.validator:
            with self.validator.expect_ok(
                r"/sch/i\.html.*_udhi=",
                method="GET",
                query_params={"_udhi": price_str},
            ):
                max_input.press("Enter")
        else:
            max_input.press("Enter")
        self.page.wait_for_load_state("domcontentloaded")
        try:
            self.page.wait_for_url(lambda u: "_udhi=" in u, timeout=10000)
        except Exception:
            raise RuntimeError(
                f"Price filter not reflected in URL after Enter; URL: {self.page.url}"
            )
        return self

    def _goto_with_udhi(self, price_str: str) -> None:
        parsed = urlparse(self.page.url)
        qs = dict(parse_qsl(parsed.query))
        qs["_udhi"] = price_str
        new_url = urlunparse(parsed._replace(query=urlencode(qs)))
        if self.validator:
            with self.validator.expect_ok(
                r"/sch/i\.html.*_udhi=",
                method="GET",
                query_params={"_udhi": price_str},
            ):
                self.page.goto(new_url, wait_until="domcontentloaded")
        else:
            self.page.goto(new_url, wait_until="domcontentloaded")

    @allure.step("Collect up to {limit} item URLs (verifying price <= max)")
    def collect_item_urls(self, limit: int) -> list[str]:
        urls: list[str] = []
        rows = self.page.locator(
            'xpath=//li[contains(@class, "s-item")] | //div[contains(@class, "s-card")]'
        ).all()
        if not rows:
            # Fallback: legacy structure or new card layout we don't recognise.
            # Walk anchor-by-anchor; skip price verification (no row context).
            return self._collect_unverified(limit)
        for row in rows:
            link = row.locator('xpath=.//a[contains(@href, "/itm/")]').first
            if not link.count():
                continue
            href = link.get_attribute("href")
            if not href:
                continue
            absolute = urljoin(self.page.url, href).split("?")[0].split("#")[0]
            canonical = canonical_item_url(absolute)
            if not canonical or canonical in self._seen:
                continue
            if not self._row_price_under_max(row):
                continue
            self._seen.add(canonical)
            urls.append(canonical)
            if len(urls) >= limit:
                break
        return urls

    def _collect_unverified(self, limit: int) -> list[str]:
        urls: list[str] = []
        for link in self.page.locator('xpath=//a[contains(@href, "/itm/")]').all():
            href = link.get_attribute("href")
            if not href:
                continue
            absolute = urljoin(self.page.url, href).split("?")[0].split("#")[0]
            canonical = canonical_item_url(absolute)
            if not canonical or canonical in self._seen:
                continue
            self._seen.add(canonical)
            urls.append(canonical)
            if len(urls) >= limit:
                break
        return urls

    def _row_price_under_max(self, row) -> bool:
        # Positive-drop: only exclude when we *confirm* the row exceeds max_price in
        # the same currency. If the price element is missing, the text is empty, the
        # parser refuses (range / no currency token), or the currency differs from
        # the scenario's, fall back on the server-side URL filter (already validated
        # by the network validator) and include the row.
        if self._max_price is None:
            return True
        price_locator = row.locator(
            '.s-item__price, [class*="s-item__price"], [data-testid*="price"], [class*="ITEM_CARD_PRICE"]'
        ).first
        if not price_locator.count():
            return True
        price_text = (price_locator.text_content() or "").strip()
        if not price_text:
            return True
        try:
            money = parse_total(price_text)
        except Exception:
            return True
        if self._max_currency is not None and money.currency != self._max_currency:
            return True
        return money.amount <= self._max_price

    @allure.step("Go to next results page")
    def next_page(self) -> bool:
        for sel in ('a[aria-label="Go to next search page"]', "a.pagination__next"):
            loc = self.page.locator(sel).first
            if loc.count() and loc.is_visible() and loc.is_enabled():
                if self.validator:
                    with self.validator.expect_ok(
                        r"/sch/i\.html.*_pgn=",
                        method="GET",
                    ):
                        loc.click()
                else:
                    loc.click()
                self.page.wait_for_load_state("domcontentloaded")
                return True
        return False
