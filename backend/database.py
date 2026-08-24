import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from backend.config import DB_PATH
from backend.scrapers.base import Listing

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id TEXT PRIMARY KEY,
        portal TEXT NOT NULL,
        title TEXT NOT NULL,
        price REAL,
        currency TEXT DEFAULT 'EUR',
        surface_sqm REAL,
        rooms INTEGER DEFAULT 2,
        year INTEGER,
        floor TEXT,
        neighborhood TEXT,
        city TEXT DEFAULT 'Bucuresti',
        sector TEXT DEFAULT 'Sector 6',
        description TEXT,
        url TEXT NOT NULL UNIQUE,
        thumbnail TEXT,
        images_json TEXT,
        date_published TEXT,
        date_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_alerted INTEGER DEFAULT 0,
        alerted_at TIMESTAMP,
        raw_json TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrape_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP,
        portals_scraped TEXT,
        total_found INTEGER DEFAULT 0,
        new_found INTEGER DEFAULT 0,
        status TEXT DEFAULT 'running',
        error_message TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        recipient_count INTEGER DEFAULT 0,
        recipients_json TEXT,
        listings_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'success',
        error_message TEXT
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_portal ON listings (portal)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_alerted ON listings (is_alerted)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_discovered ON listings (date_discovered DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_price ON listings (price)")

    conn.commit()
    conn.close()

def save_listings(listings: List[Listing]) -> Tuple[int, List[Listing]]:
    """
    Saves listings to database.
    Returns (count_of_new_listings, list_of_new_listings).
    """
    if not listings:
        return 0, []

    conn = get_db_connection()
    cursor = conn.cursor()

    new_listings: List[Listing] = []

    for item in listings:
        # Check if already exists by id or url
        cursor.execute("SELECT id, is_alerted FROM listings WHERE id = ? OR url = ?", (item.id, item.url))
        row = cursor.fetchone()

        if row is None:
            # Brand new listing
            cursor.execute("""
            INSERT INTO listings (
                id, portal, title, price, currency, surface_sqm, rooms, year,
                floor, neighborhood, city, sector, description, url, thumbnail,
                images_json, date_published, date_discovered, is_alerted, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                item.id,
                item.portal,
                item.title,
                item.price,
                item.currency,
                item.surface_sqm,
                item.rooms,
                item.year,
                item.floor,
                item.neighborhood,
                item.city,
                item.sector,
                item.description,
                item.url,
                item.thumbnail,
                json.dumps(item.images),
                item.date_published,
                item.date_discovered.isoformat(),
                json.dumps(item.raw_data) if item.raw_data else None
            ))
            new_listings.append(item)
        else:
            # Update price or other attributes if changed, but keep is_alerted status
            cursor.execute("""
            UPDATE listings SET
                title = ?,
                price = ?,
                thumbnail = COALESCE(?, thumbnail),
                year = COALESCE(?, year),
                neighborhood = COALESCE(?, neighborhood),
                description = COALESCE(?, description)
            WHERE id = ?
            """, (
                item.title,
                item.price,
                item.thumbnail,
                item.year,
                item.neighborhood,
                item.description,
                row["id"]
            ))

    conn.commit()
    conn.close()
    return len(new_listings), new_listings

def get_unalerted_listings() -> List[Listing]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM listings 
    WHERE is_alerted = 0 
    ORDER BY date_discovered DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    return [_row_to_listing(r) for r in rows]

def mark_listings_as_alerted(listing_ids: List[str]):
    if not listing_ids:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat()
    placeholders = ",".join("?" for _ in listing_ids)
    cursor.execute(f"""
    UPDATE listings 
    SET is_alerted = 1, alerted_at = ? 
    WHERE id IN ({placeholders})
    """, [now_str] + listing_ids)
    conn.commit()
    conn.close()

def mark_all_as_alerted():
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat()
    cursor.execute("UPDATE listings SET is_alerted = 1, alerted_at = ?", (now_str,))
    conn.commit()
    conn.close()

def get_all_listings(
    portal: Optional[str] = None,
    neighborhood: Optional[str] = None,
    is_alerted: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[int, List[Listing]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM listings WHERE 1=1"
    params: List[Any] = []

    if portal and portal.lower() != "all":
        query += " AND portal = ?"
        params.append(portal.lower())

    if neighborhood and neighborhood.lower() != "all":
        query += " AND neighborhood LIKE ?"
        params.append(f"%{neighborhood}%")

    if is_alerted is not None:
        query += " AND is_alerted = ?"
        params.append(1 if is_alerted else 0)

    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)

    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)

    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR neighborhood LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])

    # Count total matching
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # Order and paginate
    query += " ORDER BY date_discovered DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return total, [_row_to_listing(r) for r in rows]

def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM listings")
    total_listings = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listings WHERE is_alerted = 0")
    new_unalerted = cursor.fetchone()[0]

    cursor.execute("SELECT portal, COUNT(*) as cnt FROM listings GROUP BY portal")
    by_portal = {row["portal"]: row["cnt"] for row in cursor.fetchall()}

    cursor.execute("SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 1")
    last_run_row = cursor.fetchone()
    last_run = dict(last_run_row) if last_run_row else None

    cursor.execute("SELECT * FROM alert_history ORDER BY id DESC LIMIT 1")
    last_alert_row = cursor.fetchone()
    last_alert = dict(last_alert_row) if last_alert_row else None

    cursor.execute("SELECT DISTINCT neighborhood FROM listings WHERE neighborhood IS NOT NULL")
    neighborhoods = [r[0] for r in cursor.fetchall() if r[0]]

    conn.close()

    return {
        "total_listings": total_listings,
        "new_unalerted": new_unalerted,
        "by_portal": by_portal,
        "last_run": last_run,
        "last_alert": last_alert,
        "neighborhoods": sorted(neighborhoods)
    }

def log_scrape_run_start(portals: List[str]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO scrape_runs (portals_scraped, status)
    VALUES (?, 'running')
    """, (",".join(portals),))
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id

def log_scrape_run_end(run_id: int, total_found: int, new_found: int, status: str = "success", error: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE scrape_runs
    SET finished_at = CURRENT_TIMESTAMP,
        total_found = ?,
        new_found = ?,
        status = ?,
        error_message = ?
    WHERE id = ?
    """, (total_found, new_found, status, error, run_id))
    conn.commit()
    conn.close()

def log_alert_history(recipients: List[str], listings_count: int, status: str = "success", error: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO alert_history (recipient_count, recipients_json, listings_count, status, error_message)
    VALUES (?, ?, ?, ?, ?)
    """, (len(recipients), json.dumps(recipients), listings_count, status, error))
    conn.commit()
    conn.close()

def _row_to_listing(row: sqlite3.Row) -> Listing:
    images = []
    if row["images_json"]:
        try:
            images = json.loads(row["images_json"])
        except Exception:
            pass

    date_disc = datetime.fromisoformat(row["date_discovered"]) if row["date_discovered"] else datetime.utcnow()

    return Listing(
        id=row["id"],
        portal=row["portal"],
        title=row["title"],
        price=row["price"],
        currency=row["currency"] or "EUR",
        surface_sqm=row["surface_sqm"],
        rooms=row["rooms"] or 2,
        year=row["year"],
        floor=row["floor"],
        neighborhood=row["neighborhood"],
        city=row["city"] or "Bucuresti",
        sector=row["sector"] or "Sector 6",
        description=row["description"],
        url=row["url"],
        thumbnail=row["thumbnail"],
        images=images,
        date_published=row["date_published"],
        date_discovered=date_disc,
        is_alerted=bool(row["is_alerted"])
    )

# Initialize database tables immediately
init_db()
