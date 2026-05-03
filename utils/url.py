import re
from urllib.parse import urlparse

_CAPTCHA_RE = re.compile(r"/splashui/(captcha|challenge)\b", re.I)
_ITEM_ID_RE = re.compile(r"/itm/(?:[^/]+/)?(\d+)")
_ITEM_URL_RE = re.compile(r"^https?://(?:www\.)?ebay\.com/itm/(\d{11,13})(?:[/?]|$)")


def is_captcha_url(url: str) -> bool:
    """eBay's anti-bot redirects to /splashui/captcha or /splashui/challenge."""
    return bool(_CAPTCHA_RE.search(url or ""))


def is_live_cart_url(url: str) -> bool:
    """Path-segment-aware check for the live-cart view (excludes Saved Cart `/sc/...`)."""
    parsed = urlparse(url)
    if not (
        parsed.netloc.endswith("cart.ebay.com")
        or parsed.netloc.endswith("cart.payments.ebay.com")
    ):
        return False
    if re.match(r"/sc(/|$)", parsed.path):
        return False
    return parsed.path == "/" or parsed.path.startswith("/cart")


def extract_item_id(url: str) -> str | None:
    """Extract numeric item ID from any /itm/<id>/ URL form (slug-prefixed or bare)."""
    m = _ITEM_ID_RE.search(url or "")
    return m.group(1) if m else None


def canonical_item_url(url: str) -> str | None:
    """Return canonical https://www.ebay.com/itm/<id> for a valid eBay item URL, else None."""
    m = _ITEM_URL_RE.match(url or "")
    return f"https://www.ebay.com/itm/{m.group(1)}" if m else None
