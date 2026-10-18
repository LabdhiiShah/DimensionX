CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  employee_id   TEXT UNIQUE NOT NULL,
  full_name     TEXT,
  email         TEXT,
  password_hash TEXT NOT NULL,
  is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS projects (
  id SERIAL PRIMARY KEY,
  owner_employee_id VARCHAR(100) NOT NULL
    REFERENCES users(employee_id) ON DELETE CASCADE,
  project_name TEXT NOT NULL,
  description TEXT,
  client_name TEXT NOT NULL,
  client_contact TEXT,
  designer_name TEXT NOT NULL,
  site_address TEXT,
  due_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS projects_owner_idx
ON projects(owner_employee_id);

-- Safe additive migration for existing databases
ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;

-- Email uniqueness is case-insensitive; existing rows may have NULL email
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique
ON users (LOWER(email))
WHERE email IS NOT NULL;