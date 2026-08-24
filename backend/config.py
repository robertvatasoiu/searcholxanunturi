import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "listings.db"

class SMTPSettings(BaseModel):
    enabled: bool = False
    provider: str = "smtp"  # "smtp", "resend", "brevo"
    # For standard SMTP
    host: str = "smtp.gmail.com"
    port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    username: str = ""
    password: str = ""
    sender_email: str = "alerte@imobiliare-sector6.ro"
    sender_name: str = "Imobiliare Sector 6 Alerte"
    recipient_emails: List[str] = Field(default_factory=lambda: ["destinatar@exemplu.ro"])
    # For transactional email services (Resend / Brevo) without personal accounts
    resend_api_key: str = ""
    brevo_api_key: str = ""

class TelegramSettings(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""

class SearchSettings(BaseModel):
    rooms: int = 2
    min_year: int = 1978
    sector: str = "Sector 6"
    city: str = "Bucuresti"
    max_price: Optional[float] = None
    enabled_portals: List[str] = Field(default_factory=lambda: [
        "olx", "storia", "imobiliare", "publi24", "anuntul"
    ])

class ScheduleSettings(BaseModel):
    enabled: bool = True
    hour: int = 8
    minute: int = 0
    timezone: str = "Europe/Bucharest"

class AppConfig(BaseModel):
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception as e:
                print(f"Error loading config.json, using defaults: {e}")
        config = cls()
        config.save()
        return config

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

config = AppConfig.load()
