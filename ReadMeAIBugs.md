# AI-Generated Code — Bug Review

## Three major problems

1. **Mixed frameworks.** `from selenium import webdriver` is imported but never used. You don't mix Playwright with Selenium in the same test.
2. **No assertions.** `results = page.locator(".result-item")` just stores a locator; nothing is checked.
3. **Playwright never stopped → leak.** `sync_playwright().start()` is called but `.stop()` is never called. `browser.close()` closes the browser, not the Playwright process. No `with sync_playwright() as p:` block, no `try/finally`.

## Minor problems

- `time.sleep(2)` and `time.sleep(3)` — hard waits. Playwright auto-waits; use `wait_for_selector` / `wait_for_load_state` if needed.
- Brittle selectors (`#search`, `.button`, `.result-item`) — too generic. Prefer `get_by_role`, `get_by_test_id`.
- `example.com` doesn't have any of those elements — `fill` will time out and crash.
- No `try/finally` — if anything raises mid-test, the browser stays open and leaks.
- `results` is assigned and never read — dead code.
- Named `test_*` but uses no pytest fixtures, no teardown, no parametrization. Looks like pytest but isn't structured as one.
- `browser.new_page()` skips creating a context explicitly — works, but contexts let you isolate cookies/storage between tests.
