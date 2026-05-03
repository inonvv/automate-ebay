"""Per-step network validation: assert a matching request fired and a 2xx response returned.

Pages wrap each network-firing action in `with validator.expect_ok(...):` so that
silent regressions (filter not applied, 4xx from cart API, redirect to a soft-block
page) surface as test failures with Allure attachments instead of slipping through.

Why a thin facade over Playwright's `page.expect_response`:
- Centralised request-payload checks (query-string keys, post-data substrings).
- Centralised response coherence checks (status range, JSON keys).
- Background subscription to every response builds a per-test traffic log
  attached to Allure on teardown — invaluable when a step times out and you
  need to know what the page actually fetched.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Iterable, Iterator
from urllib.parse import parse_qs, urlparse

import allure
from playwright.sync_api import Page, Response


class NetworkValidator:
    def __init__(self, page: Page):
        self.page = page
        self._log: list[tuple[str, str, int]] = []
        page.on("response", self._record)

    def _record(self, resp: Response) -> None:
        try:
            self._log.append((resp.request.method, resp.url, resp.status))
        except Exception:
            pass

    @contextmanager
    def expect_ok(
        self,
        url_pattern: str,
        *,
        method: str | None = None,
        query_params: dict[str, str] | None = None,
        post_contains: str | None = None,
        json_contains: Iterable[str] | None = None,
        timeout: int = 20000,
    ) -> Iterator[None]:
        regex = re.compile(url_pattern)

        def matches(r: Response) -> bool:
            if not regex.search(r.url):
                return False
            if method and r.request.method != method.upper():
                return False
            return True

        with self.page.expect_response(matches, timeout=timeout) as info:
            yield
        resp = info.value
        req = resp.request
        problems: list[str] = []

        if not (200 <= resp.status < 400):
            problems.append(f"status {resp.status} not in 2xx/3xx")

        if query_params:
            qs = parse_qs(urlparse(req.url).query)
            for k, expected in query_params.items():
                actual = qs.get(k, [None])[0]
                if actual != expected:
                    problems.append(f"query[{k}]={actual!r} expected {expected!r}")

        if post_contains:
            body = req.post_data or ""
            if post_contains not in body:
                problems.append(f"post body missing {post_contains!r}")

        if json_contains:
            try:
                body = resp.json()
            except Exception as e:
                problems.append(f"response not JSON-parseable: {e}")
            else:
                for k in json_contains:
                    if k not in body:
                        problems.append(f"json missing key {k!r}")

        summary = f"{req.method} {resp.url} -> {resp.status}"
        if problems:
            allure.attach(
                summary + "\n" + "\n".join(problems),
                name="network-validation-failed",
                attachment_type=allure.attachment_type.TEXT,
            )
            raise AssertionError(f"Network validation failed: {summary} :: " + "; ".join(problems))
        allure.attach(
            summary,
            name="network-validation-ok",
            attachment_type=allure.attachment_type.TEXT,
        )

    def attach_traffic_log(self) -> None:
        if not self._log:
            return
        rows = [f"{m:6s} {s:3d}  {u}" for m, u, s in self._log]
        allure.attach(
            "\n".join(rows[-200:]),
            name="network-traffic",
            attachment_type=allure.attachment_type.TEXT,
        )
