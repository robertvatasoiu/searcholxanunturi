from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib

class Listing(BaseModel):
    id: str  # Unique ID, e.g. olx_12345 or md5 hash of URL
    portal: str  # olx, storia, imobiliare, publi24, anuntul
    title: str
    price: Optional[float] = None
    currency: str = "EUR"
    surface_sqm: Optional[float] = None
    rooms: int = 2
    year: Optional[int] = None
    floor: Optional[str] = None
    neighborhood: Optional[str] = None
    city: str = "Bucuresti"
    sector: str = "Sector 6"
    description: Optional[str] = None
    url: str
    thumbnail: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    date_published: Optional[str] = None
    date_discovered: datetime = Field(default_factory=datetime.utcnow)
    is_alerted: bool = False
    raw_data: Optional[Dict[str, Any]] = None

    @staticmethod
    def generate_id(portal: str, identifier: str) -> str:
        clean_id = str(identifier).strip()
        if not clean_id:
            clean_id = hashlib.md5(portal.encode()).hexdigest()
        return f"{portal}_{clean_id}"

class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_listings(self, min_year: int = 1978, rooms: int = 2, max_pages: int = 2) -> List[Listing]:
        """Fetch and parse apartment listings from the real estate portal."""
        pass
