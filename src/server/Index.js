require('dotenv').config();
const express = require('express');
const cors = require('cors');
const authRoutes = require('./routes/auth');

const app = express();

app.use(cors({ origin: process.env.CLIENT_ORIGIN || 'http://localhost:5174' }));
app.use(express.json());

app.use('/api/auth', authRoutes);

app.get('/api/health', (_req, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`DimensionX auth server listening on http://localhost:${PORT}`);
});