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


def parse_total(text: str) -> Money:
    """Parse a cart-total string into a `Money(amount, currency)`.

    Locale heuristic — assumes one of:
      - US/UK: ``$220.00`` or ``£220.00`` — comma is thousands, dot is decimal.
      - EU: ``€220,00`` — comma is decimal when followed by exactly 2 digits.
      - Mixed: ``1.234,56`` (EU thousands+decimal) — last separator wins.
    Refuses ranges (``$220 to $250``) loudly rather than silently picking the lower bound.
    Refuses bare numbers with no currency token — silently treating ILS as USD was the bug
    that motivated this module.
    """
    currency = _detect_currency(text)
    tokens = re.findall(r"\d[\d.,]*", text)
    if len(tokens) > 1 or " to " in text.lower():
        raise ValueError(f"Cart total looks like a range, refusing to guess: {text!r}")
    if not tokens:
        raise ValueError(f"No numeric token in cart total text: {text!r}")
    digits = tokens[0]
    if "." in digits and "," in digits:
        if digits.rfind(".") > digits.rfind(","):
            digits = digits.replace(",", "")
        else:
            digits = digits.replace(".", "").replace(",", ".")
    elif "," in digits:
        if len(digits.rsplit(",", 1)[-1]) == 2:
            digits = digits.replace(",", ".")
        else:
            digits = digits.replace(",", "")
    return Money(amount=float(digits), currency=currency)
