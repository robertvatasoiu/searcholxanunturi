import json
from pathlib import Path
from datetime import datetime
from backend.config import BASE_DIR
from backend import database

STATIC_TEMPLATE = """<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Apartamente 2 Camere Sector 6 (>1977) - Platformă Live</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    __CSS_CONTENT__
    .badge-live {
      background: #10b981;
      color: #fff;
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header>
      <div class="logo-area">
        <div class="logo-icon">🏢</div>
        <div class="brand">
          <h1>Platformă Imobiliare Sector 6</h1>
          <p>
            <span>2 Camere • Construcție &gt; 1977</span>
            <span class="badge-tag">Actualizat: __NOW_STR__</span>
            <span class="badge-live">● LIVE</span>
          </p>
        </div>
      </div>
      <div class="header-actions">
        <span style="font-size: 14px; font-weight: 700; color: #38bdf8;">
          __TOTAL_COUNT__ Anunțuri Active
        </span>
      </div>
    </header>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-label">Total Anunțuri</span>
          <div class="stat-icon">📊</div>
        </div>
        <div class="stat-value" id="statTotal">__TOTAL_COUNT__</div>
        <div class="stat-sub">Centralizate din 5 portaluri</div>
      </div>

      <div class="stat-card emerald">
        <div class="stat-header">
          <span class="stat-label">Actualizare Automată</span>
          <div class="stat-icon">⏰</div>
        </div>
        <div class="stat-value">08:00 AM</div>
        <div class="stat-sub">În fiecare dimineață</div>
      </div>

      <div class="stat-card purple">
        <div class="stat-header">
          <span class="stat-label">Criterii Căutare</span>
          <div class="stat-icon">🎯</div>
        </div>
        <div class="stat-value">2 Camere</div>
        <div class="stat-sub">Sector 6 București (&gt;1977)</div>
      </div>

      <div class="stat-card amber">
        <div class="stat-header">
          <span class="stat-label">Portaluri Sursă</span>
          <div class="stat-icon">🌐</div>
        </div>
        <div class="portals-bar">
          <span class="portal-chip chip-olx">OLX: <strong>__CNT_OLX__</strong></span>
          <span class="portal-chip chip-storia">Storia: <strong>__CNT_STORIA__</strong></span>
          <span class="portal-chip chip-imobiliare">Imobiliare: <strong>__CNT_IMOBILIARE__</strong></span>
          <span class="portal-chip chip-publi24">Publi24: <strong>__CNT_PUBLI24__</strong></span>
          <span class="portal-chip chip-anuntul">Anunțul: <strong>__CNT_ANUNTUL__</strong></span>
        </div>
      </div>
    </div>

    <!-- Filter Card -->
    <div class="filter-card">
      <div class="filter-grid">
        <div class="form-group">
          <label>Cuvinte cheie / Stradă</label>
          <input type="text" id="filterSearch" class="form-control" placeholder="ex: Drumul Taberei, metrou, renovat...">
        </div>

        <div class="form-group">
          <label>Portal Sursă</label>
          <select id="filterPortal" class="form-control">
            <option value="all">Toate portalurile</option>
            <option value="olx">OLX.ro</option>
            <option value="storia">Storia.ro</option>
            <option value="imobiliare">Imobiliare.ro</option>
            <option value="publi24">Publi24.ro</option>
            <option value="anuntul">Anunțul Telefonic</option>
          </select>
        </div>

        <div class="form-group">
          <label>Cartier / Zonă</label>
          <select id="filterNeighborhood" class="form-control">
            <option value="all">Toate zonele</option>
            <option value="Militari">Militari</option>
            <option value="Drumul Taberei">Drumul Taberei</option>
            <option value="Crângași">Crângași</option>
            <option value="Ghencea">Ghencea</option>
            <option value="Politehnica">Politehnica</option>
            <option value="Grozăvești">Grozăvești</option>
            <option value="Lujerului">Lujerului</option>
            <option value="Gorjului">Gorjului</option>
          </select>
        </div>

        <div class="form-group">
          <label>Preț Max (€)</label>
          <input type="number" id="filterMaxPrice" class="form-control" placeholder="ex: 120000">
        </div>

        <div class="form-group">
          <label>Sortare</label>
          <select id="filterSort" class="form-control">
            <option value="newest">Cele mai noi</option>
            <option value="price_asc">Preț crescător</option>
            <option value="price_desc">Preț descrescător</option>
          </select>
        </div>

        <div class="form-group">
          <button id="btnResetFilters" class="btn btn-secondary" style="height: 42px;">
            Resetare
          </button>
        </div>
      </div>
    </div>

    <!-- Listings Header -->
    <div class="listings-header">
      <div class="listings-title">
        <span>Toate Anunțurile Disponibile</span>
        <span id="resultsCount" class="badge-tag" style="margin-left: 8px;">__TOTAL_COUNT__</span>
      </div>
    </div>

    <!-- Listings Grid -->
    <div id="listingsGrid" class="listings-grid"></div>

    <!-- Pagination -->
    <div id="pagination" class="pagination"></div>
  </div>

  <script>
    const ALL_LISTINGS = __JSON_DATA__;
    let currentPage = 1;
    const PAGE_SIZE = 24;

    const filterSearch = document.getElementById('filterSearch');
    const filterPortal = document.getElementById('filterPortal');
    const filterNeighborhood = document.getElementById('filterNeighborhood');
    const filterMaxPrice = document.getElementById('filterMaxPrice');
    const filterSort = document.getElementById('filterSort');
    const btnResetFilters = document.getElementById('btnResetFilters');
    const listingsGrid = document.getElementById('listingsGrid');
    const resultsCount = document.getElementById('resultsCount');
    const pagination = document.getElementById('pagination');

    function applyFilters() {
      const q = filterSearch.value.toLowerCase().trim();
      const portal = filterPortal.value.toLowerCase();
      const neighborhood = filterNeighborhood.value.toLowerCase();
      const maxPrice = parseFloat(filterMaxPrice.value) || null;
      const sort = filterSort.value;

      let filtered = ALL_LISTINGS.filter(it => {
        if (portal !== 'all' && it.portal.toLowerCase() !== portal) return false;
        if (neighborhood !== 'all' && !(it.neighborhood || '').toLowerCase().includes(neighborhood)) return false;
        if (maxPrice && it.price && it.price > maxPrice) return false;
        if (q) {
          const hay = ((it.title || '') + ' ' + (it.neighborhood || '') + ' ' + (it.description || '')).toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      if (sort === 'price_asc') {
        filtered.sort((a, b) => (a.price || 9999999) - (b.price || 9999999));
      } else if (sort === 'price_desc') {
        filtered.sort((a, b) => (b.price || 0) - (a.price || 0));
      }

      resultsCount.textContent = filtered.length;
      renderListings(filtered);
      renderPagination(filtered.length);
    }

    function renderListings(items) {
      const start = (currentPage - 1) * PAGE_SIZE;
      const paginated = items.slice(start, start + PAGE_SIZE);

      if (!paginated.length) {
        listingsGrid.innerHTML = `
          <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-lg);">
            <div style="font-size: 40px; margin-bottom: 12px;">🔍</div>
            <h3 style="color: #fff; margin-bottom: 6px;">Niciun anunț conform filtrelor</h3>
            <p style="font-size: 14px;">Încearcă să resetezi filtrele sau să cauți alt cuvânt cheie.</p>
          </div>
        `;
        return;
      }

      const fallbackImg = "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop";

      listingsGrid.innerHTML = paginated.map(item => {
        const priceFormatted = item.price 
          ? `${Math.round(item.price).toLocaleString("ro-RO")} ${item.currency}` 
          : "Preț la cerere";

        const portalClass = `chip-${item.portal}`;
        const imgUrl = item.thumbnail || fallbackImg;
        const yearBadge = item.year 
          ? `<span class="tag-item highlight-year">🏗️ An ${item.year}</span>`
          : `<span class="tag-item highlight-year">🏗️ &gt;1977</span>`;

        const surfBadge = item.surface_sqm 
          ? `<span class="tag-item">📐 ${item.surface_sqm} mp</span>` 
          : "";

        return `
          <div class="listing-card">
            <div class="listing-img-box">
              <img src="${imgUrl}" alt="${escapeHtml(item.title)}" class="listing-img" onerror="this.src='${fallbackImg}'">
              <span class="portal-badge-corner portal-chip ${portalClass}">${item.portal}</span>
            </div>
            <div class="listing-content">
              <div class="listing-price-row">
                <div class="listing-price">${priceFormatted}</div>
              </div>
              <a href="${item.url}" target="_blank" class="listing-card-title" title="${escapeHtml(item.title)}">
                ${escapeHtml(item.title)}
              </a>
              <div class="listing-tags">
                <span class="tag-item">📍 ${item.neighborhood || "Sector 6"}</span>
                <span class="tag-item">🚪 2 Camere</span>
                ${yearBadge}
                ${surfBadge}
              </div>
              <div class="listing-footer">
                <span class="listing-date">București, Sector 6</span>
                <a href="${item.url}" target="_blank" class="btn btn-secondary btn-sm" style="font-weight: 700;">
                  Vezi Anunț &rarr;
                </a>
              </div>
            </div>
          </div>
        `;
      }).join("");
    }

    function renderPagination(totalItems) {
      const totalPages = Math.ceil(totalItems / PAGE_SIZE);
      if (totalPages <= 1) {
        pagination.innerHTML = "";
        return;
      }

      let html = `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">« Înapoi</button>`;
      for (let p = Math.max(1, currentPage - 2); p <= Math.min(totalPages, currentPage + 2); p++) {
        html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
      }
      html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">Înainte »</button>`;
      pagination.innerHTML = html;
    }

    function goToPage(p) {
      currentPage = p;
      applyFilters();
      window.scrollTo({ top: 350, behavior: 'smooth' });
    }

    function escapeHtml(text) {
      if (!text) return "";
      return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // Listeners
    filterSearch.addEventListener('input', () => { currentPage = 1; applyFilters(); });
    filterPortal.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    filterNeighborhood.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    filterMaxPrice.addEventListener('input', () => { currentPage = 1; applyFilters(); });
    filterSort.addEventListener('change', () => { currentPage = 1; applyFilters(); });

    btnResetFilters.addEventListener('click', () => {
      filterSearch.value = '';
      filterPortal.value = 'all';
      filterNeighborhood.value = 'all';
      filterMaxPrice.value = '';
      filterSort.value = 'newest';
      currentPage = 1;
      applyFilters();
    });

    // Init
    applyFilters();
  </script>
</body>
</html>
"""

def generate_static_dashboard(output_path: Path = None) -> Path:
    if output_path is None:
        docs_dir = BASE_DIR / "docs"
        docs_dir.mkdir(exist_ok=True)
        output_path = docs_dir / "index.html"

    # Get all listings from database
    total, listings = database.get_all_listings(limit=2000)
    stats = database.get_stats()
    
    listings_data = [it.model_dump() for it in listings]
    now_str = datetime.now().strftime("%d.%m.%Y, %H:%M")

    # Read base CSS
    css_file = BASE_DIR / "web" / "static" / "css" / "style.css"
    css_content = css_file.read_text(encoding="utf-8") if css_file.exists() else ""

    by_portal = stats.get('by_portal', {})
    
    html = STATIC_TEMPLATE
    html = html.replace("__CSS_CONTENT__", css_content)
    html = html.replace("__NOW_STR__", now_str)
    html = html.replace("__TOTAL_COUNT__", str(len(listings_data)))
    html = html.replace("__CNT_OLX__", str(by_portal.get('olx', 0)))
    html = html.replace("__CNT_STORIA__", str(by_portal.get('storia', 0)))
    html = html.replace("__CNT_IMOBILIARE__", str(by_portal.get('imobiliare', 0)))
    html = html.replace("__CNT_PUBLI24__", str(by_portal.get('publi24', 0)))
    html = html.replace("__CNT_ANUNTUL__", str(by_portal.get('anuntul', 0)))
    html = html.replace("__JSON_DATA__", json.dumps(listings_data, default=str, ensure_ascii=False))

    output_path.write_text(html, encoding="utf-8")
    return output_path

if __name__ == "__main__":
    out = generate_static_dashboard()
    print(f"Static dashboard generated successfully at: {out}")
