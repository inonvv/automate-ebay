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

## First Run — Manual Login

eBay's bot detection makes scripted login impractical. The suite uses a persistent profile: log in once, the session is reused.

```bash
python save_auth.py
```

Browse for 20-30 seconds, click Sign In, enter credentials, solve any CAPTCHA, then return to the terminal and press Enter. Session is saved to `.user-data/` (gitignored).

## Run Tests

```bash
pytest -q
```

Each scenario in `data/test_data.json` runs as a parametrized test. Some scenarios pass, some fail by design — the data-driven structure exercises the threshold boundary.

## Allure Report

```bash
allure serve allure-results
```

## Project Structure

```
core/      EbayActions (4 spec functions) + NetworkValidator
pages/     POM (search, results, item, cart)
utils/     pure helpers (url, money)
tests/     parametrized E2E test
data/      scenario JSON
```
