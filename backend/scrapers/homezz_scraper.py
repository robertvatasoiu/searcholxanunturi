import re
import logging
from typing import List
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing
from backend.transaction_filter import parse_price, is_rental_or_invalid_transaction
from backend.year_filter import evaluate_listing_year
from backend.location_filter import is_excluded_location, detect_neighborhood, normalize_floor

logger = logging.getLogger("scrapers.homezz")


class HomeZZScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="homezz")
        self.base_url = "https://homezz.ro"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        # On HomeZZ, ar=7 corresponds to Sector 6 in Bucuresti-Ilfov
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/vanzare-apartamente/bucuresti-if/{rooms}-camere?ar=7"
            if page > 1:
                url += f"&page={page}"

            try:
                logger.info(f"Fetching HomeZZ page {page}: {url}")
                resp = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"HomeZZ page {page} returned status {resp.status_code}")
                    break

                page_listings = self._parse_page(resp.text, min_year, rooms)
                if not page_listings:
                    break
                results.extend(page_listings)
            except Exception as e:
                logger.error(f"Error fetching HomeZZ page {page}: {e}")
                break

        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        soup = BeautifulSoup(html, "html.parser")

        cards = [
            a for a in soup.find_all("a", href=True)
            if a["href"].endswith(".html")
            and "ansambluri-rezidentiale" not in a["href"]
            and re.search(r"-\d+\.html$", a["href"])
        ]

        seen_urls = set()
        for card in cards:
            try:
                href = card["href"]
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                id_match = re.search(r"-(\d+)\.html$", full_url)
                ad_id_val = id_match.group(1) if id_match else full_url.split("/")[-1]
                ad_id = Listing.generate_id("homezz", ad_id_val)

                card_text = re.sub(r"\s+", " ", card.get_text(separator=" | ", strip=True))
                parts = [p.strip() for p in card_text.split("|") if p.strip()]
                if not parts:
                    continue

                title_text = parts[0]
                if len(title_text) < 4:
                    title_text = "Apartament 2 camere Sector 6"

                price_segment = ""
                for p in parts[1:]:
                    if any(k in p.lower() for k in ("€", "eur", "lei", "ron")):
                        price_segment = p
                        break
                if not price_segment and len(parts) > 1:
                    price_segment = parts[1]
                price_val, currency = parse_price(price_segment)

                is_rental, rent_reason = is_rental_or_invalid_transaction(
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

                surf_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:m²|mp)", card_text, re.IGNORECASE)
                surface_val = float(surf_match.group(1).replace(",", ".")) if surf_match else None

                floor_norm = normalize_floor(None, title_text, card_text)
                neighborhood = detect_neighborhood(title_text, card_text, "Sector 6")

                img_el = card.find("img")
                thumb = None
                if img_el:
                    thumb = img_el.get("src") or img_el.get("data-src")
                    if thumb and thumb.startswith("//"):
                        thumb = "https:" + thumb

                listings.append(
                    Listing(
                        id=ad_id,
                        portal="homezz",
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
                        description=card_text[:280],
                        url=full_url,
                        thumbnail=thumb,
                        images=[thumb] if thumb else [],
                    )
                )
            except Exception as e:
                logger.debug(f"Error parsing HomeZZ card: {e}")

        return listings
