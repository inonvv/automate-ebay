# eBay E2E Automation Drill

Playwright (Python) + pytest E2E suite against eBay. Page Object Model, data-driven scenarios, Allure reporting.

## Prerequisites

- Python 3.10+
- Google Chrome installed natively
- Allure CLI (`scoop install allure` / `brew install allure`)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env        # then paste credentials into .env
```

## First Run — Login

Auto-login boots from `.env` on the first test run; session is then reused from `.user-data/` (gitignored). If 2FA or CAPTCHA blocks the auto path, fall back to:

```bash
python save_auth.py
```

Browse for 20-30s, sign in, solve CAPTCHA, press Enter.

## Run Tests

```bash
pytest -q
allure serve allure-results
```

Each scenario in `data/test_data.json` runs as a parametrized test.

---

## Architecture

- **POM** — `pages/base_page.py:6`. 5 pages: `SearchPage` (homepage + search → results), `ResultsPage` (max-price filter, URL collection, pagination), `ItemPage` (3 variant-pick strategies, multi-candidate ATC retry), `CartPage` (clear + read subtotal), `LoginPage` (user → pass → skip 2FA).
- **Orchestration** — `core/ebay_actions.py:13`. `EbayActions` exposes the 4 spec functions: `login`, `search_items_by_name_under_price`, `add_items_to_cart`, `assert_cart_total_not_exceeds`.
- **Auth bootstrap** — `core/auth.py:37` reuses persistent profile or auto-logs in. Manual fallback at `save_auth.py:27`.
- **Network validator** — `core/network_validator.py:25` wraps actions with `expect_ok()` so silent 4xx/5xx/empty responses fail loud. Per-test traffic attached to Allure.
- **Validation** — `core/schemas.py` (pydantic): `SearchInput`, `Money`, `Credentials`.
- **Utils** — `utils/money.py` (price text → `Money(amount, currency)`), `utils/url.py` (captcha detect, item-id extract, canonicalize).
- **Data-driven** — `data/test_data.json` (4 scenarios) parametrized at `conftest.py:26`. Single E2E in `tests/test_e2e_shopping.py:4`.
- **Fixtures** — session bootstrap, context, page, validator, cart-clear before each test, screenshot + traffic on end.
- **Reports** — Allure via `pytest.ini`; `@allure.step` throughout; screenshots on failure + key actions.

## Gaps

- **Per-item price verify** — spec says "XPath items whose price ≤ max"; `results_page.py:41` collects URLs only.
- **No min-price filter** — only max is wired (`results_page.py:17`); JSON has no `minPrice`.
- **Quantity variant** — intentionally skipped (`item_page.py:137`); random qty would blow the budget.
- **No "return to search"** — `ebay_actions.py:54` jumps straight to next URL.
- **No CI / headless** — `conftest.py:18` hardcodes `headless=False` (anti-bot).
- **Allure only** — no JUnit/HTML fallback (spec asks for one, so OK).
- **No FX** — currency detected, never converted; mismatches reject by design.

## Limitations / assumptions

- **First-run login is manual-ish.** Akamai flags cold-profile `/signin/`; need 20–30s of homepage browsing first. Reused from `.user-data/` after.
- **Strict currency.** Cart currency must match scenario; otherwise loud raise (`ebay_actions.py:97`). Set account country = US to match JSON.
- **Headless off** for lower anti-bot score.
- **Cart-clear best-effort** — autouse fixture catches and logs, doesn't raise.
- **Variant pick excludes quantity** (intentional).
- **Partial fills allowed** — per-URL failures skip; only 0/N raises. Threshold uses intended `len(urls)`, so partial fills only loosen the check.
- **Profile per xdist worker** (`.user-data-N/`); each needs its own login.
- **Subtotal, not grand total** — items only; shipping/tax appear at checkout.
- **Auth fallback:** empty profile → auto-login → on 2FA/captcha → `save_auth.py`.
