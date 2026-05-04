import re

from core.schemas import Currency, Money

_CURRENCY_PATTERNS: tuple[tuple[re.Pattern[str], Currency], ...] = (
    (re.compile(r"\bUS\s*\$|\bUSD\b|(?<![A-Z])\$"), "USD"),
    (re.compile(r"\bILS\b|\u20aa"), "ILS"),
    (re.compile(r"\bEUR\b|\u20ac"), "EUR"),
    (re.compile(r"\bGBP\b|\u00a3"), "GBP"),
)


def _detect_currency(text: str) -> Currency:
    for pat, code in _CURRENCY_PATTERNS:
        if pat.search(text):
            return code
    raise ValueError(f"No currency token in cart total text: {text!r}")


_USD_LIKE: frozenset[Currency] = frozenset({"USD", "GBP", "ILS"})


def parse_total(text: str) -> Money:
    """Parse a price string into a `Money(amount, currency)`.

    Locale rules are driven by the detected currency, not by counting digits
    after a comma — the digit-count heuristic misreads EU prices like
    ``€1,5`` (1.50, not 15) and any other non-2-decimal comma.
      - USD / GBP / ILS: comma is thousands, dot is decimal.
      - EUR: dot is thousands, comma is decimal (``1.234,56`` and ``€1,5`` both work).
    Refuses ranges (``$220 to $250``) loudly rather than silently picking the lower bound.
    Refuses bare numbers with no currency token.
    """
    currency = _detect_currency(text)
    tokens = re.findall(r"\d[\d.,]*", text)
    if len(tokens) > 1 or " to " in text.lower():
        raise ValueError(f"Price looks like a range, refusing to guess: {text!r}")
    if not tokens:
        raise ValueError(f"No numeric token in price text: {text!r}")
    digits = tokens[0]
    if currency in _USD_LIKE:
        digits = digits.replace(",", "")
    else:
        if "." in digits and "," in digits:
            digits = digits.replace(".", "").replace(",", ".")
        elif "," in digits:
            digits = digits.replace(",", ".")
    return Money(amount=float(digits), currency=currency)
