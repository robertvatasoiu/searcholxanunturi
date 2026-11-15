import re
import json
from pathlib import Path
from datetime import datetime
from backend.config import BASE_DIR
from backend import database
from backend.location_filter import is_ground_or_top_floor, is_direct_owner_or_zero_commission

STATIC_TEMPLATE = """<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Apartamente 2 Camere Sector 6 (&gt;1977) — Radar Imobiliar</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    __CSS_CONTENT__
  </style>
</head>
<body>
  <div class="container">
    <!-- Top Navigation Header -->
    <header>
      <div class="brand-section">
        <div class="brand-badge-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="16" height="20" x="4" y="2" rx="2" ry="2"/>
            <path d="M9 22v-4h6v4"/>
            <path d="M8 6h.01"/>
            <path d="M16 6h.01"/>
            <path d="M8 10h.01"/>
            <path d="M16 10h.01"/>
            <path d="M8 14h.01"/>
            <path d="M16 14h.01"/>
          </svg>
        </div>
        <div class="brand-info">
          <h1>
            Radar Imobiliar Sector 6
            <span class="live-pill">
              <span class="live-dot"></span> Live
            </span>
          </h1>
          <div class="brand-meta">
            <span>2 Camere</span>
            <span class="separator">•</span>
            <span>Construcție &gt; 1977</span>
            <span class="separator">•</span>
            <span>Actualizat: __NOW_STR__</span>
          </div>
        </div>
      </div>
      <div class="header-controls">
        <button id="btnTriggerCloudScan" class="btn btn-cloud-run">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          Scanează Acum în Cloud
        </button>
        <button id="btnConfigToken" class="btn btn-secondary btn-icon" title="Setări Token Cloud">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- Cloud Status Banner (Visible during cloud execution) -->
    <div id="cloudStatusBanner" class="cloud-banner">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;">
        <div style="display: flex; align-items: center; gap: 14px;">
          <div class="spinner-icon"></div>
          <div>
            <h4 id="cloudStatusTitle" style="color: var(--text-primary); font-size: 14px; font-weight: 700; margin-bottom: 2px;">
              Scanare lansată în Cloud GitHub Actions...
            </h4>
            <p id="cloudStatusDesc" style="color: var(--text-secondary); font-size: 12px; margin: 0;">
              Se extrag datele în timp real de pe OLX, Storia, Imobiliare, Publi24 și Anunțul.
            </p>
          </div>
        </div>
        <div>
          <span id="cloudTimer" style="background: var(--bg-surface); color: var(--accent-primary); padding: 5px 12px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 700; font-family: var(--font-mono); border: 1px solid var(--border-subtle);">
            0s
          </span>
        </div>
      </div>
    </div>

    <!-- Metrics Row -->
    <div class="metrics-row">
      <div class="metric-box">
        <div class="metric-label">
          <span>Total Anunțuri Active</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
        </div>
        <div class="metric-value">__TOTAL_COUNT__</div>
        <div class="metric-sub">Verificate și filtrate &gt;1977</div>
      </div>

      <div class="metric-box">
        <div class="metric-label">
          <span>Automatizare Cloud</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div class="metric-value" style="color: var(--accent-emerald);">08:00 AM</div>
        <div class="metric-sub">Rulare zilnică GitHub Actions</div>
      </div>

      <div class="metric-box">
        <div class="metric-label">
          <span>Target Geografic</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
        </div>
        <div class="metric-value">Sector 6</div>
        <div class="metric-sub">Militari, Dr. Taberei, Crângași, Poli</div>
      </div>

      <div class="metric-box">
        <div class="metric-label">
          <span>Surse Monitorizate</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        </div>
        <div class="portal-tags-grid" style="margin-top: 8px;">
          <div class="portal-counter-tag olx">OLX <span class="count">__CNT_OLX__</span></div>
          <div class="portal-counter-tag storia">Storia <span class="count">__CNT_STORIA__</span></div>
          <div class="portal-counter-tag imobiliare">Imob <span class="count">__CNT_IMOBILIARE__</span></div>
          <div class="portal-counter-tag publi24">P24 <span class="count">__CNT_PUBLI24__</span></div>
          <div class="portal-counter-tag anuntul">Anunțul <span class="count">__CNT_ANUNTUL__</span></div>
        </div>
      </div>
    </div>

    <!-- Filter & Search Panel -->
    <div class="filter-panel">
      <div class="filter-main-row">
        <div class="input-wrapper">
          <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
          </svg>
          <input type="text" id="filterSearch" class="form-input" placeholder="Caută după stradă, metrou, renovat...">
        </div>

        <div>
          <select id="filterNeighborhood" class="form-select">
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

        <div>
          <input type="number" id="filterMaxPrice" class="form-input" style="padding-left: 14px;" placeholder="Preț Max (€)">
        </div>

        <div>
          <select id="filterSort" class="form-select">
            <option value="newest">Cele mai noi</option>
            <option value="price_asc">Preț crescător</option>
            <option value="price_desc">Preț descrescător</option>
            <option value="sqm_asc">Preț / mp crescător</option>
            <option value="surface_desc">Suprafață descrescătoare</option>
            <option value="price_drop">Scăderi de preț</option>
          </select>
        </div>

        <div>
          <button id="btnResetFilters" class="btn btn-secondary" style="height: 40px; width: 100%;">
            Resetare
          </button>
        </div>
      </div>

      <!-- Quick Portal & Neighborhood Chips -->
      <div class="quick-pills-row">
        <div class="pill-group" id="portalPills">
          <span class="pill-group-label">Portal:</span>
          <button class="chip-btn active" data-portal="all">Toate</button>
          <button class="chip-btn" data-portal="olx">OLX</button>
          <button class="chip-btn" data-portal="storia">Storia</button>
          <button class="chip-btn" data-portal="imobiliare">Imobiliare</button>
          <button class="chip-btn" data-portal="publi24">Publi24</button>
          <button class="chip-btn" data-portal="anuntul">Anunțul</button>
        </div>

        <div class="pill-group" id="pricePills">
          <span class="pill-group-label">Buget:</span>
          <button class="chip-btn" data-price="75000">&lt; 75k €</button>
          <button class="chip-btn" data-price="90000">&lt; 90k €</button>
          <button class="chip-btn" data-price="110000">&lt; 110k €</button>
          <button class="chip-btn" data-price="130000">&lt; 130k €</button>
        </div>
      </div>

      <!-- Smart Quick Filter Chips -->
      <div class="quick-pills-row" style="padding-top: 10px;">
        <div class="pill-group" id="smartFilterPills">
          <span class="pill-group-label">Filtre rapide:</span>
          <button class="chip-btn" id="chipFav" onclick="toggleSmartFilter('fav')">⭐ Favorite (<span id="favCount">0</span>)</button>
          <button class="chip-btn" id="chipRecent" onclick="toggleSmartFilter('recent')">🔥 Ultimele 48h</button>
          <button class="chip-btn" id="chipDrop" onclick="toggleSmartFilter('drop')">📉 Preț redus</button>
          <button class="chip-btn" id="chipOwner" onclick="toggleSmartFilter('owner')">👤 Proprietar / 0% Comision</button>
          <button class="chip-btn" id="chipNoBadFloor" onclick="toggleSmartFilter('noBadFloor')">🚫 Fără Parter / Ultimul etaj</button>
          <button class="chip-btn active" id="chipDedup" onclick="toggleSmartFilter('dedup')">🔗 Grupează duplicatele</button>
          <button class="chip-btn" id="chipHidden" onclick="toggleSmartFilter('hidden')">👁️ Ascunse (<span id="hiddenCount">0</span>)</button>
        </div>
      </div>
    </div>

    <!-- Results Header -->
    <div class="results-bar">
      <div class="results-count-title">
        Afișare: <strong id="resultsCount">__TOTAL_COUNT__</strong> apartamente
      </div>
    </div>

    <!-- Listings Grid -->
    <div id="listingsGrid" class="listings-grid"></div>

    <!-- Pagination -->
    <div id="pagination" class="pagination"></div>
  </div>

  <!-- Token Modal -->
  <div id="tokenModal" class="modal-overlay">
    <div class="modal-box">
      <div class="modal-header">
        <h3>Configurare Cheie GitHub Actions</h3>
        <button class="btn-close" onclick="closeTokenModal()">&times;</button>
      </div>
      <div class="modal-body">
        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 16px;">
          Pentru a putea lansa căutarea direct de pe telefon când laptopul este închis, introduceți un GitHub Personal Access Token (se configurează o singură dată per dispozitiv):
        </p>

        <div style="background: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; margin-bottom: 16px;">
          <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">
            1. Obțineți token-ul în 30 de secunde:
          </div>
          <a href="https://github.com/settings/tokens/new?scopes=repo,workflow&description=Imobiliare+Sector+6+Trigger" target="_blank" style="color: var(--accent-primary); font-size: 12px; font-weight: 600; text-decoration: underline;">
            Deschide Pagina de Generare GitHub &rarr;
          </a>
        </div>

        <div>
          <label style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); display: block; margin-bottom: 6px;">
            Introduceți Token-ul (ghp_...)
          </label>
          <input type="password" id="inputGithubToken" class="form-input" style="padding-left: 14px;" placeholder="ghp_123456789...">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="closeTokenModal()">Anulează</button>
        <button class="btn btn-primary" onclick="saveGithubToken()">Salvează pe acest dispozitiv</button>
      </div>
    </div>
  </div>

  <div id="toastContainer" class="toast-container"></div>

  <script>
    const ALL_LISTINGS = __JSON_DATA__;
    let currentPage = 1;
    const PAGE_SIZE = 24;
    let selectedPortal = 'all';
    let selectedMaxPrice = null;

    const filterSearch = document.getElementById('filterSearch');
    const filterNeighborhood = document.getElementById('filterNeighborhood');
    const filterMaxPrice = document.getElementById('filterMaxPrice');
    const filterSort = document.getElementById('filterSort');
    const btnResetFilters = document.getElementById('btnResetFilters');
    const listingsGrid = document.getElementById('listingsGrid');
    const resultsCount = document.getElementById('resultsCount');
    const pagination = document.getElementById('pagination');

    const btnTriggerCloudScan = document.getElementById('btnTriggerCloudScan');
    const btnConfigToken = document.getElementById('btnConfigToken');
    const tokenModal = document.getElementById('tokenModal');
    const inputGithubToken = document.getElementById('inputGithubToken');
    const cloudStatusBanner = document.getElementById('cloudStatusBanner');
    const cloudTimer = document.getElementById('cloudTimer');
    const cloudStatusTitle = document.getElementById('cloudStatusTitle');
    const cloudStatusDesc = document.getElementById('cloudStatusDesc');

    const GITHUB_REPO_OWNER = 'robertvatasoiu';
    const GITHUB_REPO_NAME = 'searcholxanunturi';
    const WORKFLOW_ID = 'daily_scan.yml';

    let timerInterval = null;
    let pollInterval = null;

    function showToast(msg, type = 'info') {
      const container = document.getElementById('toastContainer');
      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      toast.textContent = msg;
      container.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 250);
      }, 3500);
    }

    function openTokenModal() {
      inputGithubToken.value = localStorage.getItem('gh_token_imob') || '';
      tokenModal.classList.add('active');
    }

    function closeTokenModal() {
      tokenModal.classList.remove('active');
    }

    function saveGithubToken() {
      const token = inputGithubToken.value.trim();
      if (!token) {
        showToast('Introduceți un token valid.', 'error');
        return;
      }
      localStorage.setItem('gh_token_imob', token);
      closeTokenModal();
      showToast('Token salvat pe acest dispozitiv!', 'success');
      triggerCloudScan();
    }

    async function triggerCloudScan() {
      const token = localStorage.getItem('gh_token_imob');
      if (!token) {
        openTokenModal();
        return;
      }

      btnTriggerCloudScan.disabled = true;
      btnTriggerCloudScan.innerHTML = '<div class="spinner-icon" style="width: 14px; height: 14px;"></div> Se pornește...';

      cloudStatusBanner.style.display = 'block';
      cloudStatusTitle.textContent = 'Scanare lansată în Cloud GitHub Actions...';
      cloudStatusDesc.textContent = 'Serverul GitHub extrage datele de pe OLX, Storia, Imobiliare, Publi24 și Anunțul.';

      let seconds = 0;
      if (timerInterval) clearInterval(timerInterval);
      timerInterval = setInterval(() => {
        seconds++;
        cloudTimer.textContent = `${seconds}s`;
      }, 1000);

      try {
        const url = `https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/actions/workflows/${WORKFLOW_ID}/dispatches`;
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Accept': 'application/vnd.github+json',
            'Authorization': `Bearer ${token}`,
            'X-GitHub-Api-Version': '2022-11-28'
          },
          body: JSON.stringify({ ref: 'main' })
        });

        if (res.status === 204 || res.status === 200) {
          showToast('Scanarea a pornit în Cloud!', 'success');
          pollCloudWorkflow(token);
        } else if (res.status === 401 || res.status === 403) {
          showToast('Token GitHub invalid sau expirat.', 'error');
          localStorage.removeItem('gh_token_imob');
          openTokenModal();
          resetTriggerButton();
        } else {
          const errData = await res.json().catch(() => ({}));
          showToast(`Eroare GitHub (${res.status}): ${errData.message || 'Verificați token-ul'}`, 'error');
          resetTriggerButton();
        }
      } catch (err) {
        showToast('Eroare conexiune GitHub API.', 'error');
        resetTriggerButton();
      }
    }

    function pollCloudWorkflow(token) {
      let checks = 0;
      if (pollInterval) clearInterval(pollInterval);
      pollInterval = setInterval(async () => {
        checks++;
        try {
          const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/actions/runs?per_page=1`, {
            headers: {
              'Accept': 'application/vnd.github+json',
              'Authorization': `Bearer ${token}`
            }
          });
          const data = await res.json();
          if (data.workflow_runs && data.workflow_runs.length > 0) {
            const latest = data.workflow_runs[0];
            if (latest.status === 'completed') {
              clearInterval(pollInterval);
              clearInterval(timerInterval);
              cloudStatusTitle.textContent = '✅ Scanare Finalizată cu Succes!';
              cloudStatusDesc.textContent = `Notificarea a fost trimisă. Reîmprospătare pagină...`;
              setTimeout(() => {
                window.location.reload();
              }, 3000);
            } else if (latest.status === 'in_progress') {
              cloudStatusDesc.textContent = `Serverul rulează scraperele pe cele 5 portaluri...`;
            }
          }
        } catch (e) {
          console.error(e);
        }

        if (checks > 60) {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          resetTriggerButton();
        }
      }, 4000);
    }

    function resetTriggerButton() {
      btnTriggerCloudScan.disabled = false;
      btnTriggerCloudScan.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
        Scanează Acum în Cloud
      `;
    }

    btnTriggerCloudScan.addEventListener('click', triggerCloudScan);
    btnConfigToken.addEventListener('click', openTokenModal);

    // Portal Pills Listeners
    document.querySelectorAll('#portalPills .chip-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#portalPills .chip-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedPortal = btn.getAttribute('data-portal');
        currentPage = 1;
        applyFilters();
      });
    });

    // Price Pills Listeners
    document.querySelectorAll('#pricePills .chip-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const isCurrentActive = btn.classList.contains('active');
        document.querySelectorAll('#pricePills .chip-btn').forEach(b => b.classList.remove('active'));
        if (isCurrentActive) {
          selectedMaxPrice = null;
          filterMaxPrice.value = '';
        } else {
          btn.classList.add('active');
          selectedMaxPrice = parseFloat(btn.getAttribute('data-price'));
          filterMaxPrice.value = selectedMaxPrice;
        }
        currentPage = 1;
        applyFilters();
      });
    });

    function applyFilters() {
      const q = filterSearch.value.toLowerCase().trim();
      const neighborhood = filterNeighborhood.value.toLowerCase();
      const inputMax = parseFloat(filterMaxPrice.value) || null;
      const maxPrice = inputMax || selectedMaxPrice;
      const sort = filterSort.value;
      const favSet = getFavSet();
      const hiddenSet = getHiddenSet();
      const nowMs = Date.now();

      updateSmartCounters(favSet, hiddenSet);

      let filtered = ALL_LISTINGS.filter(it => {
        if (smartFilters.hidden) {
          if (!hiddenSet.has(it.id)) return false;
        } else {
          if (hiddenSet.has(it.id)) return false;
        }

        if (smartFilters.fav && !favSet.has(it.id)) return false;
        if (smartFilters.dedup && it.dup && !smartFilters.fav && !smartFilters.hidden) return false;
        if (smartFilters.noBadFloor && it.bad_fl) return false;
        if (smartFilters.owner && !it.owner) return false;
        if (smartFilters.drop && !(it.previous_price && it.price && it.previous_price > it.price)) return false;
        if (smartFilters.recent) {
          const discMs = it.date_discovered ? new Date(it.date_discovered).getTime() : 0;
          if (!discMs || (nowMs - discMs) > 48 * 3600 * 1000) return false;
        }

        if (selectedPortal !== 'all' && it.portal.toLowerCase() !== selectedPortal) return false;
        if (neighborhood !== 'all' && !(it.neighborhood || '').toLowerCase().includes(neighborhood)) return false;
        if (maxPrice && it.price && it.price > maxPrice) return false;
        if (q) {
          const hay = ((it.title || '') + ' ' + (it.neighborhood || '') + ' ' + (it.floor || '') + ' ' + (it.desc_snippet || '')).toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      if (sort === 'price_asc') {
        filtered.sort((a, b) => (a.price || 9999999) - (b.price || 9999999));
      } else if (sort === 'price_desc') {
        filtered.sort((a, b) => (b.price || 0) - (a.price || 0));
      } else if (sort === 'sqm_asc') {
        const getSqm = x => (x.price && x.surface_sqm && x.surface_sqm > 0) ? (x.price / x.surface_sqm) : 9999999;
        filtered.sort((a, b) => getSqm(a) - getSqm(b));
      } else if (sort === 'surface_desc') {
        filtered.sort((a, b) => (b.surface_sqm || 0) - (a.surface_sqm || 0));
      } else if (sort === 'price_drop') {
        const getDrop = x => (x.previous_price && x.price && x.previous_price > x.price) ? (x.previous_price - x.price) : -1;
        filtered.sort((a, b) => getDrop(b) - getDrop(a));
      }

      resultsCount.textContent = filtered.length;
      renderListings(filtered, favSet, hiddenSet);
      renderPagination(filtered.length);
    }

    const smartFilters = {
      fav: false,
      recent: false,
      drop: false,
      owner: false,
      noBadFloor: false,
      dedup: true,
      hidden: false
    };

    function getFavSet() {
      try {
        return new Set(JSON.parse(localStorage.getItem('imob_fav_ids') || '[]'));
      } catch (e) {
        return new Set();
      }
    }

    function getHiddenSet() {
      try {
        return new Set(JSON.parse(localStorage.getItem('imob_hidden_ids') || '[]'));
      } catch (e) {
        return new Set();
      }
    }

    function updateSmartCounters(favSet, hiddenSet) {
      const fc = document.getElementById('favCount');
      const hc = document.getElementById('hiddenCount');
      if (fc) fc.textContent = favSet.size;
      if (hc) hc.textContent = hiddenSet.size;
    }

    function toggleSmartFilter(key) {
      smartFilters[key] = !smartFilters[key];
      if (key === 'hidden' && smartFilters.hidden) {
        smartFilters.fav = false;
      }
      const btnMap = {
        fav: 'chipFav',
        recent: 'chipRecent',
        drop: 'chipDrop',
        owner: 'chipOwner',
        noBadFloor: 'chipNoBadFloor',
        dedup: 'chipDedup',
        hidden: 'chipHidden'
      };
      Object.keys(btnMap).forEach(k => {
        const el = document.getElementById(btnMap[k]);
        if (el) el.classList.toggle('active', !!smartFilters[k]);
      });
      currentPage = 1;
      applyFilters();
    }

    function toggleFav(id, ev) {
      if (ev) ev.stopPropagation();
      const set = getFavSet();
      if (set.has(id)) {
        set.delete(id);
        showToast('Eliminat de la favorite.', 'info');
      } else {
        set.add(id);
        showToast('⭐ Salvat la favorite!', 'success');
      }
      localStorage.setItem('imob_fav_ids', JSON.stringify(Array.from(set)));
      applyFilters();
    }

    function toggleHide(id, ev) {
      if (ev) ev.stopPropagation();
      const set = getHiddenSet();
      if (set.has(id)) {
        set.delete(id);
        showToast('Anunț restaurat în listă.', 'info');
      } else {
        set.add(id);
        showToast('Anunț ascuns (îl poți vedea în filtrul Ascunse).', 'info');
      }
      localStorage.setItem('imob_hidden_ids', JSON.stringify(Array.from(set)));
      applyFilters();
    }

    function renderListings(items, favSet, hiddenSet) {
      const start = (currentPage - 1) * PAGE_SIZE;
      const paginated = items.slice(start, start + PAGE_SIZE);

      if (!paginated.length) {
        listingsGrid.innerHTML = `
          <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted); background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg);">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 12px; opacity: 0.6;"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            <h3 style="color: var(--text-primary); font-size: 15px; margin-bottom: 4px;">Niciun anunț conform filtrelor</h3>
            <p style="font-size: 13px;">Încercați să resetați filtrele sau căutați alt termen.</p>
          </div>
        `;
        return;
      }

      const fallbackImg = "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop";

      listingsGrid.innerHTML = paginated.map(item => {
        const priceFormatted = item.price 
          ? `${Math.round(item.price).toLocaleString("ro-RO")} ${item.currency}` 
          : "Preț la cerere";

        let priceDropHtml = "";
        if (item.previous_price && item.price && item.previous_price > item.price) {
          const diff = Math.round(item.previous_price - item.price).toLocaleString("ro-RO");
          const oldFmt = Math.round(item.previous_price).toLocaleString("ro-RO");
          priceDropHtml = `<span class="price-drop-pill" title="Preț anterior: ${oldFmt} ${item.currency}">↓ -${diff} €</span><span class="price-old">${oldFmt} €</span>`;
        }

        const sqmPrice = (item.price && item.surface_sqm && item.surface_sqm > 0)
          ? `${Math.round(item.price / item.surface_sqm).toLocaleString("ro-RO")} €/mp`
          : "";

        const portalClass = item.portal.toLowerCase();
        const imgUrl = item.thumbnail || fallbackImg;
        const yearBadge = item.year 
          ? `<span class="year-chip-badge">An ${item.year}</span>`
          : `<span class="year-chip-badge">&gt;1977</span>`;

        const surfBadge = item.surface_sqm 
          ? `<span class="attr-tag"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg> ${item.surface_sqm} mp</span>` 
          : "";

        const floorBadge = item.floor
          ? `<span class="attr-tag floor-tag">${escapeHtml(item.floor)}</span>`
          : "";

        const ownerBadge = item.owner
          ? `<span class="attr-tag owner-tag">Proprietar / 0%</span>`
          : "";

        let crossPortalHtml = "";
        if (item.alt && item.alt.length > 0) {
          const links = item.alt.map(a => {
            const pr = a.price ? ` (${Math.round(a.price).toLocaleString("ro-RO")} €)` : "";
            return `<a href="${a.url}" target="_blank" class="cross-portal-link">${a.portal.toUpperCase()}${pr}</a>`;
          }).join("");
          crossPortalHtml = `<div class="cross-portal-bar"><span>🔗 Și pe:</span>${links}</div>`;
        }

        const isFav = favSet.has(item.id);
        const isHidden = hiddenSet.has(item.id);

        return `
          <div class="listing-card">
            <div class="card-media">
              <img src="${imgUrl}" alt="${escapeHtml(item.title)}" class="card-img" loading="lazy" onerror="this.src='${fallbackImg}'">
              <span class="portal-badge ${portalClass}">${item.portal}</span>
              ${yearBadge}
              <div class="card-actions-overlay">
                <button class="btn-card-action ${isFav ? 'fav-active' : ''}" onclick="toggleFav('${item.id}', event)" title="${isFav ? 'Elimină de la favorite' : 'Salvează la favorite'}">
                  ${isFav ? '★' : '☆'}
                </button>
                <button class="btn-card-action ${isHidden ? 'hide-active' : ''}" onclick="toggleHide('${item.id}', event)" title="${isHidden ? 'Restaurează anunțul' : 'Ascunde anunțul'}">
                  ✕
                </button>
              </div>
            </div>
            <div class="card-content">
              <div class="card-price-row">
                <div class="price-main">${priceFormatted}${priceDropHtml}</div>
                ${sqmPrice ? `<div class="price-sqm">${sqmPrice}</div>` : ''}
              </div>
              <a href="${item.url}" target="_blank" class="card-title" title="${escapeHtml(item.title)}">
                ${escapeHtml(item.title)}
              </a>
              <div class="card-attributes">
                <span class="attr-tag">2 Camere</span>
                ${surfBadge}
                ${floorBadge}
                <span class="attr-tag">${item.neighborhood || "Sector 6"}</span>
                ${ownerBadge}
              </div>
              ${crossPortalHtml}
              <div class="card-footer">
                <span class="card-location">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
                  ${item.neighborhood || "Sector 6"}
                </span>
                <a href="${item.url}" target="_blank" class="btn-open-ad">
                  Vezi Anunț
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" x2="21" y1="14" y2="3"/></svg>
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

      let html = `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">Înapoi</button>`;
      for (let p = Math.max(1, currentPage - 2); p <= Math.min(totalPages, currentPage + 2); p++) {
        html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
      }
      html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">Înainte</button>`;
      pagination.innerHTML = html;
    }

    function goToPage(p) {
      currentPage = p;
      applyFilters();
      window.scrollTo({ top: 320, behavior: 'smooth' });
    }

    function escapeHtml(text) {
      if (!text) return "";
      return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    // Listeners
    filterSearch.addEventListener('input', () => { currentPage = 1; applyFilters(); });
    filterNeighborhood.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    filterMaxPrice.addEventListener('input', () => { 
      selectedMaxPrice = parseFloat(filterMaxPrice.value) || null;
      document.querySelectorAll('#pricePills .chip-btn').forEach(b => b.classList.remove('active'));
      currentPage = 1; 
      applyFilters(); 
    });
    filterSort.addEventListener('change', () => { currentPage = 1; applyFilters(); });

    btnResetFilters.addEventListener('click', () => {
      filterSearch.value = '';
      filterNeighborhood.value = 'all';
      filterMaxPrice.value = '';
      filterSort.value = 'newest';
      selectedPortal = 'all';
      selectedMaxPrice = null;
      smartFilters.fav = false;
      smartFilters.recent = false;
      smartFilters.drop = false;
      smartFilters.owner = false;
      smartFilters.noBadFloor = false;
      smartFilters.dedup = true;
      smartFilters.hidden = false;
      ['chipFav', 'chipRecent', 'chipDrop', 'chipOwner', 'chipNoBadFloor', 'chipHidden'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('active');
      });
      const dedupEl = document.getElementById('chipDedup');
      if (dedupEl) dedupEl.classList.add('active');
      document.querySelectorAll('#portalPills .chip-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-portal') === 'all'));
      document.querySelectorAll('#pricePills .chip-btn').forEach(b => b.classList.remove('active'));
      currentPage = 1;
      applyFilters();
    });

    // Init
    applyFilters();
  </script>
</body>
</html>
"""


def _extract_floor_key(floor_str: str) -> str:
    if not floor_str:
        return ""
    fl = floor_str.lower()
    if "parter" in fl:
        return "0"
    m = re.search(r"(\d{1,2})", fl)
    return m.group(1) if m else ""


def _build_compact_listings_with_dedup(listings) -> list:
    items = []
    for it in listings:
        raw_desc = it.description or ""
        clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()[:220]

        bad_fl = 1 if is_ground_or_top_floor(it.floor, it.title, raw_desc) else 0
        owner = 1 if is_direct_owner_or_zero_commission(it.title, raw_desc) else 0

        items.append({
            "id": it.id,
            "portal": it.portal,
            "title": it.title,
            "price": it.price,
            "initial_price": it.initial_price,
            "previous_price": it.previous_price,
            "currency": it.currency,
            "surface_sqm": it.surface_sqm,
            "year": it.year,
            "floor": it.floor,
            "neighborhood": it.neighborhood,
            "url": it.url,
            "thumbnail": it.thumbnail,
            "date_discovered": it.date_discovered.isoformat() if it.date_discovered else None,
            "desc_snippet": clean_desc,
            "bad_fl": bad_fl,
            "owner": owner,
            "dup": 0,
            "alt": [],
        })

    # Group cross-portal duplicates:
    # 1) Exact normalized title (>= 22 chars) + price within 3%
    # 2) Same specific neighborhood + surface within 0.5 sqm + same floor number + price within 2%
    groups = {}
    for idx, item in enumerate(items):
        norm_title = re.sub(r"[^a-z0-9]+", "", (item["title"] or "").lower())
        pr = item["price"] or 0
        nb = (item["neighborhood"] or "").lower()
        surf = round(item["surface_sqm"] or 0)
        fl_key = _extract_floor_key(item["floor"] or "")

        key = None
        if len(norm_title) >= 24 and pr > 0:
            key = ("title", norm_title[:42], int(pr // 2000))
        elif nb and nb != "sector 6" and surf >= 32 and fl_key and pr > 0:
            key = ("struct", nb, surf, fl_key, int(pr // 1500))

        if key:
            groups.setdefault(key, []).append(idx)

    for indices in groups.values():
        if len(indices) <= 1:
            continue
        # Sort group so lowest price (and then newest/first) is primary
        sorted_idx = sorted(indices, key=lambda i: (items[i]["price"] or 9999999, i))
        primary_i = sorted_idx[0]
        seen_portals = {items[primary_i]["portal"]}
        alt_links = []

        for sec_i in sorted_idx[1:]:
            items[sec_i]["dup"] = 1
            p_name = items[sec_i]["portal"]
            if p_name not in seen_portals and len(alt_links) < 4:
                seen_portals.add(p_name)
                alt_links.append({
                    "portal": p_name,
                    "url": items[sec_i]["url"],
                    "price": items[sec_i]["price"],
                })

        if alt_links:
            items[primary_i]["alt"] = alt_links

    return items


def generate_static_dashboard(output_path: Path = None) -> Path:
    if output_path is None:
        docs_dir = BASE_DIR / "docs"
        docs_dir.mkdir(exist_ok=True)
        output_path = docs_dir / "index.html"

    total, listings = database.get_all_listings(limit=2500)
    stats = database.get_stats()
    
    listings_data = _build_compact_listings_with_dedup(listings)
    now_str = datetime.now().strftime("%d.%m.%Y, %H:%M")

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
