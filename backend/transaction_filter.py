import re
from typing import Tuple, Optional

MIN_SALE_PRICE_EUR = 25000.0

def parse_price(raw_text: str) -> Tuple[Optional[float], str]:
    """
    Robustly parses price and currency from raw text.
    Handles '111 975 EUR', '116,000 EUR', '88.000 €', '116,000 EUR 119,000 EUR'.
    """
    if not raw_text:
        return None, "EUR"

    currency = "EUR"
    lower = raw_text.lower()
    if "ron" in lower or "lei" in lower:
        currency = "RON"
    elif "usd" in lower or "$" in lower:
        currency = "USD"

    # Replace non-breaking spaces
    clean = raw_text.replace("\xa0", " ").strip()

    # Match first valid price pattern
    match = re.search(r"(\d{1,3}(?:[.,\s]\d{3})+|\d+)", clean)
    if match:
        num_str = match.group(1).strip()
        digits_only = re.sub(r"[^\d]", "", num_str)
        if digits_only:
            val = float(digits_only)
            # If price was entered as thousands shortcut (e.g. 111, 116, 88 instead of 111000)
            if 30 <= val <= 350:
                val = val * 1000.0
            return val, currency

    return None, currency

def is_rental_or_invalid_transaction(
    title: str = "",
    description: str = "",
    url: str = "",
    price: Optional[float] = None,
    currency: str = "EUR"
) -> Tuple[bool, str]:
    """
    Strictly distinguishes between property sales and rentals.
    Returns (is_rental, reason).
    """
    title_lower = title.lower()
    url_lower = url.lower()

    # 1. URL strictly indicates rental
    if any(k in url_lower for k in ["/inchirieri/", "/de-inchiriat/", "-de-inchiriat-", "/inchiriere/"]):
        return True, "URL indică închiriere"

    # 2. Explicit rental in title (unless it explicitly says 'vanzare' / 'vand')
    is_sale_title = bool(re.search(r"\b(vanzare|de\s+vanzare|vand|vînd|cumparare)\b", title_lower, re.I))
    
    rental_title_patterns = [
        r"^inchiriez\b",
        r"\bde\s+inchiriat\b",
        r"\bofer\s+spre\s+inchiriere\b",
        r"\binchiriere\s+apartament\b",
        r"\bchirie\s+lunara\b",
        r"/\s*luna\b",
        r"\beuro\s*/\s*luna\b",
        r"\beur\s*/\s*luna\b"
    ]

    for pat in rental_title_patterns:
        if re.search(pat, title_lower, re.IGNORECASE):
            if not is_sale_title:
                return True, f"Titlu indică închiriere: {pat}"

    # 3. Monthly rental price threshold (< 25,000 EUR for a 2-room apartment)
    if price is not None:
        price_in_eur = price if currency == "EUR" else price / 5.0
        # If price is typical monthly rent (e.g. 200 EUR - 3,000 EUR)
        if 50 <= price_in_eur < MIN_SALE_PRICE_EUR:
            return True, f"Preț de închiriere lunară detectat ({price_in_eur:.0f} EUR < {MIN_SALE_PRICE_EUR:.0f} EUR)"

    return False, "Vânzare validă"
