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