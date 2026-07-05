# Rastreador de Campeones de League of Legends (Modo Arena)

Esta aplicación web te permite registrar con qué campeones has jugado, cuáles han quedado en el Top 4 y con cuáles has ganado el primer lugar (1.º) en el modo de juego Arena de League of Legends.

---

## Instrucciones de Instalación Rápida

### Paso 1: Instalar y Abrir Docker Desktop (Solo la primera vez)
Si no tienes Docker instalado en tu computadora:
1. Descarga e instala **Docker Desktop para Windows** desde aquí:
   [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Abre la aplicación **Docker Desktop** desde el menú de inicio de Windows.
3. Asegúrate de que el icono en la esquina inferior izquierda de Docker esté de color **verde** (indica que está activo y corriendo).

### Paso 2: Ejecutar el Rastreador
1. Extrae los archivos de este archivo comprimido en cualquier carpeta de tu computadora.
2. Haz doble clic en el archivo **`run_arena_tracker.bat`**.

¡Eso es todo! La consola abrirá Docker, descargará automáticamente la lista de campeones e imágenes actualizadas del juego (tomará unos 10-15 segundos en la primera ejecución) y **abrirá automáticamente tu navegador** en:
👉 **[http://localhost:3000](http://localhost:3000)**

---

## Cómo Funciona la Aplicación

- **Barra de 3 Estados (P, T, W):**
  - **P (Played / Jugado):** Haz clic para marcar si jugaste con el personaje (color bronce).
  - **T (Top 4):** Haz clic para marcar si quedaste en los mejores 4 lugares (color platino/azul). Al marcarlo, se marcará automáticamente "Jugado".
  - **W (Won / Ganado 1.º):** Haz clic para marcar si ganaste el 1.º lugar (color oro/rosa). Al marcarlo, se marcarán automáticamente "Jugado" y "Top 4".
- **Resaltado de Victoria (Campeón Ganador):** Cuando logras el 1.º lugar con un campeón, su tarjeta se resalta con un borde dorado brillante, un efecto de pulsación y una corona dorada sobre su retrato.
- **Buscador y Filtros:** Puedes escribir el nombre del campeón para encontrarlo al instante o usar los botones de filtrado (ej. *Falta Top 4*, *Falta Ganar*) para ver rápidamente tus tareas pendientes.

---

## Guardado de Datos
Tus datos y las imágenes de los campeones se guardan de forma local y persistente en tu computadora dentro del volumen de Docker (`lol-arena-data`). Esto significa que aunque cierres o actualices la aplicación, no perderás tu progreso.

## Cómo Cerrar la Aplicación
Para apagar la aplicación cuando termines de jugar:
1. Abre Docker Desktop y haz clic en el botón de "Detener" (Stop) al lado del contenedor `lol-arena-tracker`.
2. O bien, abre una consola en esta carpeta y ejecuta:
   ```bash
   docker compose down
   ```
