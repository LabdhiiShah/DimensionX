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
  ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';

  -- Email uniqueness is case-insensitive; existing rows may have NULL email
  CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique
  ON users (LOWER(email))
  WHERE email IS NOT NULL;

  -- Furniture catalog schema from Hi
  CREATE TABLE IF NOT EXISTS furniture_type (
    type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL
  );

  CREATE TABLE IF NOT EXISTS furniture_style (
    style_id SERIAL PRIMARY KEY,
    type_id INTEGER NOT NULL REFERENCES furniture_type(type_id) ON DELETE CASCADE,
    style_name VARCHAR(50) NOT NULL,
    prefab_path TEXT NOT NULL,
    preview_image TEXT,
    CONSTRAINT furniture_style_type_id_style_name_key UNIQUE (type_id, style_name)
  );

  -- Seed furniture types
  INSERT INTO furniture_type (type_id, type_name) VALUES
    (1, 'Bed'),
    (2, 'Sofa'),
    (3, 'Chair'),
    (4, 'Desk'),
    (5, 'Table'),
    (6, 'Wadrobe'),
    (7, 'sink'),
    (8, 'stove'),
    (9, 'shower'),
    (10, 'toilet'),
    (11, 'tv'),
    (12, 'drawer'),
    (13, 'lamp')
  ON CONFLICT (type_id) DO UPDATE SET type_name = EXCLUDED.type_name;

  -- Seed furniture styles
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
