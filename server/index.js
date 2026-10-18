
require('dotenv').config();

const express = require('express');
const path = require('path');
const cors = require('cors');
const authRoutes = require('./routes/auth');
const projectsRouter = require('./projects.cjs');

const app = express();

app.use(cors());
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/projects', projectsRouter);

app.get('/api/health', (_req, res) => {
  res.json({ ok: true });
});

// Serve the built React frontend
const frontendPath = path.join(__dirname, '..', 'client', 'dist');
app.use(express.static(frontendPath));

// Keep unknown API requests from returning index.html
app.use('/api', (_req, res) => {
  res.status(404).json({ error: 'API endpoint not found.' });
});

// Support React Router page refreshes
app.get('*', (_req, res) => {
  res.sendFile(path.join(frontendPath, 'index.html'));
});

if (!process.env.JWT_SECRET) {
  console.warn('WARNING: JWT_SECRET is not set.');
}

const PORT = process.env.PORT || 4000;

app.listen(PORT, '0.0.0.0', () => {
  console.log(`DimensionX server listening on port ${PORT}`);
});
