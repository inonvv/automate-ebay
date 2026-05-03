"""The four spec functions, wrapped on a Page. Thin orchestration over POM."""
import allure
from playwright.sync_api import Page

from core.network_validator import NetworkValidator
from pages.cart_page import CartPage
from pages.item_page import ItemPage
from pages.search_page import SearchPage


class EbayActions:
    def __init__(self, page: Page, validator: NetworkValidator | None = None):
        self.page = page
        self.validator = validator or NetworkValidator(page)
        page._validator = self.validator

    @allure.step("Verify eBay session")
    def login(self) -> None:
        self.page.goto(
            "https://www.ebay.com/", wait_until="domcontentloaded", timeout=15000
        )
        try:
            self.page.get_by_role("link", name="My eBay").first.wait_for(
                state="visible", timeout=5000
            )
        except Exception:
            raise RuntimeError(
                "eBay session expired or missing. Re-run: python save_auth.py"
            )

    @allure.step("Search '{query}' under {max_price} (limit {limit})")
    def search_items_by_name_under_price(
        self, query: str, max_price: float, limit: int = 5
    ) -> list[str]:
        results = SearchPage(self.page, self.validator).goto().search(query).apply_price_filter(max_price)
        urls: list[str] = []
        while len(urls) < limit:
            urls.extend(results.collect_item_urls(limit - len(urls)))
            if len(urls) >= limit or not results.next_page():
                break
        return urls[:limit]

    @allure.step("Add items to cart")
    def add_items_to_cart(self, urls: list[str]) -> int:
        added = 0
        error_types: list[str] = []
        for idx, url in enumerate(urls):
            if idx > 0:
                # Pace between items: let the previous page settle so eBay's anti-bot
                # rate heuristic doesn't trip. networkidle is the real signal, not a
                # hardcoded sleep.
                try:
                    self.page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
            try:
                ItemPage(self.page, self.validator).goto(url).pick_random_variants().add_to_cart()
                added += 1
            except Exception as e:
                error_types.append(type(e).__name__)
                print(f"[skip] {url}: {type(e).__name__}: {str(e)[:200]}", flush=True)
                allure.attach(
                    f"Skipped {url}: {type(e).__name__}: {e}",
                    name="skip-item",
                    attachment_type=allure.attachment_type.TEXT,
                )
        if urls and added == 0:
            raise RuntimeError(
                f"Systemic add-to-cart failure: 0/{len(urls)} added; error types={set(error_types)}"
            )
        return added

    @allure.step("Assert cart total <= {budget_per_item} x {items_count}")
    def assert_cart_total_not_exceeds(self, budget_per_item: float, items_count: int) -> None:
        cart = CartPage(self.page, self.validator).goto()
        threshold = budget_per_item * items_count
        raw = cart.get_total_text()
        actual = CartPage.parse_total(raw)
        allure.attach(
            f"raw={raw!r} parsed={actual} threshold={threshold}",
            name="cart-total-check",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            cart.screenshot(),
            name="cart-page",
            attachment_type=allure.attachment_type.PNG,
        )
        assert actual <= threshold, (
            f"Cart total {actual} exceeds threshold {threshold} (raw: {raw!r})"
        )
