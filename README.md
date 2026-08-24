# 🏢 Platformă Monitorizare & Alerte Imobiliare Sector 6 (București)

Platformă automată dedicată căutării și notificării zilnice pentru anunțuri noi de **apartamente cu 2 camere**, în **Sectorul 6, București**, cu an de construcție **după 1977** (`> 1977`).

Agregă în timp real anunțuri de pe cele mai mari 5 portaluri imobiliare din România:
- 🟢 **OLX.ro**
- 🟠 **Storia.ro**
- 🔴 **Imobiliare.ro**
- 🔵 **Publi24.ro**
- 🟡 **Anunțul.ro (Anunțul Telefonic)**

---

## 🚀 Caracteristici Cheie

1. **Filtrare Precisă**:
   - Locație: București, Sector 6 (Militari, Drumul Taberei, Crângași, Ghencea, Politehnica, Grozăvești, etc.)
   - Tip: Apartamente 2 camere de vânzare
   - An de construcție: `> 1977` (1978 onwards, blocuri noi / după 2000)
2. **Notificare Automată Zilnică (Ora 08:00)**:
   - În fiecare dimineață la ora 08:00 scanează automat toate portalurile.
   - Identifică anunțurile noi (deduplicare inteligentă prin SQLite `listings.db`).
   - Trimite un raport email HTML responsive cu imagini, detalii, preț și link-uri directe către anunțuri.
3. **Panou de Control Web Modern**:
   - Dashboard dark-mode cu glassmorphism.
   - Statistici în timp real (total anunțuri, anunțuri noi, distribuție pe portaluri).
   - Declanșare manuală a căutării ("*Caută Acum*") cu bară de progres și log-uri live.
   - Trimitere instantă a raportului pe email ("*Trimite Raport Email*").
   - Explorator avansat de anunțuri cu filtrare după portal, cartier, preț, cuvinte cheie și status.
   - Configurare simplă din interfață pentru SMTP (Gmail, Yahoo, Outlook, custom) și destinatari.
   - Export anunțuri în CSV / JSON.

---

## 📦 Instalare & Pornire Rapidă

### 1. Clonare & Mediu Virtual

Mediul virtual `venv` este deja configurat în acest folder. Dacă doriți să îl reinstalați:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Pornire Dashboard Web

Rulați scriptul de pornire:

```bash
./start_dashboard.sh
```

Apoi deschideți în browser: **[http://localhost:8000](http://localhost:8000)**

Serverul pornește automat și scheduler-ul de fundal pentru ora 08:00 AM.

---

## ✉️ Configurare Notificări Email (SMTP)

Pentru a primi alertele pe email:
1. Deschideți interfața web la `http://localhost:8000`.
2. Faceți click pe butonul **"⚙️ Setări & SMTP"**.
3. Bifați **"Activează trimiterea automată de email-uri"**.
4. Introduceți datele contului dvs. de email:
   - **Pentru Gmail**:
     - Host: `smtp.gmail.com`
     - Port: `587`
     - Utilizator: `adresa.ta@gmail.com`
     - Parolă: O **Parolă pentru aplicații (App Password)** generată din contul Google (*Securitate -> Verificare în doi pași -> Parole pentru aplicații*).
   - **Pentru Yahoo / Outlook**: Host-ul și portul standard aferente.
5. Adăugați adresa/adresele de email ale destinatarilor (ex: `adresa1@gmail.com, adresa2@yahoo.com`).
6. Faceți click pe **"🧪 Testează conexiunea SMTP"** pentru a valida trimiterea.
7. Faceți click pe **"Salvează Setările"**.

---

## ⏰ Rulare Manuală & Automatizare Cron / macOS Launchd

Puteți rula căutarea și trimiterea emailului oricând doriți direct din terminal sau automatiza prin Cron:

### Rulare Imediată din Terminal:
```bash
./run_daily.sh
```

### Programare via Crontab (în fiecare zi la 08:00):
```bash
crontab -e
```
Adăugați linia:
```cron
0 8 * * * /Users/robertvatasoiu/Desktop/LUCREZ/olx_cautare/run_daily.sh >> /Users/robertvatasoiu/Desktop/LUCREZ/olx_cautare/cron.log 2>&1
```

---

## 📁 Structura Fișierelor

```
olx_cautare/
├── backend/
│   ├── config.py              # Management configurație (config.json)
│   ├── database.py            # SQLite listings.db (anunțuri, dedup, istoric)
│   ├── email_service.py       # Generator HTML email & client SMTP
│   ├── manager.py             # Agregator de căutare multi-portal
│   ├── scheduler.py           # Scheduler APScheduler zilnic ora 08:00
│   └── scrapers/
│       ├── base.py            # Model de date Listing & interfață scraper
│       ├── olx_scraper.py     # Scraper OLX.ro
│       ├── storia_scraper.py  # Scraper Storia.ro
│       ├── imobiliare_scraper.py # Scraper Imobiliare.ro
│       ├── publi24_scraper.py # Scraper Publi24.ro
│       └── anuntul_scraper.py # Scraper Anuntul.ro
├── web/
│   ├── server.py              # Server FastAPI & API REST
│   ├── static/
│   │   ├── css/style.css      # Design modern Dark Glassmorphism
│   │   └── js/app.js          # Interfață dinamică & AJAX
│   └── templates/
│       ├── index.html         # Dashboard principal
│       └── email_template.html# Șablon email alerte zilnice
├── run_daily.sh               # Script pentru rulare zilnică / cron
├── start_dashboard.sh         # Script pornire dashboard web
├── requirements.txt           # Dependențe Python
└── README.md                  # Documentație completă
```
