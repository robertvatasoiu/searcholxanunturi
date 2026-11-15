import re
import logging
from typing import List
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing
from backend.transaction_filter import parse_price, is_rental_or_invalid_transaction
from backend.year_filter import evaluate_listing_year
from backend.location_filter import is_excluded_location, detect_neighborhood, normalize_floor

logger = logging.getLogger("scrapers.imoradar")


class ImoradarScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="imoradar")
        self.base_url = "https://www.imoradar24.ro"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9",
        }

        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/apartamente-de-vanzare/bucuresti/sector-6/{rooms}-camere"
            if page > 1:
                url += f"?page={page}"

            try:
                logger.info(f"Fetching Imoradar24 page {page}: {url}")
                resp = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Imoradar24 page {page} returned status {resp.status_code}")
                    break

                page_listings = self._parse_page(resp.text, min_year, rooms)
                if not page_listings:
                    break
                results.extend(page_listings)
            except Exception as e:
                logger.error(f"Error fetching Imoradar24 page {page}: {e}")
                break

        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        soup = BeautifulSoup(html, "html.parser")

        ext_links = soup.select("a[href*='/link-extern/']")
        seen_ids = set()

        for a in ext_links:
            try:
                href = a["href"]
                id_match = re.search(r"/link-extern/(\d+)", href)
                if not id_match:
                    continue
                ad_id_val = id_match.group(1)
                if ad_id_val in seen_ids:
                    continue
                seen_ids.add(ad_id_val)

                ad_id = Listing.generate_id("imoradar", ad_id_val)
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                container = a
                for _ in range(7):
                    if container.parent and container.parent.name != "body":
                        container = container.parent
                        txt = container.get_text(" | ", strip=True)
                        if ("€" in txt or "EUR" in txt.upper()) and len(txt) >= 120:
                            break

                card_text = container.get_text(" | ", strip=True)
                parts = [p.strip() for p in card_text.split("|") if p.strip()]
                if not parts:
                    continue

                title_text = parts[0]
                for p in parts:
                    if len(p) > 15 and any(k in p.lower() for k in ["apartament", "camere", "studio", "vanzare", "vânzare"]):
                        title_text = p
                        break

                # Price specifically matched near € / EUR
                price_match = re.search(r"(\d{2,3}(?:[\.\s,]\d{3})+|\d{5,6})\s*(?:€|EUR|eur)", card_text)
                if price_match:
                    price_val, currency = parse_price(price_match.group(0))
                else:
                    price_val, currency = parse_price(card_text)

                is_rental, _ = is_rental_or_invalid_transaction(
                    title=title_text,
                    description=card_text,
                    url=full_url,
                    price=price_val,
                    currency=currency,
                )
                if is_rental:
                    continue

                is_excl, _ = is_excluded_location(
                    title=title_text,
                    description=card_text,
                    neighborhood="Sector 6",
                    url=full_url,
                )
                if is_excl:
                    continue

                is_valid, year_val, _ = evaluate_listing_year(
                    explicit_year=None,
                    title=title_text,
                    description=card_text,
                    min_year=min_year,
                )
                if not is_valid:
                    continue

                surf_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:mp|m²)", card_text, re.IGNORECASE)
                surface_val = float(surf_match.group(1).replace(",", ".")) if surf_match else None

                floor_norm = normalize_floor(None, title_text, card_text)
                neighborhood = detect_neighborhood(title_text, card_text, "Sector 6")

                img_el = container.find("img")
                thumb = None
                if img_el:
                    thumb = img_el.get("src") or img_el.get("data-src")
                    if thumb and thumb.startswith("//"):
                        thumb = "https:" + thumb

                listings.append(
                    Listing(
                        id=ad_id,
                        portal="imoradar",
                        title=title_text,
                        price=price_val,
                        currency=currency,
                        surface_sqm=surface_val,
                        rooms=rooms,
                        year=year_val,
                        floor=floor_norm,
                        neighborhood=neighborhood,
                        city="Bucuresti",
                        sector="Sector 6",
                        description=card_text[:300],
                        url=full_url,
                        thumbnail=thumb,
                        images=[thumb] if thumb else [],
                    )
                )
            except Exception as e:
                logger.debug(f"Error parsing Imoradar24 card: {e}")

        return listings
