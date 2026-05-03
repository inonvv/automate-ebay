# eBay E2E Automation Drill

End-to-end test suite against eBay using Playwright (Python) with POM, OOP, and data-driven inputs. Verifies: search with price filter → add items to cart → assert cart total within budget threshold. Use pydantic, intercept API request when in need,Robustness & Smart Locator 

---

## Prerequisites

- **Python 3.10 or newer**
- **Google Chrome** installed natively (the suite uses your real Chrome, not Playwright's bundled Chromium)
- **Allure CLI** for viewing reports — install via `scoop install allure` (Windows), `brew install allure` (macOS), or [download from GitHub](https://github.com/allure-framework/allure2/releases)
- **Git** to clone the repo

---

## One-Time Setup

```bash
git clone <repo-url> ebay-automation
cd ebay-automation

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
playwright install chromium
```

---

## Credentials

eBay credentials for the test account are sent **separately by email**.

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env        # Windows
   # cp .env.example .env        # macOS/Linux
   ```
2. Open `.env` and paste the credentials you received into the empty fields.
3. Save the file. `.env` is gitignored — it will not be committed.

---

## First Run — Manual Login Flow

eBay's bot detection makes scripted login impractical. The suite uses a **persistent browser profile** instead: you log in manually once, the session is saved to disk, and tests reuse it for weeks.

```bash
python save_auth.py
```

This opens a real Chrome window at `ebay.com`. **Follow these steps in order:**

1. **Browse for 20–30 seconds before signing in.** Scroll, hover a category, click into a product, scroll the results, go back. This lets eBay's risk-scoring see organic activity before authentication — direct cold navigation to `/signin/` is itself a bot signal.
2. **Click "Sign In"** at the top of the page.
3. **Enter the credentials from `.env`** (or copy-paste them in).
4. **Tick "Keep me signed in"** if shown (doubles cookie lifetime). If not shown, ignore — eBay sometimes hides it.
5. **Solve any CAPTCHA or 2-step verification** if presented. If 2SV asks to set up a method, click "Not now."
6. **Verify you're logged in** — the homepage should show your account name top-right.
7. **Return to the terminal and press Enter.** The script saves the session to `.user-data/` and exits.

`.user-data/` is gitignored. It contains cookies, localStorage, and browser fingerprint state. Treat it like a credential.

---

## Running Tests

```bash
pytest -q
```

Each scenario in `data/test_data.json` runs as a parametrized test. Expected output: a mix of passes and failures (see `docs/findings.md` for why some scenarios are designed to fail — they exercise the threshold boundary).

---

## Viewing the Allure Report

After the test run completes:

```bash
allure serve allure-results
```

A browser opens automatically with the interactive report. The report includes:

- Per-step breakdown (search, filter, add-to-cart, assert)
- Screenshots for every cart-add and the final cart page
- Network traffic log per test
- Failure screenshots when assertions break

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `pytest.exit: No saved session at .user-data/` | First run, no profile yet | Run `python save_auth.py` |
| `pytest.exit: eBay session expired` | Profile aged out | Re-run `python save_auth.py` |
| Tests fail with "splashui" in error | eBay served a CAPTCHA mid-test | Wait 10–15 minutes, run again |
| `Cart subtotal not found` | eBay rotated cart selectors | Inspect cart manually, file an issue |
| `parse_total: looks like a range` | Cart subtotal showed `$X to $Y` | Investigate — shouldn't happen for a normal cart |

---

## Project Structure

```
.
├── README.md                    # this file
├── requirements.txt
├── pytest.ini
├── .env.example                 # template for credentials
├── .gitignore
├── save_auth.py                 # one-time manual login → .user-data/
├── conftest.py                  # pytest fixtures, session validation, screenshot hooks
├── data/
│   └── test_data.json           # parametrized test scenarios
├── core/
│   ├── ebay_actions.py          # the 4 spec functions (login, search, add, assert)
│   └── network_validator.py     # per-step API call validation
├── pages/                       # Page Object Model
│   ├── base_page.py
│   ├── search_page.py
│   ├── results_page.py
│   ├── item_page.py
│   └── cart_page.py
├── tests/
│   └── test_e2e_shopping.py     # the parametrized E2E test
└── docs/
    ├── spec.md                  # the original drill specification
    ├── findings.md              # observations from test runs (incl. why some fail by design)
    └── ReadMeAIBugs.md          # static review of AI-generated buggy sample code
```

---

## What's Intentionally Not Done

- **Automated login form fill** — would trip eBay's bot detection. Manual login + persistent profile is the documented approach.
- **Anti-detection libraries** (playwright-stealth, proxy rotation, fingerprint spoofing) — out of scope and against the spirit of the drill.
- **Multiple reporting tools** — spec allowed Extent/Allure/ReportPortal; Allure was chosen for its pytest integration. Adding others would be redundant.
- **Mocked tests** — the suite hits live eBay. Replay/mock mode is documented in `docs/TODO.md` as a future direction.

---

## Author Notes

The suite was designed under the principle that a passing test should pass for the right reasons. Several scenarios in `data/test_data.json` are intentionally crafted so the data-driven structure surfaces the assertion's actual behavior (vs. always passing, which would prove nothing). See `docs/findings.md`.
