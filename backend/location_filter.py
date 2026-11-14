import re
from typing import Tuple

EXCLUDED_NEIGHBORHOODS = {
    "chiajna",
    "rosu",
    "roșu",
    "dudu",
    "militari residence",
    "militari-residence",
}

# Negation context where a seller clarifies the property is NOT in Militari Residence
NEGATION_PATTERN = re.compile(
    r"(?:a\s+nu\s+se\s+confunda\s+cu|nu\s+(?:este|se\s+afl[aă]|e)\s+(?:[iî]n|la|parte\s+din)?|f[aă]r[aă]|departe\s+de|nu\s+vorbim\s+de)\s+"
    r"militari\s*[\-_]?\s*re[sz]iden\w*",
    re.IGNORECASE,
)

EXCLUDED_LOCATION_PATTERNS = [
    (r"militari[\s\-_]*re[sz]iden(?:ce|tial)\b|militari[\s\-_]*re[sz]idence", "Militari Residence"),
    (r"\bchiajna\b", "Chiajna / Militari Residence"),
    (r"\b(?:sat(?:ul)?|comuna|zona)\s+ro[sș]u\b", "Roșu (Chiajna) / Militari Residence"),
    (r"\bweiner(?:\s*palada|\s*residence|\s*\d+)?\b", "Str. Weiner Palada (Militari Residence)"),
    (r"\b(?:str(?:ada)?\.?\s*)?rezervelor\b", "Str. Rezervelor (Militari Residence)"),
    (r"\bstr(?:ada)?\.?\s*tineretului\b", "Str. Tineretului (Militari Residence)"),
    (r"\bstr(?:ada)?\.?\s*(?:sg\.?|sergent)\s*ilie\s*petre\b", "Str. Sg. Ilie Petre (Chiajna)"),
]


def is_excluded_location(
    title: str = "",
    description: str = "",
    neighborhood: str = "",
    url: str = "",
) -> Tuple[bool, str]:
    """
    Returns (True, reason) when a listing belongs to Militari Residence / Chiajna
    (outside Sector 6 proper) and should be excluded from results and alerts.
    """
    nb_clean = (neighborhood or "").strip().lower()
    if nb_clean in EXCLUDED_NEIGHBORHOODS:
        return True, f"Cartier exclus: {neighborhood}"

    # Remove explicit negations (e.g. "ATENTIE a nu se confunda cu Militari Residence")
    cleaned_desc = NEGATION_PATTERN.sub(" ", description or "")
    combined = f"{title or ''} {cleaned_desc} {neighborhood or ''} {url or ''}"

    for pattern, label in EXCLUDED_LOCATION_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return True, f"Zonă exclusă ({label})"

    return False, "Zonă validă Sector 6"
