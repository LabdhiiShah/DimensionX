
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
  return employeeId.includes('@')
    ? employeeId.split('@')[0]
    : employeeId;
}

function isValidEmail(email) {
  return typeof email === 'string' &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

function issueToken(user) {
  return jwt.sign(
    {
      userId: user.id,
      employeeId: user.employee_id,
      isAdmin: user.is_admin,
    },
    JWT_SECRET,
    { expiresIn: '8h' }
  );
}

function authResponse(user) {
  return {
    token: issueToken(user),
    username: usernameFromEmployeeId(user.employee_id),
    fullName: user.full_name || '',
    email: user.email || '',
    isAdmin: user.is_admin,
  };
}

// POST /api/auth/signup
router.post('/signup', async (req, res) => {
  const { fullName, email, employeeId, password } = req.body || {};

  const cleanName = typeof fullName === 'string' ? fullName.trim() : '';
  const cleanEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
  const cleanEmployeeId =
    typeof employeeId === 'string' ? employeeId.trim() : '';

  if (cleanName.length < 2 || cleanName.length > 100) {
    return res.status(400).json({
      error: 'Please enter your full name (2–100 characters).',
    });
  }

  if (!isValidEmail(cleanEmail) || cleanEmail.length > 254) {
    return res.status(400).json({
      error: 'Please enter a valid email address.',
    });
  }

  if (!isValidEmployeeId(cleanEmployeeId)) {
    return res.status(400).json({
      error: 'Employee/Admin ID must be at least 3 characters.',
    });
  }

  if (typeof password !== 'string' || password.length < 8) {
    return res.status(400).json({
      error: 'Password must be at least 8 characters.',
    });
  }

  try {
    const existing = await pool.query(
      `SELECT id
       FROM users
       WHERE employee_id = $1 OR LOWER(email) = LOWER($2)
       LIMIT 1`,
      [cleanEmployeeId, cleanEmail]
    );

    if (existing.rows.length > 0) {
      return res.status(409).json({
        error: 'That Employee/Admin ID or email is already registered.',
      });
    }

    const passwordHash = await bcrypt.hash(password, 10);

    // Public signup must never grant administrator privileges.
    const result = await pool.query(
      `INSERT INTO users
         (employee_id, full_name, email, password_hash, is_admin)
       VALUES ($1, $2, $3, $4, FALSE)
       RETURNING id, employee_id, full_name, email, is_admin`,
      [cleanEmployeeId, cleanName, cleanEmail, passwordHash]
    );

    return res.status(201).json(authResponse(result.rows[0]));
  } catch (err) {
    // Also handle concurrent signup attempts against unique constraints.
    if (err.code === '23505') {
      return res.status(409).json({
        error: 'That Employee/Admin ID or email is already registered.',
      });
    }

    console.error('Signup error:', err);
    return res.status(500).json({
      error: 'Something went wrong creating your account.',
    });
  }
});

// POST /api/auth/login
router.post('/login', async (req, res) => {
  const { employeeId, password } = req.body || {};
  const cleanEmployeeId =
    typeof employeeId === 'string' ? employeeId.trim() : '';

  if (!isValidEmployeeId(cleanEmployeeId) ||
      typeof password !== 'string' || !password) {
    return res.status(400).json({
      error: 'Employee/Admin ID and password are required.',
    });
  }

  try {
    const result = await pool.query(
      `SELECT id, employee_id, full_name, email, password_hash, is_admin
       FROM users
       WHERE employee_id = $1`,
      [cleanEmployeeId]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({
        error: 'Invalid Employee/Admin ID or password.',
      });
    }

    const user = result.rows[0];
    const passwordMatches = await bcrypt.compare(
      password,
      user.password_hash
    );

    if (!passwordMatches) {
      return res.status(401).json({
        error: 'Invalid Employee/Admin ID or password.',
      });
    }

    return res.json(authResponse(user));
  } catch (err) {
    console.error('Login error:', err);
    return res.status(500).json({
      error: 'Something went wrong logging you in.',
    });
  }
});

module.exports = router;
