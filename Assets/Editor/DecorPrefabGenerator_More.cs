// Part 2 of DecorPrefabGenerator: three more styles for EVERY furniture / decor type (69 prefabs).
// Keep this file next to DecorPrefabGenerator.cs in Assets/Editor/. It runs automatically with the same menu item.
#if UNITY_EDITOR
using UnityEngine;

public static partial class DecorPrefabGenerator
{
    static Color Wine, Sage, Rattan;

    static void GenerateMore()
    {
        Wine = H("#6d1f2f"); Sage = H("#8fa98c"); Rattan = H("#c9a36a");

        // ---------------- Beds: Classic / Luxury / Boho ----------------
        Make("Bed", "Bed_Classic", r => {
            Bed(r, 1.6f, 2.0f, DarkWood, Cream, White, 1.3f, true);
            foreach (float sx in new[] { -1f, 1f }) foreach (float sz in new[] { -1f, 1f })
                Cyl(r, sx * 0.75f, 0.9f, sz * 0.95f, 0.07f, 1.8f, DarkWood);
            Box(r, -0.75f, 1.8f, 0, 0.05f, 0.05f, 1.95f, DarkWood); Box(r, 0.75f, 1.8f, 0, 0.05f, 0.05f, 1.95f, DarkWood);
            Box(r, 0, 1.8f, -0.95f, 1.55f, 0.05f, 0.05f, DarkWood); Box(r, 0, 1.8f, 0.95f, 1.55f, 0.05f, 0.05f, DarkWood); });
        Make("Bed", "Bed_Luxury", r => {
            Bed(r, 1.8f, 2.1f, Navy, H("#d9d4c7"), White, 1.4f, true);
            Box(r, 0, 0.9f, -0.96f, 1.6f, 0.9f, 0.08f, Dk(Navy, 0.15f));
            Box(r, 0, 1.42f, -1.01f, 1.8f, 0.04f, 0.1f, Brass, 0f, 0f, 0f, 0.7f, 0.9f); });
        Make("Bed", "Bed_Boho", r => {
            Bed(r, 1.5f, 2.0f, Rattan, Cream, Terracotta, 0.5f, false);
            Cyl(r, 0, 0.95f, -0.97f, 1.1f, 0.05f, Rattan, 90f); });

        // ---------------- Sofas: Classic / Luxury / Compact ----------------
        Make("Sofa", "Sofa_Classic", r => {
            Sofa(r, 2.1f, 0.95f, Wine, Dk(Wine, 0.1f), false);
            foreach (float s in new[] { -1f, 1f }) Cyl(r, s * (1.05f - 0.08f), 0.72f, 0, 0.2f, 0.95f, Wine, 90f); });
        Make("Sofa", "Sofa_Luxury", r => {
            Sofa(r, 2.4f, 1.0f, H("#2d5a47"), H("#2a5143"), false);
            Box(r, -0.7f, 0.68f, -0.2f, 0.4f, 0.4f, 0.12f, Mustard, -15f, 15f, 0f);
            Box(r, 0.7f, 0.68f, -0.2f, 0.4f, 0.4f, 0.12f, Terracotta, -15f, -15f, 0f); });
        Make("Sofa", "Sofa_Compact", r => Sofa(r, 1.5f, 0.8f, Grey, Dk(Grey, 0.1f), false));

        // ---------------- Chairs: Classic / Rustic / Boho ----------------
        Make("chair", "Chair_Classic", r => {
            Chair(r, Cream, DarkWood, 0.46f, 0.55f);
            Box(r, 0, 1.08f, -0.21f, 0.5f, 0.05f, 0.05f, DarkWood); });
        Make("chair", "Chair_Rustic", r => Chair(r, Wood, DarkWood, 0.46f, 0.45f));
        Make("chair", "Chair_Boho", r => {
            Chair(r, Rattan, Wood, 0.45f, 0.02f);
            Cyl(r, 0, 0.78f, -0.21f, 0.5f, 0.03f, Rattan, 90f); });

        // ---------------- Desks: Classic / Rustic / Compact ----------------
        Make("Desk", "Desk_Classic", r => {
            Desk(r, 1.4f, DarkWood, DarkWood, true, false);
            Box(r, -0.45f, 0.5f, 0, 0.4f, 0.4f, 0.55f, Dk(DarkWood, 0.1f)); });
        Make("Desk", "Desk_Rustic", r => Desk(r, 1.5f, Wood, DarkWood, false, true));
        Make("Desk", "Desk_Compact", r => Desk(r, 0.9f, White, Charcoal, false, false));

        // ---------------- Tables: Classic / Rustic / Luxury ----------------
        Make("table", "Table_Classic", r => Table(r, 1.8f, 1.0f, 0.75f, DarkWood, DarkWood, false));
        Make("table", "Table_Rustic", r => {
            Table(r, 2.0f, 0.9f, 0.76f, Wood, DarkWood, false);
            for (int i = -1; i <= 1; i++) Box(r, 0, 0.7605f, i * 0.225f, 2.0f, 0.002f, 0.006f, Dk(Wood, 0.35f)); });
        Make("table", "Table_Luxury", r => Table(r, 1.2f, 1.2f, 0.75f, White, Brass, true));

        // ---------------- Wardrobes: Classic / Rustic / Luxury ----------------
        Make("Wadrobe", "Wardrobe_Classic", r => {
            Wardrobe(r, 1.2f, DarkWood, Wood, false);
            Box(r, 0, 2.04f, 0.02f, 1.28f, 0.08f, 0.66f, DarkWood); });
        Make("Wadrobe", "Wardrobe_Rustic", r => Wardrobe(r, 1.1f, Wood, DarkWood, false));
        Make("Wadrobe", "Wardrobe_Luxury", r => Wardrobe(r, 1.4f, White, Glass, false));

        // ---------------- Sinks: Industrial / Classic / Luxury ----------------
        Make("sink", "Sink_Industrial", r => SinkVanity(r, Black, DarkWood, Steel));
        Make("sink", "Sink_Classic", r => SinkPedestal(r));
        Make("sink", "Sink_Luxury", r => SinkVanity(r, White, Grey, Brass));

        // ---------------- Stoves: Industrial / Classic / Compact ----------------
        Make("stove", "Stove_Industrial", r => Stove(r, 0.9f, Steel, Black, 4, true));
        Make("stove", "Stove_Classic", r => Stove(r, 0.75f, Cream, Brass, 4, false));
        Make("stove", "Stove_Compact", r => Stove(r, 0.5f, White, Steel, 2, false));

        // ---------------- Showers: Scandinavian / Minimal / Industrial ----------------
        Make("shower", "Shower_Scandinavian", r => Shower(r, Wood, 1));
        Make("shower", "Shower_Minimal", r => Shower(r, Steel, 0));
        Make("shower", "Shower_Industrial", r => Shower(r, Black, 2));

        // ---------------- Toilets: Classic / Industrial / Compact ----------------
        Make("toilet", "Toilet_Classic", r => Toilet(r, White, 0));
        Make("toilet", "Toilet_Industrial", r => Toilet(r, Charcoal, 1));
        Make("toilet", "Toilet_Compact", r => Toilet(r, White, 2));

        // ---------------- TVs: Industrial / Classic / Compact ----------------
        Make("tv", "TV_Industrial", r => TvStand(r, 1.4f, DarkWood, Black, 0.7f));
        Make("tv", "TV_Classic", r => TvCrt(r));
        Make("tv", "TV_Compact", r => TvStand(r, 0.8f, White, Grey, 0.4f));

        // ---------------- Drawers: Classic / Rustic / Luxury ----------------
        Make("drawer", "Drawer_Classic", r => DrawerUnit(r, 0.9f, DarkWood, Wood, Brass));
        Make("drawer", "Drawer_Rustic", r => DrawerUnit(r, 0.8f, Wood, LightWood, Black));
        Make("drawer", "Drawer_Luxury", r => DrawerUnit(r, 1.0f, White, Cream, Brass));

        // ---------------- Lamps: Classic / Luxury / Rustic ----------------
        Make("lamp", "Lamp_Classic", r => LampTable(r, Navy, Cream));
        Make("lamp", "Lamp_Luxury", r => LampFloor(r, Brass, Cream, 1.5f));
        Make("lamp", "Lamp_Rustic", r => LampTripod(r, Wood, Cream));

        // ---------------- Plants: Rustic / Luxury / Classic ----------------
        Make("plant", "Cactus_Rustic", r => Cactus(r));
        Make("plant", "Palm_Luxury", r => {
            Pot(r, Brass, 0.36f, 0.4f);
            Cyl(r, 0, 1.0f, 0, 0.06f, 1.2f, DarkWood);
            for (int i = 0; i < 9; i++) Blade(r, 0, 1.6f, 0, i * 40f, 50f + (i % 2) * 10f, 0.8f, 0.16f, i % 2 == 0 ? Green : LeafGreen); });
        Make("plant", "Fern_Classic", r => {
            Pot(r, Terracotta, 0.32f, 0.28f);
            for (int j = 0; j < 2; j++) for (int i = 0; i < 10; i++)
                Blade(r, 0, 0.28f, 0, i * 36f + j * 18f, 30f + j * 25f, 0.5f - j * 0.1f, 0.09f, j == 0 ? DarkGreen : LeafGreen); });

        // ---------------- Paintings: Classic / Rustic / Boho ----------------
        Make("painting", "OrnatePortrait_Classic", r => {
            Box(r, 0, 1.5f, -0.006f, 1.1f, 0.85f, 0.04f, Brass, 0f, 0f, 0f, 0.6f, 0.8f);
            Frame(r, 1.0f, 0.75f, Dk(Brass, 0.3f), H("#c9d6c0"));
            Ball(r, 0, 1.55f, 0.034f, 0.28f, 0.34f, 0.01f, Cream);
            Box(r, 0, 1.27f, 0.034f, 0.4f, 0.28f, 0.01f, Wine); });
        Make("painting", "WordBoard_Rustic", r => {
            Frame(r, 0.9f, 0.6f, Wood, Cream);
            for (int i = 0; i < 3; i++) Box(r, 0, 1.58f - i * 0.1f, 0.034f, 0.5f - i * 0.06f, 0.025f, 0.01f, Charcoal); });
        Make("painting", "SunArt_Boho", r => {
            Cyl(r, 0, 1.5f, 0, 0.8f, 0.03f, Cream, 90f);
            Cyl(r, 0, 1.5f, 0.01f, 0.6f, 0.03f, Terracotta, 90f);
            Cyl(r, 0, 1.5f, 0.02f, 0.45f, 0.03f, Mustard, 90f);
            Cyl(r, 0, 1.5f, 0.03f, 0.3f, 0.03f, Sage, 90f);
            Cyl(r, 0, 1.5f, 0.04f, 0.15f, 0.03f, Cream, 90f); });

        // ---------------- Vases: Classic / Industrial / Luxury ----------------
        Make("vase", "Urn_Classic", r => {
            Cyl(r, 0, 0.03f, 0, 0.12f, 0.06f, Navy);
            Ball(r, 0, 0.2f, 0, 0.24f, 0.3f, 0.24f, Navy, 0f, 0f, 0f, 0.7f);
            Cyl(r, 0, 0.38f, 0, 0.09f, 0.1f, Navy);
            Cyl(r, 0, 0.44f, 0, 0.14f, 0.02f, Brass, 0f, 0f, 0f, 0.7f, 0.9f);
            Ball(r, -0.13f, 0.28f, 0, 0.05f, 0.1f, 0.03f, Brass); Ball(r, 0.13f, 0.28f, 0, 0.05f, 0.1f, 0.03f, Brass); });
        Make("vase", "MetalVase_Industrial", r => {
            Cyl(r, 0, 0.175f, 0, 0.14f, 0.35f, Steel, 0f, 0f, 0f, 0.6f, 0.9f);
            Cyl(r, 0, 0.36f, 0, 0.16f, 0.02f, Charcoal); });
        Make("vase", "GoldVase_Luxury", r => {
            Ball(r, 0, 0.14f, 0, 0.22f, 0.26f, 0.22f, Brass, 0f, 0f, 0f, 0.85f, 0.95f);
            Cyl(r, 0, 0.36f, 0, 0.06f, 0.3f, Brass, 0f, 0f, 0f, 0.85f, 0.95f);
            Cyl(r, 0, 0.52f, 0, 0.12f, 0.02f, Brass, 0f, 0f, 0f, 0.85f, 0.95f); });

        // ---------------- Rugs: Classic / Boho / Industrial ----------------
        Make("rug", "RugPersian_Classic", r => {
            Box(r, 0, 0.01f, 0, 2.2f, 0.02f, 3.2f, Wine);
            Box(r, 0, 0.0125f, 0, 1.9f, 0.025f, 2.9f, Cream);
            Box(r, 0, 0.015f, 0, 1.7f, 0.03f, 2.7f, Wine);
            Cyl(r, 0, 0.017f, 0, 0.9f, 0.034f, Brass); });
        Make("rug", "RugStripes_Boho", r => {
            Color[] cs = { Terracotta, Cream, Mustard, Sage };
            for (int i = 0; i < 7; i++) Box(r, -0.9f + i * 0.3f, 0.01f, 0, 0.3f, 0.02f, 2.4f, cs[i % 4]); });
        Make("rug", "RugSlate_Industrial", r => {
            Box(r, 0, 0.01f, 0, 2.4f, 0.02f, 1.7f, Charcoal);
            Box(r, 0, 0.0125f, 0, 2.2f, 0.025f, 1.5f, Dk(Charcoal, 0.3f)); });

        // ---------------- Mirrors: Classic / Industrial / Luxury ----------------
        Make("mirror", "ArchMirror_Classic", r => {
            Box(r, 0, 1.3f, 0, 0.7f, 1.0f, 0.04f, Brass, 0f, 0f, 0f, 0.6f, 0.8f);
            Cyl(r, 0, 1.8f, 0, 0.7f, 0.038f, Brass, 90f, 0f, 0f, 0.6f, 0.8f);
            Box(r, 0, 1.3f, 0.022f, 0.58f, 0.88f, 0.012f, Glass, 0f, 0f, 0f, 0.95f, 0.8f);
            Cyl(r, 0, 1.74f, 0.022f, 0.58f, 0.012f, Glass, 90f, 0f, 0f, 0.95f, 0.8f); });
        Make("mirror", "GridMirror_Industrial", r => {
            Box(r, 0, 1.4f, 0, 0.7f, 1.0f, 0.04f, Black);
            Box(r, 0, 1.4f, 0.022f, 0.62f, 0.92f, 0.012f, Glass, 0f, 0f, 0f, 0.95f, 0.8f);
            Box(r, 0, 1.4f, 0.03f, 0.012f, 0.92f, 0.01f, Black);
            Box(r, 0, 1.4f, 0.03f, 0.62f, 0.012f, 0.01f, Black); });
        Make("mirror", "Sunburst_Luxury", r => {
            Cyl(r, 0, 1.5f, -0.005f, 0.56f, 0.03f, Brass, 90f, 0f, 0f, 0.8f, 0.9f);
            Cyl(r, 0, 1.5f, 0, 0.5f, 0.03f, Glass, 90f, 0f, 0f, 0.95f, 0.8f);
            for (int i = 0; i < 16; i++) {
                float a = i * 22.5f * Mathf.Deg2Rad;
                Box(r, Mathf.Cos(a) * 0.4f, 1.5f + Mathf.Sin(a) * 0.4f, 0, 0.025f, 0.22f, 0.02f, Brass, 0f, 0f, i * 22.5f - 90f, 0.7f, 0.9f);
            } });

        // ---------------- Bookshelves: Classic / Rustic / Minimal ----------------
        Make("bookshelf", "Bookcase_Classic", r => Shelf(r, 1.0f, 2.0f, 0.35f, DarkWood, DarkWood, 5, 4));
        Make("bookshelf", "Bookcase_Rustic", r => Shelf(r, 0.9f, 1.6f, 0.3f, Wood, Wood, 4, 5));
        Make("bookshelf", "LowShelf_Minimal", r => Shelf(r, 1.4f, 0.8f, 0.3f, White, White, 2, 6));

        // ---------------- Clocks: Classic / Minimal / Luxury ----------------
        Make("clock", "WallClock_Classic", r => {
            Cyl(r, 0, 1.8f, 0, 0.44f, 0.05f, Brass, 90f, 0f, 0f, 0.6f, 0.8f);
            Cyl(r, 0, 1.8f, 0.004f, 0.36f, 0.055f, Cream, 90f);
            Hands(r, 0, 1.8f, 0.034f);
            Box(r, 0, 1.5f, 0, 0.012f, 0.2f, 0.01f, Brass);
            Cyl(r, 0, 1.38f, 0, 0.1f, 0.012f, Brass, 90f, 0f, 0f, 0.7f, 0.9f); });
        Make("clock", "WallClock_Minimal", r => {
            Cyl(r, 0, 1.8f, 0, 0.32f, 0.02f, Black, 90f);
            Cyl(r, 0, 1.8f, 0.002f, 0.29f, 0.022f, White, 90f);
            Hands(r, 0, 1.8f, 0.02f); });
        Make("clock", "WallClock_Luxury", r => {
            Cyl(r, 0, 1.8f, 0, 0.3f, 0.03f, Brass, 90f, 0f, 0f, 0.8f, 0.9f);
            for (int i = 0; i < 12; i++) {
                float a = i * 30f * Mathf.Deg2Rad;
                Box(r, Mathf.Cos(a) * 0.26f, 1.8f + Mathf.Sin(a) * 0.26f, 0, 0.02f, 0.18f, 0.015f, Brass, 0f, 0f, i * 30f - 90f, 0.8f, 0.9f);
            }
            Cyl(r, 0, 1.8f, 0.004f, 0.26f, 0.034f, Cream, 90f);
            Hands(r, 0, 1.8f, 0.025f); });

        // ---------------- Showpieces: Classic / Rustic / Boho ----------------
        Make("showpiece", "Statue_Classic", r => {
            Box(r, 0, 0.15f, 0, 0.24f, 0.3f, 0.24f, White);
            Box(r, 0, 0.31f, 0, 0.28f, 0.02f, 0.28f, Cream);
            Cyl(r, 0, 0.42f, 0, 0.16f, 0.2f, Cream);
            Ball(r, 0, 0.58f, 0, 0.14f, 0.17f, 0.14f, Cream); });
        Make("showpiece", "LogStack_Rustic", r => {
            Cyl(r, 0, 0.06f, -0.07f, 0.12f, 0.35f, Wood, 0f, 0f, 90f);
            Cyl(r, 0, 0.06f, 0.07f, 0.12f, 0.35f, Wood, 0f, 0f, 90f);
            Cyl(r, 0, 0.17f, 0, 0.12f, 0.35f, DarkWood, 0f, 0f, 90f); });
        Make("showpiece", "Basket_Boho", r => {
            Cyl(r, 0, 0.11f, 0, 0.3f, 0.22f, Rattan);
            Cyl(r, 0, 0.225f, 0, 0.32f, 0.02f, Wood);
            for (int i = 0; i < 6; i++) Blade(r, 0, 0.22f, 0, i * 60f, 20f, 0.35f, 0.05f, LeafGreen); });

        // ---------------- Curtains: Classic / Luxury / Boho ----------------
        Make("curtain", "Curtain_Classic", r => {
            Curtain(r, Wine, Brass, 8);
            Ball(r, -0.92f, 2.3f, 0, 0.06f, 0.06f, 0.06f, Brass); Ball(r, 0.92f, 2.3f, 0, 0.06f, 0.06f, 0.06f, Brass); });
        Make("curtain", "Curtain_Luxury", r => {
            Curtain(r, Navy, Brass, 8);
            Ball(r, -0.92f, 2.3f, 0, 0.06f, 0.06f, 0.06f, Brass); Ball(r, 0.92f, 2.3f, 0, 0.06f, 0.06f, 0.06f, Brass); });
        Make("curtain", "Curtain_Boho", r => Curtain(r, Terracotta, Wood, 8));

        // ---------------- Coffee tables: Classic / Rustic / Luxury ----------------
        Make("coffeetable", "CoffeeTable_Classic", r => Table(r, 1.1f, 0.6f, 0.42f, DarkWood, DarkWood, false));
        Make("coffeetable", "CoffeeTable_Rustic", r => {
            Table(r, 1.1f, 0.6f, 0.42f, Wood, DarkWood, false);
            Box(r, 0, 0.12f, 0, 1.0f, 0.03f, 0.5f, DarkWood); });
        Make("coffeetable", "CoffeeTable_Luxury", r => Table(r, 0.9f, 0.9f, 0.4f, White, Brass, true));
    }

    // =====================================================================
    //  EXTRA BUILDERS
    // =====================================================================
    static void SinkPedestal(GameObject r)
    {
        Cyl(r, 0, 0.4f, -0.05f, 0.16f, 0.8f, White, 0f, 0f, 0f, 0.6f);
        Box(r, 0, 0.82f, 0, 0.6f, 0.14f, 0.45f, White, 0f, 0f, 0f, 0.6f);
        Box(r, 0, 0.895f, 0.02f, 0.46f, 0.02f, 0.32f, Dk(White, 0.12f));
        Cyl(r, 0, 0.97f, -0.18f, 0.03f, 0.14f, Steel, 0f, 0f, 0f, 0.7f, 0.9f);
        Box(r, 0, 1.04f, -0.12f, 0.03f, 0.03f, 0.14f, Steel, 0f, 0f, 0f, 0.7f, 0.9f);
    }

    static void SinkVanity(GameObject r, Color body, Color top, Color tap)
    {
        Box(r, 0, 0.4f, 0, 0.9f, 0.8f, 0.5f, body);
        Box(r, -0.225f, 0.4f, 0.255f, 0.42f, 0.7f, 0.01f, Dk(body, 0.08f));
        Box(r, 0.225f, 0.4f, 0.255f, 0.42f, 0.7f, 0.01f, Dk(body, 0.08f));
        Box(r, 0, 0.82f, 0, 0.96f, 0.04f, 0.54f, top, 0f, 0f, 0f, 0.5f);
        Ball(r, 0, 0.92f, 0.02f, 0.4f, 0.16f, 0.3f, White, 0f, 0f, 0f, 0.7f);
        Cyl(r, 0, 1.0f, -0.18f, 0.03f, 0.22f, tap, 0f, 0f, 0f, 0.7f, 0.9f);
        Box(r, 0, 1.1f, -0.1f, 0.03f, 0.03f, 0.16f, tap, 0f, 0f, 0f, 0.7f, 0.9f);
    }

    static void Stove(GameObject r, float w, Color body, Color knob, int burners, bool hood)
    {
        Box(r, 0, 0.45f, 0, w, 0.9f, 0.6f, body, 0f, 0f, 0f, 0.5f, 0.3f);
        Box(r, 0, 0.905f, 0, w, 0.02f, 0.6f, Black, 0f, 0f, 0f, 0.7f);
        float bx = w * 0.22f;
        if (burners == 4)
            foreach (float sx in new[] { -1f, 1f }) foreach (float sz in new[] { -1f, 1f })
            { Cyl(r, sx * bx, 0.92f, sz * 0.16f, 0.16f, 0.02f, Charcoal); Cyl(r, sx * bx, 0.935f, sz * 0.16f, 0.06f, 0.015f, Black); }
        else
            foreach (float sx in new[] { -1f, 1f })
            { Cyl(r, sx * w * 0.25f, 0.92f, 0, 0.16f, 0.02f, Charcoal); Cyl(r, sx * w * 0.25f, 0.935f, 0, 0.06f, 0.015f, Black); }
        Box(r, 0, 0.4f, 0.305f, w - 0.1f, 0.5f, 0.015f, Black, 0f, 0f, 0f, 0.9f);
        Box(r, 0, 0.42f, 0.314f, w - 0.25f, 0.3f, 0.005f, H("#222a30"), 0f, 0f, 0f, 0.9f);
        Box(r, 0, 0.68f, 0.33f, w - 0.2f, 0.02f, 0.02f, Steel, 0f, 0f, 0f, 0.7f, 0.9f);
        for (int i = 0; i < 4; i++) Cyl(r, -w * 0.3f + i * w * 0.2f, 0.82f, 0.31f, 0.04f, 0.03f, knob, 90f);
        if (hood)
        {
            Box(r, 0, 1.75f, -0.1f, w, 0.35f, 0.45f, body, 0f, 0f, 0f, 0.5f, 0.3f);
            Box(r, 0, 2.15f, -0.2f, 0.3f, 0.5f, 0.25f, body, 0f, 0f, 0f, 0.5f, 0.3f);
        }
    }

    // kind: 0 = open frame, 1 = frame + wooden half wall, 2 = frame + curtain
    static void Shower(GameObject r, Color frame, int kind)
    {
        Box(r, 0, 0.04f, 0, 0.9f, 0.08f, 0.9f, White, 0f, 0f, 0f, 0.6f);
        foreach (float sx in new[] { -1f, 1f }) foreach (float sz in new[] { -1f, 1f })
            Cyl(r, sx * 0.43f, 1.0f, sz * 0.43f, 0.03f, 2.0f, frame, 0f, 0f, 0f, 0.6f, 0.8f);
        Box(r, 0, 2.0f, -0.43f, 0.86f, 0.03f, 0.03f, frame, 0f, 0f, 0f, 0.6f, 0.8f);
        Box(r, 0, 2.0f, 0.43f, 0.86f, 0.03f, 0.03f, frame, 0f, 0f, 0f, 0.6f, 0.8f);
        Box(r, -0.43f, 2.0f, 0, 0.03f, 0.03f, 0.86f, frame, 0f, 0f, 0f, 0.6f, 0.8f);
        Box(r, 0.43f, 2.0f, 0, 0.03f, 0.03f, 0.86f, frame, 0f, 0f, 0f, 0.6f, 0.8f);
        Cyl(r, 0, 1.05f, -0.4f, 0.025f, 2.1f, Steel, 0f, 0f, 0f, 0.7f, 0.9f);
        Box(r, 0, 2.05f, -0.33f, 0.02f, 0.02f, 0.14f, Steel, 0f, 0f, 0f, 0.7f, 0.9f);
        Cyl(r, 0, 2.05f, -0.24f, 0.22f, 0.02f, Steel, 0f, 0f, 0f, 0.7f, 0.9f);
        if (kind == 1) Box(r, 0, 0.55f, -0.45f, 0.9f, 1.1f, 0.04f, LightWood);
        if (kind == 2) Box(r, 0, 1.0f, 0.44f, 0.88f, 1.9f, 0.015f, Grey);
    }

    // kind: 0 = classic high cistern, 1 = standard, 2 = compact wall-hung
    static void Toilet(GameObject r, Color c, int kind)
    {
        float s = kind == 2 ? 0.9f : 1f;
        float by = kind == 2 ? 0.42f : 0.38f;
        if (kind != 2) Cyl(r, 0, 0.17f, 0.08f, 0.24f, 0.34f, c, 0f, 0f, 0f, 0.7f);
        Ball(r, 0, by, 0.1f, 0.38f * s, 0.22f, 0.52f * s, c, 0f, 0f, 0f, 0.7f);
        Ball(r, 0, by + 0.1f, 0.1f, 0.36f * s, 0.04f, 0.46f * s, Dk(c, 0.08f), 0f, 0f, 0f, 0.7f);
        if (kind == 0)
        {
            Box(r, 0, 1.7f, -0.25f, 0.45f, 0.3f, 0.18f, c, 0f, 0f, 0f, 0.7f);
            Cyl(r, 0, 1.0f, -0.2f, 0.04f, 1.3f, Steel, 0f, 0f, 0f, 0.6f, 0.8f);
        }
        else
        {
            Box(r, 0, 0.62f, -0.2f, 0.4f * s, 0.34f, 0.17f, c, 0f, 0f, 0f, 0.7f);
            Cyl(r, 0, 0.8f, -0.2f, 0.05f, 0.015f, Steel, 0f, 0f, 0f, 0.7f, 0.9f);
        }
    }

    static void TvStand(GameObject r, float w, Color stand, Color legs, float screenH)
    {
        Box(r, 0, 0.35f, 0, w, 0.05f, 0.4f, stand);
        foreach (float sx in new[] { -1f, 1f }) Box(r, sx * (w / 2 - 0.03f), 0.17f, 0, 0.04f, 0.34f, 0.38f, legs);
        Box(r, 0, 0.15f, 0, w - 0.1f, 0.02f, 0.36f, stand);
        float tw = w * 0.8f, cy = 0.375f + screenH / 2 + 0.05f;
        Box(r, 0, 0.4f, 0, 0.12f, 0.06f, 0.1f, Charcoal);
        Box(r, 0, cy, 0, tw, screenH, 0.035f, Black);
        Box(r, 0, cy, 0.019f, tw - 0.05f, screenH - 0.05f, 0.004f, H("#0b1220"), 0f, 0f, 0f, 0.9f, 0.3f);
    }

    static void TvCrt(GameObject r)
    {
        foreach (float sx in new[] { -1f, 1f }) foreach (float sz in new[] { -1f, 1f })
            Cyl(r, sx * 0.3f, 0.05f, sz * 0.2f, 0.05f, 0.1f, DarkWood);
        Box(r, 0, 0.41f, 0, 0.75f, 0.62f, 0.55f, Wood);
        Box(r, -0.08f, 0.42f, 0.28f, 0.5f, 0.42f, 0.02f, H("#1b2227"), 0f, 0f, 0f, 0.9f, 0.3f);
        Box(r, 0.28f, 0.42f, 0.28f, 0.14f, 0.42f, 0.02f, DarkWood);
        Cyl(r, 0.28f, 0.52f, 0.295f, 0.05f, 0.02f, Brass, 90f, 0f, 0f, 0.7f, 0.9f);
        Cyl(r, 0.28f, 0.36f, 0.295f, 0.05f, 0.02f, Brass, 90f, 0f, 0f, 0.7f, 0.9f);
    }

    static void LampTable(GameObject r, Color baseC, Color shade)
    {
        Ball(r, 0, 0.14f, 0, 0.2f, 0.26f, 0.2f, baseC, 0f, 0f, 0f, 0.7f);
        Cyl(r, 0, 0.31f, 0, 0.04f, 0.1f, baseC);
        Cyl(r, 0, 0.45f, 0, 0.32f, 0.2f, shade, 0f, 0f, 0f, 0.1f);
    }

    static void LampFloor(GameObject r, Color baseC, Color shade, float h)
    {
        Cyl(r, 0, 0.015f, 0, 0.3f, 0.03f, baseC, 0f, 0f, 0f, 0.7f, 0.8f);
        Cyl(r, 0, h / 2, 0, 0.03f, h, baseC, 0f, 0f, 0f, 0.7f, 0.8f);
        Cyl(r, 0, h + 0.05f, 0, 0.4f, 0.28f, shade, 0f, 0f, 0f, 0.1f);
    }

    static void LampTripod(GameObject r, Color wood, Color shade)
    {
        for (int i = 0; i < 3; i++)
        {
            float ang = i * 120f, a = ang * Mathf.Deg2Rad;
            Blade(r, Mathf.Sin(a) * 0.3f, 0f, Mathf.Cos(a) * 0.3f, ang + 180f, 12f, 1.4f, 0.04f, wood);
        }
        Cyl(r, 0, 1.45f, 0, 0.4f, 0.28f, shade, 0f, 0f, 0f, 0.1f);
    }

    static void Cactus(GameObject r)
    {
        Pot(r, Terracotta, 0.22f, 0.18f);
        Cyl(r, 0, 0.4f, 0, 0.14f, 0.45f, Green);
        Ball(r, 0, 0.625f, 0, 0.14f, 0.14f, 0.14f, Green);
        Cyl(r, -0.1f, 0.36f, 0, 0.07f, 0.14f, Green, 0f, 0f, 90f);
        Cyl(r, -0.17f, 0.46f, 0, 0.07f, 0.2f, Green);
        Ball(r, -0.17f, 0.56f, 0, 0.07f, 0.07f, 0.07f, Green);
        Cyl(r, 0.1f, 0.33f, 0, 0.07f, 0.14f, Green, 0f, 0f, 90f);
        Cyl(r, 0.17f, 0.4f, 0, 0.07f, 0.16f, Green);
        Ball(r, 0.17f, 0.48f, 0, 0.07f, 0.07f, 0.07f, Green);
    }
}
#endif
