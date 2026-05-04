"""eBay sign-in POM. Each atomic step is wrapped in `validator.expect_ok(...)`
so a missed network call (form not actually submitting, redirect to splashui,
4xx from the auth endpoint) surfaces as a clear failure instead of a silent
selector hang.
"""
import re

import allure

from pages.base_page import BasePage
from utils.url import is_captcha_url


class LoginPage(BasePage):
    SIGNIN_URL = "https://signin.ebay.com/signin"

    @allure.step("Open sign-in page")
    def goto(self) -> "LoginPage":
        if self.validator:
            with self.validator.expect_ok(r"signin\.ebay\.com/", method="GET"):
                self.page.goto(self.SIGNIN_URL, wait_until="domcontentloaded")
        else:
            self.page.goto(self.SIGNIN_URL, wait_until="domcontentloaded")
        if is_captcha_url(self.page.url):
            raise RuntimeError(
                f"eBay served splashui on sign-in — fall back to manual save_auth.py; URL: {self.page.url}"
            )
        return self

    @allure.step("Submit username")
    def submit_username(self, user: str) -> "LoginPage":
        field = self.page.locator("#userid")
        field.wait_for(state="visible", timeout=10000)
        field.fill(user)
        cont = self.page.locator(
            "#signin-continue-btn, button[type='submit']:has-text('Continue'), input[type='submit']"
        ).first
        if self.validator:
            with self.validator.expect_ok(r"signin\.ebay\.com/(signin|ws)"):
                cont.click()
        else:
            cont.click()
        self.page.wait_for_load_state("domcontentloaded")
        if is_captcha_url(self.page.url):
            raise RuntimeError(
                f"eBay served splashui after username — fall back to manual save_auth.py; URL: {self.page.url}"
            )
        return self

    @allure.step("Submit password")
    def submit_password(self, password: str) -> "LoginPage":
        field = self.page.locator("#pass")
        field.wait_for(state="visible", timeout=10000)
        field.fill(password)
        try:
            keep = self.page.locator("#keepMeSignInOption, input[name='keepmesignin']").first
            if keep.count() and not keep.is_checked():
                keep.check()
        except Exception:
            pass
        submit = self.page.locator(
            "#sgnBt, button[type='submit']:has-text('Sign in'), input[type='submit']"
        ).first
        if self.validator:
            with self.validator.expect_ok(r"signin\.ebay\.com|ebay\.com/$|ebay\.com/\?"):
                submit.click()
        else:
            submit.click()
        self.page.wait_for_load_state("domcontentloaded")
        if is_captcha_url(self.page.url):
            raise RuntimeError(
                f"eBay served splashui after password — fall back to manual save_auth.py; URL: {self.page.url}"
            )
        return self

    @allure.step("Skip post-login interstitials (extra-step / 2FA prompts)")
    def skip_interstitials(self) -> "LoginPage":
        labels = ("Not now", "Skip", "Maybe later", "No thanks", "Remind me later")
        for _ in range(3):
            clicked = False
            for label in labels:
                btn = self.page.get_by_role(
                    "button", name=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)
                ).first
                if btn.count() and btn.is_visible():
                    try:
                        btn.click(timeout=2000)
                        self.page.wait_for_load_state("domcontentloaded")
                        clicked = True
                        break
                    except Exception:
                        continue
                link = self.page.get_by_role(
                    "link", name=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)
                ).first
                if link.count() and link.is_visible():
                    try:
                        link.click(timeout=2000)
                        self.page.wait_for_load_state("domcontentloaded")
                        clicked = True
                        break
                    except Exception:
                        continue
            if not clicked:
                break
        return self
