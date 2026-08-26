import json
import logging
from typing import List, Optional
from curl_cffi import requests
from bs4 import BeautifulSoup
from backend.scrapers.base import BaseScraper, Listing

logger = logging.getLogger("scrapers.storia")

class StoriaScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="storia")
        self.base_url = "https://www.storia.ro"

    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        results: List[Listing] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        rooms_param = "%5BTWO%5D" if rooms == 2 else f"%5B{rooms}%5D"

        for page in range(1, max_pages + 1):
            url = (
                f"{self.base_url}/ro/cautare/vanzare/apartament/bucuresti/sectorul-6"
                f"?by=LATEST&roomsNumber={rooms_param}&buildYearMin={min_year}"
            )
            if page > 1:
                url += f"&page={page}"

            try:
                logger.info(f"Fetching Storia page {page}: {url}")
                resp = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Storia page {page} returned status {resp.status_code}")
                    break

                page_listings = self._parse_page(resp.text, min_year, rooms)
                if not page_listings:
                    break
                results.extend(page_listings)
            except Exception as e:
                logger.error(f"Error fetching Storia page {page}: {e}")
                break

        unique = {}
        for item in results:
            if item.id not in unique:
                unique[item.id] = item
        return list(unique.values())

    def _parse_page(self, html: str, min_year: int, rooms: int) -> List[Listing]:
        listings: List[Listing] = []
        soup = BeautifulSoup(html, "html.parser")

        # Extract __NEXT_DATA__
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                data = json.loads(script.string)
                page_props = data.get("props", {}).get("pageProps", {})
                search_ads = page_props.get("data", {}).get("searchAds", {})
                items = search_ads.get("items", [])

                for it in items:
                    listing = self._parse_storia_item(it, min_year, rooms)
                    if listing:
                        listings.append(listing)
                if listings:
                    return listings
            except Exception as e:
                logger.warning(f"Error parsing Storia __NEXT_DATA__: {e}")

        # Fallback HTML parsing
        cards = soup.select("[data-cy=\"listing-item\"], article[data-cy=\"ad-card\"]")
        for card in cards:
            try:
                a_tag = card.select_one("a[href*=\"/ro/oferta/\"]") or card.find("a")
                if not a_tag or not a_tag.has_attr("href"):
                    continue
                href = a_tag["href"]
                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                title_el = card.select_one("h3, [data-cy=\"listing-item-title\"]")
                title = title_el.text.strip() if title_el else "Apartament 2 camere Storia"
                
                slug = href.rstrip("/").split("/")[-1]
                ad_id = Listing.generate_id("storia", slug)

                img_el = card.select_one("img")
                thumb = img_el.get("src") if img_el else None

                listings.append(Listing(
                    id=ad_id,
                    portal="storia",
                    title=title,
                    rooms=rooms,
                    city="Bucuresti",
                    sector="Sector 6",
                    url=full_url,
                    thumbnail=thumb,
                    images=[thumb] if thumb else []
                ))
            except Exception as e:
                logger.debug(f"Error in Storia fallback card: {e}")

        return listings

    def _parse_storia_item(self, it: dict, min_year: int, rooms: int) -> Optional[Listing]:
        slug = it.get("slug")
        if not slug:
            return None

        ad_id = Listing.generate_id("storia", str(it.get("id") or slug))
        url = f"{self.base_url}/ro/oferta/{slug}"
        title = it.get("title") or "Apartament 2 camere Sector 6"

        # Price
        price_obj = it.get("totalPrice", {})
        price_val = price_obj.get("value")
        currency = price_obj.get("currency", "EUR")

        # Check if rental
        from backend.transaction_filter import is_rental_or_invalid_transaction
        is_rental, rent_reason = is_rental_or_invalid_transaction(
            title=title,
            description=str(it),
            url=url,
            price=price_val,
            currency=currency
        )
        if is_rental:
            logger.info(f"Discarding Storia rental ad: '{title}' | Reason: {rent_reason}")
            return None

        # Surface
        surface = it.get("areaInSquareMeters")

        # Year & text check
        from backend.year_filter import evaluate_listing_year
        build_year = it.get("buildYear")
        is_valid, detected_yr, reason = evaluate_listing_year(
            explicit_year=build_year,
            title=title,
            description=str(it),
            min_year=min_year
        )
        if not is_valid:
            logger.info(f"Discarding Storia ad <= 1977: '{title}' | Reason: {reason}")
            return None
        
        final_year = build_year or detected_yr

        # Location details
        location_obj = it.get("location", {})
        reverse_geo = location_obj.get("reverseGeocoding", {}).get("locations", [])
        district_name = None
        for loc in reverse_geo:
            if loc.get("locationLevel") == "district":
                district_name = loc.get("name")
                break
        if not district_name and reverse_geo:
            district_name = reverse_geo[-1].get("name")

        # Photos
        photos = []
        for img in it.get("images", []):
            if isinstance(img, dict):
                src = img.get("large") or img.get("medium") or img.get("small")
                if src:
                    photos.append(src)
            elif isinstance(img, str):
                photos.append(img)
        thumbnail = photos[0] if photos else None

        # Floor
        floor = it.get("floor")

        # Date
        created = it.get("dateCreated") or it.get("dateCreatedFirst")

        return Listing(
            id=ad_id,
            portal="storia",
            title=title,
            price=float(price_val) if price_val is not None else None,
            currency=currency,
            surface_sqm=float(surface) if surface is not None else None,
            rooms=rooms,
            year=build_year,
            floor=str(floor) if floor is not None else None,
            neighborhood=district_name or "Sector 6",
            city="Bucuresti",
            sector="Sector 6",
            description=None,
            url=url,
            thumbnail=thumbnail,
            images=photos,
            date_published=created,
            raw_data=it
        )
