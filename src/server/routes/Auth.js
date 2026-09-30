const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const pool = require('../db');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'dev-only-secret-change-me';

function isValidEmployeeId(id) {
  return typeof id === 'string' && id.trim().length >= 3;
}

function usernameFromEmployeeId(employeeId) {
  // Matches the original frontend logic: everything before '@', if present.
  return employeeId.includes('@') ? employeeId.split('@')[0] : employeeId;
}

function issueToken(user) {
  return jwt.sign(
    { userId: user.id, employeeId: user.employee_id, isAdmin: user.is_admin },
    JWT_SECRET,
    { expiresIn: '8h' }
  );
}

// POST /api/auth/signup
router.post('/signup', async (req, res) => {
  const { employeeId, password } = req.body || {};

  if (!isValidEmployeeId(employeeId) || !password || password.length < 6) {
    return res.status(400).json({
      error: 'Employee ID (min 3 characters) and a password of at least 6 characters are required.',
    });
  }

  try {
    const existing = await pool.query('SELECT id FROM users WHERE employee_id = $1', [employeeId]);
    if (existing.rows.length > 0) {
      return res.status(409).json({ error: 'An account with that Employee/Admin ID already exists.' });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    // Same rule the original frontend used client-side, now enforced server-side instead.
    const isAdmin = employeeId.toLowerCase().includes('admin');

    const result = await pool.query(
      'INSERT INTO users (employee_id, password_hash, is_admin) VALUES ($1, $2, $3) RETURNING id, employee_id, is_admin',
      [employeeId, passwordHash, isAdmin]
    );
    const user = result.rows[0];

    return res.status(201).json({
      token: issueToken(user),
      username: usernameFromEmployeeId(user.employee_id),
      isAdmin: user.is_admin,
    });
  } catch (err) {
    console.error('Signup error:', err);
    return res.status(500).json({ error: 'Something went wrong creating your account.' });
  }
});

// POST /api/auth/login
router.post('/login', async (req, res) => {
  const { employeeId, password } = req.body || {};

  if (!isValidEmployeeId(employeeId) || !password) {
    return res.status(400).json({ error: 'Employee ID and password are required.' });
  }

  try {
    const result = await pool.query(
      'SELECT id, employee_id, password_hash, is_admin FROM users WHERE employee_id = $1',
      [employeeId]
    );
    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid Employee/Admin ID or password.' });
    }

    const user = result.rows[0];
    const passwordMatches = await bcrypt.compare(password, user.password_hash);
    if (!passwordMatches) {
      return res.status(401).json({ error: 'Invalid Employee/Admin ID or password.' });
    }

    return res.json({
      token: issueToken(user),
      username: usernameFromEmployeeId(user.employee_id),
      isAdmin: user.is_admin,
    });
  } catch (err) {
    console.error('Login error:', err);
    return res.status(500).json({ error: 'Something went wrong logging you in.' });
  }
});

module.exports = router;