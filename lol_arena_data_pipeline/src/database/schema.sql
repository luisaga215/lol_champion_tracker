-- League of Legends Arena data pipeline schema.
-- The core tables below match the specification; supplementary tables support the
-- crawler frontier, timeline item purchases, and CommunityDragon reference data.

CREATE TABLE IF NOT EXISTS raw_matches (
    match_id TEXT PRIMARY KEY,
    game_version TEXT NOT NULL,
    patch_minor TEXT NOT NULL,  -- e.g., "26.21"
    game_duration INTEGER,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS arena_participant_stats (
    match_id TEXT,
    puuid TEXT,
    champion_id INTEGER,
    champion_name TEXT,
    patch_minor TEXT NOT NULL,
    placement INTEGER,
    subteam_placement INTEGER,
    team_id INTEGER,
    partner_champion_id INTEGER,
    item0 INTEGER, item1 INTEGER, item2 INTEGER,
    item3 INTEGER, item4 INTEGER, item5 INTEGER, item6 INTEGER,
    player_augment1 INTEGER, player_augment2 INTEGER,
    player_augment3 INTEGER, player_augment4 INTEGER,
    skill_order_str TEXT,
    skill_progression TEXT,
    PRIMARY KEY (match_id, puuid)
);

CREATE TABLE IF NOT EXISTS champion_arena_meta (
    champion_id INTEGER,
    patch_version TEXT,
    build_style TEXT NOT NULL DEFAULT 'Recommended',
    champion_name TEXT,
    total_games INTEGER,
    win_count INTEGER,
    top4_count INTEGER,
    win_rate REAL,
    top4_rate REAL,
    avg_placement REAL,
    tier_rank TEXT,          -- S+, S, A, B, C based on tier score formula
    skill_priority TEXT,     -- e.g., "Q > W > E"
    skill_order_distribution_json TEXT,
    skill_progression TEXT,

    -- Structured JSON payloads for UI Modal
    augments_overall_json TEXT,
    augments_silver_json TEXT,
    augments_gold_json TEXT,
    augments_prismatic_json TEXT,
    boots_json TEXT,
    prismatic_items_json TEXT,
    round_items_json TEXT,
    elixirs_json TEXT,
    build_styles_json TEXT,
    partner_synergies_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (champion_id, patch_version, build_style)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_participant_patch ON arena_participant_stats(patch_minor, champion_id);
CREATE INDEX IF NOT EXISTS idx_raw_patch ON raw_matches(patch_minor);
CREATE INDEX IF NOT EXISTS idx_meta_patch_build ON champion_arena_meta(patch_version, build_style);

-- Supplementary table: crawler frontier (PUUIDs awaiting match-history expansion).
CREATE TABLE IF NOT EXISTS crawl_queue (
    puuid TEXT NOT NULL,
    queue_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TIMESTAMP,
    PRIMARY KEY (puuid, queue_id)
);

CREATE INDEX IF NOT EXISTS idx_crawl_queue_status ON crawl_queue(status);

-- Supplementary table: timeline-derived item purchases keyed to Arena shop rounds.
CREATE TABLE IF NOT EXISTS arena_item_purchases (
    match_id TEXT NOT NULL,
    puuid TEXT NOT NULL,
    patch_minor TEXT NOT NULL,
    champion_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    round_number INTEGER,
    timestamp INTEGER NOT NULL,
    PRIMARY KEY (match_id, puuid, item_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_item_purchases_champion_patch ON arena_item_purchases(patch_minor, champion_id);

-- Reference data cache: CommunityDragon items + augments.
CREATE TABLE IF NOT EXISTS reference_items (
    item_id INTEGER PRIMARY KEY,
    name TEXT,
    categories TEXT,
    description TEXT,
    icon TEXT,
    price INTEGER
);

CREATE TABLE IF NOT EXISTS reference_augments (
    augment_id INTEGER PRIMARY KEY,
    name TEXT,
    rarity INTEGER,
    description TEXT,
    icon TEXT
);

CREATE TABLE IF NOT EXISTS reference_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
