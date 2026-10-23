using System;

/// <summary>
/// Shared layout data shapes. FurnitureSyncManager writes these when you
/// click "View in VR"; VrLayoutLoader (in your VR scene/build) reads them
/// back and spawns the furniture. Keeping this in one shared file means
/// the two can never drift out of sync with each other.
/// </summary>
[Serializable]
public class FurnitureLayoutEntry
{
    public string instance_id;        // blank for the original type-keyed catalog demo objects
    public int type_id;
    public int style_id;
    public string prefab_path;
    public float px, py, pz;          // world position
    public float rx, ry, rz, rw;      // world rotation (quaternion)
    public float sx, sy, sz;          // local scale
}

[Serializable]
public class FurnitureLayoutSnapshot
{
    public FurnitureLayoutEntry[] items;
    public string saved_at;
}

// --- NEW: Used to parse the layout coming from the database via Node.js ---
[Serializable]
public class SavedFurnitureItem
{
    public string instance_id;
    public int type_id;
    public int style_id;
    public string style_name;
    public string prefab_path;
    public float world_x;
    public float world_y;
    public float world_z;
    public float rotation_y_deg;
    public float scale;
    public float scale_multiplier;
}