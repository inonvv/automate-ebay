import json
import os
from pathlib import Path

import allure
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Playwright

from core.ebay_actions import EbayActions
from core.network_validator import NetworkValidator

load_dotenv()

_worker = os.environ.get("PYTEST_XDIST_WORKER", "")
USER_DATA_DIR = Path(f".user-data{('-' + _worker) if _worker else ''}")
LAUNCH_KWARGS = {
    "headless": False,
    "channel": "chrome",
    "args": ["--disable-blink-features=AutomationControlled"],
}

_DATA_FILE = Path(__file__).parent / "data" / "test_data.json"


def pytest_generate_tests(metafunc):
    if "scenario" in metafunc.fixturenames:
        scenarios = json.loads(_DATA_FILE.read_text())
        metafunc.parametrize("scenario", scenarios, ids=lambda s: s["query"])


@pytest.fixture(scope="session")
def test_data():
    return json.loads(_DATA_FILE.read_text())


@pytest.fixture(scope="session", autouse=True)
def _verify_session(playwright: Playwright):
    print("\n[verify_session] fixture entered", flush=True)
    if not USER_DATA_DIR.exists():
        pytest.exit(
            f"No saved session at {USER_DATA_DIR}/ — run: python save_auth.py",
            returncode=2,
        )
    ctx = playwright.chromium.launch_persistent_context(
        str(USER_DATA_DIR), **LAUNCH_KWARGS
    )
    try:
        p = ctx.new_page()
        try:
            EbayActions(p).login()
        except RuntimeError as e:
            pytest.exit(str(e), returncode=2)
    finally:
        ctx.close()


@pytest.fixture
def context(playwright: Playwright):
    ctx = playwright.chromium.launch_persistent_context(
        str(USER_DATA_DIR), **LAUNCH_KWARGS
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    return context.pages[0] if context.pages else context.new_page()


@pytest.fixture
def validator(page) -> NetworkValidator:
    return NetworkValidator(page)


@pytest.fixture(autouse=True)
def _clear_cart_before(page):
    from pages.cart_page import CartPage
    try:
        CartPage(page).clear()
    except Exception as e:
        print(f"[clear_cart] skipped: {type(e).__name__}: {e}", flush=True)
    yield


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        page = item.funcargs.get("page")
        if page is not None:
            validator = item.funcargs.get("validator")
            if validator is not None:
                try:
                    validator.attach_traffic_log()
                except Exception:
                    pass
            if rep.failed:
                allure.attach(
                    page.screenshot(),
                    name="failure",
                    attachment_type=allure.attachment_type.PNG,
                )
