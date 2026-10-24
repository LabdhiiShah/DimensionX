using System;
using System.Threading.Tasks;
using UnityEngine;
using GLTFast;

public class FloorplanLoader : MonoBehaviour
{
    public static FloorplanLoader Instance { get; private set; }

    [Serializable] public class PlanVec2 { public float x; public float y; }

    [Serializable]
    public class PlanInfo
    {
        public bool valid;
        public string key;
        public string plan_id;
        public PlanVec2 footprint_center_m = new PlanVec2();
        public PlanVec2 spawn_m = new PlanVec2();
        public PlanVec2 facing = new PlanVec2();
    }

    [Serializable]
    public class LoadFloorplanMessage
    {
        public string type;
        public string glb_url;
        public string project_id;
        public PlanInfo plan = new PlanInfo();
        public SavedFurnitureItem[] saved_furniture;
    }

    [Serializable]
    private class FloorplanStatusMessage
    {
        public string type = "floorplan_status";
        public string state;
        public string message;
        public string glb_url;
    }

    [Header("Website-controlled cameras (leave empty to use the ones on FurnitureSyncManager)")]
    public Camera interiorCamera;
    public Camera floorPlanCamera;

    [Header("Interior (drag-and-drop) camera framing")]
    [Range(25f, 85f)] public float interiorPitch = 60f;
    [Range(25f, 90f)] public float interiorFov = 55f;
    public float fitMargin = 1.2f;

    [Header("Old static test room - switched off when a house loads")]
    public GameObject[] hideOnLoad;

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
            if (!ok) throw new Exception("could not download/parse " + msg.glb_url);

            Report("loading", "Building the house...", msg.glb_url);
            root = new GameObject("DX_House");
            ok = await gltf.InstantiateMainSceneAsync(root.transform);
            if (!ok) throw new Exception("the glTF loaded but its scene could not be instantiated");

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

    private void SwapInHouse(GameObject root, GltfImport gltf, LoadFloorplanMessage msg)
    {
        PlanInfo plan = (msg.plan != null && msg.plan.valid) ? msg.plan : null;

        ClassifyAndCollide(root);
        AlignToPlanAxes(root, plan);
        Physics.SyncTransforms();

        if (_root != null)
        {
            _root.SetActive(false);
            Destroy(_root);
        }
        _gltf?.Dispose();
        foreach (var go in hideOnLoad) if (go != null) go.SetActive(false);

        _root = root;
        _gltf = gltf;
        HouseBounds = ComputeHouseBounds(root);

        var sync = FurnitureSyncManager.Instance;
        if (sync != null)
        {
            // Setup floor mask dynamically based on name
            int floorLayerIndex = LayerMask.NameToLayer("DX_Floor");
            if (floorLayerIndex < 0) floorLayerIndex = 8; // Fallback

            sync.floorLayerMask = 1 << floorLayerIndex;
            sync.ResetForNewPlan(plan != null && !string.IsNullOrEmpty(plan.key) ? plan.key : msg.glb_url);

            if (msg.saved_furniture != null && msg.saved_furniture.Length > 0)
            {
                sync.SpawnSavedFurniture(msg.saved_furniture);
            }
        }

        SetUpWebsiteCameras(HouseBounds);
        ComputeSpawn(plan, HouseBounds);

        Debug.Log($"[FloorplanLoader] House ready. Bounds center {HouseBounds.center}, size {HouseBounds.size}. VR spawn {SpawnPosition}, yaw {SpawnYaw:0}.");
        OnHouseReady?.Invoke();
    }

    private void ClassifyAndCollide(GameObject root)
    {
        // FIX: Look up layer indices by their exact string names
        int floorLayerIndex = LayerMask.NameToLayer("DX_Floor");
        int wallLayerIndex = LayerMask.NameToLayer("DX_Walls");
        int roofLayerIndex = LayerMask.NameToLayer("DX_Roof");

        // Fallbacks in case the layers aren't created yet
        if (floorLayerIndex < 0) floorLayerIndex = 8;
        if (wallLayerIndex < 0) wallLayerIndex = 9;
        if (roofLayerIndex < 0) roofLayerIndex = 10;

        foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
        {
            string n = mf.name;
            string p = mf.transform.parent != null ? mf.transform.parent.name : "";

            int layer = -1;
            bool collide = false;
            bool roof = false;

            if (Is(n, p, "Floor") || Starts(n, p, "Balcony_")) { layer = floorLayerIndex; collide = true; }
            else if (Is(n, p, "Roof")) { layer = roofLayerIndex; roof = true; }
            else if (Starts(n, p, "Wall_") || Starts(n, p, "Window_")) { layer = wallLayerIndex; collide = true; }
            else if (Starts(n, p, "Door_")) { layer = wallLayerIndex; }

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
        if (dot < -0.01f) root.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
    }

    private Bounds ComputeHouseBounds(GameObject root)
    {
        bool has = false;
        var b = new Bounds(root.transform.position, Vector3.zero);
        foreach (var r in root.GetComponentsInChildren<Renderer>())
        {
            if (r.gameObject.layer == LayerMask.NameToLayer("DX_Roof")) continue;
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

        if (cam == null) return;

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
        int roofIndex = LayerMask.NameToLayer("DX_Roof");
        if (roofIndex >= 0) cam.cullingMask &= ~(1 << roofIndex);
    }

    private void ComputeSpawn(PlanInfo plan, Bounds b)
    {
        Vector3 want = plan != null ? new Vector3(plan.spawn_m.x, 0f, plan.spawn_m.y) : new Vector3(b.center.x, 0f, b.center.z);
        SpawnPosition = FindFloorPointNear(want);
        Vector2 f = plan != null ? new Vector2(plan.facing.x, plan.facing.y) : Vector2.up;
        SpawnYaw = Mathf.Atan2(f.x, f.y) * Mathf.Rad2Deg;
    }

    private Vector3 FindFloorPointNear(Vector3 want)
    {
        int floorMask = 1 << LayerMask.NameToLayer("DX_Floor");
        int wallMask = 1 << LayerMask.NameToLayer("DX_Walls");

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
        return want;
    }

    private static bool Is(string a, string b, string name) => a == name || b == name;
    private static bool Starts(string a, string b, string prefix) => a.StartsWith(prefix, StringComparison.Ordinal) || b.StartsWith(prefix, StringComparison.Ordinal);

    private static Transform FindNode(Transform root, string name)
    {
        foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (t.name == name) return t;
        return null;
    }

    private void Report(string state, string message, string url)
    {
        Debug.Log($"[FloorplanLoader] {state}: {message}");
        var sync = FurnitureSyncManager.Instance;
        if (sync != null) sync.SendToBridge(new FloorplanStatusMessage { state = state, message = message, glb_url = url ?? "" });
    }
}