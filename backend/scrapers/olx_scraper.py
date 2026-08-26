import re
import json
import logging
from typing import List, Optional
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing

logger = logging.getLogger("scrapers.olx")

class OLXScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="olx")
        self.base_url = "https://www.olx.ro"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        for page in range(1, max_pages + 1):
            url = (
                f"{self.base_url}/imobiliare/apartamente-garsoniere-de-vanzare/{rooms}-camere/bucuresti/q-sector-6/"
                f"?search%5Border%5D=created_at:desc"
                f"&search%5Bfilter_enum_constructie%5D%5B0%5D=dupa-2000"
                f"&search%5Bfilter_enum_constructie%5D%5B1%5D=1990-2000"
                f"&search%5Bfilter_enum_constructie%5D%5B2%5D=1977-1990"
            )
            if page > 1:
                url += f"&page={page}"

            try:
                logger.info(f"Fetching OLX page {page}: {url}")
                resp = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"OLX page {page} returned status {resp.status_code}")
                    break

                page_listings = self._parse_page(resp.text, min_year, rooms)
                if not page_listings:
                    break
                results.extend(page_listings)
            except Exception as e:
                logger.error(f"Error fetching OLX page {page}: {e}")
                break

        # Remove duplicates
        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        
        # Try JSON state extraction from __PRERENDERED_STATE__
        match = re.search(r"window\.__PRERENDERED_STATE__\s*=\s*\"(.*?)\";", html)
        if match:
            try:
                try:
                    raw_json = match.group(1).encode("utf-8").decode("unicode_escape")
                    data = json.loads(raw_json)
                except Exception:
                    data = json.loads(json.loads("\"" + match.group(1) + "\""))

                ads = data.get("listing", {}).get("listing", {}).get("ads", [])
                for ad in ads:
                    listing = self._parse_ad_json(ad, min_year, rooms)
                    if listing:
                        listings.append(listing)
                if listings:
                    return listings
            except Exception as e:
                logger.warning(f"Error parsing OLX JSON state: {e}")

        # Fallback to HTML parsing if JSON structure changes
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[data-cy=\"l-card\"], div[data-cy=\"ad-card-title\"]")
        for card in cards:
            try:
                link_el = card.select_one("a[href*=\"/d/oferta/\"]") or card.find_parent("a")
                if not link_el or not link_el.has_attr("href"):
                    continue
                href = link_el["href"]
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                title = card.select_one("h4, h6, [data-cy=\"ad-card-title\"]")
                title_text = title.text.strip() if title else "Apartament 2 camere Sector 6"
                price_el = card.select_one("[data-testid=\"ad-price\"]")
                price_val, currency = self._parse_price_text(price_el.text if price_el else "")
                
                ad_id = Listing.generate_id("olx", full_url.split("-ID")[-1].replace(".html", ""))
                
                img_el = card.select_one("img")
                thumb = img_el.get("src") if img_el else None

                listings.append(Listing(
                    id=ad_id,
                    portal="olx",
                    title=title_text,
                    price=price_val,
                    currency=currency,
                    rooms=rooms,
                    city="Bucuresti",
                    sector="Sector 6",
                    url=full_url,
                    thumbnail=thumb,
                    images=[thumb] if thumb else []
                ))
            except Exception as e:
                logger.debug(f"Error parsing HTML fallback card: {e}")

        return listings

    def _parse_ad_json(self, ad: dict, min_year: int, rooms: int) -> Optional[Listing]:
        ad_id_val = str(ad.get("id") or ad.get("url", ""))
        ad_id = Listing.generate_id("olx", ad_id_val)
        title = (ad.get("title") or "").strip()
        url = ad.get("url", "")
        if not url:
            return None

        # Price
        price_obj = ad.get("price", {})
        price_val = None
        currency = "EUR"
        if isinstance(price_obj, dict):
            reg = price_obj.get("regularPrice", {})
            if isinstance(reg, dict) and reg.get("value") is not None:
                try:
                    price_val = float(reg.get("value"))
                    currency = reg.get("currencyCode", "EUR")
                except ValueError:
                    pass
            elif price_obj.get("value") is not None:
                try:
                    price_val = float(price_obj.get("value"))
                    currency = price_obj.get("currency", "EUR")
                except ValueError:
                    pass
        # Check if rental
        from backend.transaction_filter import is_rental_or_invalid_transaction
        is_rental, rent_reason = is_rental_or_invalid_transaction(
            title=title,
            description=ad.get("description", ""),
            url=url,
            price=price_val,
            currency=currency
        )
        if is_rental:
            logger.info(f"Discarding OLX rental ad: '{title}' | Reason: {rent_reason}")
            return None

        # Parameters
        params = ad.get("params", [])
        param_map = {}
        for p in params:
            if isinstance(p, dict):
                key = p.get("key")
                val = p.get("value")
                if isinstance(val, dict):
                    param_map[key] = val.get("label") or val.get("key") or ""
                elif isinstance(val, str):
                    param_map[key] = val
                else:
                    param_map[key] = str(val) if val is not None else ""

        # Year check
        from backend.year_filter import evaluate_listing_year
        constructie = str(param_map.get("constructie", ""))
        explicit_year_cand = None
        if "dupa 2000" in constructie.lower():
            explicit_year_cand = 2005
        elif "1990 - 2000" in constructie.lower():
            explicit_year_cand = 1995
        elif "1977 - 1990" in constructie.lower():
            explicit_year_cand = 1982
        elif "inainte de 1977" in constructie.lower():
            return None

        is_valid, detected_yr, reason = evaluate_listing_year(
            explicit_year=explicit_year_cand,
            title=title,
            description=f"{ad.get('description', '')} {constructie}",
            min_year=min_year
        )
        if not is_valid:
            logger.info(f"Discarding OLX ad <= 1977: '{title}' | Reason: {reason}")
            return None
        
        year_num = explicit_year_cand or detected_yr

        # Check surface
        surface_val = None
        m_str = str(param_map.get("m", ""))
        m_match = re.search(r"(\d+(?:[\.,]\d+)?)", m_str)
        if m_match:
            try:
                surface_val = float(m_match.group(1).replace(",", "."))
            except ValueError:
                pass

        # Floor
        floor = param_map.get("floor")

        # Location
        loc = ad.get("location", {}) if isinstance(ad.get("location"), dict) else {}
        district = loc.get("districtName") or loc.get("cityName") or "Sector 6"
        city = loc.get("cityName") or "Bucuresti"

        # Photos
        photos = []
        raw_photos = ad.get("photos", [])
        if isinstance(raw_photos, list):
            for ph in raw_photos:
                if isinstance(ph, dict):
                    link = ph.get("link", "")
                    if link:
                        photo_url = link.replace("{width}x{height}", "800x600")
                        photos.append(photo_url)
                elif isinstance(ph, str):
                    photos.append(ph)
        thumbnail = photos[0] if photos else None

        # Date
        created_time = ad.get("createdTime")

        return Listing(
            id=ad_id,
            portal="olx",
            title=title,
            price=price_val,
            currency=currency,
            surface_sqm=surface_val,
            rooms=rooms,
            year=year_num,
            floor=str(floor) if floor else None,
            neighborhood=district,
            city=city,
            sector="Sector 6",
            description=ad.get("description"),
            url=url,
            thumbnail=thumbnail,
            images=photos,
            date_published=created_time,
            raw_data=ad
        )

    def _parse_price_text(self, text: str):
        if not text:
            return None, "EUR"
        clean = text.replace(" ", "").replace("\xa0", "").replace(".", "").replace(",", ".")
        match = re.search(r"(\d+(?:\.\d+)?)", clean)
        val = float(match.group(1)) if match else None
        currency = "RON" if "lei" in text.lower() or "ron" in text.lower() else "EUR"
        return val, currency
