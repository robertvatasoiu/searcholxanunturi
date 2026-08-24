import io
import csv
import json
import logging
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend.config import config, BASE_DIR, AppConfig, SMTPSettings, SearchSettings, ScheduleSettings
from backend import database
from backend.manager import scraper_manager
from backend.email_service import email_service
from backend.scheduler import start_scheduler, get_scheduler_status, reschedule, daily_morning_job

logger = logging.getLogger("web.server")

app = FastAPI(title="Imobiliare Sector 6 - Platformă Căutare & Notificare")

# Mount static and templates
static_dir = BASE_DIR / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "css").mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)

templates_dir = BASE_DIR / "web" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# In-memory scraping state
scrape_state = {
    "is_running": False,
    "progress": 0,
    "current_message": "Inactiv",
    "last_result": None,
    "logs": []
}

def log_progress(msg: str, progress: int = 0):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    scrape_state["progress"] = progress
    scrape_state["current_message"] = msg
    scrape_state["logs"].append(formatted)
    if len(scrape_state["logs"]) > 100:
        scrape_state["logs"].pop(0)

def run_scrape_background():
    scrape_state["is_running"] = True
    scrape_state["logs"] = []
    log_progress("Pornire proces de scraping...", 5)
    try:
        res = scraper_manager.run_scrape(progress_callback=log_progress)
        scrape_state["last_result"] = res
        log_progress("Căutare finalizată cu succes!", 100)
    except Exception as e:
        log_progress(f"Eroare: {str(e)}", 100)
    finally:
        scrape_state["is_running"] = False

@app.on_event("startup")
async def startup_event():
    # Start the automated daily 08:00 AM scheduler on server boot
    if config.schedule.enabled:
        start_scheduler()

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def get_statistics():
    stats = database.get_stats()
    scheduler_info = get_scheduler_status()
    stats["scheduler"] = scheduler_info
    stats["smtp_enabled"] = config.smtp.enabled
    return stats

@app.get("/api/listings")
async def list_listings(
    portal: Optional[str] = "all",
    neighborhood: Optional[str] = "all",
    is_alerted: Optional[str] = "all",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 24
):
    offset = (page - 1) * limit
    alert_filter = None
    if is_alerted == "new":
        alert_filter = False
    elif is_alerted == "sent":
        alert_filter = True

    total, items = database.get_all_listings(
        portal=portal,
        neighborhood=neighborhood,
        is_alerted=alert_filter,
        min_price=min_price,
        max_price=max_price,
        search=search,
        limit=limit,
        offset=offset
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "items": [item.model_dump() for item in items]
    }

@app.post("/api/scrape/start")
async def start_scraping(background_tasks: BackgroundTasks):
    if scrape_state["is_running"]:
        return JSONResponse({"status": "error", "message": "Un proces de căutare rulează deja!"}, status_code=400)
    background_tasks.add_task(run_scrape_background)
    return {"status": "ok", "message": "Procesul de căutare a fost lansat."}

@app.get("/api/scrape/status")
async def get_scrape_status():
    return scrape_state

class TestEmailRequest(BaseModel):
    recipient: str

@app.post("/api/email/test")
async def test_email(req: TestEmailRequest):
    success, msg = email_service.send_test_email(req.recipient)
    if not success:
        return JSONResponse({"status": "error", "message": msg}, status_code=400)
    return {"status": "ok", "message": msg}

@app.post("/api/telegram/test")
async def test_telegram():
    success, msg = email_service.send_test_telegram()
    if not success:
        return JSONResponse({"status": "error", "message": msg}, status_code=400)
    return {"status": "ok", "message": msg}

@app.post("/api/email/send-digest")
async def send_digest_now():
    unalerted = database.get_unalerted_listings()
    if not unalerted:
        return {"status": "ok", "message": "Nu există anunțuri noi de trimis."}
    success, msg = email_service.send_digest(unalerted)
    if not success:
        return JSONResponse({"status": "error", "message": msg}, status_code=400)
    return {"status": "ok", "message": msg, "count": len(unalerted)}

@app.post("/api/listings/mark-all-alerted")
async def mark_all_alerted():
    database.mark_all_as_alerted()
    return {"status": "ok", "message": "Toate anunțurile au fost marcate ca trimise."}

@app.get("/api/config")
async def get_app_config():
    cfg = config.model_dump()
    if cfg.get("smtp", {}).get("password"):
        cfg["smtp"]["password_set"] = True
        cfg["smtp"]["password"] = "••••••••"
    else:
        cfg["smtp"]["password_set"] = False
    return cfg

class ConfigUpdateRequest(BaseModel):
    smtp: Optional[SMTPSettings] = None
    telegram: Optional[dict] = None
    search: Optional[SearchSettings] = None
    schedule: Optional[ScheduleSettings] = None

@app.post("/api/config")
async def update_app_config(req: ConfigUpdateRequest):
    if req.smtp:
        if req.smtp.password == "••••••••" or req.smtp.password == "":
            req.smtp.password = config.smtp.password
        config.smtp = req.smtp

    if req.telegram:
        from backend.config import TelegramSettings
        config.telegram = TelegramSettings(**req.telegram)

    if req.search:
        config.search = req.search

    if req.schedule:
        old_h = config.schedule.hour
        old_m = config.schedule.minute
        config.schedule = req.schedule
        if old_h != req.schedule.hour or old_m != req.schedule.minute:
            reschedule(req.schedule.hour, req.schedule.minute)

    config.save()
    return {"status": "ok", "message": "Configurația a fost salvată cu succes!"}

@app.get("/api/export")
async def export_listings(format: str = Query("json", enum=["json", "csv"])):
    _, items = database.get_all_listings(limit=10000)
    
    if format == "json":
        data = [it.model_dump() for it in items]
        return JSONResponse(
            content=data,
            headers={"Content-Disposition": "attachment; filename=anunturi_sector6.json"}
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Portal", "Titlu", "Pret", "Moneda", "Camere", "An", "Suprafata_mp", "Cartier", "URL", "Data_Descoperit"])
        for it in items:
            writer.writerow([
                it.id, it.portal, it.title, it.price or "", it.currency,
                it.rooms, it.year or "", it.surface_sqm or "", it.neighborhood or "",
                it.url, it.date_discovered.isoformat()
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=anunturi_sector6.csv"}
        )
