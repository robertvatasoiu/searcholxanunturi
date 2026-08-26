import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from backend.config import config
from backend.scrapers.base import Listing, BaseScraper
from backend.scrapers.olx_scraper import OLXScraper
from backend.scrapers.storia_scraper import StoriaScraper
from backend.scrapers.imobiliare_scraper import ImobiliareScraper
from backend.scrapers.publi24_scraper import Publi24Scraper
from backend.scrapers.anuntul_scraper import AnuntulScraper
from backend import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scraper.manager")

class ScraperManager:
    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {
            "olx": OLXScraper(),
            "storia": StoriaScraper(),
            "imobiliare": ImobiliareScraper(),
            "publi24": Publi24Scraper(),
            "anuntul": AnuntulScraper(),
        }

    def run_scrape(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """
        Executes scraping across all enabled portals.
        Saves discovered listings and returns run statistics.
        """
        search_cfg = config.search
        enabled_portals = [p for p in search_cfg.enabled_portals if p in self.scrapers]
        
        logger.info(f"Starting scraping session for portals: {enabled_portals}")
        run_id = database.log_scrape_run_start(enabled_portals)

        all_listings: List[Listing] = []
        portal_stats: Dict[str, int] = {}
        errors: List[str] = []

        total_portals = len(enabled_portals)
        for idx, portal_key in enumerate(enabled_portals):
            scraper = self.scrapers[portal_key]
            msg = f"Căutare pe {portal_key.upper()}..."
            if progress_callback:
                progress_callback(msg, int((idx / total_portals) * 100))

            try:
                logger.info(f"Running scraper: {portal_key}")
                items = scraper.fetch_listings(
                    min_year=search_cfg.min_year,
                    rooms=search_cfg.rooms,
                    max_pages=2
                )
                
                # Apply strict year filter gatekeeper
                from backend.year_filter import evaluate_listing_year
                valid_items = []
                for it in items:
                    is_valid, detected_yr, reason = evaluate_listing_year(
                        explicit_year=it.year,
                        title=it.title,
                        description=it.description or "",
                        min_year=search_cfg.min_year
                    )
                    if is_valid:
                        if detected_yr and not it.year:
                            it.year = detected_yr
                        valid_items.append(it)
                    else:
                        logger.info(f"Filtered out listing <= 1977 [{it.portal}]: '{it.title}' | Reason: {reason}")

                logger.info(f"Scraper {portal_key} found {len(items)} items ({len(valid_items)} valid post-1977)")
                portal_stats[portal_key] = len(valid_items)
                all_listings.extend(valid_items)
            except Exception as e:
                err_msg = f"Eroare la scraping pe {portal_key}: {str(e)}"
                logger.error(err_msg, exc_info=True)
                errors.append(err_msg)
                portal_stats[portal_key] = 0

        # Save to database and detect new ones
        if progress_callback:
            progress_callback("Salvare anunțuri în baza de date...", 90)

        new_count, new_items = database.save_listings(all_listings)
        
        status = "success" if not errors else ("partial_success" if all_listings else "failed")
        database.log_scrape_run_end(
            run_id=run_id,
            total_found=len(all_listings),
            new_found=new_count,
            status=status,
            error="; ".join(errors) if errors else None
        )

        if progress_callback:
            progress_callback(f"Finalizat! {len(all_listings)} găsite, {new_count} noi.", 100)

        return {
            "run_id": run_id,
            "total_found": len(all_listings),
            "new_found": new_count,
            "portal_stats": portal_stats,
            "errors": errors,
            "new_items": new_items,
            "finished_at": datetime.utcnow().isoformat()
        }

scraper_manager = ScraperManager()
