# 🏢 Platformă Monitorizare & Alerte Imobiliare Sector 6 (București)

Platformă automată dedicată căutării, filtrării stricte și notificării zilnice pentru anunțuri noi de **apartamente cu 2 camere**, în **Sectorul 6, București**, cu an de construcție **după 1977** (`> 1977`, minim 1978 sau blocuri noi).

Agregă în timp real anunțuri de pe cele mai mari 5 portaluri imobiliare din România:
- 🟢 **OLX.ro**
- 🟠 **Storia.ro**
- 🔴 **Imobiliare.ro**
- 🔵 **Publi24.ro**
- 🟡 **Anunțul.ro (Anunțul Telefonic)**

---

## 🌐 Platforma Online Live (GitHub Pages)

Platforma este găzduită online 100% gratuit și disponibilă permanent la:
👉 **[https://robertvatasoiu.github.io/searcholxanunturi/](https://robertvatasoiu.github.io/searcholxanunturi/)**

* **Optimizat pentru telefon:** Antetul face scroll natural odată cu pagina și nu blochează ecranul.
* **Filtrare dinamică:** Căutare rapidă după stradă/metrou, filtrare după cartier (*Drumul Taberei, Militari, Crângași, Politehnica, Grozăvești, Lujerului, Gorjului etc.*) și sortare după preț.

---

## ⚡ Căutare la Cerere Direct de pe Telefon (Laptop Oprit)

Pe platforma online găsești butonul **„⚡ Caută Acum în Cloud”**. 
Când apeși pe el de pe telefon sau calculator, acesta pornește instant mașina virtuală din **GitHub Actions**, scanează toate cele 5 portaluri, trimite notificarea și actualizează platforma în aproximativ 30-45 de secunde!

### 🔑 Configurare Token (O singură dată per telefon/dispozitiv):
Pentru ca telefonul tău să aibă permisiunea de a comanda serverul GitHub:
1. La prima apăsare a butonului pe telefon, se va deschide o fereastră.
2. Apasă pe link-ul: **[Generare Token GitHub](https://github.com/settings/tokens/new?scopes=repo,workflow&description=Imobiliare+Sector+6+Trigger)**.
3. Derulează în jos pe pagina GitHub și apasă butonul verde **„Generate token”**.
4. Copiază token-ul generat (începe cu `ghp_...`) și lipește-l în căsuță.
5. Se salvează în memoria browserului (`localStorage`) și nu va mai trebui introdus niciodată pe acel dispozitiv.

---

## 🔍 Filtrare Avansată a Anului de Construcție (>1977)

Platforma include un modul dedicat de validare ([backend/year_filter.py](backend/year_filter.py)) care elimină erorile și trucurile de marketing ale agențiilor imobiliare:
* **Prioritate pentru anul de construcție al blocului:** Dacă un vânzător pune în titlu *„Apartament renovat 2026”*, dar în text scrie *„bloc construit în 1972”*, sistemul identifică anul real al structurii și **respinge automat anunțul**.
* **Detecție extinsă pre-1978:** Caută sintagme precum *„bloc '68”*, *„construit în 1974”*, *„înainte de 1977”*, *„bloc rusesc”*, *„pre-1977”*.
* **Verificare completă:** Analizează titlul, descrierea integrală, parametrii tehnici și etichetele portalului.

---

## ✉️ Alerte Zilnice Inteligente (Ora 08:00 AM)

* **Email Compact & Rapid:** Trimite un email curat cu **Top 12 cele mai noi anunțuri** ale dimineții (pentru a se încărca instant și a nu fi trunchiat de Gmail) și un buton mare:
  👉 **„🌐 Deschide Platforma Online (Vezi Toate Anunțurile) →”**
* **Opțiuni de Trimitere fără Cont Personal:**
  1. **Resend API (Recomandat):** Trimite de la o adresă de sistem (`onboarding@resend.dev`) fără a expune parola sau adresa ta personală.
  2. **Telegram Bot:** Notificări push instant cu poze și linkuri direct pe telefon în aplicația Telegram.
  3. **SMTP Clasic:** Opțiune pentru servere dedicate.

---

## ☁️ Automatizare 24/7 în GitHub Actions

Workflow-ul [.github/workflows/daily_scan.yml](.github/workflows/daily_scan.yml) rulează complet autonom în cloud:
1. **La ora 08:00 AM (ora României)** pornește automat serverul GitHub.
2. Descarcă baza de date `data/listings.db` salvată în repository.
3. Rulează scrapers-urile pe cele 5 portaluri și compară cu anunțurile existente (pentru a nu trimite duplicate).
4. Trimite notificarea pe Email / Telegram.
5. Regenerează pagina web `docs/index.html` și o publică pe **GitHub Pages**.
6. Salvează baza de date actualizată direct în repozitoriu printr-un commit automat.

### Secrete GitHub Necesare (Settings -> Secrets and variables -> Actions):
* `RESEND_API_KEY`: Cheia gratuită de pe [resend.com](https://resend.com).
* `RECIPIENT_EMAIL`: Adresa ta de email unde primești alertele.
* *(Opțional)* `TELEGRAM_BOT_TOKEN` și `TELEGRAM_CHAT_ID` pentru Telegram.

---

## 💻 Rulare Locală pe Mac / PC (Opțional)

Dacă doriți să porniți serverul web și interfața locală de administrare:

```bash
# 1. Activare mediu virtual și instalare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Pornire Panou de Control Web Local
./start_dashboard.sh
# Deschide în browser: http://localhost:8000

# 3. Rulare scanare manuală din terminal
./run_daily.sh
```

---

## 📁 Structura Proiectului

```
olx_cautare/
├── .github/workflows/
│   └── daily_scan.yml         # Automatizare GitHub Actions zilnic la ora 08:00
├── backend/
│   ├── cloud_runner.py        # Executabil pentru mediul cloud / GitHub Actions
│   ├── config.py              # Management setări (SMTP, Resend, Telegram, Căutare)
│   ├── database.py            # SQLite listings.db & deduplicare anunțuri
│   ├── email_service.py       # Generator email HTML compact & trimitere Resend/SMTP/Telegram
│   ├── export_static.py       # Generator platformă web statică pentru GitHub Pages
│   ├── manager.py             # Coordonator multi-portal & poartă de filtrare an
│   ├── scheduler.py           # APScheduler pentru rulare automată locală
│   ├── year_filter.py         # Motor de validare strictă a anului de construcție (>1977)
│   └── scrapers/
│       ├── base.py            # Model unificat Listing
│       ├── olx_scraper.py     # Scraper OLX.ro
│       ├── storia_scraper.py  # Scraper Storia.ro
│       ├── imobiliare_scraper.py # Scraper Imobiliare.ro
│       ├── publi24_scraper.py # Scraper Publi24.ro
│       └── anuntul_scraper.py # Scraper Anunțul.ro (Anunțul Telefonic)
├── docs/
│   └── index.html             # Platforma live găzduită pe GitHub Pages
├── web/
│   ├── server.py              # Server FastAPI local cu REST API
│   ├── static/css/style.css   # Stiluri moderne Dark Mode & Mobile Responsive
│   ├── static/js/app.js       # Interfață dinamică panou local
│   └── templates/
│       ├── index.html         # Șablon dashboard local
│       └── email_template.html# Șablon email alerte
├── config.example.json        # Șablon configurație fără date secrete
├── run_daily.sh               # Script rulare zilnică locală
├── start_dashboard.sh         # Script pornire dashboard local
├── requirements.txt           # Dependențe Python
└── README.md                  # Documentație completă
```
