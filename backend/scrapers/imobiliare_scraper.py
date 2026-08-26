import re
import logging
from typing import List, Optional
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing

logger = logging.getLogger("scrapers.imobiliare")

class ImobiliareScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="imobiliare")
        self.base_url = "https://www.imobiliare.ro"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9",
            "Referer": "https://www.google.ro/"
        }

        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/vanzare-apartamente/bucuresti/sector-6?numar_camere={rooms}&an_constructie_min={min_year}"
            if page > 1:
                url += f"&pagina={page}"

            try:
                logger.info(f"Fetching Imobiliare page {page}: {url}")
                resp = requests.get(url, headers=headers, impersonate="safari17_0", timeout=20)
                if resp.status_code != 200:
                    logger.warning(f"Imobiliare page {page} returned status {resp.status_code}")
                    break

                page_listings = self._parse_page(resp.text, min_year, rooms)
                if not page_listings:
                    break
                results.extend(page_listings)
            except Exception as e:
                logger.error(f"Error fetching Imobiliare page {page}: {e}")
                break

        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        soup = BeautifulSoup(html, "html.parser")

        # Find all listing links matching /oferta/
        offer_links = soup.find_all("a", href=lambda h: h and "/oferta/" in h)
        seen_urls = set()

        for a in offer_links:
            href = a["href"]
            if href in seen_urls:
                continue
            seen_urls.add(href)

            full_url = href if href.startswith("http") else f"{self.base_url}{href}"
            
            # Find parent container with the card details
            container = a
            while container and container.name != "body" and len(container.get_text()) < 60:
                container = container.parent

            if not container:
                continue

            card_text = container.get_text(separator=" | ", strip=True)

            # Check if this card matches 2 rooms and Sector 6
            # Extract ID from URL
            ad_id_match = re.search(r"-(\d+)(?:\?|$)", href)
            ad_id_val = ad_id_match.group(1) if ad_id_match else href.split("/")[-1]
            ad_id = Listing.generate_id("imobiliare", ad_id_val)

            # Title
            title_el = container.find(["h2", "h3", "strong"])
            title = title_el.text.strip() if title_el else a.text.strip()
            if not title or len(title) < 5:
                # generate title from URL slug
                slug = href.split("/")[-1].replace(f"-{ad_id_val}", "").replace("-", " ")
                title = slug.capitalize() if slug else "Apartament 2 camere Sector 6"

            # Price & Rental filter
            from backend.transaction_filter import parse_price, is_rental_or_invalid_transaction
            price_val, currency = parse_price(card_text)

            is_rental, rent_reason = is_rental_or_invalid_transaction(
                title=title,
                description=card_text,
                url=href,
                price=price_val,
                currency=currency
            )
            if is_rental:
                logger.info(f"Discarding Imobiliare rental ad: '{title}' | Reason: {rent_reason}")
                continue

            # Year & pre-1978 validation
            from backend.year_filter import evaluate_listing_year
            is_valid, detected_year, reason = evaluate_listing_year(
                explicit_year=None,
                title=title,
                description=card_text,
                min_year=min_year
            )
            if not is_valid:
                logger.info(f"Discarding Imobiliare ad <= 1977: '{title}' | Reason: {reason}")
                continue

            year_val = detected_year

            # Surface
            surf_match = re.search(r"(\d+(?:[\.,]\d+)?)\s*mp", card_text, re.IGNORECASE)
            surface_val = None
            if surf_match:
                try:
                    surface_val = float(surf_match.group(1).replace(",", "."))
                except ValueError:
                    pass

            # Neighborhood
            neighborhood = "Sector 6"
            for n in ["Militari", "Drumul Taberei", "Crângași", "Crangasi", "Ghencea", "Politehnica", "Grozăvești", "Gro縫vesti", "Lujerului", "Gorjului", "Valea Oltului"]:
                if n.lower() in card_text.lower() or n.lower() in href.lower():
                    neighborhood = n
                    break

            # Image
            img = container.find("img")
            thumb = img.get("src") or img.get("data-src") if img else None
            if thumb and thumb.startswith("//"):
                thumb = "https:" + thumb

            listings.append(Listing(
                id=ad_id,
                portal="imobiliare",
                title=title,
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
                images=[thumb] if thumb else []
            ))

        return listings
