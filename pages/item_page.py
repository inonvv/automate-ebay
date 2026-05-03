import random
import re

import allure

from pages.base_page import BasePage, is_captcha_url


class ItemPage(BasePage):
    @allure.step("Open item page: {url}")
    def goto(self, url: str) -> "ItemPage":
        m = re.search(r"/itm/(?:[^/]+/)?(\d+)", url)
        self._source_iid = m.group(1) if m else None
        if self.validator:
            with self.validator.expect_ok(r"/itm/", method="GET"):
                try:
                    self.page.goto(url, wait_until="commit")
                except Exception as e:
                    if "ERR_ABORTED" not in str(e):
                        raise
        else:
            try:
                self.page.goto(url, wait_until="commit")
            except Exception as e:
                if "ERR_ABORTED" not in str(e):
                    raise
        self.page.wait_for_load_state("domcontentloaded", timeout=20000)
        if is_captcha_url(self.page.url):
            raise RuntimeError(
                f"eBay served splashui — wait several minutes and re-run; URL: {self.page.url}"
            )
        if "/itm/" not in self.page.url:
            raise RuntimeError(f"Expected item page after goto, got {self.page.url}")
        return self

    @allure.step("Pick random variants")
    def pick_random_variants(self) -> "ItemPage":
        picks: list[str] = []

        # Strategy A: eBay's listbox-button variant widget (e.g. "Colour: Select" + chevron).
        # Filter to buttons whose label starts with a known variant key — other buttons on
        # the page also use aria-haspopup="listbox" (seller feedback dropdown navigates away).
        # Re-iterate so dependent variants (Pack often renders after Colour) get picked too.
        variant_label_re = re.compile(
            r"^\s*(Colour|Color|Size|Style|Material|Pack|Capacity|Pattern|Shape|Configuration|Type|Model|Edition|Set|Bundle)\s*:",
            re.I,
        )
        placeholder_re = re.compile(r"^\s*-?\s*Select\s*-?\s*$", re.I)
        for _round in range(6):
            progress = False
            for btn in self.page.locator('button[aria-haspopup="listbox"]').all():
                if not btn.is_visible():
                    continue
                label_full = (btn.get_attribute("aria-label") or btn.text_content() or "").strip()
                m = variant_label_re.match(label_full)
                if not m:
                    continue
                # Skip if the picker already has a real value (text after "Label:" isn't placeholder).
                value_part = label_full[m.end():].strip()
                if value_part and not placeholder_re.match(value_part):
                    continue
                label = m.group(0).rstrip(":").strip()
                try:
                    btn.click()
                except Exception:
                    continue
                popup = None
                for popup_sel in ('[role="listbox"]:visible', '[role="menu"]:visible'):
                    loc = self.page.locator(popup_sel).first
                    try:
                        loc.wait_for(state="visible", timeout=3000)
                        popup = loc
                        break
                    except Exception:
                        continue
                if popup is None:
                    try:
                        self.page.keyboard.press("Escape")
                    except Exception:
                        pass
                    continue
                options = popup.locator('[role="option"]').all()
                if not options:
                    options = popup.locator('[role="menuitem"], [role="menuitemradio"]').all()
                enabled: list[tuple] = []
                for o in options:
                    if not o.is_visible():
                        continue
                    if (o.get_attribute("aria-disabled") or "false").lower() == "true":
                        continue
                    if (o.get_attribute("data-disabled") or "false").lower() == "true":
                        continue
                    txt = (o.text_content() or "").strip()
                    if not txt or placeholder_re.match(txt):
                        continue
                    enabled.append((o, txt))
                if not enabled:
                    try:
                        self.page.keyboard.press("Escape")
                    except Exception:
                        pass
                    continue
                chosen, chosen_text = random.choice(enabled)
                with allure.step(f"Pick {label}: {chosen_text}"):
                    chosen.click()
                picks.append(f"{label} = {chosen_text}")
                progress = True
                self.page.wait_for_load_state("domcontentloaded")
            if not progress:
                break

        # Strategy B: legacy / non-skinned native <select>.
        # Skip <select> hidden behind a Strategy-A skin (display:none → not visible).
        panel = self.page.locator(
            "#mainContent, #vi_main_pic_wrapper, [data-testid*='ux-layout-section-evo']"
        ).first
        selects = panel.locator("select").all() if panel.count() else []
        if not selects:
            selects = self.page.locator("select").all()
        for select in selects:
            if not select.is_visible():
                continue
            name_attr = (select.get_attribute("name") or "").lower()
            if "quantity" in name_attr or "qty" in name_attr:
                continue
            # Skip non-variant utility selects (e.g., language, currency, country).
            sid = (select.get_attribute("id") or "").lower()
            if any(k in sid for k in ("lang", "currency", "country", "loc")):
                continue
            label = (
                select.get_attribute("aria-label")
                or select.evaluate(
                    "el => el.closest('[data-testid*=\"ux-select-box\"]')"
                    "?.querySelector('[class*=\"label\"]')?.textContent?.trim() "
                    "|| el.labels?.[0]?.textContent?.trim() "
                    "|| el.previousElementSibling?.textContent?.trim() "
                    "|| ''"
                )
                or select.get_attribute("id")
                or "variant"
            )
            valid: list[tuple[str, str]] = []
            for opt in select.locator("option:not([disabled])").all():
                value = opt.get_attribute("value")
                if value and value != "-1":
                    text = (opt.text_content() or "").strip()
                    valid.append((value, text))
            if not valid:
                raise RuntimeError(
                    f"Variant {label} has zero valid options after filtering — likely all out of stock"
                )
            value, text = random.choice(valid)
            with allure.step(f"Pick {label}: {text}"):
                self._select_value(select, value)
            picks.append(f"{label} = {text}")

        for group in self.page.get_by_role("radiogroup").all():
            label = group.get_attribute("aria-label") or "variant"
            radios = group.get_by_role("radio").all()
            if any(r.get_attribute("aria-checked") == "true" for r in radios):
                picks.append(f"{label} = (already selected)")
                continue
            valid_radios: list[tuple] = []
            for r in radios:
                if r.get_attribute("aria-disabled") == "true":
                    continue
                text = (r.get_attribute("aria-label") or r.text_content() or "").strip()
                valid_radios.append((r, text))
            if not valid_radios:
                raise RuntimeError(
                    f"Variant {label} has zero enabled radio options — likely all out of stock"
                )
            chosen, text = random.choice(valid_radios)
            with allure.step(f"Pick {label}: {text}"):
                chosen.click()
            picks.append(f"{label} = {text}")

        if picks:
            allure.attach(
                "\n".join(picks),
                name="picked-variants",
                attachment_type=allure.attachment_type.TEXT,
            )
        return self

    @allure.step("Add to cart")
    def add_to_cart(self) -> "ItemPage":
        candidates = [
            self.page.get_by_role("link", name=re.compile(r"^Add to cart$", re.I)).first,
            self.page.get_by_role("button", name=re.compile(r"^Add to cart$", re.I)).first,
            self.page.locator('a[id^="atcBtn_btn"]').first,
            self.page.locator('a[data-testid="ux-call-to-action"]:has-text("Add to cart")').first,
            self.page.locator('button[id^="atcBtn_btn"]').first,
        ]
        for btn in candidates:
            if btn.count() and btn.is_visible():
                btn.click()
                self._wait_for_atc_signal()
                self._dismiss_post_add_modals()
                allure.attach(
                    self.screenshot(),
                    name="add-to-cart",
                    attachment_type=allure.attachment_type.PNG,
                )
                return self
        allure.attach(
            self.screenshot(),
            name="no-add-to-cart",
            attachment_type=allure.attachment_type.PNG,
        )
        raise RuntimeError(f"No 'Add to cart' button found at {self.page.url}")

    def _select_value(self, select, value: str) -> None:
        """eBay wraps native <select> in a visual skin that often hides the original.
        Try the user-facing path first; fall back to JS so hidden skins still work.
        """
        try:
            select.select_option(value=value, timeout=4000)
            return
        except Exception:
            pass
        select.evaluate(
            "(el, val) => {"
            " el.value = val;"
            " el.dispatchEvent(new Event('input', {bubbles: true}));"
            " el.dispatchEvent(new Event('change', {bubbles: true}));"
            "}",
            value,
        )

    def _wait_for_atc_signal(self) -> None:
        """Require positive proof: cart-subdomain navigation OR success toast/heading/modal
        OR a post-ATC affordance like "Go to cart"/"View cart" that eBay shows in a flyout.
        Raise on validation error or no signal — silent success would let an empty cart
        pass downstream assertions.
        """
        try:
            self.page.wait_for_url(
                lambda u: "cart.ebay.com" in u or "cart.payments.ebay.com" in u,
                timeout=12000,
            )
            return
        except Exception:
            pass
        for sel in (
            'role=heading[name=/added to.*(cart|bag)/i]',
            'text=/added to.*(cart|bag)/i',
            'role=link[name=/^(go to|view) cart$/i]',
            'role=button[name=/^(go to|view) cart$/i]',
            'role=dialog',
        ):
            try:
                self.page.locator(sel).first.wait_for(state="visible", timeout=2000)
                return
            except Exception:
                continue
        validation = self.page.get_by_text(
            re.compile(r"please select|please choose", re.I)
        ).first
        if validation.count() and validation.is_visible():
            txt = (validation.text_content() or "").strip()
            allure.attach(
                self.screenshot(),
                name="atc-validation-error",
                attachment_type=allure.attachment_type.PNG,
            )
            raise RuntimeError(f"Add-to-cart blocked by validation: {txt!r}")
        allure.attach(
            self.screenshot(),
            name="atc-no-signal",
            attachment_type=allure.attachment_type.PNG,
        )
        raise RuntimeError(
            f"Add-to-cart click produced no cart navigation or success signal; URL: {self.page.url}"
        )

    def _dismiss_post_add_modals(self) -> None:
        for role, name in (("button", "No thanks"), ("button", "Not now")):
            try:
                self.page.get_by_role(role, name=name).first.click(timeout=1500)
            except Exception:
                pass
        try:
            self.page.locator('[aria-label*="Close"]').first.click(timeout=1500)
        except Exception:
            pass
