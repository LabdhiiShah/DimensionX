// DimensionX API server (auth + projects). CommonJS only - do NOT mix import/require.
require('dotenv').config();           // must be first so process.env is filled before anything else loads
const express = require('express');
const cors = require('cors');
const authRoutes = require('./routes/auth');
const projectsRouter = require('./projects.cjs');

const app = express();

// Allow the Vite dev server (5173 by default, 5174 if 5173 is busy) plus anything in CLIENT_ORIGIN.
const origins = [
  'http://localhost:5173',
  'http://localhost:5174',
  ...(process.env.CLIENT_ORIGIN || '').split(',').map((s) => s.trim()).filter(Boolean),
];
app.use(cors({ origin: origins }));
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/projects', projectsRouter);
app.get('/api/health', (_req, res) => res.json({ ok: true }));

if (!process.env.JWT_SECRET) {
  console.warn('WARNING: JWT_SECRET is not set. Login may still work if routes/auth.js has its own fallback, but /api/projects will reject every request.');
}

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`DimensionX API listening on http://localhost:${PORT}`));
