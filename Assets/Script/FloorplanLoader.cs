using System;
using System.Threading.Tasks;
using UnityEngine;
using GLTFast;

/// <summary>
/// Turns the GLB produced by the website's DXF pipeline into the live house, and then sets
/// up everything that depends on that house:
///
///   1. Downloads + instantiates the GLB (the website sends "load_floorplan" through the bridge).
///   2. Puts the pieces on layers and gives them colliders:
///        Floor, Balcony_*   -> floorLayer  (the ONLY surface furniture can be dropped on)
///        Wall_*, Window_*   -> wallLayer   (solid)
///        Door_*             -> wallLayer   (no collider: you can walk through doorways)
///        Roof               -> roofLayer   (hidden from the website cameras, visible in VR)
///   3. Aligns the house so Unity world X/Z == the DXF's x/y (in metres).
///   4. Frames the website's Interior (drag-and-drop) camera around the whole house, and
///      keeps the roof out of both website cameras (otherwise you'd be looking at the roof,
///      and drop raycasts would hit it).
///   5. Works out where the VR rig should start (just inside the main entrance, facing in).
///      VrSyncManager reads SpawnPosition / SpawnYaw on "View in VR".
///   6. Tells FurnitureSyncManager to start a clean furniture session for this plan.
///
/// Setup: put this on the same GameObject as FurnitureSyncManager (SYNCMAN). Drag the old
/// hard-coded test room (floor, Wall1-4, p1/p2 and the five furniture prefab instances) into
/// "Hide On Load" so it switches off when a real house arrives.
/// </summary>
public class FloorplanLoader : MonoBehaviour
{
    public static FloorplanLoader Instance { get; private set; }

    // ---------------- Message shapes (JSON from the bridge) ----------------

    [Serializable] public class PlanVec2 { public float x; public float y; }

    [Serializable]
    public class PlanInfo
    {
        public bool valid;                       // false/absent -> fall back to bounds-based guesses
        public string key;                       // unique per upload; saved furniture is filed under it
        public string plan_id;
        public PlanVec2 footprint_center_m = new PlanVec2(); // DXF x/y, metres
        public PlanVec2 spawn_m = new PlanVec2();            // DXF x/y, metres
        public PlanVec2 facing = new PlanVec2();             // unit vector, DXF x/y
    }

    [Serializable]
    public class LoadFloorplanMessage
    {
        public string type;
        public string glb_url;
        public string project_id;
        public PlanInfo plan = new PlanInfo();
        public SavedFurnitureItem[] saved_furniture; // <--- NEW: Furniture layout from database
    }

    [Serializable]
    private class FloorplanStatusMessage
    {
        public string type = "floorplan_status";
        public string state;   // loading | ready | error
        public string message;
        public string glb_url;
    }

    // ---------------- Inspector ----------------

    [Header("Layers (named for you by Editor/DimensionXLayerSetup)")]
    public int floorLayer = 8;
    public int wallLayer = 9;
    public int roofLayer = 10;

    [Header("Website-controlled cameras (leave empty to use the ones on FurnitureSyncManager)")]
    [Tooltip("The drag-and-drop camera. Defaults to FurnitureSyncManager.streamCamera.")]
    public Camera interiorCamera;
    [Tooltip("Top-down camera used for the PDF. Defaults to FurnitureSyncManager.floorPlanCamera.")]
    public Camera floorPlanCamera;

    [Header("Interior (drag-and-drop) camera framing")]
    [Tooltip("Camera tilt in degrees. 90 = straight down (plan view), lower = more of a dollhouse view. Higher values see over the front wall better.")]
    [Range(25f, 85f)] public float interiorPitch = 60f;
    [Range(25f, 90f)] public float interiorFov = 55f;
    [Tooltip("1.0 = house just touches the frame edges.")]
    public float fitMargin = 1.2f;

    [Header("Old static test room - switched off when a house loads")]
    public GameObject[] hideOnLoad;

    // ---------------- Public state (read by VrSyncManager) ----------------

    public bool HasHouse => _root != null;
    public Bounds HouseBounds { get; private set; }
    public Vector3 SpawnPosition { get; private set; }
    public float SpawnYaw { get; private set; }
    public event Action OnHouseReady;

    private GameObject _root;
    private GltfImport _gltf;
    private string _loadedUrl;
    private string _loadingUrl;

    void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(this); return; }
        Instance = this;
    }

    void OnDestroy()
    {
        if (Instance == this) Instance = null;
        _gltf?.Dispose();
    }

    // ---------------- Entry point (called by FurnitureSyncManager on "load_floorplan") ----------------

    public void HandleLoadMessage(string json)
    {
        LoadFloorplanMessage msg;
        try { msg = JsonUtility.FromJson<LoadFloorplanMessage>(json); }
        catch (Exception e) { Report("error", "Bad load_floorplan message: " + e.Message, null); return; }

        if (msg == null || string.IsNullOrEmpty(msg.glb_url))
        {
            Report("error", "load_floorplan had no glb_url", null);
            return;
        }
        _ = LoadHouse(msg);
    }

    private async Task LoadHouse(LoadFloorplanMessage msg)
    {
        // The website re-sends this on every reconnect; don't rebuild a house we already have.
        if (msg.glb_url == _loadedUrl) { Report("ready", "House already loaded", msg.glb_url); return; }
        if (msg.glb_url == _loadingUrl) return;

        _loadingUrl = msg.glb_url;
        Report("loading", "Downloading the floor plan model...", msg.glb_url);

        GltfImport gltf = null;
        GameObject root = null;
        try
        {
            gltf = new GltfImport();
            bool ok = await gltf.Load(msg.glb_url);
            if (!ok) throw new Exception("could not download/parse " + msg.glb_url + ". For http:// URLs set Player Settings > Other Settings > Allow downloads over HTTP.");

            Report("loading", "Building the house...", msg.glb_url);
            root = new GameObject("DX_House");
            ok = await gltf.InstantiateMainSceneAsync(root.transform);
            if (!ok) throw new Exception("the glTF loaded but its scene could not be instantiated");

            // A newer upload may have arrived while we were awaiting.
            if (_loadingUrl != msg.glb_url) { Destroy(root); gltf.Dispose(); return; }

            SwapInHouse(root, gltf, msg);
            _loadedUrl = msg.glb_url;

            Vector3 size = HouseBounds.size;
            Report("ready", $"{size.x:0.0} m x {size.z:0.0} m", msg.glb_url);
        }
        catch (Exception e)
        {
            Debug.LogError("[FloorplanLoader] " + e);
            if (root != null && root != _root) Destroy(root);
            if (gltf != null && gltf != _gltf) gltf.Dispose();
            Report("error", e.Message, msg.glb_url);
        }
        finally
        {
            if (_loadingUrl == msg.glb_url) _loadingUrl = null;
        }
    }

    // ---------------- Building the scene around the new house ----------------

    private void SwapInHouse(GameObject root, GltfImport gltf, LoadFloorplanMessage msg)
    {
        PlanInfo plan = (msg.plan != null && msg.plan.valid) ? msg.plan : null;

        ClassifyAndCollide(root);
        AlignToPlanAxes(root, plan);
        Physics.SyncTransforms();

        // Out with the old house and the old test room.
        if (_root != null)
        {
            _root.SetActive(false); // colliders vanish immediately, Destroy only happens at end of frame
            Destroy(_root);
        }
        _gltf?.Dispose();
        foreach (var go in hideOnLoad) if (go != null) go.SetActive(false);

        _root = root;
        _gltf = gltf;
        HouseBounds = ComputeHouseBounds(root);

        // Furniture can only be dropped on the floor; start a clean session filed under this plan.
        var sync = FurnitureSyncManager.Instance;
        if (sync != null)
        {
            sync.floorLayerMask = 1 << floorLayer;
            sync.ResetForNewPlan(plan != null && !string.IsNullOrEmpty(plan.key) ? plan.key : msg.glb_url);

            // --- NEW: Spawn the saved furniture from the database ---
            if (msg.saved_furniture != null && msg.saved_furniture.Length > 0)
            {
                sync.SpawnSavedFurniture(msg.saved_furniture);
            }
        }
        else Debug.LogWarning("[FloorplanLoader] No FurnitureSyncManager in the scene - cameras are framed but nothing will be streamed.");

        SetUpWebsiteCameras(HouseBounds);
        ComputeSpawn(plan, HouseBounds);

        Debug.Log($"[FloorplanLoader] House ready. Bounds center {HouseBounds.center}, size {HouseBounds.size}. VR spawn {SpawnPosition}, yaw {SpawnYaw:0}.");
        OnHouseReady?.Invoke();
    }

    private void ClassifyAndCollide(GameObject root)
    {
        foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
        {
            string n = mf.name;
            string p = mf.transform.parent != null ? mf.transform.parent.name : "";

            int layer = -1;
            bool collide = false;
            bool roof = false;

            if (Is(n, p, "Floor") || Starts(n, p, "Balcony_")) { layer = floorLayer; collide = true; }
            else if (Is(n, p, "Roof")) { layer = roofLayer; roof = true; }
            else if (Starts(n, p, "Wall_") || Starts(n, p, "Window_")) { layer = wallLayer; collide = true; }
            else if (Starts(n, p, "Door_")) { layer = wallLayer; } // doorway stays walk-through
            if (layer < 0) continue;

            var go = mf.gameObject;
            go.layer = layer;

            if (collide && go.GetComponent<MeshCollider>() == null)
            {
                var col = go.AddComponent<MeshCollider>();
                col.sharedMesh = mf.sharedMesh;
            }
            if (roof)
            {
                var mr = go.GetComponent<MeshRenderer>();
                if (mr != null) mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
        }
    }

    private void AlignToPlanAxes(GameObject root, PlanInfo plan)
    {
        if (plan == null) return;

        Transform floor = FindNode(root.transform, "Floor");
        Renderer r = floor != null ? floor.GetComponentInChildren<Renderer>() : null;
        if (r == null) return;

        Vector3 c = r.bounds.center;
        float dot = c.x * plan.footprint_center_m.x + c.z * plan.footprint_center_m.y;
        if (dot < -0.01f)
        {
            root.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
            Debug.Log($"[FloorplanLoader] Floor landed at {c}, DXF says ({plan.footprint_center_m.x:0.00}, {plan.footprint_center_m.y:0.00}) - rotated the house 180 degrees to match.");
        }
        else
        {
            Debug.Log($"[FloorplanLoader] Floor landed at {c}; already matches the DXF axes.");
        }
    }

    private Bounds ComputeHouseBounds(GameObject root)
    {
        bool has = false;
        var b = new Bounds(root.transform.position, Vector3.zero);
        foreach (var r in root.GetComponentsInChildren<Renderer>())
        {
            if (r.gameObject.layer == roofLayer) continue;
            if (!has) { b = r.bounds; has = true; }
            else b.Encapsulate(r.bounds);
        }
        return b;
    }

    private void SetUpWebsiteCameras(Bounds b)
    {
        var sync = FurnitureSyncManager.Instance;
        Camera cam = interiorCamera != null ? interiorCamera : (sync != null ? sync.streamCamera : null);
        Camera plan = floorPlanCamera != null ? floorPlanCamera : (sync != null ? sync.floorPlanCamera : null);

        PrepareWebsiteCamera(cam);
        PrepareWebsiteCamera(plan);

        if (cam == null)
        {
            Debug.LogWarning("[FloorplanLoader] No interior camera (assign one here or on FurnitureSyncManager.streamCamera).");
            return;
        }

        cam.orthographic = false;
        cam.fieldOfView = interiorFov;
        float radius = b.extents.magnitude * fitMargin;
        float dist = radius / Mathf.Tan(cam.fieldOfView * 0.5f * Mathf.Deg2Rad);
        Quaternion rot = Quaternion.Euler(interiorPitch, 0f, 0f);
        cam.transform.SetPositionAndRotation(b.center - rot * Vector3.forward * dist, rot);
        cam.farClipPlane = Mathf.Max(cam.farClipPlane, dist + radius * 2f);
    }

    private void PrepareWebsiteCamera(Camera cam)
    {
        if (cam == null) return;
        cam.cullingMask &= ~(1 << roofLayer);
    }

    private void ComputeSpawn(PlanInfo plan, Bounds b)
    {
        Vector3 want = plan != null
            ? new Vector3(plan.spawn_m.x, 0f, plan.spawn_m.y)
            : new Vector3(b.center.x, 0f, b.center.z);
        SpawnPosition = FindFloorPointNear(want);

        Vector2 f = plan != null ? new Vector2(plan.facing.x, plan.facing.y) : Vector2.up;
        SpawnYaw = Mathf.Atan2(f.x, f.y) * Mathf.Rad2Deg;
    }

    private Vector3 FindFloorPointNear(Vector3 want)
    {
        int floorMask = 1 << floorLayer;
        int wallMask = 1 << wallLayer;

        for (float radius = 0f; radius <= 6f; radius += 0.5f)
        {
            int steps = radius <= 0f ? 1 : 12;
            for (int i = 0; i < steps; i++)
            {
                float a = i * (Mathf.PI * 2f / steps);
                Vector3 p = want + new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * radius;
                if (!Physics.Raycast(p + Vector3.up * 50f, Vector3.down, out RaycastHit hit, 100f, floorMask)) continue;
                if (Physics.CheckSphere(hit.point + Vector3.up * 1f, 0.35f, wallMask)) continue;
                return hit.point;
            }
        }
        Debug.LogWarning("[FloorplanLoader] Couldn't find clear floor near the spawn point; using it as-is.");
        return want;
    }

    private static bool Is(string a, string b, string name) => a == name || b == name;

    private static bool Starts(string a, string b, string prefix) =>
        a.StartsWith(prefix, StringComparison.Ordinal) || b.StartsWith(prefix, StringComparison.Ordinal);

    private static Transform FindNode(Transform root, string name)
    {
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
            if (t.name == name) return t;
        return null;
    }

    private void Report(string state, string message, string url)
    {
        Debug.Log($"[FloorplanLoader] {state}: {message}");
        var sync = FurnitureSyncManager.Instance;
        if (sync != null)
            sync.SendToBridge(new FloorplanStatusMessage { state = state, message = message, glb_url = url ?? "" });
    }
}