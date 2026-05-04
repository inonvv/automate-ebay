# eBay E2E Automation Drill

Playwright (Python) + pytest E2E suite against eBay. Page Object Model, data-driven scenarios, Allure reporting.

## Prerequisites

Python 3.10+ · Chrome · Git · Allure CLI (`scoop install allure` / `brew install allure`)

## Steps

1. Get creds from instructor (`EBAY_USER`, `EBAY_PASS`).
2. Clone
   ```bash
   git clone <repo-url>
   cd Automate-Ebay
   ```
3. Venv + install
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   playwright install chromium
   ```
4. Configure
   ```bash
   copy .env.example .env
   ```
   Paste `EBAY_USER` / `EBAY_PASS` into `.env`.
5. First-run login (one time)
   ```bash
   python save_auth.py
   ```
   Browse 20–30s → Sign In → tick "Keep me signed in" → press Enter in terminal.
6. Run tests
   ```bash
   pytest -q
   ```
7. Allure report
   ```bash
   allure serve allure-results
   ```

## Common issues

- **No saved session** → redo step 5.
- **Currency mismatch** → set eBay account country to US, or edit `currency` in `data/test_data.json`.
- **Captcha during tests** → wait a few minutes, retry.

---

## Architecture

- **POM** — `pages/base_page.py:6`. 5 pages: `SearchPage` (`search_page.py:7`), `ResultsPage` (`results_page.py:13` — max-price filter, row-level price verify, pagination), `ItemPage` (`item_page.py:16` — 3 variant-pick strategies, multi-candidate ATC retry), `CartPage` (`cart_page.py:10` — clear + read subtotal), `LoginPage` (`login_page.py:14` — user → pass → skip 2FA).
- **Orchestration** — `core/ebay_actions.py:13`. `EbayActions` exposes the 4 spec functions: `login`, `search_items_by_name_under_price`, `add_items_to_cart`, `assert_cart_total_not_exceeds`.
- **Auth bootstrap** — `core/auth.py:37` reuses persistent profile or auto-logs in. Manual fallback at `save_auth.py:27`.
- **Network validator** — `core/network_validator.py:25` wraps actions with `expect_ok()` so silent 4xx/5xx/empty responses fail loud. Per-test traffic attached to Allure.
- **Validation** — `core/schemas.py` (pydantic): `SearchInput`, `Money`, `Credentials`.
- **Utils** — `utils/money.py` (price text → `Money(amount, currency)`), `utils/url.py` (captcha detect, item-id extract, canonicalize).
- **Data-driven** — `data/test_data.json` (4 scenarios) parametrized at `conftest.py:26`. Single E2E in `tests/test_e2e_shopping.py:4`.
- **Fixtures** — session bootstrap, context, page, validator, cart-clear before each test, screenshot + traffic on end.
- **Reports** — Allure via `pytest.ini`; `@allure.step` throughout; screenshots on failure + key actions.

## Gaps

- **No min-price filter** — only max is wired (`results_page.py:21`); JSON has no `minPrice`.
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
- **Subtotal, not grand total** (`cart_page.py:84`) — items only; shipping/tax appear at checkout.
- **Auth fallback:** empty profile → auto-login → on 2FA/captcha → `save_auth.py`.
