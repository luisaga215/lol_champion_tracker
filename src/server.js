const express = require('express');
const path = require('path');
const fs = require('fs');
const { initDatabase } = require('./init_db');

const app = express();
app.use(express.json());

// Set up paths
// DATA_DIR is relative to the root when run locally (one level up from src/)
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, '..', 'data');
const DB_PATH = path.join(DATA_DIR, 'arena_tracker.db');
const IMAGES_DIR = path.join(DATA_DIR, 'images', 'champion');
const PORT = process.env.PORT || 3000;

let db;

// Serve static assets
app.use(express.static(path.join(__dirname, 'public')));
app.use('/images/champion', express.static(IMAGES_DIR));

// Get all champions
app.get('/api/champions', (req, res) => {
  if (!db) {
    return res.status(503).json({ error: 'Database is initializing' });
  }

  db.all('SELECT * FROM champions ORDER BY name ASC', (err, rows) => {
    if (err) {
      console.error('[API] Error fetching champions:', err);
      return res.status(500).json({ error: 'Database error' });
    }
    res.json(rows);
  });
});

// Get overall stats
app.get('/api/stats', (req, res) => {
  if (!db) {
    return res.status(503).json({ error: 'Database is initializing' });
  }

  const queries = {
    total: 'SELECT COUNT(*) as count FROM champions',
    played: 'SELECT COUNT(*) as count FROM champions WHERE played = 1',
    top4: 'SELECT COUNT(*) as count FROM champions WHERE top4 = 1',
    won: 'SELECT COUNT(*) as count FROM champions WHERE won = 1'
  };

  const stats = {};
  const keys = Object.keys(queries);
  let completed = 0;
  let hasError = false;

  keys.forEach((key) => {
    db.get(queries[key], (err, row) => {
      if (hasError) return;
      if (err) {
        hasError = true;
        console.error(`[API] Error fetching stat ${key}:`, err);
        return res.status(500).json({ error: 'Database error' });
      }
      stats[key] = row ? row.count : 0;
      completed++;

      if (completed === keys.length) {
        res.json(stats);
      }
    });
  });
});

// Update champion status
app.post('/api/champions/:id/status', (req, res) => {
  if (!db) {
    return res.status(503).json({ error: 'Database is initializing' });
  }

  const championId = req.params.id;
  let { played, top4, won } = req.body;

  // Convert inputs to integers (0 or 1) and sanitize
  played = played ? 1 : 0;
  top4 = top4 ? 1 : 0;
  won = won ? 1 : 0;

  // Get current champion state to determine what changed
  db.get('SELECT played, top4, won FROM champions WHERE id = ?', [championId], (err, current) => {
    if (err) {
      console.error(`[API] Error fetching champion ${championId}:`, err);
      return res.status(500).json({ error: 'Database error' });
    }

    if (!current) {
      return res.status(404).json({ error: 'Champion not found' });
    }

    let newPlayed = played;
    let newTop4 = top4;
    let newWon = won;

    // Detect which field was toggled and enforce hierarchical logic
    if (won !== current.won) {
      // Won was toggled
      if (won === 1) {
        newPlayed = 1;
        newTop4 = 1;
        newWon = 1;
      } else {
        newWon = 0;
      }
    } else if (top4 !== current.top4) {
      // Top 4 was toggled
      if (top4 === 1) {
        newPlayed = 1;
        newTop4 = 1;
      } else {
        newTop4 = 0;
        newWon = 0;
      }
    } else if (played !== current.played) {
      // Played was toggled
      if (played === 1) {
        newPlayed = 1;
      } else {
        newPlayed = 0;
        newTop4 = 0;
        newWon = 0;
      }
    } else {
      // If no change is detected (or multiple fields changed, fallback to standard hierarchy)
      if (newWon === 1) {
        newTop4 = 1;
        newPlayed = 1;
      }
      if (newTop4 === 1) {
        newPlayed = 1;
      }
      if (newPlayed === 0) {
        newTop4 = 0;
        newWon = 0;
      }
      if (newTop4 === 0) {
        newWon = 0;
      }
    }

    // Update in database
    db.run(
      'UPDATE champions SET played = ?, top4 = ?, won = ? WHERE id = ?',
      [newPlayed, newTop4, newWon, championId],
      function (err) {
        if (err) {
          console.error(`[API] Error updating champion ${championId}:`, err);
          return res.status(500).json({ error: 'Database error' });
        }

        // Return updated champion
        db.get('SELECT * FROM champions WHERE id = ?', [championId], (err, row) => {
          if (err) {
            return res.status(500).json({ error: 'Database error fetching updated champion' });
          }
          res.json(row);
        });
      }
    );
  });
});

// Helper database setter for testing
app.setDb = (databaseInstance) => {
  db = databaseInstance;
};

// Initialize database and start listening (only if run directly, not in tests)
if (require.main === module) {
  (async () => {
    try {
      console.log('[Server] Initializing database and syncing assets...');
      db = await initDatabase(DB_PATH, IMAGES_DIR);
      console.log('[Server] Database initialization completed.');
      
      app.listen(PORT, '0.0.0.0', () => {
        console.log(`[Server] Web application running at http://localhost:${PORT}`);
      });
    } catch (err) {
      console.error('[Server] Critical initialization failure:', err);
      process.exit(1);
    }
  })();
}

module.exports = app;
