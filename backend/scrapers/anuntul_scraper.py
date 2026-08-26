import re
import logging
from typing import List, Optional
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing

logger = logging.getLogger("scrapers.anuntul")

class AnuntulScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="anuntul")
        self.base_url = "https://www.anuntul.ro"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/anunturi-imobiliare-vanzari/apartamente-{rooms}-camere/bucuresti/sector-6/"
            if page > 1:
                url += f"?page={page}"

            try:
                logger.info(f"Fetching Anuntul page {page}: {url}")
                resp = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Anuntul page {page} returned status {resp.status_code}")
                    break

                page_listings = self._parse_page(resp.text, min_year, rooms)
                if not page_listings:
                    break
                results.extend(page_listings)
            except Exception as e:
                logger.error(f"Error fetching Anuntul page {page}: {e}")
                break

        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".card.impression")

        for card in cards:
            try:
                # Find link
                link_el = card.select_one("a[href*=\"/anunt-\"], a[href*=\"/anunturi-\"], a[href*=\"-rm\"], a[href*=\"#\"]")
                # Look inside card for all <a> tags
                all_a = card.find_all("a", href=True)
                valid_a = None
                for a in all_a:
                    if "/anunt-" in a["href"] or "/anunturi-" in a["href"]:
                        valid_a = a
                        break

                if not valid_a:
                    continue

                href = valid_a["href"]
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                
                # Title
                title_text = valid_a.text.strip()
                if not title_text or len(title_text) < 3:
                    h2 = card.find(["h2", "h3", "h4"])
                    title_text = h2.text.strip() if h2 else "Apartament 2 camere Sector 6"

                # Card full text
                card_text = card.get_text(separator=" | ", strip=True)

                # Tags parsing (e.g. 'An 1981', 'Suprafata 55 mp', 'Decomandat', 'Etaj 6 din 10')
                tags = [t.text.strip() for t in card.select(".anunt-etichete span, .badge")]
                
                # Strict Year check using evaluate_listing_year
                from backend.year_filter import evaluate_listing_year
                is_valid, year_val, reason = evaluate_listing_year(
                    explicit_year=None,
                    title=title_text,
                    description=card_text,
                    tags=tags,
                    min_year=min_year
                )
                if not is_valid:
                    logger.info(f"Discarding Anuntul ad <= 1977: '{title_text}' | Reason: {reason}")
                    continue

                # ID
                raw_id = card.get("id") or card.get("data-hash") or href
                ad_id = Listing.generate_id("anuntul", str(raw_id).replace("aid-", ""))

                # Price
                price_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*€", card_text)
                price_val = None
                if price_match:
                    try:
                        p_str = price_match.group(1).replace(".", "").replace(",", ".")
                        price_val = float(p_str)
                    except ValueError:
                        pass

                # Surface
                surf_match = re.search(r"Suprafata\s*(\d+)\s*mp", card_text, re.I)
                surface_val = float(surf_match.group(1)) if surf_match else None

                # Image
                img = card.select_one("img")
                thumb = None
                if img:
                    thumb = img.get("src") or img.get("data-src")
                    if thumb and thumb.startswith("//"):
                        thumb = "https:" + thumb

                # Date
                date_match = re.search(r"(ieri[^\n\|]*|\d{1,2}\s+[a-z]+[^\n\|]*|\d{2}:\d{2})", card_text, re.I)
                date_text = date_match.group(1).strip() if date_match else None

                # Neighborhood
                neighborhood = "Sector 6"
                for n in ["Militari", "Drumul Taberei", "Crângași", "Crangasi", "Ghencea", "Politehnica", "Grozăvești", "Lujerului", "Gorjului", "Valea Oltului"]:
                    if n.lower() in card_text.lower() or n.lower() in href.lower():
                        neighborhood = n
                        break

                listings.append(Listing(
                    id=ad_id,
                    portal="anuntul",
                    title=f"{title_text} - 2 Camere",
                    price=price_val,
                    currency="EUR",
                    surface_sqm=surface_val,
                    rooms=rooms,
                    year=year_val,
                    neighborhood=neighborhood,
                    city="Bucuresti",
                    sector="Sector 6",
                    description=card_text[:300] if card_text else None,
                    url=full_url,
                    thumbnail=thumb,
                    images=[thumb] if thumb else [],
                    date_published=date_text
                ))
            except Exception as e:
                logger.debug(f"Error parsing Anuntul card: {e}")

        return listings
