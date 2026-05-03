import re


def parse_total(text: str) -> float:
    """Parse a money string into a float.

    Locale heuristic — assumes one of:
      - US/UK: ``$220.00`` or ``£220.00`` — comma is thousands, dot is decimal.
      - EU: ``€220,00`` — comma is decimal when followed by exactly 2 digits.
      - Mixed: ``1.234,56`` (EU thousands+decimal) — last separator wins.
    Refuses ranges (``$220 to $250``) loudly rather than silently picking the lower bound.
    """
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
    return float(digits)
