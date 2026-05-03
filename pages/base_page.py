from playwright.sync_api import Page

from core.network_validator import NetworkValidator


class BasePage:
    def __init__(self, page: Page, validator: NetworkValidator | None = None):
        self.page = page
        self.validator = validator

    def screenshot(self) -> bytes:
        return self.page.screenshot()
