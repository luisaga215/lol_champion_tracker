// Global State
let champions = [];
let stats = { total: 0, played: 0, top4: 0, won: 0 };
let searchQuery = '';
let currentFilter = 'all';
let currentRole = 'all';
let currentSort = 'name-asc';
let arenaMeta = {};
let latestPatch = null;

// DOM Elements
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search');
const filterButtons = document.querySelectorAll('.filter-btn');
const roleSelect = document.getElementById('role-select');
const sortSelect = document.getElementById('sort-select');
const championsGrid = document.getElementById('champions-grid');
const loadingState = document.getElementById('loading-state');

// Stats Elements
const statTotal = document.getElementById('stat-total');
const fractionPlayed = document.getElementById('fraction-played');
const pctPlayed = document.getElementById('pct-played');
const barPlayed = document.getElementById('bar-played');

const fractionTop4 = document.getElementById('fraction-top4');
const pctTop4 = document.getElementById('pct-top4');
const barTop4 = document.getElementById('bar-top4');

const fractionWon = document.getElementById('fraction-won');
const pctWon = document.getElementById('pct-won');
const barWon = document.getElementById('bar-won');

// Initialize App
window.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupMetaModal();
    setupTooltip();
    initPingTester();
    fetchData();
});

// Setup Event Listeners
function setupEventListeners() {
    // Search input
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            if (clearSearchBtn) {
                clearSearchBtn.style.display = searchQuery ? 'flex' : 'none';
            }
            renderGrid();
        });
    }

    // Clear search
    if (clearSearchBtn && searchInput) {
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = '';
            searchQuery = '';
            clearSearchBtn.style.display = 'none';
            searchInput.focus();
            renderGrid();
        });
    }

    // Filter buttons
    if (filterButtons) {
        filterButtons.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                filterButtons.forEach((b) => b.classList.remove('active'));
                e.target.classList.add('active');
                currentFilter = e.target.getAttribute('data-filter');
                renderGrid();
            });
        });
    }

    // Role select
    if (roleSelect) {
        roleSelect.addEventListener('change', (e) => {
            currentRole = e.target.value;
            renderGrid();
        });
    }

    // Sort select
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            currentSort = e.target.value;
            renderGrid();
        });
    }
}

// Fetch champions and statistics
async function fetchData() {
    try {
        const [champsRes, statsRes] = await Promise.all([
            fetch('/api/champions'),
            fetch('/api/stats')
        ]);

        if (!champsRes.ok || !statsRes.ok) {
            throw new Error('Server returned an error fetching data.');
        }

        champions = await champsRes.json();
        stats = await statsRes.json();
        arenaMeta = await fetchArenaMeta();
        await fetchBuildStyles();

        renderStats();
        renderGrid();
    } catch (err) {
        console.error('Error fetching data:', err);
        championsGrid.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Tracker</h3>
                <p>Failed to connect to the server database. Is the server running?</p>
                <button onclick="fetchData()" class="filter-btn active" style="margin-top: 1rem;">Try Again</button>
            </div>
        `;
    } finally {
        // Always hide loading state once fetch concludes
        if (loadingState) {
            loadingState.style.display = 'none';
        }
    }
}

// Fetch arena meta for the latest patch and index it by numeric champion id.
async function fetchArenaMeta() {
    try {
        const patchesRes = await fetch('/api/arena/patches');
        if (!patchesRes.ok) return {};
        const patches = await patchesRes.json();
        if (!Array.isArray(patches) || patches.length === 0) return {};
        const latest = patches[0];
        latestPatch = latest;
        updatePatchBadge(latest);

        const metaRes = await fetch(`/api/arena/meta?patch=${encodeURIComponent(latest)}`);
        if (!metaRes.ok) return {};

        const list = await metaRes.json();
        const map = {};
        for (const meta of list) {
            map[String(meta.champion_id)] = meta;
        }
        return map;
    } catch (err) {
        return {};
    }
}

function updatePatchBadge(latest) {
    const badge = document.getElementById('patch-badge');
    const value = document.getElementById('patch-badge-value');
    if (badge && latest) {
        badge.hidden = false;
        if (value) value.textContent = latest;
    }
}

// Render Statistics Dashboard
function renderStats() {
    statTotal.textContent = stats.total;

    // Played Stats
    fractionPlayed.textContent = `${stats.played}/${stats.total}`;
    const playedPctVal = stats.total > 0 ? Math.round((stats.played / stats.total) * 100) : 0;
    pctPlayed.textContent = `${playedPctVal}%`;
    barPlayed.style.width = `${playedPctVal}%`;

    // Top 4 Stats
    fractionTop4.textContent = `${stats.top4}/${stats.total}`;
    const top4PctVal = stats.total > 0 ? Math.round((stats.top4 / stats.total) * 100) : 0;
    pctTop4.textContent = `${top4PctVal}%`;
    barTop4.style.width = `${top4PctVal}%`;

    // Won Stats
    fractionWon.textContent = `${stats.won}/${stats.total}`;
    const wonPctVal = stats.total > 0 ? Math.round((stats.won / stats.total) * 100) : 0;
    pctWon.textContent = `${wonPctVal}%`;
    barWon.style.width = `${wonPctVal}%`;
}

// Update single champion status in the backend
async function toggleStatus(champId, field) {
    const champ = champions.find((c) => c.id === champId);
    if (!champ) return;

    // Prepare payload by toggling the selected field
    const payload = {
        played: field === 'played' ? !champ.played : champ.played,
        top4: field === 'top4' ? !champ.top4 : champ.top4,
        won: field === 'won' ? !champ.won : champ.won
    };

    try {
        const response = await fetch(`/api/champions/${champId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Failed to update champion status');

        const updatedChamp = await response.json();
        
        // Update local champion data
        const index = champions.findIndex((c) => c.id === champId);
        if (index !== -1) {
            champions[index] = updatedChamp;
        }

        // Fetch updated stats from server
        const statsRes = await fetch('/api/stats');
        if (statsRes.ok) {
            stats = await statsRes.json();
            renderStats();
        }

        // Update the card DOM directly to avoid full grid re-render (smooth animation!)
        updateCardDOM(updatedChamp);

    } catch (err) {
        console.error('Error updating champion status:', err);
    }
}

// Update card DOM in-place without rebuilding grid
function updateCardDOM(champ) {
    const card = document.querySelector(`.champion-card[data-id="${champ.id}"]`);
    if (!card) return;

    // Update unplayed/won classes on the card
    const isUnplayed = !champ.played;
    if (isUnplayed) {
        card.classList.add('unplayed');
    } else {
        card.classList.remove('unplayed');
    }

    if (champ.won) {
        card.classList.add('won-champion');
        // Add crown if not present
        if (!card.querySelector('.crown-icon')) {
            const crown = document.createElement('div');
            crown.className = 'crown-icon';
            crown.innerHTML = `
                <svg viewBox="0 0 24 24">
                    <path d="M12 2l3 5.5 5.5-2.5-3 8.5h-11l-3-8.5 5.5 2.5zM2 20h20v2h-20z"></path>
                </svg>
            `;
            card.querySelector('.portrait-container').appendChild(crown);
        }
    } else {
        card.classList.remove('won-champion');
        const crown = card.querySelector('.crown-icon');
        if (crown) crown.remove();
    }

    // Update status buttons active classes
    const secP = card.querySelector('.sec-p');
    const secT = card.querySelector('.sec-t');
    const secW = card.querySelector('.sec-w');

    if (champ.played) secP.classList.add('active'); else secP.classList.remove('active');
    if (champ.top4) secT.classList.add('active'); else secT.classList.remove('active');
    if (champ.won) secW.classList.add('active'); else secW.classList.remove('active');

    // If card no longer matches filter, we can animate it fading out
    if (!matchesFilter(champ)) {
        card.style.transition = 'opacity 0.25s, transform 0.25s';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.8)';
        setTimeout(() => {
            // Check if filter has changed since timeout
            if (!matchesFilter(champions.find(c => c.id === champ.id))) {
                card.style.display = 'none';
            } else {
                card.style.display = 'flex';
                card.style.opacity = '1';
                card.style.transform = 'none';
            }
        }, 250);
    }
}

// Check if a champion matches the current filter
function matchesFilter(champ) {
    // Search query check
    if (searchQuery && !champ.name.toLowerCase().includes(searchQuery)) {
        return false;
    }

    // Role filter check
    if (currentRole !== 'all') {
        const roles = champ.tags ? champ.tags.split(',') : [];
        if (!roles.includes(currentRole)) {
            return false;
        }
    }

    // Status filter check
    switch (currentFilter) {
        case 'unplayed':
            return champ.played === 0;
        case 'played':
            return champ.played === 1;
        case 'top4':
            return champ.top4 === 1;
        case 'won':
            return champ.won === 1;
        case 'missing-top4':
            return champ.played === 1 && champ.top4 === 0;
        case 'missing-won':
            return champ.played === 1 && champ.won === 0;
        case 'all':
        default:
            return true;
    }
}

// Render Champion Cards Grid
function renderGrid() {
    // Filter champions
    let filteredChamps = champions.filter(matchesFilter);

    // Sort champions
    filteredChamps.sort((a, b) => {
        // Name A-Z
        if (currentSort === 'name-asc') {
            return a.name.localeCompare(b.name);
        }
        // Name Z-A
        if (currentSort === 'name-desc') {
            return b.name.localeCompare(a.name);
        }
        
        // Custom score for completion sort: Won = 3, Top 4 = 2, Played = 1, Unplayed = 0
        const score = (champ) => {
            if (champ.won) return 3;
            if (champ.top4) return 2;
            if (champ.played) return 1;
            return 0;
        };

        const scoreA = score(a);
        const scoreB = score(b);

        if (currentSort === 'status-desc') {
            // Highest completion first, alphabetical if equal
            if (scoreB !== scoreA) return scoreB - scoreA;
            return a.name.localeCompare(b.name);
        }
        if (currentSort === 'status-asc') {
            // Lowest completion first, alphabetical if equal
            if (scoreA !== scoreB) return scoreA - scoreB;
            return a.name.localeCompare(b.name);
        }
        return 0;
    });

    // Clear grid
    championsGrid.innerHTML = '';

    if (filteredChamps.length === 0) {
        championsGrid.innerHTML = `
            <div class="empty-state">
                <h3>No Champions Found</h3>
                <p>Try modifying your search query or filter chips.</p>
            </div>
        `;
        return;
    }

    // Build fragment to insert efficiently
    const fragment = document.createDocumentFragment();

    filteredChamps.forEach((champ) => {
        const card = document.createElement('div');
        card.className = 'champion-card';
        card.setAttribute('data-id', champ.id);
        if (!champ.played) card.classList.add('unplayed');
        if (champ.won) card.classList.add('won-champion');

        // Portrait Container (click opens the Arena meta modal)
        const portraitCont = document.createElement('div');
        portraitCont.className = 'portrait-container';

        const img = document.createElement('img');
        img.src = `/images/champion/${champ.image_name}`;
        img.alt = champ.name;
        img.loading = 'lazy';
        img.className = 'portrait-img';
        img.addEventListener('click', () => {
            const m = arenaMeta[String(champ.key)] || emptyMeta('Recommended');
            if (!m.patch_version) m.patch_version = latestPatch || '';
            openMetaModal(champ, m);
        });
        portraitCont.appendChild(img);

        // Add Crown overlay if Won
        if (champ.won) {
            const crown = document.createElement('div');
            crown.className = 'crown-icon';
            crown.innerHTML = `
                <svg viewBox="0 0 24 24">
                    <path d="M12 2l3 5.5 5.5-2.5-3 8.5h-11l-3-8.5 5.5 2.5zM2 20h20v2h-20z"></path>
                </svg>
            `;
            portraitCont.appendChild(crown);
        }

        card.appendChild(portraitCont);

        // Info / Name
        const info = document.createElement('div');
        info.className = 'champ-info';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'champ-name';
        nameSpan.textContent = champ.name;
        info.appendChild(nameSpan);

        // Arena tier badge -> Metasrc build link
        const meta = arenaMeta[String(champ.key)];
        if (meta) {
            const slug = ({'Nunu & Willump': 'nunu', 'Jarvan IV': 'jarvan'})[champ.name]
                || champ.name.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-');
            const badge = document.createElement('a');
            badge.className = `meta-tier-badge ${tierClass(meta.tier_rank)}`;
            badge.textContent = meta.tier_rank;
            badge.href = `https://www.metasrc.com/lol/arena/champions/${slug}/build`;
            badge.target = '_blank';
            badge.rel = 'noopener noreferrer';
            badge.title = 'Open Metasrc build';
            badge.addEventListener('click', (e) => e.stopPropagation());
            info.appendChild(badge);
        }

        card.appendChild(info);

        // Status Button Bar
        const statusBar = document.createElement('div');
        statusBar.className = 'status-bar';

        // P (Played)
        const btnP = document.createElement('button');
        btnP.className = `status-sec sec-p ${champ.played ? 'active' : ''}`;
        btnP.textContent = 'P';
        btnP.setAttribute('data-tooltip', 'Played');
        btnP.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleStatus(champ.id, 'played');
        });

        // T (Top 4)
        const btnT = document.createElement('button');
        btnT.className = `status-sec sec-t ${champ.top4 ? 'active' : ''}`;
        btnT.textContent = 'T';
        btnT.setAttribute('data-tooltip', 'Top 4');
        btnT.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleStatus(champ.id, 'top4');
        });

        // W (Won)
        const btnW = document.createElement('button');
        btnW.className = `status-sec sec-w ${champ.won ? 'active' : ''}`;
        btnW.textContent = 'W';
        btnW.setAttribute('data-tooltip', 'Won (1st)');
        btnW.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleStatus(champ.id, 'won');
        });

        statusBar.appendChild(btnP);
        statusBar.appendChild(btnT);
        statusBar.appendChild(btnW);
        card.appendChild(statusBar);

        fragment.appendChild(card);
    });

    championsGrid.appendChild(fragment);
}

// ==========================================
// Live Server Latency / Ping Tester
// ==========================================
const PING_REGIONS = {
    la1: { name: 'LAN', url: 'https://la1.api.riotgames.com', extUrl: 'https://lol-ping.com/en/lan-ping-test/' },
    na1: { name: 'NA', url: 'https://na1.api.riotgames.com', extUrl: 'https://lol-ping.com/en/na-ping-test/' },
    la2: { name: 'LAS', url: 'https://la2.api.riotgames.com', extUrl: 'https://lol-ping.com/en/las-ping-test/' },
    euw1: { name: 'EUW', url: 'https://euw1.api.riotgames.com', extUrl: 'https://lol-ping.com/en/euw-ping-test/' },
    br1: { name: 'BR', url: 'https://br1.api.riotgames.com', extUrl: 'https://lol-ping.com/en/br-ping-test/' }
};

let currentPingRegion = 'la1';
try {
    currentPingRegion = localStorage.getItem('lol_arena_ping_region') || 'la1';
} catch (e) {
    currentPingRegion = 'la1';
}
let isTestingPing = false;

function initPingTester() {
    const pingWidget = document.getElementById('ping-widget');
    const regionSelect = document.getElementById('ping-region-select');
    const retestBtn = document.getElementById('ping-retest-btn');
    const refreshBtn = document.getElementById('ping-refresh-btn');

    if (!pingWidget) return;

    if (regionSelect) {
        if (PING_REGIONS[currentPingRegion]) {
            regionSelect.value = currentPingRegion;
        }
        updatePingExtLink();

        regionSelect.addEventListener('change', (e) => {
            currentPingRegion = e.target.value;
            try {
                localStorage.setItem('lol_arena_ping_region', currentPingRegion);
            } catch (err) {}
            updatePingExtLink();
            testPing();
        });
    }

    if (retestBtn) {
        retestBtn.addEventListener('click', () => {
            if (!isTestingPing) testPing();
        });
        retestBtn.addEventListener('keydown', (e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !isTestingPing) {
                e.preventDefault();
                testPing();
            }
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!isTestingPing) testPing();
        });
    }

    // Initial test on page load
    testPing(false);

    // Auto-refresh every 15 seconds when active
    setInterval(() => {
        if (!document.hidden && !isTestingPing) {
            testPing(true);
        }
    }, 15000);

    // Re-test when tab gains focus
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && !isTestingPing) {
            testPing(true);
        }
    });
}

function updatePingExtLink() {
    const extLink = document.getElementById('ping-ext-link');
    const regionData = PING_REGIONS[currentPingRegion] || PING_REGIONS.la1;
    if (extLink && regionData.extUrl) {
        extLink.href = regionData.extUrl;
    }
}

async function pingOnce(baseUrl) {
    const start = performance.now();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
    const url = `${baseUrl}?_t=${Date.now()}_${Math.random()}`;

    try {
        await fetch(url, {
            method: 'GET',
            mode: 'no-cors',
            cache: 'no-store',
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return Math.max(1, Math.round(performance.now() - start));
    } catch (e) {
        clearTimeout(timeoutId);
        if (e.name === 'AbortError') return null;
        const elapsed = Math.round(performance.now() - start);
        return elapsed > 0 && elapsed < 2500 ? elapsed : null;
    }
}

async function testPing(isAuto = false) {
    if (isTestingPing) return;
    isTestingPing = true;

    const pingWidget = document.getElementById('ping-widget');
    const pingValue = document.getElementById('ping-value');
    const refreshBtn = document.getElementById('ping-refresh-btn');
    const regionData = PING_REGIONS[currentPingRegion] || PING_REGIONS.la1;

    if (pingWidget) {
        if (!isAuto || !pingValue || pingValue.textContent === '-- ms') {
            pingWidget.className = 'ping-widget quality-testing';
            if (pingValue) pingValue.textContent = '... ms';
        }
        pingWidget.title = `Testing latency to Riot ${regionData.name} server...`;
    }
    if (refreshBtn) refreshBtn.classList.add('rotating');

    try {
        // Warmup connection
        await pingOnce(regionData.url);

        // Run 4 latency samples
        const samples = [];
        for (let i = 0; i < 4; i++) {
            const ms = await pingOnce(regionData.url);
            if (ms !== null) samples.push(ms);
            if (i < 3) await new Promise((r) => setTimeout(r, 70));
        }

        if (samples.length > 0) {
            const avgPing = Math.round(samples.reduce((a, b) => a + b, 0) / samples.length);
            let jitter = 0;
            if (samples.length > 1) {
                let diffSum = 0;
                for (let i = 1; i < samples.length; i++) {
                    diffSum += Math.abs(samples[i] - samples[i - 1]);
                }
                jitter = Math.round(diffSum / (samples.length - 1));
            }
            applyPingResult(avgPing, jitter, regionData.name, samples);
        } else {
            applyPingError(regionData.name);
        }
    } catch (err) {
        applyPingError(regionData.name);
    } finally {
        isTestingPing = false;
        if (refreshBtn) refreshBtn.classList.remove('rotating');
    }
}

function applyPingResult(ms, jitter, regionName, samples) {
    const pingWidget = document.getElementById('ping-widget');
    const pingValue = document.getElementById('ping-value');
    if (!pingWidget || !pingValue) return;

    let qualityClass = 'quality-excellent';
    let qualityLabel = '🟢 Excellent (0-30 ms)';

    if (ms > 100) {
        qualityClass = 'quality-poor';
        qualityLabel = '🔴 Poor (100+ ms)';
    } else if (ms > 60) {
        qualityClass = 'quality-fair';
        qualityLabel = '🟡 Fair (60-100 ms)';
    } else if (ms > 30) {
        qualityClass = 'quality-good';
        qualityLabel = '🔵 Good (30-60 ms)';
    }

    pingWidget.className = `ping-widget ${qualityClass}`;
    pingValue.textContent = `${ms} ms`;
    const minPing = Math.min(...samples);
    const maxPing = Math.max(...samples);
    const estGamePing = Math.max(15, ms - 40);
    pingWidget.title = `${regionName} Server (${PING_REGIONS[currentPingRegion]?.url || ''})\n` +
        `Web Latency: ${ms} ms • Jitter: ${jitter} ms\n` +
        `Est. In-Game UDP: ~${estGamePing} ms\n` +
        `Range: ${minPing} - ${maxPing} ms (${qualityLabel})\n` +
        `Auto-refreshes every 15s • Click to re-test`;
}

function applyPingError(regionName) {
    const pingWidget = document.getElementById('ping-widget');
    const pingValue = document.getElementById('ping-value');
    if (!pingWidget || !pingValue) return;

    pingWidget.className = 'ping-widget quality-poor';
    pingValue.textContent = 'Offline';
    pingWidget.title = `Could not reach ${regionName} server. Click to retry.`;
}

// ==========================================
// Arena Meta Modal
// ==========================================
const BUILD_STYLES = [
    'Recommended', 'AD', 'Crit', 'MS', 'CDR', 'HP', 'On-Hit',
    'Lethality', 'MR', 'AP', 'AR', 'LS', 'Mana', 'SV'
];

let buildStyleList = [];

const modalState = {
    champion: null,
    patch: null,
    styles: [],
    currentStyle: 'Recommended',
    meta: null
};

function setupMetaModal() {
    const modal = document.getElementById('meta-modal');
    const closeBtn = document.getElementById('meta-modal-close');
    if (!modal || !closeBtn) return;

    closeBtn.addEventListener('click', closeMetaModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeMetaModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMetaModal();
    });
    document.addEventListener('click', (e) => {
        const menu = document.getElementById('style-menu');
        if (menu && !menu.hidden && !e.target.closest('.style-dropdown')) menu.hidden = true;
    });
}

async function fetchBuildStyles() {
    try {
        const res = await fetch('/api/arena/build-styles');
        if (res.ok) buildStyleList = await res.json();
    } catch (err) { /* pipeline unavailable */ }
}

function styleIcon(style) {
    const found = buildStyleList.find((s) => s.build_style === style);
    return found ? found.icon : '';
}

function toggleStyleMenu(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('style-menu');
    if (menu) menu.hidden = !menu.hidden;
}

async function openMetaModal(champ, meta) {
    modalState.champion = champ;
    modalState.patch = meta.patch_version;
    modalState.currentStyle = meta.build_style || 'Recommended';
    modalState.meta = meta;
    modalState.styles = [];

    const modal = document.getElementById('meta-modal');
    modal.hidden = false;
    renderMetaModal();

    const key = encodeURIComponent(champ.key);
    try {
        const res = await fetch(`/api/arena/meta/${key}/styles?patch=${encodeURIComponent(meta.patch_version)}`);
        if (res.ok) {
            modalState.styles = await res.json();
            renderMetaModal();
        }
    } catch (err) { /* pipeline unavailable; keep default */ }
}

async function changeStyle(style) {
    modalState.currentStyle = style;
    const menu = document.getElementById('style-menu');
    if (menu) menu.hidden = true;
    renderMetaModal();
    const key = encodeURIComponent(modalState.champion.key);
    const patch = encodeURIComponent(modalState.patch);
    try {
        const res = await fetch(`/api/arena/meta/${key}?patch=${patch}&build_style=${encodeURIComponent(style)}`);
        if (res.ok) {
            modalState.meta = await res.json();
        } else {
            modalState.meta = emptyMeta(style);
        }
    } catch (err) {
        modalState.meta = emptyMeta(style);
    }
    renderMetaModal();
}

function emptyMeta(style) {
    return {
        champion_id: modalState.champion ? modalState.champion.key : 0,
        champion_name: modalState.champion ? modalState.champion.name : '',
        patch_version: modalState.patch,
        build_style: style,
        total_games: 0, win_count: 0, top4_count: 0, win_rate: 0, top4_rate: 0,
        avg_placement: 0, tier_rank: '-', skill_priority: '', skill_progression: null,
        skill_order_distribution: [], augments_overall: [], augments_silver: [],
        augments_gold: [], augments_prismatic: [], boots: [], prismatic_items: [],
        round_items: {}, elixirs: [], build_styles: [], partner_synergies: []
    };
}

function closeMetaModal() {
    const modal = document.getElementById('meta-modal');
    if (modal) modal.hidden = true;
}

function tierClass(tier) {
    return 'tier-' + String(tier || '').replace('+', 'plus');
}

function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

function pct(v) {
    return `${Math.round((v || 0) * 100)}%`;
}

function iconImg(url, name, rarity) {
    const rar = rarity ? `rarity-${rarity}` : '';
    const inner = url
        ? `<img class="icon-img" src="${esc(url)}" alt="${esc(name || '')}" loading="lazy">`
        : `<div class="icon-ph">${esc((name || '?').charAt(0))}</div>`;
    return `<div class="icon-avatar ${rar}">${inner}</div>`;
}

function colorSkillLetters(str) {
    return String(str || '').replace(/[QWER]/g, (m) => (
        `<span class="skill-letter skill-${m}">${m}</span>`
    ));
}

function iconCard(entry, opts) {
    const name = entry.name || `#${entry[opts.idKey]}`;
    const tierVal = opts.showTier ? (entry.performance_tier || entry.tier) : null;
    const tipData = JSON.stringify({
        name: name,
        rarity: entry.tier || '',
        tier: tierVal || '',
        desc: entry.description || '',
        descHtml: entry.desc_html || '',
        price: entry.price || 0,
        icon: entry.icon || ''
    });
    const parts = [];
    if (opts.showPick && entry.pick_rate != null) parts.push(`Pick ${pct(entry.pick_rate)}`);
    if (opts.showGames && entry.count != null) {
        parts.push(`${entry.count} game${entry.count === 1 ? '' : 's'}`);
    }
    return `<div class="icon-card" data-tip="${esc(tipData)}">
        ${iconImg(entry.icon, name, entry.tier)}
        <div class="icon-name">${esc(name)}</div>
        ${tierVal ? `<div class="icon-tier ${tierClass(tierVal)}">${esc(tierVal)}</div>` : ''}
        ${parts.length ? `<div class="icon-meta">${parts.join(' · ')}</div>` : ''}
    </div>`;
}

function iconStrip(entries, opts) {
    if (!entries || entries.length === 0) return '<span class="meta-empty">No data</span>';
    const cards = entries.slice(0, opts.limit || 10).map((e) => iconCard(e, opts)).join('');
    return `<div class="icon-grid">${cards}</div>`;
}

function iconStripWithMore(entries, opts, max = 5) {
    if (!entries || entries.length === 0) return '<span class="meta-empty">No data</span>';
    const visible = entries.slice(0, max);
    const hidden = entries.slice(max);
    let html = `<div class="icon-wrap"><div class="icon-grid">${visible.map((e) => iconCard(e, opts)).join('')}</div>`;
    if (hidden.length) {
        html += `<div class="aug-hidden" hidden><div class="icon-grid">${hidden.map((e) => iconCard(e, opts)).join('')}</div></div>`;
        html += `<button type="button" class="aug-more" data-more="Show more (+${hidden.length})" onclick="toggleAugments(this)">Show more (+${hidden.length})</button>`;
    }
    html += '</div>';
    return html;
}

function metaSection(title, content, collapsed = false) {
    return `<div class="meta-section${collapsed ? ' collapsed' : ''}">
        <button type="button" class="meta-section-header" onclick="toggleSection(this)">
            <h3>${esc(title)}</h3>
            <span class="toggle-arrow">&#9662;</span>
        </button>
        <div class="meta-section-body">${content}</div>
    </div>`;
}

function toggleSection(btn) {
    const section = btn.closest('.meta-section');
    if (section) section.classList.toggle('collapsed');
}

function toggleAugments(btn) {
    const hidden = btn.closest('.icon-wrap').querySelector('.aug-hidden');
    if (!hidden) return;
    const expand = hidden.hidden;
    hidden.hidden = !expand;
    btn.textContent = expand ? 'Show less' : btn.getAttribute('data-more');
}

function setupTooltip() {
    const tooltip = document.getElementById('meta-tooltip');
    if (!tooltip) return;
    document.addEventListener('mouseover', (e) => {
        const el = e.target.closest('[data-tip]');
        if (!el) return;
        let data;
        try { data = JSON.parse(el.getAttribute('data-tip')); } catch (err) { return; }
        tooltip.innerHTML = renderTooltip(data);
        tooltip.hidden = false;
        positionTooltip(tooltip, el);
    });
    document.addEventListener('mouseout', (e) => {
        const el = e.target.closest('[data-tip]');
        if (!el) return;
        tooltip.hidden = true;
    });
}

const RICH_TAG_CLASS = {
    stats: 'kw-stats',
    attention: 'kw-attention',
    passive: 'kw-passive',
    keyword: 'kw-keyword',
    magicdamage: 'kw-magic',
    physicaldamage: 'kw-physical',
    truedamage: 'kw-true',
    healing: 'kw-heal',
    shield: 'kw-shield',
    speed: 'kw-speed',
    scaleap: 'kw-ap',
    scalead: 'kw-ad',
    scalehealth: 'kw-health',
    scaleas: 'kw-as',
    scalecrit: 'kw-crit',
    scalemana: 'kw-mana',
    scalemr: 'kw-mr',
    scalearmor: 'kw-armor',
    spellname: 'kw-passive',
    spellmodifier: 'kw-keyword',
    status: 'kw-keyword'
};

function richDesc(html) {
    if (!html) return '';
    let s = String(html).replace(/<\/?mainText>/gi, '');
    s = s.replace(/@[\w]+@/g, '…');
    s = s.replace(/<(\/?)([a-zA-Z][\w]*)[^>]*>/g, (m, close, tag) => {
        const t = tag.toLowerCase();
        if (t === 'br') return '<br>';
        if (t === 'li') return close ? '' : '<br>• ';
        let cls;
        if (RICH_TAG_CLASS[t]) cls = RICH_TAG_CLASS[t];
        else if (t.startsWith('scale')) cls = 'kw-keyword';
        else cls = 'kw-' + t;
        return close ? '</span>' : `<span class="${cls}">`;
    });
    s = s.replace(/(<br>\s*){2,}/g, '<br>');
    return `<div class="tt-desc rich">${s}</div>`;
}

function renderTooltip(data) {
    const rar = data.rarity ? `rarity-${esc(data.rarity)}` : '';
    const icon = data.icon
        ? `<div class="icon-avatar ${rar}"><img class="icon-img" src="${esc(data.icon)}" alt=""></div>`
        : '';
    const price = data.price
        ? `<div class="tt-price"><span class="gold-dot"></span>${data.price}</div>`
        : '';
    let body = '';
    if (data.descHtml) {
        body = richDesc(data.descHtml);
    } else if (data.desc) {
        const plain = String(data.desc).replace(/@\w+@/g, '…').trim();
        body = `<div class="tt-desc">${esc(plain)}</div>`;
    }
    return `
        <div class="tt-head">
            ${icon}
            <div class="tt-headtext">
                <div class="tt-name">${esc(data.name)}</div>
                ${price}
                ${data.tier ? `<div class="tt-tier">Tier: ${esc(data.tier)}</div>` : ''}
            </div>
        </div>
        ${body}
    `;
}

function positionTooltip(tooltip, el) {
    const rect = el.getBoundingClientRect();
    tooltip.style.left = '0px';
    tooltip.style.top = '0px';
    const tw = tooltip.offsetWidth;
    const th = tooltip.offsetHeight;
    let left = rect.left + rect.width / 2 - tw / 2;
    let top = rect.top - th - 10;
    if (top < 8) top = rect.bottom + 10;
    left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
    tooltip.style.left = Math.round(left) + 'px';
    tooltip.style.top = Math.round(top) + 'px';
}

function renderMetaModal() {
    const content = document.getElementById('meta-modal-content');
    const champ = modalState.champion;
    const meta = modalState.meta;
    if (!content || !champ || !meta) return;

    const tier = meta.tier_rank || '-';
    const styleCounts = {};
    const styleIcons = {};
    for (const s of modalState.styles) {
        styleCounts[s.build_style] = s.total_games;
        styleIcons[s.build_style] = s.icon || '';
    }
    // Prefer the champion's own item icon for a style, fall back to the archetype icon.
    const iconFor = (style) => styleIcons[style] || styleIcon(style);

    const styleNames = buildStyleList.length
        ? buildStyleList.map((s) => s.build_style)
        : BUILD_STYLES;
    const currentIcon = iconFor(modalState.currentStyle);
    const options = styleNames.map((s) => {
        const count = styleCounts[s] != null ? styleCounts[s] : 0;
        const active = s === modalState.currentStyle ? ' active' : '';
        return `<button type="button" class="style-option${active}" onclick="changeStyle('${esc(s)}')">
            ${iconImg(iconFor(s), s)}
            <span class="style-option-name">${esc(s)}</span>
            ${count > 0 ? `<span class="style-option-count">${count}</span>` : ''}
        </button>`;
    }).join('');

    const augSection = (title, entries) => {
        if (!entries || entries.length === 0) return '';
        return `<div class="meta-subsection"><h4>${title}</h4>${iconStripWithMore(entries, { idKey: 'augment_id', showPick: true, showTier: true }, 5)}</div>`;
    };

    const roundKeys = ['1', '2', '4', '6', '9', '11'];
    const roundItems = meta.round_items || {};
    const bestPrismatic = (meta.prismatic_items && meta.prismatic_items.length) ? meta.prismatic_items[0] : null;

    const roundRows = roundKeys
        .filter((r) => (roundItems[r] && roundItems[r].length) || (r === '2' && bestPrismatic))
        .map((r) => {
            let items = roundItems[r] || [];
            if (r === '2' && bestPrismatic && !items.some((it) => it.item_id === bestPrismatic.item_id)) {
                items = [bestPrismatic, ...items];
            }
            return `<div class="round-row"><div class="round-label">Round ${r}</div>${iconStripWithMore(items, { idKey: 'item_id', showPick: true, showTier: true }, 5)}</div>`;
        }).join('');

    const fullBuild = meta.full_build || [];
    const fullBuildRow = fullBuild.length
        ? iconStrip(fullBuild, { idKey: 'item_id', showPick: true, limit: 6 })
        : '<span class="meta-empty">No data</span>';

    const partners = (meta.partner_synergies || []).slice(0, 6).map((p) => (
        `<span class="meta-item-chip">${esc(p.champion_name || ('#' + p.champion_id))} <span class="rate">${p.games}G / ${pct(p.win_rate)}</span></span>`
    )).join('') || '<span class="meta-empty">No data</span>';

    const skillDist = (meta.skill_order_distribution || []).slice(0, 5).map((d) => (
        `<span class="meta-pill"><span class="rate">${pct(d.pick_rate)}</span> ${esc(d.order)}</span>`
    )).join('');

    const hasAugments = meta.augments_overall && meta.augments_overall.length > 0;

    content.innerHTML = `
        <div class="meta-modal-header">
            <span class="meta-tier-badge ${tierClass(tier)}">${esc(tier)}</span>
            <h2 id="meta-modal-title">${esc(champ.name)}</h2>
        </div>

        <label class="style-label">Build Type</label>
        <div class="style-dropdown">
            <button type="button" class="style-btn" onclick="toggleStyleMenu(event)">
                ${iconImg(currentIcon, modalState.currentStyle)}
                <span class="style-btn-name">${esc(modalState.currentStyle)}</span>
                <span class="caret">&#9662;</span>
            </button>
            <div class="style-menu" id="style-menu" hidden>${options}</div>
        </div>

        <div class="meta-stats">
            <div class="meta-stat"><div class="value">${meta.total_games ?? 0}</div><div class="label">Games</div></div>
            <div class="meta-stat"><div class="value">${pct(meta.win_rate)}</div><div class="label">Win Rate</div></div>
            <div class="meta-stat"><div class="value">${pct(meta.top4_rate)}</div><div class="label">Top 4</div></div>
            <div class="meta-stat"><div class="value">${meta.avg_placement ?? '-'}</div><div class="label">Avg Place</div></div>
        </div>

        ${metaSection('Skill Order', `
            <div class="meta-tagline">
                <span class="meta-pill big">${colorSkillLetters(esc(meta.skill_priority || '-'))}</span>
                ${skillDist}
            </div>
            ${renderSkillMatrix(meta.skill_progression)}
        `)}

        <div class="meta-columns">
            <div class="meta-col">
                ${metaSection('Augments', hasAugments
                    ? `${augSection('Overall', meta.augments_overall)}
                       ${augSection('Silver', meta.augments_silver)}
                       ${augSection('Gold', meta.augments_gold)}
                       ${augSection('Prismatic', meta.augments_prismatic)}`
                    : '<span class="meta-empty">No data</span>')}
            </div>
            <div class="meta-col">
                ${metaSection('Boots', iconStripWithMore(meta.boots, { idKey: 'item_id', showPick: true, showTier: true }, 5))}
                ${metaSection('Full Build', fullBuildRow)}
                ${metaSection('Items by Round', roundRows || '<span class="meta-empty">No data</span>', true)}
            </div>
        </div>

        ${metaSection('Best Prismatic Items', iconStrip(meta.prismatic_items, { idKey: 'item_id', showPick: true, showTier: true, limit: 8 }))}

        ${metaSection('Late-Game Elixirs', iconStrip(meta.elixirs, { idKey: 'item_id', showPick: true, showTier: true, limit: 6 }))}

        ${metaSection('Best Partners', `<div class="meta-item-list">${partners}</div>`)}
    `;
}

function renderSkillMatrix(progression) {
    if (!progression) return '<span class="meta-empty">No data</span>';
    const letters = progression.split('').slice(0, 17);
    let html = '<div class="meta-skill-grid">';
    html += '<div class="meta-skill-cell head">Lv</div>';
    for (let i = 1; i <= 18; i++) html += `<div class="meta-skill-cell head">${i}</div>`;
    html += '</div><div class="meta-skill-grid">';
    html += '<div class="meta-skill-cell head">Skill</div>';
    html += '<div class="meta-skill-cell">-</div>';
    for (let i = 0; i < 17; i++) {
        const letter = letters[i] || '';
        html += `<div class="meta-skill-cell skill-${esc(letter)}">${esc(letter)}</div>`;
    }
    html += '</div>';
    return html;
}
