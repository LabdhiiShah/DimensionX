-- ==============================================================================
-- UNIFIED DATABASE SETUP SCRIPT
-- Combines schema setup (schema.sql) and database dump (dimx.sql)
-- ==============================================================================

-- 1. CREATE TABLES
-- ==============================================================================

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    employee_id   VARCHAR(100) UNIQUE NOT NULL,
    full_name     TEXT,
    email         TEXT,
    password_hash TEXT NOT NULL,
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Projects Table (Incorporating columns from screenshots & schema.sql)
CREATE TABLE IF NOT EXISTS projects (
    id                SERIAL PRIMARY KEY,
    owner_employee_id VARCHAR(100) NOT NULL REFERENCES users(employee_id) ON DELETE CASCADE,
    project_name      VARCHAR(200) NOT NULL,
    description       TEXT,
    client_name       VARCHAR(200) NOT NULL,
    client_contact    VARCHAR(200),
    designer_name     VARCHAR(200) NOT NULL,
    site_address      VARCHAR(300),
    due_date          DATE,
    status            VARCHAR(50) DEFAULT 'active',
    glb_url           TEXT,
    plan              JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Furniture Type Table
CREATE TABLE IF NOT EXISTS furniture_type (
    type_id   SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL
);

-- Furniture Style Table
CREATE TABLE IF NOT EXISTS furniture_style (
    style_id      SERIAL PRIMARY KEY,
    type_id       INTEGER NOT NULL REFERENCES furniture_type(type_id) ON DELETE CASCADE,
    style_name    VARCHAR(50) NOT NULL,
    prefab_path   TEXT NOT NULL,
    preview_image TEXT,
    CONSTRAINT furniture_style_type_id_style_name_key UNIQUE (type_id, style_name)
);

-- CAD Projects Table (From dimx.sql)
CREATE TABLE IF NOT EXISTS cad_project (
    project_id   SERIAL PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL,
    client_name  VARCHAR(100),
    cad_file     TEXT NOT NULL,
    upload_date  TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Generated Rooms Table (From dimx.sql)
CREATE TABLE IF NOT EXISTS generated_room (
    room_id    SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES cad_project(project_id) ON DELETE CASCADE,
    room_name  VARCHAR(50) NOT NULL
);


-- 2. CREATE INDEXES
-- ==============================================================================

CREATE INDEX IF NOT EXISTS idx_projects_owner 
ON projects(owner_employee_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique
ON users (LOWER(email))
WHERE email IS NOT NULL;


-- 3. SEED STATIC DATA (Furniture)
-- ==============================================================================

INSERT INTO furniture_type (type_id, type_name) VALUES
    (1, 'Bed'), (2, 'Sofa'), (3, 'Chair'), (4, 'Desk'), (5, 'Table'), 
    (6, 'Wadrobe'), (7, 'sink'), (8, 'stove'), (9, 'shower'), (10, 'toilet'), 
    (11, 'tv'), (12, 'drawer'), (13, 'lamp')
ON CONFLICT (type_id) DO UPDATE SET type_name = EXCLUDED.type_name;

INSERT INTO furniture_style (style_id, type_id, style_name, prefab_path) VALUES
    (1, 1, 'Modern', 'Assets/Furniture/Bed/bedsc.prefab'),
    (2, 1, 'Scandinavian', 'Assets/Furniture/Bed/Bunkbedsc.prefab'),
    (3, 2, 'Modern', 'Assets/Furniture/Sofa/Couch_Large1.prefab'),
    (4, 2, 'Scandinavian', 'Assets/Furniture/Sofa/Couch_Medium2.prefab'),
    (5, 2, 'Minimal', 'Assets/Furniture/Sofa/Couch_Small1.prefab'),
    (6, 3, 'Scandinavian', 'Assets/Furniture/chair/Sc.prefab'),
    (8, 4, 'Scandinavian', 'Assets/Furniture/Desk/sc.prefab'),
    (9, 12, 'Modern', 'Assets/Furniture/drawer/Drawer_mo.prefab'),
    (10, 12, 'Scandinavian', 'Assets/Furniture/drawer/drawersc.prefab'),
    (11, 5, 'Scandinavian', 'Assets/Furniture/table/ScanndinavianSideTable.prefab'),
    (12, 7, 'Modern', 'Assets/Furniture/sink/bathroomSinkSquare.prefab'),
    (13, 7, 'Scandinavian', 'Assets/Furniture/sink/WoodSink1KitchenCabinet1.prefab'),
    (14, 7, 'Minimal', 'Assets/Furniture/sink/SteelSink1KitchenCabinet1.prefab'),
    (15, 8, 'Modern', 'Assets/Furniture/stove/GasStove1.prefab'),
    (16, 8, 'Scandinavian', 'Assets/Furniture/stove/Kitchen_Oven_Large.prefab'),
    (17, 8, 'Minimal', 'Assets/Furniture/stove/model.prefab'),
    (18, 9, 'Modern', 'Assets/Furniture/shower/showerRound.prefab'),
    (21, 10, 'Modern', 'Assets/Furniture/toilet/Bathroom_Toilet.prefab'),
    (22, 10, 'Scandinavian', 'Assets/Furniture/toilet/SIEFRING_Toilet_LP.prefab'),
    (23, 10, 'Minimal', 'Assets/Furniture/toilet/toiletSquare.prefab'),
    (24, 11, 'Modern', 'Assets/Furniture/tv/TV.prefab'),
    (25, 11, 'Scandinavian', 'Assets/Furniture/tv/TV_01.prefab'),
    (26, 13, 'Modern', 'Assets/Furniture/lamp/FloorLamp1.prefab'),
    (27, 13, 'Scandinavian', 'Assets/Furniture/lamp/Light_Ceiling2.prefab'),
    (28, 13, 'Minimal', 'Assets/Furniture/lamp/Light_Ceiling4.prefab'),
    (29, 13, 'Industrial', 'Assets/Furniture/lamp/Light_Cube2.prefab')
ON CONFLICT (style_id) DO UPDATE SET
    type_id = EXCLUDED.type_id,
    style_name = EXCLUDED.style_name,
    prefab_path = EXCLUDED.prefab_path;


-- 4. SEED DYNAMIC DATA (Users & Projects from dimx.sql)
-- Using ON CONFLICT DO NOTHING to prevent errors on re-runs
-- ==============================================================================

INSERT INTO users (id, employee_id, password_hash, is_admin, created_at) VALUES
    (1, 'heshavasani28@gmail.com', '$2a$10$5UEiZ3P55CeHzU6lNMhjCeobqlYnK1GJeje3pp84q18jb6wftyzui', false, '2026-09-30 09:56:42.002105+05:30'),
    (2, 'bhoomidesai@gmail.com', '$2a$10$k8xIoCCxOBpZXhT42S5tRuqxzeuMjIf3N1lFJRCqcirj3TQrHJ2w2', false, '2026-10-13 14:58:28.63822+05:30'),
    (3, 'ak@gmail.com', '$2a$10$nUSFQMnXck7LO7Jwef/s..AW.YtAN1Jatn.MLSyzMnNvngchlXqFS', false, '2026-10-13 20:57:50.747358+05:30')
ON CONFLICT (id) DO NOTHING;

INSERT INTO projects (id, owner_employee_id, project_name, description, client_name, client_contact, designer_name, site_address, due_date, created_at) VALUES
    (1, 'heshavasani28@gmail.com', 'building', 'haha', 'hesha', '9821922236', 'hesha', 'vile parle', '2026-10-01', '2026-10-13 20:45:28.712016+05:30'),
    (2, 'heshavasani28@gmail.com', 'apartment', 'hehe', 'bhoomm', 'heshavasani28@gmail.com', 'hesa', 'kandivali', '2026-10-31', '2026-10-13 20:58:53.796898+05:30')
ON CONFLICT (id) DO NOTHING;


-- 5. SYNC SEQUENCES
-- Ensures that future inserts don't conflict with the manually inserted IDs above
-- ==============================================================================

SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1), true);
SELECT setval('projects_id_seq', COALESCE((SELECT MAX(id) FROM projects), 1), true);
SELECT setval('furniture_type_type_id_seq', COALESCE((SELECT MAX(type_id) FROM furniture_type), 1), true);
SELECT setval('furniture_style_style_id_seq', COALESCE((SELECT MAX(style_id) FROM furniture_style), 1), true);