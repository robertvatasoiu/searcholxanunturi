// State management
let currentPage = 1;
const PAGE_SIZE = 24;
let pollInterval = null;

// DOM Elements
const statTotal = document.getElementById("statTotal");
const statNew = document.getElementById("statNew");
const statSchedule = document.getElementById("statSchedule");
const statNextRun = document.getElementById("statNextRun");
const cntOlx = document.getElementById("cntOlx");
const cntStoria = document.getElementById("cntStoria");
const cntImobiliare = document.getElementById("cntImobiliare");
const cntPubli24 = document.getElementById("cntPubli24");
const cntAnuntul = document.getElementById("cntAnuntul");
const resultsCount = document.getElementById("resultsCount");
const listingsGrid = document.getElementById("listingsGrid");
const pagination = document.getElementById("pagination");

// Filter elements
const filterSearch = document.getElementById("filterSearch");
const filterPortal = document.getElementById("filterPortal");
const filterNeighborhood = document.getElementById("filterNeighborhood");
const filterStatus = document.getElementById("filterStatus");
const filterMaxPrice = document.getElementById("filterMaxPrice");
const btnResetFilters = document.getElementById("btnResetFilters");

// Buttons
const btnScrapeNow = document.getElementById("btnScrapeNow");
const btnSendDigestNow = document.getElementById("btnSendDigestNow");
const btnOpenSettings = document.getElementById("btnOpenSettings");
const btnExport = document.getElementById("btnExport");
const btnMarkAllAlerted = document.getElementById("btnMarkAllAlerted");

// Modals
const scrapeModal = document.getElementById("scrapeModal");
const settingsModal = document.getElementById("settingsModal");
const scrapeProgressBar = document.getElementById("scrapeProgressBar");
const scrapeStatusText = document.getElementById("scrapeStatusText");
const scrapeLogs = document.getElementById("scrapeLogs");

// Init
document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadListings();
  setupEventListeners();
});

function setupEventListeners() {
  // Filters
  let debounceTimeout;
  filterSearch.addEventListener("input", () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      currentPage = 1;
      loadListings();
    }, 300);
  });

  filterPortal.addEventListener("change", () => { currentPage = 1; loadListings(); });
  filterNeighborhood.addEventListener("change", () => { currentPage = 1; loadListings(); });
  filterStatus.addEventListener("change", () => { currentPage = 1; loadListings(); });
  filterMaxPrice.addEventListener("input", () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      currentPage = 1;
      loadListings();
    }, 400);
  });

  btnResetFilters.addEventListener("click", () => {
    filterSearch.value = "";
    filterPortal.value = "all";
    filterNeighborhood.value = "all";
    filterStatus.value = "all";
    filterMaxPrice.value = "";
    currentPage = 1;
    loadListings();
  });

  // Action buttons
  btnScrapeNow.addEventListener("click", startScraping);
  btnSendDigestNow.addEventListener("click", sendDigestNow);
  btnOpenSettings.addEventListener("click", openSettingsModal);
  btnExport.addEventListener("click", () => {
    window.open("/api/export?format=csv", "_blank");
  });
  btnMarkAllAlerted.addEventListener("click", markAllAlerted);

  // Settings & Notification Handlers
  document.getElementById("btnSaveSettings").addEventListener("click", saveSettings);
  document.getElementById("btnTestResend").addEventListener("click", () => testEmailConnection("resend"));
  document.getElementById("btnTestTelegram").addEventListener("click", testTelegramConnection);
  document.getElementById("btnTestSmtp").addEventListener("click", () => testEmailConnection("smtp"));

  // Radio button channel toggles
  document.querySelectorAll("input[name='notifChannel']").forEach(radio => {
    radio.addEventListener("change", (e) => {
      toggleNotificationSections(e.target.value);
    });
  });
}

function toggleNotificationSections(channel) {
  document.getElementById("sectionResend").style.display = channel === "resend" ? "block" : "none";
  document.getElementById("sectionTelegram").style.display = channel === "telegram" ? "block" : "none";
  document.getElementById("sectionSmtp").style.display = channel === "smtp" ? "block" : "none";
}

// Toast helper
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal helper
function openModal(modalId) {
  document.getElementById(modalId).classList.add("active");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("active");
}

// Load statistics
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    
    statTotal.textContent = data.total_listings || 0;
    statNew.textContent = data.new_unalerted || 0;
    
    if (data.scheduler) {
      statSchedule.textContent = data.scheduler.scheduled_time || "08:00";
      if (data.scheduler.next_run) {
        const nextDate = new Date(data.scheduler.next_run);
        statNextRun.textContent = `Următoarea rulare: ${nextDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} (${nextDate.toLocaleDateString()})`;
      }
    }

    const byPortal = data.by_portal || {};
    cntOlx.textContent = byPortal.olx || 0;
    cntStoria.textContent = byPortal.storia || 0;
    cntImobiliare.textContent = byPortal.imobiliare || 0;
    cntPubli24.textContent = byPortal.publi24 || 0;
    cntAnuntul.textContent = byPortal.anuntul || 0;

  } catch (err) {
    console.error("Error loading stats:", err);
  }
}

// Load listings
async function loadListings() {
  listingsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">Încărcare anunțuri...</div>`;
  
  const params = new URLSearchParams({
    page: currentPage,
    limit: PAGE_SIZE,
    portal: filterPortal.value,
    neighborhood: filterNeighborhood.value,
    is_alerted: filterStatus.value,
  });

  if (filterSearch.value.trim()) {
    params.append("search", filterSearch.value.trim());
  }
  if (filterMaxPrice.value) {
    params.append("max_price", filterMaxPrice.value);
  }

  try {
    const res = await fetch(`/api/listings?${params.toString()}`);
    const data = await res.json();

    resultsCount.textContent = data.total;
    renderListings(data.items);
    renderPagination(data.page, data.pages);
  } catch (err) {
    listingsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--accent-rose);">Eroare la încărcarea anunțurilor.</div>`;
    console.error(err);
  }
}

// Render cards
function renderListings(items) {
  if (!items || items.length === 0) {
    listingsGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-lg); border: 1px dashed var(--border-color);">
        <div style="font-size: 40px; margin-bottom: 12px;">🔍</div>
        <h3 style="color: #fff; margin-bottom: 6px;">Niciun anunț găsit</h3>
        <p style="font-size: 14px;">Apasă pe butonul "Caută Acum" pentru a scana automat cele 5 portaluri imobiliare.</p>
      </div>
    `;
    return;
  }

  listingsGrid.innerHTML = items.map(item => {
    const priceFormatted = item.price 
      ? `${Math.round(item.price).toLocaleString("ro-RO")} ${item.currency}` 
      : "Preț la cerere";

    const portalClass = `chip-${item.portal}`;
    const newBadge = !item.is_alerted ? `<span class="new-badge">✨ NOU</span>` : "";

    const fallbackImg = "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop";
    const imgUrl = item.thumbnail || fallbackImg;

    const yearBadge = item.year 
      ? `<span class="tag-item highlight-year">🏗️ An ${item.year}</span>`
      : `<span class="tag-item highlight-year">🏗️ &gt;1977</span>`;

    const surfBadge = item.surface_sqm 
      ? `<span class="tag-item">📐 ${item.surface_sqm} mp</span>` 
      : "";

    const dateStr = item.date_discovered 
      ? new Date(item.date_discovered).toLocaleDateString("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
      : "";

    return `
      <div class="listing-card">
        <div class="listing-img-box">
          <img src="${imgUrl}" alt="${escapeHtml(item.title)}" class="listing-img" onerror="this.src='${fallbackImg}'">
          ${newBadge}
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
            <span class="listing-date">🕒 ${dateStr}</span>
            <a href="${item.url}" target="_blank" class="btn btn-secondary btn-sm" style="font-weight: 700;">
              Vezi Anunț &rarr;
            </a>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Pagination
function renderPagination(current, totalPages) {
  if (totalPages <= 1) {
    pagination.innerHTML = "";
    return;
  }

  let html = `<button class="page-btn" ${current === 1 ? 'disabled' : ''} onclick="goToPage(${current - 1})">&laquo; Înapoi</button>`;
  
  for (let p = Math.max(1, current - 2); p <= Math.min(totalPages, current + 2); p++) {
    html += `<button class="page-btn ${p === current ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
  }

  html += `<button class="page-btn" ${current === totalPages ? 'disabled' : ''} onclick="goToPage(${current + 1})">Înainte &raquo;</button>`;
  pagination.innerHTML = html;
}

function goToPage(page) {
  currentPage = page;
  loadListings();
  window.scrollTo({ top: 400, behavior: "smooth" });
}

// Start scraping
async function startScraping() {
  try {
    openModal("scrapeModal");
    scrapeProgressBar.style.width = "5%";
    scrapeStatusText.textContent = "Inițializare căutare...";
    scrapeLogs.innerHTML = "";

    const res = await fetch("/api/scrape/start", { method: "POST" });
    const data = await res.json();
    if (data.status !== "ok") {
      showToast(data.message || "Eroare la lansarea căutării", "error");
      return;
    }

    // Start polling
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollScrapeStatus, 1000);
  } catch (err) {
    showToast("Eroare de conexiune la server", "error");
  }
}

async function pollScrapeStatus() {
  try {
    const res = await fetch("/api/scrape/status");
    const state = await res.json();

    scrapeProgressBar.style.width = `${state.progress}%`;
    scrapeStatusText.textContent = state.current_message;

    if (state.logs && state.logs.length > 0) {
      scrapeLogs.innerHTML = state.logs.map(l => `<div>${escapeHtml(l)}</div>`).join("");
      scrapeLogs.scrollTop = scrapeLogs.scrollHeight;
    }

    if (!state.is_running) {
      clearInterval(pollInterval);
      pollInterval = null;
      loadStats();
      loadListings();
      showToast("Scanarea s-a încheiat cu succes!", "success");
    }
  } catch (err) {
    console.error("Error polling scrape status:", err);
  }
}

// Send digest
async function sendDigestNow() {
  if (!confirm("Vrei să trimiți acum raportul cu toate anunțurile noi către canalele configurate (Email / Telegram)?")) {
    return;
  }
  try {
    showToast("Trimitere raport în curs...", "info");
    const res = await fetch("/api/email/send-digest", { method: "POST" });
    const data = await res.json();
    if (data.status === "ok") {
      showToast(data.message, "success");
      loadStats();
      loadListings();
    } else {
      showToast(data.message || "Eroare la trimitere", "error");
    }
  } catch (err) {
    showToast("Eroare de comunicare cu serverul", "error");
  }
}

// Mark all alerted
async function markAllAlerted() {
  if (!confirm("Sigur vrei să marchezi toate anunțurile existente ca fiind deja trimise?")) {
    return;
  }
  try {
    const res = await fetch("/api/listings/mark-all-alerted", { method: "POST" });
    const data = await res.json();
    showToast(data.message, "success");
    loadStats();
    loadListings();
  } catch (err) {
    showToast("Eroare la actualizarea statusului", "error");
  }
}

// Settings modal
async function openSettingsModal() {
  try {
    const res = await fetch("/api/config");
    const cfg = await res.json();

    // Provider channel selection
    const isTg = cfg.telegram?.enabled;
    const isSmtp = cfg.smtp?.provider === "smtp";
    let selectedChannel = "resend";
    if (isTg && !cfg.smtp?.enabled) {
      selectedChannel = "telegram";
    } else if (isSmtp) {
      selectedChannel = "smtp";
    }

    if (document.getElementById(`opt${capitalize(selectedChannel)}`)) {
      document.getElementById(`opt${capitalize(selectedChannel)}`).checked = true;
    }
    toggleNotificationSections(selectedChannel);

    // Resend fields
    document.getElementById("resendApiKey").value = cfg.smtp?.resend_api_key || "";
    document.getElementById("resendRecipients").value = (cfg.smtp?.recipient_emails || []).join(", ");

    // Telegram fields
    document.getElementById("tgBotToken").value = cfg.telegram?.bot_token || "";
    document.getElementById("tgChatId").value = cfg.telegram?.chat_id || "";

    // SMTP fields
    document.getElementById("smtpHost").value = cfg.smtp?.host || "smtp.gmail.com";
    document.getElementById("smtpPort").value = cfg.smtp?.port || 587;
    document.getElementById("smtpUser").value = cfg.smtp?.username || "";
    document.getElementById("smtpPassword").value = cfg.smtp?.password || "";
    document.getElementById("smtpRecipients").value = (cfg.smtp?.recipient_emails || []).join(", ");

    // Schedule & Search
    document.getElementById("scheduleHour").value = cfg.schedule?.hour ?? 8;
    document.getElementById("scheduleMinute").value = cfg.schedule?.minute ?? 0;
    document.getElementById("searchMinYear").value = cfg.search?.min_year || 1978;

    openModal("settingsModal");
  } catch (err) {
    showToast("Eroare la încărcarea setărilor", "error");
  }
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

async function saveSettings() {
  const selectedChannel = document.querySelector("input[name='notifChannel']:checked")?.value || "resend";
  
  let recipients = [];
  if (selectedChannel === "resend") {
    recipients = document.getElementById("resendRecipients").value.split(",").map(e => e.trim()).filter(Boolean);
  } else {
    recipients = document.getElementById("smtpRecipients").value.split(",").map(e => e.trim()).filter(Boolean);
  }

  const payload = {
    smtp: {
      enabled: selectedChannel === "resend" || selectedChannel === "smtp",
      provider: selectedChannel === "resend" ? "resend" : "smtp",
      host: document.getElementById("smtpHost").value,
      port: parseInt(document.getElementById("smtpPort").value) || 587,
      use_tls: true,
      use_ssl: false,
      username: document.getElementById("smtpUser").value,
      password: document.getElementById("smtpPassword").value,
      sender_email: "onboarding@resend.dev",
      sender_name: "Imobiliare Sector 6 Alerte",
      recipient_emails: recipients,
      resend_api_key: document.getElementById("resendApiKey").value
    },
    telegram: {
      enabled: selectedChannel === "telegram",
      bot_token: document.getElementById("tgBotToken").value.trim(),
      chat_id: document.getElementById("tgChatId").value.trim()
    },
    schedule: {
      enabled: true,
      hour: parseInt(document.getElementById("scheduleHour").value) || 8,
      minute: parseInt(document.getElementById("scheduleMinute").value) || 0,
      timezone: "Europe/Bucharest"
    },
    search: {
      rooms: 2,
      min_year: parseInt(document.getElementById("searchMinYear").value) || 1978,
      sector: "Sector 6",
      city: "Bucuresti",
      enabled_portals: ["olx", "storia", "imobiliare", "publi24", "anuntul"]
    }
  };

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "ok") {
      showToast("Setările au fost salvate cu succes!", "success");
      closeModal("settingsModal");
      loadStats();
    } else {
      showToast(data.message || "Eroare la salvare", "error");
    }
  } catch (err) {
    showToast("Eroare de comunicare cu serverul", "error");
  }
}

async function testEmailConnection(providerType) {
  let recipient = "";
  if (providerType === "resend") {
    recipient = document.getElementById("resendRecipients").value.split(",")[0]?.trim();
  } else {
    recipient = document.getElementById("smtpRecipients").value.split(",")[0]?.trim() || document.getElementById("smtpUser").value;
  }

  if (!recipient) {
    showToast("Introduceți adresa de email unde doriți să primiți testul.", "error");
    return;
  }

  showToast(`Trimitere email de test către ${recipient}...`, "info");
  try {
    await saveSettings();
    const res = await fetch("/api/email/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient: recipient })
    });
    const data = await res.json();
    if (data.status === "ok") {
      showToast(data.message, "success");
    } else {
      showToast(data.message || "Eroare la testul de email", "error");
    }
  } catch (err) {
    showToast("Eroare de conexiune la trimiterea testului", "error");
  }
}

async function testTelegramConnection() {
  showToast("Trimitere mesaj de test pe Telegram...", "info");
  try {
    await saveSettings();
    const res = await fetch("/api/telegram/test", { method: "POST" });
    const data = await res.json();
    if (data.status === "ok") {
      showToast(data.message, "success");
    } else {
      showToast(data.message || "Eroare la testul Telegram", "error");
    }
  } catch (err) {
    showToast("Eroare la conexiunea cu Telegram", "error");
  }
}
