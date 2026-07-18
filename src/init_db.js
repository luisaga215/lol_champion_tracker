const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3');

/**
 * Downloads a file from a URL and saves it to the destination path.
 */
async function downloadFile(url, destPath) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.statusText}`);
  }
  const arrayBuffer = await response.arrayBuffer();
  await fs.promises.writeFile(destPath, Buffer.from(arrayBuffer));
}

/**
 * Initializes the SQLite database, checks Riot DDragon for champions,
 * inserts new ones, and downloads missing champion portraits.
 */
async function initDatabase(dbPath, imagesDir) {
  // Ensure data and images directories exist
  const dbDir = path.dirname(dbPath);
  if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
  }
  if (!fs.existsSync(imagesDir)) {
    fs.mkdirSync(imagesDir, { recursive: true });
  }

  console.log(`[Database] Initializing SQLite database at ${dbPath}`);
  
  // Open the database
  const db = await new Promise((resolve, reject) => {
    const database = new sqlite3.Database(dbPath, (err) => {
      if (err) reject(err);
      else resolve(database);
    });
  });

  // Create table
  await new Promise((resolve, reject) => {
    db.run(
      `CREATE TABLE IF NOT EXISTS champions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        image_name TEXT NOT NULL,
        played INTEGER DEFAULT 0,
        top4 INTEGER DEFAULT 0,
        won INTEGER DEFAULT 0
      )`,
      (err) => {
        if (err) reject(err);
        else resolve();
      }
    );
  });

  // Ensure tags column exists (migration for existing databases)
  await new Promise((resolve) => {
    db.run(`ALTER TABLE champions ADD COLUMN tags TEXT`, (err) => {
      // Ignore error if column already exists
      resolve();
    });
  });

  // Get Riot DDragon version
  let version = '14.12.1'; // Fallback version
  try {
    console.log('[DDragon] Fetching latest game version...');
    const response = await fetch('https://ddragon.leagueoflegends.com/api/versions.json');
    if (response.ok) {
      const versions = await response.json();
      if (Array.isArray(versions) && versions.length > 0) {
        version = versions[0];
        console.log(`[DDragon] Latest version detected: ${version}`);
      }
    }
  } catch (error) {
    console.warn('[DDragon] Failed to fetch latest version, using fallback:', version, error.message);
  }

  // Get champions list
  let championData = {};
  try {
    console.log(`[DDragon] Fetching champion data for version ${version}...`);
    const response = await fetch(`https://ddragon.leagueoflegends.com/cdn/${version}/data/en_US/champion.json`);
    if (!response.ok) {
      throw new Error(`Failed to fetch champion list: ${response.statusText}`);
    }
    const json = await response.json();
    championData = json.data || {};
  } catch (error) {
    console.error('[DDragon] Error fetching champion list:', error.message);
    // If it fails, check if we have database data already. If so, we can proceed.
    const count = await new Promise((resolve) => {
      db.get('SELECT COUNT(*) as count FROM champions', (err, row) => {
        resolve(row ? row.count : 0);
      });
    });
    if (count > 0) {
      console.log(`[DDragon] Network fetch failed, but database has ${count} champions. Proceeding.`);
      return db;
    }
    throw new Error('Could not fetch champion list and no local database seed is available.');
  }

  const champions = Object.values(championData);
  console.log(`[DDragon] Found ${champions.length} champions. Syncing with database...`);

  // Sync with DB and download images
  let insertedCount = 0;
  let downloadedCount = 0;

  for (let i = 0; i < champions.length; i++) {
    const champ = champions[i];
    const champId = champ.id;
    const champName = champ.name;
    const imageName = champ.image.full;
    const localImagePath = path.join(imagesDir, imageName);

    // 1. Insert into database if not exists (checking existing tags as well)
    const existing = await new Promise((resolve, reject) => {
      db.get('SELECT tags FROM champions WHERE id = ?', [champId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    const tagsStr = Array.isArray(champ.tags) ? champ.tags.join(',') : '';

    if (!existing) {
      await new Promise((resolve, reject) => {
        db.run(
          'INSERT INTO champions (id, name, image_name, played, top4, won, tags) VALUES (?, ?, ?, 0, 0, 0, ?)',
          [champId, champName, imageName, tagsStr],
          (err) => {
            if (err) reject(err);
            else {
              insertedCount++;
              resolve();
            }
          }
        );
      });
    } else if (existing.tags === null || existing.tags === undefined || existing.tags === '') {
      // If champion exists but tags are not populated, update them
      await new Promise((resolve, reject) => {
        db.run(
          'UPDATE champions SET tags = ? WHERE id = ?',
          [tagsStr, champId],
          (err) => {
            if (err) reject(err);
            else resolve();
          }
        );
      });
    }

    // 2. Download portrait image if not exists
    if (!fs.existsSync(localImagePath)) {
      const imageUrl = `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${imageName}`;
      try {
        console.log(`[Images] Downloading ${champName} portrait (${i + 1}/${champions.length})...`);
        await downloadFile(imageUrl, localImagePath);
        downloadedCount++;
      } catch (err) {
        console.error(`[Images] Failed to download image for ${champName}:`, err.message);
      }
    }
  }

  console.log(`[Sync] Finished. Added ${insertedCount} new champions. Downloaded ${downloadedCount} portraits.`);
  return db;
}

module.exports = { initDatabase };
