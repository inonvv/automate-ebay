"""The four spec functions, wrapped on a Page. Thin orchestration over POM."""
import allure
from playwright.sync_api import Page

from core.network_validator import NetworkValidator
from core.schemas import SearchInput
from pages.cart_page import CartPage
from pages.item_page import ItemPage
from pages.search_page import SearchPage
from utils.money import parse_total


class EbayActions:
    def __init__(self, page: Page, validator: NetworkValidator | None = None):
        self.page = page
        self.validator = validator or NetworkValidator(page)

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

    @allure.step("Search '{query}' under {max_price} {currency} (limit {limit})")
    def search_items_by_name_under_price(
        self, query: str, max_price: float, limit: int = 5, currency: str = "USD"
    ) -> list[str]:
        params = SearchInput(query=query, max_price=max_price, limit=limit, currency=currency)
        results = (
            SearchPage(self.page, self.validator)
            .goto()
            .search(params.query)
            .apply_price_filter(params.max_price, params.currency)
        )
        urls: list[str] = []
        while len(urls) < params.limit:
            urls.extend(results.collect_item_urls(params.limit - len(urls)))
            if len(urls) >= params.limit or not results.next_page():
                break
        return urls[: params.limit]

    @allure.step("Add items to cart")
    def add_items_to_cart(self, urls: list[str]) -> None:
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

    @allure.step("Assert cart total <= {budget_per_item} {currency} x {items_count}")
    def assert_cart_total_not_exceeds(
        self, budget_per_item: float, items_count: int, currency: str
    ) -> None:
        cart = CartPage(self.page, self.validator).goto()
        threshold = budget_per_item * items_count
        raw = cart.get_total_text()
        money = parse_total(raw)
        allure.attach(
            f"raw={raw!r} parsed={money} threshold={threshold} {currency}",
            name="cart-total-check",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            cart.screenshot(),
            name="cart-page",
            attachment_type=allure.attachment_type.PNG,
        )
        assert money.currency == currency, (
            f"Currency mismatch: cart={money.currency!r}, scenario expects {currency!r} — "
            f"set eBay locale to match scenario or update test_data currency (raw: {raw!r})"
        )
        assert money.amount <= threshold, (
            f"Cart total {money.amount} {money.currency} exceeds threshold {threshold} {currency} (raw: {raw!r})"
        )
