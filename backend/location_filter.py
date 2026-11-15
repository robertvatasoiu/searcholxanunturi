import re
from typing import Tuple, Optional

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

OTHER_SECTOR_PATTERNS = [
    (r"\bsector(?:ul)?\s*[12345]\b", "Alt sector (Sector 1-5)"),
    (
        r"\b(?:pipera|avia[tț]iei|d[aă]m[aă]roaia|b[aă]neasa|bucure[sș]tii\s+noi|"
        r"fabrica\s+de\s+glucoz[aă]|dimitrie\s+pompeiu|cartierul\s+solar|"
        r"berceni|pope[sș]ti[\s\-]*leordeni|pallady|theodor\s+pallady|titan|colentina|"
        r"pantelimon|obor|rahova|ferentari|bragadiru|otopeni|voluntari|tunari|domne[sș]ti|"
        r"cosmopolis|ap[aă]r[aă]torii\s+patriei|13\s+septembrie)\b",
        "Zonă în afara Sectorului 6",
    ),
]

# Ordered from specific sub-zones to broader Sector 6 neighborhoods
NEIGHBORHOOD_RULES = [
    (
        "Drumul Taberei",
        re.compile(
            r"\b(?:drumul\s+taberei|dr\.?\s*taberei|favorit|r[aâ]ul\s+doamnei|romancierilor|"
            r"moghioro[sș]|valea\s+ialomi[tț]ei|constantin\s+br[aâ]ncu[sș]i|parc(?:ul)?\s+br[aâ]ncu[sș]i|"
            r"tricodava|chilia\s+veche|poiana\s+muntelui|cetatea\s+histria|t[aâ]rgu\s+neam[tț]|"
            r"valea\s+arge[sș]ului|bd\.?\s*timi[sș]oara|timi[sș]oara|titel\s+petrescu|"
            r"plaza\s+rom[aâ]nia|mall\s+plaza|str(?:ada)?\.?\s*(?:bra[sș]ov|sibiu))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Lujerului",
        re.compile(
            r"\b(?:lujerului|pasaj(?:ul)?\s+lujerului|cora\s+lujerului|carrefour\s+lujerului|"
            r"[sș]os(?:eaua)?\.?\s*virtu[tț]ii|virtu[tț]ii|or[sș]ova|exigent\s+plaza|21\s+residence|"
            r"gran\s*via|granvia)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Gorjului",
        re.compile(
            r"\b(?:gorjului|pia[tț]a\s+gorjului|metrou\s+gorjului|moine[sș]ti|"
            r"cetatea\s+de\s+balt[aă]|dezrobirii|cerni[sș]oara)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Crângași",
        re.compile(
            r"\b(?:cr[aâ]nga[sș]i|metrou\s+cr[aâ]nga[sș]i|lacul\s+morii|ceahl[aă]u|"
            r"constructorilor|9\s+mai|george\s+v[aâ]lsan|giule[sș]ti)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Politehnica",
        re.compile(
            r"\b(?:politehnic[aă]|politehnicii|afi\s+cotroceni|afi\s+palace|"
            r"bd\.?\s*vasile\s+milea|general\s+paul\s+teodorescu)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Grozăvești",
        re.compile(
            r"\b(?:groz[aă]ve[sș]ti|regie|orhideea|carrefour\s+orhideea|"
            r"economu\s+cezarescu|oncos|pod(?:ul)?\s+groz[aă]ve[sș]ti|sema\s+park|sema\s+home|petrache\s+poenaru)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Ghencea",
        re.compile(
            r"\b(?:ghencea|prelungirea\s+ghencea|valea\s+oltului|stadion(?:ul)?\s+steaua|drumul\s+s[aă]rii)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Militari",
        re.compile(
            r"\b(?:militari|p[aă]cii|metrou\s+p[aă]cii|preciziei|metrou\s+preciziei|"
            r"apusului|uverturii|veteranilor|iuliu\s+maniu|rotar\s+park|valea\s+cascadelor|"
            r"valea\s+lung[aă]|drumul\s+osiei|autogar[aă]\s+militari|viscolului)\b",
            re.IGNORECASE,
        ),
    ),
]

CANONICAL_NEIGHBORHOOD_MAP = {
    "drumul taberei": "Drumul Taberei",
    "militari": "Militari",
    "crangasi": "Crângași",
    "crângași": "Crângași",
    "grozavesti": "Grozăvești",
    "grozăvești": "Grozăvești",
    "politehnica": "Politehnica",
    "ghencea": "Ghencea",
    "valea oltului": "Ghencea",
    "lujerului": "Lujerului",
    "gorjului": "Gorjului",
}


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

    title_and_url = f"{title or ''} {url or ''}"
    for pattern, label in OTHER_SECTOR_PATTERNS:
        if re.search(pattern, title_and_url, re.IGNORECASE):
            return True, f"Zonă exclusă ({label})"

    # If the title does not explicitly mention a Sector 6 neighborhood, also check description for other sectors
    has_s6_title = any(regex.search(title or "") for _, regex in NEIGHBORHOOD_RULES) or bool(
        re.search(r"\bsector(?:ul)?\s*6\b", title or "", re.IGNORECASE)
    )
    if not has_s6_title:
        for pattern, label in OTHER_SECTOR_PATTERNS:
            if re.search(pattern, cleaned_desc, re.IGNORECASE):
                return True, f"Zonă exclusă ({label})"

    return False, "Zonă validă Sector 6"


def detect_neighborhood(
    title: str = "",
    description: str = "",
    current_neighborhood: Optional[str] = None,
) -> str:
    """
    Detects or normalizes the specific Sector 6 neighborhood from title & description,
    especially for portals like OLX/Storia where district defaults to 'Sectorul 6' or 'Militari'.
    """
    cur = (current_neighborhood or "").strip()
    cur_lower = cur.lower()

    # Check title first (strongest signal for specific sub-zones like Lujerului, Gorjului, Drumul Taberei)
    for canonical, regex in NEIGHBORHOOD_RULES:
        if regex.search(title or ""):
            return canonical

    # If current neighborhood is already a specific canonical neighborhood (not generic Sector 6 / Militari), keep it
    if cur_lower in CANONICAL_NEIGHBORHOOD_MAP and cur_lower != "militari":
        return CANONICAL_NEIGHBORHOOD_MAP[cur_lower]

    # Check description for specific neighborhoods
    cleaned_desc = NEGATION_PATTERN.sub(" ", description or "")
    for canonical, regex in NEIGHBORHOOD_RULES:
        if regex.search(cleaned_desc):
            return canonical

    if cur_lower in CANONICAL_NEIGHBORHOOD_MAP:
        return CANONICAL_NEIGHBORHOOD_MAP[cur_lower]

    return "Sector 6"


def normalize_floor(
    floor_raw: Optional[str] = None,
    title: str = "",
    description: str = "",
) -> Optional[str]:
    """
    Normalizes floor strings across portals ('floor_3', 'parter', '3 / 8') or extracts from text.
    """
    raw = (floor_raw or "").strip()
    raw_lower = raw.lower()

    if raw_lower in {"parter", "ground_floor", "p"}:
        return "Parter"
    if raw_lower in {"demisol", "cellar", "subsol", "d"}:
        return "Demisol"
    if raw_lower in {"mansarda", "mansardă", "attic", "m", "pod"}:
        return "Mansardă"

    m_storia = re.match(r"^floor_(\d+)$", raw_lower)
    if m_storia:
        return f"Etaj {m_storia.group(1)}"
    if raw_lower == "floor_higher_10":
        return "Etaj 10+"

    m_num = re.match(r"^(?:etaj(?:ul)?|et\.?)?\s*(\d{1,2})(?:\s*(?:/|din)\s*(\d{1,2}))?$", raw_lower)
    if m_num:
        fl, tot = m_num.group(1), m_num.group(2)
        if fl == "0":
            return "Parter"
        return f"Etaj {fl}/{tot}" if tot else f"Etaj {fl}"

    # Extract from title + description if raw was empty or uninformative
    text = f"{title or ''} {description or ''}"
    m_frac = re.search(
        r"\b(?:etaj(?:ul)?|et\.?)\s*(\d{1,2})\s*(?:/|din)\s*(\d{1,2})\b",
        text,
        re.IGNORECASE,
    )
    if m_frac:
        fl, tot = m_frac.group(1), m_frac.group(2)
        return "Parter" if fl == "0" else f"Etaj {fl}/{tot}"

    m_single = re.search(r"\b(?:etaj(?:ul)?|et\.?)\s*(\d{1,2})\b", text, re.IGNORECASE)
    if m_single:
        fl = m_single.group(1)
        return "Parter" if fl == "0" else f"Etaj {fl}"

    if re.search(r"\b(?:la\s+parter|parter\s+[iî]nalt|etaj\s+parter)\b", text, re.IGNORECASE):
        return "Parter"
    if re.search(r"\b(?:mansard[aă]|demisol)\b", text, re.IGNORECASE):
        return "Mansardă" if "mansard" in text.lower() else "Demisol"

    if raw and len(raw) <= 15:
        return raw
    return None


def is_ground_or_top_floor(
    floor_norm: Optional[str] = None,
    title: str = "",
    description: str = "",
) -> bool:
    """
    Returns True if the listing is on ground floor (Parter/Demisol), attic (Mansardă),
    or top floor (e.g. Etaj 4/4, 8/8, 10/10, ultimul etaj).
    """
    fl = (floor_norm or "").strip().lower()
    if any(k in fl for k in ("parter", "demisol", "mansard", "subsol")):
        return True

    m_frac = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", fl)
    if m_frac and m_frac.group(1) == m_frac.group(2):
        return True

    text = f"{title or ''} {description or ''}"
    m_text_frac = re.search(
        r"\b(?:etaj(?:ul)?|et\.?)?\s*(\d{1,2})\s*(?:/|din)\s*(\d{1,2})\b",
        text,
        re.IGNORECASE,
    )
    if m_text_frac and m_text_frac.group(1) == m_text_frac.group(2) and int(m_text_frac.group(2)) <= 15:
        return True

    if re.search(r"\b(?:ultimul\s+etaj|la\s+parter|parter\s+[iî]nalt|demisol|mansard[aă])\b", text, re.IGNORECASE):
        return True

    return False


def is_direct_owner_or_zero_commission(title: str = "", description: str = "") -> bool:
    """
    Returns True if the listing indicates Direct Owner (Proprietar/Particular) or 0% Commission.
    """
    text = f"{title or ''} {description or ''}"
    if re.search(r"\b(?:f[aă]r[aă]\s+agen[tț]ii|exclus\s+agen[tț]ii)\b", text, re.IGNORECASE):
        return True
    if re.search(
        r"\b(?:direct\s+proprietar|proprietar\s+v[aâ]nd|proprietar\s+ofer|particular|comision\s*0\s*%?|0\s*%\s*comision|f[aă]r[aă]\s+comision|direct\s+dezvoltator)\b",
        text,
        re.IGNORECASE,
    ):
        return True
    if re.search(r"\bproprietar\b", title or "", re.IGNORECASE):
        return True
    return False
