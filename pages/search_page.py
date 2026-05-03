import allure

from pages.base_page import BasePage
from pages.results_page import ResultsPage


class SearchPage(BasePage):
    URL = "https://www.ebay.com/"

    @allure.step("Open eBay homepage")
    def goto(self) -> "SearchPage":
        self.page.goto(self.URL, wait_until="domcontentloaded")
        return self

    @allure.step("Search for '{query}'")
    def search(self, query: str) -> ResultsPage:
        box = self.page.get_by_role("combobox", name="Search for anything")
        box.fill(query)
        if self.validator:
            with self.validator.expect_ok(
                r"/sch/i\.html",
                method="GET",
                query_params={"_nkw": query},
            ):
                box.press("Enter")
        else:
            box.press("Enter")
        self.page.wait_for_load_state("domcontentloaded")
        return ResultsPage(self.page, self.validator)
