import re
from urllib.parse import urljoin

import allure
from playwright.sync_api import Page

from core.network_validator import NetworkValidator
from pages.base_page import BasePage

_ITEM_URL_RE = re.compile(r"^https?://(?:www\.)?ebay\.com/itm/(\d{11,13})(?:[/?]|$)")


class ResultsPage(BasePage):
    def __init__(self, page: Page, validator: NetworkValidator | None = None):
        super().__init__(page, validator)
        self._seen: set[str] = set()

    @allure.step("Apply max price filter: {max_price}")
    def apply_price_filter(self, max_price: float) -> "ResultsPage":
        max_input = self.page.locator('input[aria-label^="Maximum Value"]').first
        max_input.scroll_into_view_if_needed()
        max_input.fill(str(max_price))
        if self.validator:
            with self.validator.expect_ok(
                r"/sch/i\.html.*_udhi=",
                method="GET",
                query_params={"_udhi": str(int(max_price)) if max_price == int(max_price) else str(max_price)},
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

    @allure.step("Collect up to {limit} item URLs from current results page")
    def collect_item_urls(self, limit: int) -> list[str]:
        urls: list[str] = []
        for link in self.page.locator('xpath=//a[contains(@href, "/itm/")]').all():
            href = link.get_attribute("href")
            if not href:
                continue
            absolute = urljoin(self.page.url, href).split("?")[0].split("#")[0]
            m = _ITEM_URL_RE.match(absolute)
            if not m:
                continue
            canonical = f"https://www.ebay.com/itm/{m.group(1)}"
            if canonical in self._seen:
                continue
            self._seen.add(canonical)
            urls.append(canonical)
            if len(urls) >= limit:
                break
        return urls

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
