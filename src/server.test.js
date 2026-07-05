const request = require('supertest');
const sqlite3 = require('sqlite3');
const app = require('./server');

describe('LoL Arena Tracker Backend API', () => {
  let db;

  beforeAll((done) => {
    // Initialize in-memory database for testing
    db = new sqlite3.Database(':memory:', (err) => {
      if (err) return done(err);

      // Create schema
      db.run(
        `CREATE TABLE champions (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          image_name TEXT NOT NULL,
          played INTEGER DEFAULT 0,
          top4 INTEGER DEFAULT 0,
          won INTEGER DEFAULT 0
        )`,
        (err) => {
          if (err) return done(err);

          // Seed test data
          const stmt = db.prepare(
            'INSERT INTO champions (id, name, image_name, played, top4, won) VALUES (?, ?, ?, ?, ?, ?)'
          );
          stmt.run('Aatrox', 'Aatrox', 'Aatrox.png', 0, 0, 0);
          stmt.run('Ahri', 'Ahri', 'Ahri.png', 1, 0, 0);
          stmt.run('Lux', 'Lux', 'Lux.png', 1, 1, 0);
          stmt.run('Garen', 'Garen', 'Garen.png', 1, 1, 1);
          stmt.finalize((err) => {
            if (err) return done(err);
            
            // Set database on app
            app.setDb(db);
            done();
          });
        }
      );
    });
  });

  afterAll((done) => {
    if (db) {
      db.close(done);
    } else {
      done();
    }
  });

  describe('GET /api/champions', () => {
    it('should return all seeded champions sorted alphabetically', async () => {
      const response = await request(app)
        .get('/api/champions')
        .expect('Content-Type', /json/)
        .expect(200);

      expect(response.body).toHaveLength(4);
      expect(response.body[0].id).toBe('Aatrox');
      expect(response.body[1].id).toBe('Ahri');
      expect(response.body[2].id).toBe('Garen'); // G comes before L
      expect(response.body[3].id).toBe('Lux');
    });
  });

  describe('GET /api/stats', () => {
    it('should calculate statistics correctly', async () => {
      const response = await request(app)
        .get('/api/stats')
        .expect('Content-Type', /json/)
        .expect(200);

      expect(response.body).toEqual({
        total: 4,
        played: 3, // Ahri, Lux, Garen
        top4: 2,   // Lux, Garen
        won: 1     // Garen
      });
    });
  });

  describe('POST /api/champions/:id/status', () => {
    it('should update status and return updated champion data', async () => {
      const response = await request(app)
        .post('/api/champions/Aatrox/status')
        .send({ played: true, top4: false, won: false })
        .expect(200);

      expect(response.body).toEqual({
        id: 'Aatrox',
        name: 'Aatrox',
        image_name: 'Aatrox.png',
        played: 1,
        top4: 0,
        won: 0
      });
    });

    it('should enforce hierarchical logic when marking as won', async () => {
      // Ahri has played=1, top4=0, won=0
      // Setting won=true should force played=true and top4=true
      const response = await request(app)
        .post('/api/champions/Ahri/status')
        .send({ played: false, top4: false, won: true })
        .expect(200);

      expect(response.body).toEqual({
        id: 'Ahri',
        name: 'Ahri',
        image_name: 'Ahri.png',
        played: 1,
        top4: 1,
        won: 1
      });
    });

    it('should enforce hierarchical logic when marking top4 only', async () => {
      // Aatrox has played=1, top4=0, won=0 now
      // Setting top4=true should force played=true
      const response = await request(app)
        .post('/api/champions/Aatrox/status')
        .send({ played: false, top4: true, won: false })
        .expect(200);

      expect(response.body.played).toBe(1);
      expect(response.body.top4).toBe(1);
      expect(response.body.won).toBe(0);
    });

    it('should enforce hierarchical logic when unmarking played status', async () => {
      // Garen has played=1, top4=1, won=1
      // Setting played=false should force top4=false and won=false
      const response = await request(app)
        .post('/api/champions/Garen/status')
        .send({ played: false, top4: true, won: true })
        .expect(200);

      expect(response.body).toEqual({
        id: 'Garen',
        name: 'Garen',
        image_name: 'Garen.png',
        played: 0,
        top4: 0,
        won: 0
      });
    });

    it('should return 404 for a non-existent champion ID', async () => {
      await request(app)
        .post('/api/champions/InvalidChampion/status')
        .send({ played: true })
        .expect(404);
    });
  });
});
