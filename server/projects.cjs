// Project routes:  GET /api/projects   -> the logged-in user's projects
//                  POST /api/projects  -> create one (stored under their login ID)
//
// .cjs on purpose: works whether your server uses require() or import.
//
// Needs the same JWT secret your login route signs tokens with (JWT_SECRET),
// and database settings via DATABASE_URL or the usual PGHOST/PGUSER/PGPASSWORD/PGDATABASE.

const express = require('express');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

const LIMITS = { projectName: 200, description: 4000, clientName: 200, clientContact: 200, designerName: 200, siteAddress: 300 };

let defaultPool; // created on first request, so .env has certainly been loaded by then
function getDefaultPool() {
  if (!defaultPool) {
    defaultPool = new Pool(process.env.DATABASE_URL ? { connectionString: process.env.DATABASE_URL } : undefined);
  }
  return defaultPool;
}

function toApi(row) {
  return {
    id: row.id,
    projectName: row.project_name,
    description: row.description || '',
    clientName: row.client_name,
    clientContact: row.client_contact || '',
    designerName: row.designer_name,
    siteAddress: row.site_address || '',
    dueDate: row.due_date || null,         // "YYYY-MM-DD"
    createdAt: row.created_at,
  };
}

const COLUMNS = `id, project_name, description, client_name, client_contact, designer_name,
                 site_address, due_date::text AS due_date, created_at`;

function createRouter(pool) {
  const db = { query: (...a) => (pool || getDefaultPool()).query(...a) };
  const router = express.Router();
  router.use(express.json());

  // Works out WHO is calling from the login token, whatever your token payload calls things.
  async function resolveEmployeeId(payload) {
    const direct = payload.employeeId || payload.employee_id || payload.username;
    if (direct) {
      const r = await db.query('SELECT employee_id FROM users WHERE employee_id = $1', [String(direct)]);
      if (r.rows[0]) return r.rows[0].employee_id;
    }
    const uid = payload.id ?? payload.userId ?? payload.sub;
    if (uid != null && /^\d+$/.test(String(uid))) {
      const r = await db.query('SELECT employee_id FROM users WHERE id = $1', [Number(uid)]);
      if (r.rows[0]) return r.rows[0].employee_id;
    }
    return null;
  }

  async function requireAuth(req, res, next) {
    const secret = process.env.JWT_SECRET;
    if (!secret) return res.status(500).json({ error: 'Server is missing JWT_SECRET (it must match the secret used at login).' });
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : null;
    if (!token) return res.status(401).json({ error: 'Please log in again.' });
    try {
      const payload = jwt.verify(token, secret);
      const employeeId = await resolveEmployeeId(payload);
      if (!employeeId) return res.status(401).json({ error: 'Please log in again.' });
      req.employeeId = employeeId;
      next();
    } catch (err) {
      if (err && err.name && err.name.includes('Token')) return res.status(401).json({ error: 'Your session expired. Please log in again.' });
      next(err);
    }
  }
  router.use(requireAuth);

  router.get('/', async (req, res, next) => {
    try {
      const r = await db.query(
        `SELECT ${COLUMNS} FROM projects WHERE owner_employee_id = $1 ORDER BY created_at DESC, id DESC`,
        [req.employeeId]
      );
      res.json({ projects: r.rows.map(toApi) });
    } catch (err) { next(err); }
  });

  router.post('/', async (req, res, next) => {
    try {
      const b = req.body || {};
      const clean = {};
      for (const key of Object.keys(LIMITS)) {
        const v = b[key] == null ? '' : String(b[key]).trim();
        if (v.length > LIMITS[key]) return res.status(400).json({ error: `${key} is too long (max ${LIMITS[key]} characters).` });
        clean[key] = v;
      }
      if (!clean.projectName) return res.status(400).json({ error: 'Project name is required.' });
      if (!clean.clientName) return res.status(400).json({ error: 'Client name is required.' });
      if (!clean.designerName) return res.status(400).json({ error: 'Designer name is required.' });

      let dueDate = null;
      if (b.dueDate) {
        const s = String(b.dueDate);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || Number.isNaN(Date.parse(s))) return res.status(400).json({ error: 'Due date must look like 2026-12-31.' });
        dueDate = s;
      }

      const r = await db.query(
        `INSERT INTO projects (owner_employee_id, project_name, description, client_name, client_contact, designer_name, site_address, due_date)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         RETURNING ${COLUMNS}`,
        [req.employeeId, clean.projectName, clean.description || null, clean.clientName, clean.clientContact || null,
         clean.designerName, clean.siteAddress || null, dueDate]
      );
      res.status(201).json({ project: toApi(r.rows[0]) });
    } catch (err) { next(err); }
  });

  // eslint-disable-next-line no-unused-vars
  router.use((err, req, res, next) => {
    console.error('[projects] error:', err);
    if (err && err.code === '42P01') return res.status(500).json({ error: 'The projects table is missing - run projects_schema.sql in the dimensionx database.' });
    res.status(500).json({ error: 'Something went wrong saving your project.' });
  });

  return router;
}

module.exports = createRouter();       // default: require('./projects.cjs')
module.exports.createRouter = createRouter; // for tests / passing your own pool
