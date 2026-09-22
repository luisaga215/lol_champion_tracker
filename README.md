# League of Legends: Arena Champion Tracker

A sleek, interactive web application designed to help you track your progress towards completing all champions in the League of Legends Arena mode. 

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)
![Node.js](https://img.shields.io/badge/node.js-6DA55F?style=flat&logo=node.js&logoColor=white)

---

## ✨ Features

- **3-Tier Status Tracking:** Track your progress for each champion across three tiers: **Played**, **Top 4**, and **1st Place Win**.
- **Smart Status Toggles:** The UI handles hierarchical logic automatically. Marking a champion as a "Win" automatically toggles "Top 4" and "Played".
- **Premium Arena UI:** Enjoy a dark-themed, responsive design inspired by the Hextech/Arena aesthetic, featuring neon accents, hover animations, and dynamic state styling.
- **Dynamic Filtering & Search:** Easily sort by alphabetical order or progress, filter by class roles (Assassin, Mage, Tank, etc.), and quickly search for specific champions.
- **MetaSrc Integration:** Click on any champion portrait to instantly open their recommended Arena builds on MetaSrc.
- **Automated Updates:** The app automatically fetches the latest champions from Riot's Data Dragon API on startup, ensuring you're always up to date.

---

## 🚀 Quick Start (Docker)

The easiest way to run the application is using Docker. This ensures you don't need to install Node.js or configure a database locally.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/lol-arena-tracker.git
   cd lol-arena-tracker
   ```

2. **Start the application:**
   If you are on Windows, simply double-click the `run_arena_tracker.bat` file.
   
   Otherwise, open your terminal and run:
   ```bash
   docker compose up -d --build
   ```

3. **Open the App:**
   Navigate to [http://localhost:3000](http://localhost:3000) in your web browser. 
   *(Note: The very first startup may take 10-15 seconds to automatically download all champion portraits).*

---

## 💻 Local Development

If you'd prefer to run the application natively without Docker, follow these steps:

### Prerequisites
- [Node.js](https://nodejs.org/) (v18 or higher)
- npm

### Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📁 Project Structure

- `src/public/` - Static frontend files (HTML, CSS, Vanilla JS)
- `src/server.js` - Express backend API server
- `src/init_db.js` - SQLite database initialization and Riot Data Dragon sync
- `docker-compose.yml` - Docker configuration with persistent data volumes

---

## 📝 License

This project is licensed under the MIT License.

*Disclaimer: This project is not affiliated with Riot Games. League of Legends champion data and images are property of Riot Games.*
