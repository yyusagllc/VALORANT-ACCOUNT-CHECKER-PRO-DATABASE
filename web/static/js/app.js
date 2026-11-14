/**
 * VALORANT ACCOUNT CHECKER & DATABASE - FRONTEND JS
 * dash.valorant-api.com üzerindeki tüm 30 uç noktayı ve eksiksiz hesap verilerini sunar.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Global Durum
    let currentAccount = null;
    let currentSnapshot = null;
    let selectedHistoryPuuid = null;
    let activeEndpointId = "agents";
    let activeEndpointRawData = null;

    // Element Seçicileri
    const navTabs = document.querySelectorAll(".nav-tab");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const checkForm = document.getElementById("check-form");
    const redirectUrlInput = document.getElementById("redirect-url");
    const regionSelect = document.getElementById("region-select");
    const checkNotesInput = document.getElementById("check-notes");
    const btnPaste = document.getElementById("btn-paste-clipboard");
    const checkProgress = document.getElementById("check-progress");
    const btnSubmitCheck = document.getElementById("btn-submit-check");
    const dbSummaryText = document.getElementById("db-summary-text");
    const quickAccountsList = document.getElementById("quick-accounts-list");
    const quickAccountsCount = document.getElementById("quick-accounts-count");
    const detailsContainer = document.getElementById("details-container");
    const historyAccountsList = document.getElementById("history-accounts-list");
    const accountFilterInput = document.getElementById("account-filter-input");
    const logsTbody = document.getElementById("logs-tbody");
    const historyActions = document.getElementById("history-actions");
    const historyAccountTitle = document.getElementById("history-account-title");
    const btnExportLatestHtml = document.getElementById("btn-export-latest-html");
    const btnDeleteAccount = document.getElementById("btn-delete-account");
    const endpointsMenu = document.getElementById("endpoints-menu");
    const endpointActiveTitle = document.getElementById("endpoint-active-title");
    const endpointActiveDesc = document.getElementById("endpoint-active-desc");
    const endpointActiveUrl = document.getElementById("endpoint-active-url");
    const endpointItemsGrid = document.getElementById("endpoint-items-grid");
    const endpointSearchInput = document.getElementById("endpoint-search-input");
    const btnRefreshEndpoint = document.getElementById("btn-refresh-endpoint");
    const btnViewRawJson = document.getElementById("btn-view-raw-json");
    const jsonModal = document.getElementById("json-modal");
    const jsonModalCode = document.getElementById("json-modal-code");
    const btnCloseJsonModal = document.getElementById("btn-close-json-modal");
    const toastContainer = document.getElementById("toast-container");

    // ========================================================
    // YARDIMCI BİLDİRİM (TOAST)
    // ========================================================
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = `<i class="fa-solid fa-${type === 'success' ? 'circle-check' : (type === 'error' ? 'circle-exclamation' : 'circle-info')}"></i> ${message}`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.remove();
        }, 4500);
    }

    // ========================================================
    // TAB YÖNETİMİ
    // ========================================================
    function switchTab(tabId) {
        navTabs.forEach(tab => {
            tab.classList.toggle("active", tab.dataset.tab === tabId);
        });
        tabPanes.forEach(pane => {
            pane.classList.toggle("active", pane.id === tabId);
        });

        if (tabId === "tab-history") {
            loadAccountsList();
        } else if (tabId === "tab-explorer") {
            loadEndpointsList();
        }
    }

    navTabs.forEach(tab => {
        tab.addEventListener("click", () => switchTab(tab.dataset.tab));
    });

    // ========================================================
    // PANODAN YAPIŞTIR
    // ========================================================
    btnPaste.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                redirectUrlInput.value = text.trim();
                showToast("Bağlantı panodan yapıştırıldı!", "success");
            }
        } catch (err) {
            showToast("Panoya erişilemedi. Lütfen manuel yapıştırın.", "error");
        }
    });

    // ========================================================
    // VERİTABANI ÖZET BİLGİSİ
    // ========================================================
    async function updateDbStats() {
        try {
            const res = await fetch("/api/stats");
            const data = await res.json();
            dbSummaryText.textContent = `${data.total_accounts} Hesap | ${data.total_checks} Log`;
        } catch (e) {
            dbSummaryText.textContent = "Veritabanı Aktif";
        }
    }

    // ========================================================
    // HESAP KONTROL İŞLEMİ (FORM SUBMIT)
    // ========================================================
    checkForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const redirectUrl = redirectUrlInput.value.trim();
        const region = regionSelect.value;
        const notes = checkNotesInput.value.trim();

        if (!redirectUrl) {
            showToast("Lütfen yönlendirme URL'sini veya token'ı girin.", "error");
            return;
        }

        btnSubmitCheck.disabled = true;
        checkProgress.classList.remove("hidden");

        try {
            const response = await fetch("/api/check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    redirect_url: redirectUrl,
                    region: region,
                    notes: notes
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || "Hesap kontrolü sırasında bir hata oluştu.");
            }

            showToast(`${result.account.riot_id} hesabı başarıyla kontrol edildi ve loglandı!`, "success");
            currentSnapshot = result;
            currentAccount = result.account;

            redirectUrlInput.value = "";
            checkNotesInput.value = "";

            renderAccountDetails(result);
            switchTab("tab-details");

            loadQuickAccounts();
            updateDbStats();

        } catch (error) {
            showToast(error.message, "error");
        } finally {
            btnSubmitCheck.disabled = false;
            checkProgress.classList.add("hidden");
        }
    });

    // ========================================================
    // HESAP DETAYI GÖRÜNTÜLEME (SON LOG & EKSİKSİZ TÜM VERİLER)
    // ========================================================
    function renderAccountDetails(snapshot) {
        if (!snapshot) return;

        const acc = snapshot.account || {};
        const lvl = snapshot.level || {};
        const rank = snapshot.rank || {};
        const wallet = snapshot.wallet || {};
        const firstWin = snapshot.first_win || {};
        const penalties = snapshot.penalties || {};
        const loadout = snapshot.loadout || {};
        const card = (loadout.identity && loadout.identity.card) || {};
        const title = (loadout.identity && loadout.identity.title) || {};
        const store = snapshot.store || {};
        const inventory = snapshot.inventory || {};
        const ownedSkins = inventory.skins || snapshot.owned_skins || [];
        const buddies = inventory.buddies || [];
        const sprays = inventory.sprays || [];
        const cards = inventory.cards || [];
        const titles = inventory.titles || [];
        const agents = inventory.agents || [];
        const agentsRoster = inventory.agents_roster || agents || [];
        const missions = snapshot.missions || {};
        const battlepass = snapshot.battlepass || (missions && missions.battlepass);
        const agentContracts = (snapshot.contracts && snapshot.contracts.agent_contracts) || (missions && missions.agent_contracts) || [];
        const matches = snapshot.matches || [];
        const checkTime = snapshot.check_time_local || "";
        const logId = snapshot.log_id || "";

        const cardBanner = card.wideArt || card.largeArt || "";
        const cardTitle = title.titleText || title.displayName || "Ajan";
        const rankIcon = rank.rank_icon || "/static/img/unranked.png";

        let rankSubtext = `Kademe Puanı (RR): <strong>${rank.ranked_rating || 0}/100</strong>`;
        if (rank.previous_act_rank && rank.rank_tier === 0) {
            rankSubtext += ` &bull; Geçen Kısım: <strong>${rank.previous_act_rank}</strong>`;
        }
        rankSubtext += ` &bull; Zirve: <strong>${rank.peak_rank || 'Derecesiz'}</strong> (${rank.peak_season_name || ''})`;

        let html = `
        <div class="account-hero-banner">
            <div class="hero-backdrop" style="background-image: url('${cardBanner}');"></div>
            <div class="hero-main-row">
                <div class="hero-identity">
                    <div class="rank-badge-box">
                        <img src="${rankIcon}" alt="${rank.rank_name || 'Derecesiz'}">
                    </div>
                    <div class="hero-names">
                        <h1>${acc.riot_id || 'Oyuncu'} <span class="region-tag">${(acc.region || 'EU').toUpperCase()}</span></h1>
                        <div class="hero-title-text"><i class="fa-solid fa-award"></i> ${cardTitle}</div>
                        <small style="color: var(--text-muted); font-size: 11px;">PUUID: ${acc.puuid || ''}</small>
                    </div>
                </div>
                <div class="hero-actions-group">
                    <button class="btn btn-primary" onclick="exportHtml('${acc.puuid}', ${logId})">
                        <i class="fa-solid fa-file-arrow-down"></i> HTML Raporu İndir &amp; Aç
                    </button>
                    <button class="btn btn-outline" onclick="viewJsonSnapshot()">
                        <i class="fa-solid fa-code"></i> Tam Snapshot JSON
                    </button>
                </div>
            </div>
        </div>

        <!-- 6 Temel İstatistik Kartı -->
        <div class="details-stats-grid">
            <div class="detail-stat-card">
                <small>Hesap Seviyesi</small>
                <strong class="main-val">${lvl.level || 1}</strong>
                <div class="progress-bar-wrap">
                    <div class="progress-bar-fill" style="width: ${lvl.progress_percent || 0}%;"></div>
                </div>
                <div class="stat-subtext">${lvl.progress_text || ''} &bull; ${lvl.remaining_xp || 0} AP kaldı</div>
            </div>

            <div class="detail-stat-card">
                <small>Dereceli Kademe</small>
                <strong class="main-val" style="color: ${rank.rank_color || '#fff'};">${rank.rank_name || 'Derecesiz'}</strong>
                <div class="stat-subtext">${rankSubtext}</div>
            </div>

            <div class="detail-stat-card">
                <small>Cüzdan / Bakiyeler</small>
                <div class="wallet-pills">
                    <div class="wallet-pill vp">VP: ${(wallet.VP || 0).toLocaleString()}</div>
                    <div class="wallet-pill rp">RP: ${(wallet.RP || 0).toLocaleString()}</div>
                    <div class="wallet-pill kc">KC: ${(wallet.KC || 0).toLocaleString()}</div>
                </div>
                <div class="stat-subtext">Toplam Hesap AP: ${(lvl.total_ap || 0).toLocaleString()}</div>
            </div>

            <div class="detail-stat-card">
                <small>Günlük İlk Galibiyet</small>
                <strong class="main-val ${firstWin.badge_class || 'unknown'}">${firstWin.status || 'Bilinmiyor'}</strong>
                <div class="stat-subtext">${firstWin.detail || ''}</div>
            </div>

            <div class="detail-stat-card">
                <small>Hesap Ceza Durumu</small>
                <strong class="main-val ${penalties.status_class || 'good'}">${penalties.status || 'Temiz'}</strong>
                <div class="stat-subtext">${penalties.detail || ''}</div>
            </div>

            <div class="detail-stat-card">
                <small>Toplam Özel Koleksiyon</small>
                <strong class="main-val">${ownedSkins.length} Skin</strong>
                <div class="stat-subtext">${buddies.length} Uğurluk &bull; ${sprays.length} Sprey &bull; ${cards.length} Kart</div>
            </div>
        </div>

        <!-- Alt Bölümler Sekmesi (Eksiksiz Tüm Bileşenler) -->
        <div class="subtabs-bar">
            <button class="subtab-btn active" data-subtab="subtab-shop"><i class="fa-solid fa-cart-shopping"></i> Günlük Mağaza (${(store.daily_offers || []).length})</button>
            <button class="subtab-btn" data-subtab="subtab-loadout"><i class="fa-solid fa-vest"></i> Kuşanılmış Envanter (${(loadout.guns || []).length})</button>
            <button class="subtab-btn" data-subtab="subtab-skins"><i class="fa-solid fa-gun"></i> Silah Skinleri (${ownedSkins.length})</button>
            <button class="subtab-btn" data-subtab="subtab-buddies"><i class="fa-solid fa-ring"></i> Uğurluklar (${buddies.length})</button>
            <button class="subtab-btn" data-subtab="subtab-sprays"><i class="fa-solid fa-spray-can"></i> Spreyler (${sprays.length})</button>
            <button class="subtab-btn" data-subtab="subtab-cards"><i class="fa-solid fa-id-card"></i> Kartlar (${cards.length})</button>
            <button class="subtab-btn" data-subtab="subtab-titles"><i class="fa-solid fa-tag"></i> Unvanlar (${titles.length})</button>
            <button class="subtab-btn" data-subtab="subtab-agents"><i class="fa-solid fa-user-shield"></i> Ajanlar (${(agentsRoster.filter(a => a.is_unlocked)).length || agents.length})</button>
            <button class="subtab-btn" data-subtab="subtab-contracts"><i class="fa-solid fa-scroll"></i> Kontratlar &amp; Savaş Bileti</button>
            <button class="subtab-btn" data-subtab="subtab-missions"><i class="fa-solid fa-list-check"></i> Görevler</button>
            <button class="subtab-btn" data-subtab="subtab-matches"><i class="fa-solid fa-trophy"></i> Son Maçlar (${matches.length})</button>
            <button class="subtab-btn" data-subtab="subtab-penalties"><i class="fa-solid fa-triangle-exclamation"></i> Cezalar (${(penalties.records || []).length})</button>
        </div>

        <!-- 1. GÜNLÜK MAĞAZA -->
        <div id="subtab-shop" class="subtab-content active">
            <h3 style="margin-bottom: 14px; font-size: 16px;"><i class="fa-regular fa-clock"></i> Kalan Süre: ${store.remaining_duration_text || 'Bilinmiyor'}</h3>
            <div class="shop-cards-grid">
                ${(store.daily_offers || []).map(item => `
                    <div class="shop-item-card" style="border-top: 3px solid ${item.rarity_color || '#ff4655'};">
                        <div class="shop-item-thumb">
                            <img src="${item.icon || ''}" alt="${item.skin_name}" loading="lazy">
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <span style="font-size: 11px; font-weight: 700; color: ${item.rarity_color || '#fff'};">${item.rarity || 'Standart'}</span>
                            <strong style="color: var(--accent-red); font-size:13px;"><i class="fa-solid fa-coins"></i> ${(item.price || 1775).toLocaleString()} VP</strong>
                        </div>
                        <strong class="shop-item-name">${item.skin_name}</strong>
                        <small class="shop-item-weapon">${item.weapon_name}</small>
                    </div>
                `).join('')}
            </div>

            ${store.featured_bundle ? `
                <h3 style="margin: 28px 0 14px; font-size: 18px; color: var(--accent-yellow);"><i class="fa-solid fa-box-open"></i> Öne Çıkan Paket: ${store.featured_bundle.name}</h3>
                <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:12px; padding:20px; margin-bottom:20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                        <div>
                            <strong style="font-size:20px; color:#fff;">${store.featured_bundle.name}</strong>
                            <div style="font-size:13px; color:var(--text-muted); margin-top:4px;">Kalan Süre: <strong>${formatDuration(store.featured_bundle.remaining_seconds)}</strong></div>
                        </div>
                        <div>
                            <strong style="font-size:22px; color:var(--accent-red);"><i class="fa-solid fa-coins"></i> ${(store.featured_bundle.total_discounted_cost || 0).toLocaleString()} VP</strong>
                        </div>
                    </div>
                </div>
            ` : ''}

            ${store.night_market && store.night_market.is_active ? `
                <h3 style="margin: 28px 0 14px; font-size: 18px; color: var(--accent-purple);"><i class="fa-solid fa-moon"></i> Gece Pazarı Teklifleri</h3>
                <div class="shop-cards-grid">
                    ${store.night_market.offers.map(nm => `
                        <div class="shop-item-card" style="border: 1px solid var(--accent-purple);">
                            <div class="shop-item-thumb"><img src="${nm.icon}" alt="${nm.skin_name}"></div>
                            <strong class="shop-item-name">${nm.skin_name}</strong>
                            <small class="shop-item-weapon">${nm.weapon_name}</small>
                            <div style="font-size: 12px; margin-top: 8px; color: var(--accent-purple); font-weight:700;">
                                İndirim: %${nm.discount_percent} &bull; ${nm.discounted_cost.toLocaleString()} VP <span style="text-decoration:line-through; color:var(--text-muted); font-size:11px;">(${nm.original_cost.toLocaleString()} VP)</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}

            ${store.accessory_store && store.accessory_store.is_active ? `
                <h3 style="margin: 28px 0 14px; font-size: 18px; color: var(--accent-yellow);"><i class="fa-solid fa-gem"></i> Aksesuar Mağazası (Kingdom Kredisi)</h3>
                <div class="shop-cards-grid">
                    ${store.accessory_store.offers.map(acc => `
                        <div class="shop-item-card" style="border: 1px solid var(--accent-yellow);">
                            <div class="shop-item-thumb"><img src="${acc.icon}" alt="${acc.name}" loading="lazy"></div>
                            <strong class="shop-item-name">${acc.name}</strong>
                            <small class="shop-item-weapon">${acc.type || 'Aksesuar'}</small>
                            <div style="font-size: 13px; margin-top: 8px; color: var(--accent-yellow); font-weight:700;">
                                <i class="fa-solid fa-coins"></i> ${(acc.cost_kc || 0).toLocaleString()} KC
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>

        <!-- 2. KUŞANILMIŞ ENVANTER (LOADOUT + SPREYLER) -->
        <div id="subtab-loadout" class="subtab-content">
            <h3 style="margin-bottom: 14px; font-size: 16px;"><i class="fa-solid fa-crosshairs"></i> Kuşanılmış Silahlar</h3>
            <div class="shop-cards-grid">
                ${(loadout.guns || []).map(gun => `
                    <div class="shop-item-card">
                        <div style="display:flex; justify-content:space-between; font-size:11px; font-weight:700; text-transform:uppercase; margin-bottom:6px;">
                            <span>${gun.weapon_name}</span>
                            <span style="color: ${gun.rarity_color};">${gun.rarity}</span>
                        </div>
                        <div class="shop-item-thumb">
                            <img src="${gun.icon || ''}" alt="${gun.skin_name}">
                        </div>
                        <strong class="shop-item-name">${gun.skin_name}</strong>
                        ${gun.buddy ? `<small style="color: var(--accent-yellow); margin-top: 4px;"><i class="fa-solid fa-ring"></i> ${gun.buddy}</small>` : ''}
                    </div>
                `).join('')}
            </div>

            ${(loadout.sprays && loadout.sprays.length > 0) ? `
                <h3 style="margin: 28px 0 14px; font-size: 16px;"><i class="fa-solid fa-spray-can"></i> Kuşanılmış Spreyler (4 Yuva)</h3>
                <div class="shop-cards-grid">
                    ${loadout.sprays.map(sp => `
                        <div class="shop-item-card">
                            <div class="shop-item-thumb"><img src="${sp.icon}" alt="${sp.name}"></div>
                            <strong class="shop-item-name">${sp.name}</strong>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>

        <!-- 3. SAHİP OLUNAN SİLAH SKİNLERİ -->
        <div id="subtab-skins" class="subtab-content">
            <div class="skins-filter-bar">
                <input type="text" id="skin-search-filter" placeholder="Skin adı ara..." style="flex: 1;">
                <select id="skin-weapon-filter">
                    <option value="all">Tüm Silahlar (${ownedSkins.length})</option>
                    ${[...new Set(ownedSkins.map(s => s.weapon_name))].sort().map(w => `<option value="${w}">${w}</option>`).join('')}
                </select>
            </div>
            <div class="skins-collection-grid" id="skins-grid-container">
                ${renderSkinsCards(ownedSkins)}
            </div>
        </div>

        <!-- 4. UĞURLUKLAR (BUDDIES) -->
        <div id="subtab-buddies" class="subtab-content">
            <div class="skins-collection-grid">
                ${buddies.length > 0 ? buddies.map(b => `
                    <div class="skin-card">
                        <div class="skin-card-thumb"><img src="${b.icon || ''}" alt="${b.name}" loading="lazy"></div>
                        <strong class="skin-card-name">${b.name}</strong>
                        <small class="skin-card-sub">Silah Uğurluğu</small>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; text-align:center; padding:30px; color:var(--text-muted);">Uğurluk bulunamadı.</div>`}
            </div>
        </div>

        <!-- 5. SPREYLER (SPRAYS) -->
        <div id="subtab-sprays" class="subtab-content">
            <div class="skins-collection-grid">
                ${sprays.length > 0 ? sprays.map(s => `
                    <div class="skin-card">
                        <div class="skin-card-thumb"><img src="${s.icon || ''}" alt="${s.name}" loading="lazy"></div>
                        <strong class="skin-card-name">${s.name}</strong>
                        <small class="skin-card-sub">Grafiti / Sprey</small>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; text-align:center; padding:30px; color:var(--text-muted);">Sprey bulunamadı.</div>`}
            </div>
        </div>

        <!-- 6. OYUNCU KARTLARI (CARDS) -->
        <div id="subtab-cards" class="subtab-content">
            <div class="skins-collection-grid">
                ${cards.length > 0 ? cards.map(c => `
                    <div class="skin-card">
                        <div style="height:100px; background:#0d161f; border-radius:6px; overflow:hidden; margin-bottom:8px;">
                            <img src="${c.wideArt || c.largeArt || c.smallIcon}" style="width:100%; height:100%; object-fit:cover;" loading="lazy">
                        </div>
                        <strong class="skin-card-name">${c.name}</strong>
                        <small class="skin-card-sub">Oyuncu Kartı</small>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; text-align:center; padding:30px; color:var(--text-muted);">Kart bulunamadı.</div>`}
            </div>
        </div>

        <!-- 7. OYUNCU UNVANLARI (TITLES) -->
        <div id="subtab-titles" class="subtab-content">
            <div class="skins-collection-grid">
                ${titles.length > 0 ? titles.map(t => `
                    <div class="skin-card" style="padding:16px; text-align:center;">
                        <strong style="color:var(--accent-yellow); font-size:15px; display:block;">${t.titleText}</strong>
                        <small class="skin-card-sub">Unvan</small>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; text-align:center; padding:30px; color:var(--text-muted);">Unvan bulunamadı.</div>`}
            </div>
        </div>

        <!-- 8. AJANLAR (AGENTS) -->
        <div id="subtab-agents" class="subtab-content">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <h3 style="font-size:16px;"><i class="fa-solid fa-user-shield"></i> Oynanabilir Ajan Kadrosu (${agentsRoster.filter(a => a.is_unlocked).length} / ${agentsRoster.length || 26} Açık)</h3>
            </div>
            <div class="agents-roster-grid">
                ${agentsRoster.length > 0 ? agentsRoster.map(a => `
                    <div class="agent-roster-card ${a.is_unlocked ? 'unlocked' : 'locked'}">
                        <div class="agent-avatar-wrap">
                            <img src="${a.fullPortrait || a.icon || ''}" alt="${a.name}" class="agent-portrait" loading="lazy">
                            <span class="agent-status-badge ${a.is_unlocked ? 'badge-unlocked' : 'badge-locked'}">
                                <i class="fa-solid fa-${a.is_unlocked ? 'check' : 'lock'}"></i> ${a.is_unlocked ? 'Açık' : 'Kilitli'}
                            </span>
                        </div>
                        <div class="agent-info-wrap">
                            <div class="agent-role-tag">
                                ${a.role_icon ? `<img src="${a.role_icon}" style="width:13px; height:13px; vertical-align:middle;">` : ''}
                                <span>${a.role || 'Ajan'}</span>
                            </div>
                            <strong class="agent-name">${a.name}</strong>
                            <div class="agent-abilities-row">
                                ${(a.abilities || []).slice(0, 4).map(ab => `
                                    <div class="ability-icon-pill" title="${ab.slot}: ${ab.name}">
                                        ${ab.icon ? `<img src="${ab.icon}" alt="${ab.name}">` : `<span>${ab.slot}</span>`}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; text-align:center; padding:30px; color:var(--text-muted);">Ajan bilgisi yüklenemedi.</div>`}
            </div>
        </div>

        <!-- 8.5 KONTRATLAR & SAVAŞ BİLETİ (CONTRACTS) -->
        <div id="subtab-contracts" class="subtab-content">
            ${battlepass ? `
                <div class="bp-hero-card" style="background:var(--bg-card); border:1px solid var(--accent-yellow); border-radius:12px; padding:20px; margin-bottom:24px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                        <div style="display:flex; align-items:center; gap:16px;">
                            ${battlepass.display_icon ? `<img src="${battlepass.display_icon}" style="width:54px; height:54px; border-radius:8px;">` : `<i class="fa-solid fa-scroll" style="font-size:32px; color:var(--accent-yellow);"></i>`}
                            <div>
                                <small style="color:var(--accent-yellow); font-weight:700; text-transform:uppercase;">Aktif Savaş Bileti / Sezon Pasosu</small>
                                <h3 style="font-size:20px; color:#fff; margin-top:2px;">${battlepass.name}</h3>
                                <div style="color:var(--text-muted); font-size:12px;">Toplam Kazanılan XP: <strong style="color:#fff;">${battlepass.total_xp.toLocaleString()} XP</strong></div>
                            </div>
                        </div>
                    </div>
                </div>
            ` : '<div style="background:var(--bg-card); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:24px; color:var(--text-muted);">Aktif Savaş Bileti kaydı bulunmuyor veya sezonluk geçiş tamamlanmış.</div>'}

            <h3 style="margin-bottom:14px; font-size:16px;"><i class="fa-solid fa-user-gear"></i> Ajan Kontrat İlerlemeleri</h3>
            <div class="shop-cards-grid">
                ${(agentContracts && agentContracts.length > 0) ? agentContracts.map(c => `
                    <div class="shop-item-card">
                        <strong style="color:#fff; font-size:14px;">${c.name}</strong>
                        <div style="color:var(--accent-green); font-size:12px; margin:6px 0;">Kazanılan XP: <strong>${c.total_xp.toLocaleString()} XP</strong></div>
                        <small style="color:var(--text-muted); font-size:11px;">Durum: ${c.state || 'Aktif'}</small>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; padding:20px; color:var(--text-muted);">Ajan kontrat ilerlemesi bulunmuyor.</div>`}
            </div>
        </div>

        <!-- 9. GÖREVLER (MISSIONS) -->
        <div id="subtab-missions" class="subtab-content">
            <h3 style="margin-bottom: 14px; font-size: 16px;"><i class="fa-solid fa-calendar-day"></i> Günlük Görevler</h3>
            <div class="shop-cards-grid" style="margin-bottom:28px;">
                ${(missions.daily_missions && missions.daily_missions.length > 0) ? missions.daily_missions.map(m => `
                    <div class="shop-item-card">
                        <strong style="color:#fff; font-size:14px;">${m.title}</strong>
                        <div style="font-size:12px; color:var(--accent-green); margin:6px 0;">Ödül: <strong>+${(m.xp_reward || 1000).toLocaleString()} XP</strong></div>
                        <div class="progress-bar-wrap">
                            <div class="progress-bar-fill" style="width: ${Math.min(100, Math.round((m.progress / Math.max(1, m.target)) * 100))}%;"></div>
                        </div>
                        <small style="color:var(--text-muted); font-size:11px;">İlerleme: ${m.progress} / ${m.target} ${m.complete ? '(Tamamlandı)' : ''}</small>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; padding:20px; color:var(--text-muted);">Aktif günlük görev bulunmuyor.</div>`}
            </div>

            <h3 style="margin-bottom: 14px; font-size: 16px;"><i class="fa-solid fa-calendar-week"></i> Haftalık Görevler</h3>
            <div class="shop-cards-grid">
                ${(missions.weekly_missions && missions.weekly_missions.length > 0) ? missions.weekly_missions.map(m => `
                    <div class="shop-item-card">
                        <strong style="color:#fff; font-size:14px;">${m.title}</strong>
                        <div style="font-size:12px; color:var(--accent-yellow); margin:6px 0;">Ödül: <strong>+${(m.xp_reward || 15000).toLocaleString()} XP</strong></div>
                        <div class="progress-bar-wrap">
                            <div class="progress-bar-fill" style="width: ${Math.min(100, Math.round((m.progress / Math.max(1, m.target)) * 100))}%;"></div>
                        </div>
                        <small style="color:var(--text-muted); font-size:11px;">İlerleme: ${m.progress} / ${m.target} ${m.complete ? '(Tamamlandı)' : ''}</small>
                    </div>
                `).join('') : `<div style="grid-column: 1/-1; padding:20px; color:var(--text-muted);">Aktif haftalık görev bulunmuyor.</div>`}
            </div>
        </div>

        <!-- 10. MAÇ GEÇMİŞİ -->
        <div id="subtab-matches" class="subtab-content">
            <div class="table-wrap">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Harita</th>
                            <th>Mod</th>
                            <th>Ajan</th>
                            <th>K / D / A</th>
                            <th>ACS</th>
                            <th>Skor</th>
                            <th>Sonuç</th>
                            <th>Tarih</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${matches.map(m => `
                            <tr>
                                <td>
                                    <div style="display:flex; align-items:center; gap:8px;">
                                        <img src="${m.map_splash}" style="width:40px; height:24px; border-radius:4px; object-fit:cover;">
                                        <strong>${m.map_name}</strong>
                                    </div>
                                </td>
                                <td>${m.game_mode}</td>
                                <td>
                                    <div style="display:flex; align-items:center; gap:8px;">
                                        <img src="${m.agent_icon}" style="width:28px; height:28px; border-radius:50%; background:#192633; object-fit:cover;">
                                        <span>${m.agent_name}</span>
                                    </div>
                                </td>
                                <td><strong>${m.kda_text}</strong> <small style="color:var(--text-muted);">(${m.kd_ratio} KD)</small></td>
                                <td><strong>${m.acs || '—'}</strong></td>
                                <td><strong style="color:#fff;">${m.score_text}</strong></td>
                                <td class="${m.result_class}"><strong>${m.result}</strong></td>
                                <td>${m.date}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 11. CEZALAR VE KISITLAMALAR -->
        <div id="subtab-penalties" class="subtab-content">
            <div class="table-wrap">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Ceza Türü</th>
                            <th>Durum</th>
                            <th>Bitiş Zamanı</th>
                            <th>Kalan Maç</th>
                            <th>İhlal Nedeni</th>
                            <th>Veriliş Tarihi</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(penalties.records && penalties.records.length > 0) ? penalties.records.map(p => `
                            <tr>
                                <td><strong>${p.type}</strong></td>
                                <td class="${p.badge_class}"><strong>${p.state}</strong></td>
                                <td>${p.expiry}</td>
                                <td>${p.games_remaining}</td>
                                <td>${p.infraction}</td>
                                <td>${p.issued_date}</td>
                            </tr>
                        `).join('') : `<tr><td colspan="6" style="text-align:center; padding:30px; color:var(--text-muted);">Kayıtlı ceza veya yaptırım bulunmuyor.</td></tr>`}
                    </tbody>
                </table>
            </div>
        </div>
        `;

        detailsContainer.innerHTML = html;

        // Alt Sekme Dinleyicileri
        document.querySelectorAll(".subtab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".subtab-btn").forEach(b => b.classList.remove("active"));
                document.querySelectorAll(".subtab-content").forEach(c => c.classList.remove("active"));
                btn.classList.add("active");
                const targetId = btn.dataset.subtab;
                const targetEl = document.getElementById(targetId);
                if (targetEl) targetEl.classList.add("active");
            });
        });

        // Skin filtreleme
        const skinSearch = document.getElementById("skin-search-filter");
        const skinFilter = document.getElementById("skin-weapon-filter");
        const skinsGrid = document.getElementById("skins-grid-container");

        function filterSkins() {
            const query = (skinSearch.value || "").toLowerCase();
            const weapon = skinFilter.value;

            const filtered = ownedSkins.filter(s => {
                const matchName = s.skin_name.toLowerCase().includes(query) || s.weapon_name.toLowerCase().includes(query);
                const matchWeapon = (weapon === "all") || (s.weapon_name === weapon);
                return matchName && matchWeapon;
            });

            skinsGrid.innerHTML = renderSkinsCards(filtered);
        }

        if (skinSearch) skinSearch.addEventListener("input", filterSkins);
        if (skinFilter) skinFilter.addEventListener("change", filterSkins);
    }

    function formatDuration(seconds) {
        if (!seconds) return "Bilinmiyor";
        const d = Math.floor(seconds / 86400);
        const h = Math.floor((seconds % 86400) / 3600);
        return d > 0 ? `${d} gün ${h} saat` : `${h} saat`;
    }

    function renderSkinsCards(skins) {
        if (!skins || skins.length === 0) {
            return `<div style="grid-column: 1/-1; text-align: center; padding: 30px; color: var(--text-muted);">Eşleşen skin bulunamadı.</div>`;
        }
        return skins.map(s => `
            <div class="skin-card" style="border-color: ${s.rarity_color || '#344454'}44;">
                <div class="skin-card-thumb">
                    <img src="${s.icon || ''}" alt="${s.skin_name}" loading="lazy">
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:10px; font-weight:700; color:${s.rarity_color || '#fff'};">${s.rarity || 'Standart'}</span>
                    ${s.theme_name ? `<span style="font-size:10px; color:var(--text-muted); background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px;">${s.theme_name}</span>` : ''}
                </div>
                <strong class="skin-card-name">${s.skin_name}</strong>
                <small class="skin-card-sub">${s.weapon_name}</small>
            </div>
        `).join('');
    }

    // ========================================================
    // HIZLI HESAPLAR LİSTESİ
    // ========================================================
    async function loadQuickAccounts() {
        try {
            const res = await fetch("/api/accounts");
            const accounts = await res.json();
            quickAccountsCount.textContent = accounts.length;

            if (accounts.length === 0) {
                quickAccountsList.innerHTML = `<div class="empty-state">Henüz kayıtlı hesap yok.</div>`;
                return;
            }

            quickAccountsList.innerHTML = accounts.map(acc => `
                <div class="quick-acc-item" data-puuid="${acc.puuid}">
                    <div>
                        <div class="quick-acc-name">${acc.riot_id}</div>
                        <div class="quick-acc-sub">Lv. ${acc.last_level} &bull; ${acc.region.toUpperCase()} &bull; ${acc.total_checks} kontrol</div>
                    </div>
                    <div class="quick-acc-rank" style="color: var(--accent-red);">${acc.last_rank_name}</div>
                </div>
            `).join('');

            document.querySelectorAll(".quick-acc-item").forEach(item => {
                item.addEventListener("click", () => {
                    loadAccountByPuuid(item.dataset.puuid);
                });
            });

        } catch (e) {
            console.error(e);
        }
    }

    async function loadAccountByPuuid(puuid) {
        try {
            const res = await fetch(`/api/accounts/${puuid}`);
            const data = await res.json();
            if (data.latest_log && data.latest_log.snapshot) {
                currentSnapshot = data.latest_log.snapshot;
                currentAccount = data;
                renderAccountDetails(currentSnapshot);
                switchTab("tab-details");
            } else {
                showToast("Bu hesaba ait log snapshot bulunamadı.", "error");
            }
        } catch (e) {
            showToast("Hesap detayları yüklenemedi.", "error");
        }
    }

    // ========================================================
    // GEÇMİŞ LOGLAR VE HESAPLAR TABI
    // ========================================================
    async function loadAccountsList() {
        try {
            const res = await fetch("/api/accounts");
            const accounts = await res.json();

            if (accounts.length === 0) {
                historyAccountsList.innerHTML = `<div style="padding:15px; color:var(--text-muted); font-size:13px;">Kayıtlı hesap yok.</div>`;
                logsTbody.innerHTML = `<tr><td colspan="9" class="empty-cell">Veritabanında henüz hesap kaydı bulunmuyor.</td></tr>`;
                historyActions.style.display = "none";
                return;
            }

            historyAccountsList.innerHTML = accounts.map(acc => `
                <div class="acc-select-btn ${selectedHistoryPuuid === acc.puuid ? 'active' : ''}" data-puuid="${acc.puuid}">
                    <strong style="display:block; font-size:14px; color:#fff;">${acc.riot_id}</strong>
                    <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">
                        ${acc.region.toUpperCase()} &bull; Lv. ${acc.last_level} &bull; ${acc.total_checks} Kontrol
                    </div>
                </div>
            `).join('');

            document.querySelectorAll(".acc-select-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    document.querySelectorAll(".acc-select-btn").forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");
                    selectedHistoryPuuid = btn.dataset.puuid;
                    loadAccountLogs(selectedHistoryPuuid);
                });
            });

            if (!selectedHistoryPuuid && accounts.length > 0) {
                selectedHistoryPuuid = accounts[0].puuid;
                const firstBtn = document.querySelector(`.acc-select-btn[data-puuid="${selectedHistoryPuuid}"]`);
                if (firstBtn) firstBtn.classList.add("active");
                loadAccountLogs(selectedHistoryPuuid);
            }

        } catch (e) {
            console.error(e);
        }
    }

    async function loadAccountLogs(puuid) {
        try {
            const res = await fetch(`/api/accounts/${puuid}/logs`);
            const logs = await res.json();

            historyActions.style.display = "flex";
            if (logs.length > 0) {
                historyAccountTitle.innerHTML = `<i class="fa-solid fa-list-check"></i> ${logs[0].riot_id} - Kontrol Geçmişi`;
                historyAccountSubtitle.textContent = `Toplam ${logs.length} adet detaylı kontrol kaydı listeleniyor.`;
            }

            if (logs.length === 0) {
                logsTbody.innerHTML = `<tr><td colspan="9" class="empty-cell">Bu hesaba ait log bulunamadı.</td></tr>`;
                return;
            }

            logsTbody.innerHTML = logs.map(log => `
                <tr>
                    <td>#${log.id}</td>
                    <td><strong>${log.check_date_local}</strong></td>
                    <td><span class="region-tag">${(log.region || 'EU').toUpperCase()}</span></td>
                    <td><strong>Lv. ${log.level}</strong></td>
                    <td><strong>${log.rank_name}</strong> (${log.ranked_rating} RR)</td>
                    <td><span style="color:#ff4655;">${log.wallet_vp} VP</span> / <span style="color:#00ffb3;">${log.wallet_rp} RP</span> / <span style="color:#f0bd4f;">${log.wallet_kc} KC</span></td>
                    <td><span class="${log.penalty_status === 'Temiz' ? 'good' : 'bad'}">${log.penalty_status}</span></td>
                    <td><strong>${log.skins_count}</strong> Skin</td>
                    <td>
                        <button class="btn btn-outline" style="padding:4px 8px; font-size:12px;" onclick="viewHistoricalLog(${log.id})">
                            <i class="fa-solid fa-eye"></i> Detay
                        </button>
                        <button class="btn btn-outline" style="padding:4px 8px; font-size:12px;" onclick="exportLogHtml(${log.id})">
                            <i class="fa-solid fa-file-export"></i> HTML
                        </button>
                    </td>
                </tr>
            `).join('');

        } catch (e) {
            console.error(e);
        }
    }

    window.viewHistoricalLog = async function(logId) {
        try {
            const res = await fetch(`/api/logs/${logId}`);
            const data = await res.json();
            if (data.snapshot) {
                currentSnapshot = data.snapshot;
                renderAccountDetails(currentSnapshot);
                switchTab("tab-details");
                showToast(`Log #${logId} başarıyla yüklendi!`, "success");
            }
        } catch (e) {
            showToast("Log yüklenemedi.", "error");
        }
    };

    window.exportHtml = function(puuid, logId) {
        window.open(`/api/export/html/${puuid}`, "_blank");
    };

    window.exportLogHtml = function(logId) {
        window.open(`/api/export/html/log/${logId}`, "_blank");
    };

    btnExportLatestHtml.addEventListener("click", () => {
        if (selectedHistoryPuuid) {
            window.open(`/api/export/html/${selectedHistoryPuuid}`, "_blank");
        }
    });

    btnDeleteAccount.addEventListener("click", async () => {
        if (!selectedHistoryPuuid) return;
        if (!confirm("Bu hesabı ve tüm geçmiş loglarını veritabanından kalıcı olarak silmek istediğinize emin misiniz?")) {
            return;
        }

        try {
            const res = await fetch(`/api/accounts/${selectedHistoryPuuid}`, { method: "DELETE" });
            if (res.ok) {
                showToast("Hesap veritabanından silindi.", "success");
                selectedHistoryPuuid = null;
                loadAccountsList();
                loadQuickAccounts();
                updateDbStats();
            } else {
                showToast("Hesap silinemedi.", "error");
            }
        } catch (e) {
            showToast("İstek başarısız oldu.", "error");
        }
    });

    // ========================================================
    // 4. TAB: DASH.VALORANT-API.COM 30 UÇ NOKTA GEZGİNİ
    // ========================================================
    async function loadEndpointsList() {
        try {
            const res = await fetch("/api/content/endpoints");
            const endpoints = await res.json();

            endpointsMenu.innerHTML = endpoints.map(ep => `
                <button class="endpoint-btn ${ep.id === activeEndpointId ? 'active' : ''}" data-id="${ep.id}">
                    <span>${ep.name}</span>
                    <i class="fa-solid fa-angle-right" style="font-size:11px;"></i>
                </button>
            `).join('');

            document.querySelectorAll(".endpoint-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    document.querySelectorAll(".endpoint-btn").forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");
                    activeEndpointId = btn.dataset.id;
                    loadEndpointContent(activeEndpointId);
                });
            });

            loadEndpointContent(activeEndpointId);

        } catch (e) {
            console.error(e);
        }
    }

    async function loadEndpointContent(endpointId) {
        endpointItemsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px;"><div class="spinner" style="margin: 0 auto 14px;"></div>dash.valorant-api.com verileri alınıyor...</div>`;

        try {
            const res = await fetch(`/api/content/${endpointId}`);
            const data = await res.json();
            activeEndpointRawData = data;

            endpointActiveTitle.textContent = `${endpointId.toUpperCase()}`;
            endpointActiveUrl.textContent = `https://valorant-api.com/v1/${endpointId}`;

            renderEndpointItems(data);

        } catch (e) {
            endpointItemsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; color:var(--accent-red); padding:30px;">Uç nokta yüklenemedi.</div>`;
        }
    }

    function renderEndpointItems(data) {
        if (!data) return;

        // Özel Uç Nokta Dönüşümleri (30 Uç Nokta Uyumluluğu)
        let items = [];
        if (!Array.isArray(data)) {
            // Version gibi tekil nesneler
            if (data.riotClientVersion || data.version) {
                items = [
                    { displayName: "Riot İstemci Sürümü", description: data.riotClientVersion, displayIcon: "" },
                    { displayName: "Oyun Versiyonu", description: data.version, displayIcon: "" },
                    { displayName: "Build Versiyonu", description: data.buildVersion, displayIcon: "" },
                    { displayName: "Riot Client Build", description: data.riotClientBuild, displayIcon: "" },
                    { displayName: "Derleme Tarihi", description: data.buildDate, displayIcon: "" },
                    { displayName: "Engine Versiyonu", description: data.engineVersion, displayIcon: "" },
                    { displayName: "Branch", description: data.branch, displayIcon: "" },
                    { displayName: "Manifest ID", description: data.manifestId, displayIcon: "" },
                ];
            } else {
                items = [data];
            }
        } else if (data.length > 0 && data[0].tiers) {
            // competitivetiers: Bölümlerin içindeki kademeleri (Demir..Radyant) düzleştir
            items = [];
            data.forEach(ep => {
                const epName = ep.assetObjectName ? ep.assetObjectName.replace("DataTable", "").replace("_", " ") : "Bölüm";
                (ep.tiers || []).forEach(t => {
                    if (t.tier > 0) {
                        items.push({
                            ...t,
                            displayName: t.tierName || `Kademe ${t.tier}`,
                            description: `${epName} &bull; ${t.divisionName || ''}`,
                            displayIcon: t.largeIcon || t.smallIcon || "",
                        });
                    }
                });
            });
        } else {
            items = data;
        }

        const query = (endpointSearchInput.value || "").toLowerCase();

        if (query) {
            items = items.filter(it => {
                const name = (it.displayName || it.tierName || it.title || it.name || it.titleText || "").toLowerCase();
                const desc = (it.description || it.category || it.directive || "").toLowerCase();
                return name.includes(query) || desc.includes(query);
            });
        }

        if (items.length === 0) {
            endpointItemsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:30px; color:var(--text-muted);">Eşleşen öğe bulunamadı.</div>`;
            return;
        }

        endpointItemsGrid.innerHTML = items.map(item => {
            const name = item.displayName || item.tierName || item.title || item.name || item.titleText || (item.startingLevel ? `${item.startingLevel}. Seviye Çerçevesi` : (item.seasonUuid ? `Sezon ${item.seasonUuid.substring(0,8)}` : "İçerik"));
            const icon = item.displayIcon || item.largeIcon || item.smallIcon || item.splash || item.fullTransparentIcon || item.fullRender || item.levelNumberAppearance || item.smallPlayerCardAppearance || item.swatch || (item.identity ? item.identity.smallIcon : "");
            const desc = item.description || item.category || item.directive || (item.developerName ? item.developerName : "") || (item.xpGrant ? `+${item.xpGrant.toLocaleString()} XP` : (item.startingLevel ? `Gereken Seviye: ${item.startingLevel}` : (item.startTime ? `Başlangıç: ${item.startTime.substring(0,10)}` : "")));

            return `
                <div class="item-preview-card">
                    <div class="item-thumb-box">
                        ${icon ? `<img src="${icon}" alt="${name}" loading="lazy">` : `<i class="fa-solid fa-cube" style="font-size:24px; color:var(--text-dim);"></i>`}
                    </div>
                    <strong class="item-preview-title">${name}</strong>
                    <small class="item-preview-sub">${desc ? desc.substring(0, 60) + (desc.length > 60 ? '...' : '') : ''}</small>
                </div>
            `;
        }).join('');
    }

    if (endpointSearchInput) {
        endpointSearchInput.addEventListener("input", () => {
            if (activeEndpointRawData) renderEndpointItems(activeEndpointRawData);
        });
    }

    btnRefreshEndpoint.addEventListener("click", () => {
        loadEndpointContent(activeEndpointId);
    });

    btnViewRawJson.addEventListener("click", () => {
        if (activeEndpointRawData) {
            jsonModalCode.textContent = JSON.stringify(activeEndpointRawData, null, 2);
            jsonModal.classList.remove("hidden");
        }
    });

    window.viewJsonSnapshot = function() {
        if (currentSnapshot) {
            jsonModalCode.textContent = JSON.stringify(currentSnapshot, null, 2);
            jsonModal.classList.remove("hidden");
        }
    };

    btnCloseJsonModal.addEventListener("click", () => {
        jsonModal.classList.add("hidden");
    });

    jsonModal.addEventListener("click", (e) => {
        if (e.target === jsonModal) jsonModal.classList.add("hidden");
    });

    updateDbStats();
    loadQuickAccounts();
});
