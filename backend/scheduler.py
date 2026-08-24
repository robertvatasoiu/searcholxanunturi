import logging
import sys
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.config import config
from backend.manager import scraper_manager
from backend.email_service import email_service
from backend import database

logger = logging.getLogger("scheduler")

scheduler: BackgroundScheduler = None

def daily_morning_job():
    """
    Main job executed every morning at 08:00 (or configured time).
    1. Scrapes all enabled portals (OLX, Storia, Imobiliare, Publi24, Anuntul).
    2. Identifies new listings with 2 rooms, Sector 6, year > 1977.
    3. Sends email digest to configured recipients.
    """
    logger.info("=== STARTING SCHEDULED MORNING REAL ESTATE SCAN ===")
    try:
        # Step 1: Run scrapers
        scrape_result = scraper_manager.run_scrape()
        logger.info(f"Scrape completed: {scrape_result['total_found']} found, {scrape_result['new_found']} new.")

        # Step 2: Get all unalerted listings
        unalerted = database.get_unalerted_listings()
        logger.info(f"Total unalerted listings waiting for digest: {len(unalerted)}")

        # Step 3: Send email
        if unalerted:
            success, msg = email_service.send_digest(unalerted)
            logger.info(f"Email digest result: {msg}")
        else:
            logger.info("No unalerted listings to send this morning.")

    except Exception as e:
        logger.error(f"Error executing morning job: {e}", exc_info=True)
    logger.info("=== FINISHED SCHEDULED MORNING SCAN ===")

def start_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        logger.info("Scheduler already running.")
        return

    scheduler = BackgroundScheduler(timezone=config.schedule.timezone)
    hour = config.schedule.hour
    minute = config.schedule.minute

    trigger = CronTrigger(hour=hour, minute=minute, timezone=config.schedule.timezone)
    scheduler.add_job(
        daily_morning_job,
        trigger=trigger,
        id="daily_morning_job",
        name=f"Daily Real Estate Scan at {hour:02d}:{minute:02d}",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Scheduler started. Daily job scheduled at {hour:02d}:{minute:02d} ({config.schedule.timezone}).")

def stop_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")

def get_scheduler_status():
    global scheduler
    if not scheduler or not scheduler.running:
        return {
            "running": False,
            "next_run": None,
            "scheduled_time": f"{config.schedule.hour:02d}:{config.schedule.minute:02d}"
        }
    job = scheduler.get_job("daily_morning_job")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "running": True,
        "next_run": next_run,
        "scheduled_time": f"{config.schedule.hour:02d}:{config.schedule.minute:02d}"
    }

def reschedule(hour: int, minute: int):
    global scheduler
    config.schedule.hour = hour
    config.schedule.minute = minute
    config.save()
    if scheduler and scheduler.running:
        trigger = CronTrigger(hour=hour, minute=minute, timezone=config.schedule.timezone)
        scheduler.reschedule_job("daily_morning_job", trigger=trigger)
        logger.info(f"Rescheduled daily job to {hour:02d}:{minute:02d}.")

if __name__ == "__main__":
    # If run standalone: execute immediate scan or wait on schedule
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        print("Executing instant daily morning scan...")
        daily_morning_job()
    else:
        print("Starting standalone scheduler daemon...")
        start_scheduler()
        try:
            import time
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            stop_scheduler()
