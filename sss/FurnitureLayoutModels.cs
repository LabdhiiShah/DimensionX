using System;

[Serializable]
public class FurnitureLayoutEntry
{
    public string instance_id;
    public int type_id;
    public int style_id;
    public string prefab_path;
    public float px, py, pz;
    public float rx, ry, rz, rw;
    public float sx, sy, sz;
}

[Serializable]
public class FurnitureLayoutSnapshot
{
    public FurnitureLayoutEntry[] items;
    public string saved_at;
}