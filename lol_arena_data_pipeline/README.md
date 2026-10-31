# LoL Arena Data Pipeline & Microservice API

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=flat&logo=sqlite&logoColor=white)

A production-grade Python (**FastAPI**) microservice that **ingests, aggregates, and
serves League of Legends Arena meta statistics** to the main `lol_champion_tracker`
Node.js app over Docker networking.

It crawls real Arena matches through the Riot match-v5 API, parses timelines
(item purchases, skill level-ups), classifies every build into a playstyle
archetype, enriches everything with CommunityDragon reference data (item/augment
names, icons, rarity tiers), and exposes it as a clean REST API.

---

## 📖 About The Project

The champion tracker answers *"which champions have I played?"*. This pipeline
answers *"how should I build each champion in Arena right now?"* — automatically,
from real data instead of hand-maintained spreadsheets.

It runs as an independent service so the Node app stays simple: the pipeline owns
all the heavy lifting (Riot API crawling, rate limiting, timeline parsing,
aggregation, CommunityDragon enrichment), and the tracker just proxies and renders
the already-computed JSON.

The two services are wired together with `docker compose`; the Node app reaches the
pipeline at `http://arena-pipeline:8000` on the shared Docker network.

---

## ✨ Key Features

- **Recursive Arena Crawler:** Breadth-first crawl of Arena match histories
  (rooms `1700` *Standard Arena* and `1710` *16-player customs*). Every newly
  discovered participant PUUID is automatically queued, so the dataset expands
  continuously from a small set of seeds.
- **Strict Rate Limiting:** Async token-bucket limiter enforcing Riot's
  `20 req / 1 s` and `100 req / 2 min` limits, with `Retry-After`-aware `429`
  handling and exponential backoff + jitter.
- **Timeline Parsing:** Reconstructs item purchases per Arena shop round
  (**1, 2, 4, 6, 9, 11**), skill-max priority (`Q > W > E`), and the full
  level-by-level skill progression.
- **Build-Style Archetypes:** Every game is classified into one of
  `Recommended, AD, Crit, MS, CDR, HP, On-Hit, Lethality, MR, AP, AR, LS, Mana, SV`
  from its item categories, and meta is aggregated **per champion, per patch, per
  build style**.
- **CommunityDragon Enrichment:** Item and augment names, descriptions, icons and
  rarity (Silver / Gold / Prismatic) are pulled from CommunityDragon and cached, so
  every panel is fully visual.
- **Rich Meta Panels:** Win rate, Top-4 rate, average placement, tier (`S+ … C`),
  augments (overall + by rarity, with per-augment performance tiers), boots, items
  by round, prismatic items, late-game elixirs, core build combos, and partner
  synergies — all as structured JSON.
- **Background Scheduler:** An in-process crawl → aggregate loop (`SCHEDULER_ENABLED`)
  keeps data fresh while the container is running.
- **On-Demand Seeding:** `POST /api/arena/crawl/seed` enqueues PUUIDs so you can
  bootstrap or steer the crawl at runtime.
- **Patch Isolation:** Data is isolated per major/minor patch
  (e.g. `16.21`) so aggregation never mixes meta across patches.
- **Persistent Storage:** SQLite in WAL mode, mounted as a Docker volume, so data
  survives restarts.

---

## 🏗️ Architecture

```
Browser ──► Node tracker (:3000) ──proxy /api/arena/*──► Pipeline (:8000)
                                                            │
                                            ┌───────────────┼────────────────┐
                                            ▼               ▼                ▼
                                      Riot match-v5   CommunityDragon     SQLite (WAL)
                                      (crawler)       (reference data)    (arena_pipeline.db)
```

```
lol_arena_data_pipeline/
├── src/
│   ├── config.py              # pydantic-settings configuration
│   ├── riot/
│   │   ├── client.py          # Async HTTP client + token-bucket rate limiter
│   │   └── models.py          # Pydantic match/timeline models
│   ├── crawler/
│   │   ├── worker.py          # Recursive BFS crawler (queues 1700 / 1710)
│   │   ├── timeline.py        # Purchases -> rounds, level-ups -> skill priority
│   │   └── __main__.py        # CLI: python -m src.crawler
│   ├── reference/
│   │   ├── data.py            # ItemRef/AugmentRef, archetypes, classification
│   │   └── loader.py          # CommunityDragon fetch + SQLite cache
│   ├── database/
│   │   ├── schema.sql         # Schema + performance indexes
│   │   ├── db.py              # Thread-safe sqlite3 wrapper (WAL, migrations)
│   │   └── repositories.py    # Repository pattern
│   ├── aggregation/
│   │   ├── aggregator.py      # Per-build-style meta computation
│   │   └── __main__.py        # CLI: python -m src.aggregation
│   ├── services/
│   │   └── pipeline.py        # Crawl + aggregate loop (scheduler)
│   └── api/
│       ├── main.py            # FastAPI app factory + lifespan
│       ├── routes.py          # REST endpoints
│       └── schemas.py         # Response models
├── tests/                     # pytest suite
├── pyproject.toml
├── requirements.txt
└── Dockerfile
```

---

## 🔁 How It Works

1. **Seed** — you provide one or more Arena PUUIDs (via `CRAWLER_SEED_PUUIDS` or the
   seed endpoint).
2. **Crawl** — for each queued PUUID the crawler fetches its Arena match ids, then
   for every unseen match fetches the match and its timeline, stores participant
   stats + timeline-derived item purchases, and enqueues newly discovered PUUIDs.
3. **Enrich** — on startup the service downloads CommunityDragon
   `items.json` + arena augment data (cached, versioned) to resolve names, icons,
   rarity, and item categories.
4. **Aggregate** — for each champion/patch it classifies each game into a build
   archetype and computes the "Recommended" (all games) plus per-archetype meta.
5. **Serve** — the FastAPI layer exposes the pre-computed meta to the Node app.

> **Note on data freshness:** which patches you see depends entirely on the seed
> PUUIDs. If your seeds stopped playing Arena in an older patch, the frontier only
> contains that patch. Seed players who are active on the current patch to collect
> current meta.

---

## 🚀 Quick Start

### Docker (recommended – runs alongside the champion tracker)

From the **repository root**:

```bash
# 1. Put your Riot key in a root .env (used by compose)
#    RIOT_API_KEY=RGAPI-...
docker compose up -d --build
```

This builds and starts both `lol-arena-tracker` (`:3000`) and `arena-pipeline`
(`:8000`). The tracker proxies `/api/arena/*` to the pipeline automatically.

Seed some Arena players:

```bash
curl -X POST http://localhost:8000/api/arena/crawl/seed \
  -H "Content-Type: application/json" \
  -d '{"puuids": ["<PUUID-1>", "<PUUID-2>"]}'
```

Or set `CRAWLER_SEED_PUUIDS=["<PUUID>", ...]` in the root `.env` before starting.

### Docker (standalone pipeline)

```bash
docker build -t arena-pipeline .
docker run --rm -p 8000:8000 -v arena-pipeline-data:/app/data \
  -e RIOT_API_KEY=RGAPI-... arena-pipeline
```

### Local (without Docker)

```bash
# 1. Configure
cp .env.example .env          # then set RIOT_API_KEY

# 2. Crawl (bounded run optional)
python -m src.crawler --seed <PUUID> [--max-matches 50] [--patch 16.21]

# 3. Aggregate
python -m src.aggregation [--patch 16.21]

# 4. Serve
python -m src.api
```

---

## ⚙️ Configuration

All settings are environment variables (or a local `.env`):

| Variable | Default | Description |
|---|---|---|
| `RIOT_API_KEY` | *(empty)* | Riot Developer API key. Required to crawl. |
| `RIOT_BASE_URL` | `https://americas.api.riotgames.com` | Regional match-v5 routing host. |
| `REQUEST_TIMEOUT` | `30` | HTTP timeout (seconds). |
| `DATABASE_PATH` | `data/arena_pipeline.db` | SQLite file location. |
| `QUEUE_IDS` | `[1700, 1710]` | Arena queues to crawl (JSON list). |
| `CRAWLER_CONCURRENCY` | `5` | Concurrent crawl workers. |
| `CRAWLER_MAX_MATCHES_PER_SEED` | `100` | Max match-history pages per seed. |
| `CRAWLER_MATCH_HISTORY_COUNT` | `100` | Match ids per page (max 100). |
| `CRAWLER_SEED_PUUIDS` | `[]` | Bootstrap PUUIDs (JSON list). |
| `SCHEDULER_ENABLED` | `false` (`true` in compose) | Run the crawl+aggregate loop in-process. |
| `CRAWLER_INTERVAL_SECONDS` | `900` | Seconds between scheduled cycles. |
| `REFERENCE_FETCH_ENABLED` | `true` | Fetch CommunityDragon reference data at startup. |
| `API_HOST` | `0.0.0.0` | API bind host. |
| `API_PORT` | `8000` | API bind port. |

---

## 🔌 API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe + Riot key status. |
| GET | `/api/arena/patches` | Available patch versions (newest first). |
| GET | `/api/arena/build-styles` | All build archetypes with representative icons. |
| GET | `/api/arena/champions?patch=` | Champions with aggregated meta. |
| GET | `/api/arena/meta?patch=&tier=&build_style=` | Champion meta list (filterable). |
| GET | `/api/arena/meta/{championId}?patch=&build_style=` | Meta for one champion (latest patch by default). |
| GET | `/api/arena/meta/{championId}/styles?patch=` | Available build styles + game counts (dropdown). |
| GET | `/api/arena/meta/{championId}/patch/{patch}?build_style=` | Meta for one champion on a specific patch. |
| POST | `/api/arena/crawl/seed` | Enqueue PUUIDs (`{"puuids": [...], "queue_ids": [...]}`). |

Example:

```bash
curl "http://localhost:8000/api/arena/meta/266?patch=16.21&build_style=AD"
```

---

## 🗃️ Data Model

| Table | Purpose |
|---|---|
| `raw_matches` | Registry of seen match ids + game version + patch. |
| `arena_participant_stats` | Per-match, per-participant stats, final items, augments, skill order + progression. |
| `arena_item_purchases` | Timeline item purchases mapped to Arena shop rounds. |
| `champion_arena_meta` | Aggregated meta keyed by **(champion, patch, build_style)** with all JSON panels. |
| `crawl_queue` | Persistent PUUID crawl frontier (`pending` / `done`). |
| `reference_items` / `reference_augments` / `reference_meta` | CommunityDragon cache (names, icons, categories, prices, augment rarity). |

---

## 🚦 Rate Limiting

The client enforces Riot's Developer API limits using two token buckets:

- **20 requests / 1 second**
- **100 requests / 2 minutes**

`HTTP 429` responses honour the `Retry-After` header, and transient server errors
are retried with exponential backoff + jitter. Requests are always authenticated
with the `X-Riot-Token` header.

---

## 🧪 Testing

```bash
pytest
```

The suite covers the rate limiter, timeline parser, aggregation, repositories, and
the HTTP layer (40+ tests). Run it from the `lol_arena_data_pipeline/` directory so
pytest picks up `pyproject.toml` (`asyncio_mode = auto`).

---

## 🛠️ Troubleshooting

- **`/api/arena/patches` returns `[]`** — nothing has been crawled/aggregated yet.
  Seed a PUUID and run `python -m src.aggregation` (or wait for the scheduler).
- **Handful of games per champion** — the crawler is limited by Riot's rate limits
  (roughly ~1,500 matches/hour) and your seed set. Add more seeds and let it run.
- **Data stuck on an old patch** — the crawl frontier descends from your seeds;
  seed players active on the current patch.
- **Names/icons missing** — CommunityDragon was unreachable at startup; the service
  degrades gracefully to ids. Restart once it is reachable (reference data is cached).
- **`429` storms** — Riot is throttling a burst; the client retries automatically but
  throughput drops. Reducing `CRAWLER_CONCURRENCY` helps.

---

## 📝 License & Disclaimer

This project is open-source and licensed under the **MIT License**.

**Disclaimer:** *This project is not affiliated with, endorsed, or sponsored by Riot
Games. League of Legends data, names, and imagery are property and trademarks of
Riot Games, Inc.*
