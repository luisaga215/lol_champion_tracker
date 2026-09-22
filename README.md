# LoL Arena Champion Tracker

A fast, interactive web dashboard to track your completion progress in League of Legends Arena mode. 

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg) ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)

## ✨ Features
- **3-Tier Tracking:** Easily log champions as **Played**, **Top 4**, or **1st Place**.
- **Smart UI:** Hextech-inspired dark mode aesthetic. Toggling a "Win" automatically cascades to "Top 4" and "Played".
- **Dynamic Filters:** Filter your roster by class (Assassin, Tank, etc.), missing completions, or sort alphabetically/by progress.
- **MetaSrc Integration:** Click a champion portrait to instantly open their latest Arena builds.
- **Always Updated:** Auto-syncs with Riot's Data Dragon API on startup so new champions are instantly available.

## 🚀 Quick Start (Docker)
Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.

1. **Clone & Start:**
   ```bash
   git clone https://github.com/your-username/lol_champion_tracker.git
   cd lol_champion_tracker
   docker compose up -d --build
   ```
   *Windows users: Just double-click `run_arena_tracker.bat`.*

2. **Play:** 
   Open [http://localhost:3000](http://localhost:3000) in your browser.

## 💻 Local Development
If you prefer running without Docker:
```bash
npm install
npm start
```
*Requires Node.js (v18+).*

## 📝 Disclaimer
This project is licensed under MIT and is not affiliated with Riot Games. Champion data and imagery belong to Riot Games.
