import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Tuple, Optional
import httpx
from jinja2 import Environment, FileSystemLoader
from backend.config import config, BASE_DIR
from backend.scrapers.base import Listing
from backend import database

logger = logging.getLogger("notification.service")

class NotificationService:
    def __init__(self):
        templates_dir = BASE_DIR / "web" / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

    def render_email_html(self, listings: List[Listing], scan_date: Optional[str] = None) -> str:
        if not scan_date:
            scan_date = datetime.now().strftime("%d.%m.%Y, %H:%M")
        template = self.jinja_env.get_template("email_template.html")
        platform_url = "https://robertvatasoiu.github.io/searcholxanunturi/"
        return template.render(
            listings=listings,
            featured_listings=listings[:12],
            total_count=len(listings),
            scan_date=scan_date,
            platform_url=platform_url,
            year_filter=config.search.min_year,
            sector=config.search.sector,
            rooms=config.search.rooms
        )

    def render_email_plaintext(self, listings: List[Listing], scan_date: Optional[str] = None) -> str:
        if not scan_date:
            scan_date = datetime.now().strftime("%d.%m.%Y, %H:%M")
        platform_url = "https://robertvatasoiu.github.io/searcholxanunturi/"
        lines = [
            f"--- APARTAMENTE NOI SECTOR 6 (2 CAMERE, >1977) ---",
            f"Data scanării: {scan_date}",
            f"Total anunțuri găsite: {len(listings)}",
            f"Platformă Live Online: {platform_url}",
            "",
            "Top cele mai recente anunțuri:",
            ""
        ]
        for idx, item in enumerate(listings[:12], 1):
            price_str = f"{int(item.price)} {item.currency}" if item.price else "Preț nespecificat"
            year_str = f"An: {item.year}" if item.year else "Bloc după 1977"
            lines.append(f"{idx}. [{item.portal.upper()}] {item.title}")
            lines.append(f"   Preț: {price_str} | Cartier: {item.neighborhood or 'Sector 6'} | {year_str}")
            lines.append(f"   Link: {item.url}")
            lines.append("")
        if len(listings) > 12:
            lines.append(f"...și încă {len(listings) - 12} anunțuri pe platforma online:")
            lines.append(f"{platform_url}")
        return "\n".join(lines)

    def send_digest(self, listings: List[Listing], recipients: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Sends the digest with new listings to all configured channels (Email & Telegram).
        Marks listings as alerted upon success.
        """
        if not listings:
            logger.info("No new listings to send, skipping notification.")
            return True, "Nu există anunțuri noi de trimis."

        email_success = True
        telegram_success = True
        messages = []

        # 1. Send Email if enabled
        smtp_cfg = config.smtp
        if smtp_cfg.enabled:
            target_recipients = recipients or smtp_cfg.recipient_emails
            if target_recipients:
                html_content = self.render_email_html(listings)
                plain_content = self.render_email_plaintext(listings)
                subject = f"Radar Imobiliar Sector 6 — {len(listings)} Anunturi Noi ({datetime.now().strftime('%d.%m.%Y')})"

                try:
                    if smtp_cfg.provider == "resend" and smtp_cfg.resend_api_key:
                        self._send_via_resend(subject, html_content, plain_content, target_recipients)
                    elif smtp_cfg.provider == "brevo" and smtp_cfg.brevo_api_key:
                        self._send_via_brevo(subject, html_content, plain_content, target_recipients)
                    else:
                        self._send_via_smtp(subject, html_content, plain_content, target_recipients)
                    
                    database.log_alert_history(target_recipients, len(listings), "success")
                    messages.append(f"Email trimis către {len(target_recipients)} adrese ({len(listings)} anunțuri).")
                except Exception as e:
                    err_msg = f"Eroare trimitere email: {str(e)}"
                    logger.error(err_msg, exc_info=True)
                    database.log_alert_history(target_recipients, len(listings), "failed", err_msg)
                    email_success = False
                    messages.append(err_msg)

        # 2. Send Telegram if enabled
        tg_cfg = config.telegram
        if tg_cfg.enabled and tg_cfg.bot_token and tg_cfg.chat_id:
            try:
                self.send_telegram_digest(listings)
                messages.append(f"Notificare Telegram trimisă ({len(listings)} anunțuri).")
            except Exception as e:
                err_msg = f"Eroare Telegram: {str(e)}"
                logger.error(err_msg, exc_info=True)
                telegram_success = False
                messages.append(err_msg)

        if not smtp_cfg.enabled and not tg_cfg.enabled:
            return False, "Niciun canal de notificare nu este activat (activați Email sau Telegram în Setări)."

        # Mark listings as alerted
        if email_success or telegram_success:
            listing_ids = [it.id for it in listings]
            database.mark_listings_as_alerted(listing_ids)

        final_success = email_success or telegram_success
        return final_success, " | ".join(messages)

    def send_test_email(self, recipient: str) -> Tuple[bool, str]:
        sample_listings = [
            Listing(
                id="test_1",
                portal="olx",
                title="[TEST] Apartament 2 camere modern, renovat, Drumul Taberei",
                price=89500,
                currency="EUR",
                surface_sqm=54.5,
                rooms=2,
                year=1984,
                neighborhood="Drumul Taberei",
                url="https://www.olx.ro",
                thumbnail="https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&h=450&fit=crop"
            )
        ]
        html_content = self.render_email_html(sample_listings)
        plain_content = self.render_email_plaintext(sample_listings)
        subject = "🧪 Test Configurare Email - Platformă Alerte Imobiliare Sector 6"

        try:
            smtp_cfg = config.smtp
            if smtp_cfg.provider == "resend" and smtp_cfg.resend_api_key:
                self._send_via_resend(subject, html_content, plain_content, [recipient])
            elif smtp_cfg.provider == "brevo" and smtp_cfg.brevo_api_key:
                self._send_via_brevo(subject, html_content, plain_content, [recipient])
            else:
                self._send_via_smtp(subject, html_content, plain_content, [recipient])
            return True, f"Email de test trimis cu succes către {recipient}!"
        except Exception as e:
            return False, f"Eroare trimitere: {str(e)}"

    def send_test_telegram(self) -> Tuple[bool, str]:
        tg_cfg = config.telegram
        if not tg_cfg.bot_token or not tg_cfg.chat_id:
            return False, "Completați Bot Token și Chat ID pentru Telegram."
        
        msg = "🧪 <b>Test Notificare Telegram</b>\n\nConexiunea la botul de alerte Imobiliare Sector 6 funcționează perfect!"
        try:
            url = f"https://api.telegram.org/bot{tg_cfg.bot_token}/sendMessage"
            payload = {
                "chat_id": tg_cfg.chat_id,
                "text": msg,
                "parse_mode": "HTML"
            }
            resp = httpx.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True, "Mesaj de test trimis pe Telegram cu succes!"
            else:
                return False, f"Telegram API Error ({resp.status_code}): {resp.text}"
        except Exception as e:
            return False, f"Eroare Telegram: {str(e)}"

    def send_telegram_digest(self, listings: List[Listing]):
        tg_cfg = config.telegram
        if not tg_cfg.bot_token or not tg_cfg.chat_id:
            return

        header = f"🏠 <b>[{len(listings)} Noi] Apartamente 2 Camere Sector 6 (&gt;1977)</b>\n📅 {datetime.now().strftime('%d.%m.%Y, %H:%M')}\n\n"
        
        # Send top 10 individual items or in batches
        for idx, it in enumerate(listings[:15], 1):
            price_str = f"<b>{int(it.price):,} EUR</b>".replace(",", ".") if it.price else "Preț la cerere"
            year_str = f"An {it.year}" if it.year else "Bloc &gt; 1977"
            surf_str = f" | {it.surface_sqm} mp" if it.surface_sqm else ""
            
            card_msg = (
                f"{idx}. <b>[{it.portal.upper()}]</b> <a href=\"{it.url}\">{it.title}</a>\n"
                f"💰 {price_str} | 📍 {it.neighborhood or 'Sector 6'} | 🏗️ {year_str}{surf_str}\n"
                f"🔗 <a href=\"{it.url}\">Deschide Anunțul pe {it.portal.upper()} &rarr;</a>\n\n"
            )
            
            url = f"https://api.telegram.org/bot{tg_cfg.bot_token}/sendMessage"
            payload = {
                "chat_id": tg_cfg.chat_id,
                "text": header + card_msg if idx == 1 else card_msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            try:
                httpx.post(url, json=payload, timeout=10)
            except Exception as e:
                logger.error(f"Error sending telegram card: {e}")

    def _send_via_resend(self, subject: str, html_body: str, text_body: str, recipients: List[str]):
        smtp_cfg = config.smtp
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {smtp_cfg.resend_api_key}",
            "Content-Type": "application/json"
        }
        sender = smtp_cfg.sender_email if ("@" in smtp_cfg.sender_email and not smtp_cfg.sender_email.endswith("imobiliare-sector6.ro")) else "Imobiliare Sector 6 <onboarding@resend.dev>"
        payload = {
            "from": sender,
            "to": recipients,
            "subject": subject,
            "html": html_body,
            "text": text_body
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Resend API Error ({resp.status_code}): {resp.text}")

    def _send_via_brevo(self, subject: str, html_body: str, text_body: str, recipients: List[str]):
        smtp_cfg = config.smtp
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": smtp_cfg.brevo_api_key,
            "Content-Type": "application/json"
        }
        sender = {"name": smtp_cfg.sender_name, "email": smtp_cfg.sender_email or "alerte@imobiliare.ro"}
        to_list = [{"email": r} for r in recipients]
        payload = {
            "sender": sender,
            "to": to_list,
            "subject": subject,
            "htmlContent": html_body,
            "textContent": text_body
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Brevo API Error ({resp.status_code}): {resp.text}")

    def _send_via_smtp(self, subject: str, html_body: str, text_body: str, recipients: List[str]):
        smtp_cfg = config.smtp
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        sender_header = f"{smtp_cfg.sender_name} <{smtp_cfg.sender_email or smtp_cfg.username or 'alerte-sector6@imobiliare.local'}>"
        msg["From"] = sender_header
        msg["To"] = ", ".join(recipients)

        part1 = MIMEText(text_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        if smtp_cfg.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_cfg.host, smtp_cfg.port, context=context) as server:
                if smtp_cfg.username and smtp_cfg.password:
                    server.login(smtp_cfg.username, smtp_cfg.password)
                server.sendmail(smtp_cfg.sender_email or smtp_cfg.username, recipients, msg.as_string())
        else:
            with smtplib.SMTP(smtp_cfg.host, smtp_cfg.port) as server:
                if smtp_cfg.use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                if smtp_cfg.username and smtp_cfg.password:
                    server.login(smtp_cfg.username, smtp_cfg.password)
                server.sendmail(smtp_cfg.sender_email or smtp_cfg.username, recipients, msg.as_string())

email_service = NotificationService()
