// Project routes: authenticated project listing/creation and employee directory for admins.
const express = require('express');
const jwt = require('jsonwebtoken');
const defaultPool = require('./db');

const LIMITS = { projectName: 200, description: 4000, clientName: 200, clientContact: 200, designerName: 200, siteAddress: 300 };

function toApi(row) {
  return {
    id: row.id,
    projectName: row.project_name,
    description: row.description || '',
    clientName: row.client_name,
    clientContact: row.client_contact || '',
    designerName: row.designer_name,
    designerEmployeeId: row.owner_employee_id,
    siteAddress: row.site_address || '',
    dueDate: row.due_date || null,
    createdAt: row.created_at,
  };
}

const COLUMNS = `id, owner_employee_id, project_name, description, client_name, client_contact, designer_name,
                 site_address, due_date::text AS due_date, created_at`;

function createRouter(pool) {
  const db = { query: (...a) => (pool || defaultPool).query(...a) };
  const router = express.Router();
  router.use(express.json());

  async function resolveUser(payload) {
    const uid = payload.userId ?? payload.id ?? payload.sub;
    if (uid == null || !/^\d+$/.test(String(uid))) return null;
    const result = await db.query(
      `SELECT id, employee_id, is_admin, full_name, email FROM users WHERE id = $1`,
      [Number(uid)]
    );
    return result.rows[0] || null;
  }

  async function requireAuth(req, res, next) {
    const secret = process.env.JWT_SECRET;
    if (!secret) return res.status(500).json({ error: 'Server is missing JWT_SECRET.' });
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : null;
    if (!token) return res.status(401).json({ error: 'Please log in again.' });
    try {
      const payload = jwt.verify(token, secret);
      const user = await resolveUser(payload);
      if (!user) return res.status(401).json({ error: 'Please log in again.' });
      req.user = user;
      req.employeeId = user.employee_id;
      next();
    } catch (err) {
      if (err.name && err.name.includes('Token')) {
        return res.status(401).json({ error: 'Your session expired. Please log in again.' });
      }
      next(err);
    }
  }

  router.use(requireAuth);

  // Admin-only employee directory used by the Add Project designer dropdown.
  router.get('/employees', async (req, res, next) => {
    if (!req.user.is_admin) return res.status(403).json({ error: 'Only administrators can view employees.' });
    try {
      const result = await db.query(
        `SELECT employee_id AS "employeeId", full_name AS "fullName", email
         FROM users
         WHERE COALESCE(is_admin, false) = false
           AND employee_id IS NOT NULL
         ORDER BY full_name ASC NULLS LAST, employee_id ASC`
      );
      res.json({ employees: result.rows });
    } catch (err) { next(err); }
  });

  router.get('/', async (req, res, next) => {
    try {
      const query = req.user.is_admin
        ? `SELECT ${COLUMNS} FROM projects ORDER BY created_at DESC, id DESC`
        : `SELECT ${COLUMNS} FROM projects WHERE owner_employee_id = $1 ORDER BY created_at DESC, id DESC`;
      const result = req.user.is_admin ? await db.query(query) : await db.query(query, [req.employeeId]);
      res.json({ projects: result.rows.map(toApi) });
    } catch (err) { next(err); }
  });

  router.post('/', async (req, res, next) => {
    if (!req.user.is_admin) return res.status(403).json({ error: 'Only administrators can create projects.' });
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

      // Prefer the employee ID selected from the employee directory. Verify it server-side.
      const selectedEmployeeId = String(b.designerEmployeeId || '').trim();
      if (!selectedEmployeeId) return res.status(400).json({ error: 'Please select a registered designer.' });
      const employeeResult = await db.query(
        `SELECT employee_id, full_name FROM users
         WHERE employee_id = $1 AND COALESCE(is_admin, false) = false`,
        [selectedEmployeeId]
      );
      if (!employeeResult.rows.length) return res.status(400).json({ error: 'The selected designer is not a registered employee.' });
      const employee = employeeResult.rows[0];
      clean.designerName = employee.full_name || selectedEmployeeId;

      let dueDate = null;
      if (b.dueDate) {
        const s = String(b.dueDate);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || Number.isNaN(Date.parse(s))) {
          return res.status(400).json({ error: 'Due date must look like 2026-12-31.' });
        }
        dueDate = s;
      }

      const result = await db.query(
        `INSERT INTO projects (owner_employee_id, project_name, description, client_name, client_contact, designer_name, site_address, due_date)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         RETURNING ${COLUMNS}`,
        [employee.employee_id, clean.projectName, clean.description || null, clean.clientName,
         clean.clientContact || null, clean.designerName, clean.siteAddress || null, dueDate]
      );
      res.status(201).json({ project: toApi(result.rows[0]) });
    } catch (err) { next(err); }
  });

  router.use((err, req, res, next) => {
    console.error('[projects] error:', err);
    if (err && err.code === '42P01') return res.status(500).json({ error: 'A required database table is missing. Check the schema in the dimensionx database.' });
    res.status(500).json({ error: 'Something went wrong with the project request.' });
  });

  return router;
}

module.exports = createRouter();
module.exports.createRouter = createRouter;
