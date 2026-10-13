-- Run once:  psql -U postgres -d dimensionsx -f schema.sql
-- (create the DB first:  CREATE DATABASE dimensionsx;)

CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  employee_id   TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
  id                SERIAL PRIMARY KEY,
  owner_employee_id TEXT NOT NULL REFERENCES users(employee_id) ON DELETE CASCADE,
  project_name      TEXT NOT NULL,
  description       TEXT,
  client_name       TEXT NOT NULL,
  client_contact    TEXT,
  designer_name     TEXT NOT NULL,
  site_address      TEXT,
  due_date          DATE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS projects_owner_idx ON projects(owner_employee_id);
