// DimensionX - procedural decor + extra furniture prefab generator.
// Put this file in  Assets/Editor/  then use the menu:  DimensionX > Generate Decor + Extra Furniture
//
// It builds low-poly prefabs out of primitives (no downloads needed) into
// Assets/Resources/Furniture/<folder>/<Name>_<Style>.prefab, next to your existing ones.
// Existing files are never overwritten unless you use the "Regenerate" menu item.
// Later you can swap any prefab for a real model: just save it under the SAME path/name.
#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static partial class DecorPrefabGenerator
{
    const string Root = "Assets/Resources/Furniture";
    static readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();
    static bool overwrite;
    static int created, skipped;

    // ---- palette ----
    static Color White, Cream, Black, Charcoal, Grey, Concrete, Wood, LightWood, DarkWood, Leather, Brass, Steel,
                 Green, DarkGreen, LeafGreen, Terracotta, Teal, Mustard, Navy, Glass, Pink;
    static Color[] BookCols;

    static Color H(string hex) { Color c; ColorUtility.TryParseHtmlString(hex, out c); return c; }
    static Color Dk(Color c, float f) { return Color.Lerp(c, Color.black, f); }

    static void InitPalette()
    {
        White = H("#f2f0eb"); Cream = H("#e8dcc2"); Black = H("#1e1e20"); Charcoal = H("#3a3d42");
        Grey = H("#9a9da3"); Concrete = H("#8d8f91"); Wood = H("#a9794d"); LightWood = H("#d9b98c");
        DarkWood = H("#4e3524"); Leather = H("#7a4a2b"); Brass = H("#c9a14a"); Steel = H("#a7adb3");
        Green = H("#3f7d4e"); DarkGreen = H("#2c5c3a"); LeafGreen = H("#5a9a5a"); Terracotta = H("#c8704f");
        Teal = H("#2f7f86"); Mustard = H("#d9a93b"); Navy = H("#27365c"); Glass = H("#cfe3ea"); Pink = H("#e58ca0");
        BookCols = new[] { H("#8c2f39"), H("#2f5d62"), H("#c9a227"), H("#3d405b"), H("#e07a5f"), H("#81b29a"), H("#f2cc8f"), H("#264653") };
    }

    [MenuItem("DimensionX/Generate Decor + Extra Furniture")]
    public static void GenerateMissing() { Generate(false); }

    [MenuItem("DimensionX/Regenerate (overwrite) Decor + Extra Furniture")]
    public static void RegenerateAll()
    {
        if (EditorUtility.DisplayDialog("Overwrite?", "This replaces every prefab this tool generates (same names). Continue?", "Yes", "Cancel"))
            Generate(true);
    }

    // =====================================================================
    //  WHAT GETS GENERATED   (file name = <Name>_<Style>; the style word is read by sync-catalog)
    // =====================================================================
    static void Generate(bool ow)
    {
        overwrite = ow; created = 0; skipped = 0; mats.Clear(); InitPalette();

        // ---- more styles for existing furniture ----
        Make("Bed", "Bed_Minimal", r => Bed(r, 1.5f, 2.0f, LightWood, White, Cream, 0.7f, false));
        Make("Bed", "Bed_Industrial", r => Bed(r, 1.6f, 2.0f, Black, Charcoal, Grey, 1.05f, true));
        Make("Sofa", "Sofa_Industrial", r => Sofa(r, 2.2f, 0.9f, Leather, Dk(Leather, 0.1f), true));
        Make("chair", "Armchair_Modern", r => Sofa(r, 0.9f, 0.85f, Teal, Dk(Teal, 0.12f), false));
        Make("chair", "Chair_Minimal", r => Chair(r, White, Black, 0.45f, 0.4f));
        Make("chair", "Chair_Industrial", r => Chair(r, DarkWood, Black, 0.5f, 0.45f));
        Make("Desk", "Desk_Modern", r => Desk(r, 1.4f, White, Black, true, false));
        Make("Desk", "Desk_Minimal", r => Desk(r, 1.2f, LightWood, White, false, false));
        Make("Desk", "Desk_Industrial", r => Desk(r, 1.5f, DarkWood, Black, false, true));
        Make("drawer", "Drawer_Minimal", r => DrawerUnit(r, 0.8f, White, LightWood, Steel));
        Make("drawer", "Drawer_Industrial", r => DrawerUnit(r, 0.9f, Black, DarkWood, Brass));
        Make("table", "DiningTable_Modern", r => Table(r, 1.6f, 0.9f, 0.75f, White, Black, false));
        Make("table", "DiningTable_Minimal", r => Table(r, 1.0f, 1.0f, 0.75f, LightWood, White, true));
        Make("table", "DiningTable_Industrial", r => Table(r, 1.8f, 0.9f, 0.75f, DarkWood, Black, false));
        Make("Wadrobe", "Wardrobe_Modern", r => Wardrobe(r, 1.2f, White, LightWood, false));
        Make("Wadrobe", "Wardrobe_Scandinavian", r => Wardrobe(r, 1.0f, LightWood, Wood, false));
        Make("Wadrobe", "Wardrobe_Minimal", r => Wardrobe(r, 1.6f, LightGreyCol(), White, true));
        Make("Wadrobe", "Wardrobe_Industrial", r => Wardrobe(r, 1.0f, Black, DarkWood, false));
        Make("tv", "TVWallMount_Minimal", r => TvWall(r));

        // ---- decor: plants ----
        Make("plant", "PottedPlant_Modern", PlantBushy);
        Make("plant", "FiddleLeaf_Scandinavian", PlantFiddle);
        Make("plant", "SnakePlant_Minimal", PlantSnake);
        Make("plant", "Succulent_Industrial", PlantSucculent);

        // ---- decor: paintings (hang at 1.5 m) ----
        Make("painting", "AbstractCanvas_Modern", r => {
            Frame(r, 1.0f, 0.7f, Black, Cream);
            Box(r, -0.22f, 1.56f, 0.034f, 0.32f, 0.32f, 0.01f, Terracotta);
            Box(r, 0.12f, 1.45f, 0.034f, 0.3f, 0.4f, 0.01f, Teal);
            Ball(r, 0.02f, 1.68f, 0.036f, 0.18f, 0.18f, 0.01f, Mustard); });
        Make("painting", "LandscapeFrame_Scandinavian", r => {
            Frame(r, 1.2f, 0.8f, LightWood, H("#bfe0ee"));
            Box(r, -0.22f, 1.5f, 0.032f, 0.45f, 0.45f, 0.01f, Grey, 0f, 0f, 45f);
            Box(r, 0.2f, 1.47f, 0.033f, 0.35f, 0.35f, 0.01f, Dk(Grey, 0.2f), 0f, 0f, 45f);
            Box(r, 0, 1.27f, 0.036f, 1.12f, 0.28f, 0.01f, LeafGreen);
            Ball(r, 0.32f, 1.72f, 0.034f, 0.14f, 0.14f, 0.01f, Mustard); });
        Make("painting", "LinePrint_Minimal", r => {
            Frame(r, 0.7f, 0.9f, White, H("#f7f5f0"));
            Cyl(r, 0, 1.58f, 0.034f, 0.3f, 0.01f, Terracotta, 90f);
            Box(r, 0, 1.3f, 0.034f, 0.4f, 0.008f, 0.01f, Black);
            Box(r, -0.1f, 1.4f, 0.034f, 0.008f, 0.2f, 0.01f, Black); });
        Make("painting", "MetalWallArt_Industrial", r => {
            Cyl(r, 0, 1.6f, 0, 0.9f, 0.03f, Charcoal, 90f, 0f, 0f, 0.5f, 0.8f);
            Cyl(r, 0, 1.6f, 0.02f, 0.62f, 0.03f, Brass, 90f, 0f, 0f, 0.6f, 0.9f);
            Cyl(r, 0, 1.6f, 0.04f, 0.3f, 0.03f, Charcoal, 90f, 0f, 0f, 0.5f, 0.8f); });

        // ---- decor: vases ----
        Make("vase", "CeramicVase_Modern", r => {
            Ball(r, 0, 0.13f, 0, 0.2f, 0.26f, 0.2f, Teal, 0f, 0f, 0f, 0.7f);
            Cyl(r, 0, 0.33f, 0, 0.07f, 0.14f, Teal, 0f, 0f, 0f, 0.7f); });
        Make("vase", "FlowerVase_Scandinavian", r => {
            Cyl(r, 0, 0.125f, 0, 0.14f, 0.25f, Glass, 0f, 0f, 0f, 0.9f);
            Color[] fc = { Pink, Mustard, White, Pink, Mustard };
            for (int i = 0; i < 5; i++) {
                float tilt = 10f + (i % 2) * 8f, ang = i * 72f, len = 0.4f;
                Blade(r, 0, 0.2f, 0, ang, tilt, len, 0.01f, LeafGreen);
                float a = ang * Mathf.Deg2Rad, t = tilt * Mathf.Deg2Rad;
                Ball(r, Mathf.Sin(a) * Mathf.Sin(t) * len, 0.2f + Mathf.Cos(t) * len, Mathf.Cos(a) * Mathf.Sin(t) * len, 0.08f, 0.08f, 0.08f, fc[i]);
            } });
        Make("vase", "TallVase_Minimal", r => {
            Cyl(r, 0, 0.275f, 0, 0.12f, 0.55f, Charcoal, 0f, 0f, 0f, 0.6f);
            for (int i = 0; i < 3; i++) Blade(r, 0, 0.55f, 0, i * 120f, 14f, 0.55f, 0.012f, DarkWood); });

        // ---- decor: rugs ----
        Make("rug", "RugRectangle_Modern", r => {
            Box(r, 0, 0.01f, 0, 2.0f, 0.02f, 3.0f, Navy);
            Box(r, 0, 0.0135f, 0, 1.7f, 0.027f, 2.7f, Cream); });
        Make("rug", "RugWoolRound_Scandinavian", r => {
            Cyl(r, 0, 0.01f, 0, 2.0f, 0.02f, Cream);
            Cyl(r, 0, 0.0135f, 0, 1.4f, 0.027f, H("#cbbfa8"));
            Cyl(r, 0, 0.016f, 0, 0.5f, 0.032f, Cream); });
        Make("rug", "RugPlain_Minimal", r => Box(r, 0, 0.01f, 0, 2.4f, 0.02f, 1.6f, Grey));

        // ---- decor: mirrors (hang at 1.4 m, floor mirror stands) ----
        Make("mirror", "WallMirrorRound_Modern", r => {
            Cyl(r, 0, 1.4f, 0, 0.8f, 0.04f, Brass, 90f, 0f, 0f, 0.7f, 0.9f);
            Cyl(r, 0, 1.4f, 0.005f, 0.72f, 0.05f, Glass, 90f, 0f, 0f, 0.95f, 0.8f); });
        Make("mirror", "WoodFrameMirror_Scandinavian", r => {
            Box(r, 0, 1.4f, 0, 0.7f, 1.0f, 0.04f, LightWood);
            Box(r, 0, 1.4f, 0.022f, 0.6f, 0.9f, 0.012f, Glass, 0f, 0f, 0f, 0.95f, 0.8f); });
        Make("mirror", "FloorMirror_Minimal", r => {
            var tilt = new GameObject("Tilt"); tilt.transform.SetParent(r.transform, false);
            tilt.transform.localEulerAngles = new Vector3(-8f, 0f, 0f);
            Box(tilt, 0, 0.85f, 0, 0.6f, 1.7f, 0.04f, Black);
            Box(tilt, 0, 0.85f, 0.022f, 0.52f, 1.62f, 0.012f, Glass, 0f, 0f, 0f, 0.95f, 0.8f); });

        // ---- decor: bookshelves ----
        Make("bookshelf", "BookshelfTall_Modern", r => Shelf(r, 0.9f, 1.9f, 0.32f, White, White, 5, 1));
        Make("bookshelf", "BookshelfWood_Scandinavian", r => Shelf(r, 0.8f, 1.5f, 0.3f, LightWood, LightWood, 4, 2));
        Make("bookshelf", "BookshelfMetal_Industrial", r => Shelf(r, 1.0f, 1.8f, 0.3f, Black, DarkWood, 5, 3));

        // ---- decor: clocks ----
        Make("clock", "WallClock_Modern", r => {
            Cyl(r, 0, 1.8f, 0, 0.36f, 0.04f, Black, 90f);
            Cyl(r, 0, 1.8f, 0.004f, 0.31f, 0.045f, White, 90f);
            Hands(r, 0, 1.8f, 0.03f); });
        Make("clock", "WoodClock_Scandinavian", r => {
            Box(r, 0, 1.8f, 0, 0.34f, 0.34f, 0.05f, Wood);
            Cyl(r, 0, 1.8f, 0.004f, 0.28f, 0.055f, Cream, 90f);
            Hands(r, 0, 1.8f, 0.034f); });
        Make("clock", "GrandfatherClock_Industrial", r => {
            Box(r, 0, 0.1f, 0, 0.46f, 0.2f, 0.26f, DarkWood);
            Box(r, 0, 0.95f, 0, 0.36f, 1.5f, 0.22f, DarkWood);
            Box(r, 0, 1.78f, 0, 0.46f, 0.4f, 0.26f, DarkWood);
            Cyl(r, 0, 1.78f, 0.132f, 0.3f, 0.01f, Cream, 90f);
            Hands(r, 0, 1.78f, 0.14f);
            Box(r, 0, 0.95f, 0.115f, 0.26f, 1.0f, 0.01f, Glass, 0f, 0f, 0f, 0.9f);
            Cyl(r, 0, 0.62f, 0.12f, 0.12f, 0.012f, Brass, 90f, 0f, 0f, 0.7f, 0.9f); });

        // ---- decor: showpieces ----
        Make("showpiece", "AbstractSculpture_Modern", r => {
            Box(r, 0, 0.2f, 0, 0.3f, 0.4f, 0.3f, White);
            Ball(r, 0, 0.53f, 0, 0.24f, 0.24f, 0.24f, Brass, 0f, 0f, 0f, 0.8f, 0.9f);
            Ball(r, 0.05f, 0.72f, 0.02f, 0.16f, 0.16f, 0.16f, Brass, 0f, 0f, 0f, 0.8f, 0.9f);
            Ball(r, -0.03f, 0.86f, 0f, 0.1f, 0.1f, 0.1f, Brass, 0f, 0f, 0f, 0.8f, 0.9f); });
        Make("showpiece", "CandleSet_Scandinavian", r => {
            Cyl(r, 0, 0.01f, 0, 0.3f, 0.02f, Wood);
            float[] hs = { 0.12f, 0.18f, 0.09f }; float[] xs = { -0.08f, 0.02f, 0.09f }; float[] zs = { 0.02f, -0.04f, 0.05f };
            for (int i = 0; i < 3; i++) {
                Cyl(r, xs[i], 0.02f + hs[i] / 2, zs[i], 0.05f, hs[i], Cream);
                Ball(r, xs[i], 0.04f + hs[i], zs[i], 0.02f, 0.035f, 0.02f, Mustard);
            } });
        Make("showpiece", "DecorBowl_Minimal", r => {
            Cyl(r, 0, 0.01f, 0, 0.1f, 0.02f, Charcoal);
            Ball(r, 0, 0.09f, 0, 0.3f, 0.14f, 0.3f, White, 0f, 0f, 0f, 0.6f);
            Ball(r, -0.05f, 0.17f, 0.02f, 0.08f, 0.08f, 0.08f, Terracotta);
            Ball(r, 0.05f, 0.17f, -0.02f, 0.08f, 0.08f, 0.08f, Mustard);
            Ball(r, 0.0f, 0.19f, 0.05f, 0.08f, 0.08f, 0.08f, LeafGreen); });
        Make("showpiece", "Globe_Industrial", r => {
            Cyl(r, 0, 0.015f, 0, 0.2f, 0.03f, Charcoal);
            Cyl(r, 0, 0.15f, 0, 0.02f, 0.25f, Brass, 0f, 0f, 0f, 0.7f, 0.9f);
            Ball(r, 0, 0.3f, 0, 0.28f, 0.28f, 0.28f, Navy, 0f, 0f, 0f, 0.6f);
            Ball(r, 0.0f, 0.34f, 0.125f, 0.11f, 0.09f, 0.02f, LeafGreen);
            Ball(r, 0.09f, 0.26f, 0.1f, 0.07f, 0.1f, 0.02f, LeafGreen, 0f, 25f, 0f); });

        // ---- decor: coffee tables ----
        Make("coffeetable", "CoffeeTable_Modern", r => Table(r, 1.0f, 0.55f, 0.4f, Glass, Steel, false));
        Make("coffeetable", "CoffeeTable_Scandinavian", r => Table(r, 1.0f, 0.55f, 0.4f, LightWood, Wood, false));
        Make("coffeetable", "CoffeeTable_Minimal", r => Table(r, 0.8f, 0.8f, 0.38f, White, Grey, true));
        Make("coffeetable", "CoffeeTable_Industrial", r => Table(r, 1.1f, 0.6f, 0.42f, DarkWood, Black, false));

        // ---- decor: curtains ----
        Make("curtain", "CurtainLong_Modern", r => Curtain(r, Grey, Steel, 8));
        Make("curtain", "CurtainLinen_Scandinavian", r => Curtain(r, Cream, Wood, 8));
        Make("curtain", "CurtainSheer_Minimal", r => Curtain(r, White, Black, 8));

        GenerateMore();   // part 2 (DecorPrefabGenerator_More.cs)

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        string msg = "Created " + created + " prefabs, skipped " + skipped + " that already exist.\n\nNext: run the thumbnail exporter, then `npm run catalog:apply` in /server.";
        Debug.Log("[DecorPrefabGenerator] " + msg);
        EditorUtility.DisplayDialog("DimensionX", msg, "OK");
    }

    static Color LightGreyCol() { return H("#c9ccd1"); }

    // =====================================================================
    //  ENGINE
    // =====================================================================
    static string Abs(string assetPath) { return Path.GetFullPath(Path.Combine(Application.dataPath, "..", assetPath)); }

    static void Make(string folder, string file, System.Action<GameObject> build)
    {
        string dir = Root + "/" + folder;
        Directory.CreateDirectory(Abs(dir));
        string path = dir + "/" + file + ".prefab";
        if (!overwrite && File.Exists(Abs(path))) { skipped++; return; }

        var go = new GameObject(file);
        build(go);
        var rs = go.GetComponentsInChildren<Renderer>();
        if (rs.Length > 0)
        {
            Bounds b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            var bc = go.AddComponent<BoxCollider>();
            bc.center = b.center; bc.size = b.size;
        }
        PrefabUtility.SaveAsPrefabAsset(go, path);
        Object.DestroyImmediate(go);
        created++;
    }

    static Material Mat(Color c, float smooth, float metal)
    {
        string key = ColorUtility.ToHtmlStringRGB(c) + "_" + smooth.ToString("0.00").Replace('.', 'p') + "_" + metal.ToString("0.00").Replace('.', 'p');
        Material cached;
        if (mats.TryGetValue(key, out cached) && cached != null) return cached;

        string dir = Root + "/_Materials";
        Directory.CreateDirectory(Abs(dir));
        string path = dir + "/Decor_" + key + ".mat";
        Material m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null)
        {
            Shader sh = Shader.Find("Universal Render Pipeline/Lit");
            if (sh == null) sh = Shader.Find("Standard");
            m = new Material(sh);
            m.color = c;
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", smooth);
            if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", smooth);
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", metal);
            AssetDatabase.CreateAsset(m, path);
        }
        mats[key] = m;
        return m;
    }

    static void Shape(GameObject parent, PrimitiveType t, Vector3 pos, Vector3 scale, Color c, Vector3 euler, float sm, float me)
    {
        var g = GameObject.CreatePrimitive(t);
        Object.DestroyImmediate(g.GetComponent<Collider>());
        g.transform.SetParent(parent.transform, false);
        g.transform.localPosition = pos;
        g.transform.localEulerAngles = euler;
        g.transform.localScale = scale;
        g.GetComponent<Renderer>().sharedMaterial = Mat(c, sm, me);
    }

    // Box: centre (x,y,z), size (sx,sy,sz)
    static void Box(GameObject r, float x, float y, float z, float sx, float sy, float sz, Color c,
                    float rx = 0f, float ry = 0f, float rz = 0f, float sm = 0.25f, float me = 0f)
    { Shape(r, PrimitiveType.Cube, new Vector3(x, y, z), new Vector3(sx, sy, sz), c, new Vector3(rx, ry, rz), sm, me); }

    // Cyl: centre (x,y,z), diameter d, height h (axis = Y unless rotated)
    static void Cyl(GameObject r, float x, float y, float z, float d, float h, Color c,
                    float rx = 0f, float ry = 0f, float rz = 0f, float sm = 0.25f, float me = 0f)
    { Shape(r, PrimitiveType.Cylinder, new Vector3(x, y, z), new Vector3(d, h / 2f, d), c, new Vector3(rx, ry, rz), sm, me); }

    // Ball: ellipsoid with diameters (sx,sy,sz)
    static void Ball(GameObject r, float x, float y, float z, float sx, float sy, float sz, Color c,
                     float rx = 0f, float ry = 0f, float rz = 0f, float sm = 0.25f, float me = 0f)
    { Shape(r, PrimitiveType.Sphere, new Vector3(x, y, z), new Vector3(sx, sy, sz), c, new Vector3(rx, ry, rz), sm, me); }

    // A leaf / stem blade growing from (bx,by,bz), leaning `tilt` degrees toward compass angle `angle`
    static void Blade(GameObject r, float bx, float by, float bz, float angle, float tilt, float len, float w, Color c)
    {
        float a = angle * Mathf.Deg2Rad, t = tilt * Mathf.Deg2Rad, h = len / 2f;
        Box(r, bx + Mathf.Sin(a) * Mathf.Sin(t) * h, by + Mathf.Cos(t) * h, bz + Mathf.Cos(a) * Mathf.Sin(t) * h,
            w, len, 0.012f, c, tilt, angle, 0f);
    }

    // =====================================================================
    //  BUILDERS
    // =====================================================================
    static void Bed(GameObject r, float w, float l, Color frame, Color sheet, Color pillow, float headH, bool legs)
    {
        float lift = legs ? 0.18f : 0f;
        if (legs)
            foreach (float sx in new[] { -1f, 1f })
                foreach (float sz in new[] { -1f, 1f })
                    Cyl(r, sx * (w / 2 - 0.05f), 0.09f, sz * (l / 2 - 0.05f), 0.07f, 0.18f, frame);
        Box(r, 0, lift + 0.12f, 0, w, 0.24f, l, frame);
        Box(r, 0, lift + 0.35f, 0.03f, w - 0.08f, 0.22f, l - 0.12f, sheet);
        Box(r, 0, lift + 0.47f, l * 0.12f, w - 0.06f, 0.04f, l * 0.55f, Dk(sheet, 0.15f));
        Box(r, 0, headH / 2, -l / 2 + 0.04f, w, headH, 0.08f, frame);
        Box(r, -w * 0.22f, lift + 0.52f, -l / 2 + 0.3f, w * 0.36f, 0.12f, 0.35f, pillow, 8f);
        Box(r, w * 0.22f, lift + 0.52f, -l / 2 + 0.3f, w * 0.36f, 0.12f, 0.35f, pillow, 8f);
    }

    static void Sofa(GameObject r, float w, float d, Color body, Color cushion, bool lshape)
    {
        foreach (float sx in new[] { -1f, 1f })
            foreach (float sz in new[] { -1f, 1f })
                Cyl(r, sx * (w / 2 - 0.08f), 0.04f, sz * (d / 2 - 0.08f), 0.05f, 0.08f, Black);
        Box(r, 0, 0.26f, 0, w, 0.36f, d, body);
        Box(r, 0, 0.7f, -d / 2 + 0.1f, w, 0.52f, 0.2f, body);
        foreach (float s in new[] { -1f, 1f }) Box(r, s * (w / 2 - 0.08f), 0.5f, 0, 0.16f, 0.4f, d, body);
        float cw = (w - 0.32f) / 2f - 0.01f;
        foreach (float s in new[] { -1f, 1f })
        {
            Box(r, s * (cw / 2 + 0.005f), 0.5f, 0.06f, cw, 0.14f, d - 0.3f, cushion);
            Box(r, s * (cw / 2 + 0.005f), 0.72f, -d / 2 + 0.3f, cw, 0.4f, 0.12f, cushion, -12f);
        }
        if (lshape)
        {
            Box(r, w / 2 - 0.5f, 0.26f, d / 2 + 0.45f, 1.0f, 0.36f, 0.9f, body);
            Box(r, w / 2 - 0.5f, 0.5f, d / 2 + 0.45f, 0.88f, 0.14f, 0.8f, cushion);
        }
    }

    static void Chair(GameObject r, Color seat, Color frame, float seatH, float backH)
    {
        foreach (float sx in new[] { -1f, 1f })
            foreach (float sz in new[] { -1f, 1f })
                Cyl(r, sx * 0.19f, seatH / 2, sz * 0.19f, 0.04f, seatH, frame);
        Box(r, 0, seatH + 0.02f, 0, 0.46f, 0.05f, 0.46f, seat);
        Box(r, 0, seatH + 0.045f + backH / 2, -0.21f, 0.44f, backH, 0.04f, seat);
    }

    static void Desk(GameObject r, float w, Color top, Color leg, bool drawers, bool shelf)
    {
        Box(r, 0, 0.74f, 0, w, 0.04f, 0.65f, top);
        foreach (float sx in new[] { -1f, 1f })
            foreach (float sz in new[] { -1f, 1f })
                Box(r, sx * (w / 2 - 0.04f), 0.36f, sz * 0.28f, 0.05f, 0.72f, 0.05f, leg);
        if (drawers)
        {
            Box(r, w / 2 - 0.25f, 0.5f, 0, 0.4f, 0.4f, 0.55f, Dk(top, 0.1f));
            Box(r, w / 2 - 0.25f, 0.58f, 0.28f, 0.36f, 0.16f, 0.01f, top);
            Box(r, w / 2 - 0.25f, 0.4f, 0.28f, 0.36f, 0.16f, 0.01f, top);
            Box(r, w / 2 - 0.25f, 0.58f, 0.29f, 0.1f, 0.012f, 0.012f, Steel, 0f, 0f, 0f, 0.6f, 0.8f);
            Box(r, w / 2 - 0.25f, 0.4f, 0.29f, 0.1f, 0.012f, 0.012f, Steel, 0f, 0f, 0f, 0.6f, 0.8f);
        }
        if (shelf) Box(r, 0, 0.2f, 0, w - 0.1f, 0.03f, 0.55f, leg);
    }

    static void Table(GameObject r, float w, float l, float h, Color top, Color leg, bool round)
    {
        if (round)
        {
            Cyl(r, 0, h - 0.02f, 0, w, 0.04f, top);
            Cyl(r, 0, h / 2, 0, 0.08f, h - 0.04f, leg);
            Cyl(r, 0, 0.015f, 0, w * 0.5f, 0.03f, leg);
        }
        else
        {
            Box(r, 0, h - 0.02f, 0, w, 0.04f, l, top, 0f, 0f, 0f, top == Glass ? 0.9f : 0.25f);
            foreach (float sx in new[] { -1f, 1f })
                foreach (float sz in new[] { -1f, 1f })
                    Box(r, sx * (w / 2 - 0.06f), (h - 0.04f) / 2, sz * (l / 2 - 0.06f), 0.05f, h - 0.04f, 0.05f, leg);
        }
    }

    static void Wardrobe(GameObject r, float w, Color body, Color accent, bool sliding)
    {
        Box(r, 0, 1.0f, 0, w, 2.0f, 0.6f, body);
        if (sliding)
        {
            Box(r, -w / 4f, 1.04f, 0.31f, w / 2 - 0.03f, 1.9f, 0.02f, accent);
            Box(r, w / 4f, 1.04f, 0.33f, w / 2 - 0.03f, 1.9f, 0.02f, Dk(accent, 0.08f));
            Box(r, -0.04f, 1.0f, 0.355f, 0.02f, 0.3f, 0.02f, Steel, 0f, 0f, 0f, 0.6f, 0.8f);
            Box(r, 0.04f, 1.0f, 0.355f, 0.02f, 0.3f, 0.02f, Steel, 0f, 0f, 0f, 0.6f, 0.8f);
        }
        else
        {
            Box(r, -w / 4f, 1.04f, 0.305f, w / 2 - 0.03f, 1.9f, 0.012f, accent);
            Box(r, w / 4f, 1.04f, 0.305f, w / 2 - 0.03f, 1.9f, 0.012f, accent);
            Box(r, -0.05f, 1.0f, 0.325f, 0.02f, 0.35f, 0.03f, Steel, 0f, 0f, 0f, 0.6f, 0.8f);
            Box(r, 0.05f, 1.0f, 0.325f, 0.02f, 0.35f, 0.03f, Steel, 0f, 0f, 0f, 0.6f, 0.8f);
        }
    }

    static void DrawerUnit(GameObject r, float w, Color body, Color front, Color knob)
    {
        Box(r, 0, 0.4f, 0, w, 0.8f, 0.45f, body);
        for (int i = 0; i < 3; i++)
        {
            float y = 0.16f + i * 0.25f;
            Box(r, 0, y, 0.23f, w - 0.06f, 0.22f, 0.02f, front);
            Cyl(r, 0, y, 0.255f, 0.03f, 0.03f, knob, 90f, 0f, 0f, 0.6f, 0.8f);
        }
    }

    static void TvWall(GameObject r)
    {
        Box(r, 0, 1.4f, 0, 1.2f, 0.7f, 0.035f, Black);
        Box(r, 0, 1.4f, 0.019f, 1.15f, 0.65f, 0.004f, H("#0b1220"), 0f, 0f, 0f, 0.9f, 0.3f);
        Box(r, 0, 1.4f, -0.04f, 0.3f, 0.2f, 0.04f, Charcoal);
    }

    static void Pot(GameObject r, Color c, float d, float h)
    {
        Cyl(r, 0, h / 2, 0, d, h, c);
        Cyl(r, 0, h + 0.005f, 0, d * 0.88f, 0.012f, H("#3b2a20"));
    }

    static void PlantBushy(GameObject r)
    {
        Pot(r, White, 0.34f, 0.36f);
        Cyl(r, 0, 0.55f, 0, 0.04f, 0.4f, DarkGreen);
        for (int i = 0; i < 9; i++)
        {
            float a = i * 40f * Mathf.Deg2Rad, rad = 0.12f + (i % 3) * 0.03f;
            Ball(r, Mathf.Cos(a) * rad, 0.55f + (i % 4) * 0.13f, Mathf.Sin(a) * rad, 0.26f, 0.26f, 0.26f, i % 2 == 0 ? Green : LeafGreen);
        }
    }

    static void PlantFiddle(GameObject r)
    {
        Pot(r, Cream, 0.3f, 0.3f);
        Cyl(r, 0, 0.7f, 0, 0.035f, 0.8f, DarkWood);
        for (int i = 0; i < 10; i++)
        {
            float a = i * 137f * Mathf.Deg2Rad, y = 0.6f + i * 0.075f;
            Ball(r, Mathf.Cos(a) * 0.14f, y, Mathf.Sin(a) * 0.14f, 0.24f, 0.03f, 0.17f, i % 2 == 0 ? Green : DarkGreen, 0f, i * 137f, 15f);
        }
    }

    static void PlantSnake(GameObject r)
    {
        Pot(r, Grey, 0.26f, 0.28f);
        float[] lens = { 0.7f, 0.9f, 0.6f, 0.8f, 0.55f, 0.75f, 0.65f };
        for (int i = 0; i < 7; i++)
        {
            float ang = i * 51f, a = ang * Mathf.Deg2Rad;
            Blade(r, Mathf.Sin(a) * 0.04f, 0.28f, Mathf.Cos(a) * 0.04f, ang, 4f + (i % 3) * 5f, lens[i], 0.07f, i % 2 == 0 ? DarkGreen : Green);
        }
    }

    static void PlantSucculent(GameObject r)
    {
        Pot(r, Concrete, 0.24f, 0.18f);
        for (int j = 0; j < 2; j++)
            for (int i = 0; i < 8; i++)
                Blade(r, 0, 0.18f, 0, i * 45f + j * 22f, 35f + j * 25f, 0.13f - j * 0.02f, 0.06f, j == 0 ? Teal : LeafGreen);
    }

    static void Frame(GameObject r, float w, float h, Color frame, Color canvas)
    {
        Box(r, 0, 1.5f, 0, w, h, 0.04f, frame);
        Box(r, 0, 1.5f, 0.02f, w - 0.08f, h - 0.08f, 0.012f, canvas);
    }

    static void Shelf(GameObject r, float w, float h, float d, Color frame, Color shelf, int bays, int seed)
    {
        Box(r, -w / 2 + 0.015f, h / 2, 0, 0.03f, h, d, frame);
        Box(r, w / 2 - 0.015f, h / 2, 0, 0.03f, h, d, frame);
        Box(r, 0, h / 2, -d / 2 + 0.008f, w, h, 0.016f, frame);
        float bay = (h - 0.03f) / bays;
        for (int i = 0; i <= bays; i++) Box(r, 0, 0.015f + i * bay, 0, w - 0.06f, 0.03f, d, shelf);
        var rnd = new System.Random(seed);
        for (int i = 0; i < bays; i++)
        {
            float y0 = 0.03f + i * bay, x = -w / 2 + 0.05f;
            while (x < w / 2 - 0.08f)
            {
                if (rnd.NextDouble() < 0.12) { x += 0.05f; continue; }
                float bw = 0.025f + (float)rnd.NextDouble() * 0.03f;
                float bh = (bay - 0.03f) * (0.6f + (float)rnd.NextDouble() * 0.38f);
                Box(r, x + bw / 2, y0 + bh / 2, 0, bw, bh, d * 0.7f, BookCols[rnd.Next(BookCols.Length)]);
                x += bw + 0.002f;
            }
        }
    }

    static void Hands(GameObject r, float x, float y, float z)
    {
        Box(r, x, y + 0.06f, z, 0.012f, 0.12f, 0.006f, Black);
        Box(r, x + 0.04f, y, z, 0.08f, 0.014f, 0.006f, Black);
        Ball(r, x, y, z, 0.02f, 0.02f, 0.01f, Black);
    }

    static void Curtain(GameObject r, Color cloth, Color rod, int folds)
    {
        Cyl(r, 0, 2.3f, 0, 0.025f, 1.8f, rod, 0f, 0f, 90f, 0.6f, 0.8f);
        for (int i = 0; i < folds; i++)
            Box(r, -0.77f + i * 0.22f, 1.15f, (i % 2) * 0.035f, 0.2f, 2.2f, 0.02f, i % 2 == 0 ? cloth : Dk(cloth, 0.06f));
    }
}
#endif
