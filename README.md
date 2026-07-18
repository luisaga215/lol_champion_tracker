# LoL Arena Champion Tracker

Bilingual interactive web application to track played, Top 4, and Won champions in League of Legends' Arena mode.

---

### Features
- **3-Tier Status Tracking:** Check **P (Played)**, **T (Top 4)**, and **W (Won)** for each champion.
- **Hierarchical Game Logic:** Toggling a status automatically propagates values to maintain consistency (e.g. marking **Won** automatically enables **Top 4** and **Played**; unchecking **Played** resets all).
- **Premium Arena UI:** Designed with custom dark themes, neon glow accents, hover scaling, and full-color transitions.
- **Winner Highlights:** Winning first place (Won) highlights the champion card with a golden outline, pulsing outer glow, a mini crown overlay, and an amber background gradient.
- **Dynamic Search & Filtering:** Filter by completion status (Not Played, Played, Top 4, Won, Need Top 4, Need Won) and search in real-time.
- **Offline Cache:** Automatically syncs champion lists and downloads icons on the first start, caching them locally inside Docker volumes for persistent storage.

### Folder Structure
- `src/` - Application source code
  - `public/` - Static frontend files (`index.html`, `index.css`, `app.js`)
  - `server.js` - Express backend API server
  - `init_db.js` - SQLite and Riot Data Dragon database seeding/asset downloader
  - `server.test.js` - Backend Jest unit tests
- `data/` - Git-ignored local database and image cache directory
- `Dockerfile` & `docker-compose.yml` - Docker environment definitions
- `run_arena_tracker.bat` - One-click starter script for Windows users

### Getting Started (Docker Compose)
1. Ensure **Docker Desktop** is installed and running.
2. Double-click **`run_arena_tracker.bat`** (on Windows) or run the command:
   ```bash
   docker compose up -d --build
   ```
3. Open your browser to `http://localhost:3000`. The first start will automatically download champion portraits (approx. 10-15 seconds).
