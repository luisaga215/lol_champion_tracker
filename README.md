# LoL Arena Champion Tracker / Rastreador de Campeones de Arena

Bilingual interactive web application to track played, Top 4, and Won champions in League of Legends' Arena mode.

Aplicación web interactiva bilingüe para rastrear los campeones jugados, Top 4 y ganados (1.º) en el modo de juego Arena de League of Legends.

---

## English Version

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

---

## Versión en Español

### Características
- **Rastreo de 3 Niveles:** Marca **P (Jugado)**, **T (Top 4)** y **W (Ganado - 1.º Lugar)** para cada campeón.
- **Lógica Jerárquica:** Al cambiar un estado, se actualizan los niveles para mantener la coherencia (ej. marcar **Ganado** activa automáticamente **Top 4** y **Jugado**; desmarcar **Jugado** los desactiva todos).
- **Interfaz Temática Arena:** Colores oscuros premium, resplandor neón, zoom dinámico y retratos a color al jugar con ellos.
- **Destacado de Campeón Ganador:** Al ganar el 1.º lugar con un campeón, su tarjeta se resalta con un contorno dorado, efecto de pulsación, un overlay de corona y fondo de gradiente cálido.
- **Buscador y Filtros Dinámicos:** Filtra por nivel (No Jugados, Jugados, Top 4, Ganados, Falta Top 4, Falta Ganar) y busca campeones por nombre al instante.
- **Persistencia Local:** Sincroniza y descarga las imágenes oficiales de Riot al primer inicio y las guarda en volumen persistente de Docker para uso offline.

### Estructura del Directorio
- `src/` - Código fuente de la aplicación
  - `public/` - Archivos estáticos del frontend (`index.html`, `index.css`, `app.js`)
  - `server.js` - Servidor backend de Express
  - `init_db.js` - Inicializador de base de datos SQLite y sincronización de retratos
  - `server.test.js` - Pruebas unitarias de Jest para el backend
- `data/` - Carpeta local omitida de Git que guarda la base de datos e imágenes
- `Dockerfile` & `docker-compose.yml` - Archivos de configuración de Docker
- `run_arena_tracker.bat` - Script iniciador de un solo clic para Windows

### Inicio Rápido (Docker Compose)
1. Asegúrate de tener **Docker Desktop** abierto y activo.
2. Haz doble clic en **`run_arena_tracker.bat`** (en Windows) o ejecuta en tu terminal:
   ```bash
   docker compose up -d --build
   ```
3. Abre tu navegador web en `http://localhost:3000`. El primer inicio descargará los retratos oficiales automáticamente (toma unos 10-15 segundos).
