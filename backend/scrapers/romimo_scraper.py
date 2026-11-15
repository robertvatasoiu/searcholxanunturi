import re
import logging
from typing import List
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing
from backend.transaction_filter import parse_price, is_rental_or_invalid_transaction
from backend.year_filter import evaluate_listing_year
from backend.location_filter import is_excluded_location, detect_neighborhood, normalize_floor

logger = logging.getLogger("scrapers.romimo")


class RomimoScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="romimo")
        self.base_url = "https://www.romimo.ro"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9",
        }

        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/apartamente/apartamente-{rooms}-camere/vanzare/bucuresti/sector-6/?pag={page}"
            try:
                logger.info(f"Fetching Romimo page {page}: {url}")
                resp = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Romimo page {page} returned status {resp.status_code}")
                    break

                page_listings = self._parse_page(resp.text, min_year, rooms)
                if not page_listings:
                    break
                results.extend(page_listings)
            except Exception as e:
                logger.error(f"Error fetching Romimo page {page}: {e}")
                break

        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select(".article-item, li.article-item, div.article-item")

        for el in articles:
            try:
                title_el = el.select_one("a.article-title, h2 a, a[title]")
                if not title_el or not title_el.has_attr("href"):
                    continue

                full_url = title_el["href"]
                if not full_url.startswith("http"):
                    full_url = f"{self.base_url}{full_url}"

                title_text = title_el.text.strip()
                if not title_text:
                    title_text = title_el.get("title", "Apartament 2 camere Sector 6")

                id_match = re.search(r"/([a-z0-9]{20,})\.html", full_url)
                ad_id_val = id_match.group(1) if id_match else full_url.rstrip("/").split("/")[-1]
                ad_id = Listing.generate_id("romimo", ad_id_val)

                price_el = el.select_one(".price, .article-price, strong")
                price_val, currency = parse_price(price_el.get_text(separator=" ", strip=True) if price_el else "")

                detail_el = el.select_one(".details, .article-details, p")
                detail_text = detail_el.text.strip() if detail_el else ""
                all_text = f"{title_text} {detail_text}"

                is_rental, _ = is_rental_or_invalid_transaction(
                    title=title_text,
                    description=detail_text,
                    url=full_url,
                    price=price_val,
                    currency=currency,
                )
                if is_rental:
                    continue

                is_excl, _ = is_excluded_location(
                    title=title_text,
                    description=detail_text,
                    neighborhood="Sector 6",
                    url=full_url,
                )
                if is_excl:
                    continue

                is_valid, year_val, _ = evaluate_listing_year(
                    explicit_year=None,
                    title=title_text,
                    description=detail_text,
                    min_year=min_year,
                )
                if not is_valid:
                    continue

                surf_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*mp", all_text, re.IGNORECASE)
                surface_val = float(surf_match.group(1).replace(",", ".")) if surf_match else None

                date_el = el.select_one(".date, .article-date, span.text-muted")
                date_text = date_el.text.strip() if date_el else None

                img_el = el.select_one("img")
                thumb = None
                if img_el:
                    thumb = img_el.get("src") or img_el.get("data-src")
                    if thumb and thumb.startswith("//"):
                        thumb = "https:" + thumb

                neighborhood = detect_neighborhood(title_text, detail_text, "Sector 6")
                floor_norm = normalize_floor(None, title_text, detail_text)

                listings.append(
                    Listing(
                        id=ad_id,
                        portal="romimo",
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
                        description=detail_text[:300] if detail_text else None,
                        url=full_url,
                        thumbnail=thumb,
                        images=[thumb] if thumb else [],
                        date_published=date_text,
                    )
                )
            except Exception as e:
                logger.debug(f"Error parsing Romimo item: {e}")

        return listings
