import os
import sys
import logging
from backend.config import config
from backend.manager import scraper_manager
from backend.email_service import email_service
from backend import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cloud.runner")

def run_cloud_job():
    """
    Cloud / CI/CD / GitHub Actions Runner.
    Allows configuring settings via Environment Variables or config.json.
    """
    # Override settings from Environment Variables if present (e.g. GitHub Actions Secrets)
    resend_key = os.getenv("RESEND_API_KEY")
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")

    if resend_key:
        config.smtp.enabled = True
        config.smtp.provider = "resend"
        config.smtp.resend_api_key = resend_key
        if recipient_email:
            config.smtp.recipient_emails = [r.strip() for r in recipient_email.split(",")]

    if tg_token and tg_chat:
        config.telegram.enabled = True
        config.telegram.bot_token = tg_token
        config.telegram.chat_id = tg_chat

    logger.info("--- Starting Cloud Real Estate Scan (Sector 6, 2 Camere, >1977) ---")
    
    # 1. Scrape all portals
    res = scraper_manager.run_scrape()
    logger.info(f"Scan complete: {res['total_found']} found, {res['new_found']} new.")

    # 2. Generate updated static dashboard for GitHub Pages
    try:
        from backend.export_static import generate_static_dashboard
        out = generate_static_dashboard()
        logger.info(f"Generated static live dashboard at: {out}")
    except Exception as e:
        logger.error(f"Error generating static dashboard: {e}")

    # 3. Get unalerted listings and send digest
    unalerted = database.get_unalerted_listings()
    logger.info(f"Unalerted listings: {len(unalerted)}")

    if unalerted:
        success, msg = email_service.send_digest(unalerted)
        logger.info(f"Notification result: {msg}")
    else:
        logger.info("No new listings found in this run.")

if __name__ == "__main__":
    run_cloud_job()
