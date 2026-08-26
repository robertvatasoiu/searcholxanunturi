import re
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger("year.filter")

# Pre-1978 indicators in Romanian real estate
PRE_1978_PHRASES = [
    r"inainte\s+de\s+1977",
    r"inainte\s+1977",
    r"inainte\s+de\s+[\'’`]?77",
    r"pre-?1977",
    r"pana\s+in\s+1977",
    r"pana\s+la\s+cutremur",
    r"inainte\s+de\s+cutremur",
    r"bloc\s+vechi\s+19[567]\d",
    r"bloc\s+din\s+anii\s+[’\'`]?[567]0",
    r"bloc\s+anii\s+[’\'`]?[567]0",
    r"bloc\s+tip\s+rusesc",
]

# Prefixes specifically indicating construction / building year
CONSTRUCTION_PREFIXES = r"(?:bloc|an|anul|constructie|constructiei|construit|finalizat|finalizare|zidit|edificat|imobil|an\s+constructie|an\s+de\s+constructie|bloc\s+din|bloc\s+in|blocul\s+din|imobil\s+din)\s*(?:in|din|:|–|-|\s)*"

def evaluate_listing_year(
    explicit_year: Optional[int],
    title: str = "",
    description: str = "",
    tags: Optional[List[str]] = None,
    min_year: int = 1978
) -> Tuple[bool, Optional[int], str]:
    """
    Strictly evaluates if a listing is built AFTER 1977 (min_year >= 1978).
    Returns (is_valid, detected_year, reason).
    """
    full_text = f"{title} {description} {' '.join(tags or [])}"

    # 1. PRIORITY CHECK: Any construction year in 1940..1977 (e.g. "bloc construit in 1972")
    # Even if title says "renovat 2026", construction year <= 1977 takes precedence!
    old_context_matches = re.findall(CONSTRUCTION_PREFIXES + r"(19[4-7]\d)\b", full_text, re.IGNORECASE)
    if old_context_matches:
        old_yr = int(old_context_matches[0])
        if old_yr < min_year:
            return False, old_yr, f"Bloc construit în {old_yr} < {min_year}"

    # 2. Check explicit pre-1978 negative phrases
    for phrase_regex in PRE_1978_PHRASES:
        if re.search(phrase_regex, full_text, re.IGNORECASE):
            return False, 1970, f"Text conține expresie pre-1977: {phrase_regex}"

    # 3. Check year with apostrophe (e.g. bloc '68, bloc '72, bloc '74, bloc '77)
    apostrophe_matches = re.findall(r"(?:bloc|an|constructie|imobil)\s*(?:din|in)?\s*[’\'`](\d{2})\b", full_text, re.IGNORECASE)
    for ap in apostrophe_matches:
        val = int(ap)
        yr = 2000 + val if val < 30 else 1900 + val
        if yr < min_year:
            return False, yr, f"Bloc din '{ap} ({yr}) < {min_year}"

    # 4. Check all standalone years in 1940..1977 in text
    all_years = re.findall(r"\b(19[4-7]\d)\b", full_text)
    for y_str in all_years:
        yr = int(y_str)
        if 1940 <= yr < min_year:
            if yr == 1907 and "1907" in title.lower():
                continue
            return False, yr, f"Mențiune an vechi în text: {yr} < {min_year}"

    # 5. Check explicit year field if present
    if explicit_year is not None:
        if explicit_year < min_year:
            return False, explicit_year, f"An explicit {explicit_year} < {min_year}"
        else:
            return True, explicit_year, f"An explicit {explicit_year} >= {min_year}"

    # 6. Check post-1978 context matches (e.g. bloc 1984, construit in 2021)
    new_context_matches = re.findall(CONSTRUCTION_PREFIXES + r"([12]\d{3})\b", full_text, re.IGNORECASE)
    for ym in new_context_matches:
        yr = int(ym)
        if min_year <= yr <= 2035:
            return True, yr, f"An construcție contextual {yr} >= {min_year}"

    # 7. Check positive indicators for post-1978 or new buildings
    new_building_patterns = [
        r"bloc\s+nou",
        r"ansamblu\s+rezidential",
        r"complex\s+rezidential",
        r"constructie\s+noua",
        r"dupa\s+2000",
        r"dupa\s+1977",
        r"dupa\s+cutremur",
        r"imobil\s+nou",
        r"direct\s+dezvoltator",
        r"in\s+constructie"
    ]
    for nbp in new_building_patterns:
        if re.search(nbp, full_text, re.IGNORECASE):
            return True, None, f"Indicator bloc nou/după 1977 ({nbp})"

    # Allowed by default if no pre-1978 indicator was found
    return True, None, "An nespecificat (fără indicatori pre-1977)"
