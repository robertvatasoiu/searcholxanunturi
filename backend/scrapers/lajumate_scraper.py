import json
import logging
from typing import List, Optional
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing
from backend.transaction_filter import is_rental_or_invalid_transaction
from backend.year_filter import evaluate_listing_year
from backend.location_filter import is_excluded_location, detect_neighborhood, normalize_floor

logger = logging.getLogger("scrapers.lajumate")


class LaJumateScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="lajumate")
        self.base_url = "https://lajumate.ro"
        self.image_base = "https://api-preprod.lajumate.ro/opt-image/"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9",
        }

        search_queries = ["sector-6", "drumul-taberei", "militari", "crangasi", "lujerului"]

        for q in search_queries:
            for page in range(1, max_pages + 1):
                url = f"{self.base_url}/anunturi/imobiliare/apartamente-de-vanzare/{rooms}/in/bucuresti-ilfov/bucuresti/c/{q}"
                if page > 1:
                    url += f"?page={page}"

                try:
                    logger.info(f"Fetching LaJumate ({q}) page {page}: {url}")
                    resp = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
                    if resp.status_code != 200:
                        break

                    page_listings = self._parse_page(resp.text, min_year, rooms)
                    if not page_listings:
                        break
                    results.extend(page_listings)
                except Exception as e:
                    logger.error(f"Error fetching LaJumate ({q}) page {page}: {e}")
                    break

        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return listings

        try:
            data = json.loads(script.string)
            page_props = data.get("props", {}).get("pageProps", {})
            ads = page_props.get("adsServer", []) or []
            for ad in ads:
                item = self._parse_ad_json(ad, min_year, rooms)
                if item:
                    listings.append(item)
        except Exception as e:
            logger.warning(f"Error parsing LaJumate __NEXT_DATA__: {e}")

        return listings

    def _parse_ad_json(self, ad: dict, min_year: int, rooms: int) -> Optional[Listing]:
        ad_id_num = ad.get("id")
        slug = ad.get("slug")
        if not ad_id_num or not slug:
            return None

        ad_id = Listing.generate_id("lajumate", str(ad_id_num))
        full_url = f"{self.base_url}/ad/{slug}-{ad_id_num}"
        title = (ad.get("title") or "Apartament 2 camere Sector 6").strip()
        desc = (ad.get("description") or "").strip()

        price_val = None
        if ad.get("price") is not None:
            try:
                price_val = float(ad.get("price"))
            except ValueError:
                pass
        currency = (ad.get("currency") or "EUR").upper()

        field_map = {}
        for f in ad.get("ad_fields", []) or []:
            if isinstance(f, dict) and f.get("name"):
                field_map[f["name"]] = str(f.get("value") or "").strip()

        # Check rooms if explicitly specified
        rooms_str = field_map.get("rooms", "")
        if rooms_str and rooms_str.isdigit() and int(rooms_str) != rooms:
            return None

        explicit_year = None
        yr_str = field_map.get("real_estate_year", "")
        if yr_str.isdigit():
            yr_int = int(yr_str)
            if 1900 <= yr_int <= 2035:
                explicit_year = yr_int

        surface_val = None
        surf_str = field_map.get("real_estate_dimensions", "")
        if surf_str:
            try:
                surface_val = float(surf_str.replace(",", "."))
            except ValueError:
                pass

        floor_raw = field_map.get("real_estate_floor")
        subdiv = field_map.get("real_estate_subdivision", "")
        combined_desc = f"{desc} {subdiv} An {yr_str} {surf_str} mp".strip()

        is_rental, _ = is_rental_or_invalid_transaction(
            title=title,
            description=combined_desc,
            url=full_url,
            price=price_val,
            currency=currency,
        )
        if is_rental:
            return None

        is_excl, _ = is_excluded_location(
            title=title,
            description=combined_desc,
            neighborhood="Sector 6",
            url=full_url,
        )
        if is_excl:
            return None

        is_valid, detected_yr, _ = evaluate_listing_year(
            explicit_year=explicit_year,
            title=title,
            description=combined_desc,
            min_year=min_year,
        )
        if not is_valid:
            return None

        final_year = explicit_year or detected_yr
        floor_norm = normalize_floor(floor_raw, title, combined_desc)
        neighborhood = detect_neighborhood(title, combined_desc, "Sector 6")

        # LaJumate injects promoted Bucharest ads from other sectors; require Sector 6 match
        if neighborhood == "Sector 6":
            import re
            if not re.search(r"\b(?:sector(?:ul)?\s*6|sect\.?\s*6)\b", f"{title} {combined_desc}", re.IGNORECASE):
                return None

        thumb = None
        main_img = ad.get("mainImage")
        if isinstance(main_img, dict) and main_img.get("path"):
            thumb = f"{self.image_base}{main_img['path']}?w=600"

        return Listing(
            id=ad_id,
            portal="lajumate",
            title=title,
            price=price_val,
            currency=currency,
            surface_sqm=surface_val,
            rooms=rooms,
            year=final_year,
            floor=floor_norm,
            neighborhood=neighborhood,
            city="Bucuresti",
            sector="Sector 6",
            description=combined_desc[:280],
            url=full_url,
            thumbnail=thumb,
            images=[thumb] if thumb else [],
            date_published=ad.get("listed_at"),
        )
