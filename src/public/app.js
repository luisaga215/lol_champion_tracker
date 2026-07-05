// Global State
let champions = [];
let stats = { total: 0, played: 0, top4: 0, won: 0 };
let searchQuery = '';
let currentFilter = 'all';
let currentSort = 'name-asc';

// DOM Elements
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search');
const filterButtons = document.querySelectorAll('.filter-btn');
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
    fetchData();
});

// Setup Event Listeners
function setupEventListeners() {
    // Search input
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        clearSearchBtn.style.display = searchQuery ? 'flex' : 'none';
        renderGrid();
    });

    // Clear search
    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        searchQuery = '';
        clearSearchBtn.style.display = 'none';
        searchInput.focus();
        renderGrid();
    });

    // Filter buttons
    filterButtons.forEach((btn) => {
        btn.addEventListener('click', (e) => {
            filterButtons.forEach((b) => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.getAttribute('data-filter');
            renderGrid();
        });
    });

    // Sort select
    sortSelect.addEventListener('change', (e) => {
        currentSort = e.target.value;
        renderGrid();
    });
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

        // Hide loading state
        if (loadingState) {
            loadingState.style.display = 'none';
        }

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

        // Portrait Container
        const portraitCont = document.createElement('div');
        portraitCont.className = 'portrait-container';
        
        const img = document.createElement('img');
        img.src = `/images/champion/${champ.image_name}`;
        img.alt = champ.name;
        img.loading = 'lazy';
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
