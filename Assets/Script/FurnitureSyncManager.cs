using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.WebSockets;
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
#endif

public class FurnitureSyncManager : MonoBehaviour
{
    public static FurnitureSyncManager Instance { get; private set; }

    [Header("Bridge connection")]
    public string bridgeUrl = "ws://localhost:8765";
    public bool autoReconnect = true;
    public float reconnectDelaySeconds = 3f;

    [Header("Live view streaming")]
    [Tooltip("The LIVE camera used for the Design Room.")]
    public Camera streamCamera;
    [Tooltip("Optional — a SEPARATE, dedicated top-down camera used only when \"Save Design\" is pressed.")]
    public Camera floorPlanCamera;
    public int streamWidth = 640;
    public int streamHeight = 360;
    [Tooltip("Frames per second sent to the website.")]
    public float streamFps = 5f;
    [Range(1, 100)] public int streamJpegQuality = 70;

    [Header("Drag-and-drop placement")]
    public LayerMask floorLayerMask = ~0;
    public LayerMask wallLayerMask = ~0; // MAKE SURE THIS IS SET TO 'DX_Walls' IN THE INSPECTOR
    public float raycastMaxDistance = 100f;

    [Header("Camera pan/zoom (from website D-pad)")]
    public float cameraPanSpeed = 3f;
    public float cameraZoomSpeed = 2f;
    public float minOrthographicSize = 2f;
    public float maxOrthographicSize = 30f;

    [Header("Persistence")]
    public bool autoSavePlacedInstances = true;
    public bool autoLoadPlacedInstancesOnStart = true;
    public string placedInstancesFileName = "placed_instances.json";

    [Header("Instance scale limits")]
    public float minInstanceScale = 0.2f;
    public float maxInstanceScale = 4f;

    [Header("VR handoff")]
    public string layoutFileName = "current_layout.json";

    private ClientWebSocket _socket;
    private CancellationTokenSource _cts;
    private readonly Dictionary<int, GameObject> _slots = new Dictionary<int, GameObject>();
    private readonly Dictionary<string, GameObject> _placedInstances = new Dictionary<string, GameObject>();

    private readonly Queue<Action> _mainThreadQueue = new Queue<Action>();
    private readonly object _queueLock = new object();

    private Texture2D _frameTexture;
    private RenderTexture _frameRenderTexture;

    // --- WALL PAINTING STATE ---
    private bool _isPaintMode = false;
    private List<GameObject> _selectedWalls = new List<GameObject>();
    private Dictionary<GameObject, Color> _originalWallColors = new Dictionary<GameObject, Color>();
    private float _lastWallSelectTime = 0f; // Prevents double clicks

    // ---------------- Message shapes ----------------
    [Serializable] private class MessageEnvelope { public string type; }
    [Serializable] private class SwapFurnitureMessage { public string type; public int type_id; public string type_name; public int style_id; public string style_name; public string prefab_path; public string requested_at; }
    [Serializable] private class SwapResultMessage { public string type = "swap_result"; public int type_id; public bool success; public string message; }
    [Serializable] private class PlaceFurnitureMessage { public string type; public int type_id; public string type_name; public int style_id; public string style_name; public string prefab_path; public float viewport_x; public float viewport_y; public string instance_id; }
    [Serializable] private class PlaceResultMessage { public string type = "place_result"; public bool success; public string instance_id; public string message; public float world_x, world_y, world_z; }
    [Serializable] private class MoveFurnitureMessage { public string type; public string instance_id; public float viewport_x; public float viewport_y; }
    [Serializable] private class MoveResultMessage { public string type = "move_result"; public bool success; public string instance_id; public string message; }
    [Serializable] private class CameraPanMessage { public string type; public float dx; public float dz; }
    [Serializable] private class CameraZoomMessage { public string type; public float delta; }
    [Serializable] private class CameraRotateMessage { public string type; public float degrees; }
    [Serializable] private class RemoveFurnitureMessage { public string type; public string instance_id; }
    [Serializable] private class RemoveResultMessage { public string type = "remove_result"; public bool success; public string instance_id; public string message; }
    [Serializable] private class SwapInstanceMessage { public string type; public string instance_id; public int style_id; public string style_name; public string prefab_path; }
    [Serializable] private class SwapInstanceResultMessage { public string type = "swap_instance_result"; public bool success; public string instance_id; public string message; }
    [Serializable] private class RotateInstanceMessage { public string type; public string instance_id; public float degrees; }
    [Serializable] private class ScaleInstanceMessage { public string type; public string instance_id; public float delta; }
    [Serializable] private class InstanceTransformResultMessage { public string type = "instance_transform_result"; public bool success; public string instance_id; public string message; }

    // --- PAINT MESSAGES ---
    [Serializable] private class TogglePaintMessage { public string type; public bool active; }
    [Serializable] private class ApplyColorMessage { public string type; public string color; }
    [Serializable] private class SelectWallMessage { public string type; public float viewport_x; public float viewport_y; }
    [Serializable] private class WallSelectionMessage { public string type = "wall_selection"; public int count; }

    [Serializable]
    private class InstanceInfo
    {
        public string instance_id; public int type_id; public int style_id; public string style_name; public string prefab_path;
        public float viewport_x; public float viewport_y; public float world_x; public float world_y; public float world_z;
        public float rotation_y_deg; public float scale; public float scale_multiplier;
    }
    [Serializable] private class InstancesMessage { public string type = "instances"; public InstanceInfo[] items; }
    [Serializable] private class FrameMessage { public string type = "frame"; public string image; public int width; public int height; }
    [Serializable] private class HelloMessage { public string type; public string role; }
    [Serializable] private class LaunchVrReadyMessage { public string type = "launch_vr_ready"; public string layout_path; }
    [Serializable] private class StatusMessage { public string type = "status"; public string message; }
    [Serializable] private class FloorPlanSnapshotMessage { public string type = "floorplan_snapshot"; public string image; public int width; public int height; public InstanceInfo[] items; }

    [Serializable]
    private class PlacedInstanceEntry
    {
        public string instance_id; public int type_id; public int style_id; public string style_name; public string prefab_path;
        public float px, py, pz; public float rx, ry, rz, rw; public float sx, sy, sz;
        public float base_sx, base_sy, base_sz; public float scale_multiplier;
    }
    [Serializable]
    private class PlacedInstancesFile { public PlacedInstanceEntry[] items; public string saved_at; }

    void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }

    async void Start()
    {
        _cts = new CancellationTokenSource();
        _frameTexture = new Texture2D(streamWidth, streamHeight, TextureFormat.RGB24, false);
        _frameRenderTexture = new RenderTexture(streamWidth, streamHeight, 24);

        if (autoLoadPlacedInstancesOnStart && FindObjectOfType<FloorplanLoader>() == null) LoadPlacedInstancesIfPresent();

        if (streamCamera != null)
        {
            StartCoroutine(StreamFramesLoop());
            WarnIfStreamCameraLooksShared();
        }
        else Debug.LogWarning("[FurnitureSync] No Stream Camera assigned — live view won't be sent to the website.");

        await ConnectLoop(_cts.Token);
    }

    private void WarnIfStreamCameraLooksShared()
    {
        var others = streamCamera.GetComponents<MonoBehaviour>();
        var suspicious = new List<string>();
        foreach (var c in others)
        {
            if (c == null) continue;
            string n = c.GetType().Name;
            if (n == nameof(FurnitureSyncManager)) continue;
            suspicious.Add(n);
        }
        if (suspicious.Count > 0)
        {
            Debug.LogWarning($"[FurnitureSync] Stream Camera '{streamCamera.name}' also has these script(s) on it: {string.Join(", ", suspicious)}. " +
                "If any of them drive your XR/VR simulator's head movement, they WILL fight with the website's camera_pan/zoom/rotate controls. " +
                "Give the design camera its own plain GameObject with nothing else on it, and point VrSyncManager.streamCamera at the XR rig's camera instead.");
        }
    }

    void OnDestroy()
    {
        _cts?.Cancel();
        try { _socket?.Abort(); } catch { /* ignore */ }
        if (_frameRenderTexture != null) _frameRenderTexture.Release();
    }

    void Update()
    {
        while (true)
        {
            Action action;
            lock (_queueLock)
            {
                if (_mainThreadQueue.Count == 0) break;
                action = _mainThreadQueue.Dequeue();
            }
            action();
        }
    }

    private void RunOnMainThread(Action action) { lock (_queueLock) { _mainThreadQueue.Enqueue(action); } }
    public void SendToBridge(object message) { _ = SendJson(message); }

    public void ResetForNewPlan(string planKey)
    {
        foreach (var kvp in _placedInstances) if (kvp.Value != null) Destroy(kvp.Value);
        _placedInstances.Clear();
        _slots.Clear();
        ClearWallSelection();

        var safe = new StringBuilder();
        foreach (char ch in planKey ?? "") safe.Append(char.IsLetterOrDigit(ch) || ch == '-' || ch == '_' ? ch : '_');
        string suffix = safe.Length > 0 ? safe.ToString() : "default";
        if (suffix.Length > 80) suffix = suffix.Substring(suffix.Length - 80);
        placedInstancesFileName = $"placed_instances_{suffix}.json";

        if (autoLoadPlacedInstancesOnStart) LoadPlacedInstancesIfPresent();
        Debug.Log($"[FurnitureSync] New plan session '{suffix}' ({_placedInstances.Count} piece(s) restored).");
    }

    public void SpawnSavedFurniture(SavedFurnitureItem[] items)
    {
        if (items == null || items.Length == 0) return;
        int spawnCount = 0;
        foreach (var entry in items)
        {
            if (string.IsNullOrEmpty(entry.prefab_path)) continue;
            var prefab = LoadPrefab(entry.prefab_path);
            if (prefab == null) { continue; }

            var pos = new Vector3(entry.world_x, entry.world_y, entry.world_z);
            var rot = prefab.transform.rotation * Quaternion.Euler(0, entry.rotation_y_deg, 0);
            var instance = Instantiate(prefab, pos, rot);

            var slot = instance.GetComponent<FurnitureSlot>();
            if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
            slot.baseScale = prefab.transform.localScale;
            slot.scaleMultiplier = entry.scale_multiplier > 0f ? entry.scale_multiplier : 1f;
            instance.transform.localScale = slot.baseScale * slot.scaleMultiplier;

            instance.name = $"{entry.style_name} [{entry.instance_id.Substring(0, Math.Min(6, entry.instance_id.Length))}]";
            slot.typeId = entry.type_id; slot.styleId = entry.style_id; slot.label = entry.style_name;
            slot.instanceId = entry.instance_id; slot.prefabPath = entry.prefab_path;

            _placedInstances[entry.instance_id] = instance;
            spawnCount++;
        }
        Debug.Log($"[FurnitureSync] Restored {spawnCount} furniture pieces from the database.");
    }

    public void RegisterSlot(int typeId, GameObject go) { _slots[typeId] = go; }
    public void UnregisterSlot(int typeId, GameObject go) { if (_slots.TryGetValue(typeId, out var current) && current == go) _slots.Remove(typeId); }

    private async Task ConnectLoop(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                _socket = new ClientWebSocket();
                await _socket.ConnectAsync(new Uri(bridgeUrl), token);
                await SendJson(new HelloMessage { type = "hello", role = "unity" });
                await ReceiveLoop(token);
            }
            catch (Exception e) { Debug.LogWarning($"[FurnitureSync] Connection error: {e.Message}"); }

            if (!autoReconnect || token.IsCancellationRequested) break;
            await Task.Delay(TimeSpan.FromSeconds(reconnectDelaySeconds), token).ContinueWith(_ => { });
        }
    }

    private async Task ReceiveLoop(CancellationToken token)
    {
        var buffer = new byte[16384];
        while (_socket.State == WebSocketState.Open && !token.IsCancellationRequested)
        {
            using var ms = new MemoryStream();
            WebSocketReceiveResult result;
            do
            {
                result = await _socket.ReceiveAsync(new ArraySegment<byte>(buffer), token);
                if (result.MessageType == WebSocketMessageType.Close) { Debug.LogWarning("[FurnitureSync] Bridge closed the connection."); return; }
                ms.Write(buffer, 0, result.Count);
            } while (!result.EndOfMessage);

            HandleIncoming(Encoding.UTF8.GetString(ms.ToArray()));
        }
    }

    private void HandleIncoming(string json)
    {
        try
        {
            var envelope = JsonUtility.FromJson<MessageEnvelope>(json);
            if (envelope == null) return;

            switch (envelope.type)
            {
                case "swap_furniture": RunOnMainThread(() => ApplySwap(JsonUtility.FromJson<SwapFurnitureMessage>(json))); break;
                case "place_furniture": RunOnMainThread(() => ApplyPlacement(JsonUtility.FromJson<PlaceFurnitureMessage>(json))); break;
                case "move_furniture": RunOnMainThread(() => ApplyMove(JsonUtility.FromJson<MoveFurnitureMessage>(json))); break;
                case "camera_pan": RunOnMainThread(() => ApplyCameraPan(JsonUtility.FromJson<CameraPanMessage>(json))); break;
                case "camera_zoom": RunOnMainThread(() => ApplyCameraZoom(JsonUtility.FromJson<CameraZoomMessage>(json))); break;
                case "camera_rotate": RunOnMainThread(() => ApplyCameraRotate(JsonUtility.FromJson<CameraRotateMessage>(json))); break;
                case "remove_furniture": RunOnMainThread(() => ApplyRemove(JsonUtility.FromJson<RemoveFurnitureMessage>(json))); break;
                case "swap_instance": RunOnMainThread(() => ApplySwapInstance(JsonUtility.FromJson<SwapInstanceMessage>(json))); break;
                case "rotate_instance": RunOnMainThread(() => ApplyRotateInstance(JsonUtility.FromJson<RotateInstanceMessage>(json))); break;
                case "scale_instance": RunOnMainThread(() => ApplyScaleInstance(JsonUtility.FromJson<ScaleInstanceMessage>(json))); break;
                case "launch_vr": RunOnMainThread(SaveLayoutAndSignalVr); break;
                case "capture_floorplan": RunOnMainThread(CaptureFullFloorPlan); break;
                case "load_floorplan":
                    {
                        string raw = json;
                        RunOnMainThread(() =>
                        {
                            if (FloorplanLoader.Instance != null) FloorplanLoader.Instance.HandleLoadMessage(raw);
                            else _ = SendJson(new StatusMessage { message = "Unity has no FloorplanLoader in the scene - add the component to SYNCMAN." });
                        });
                    }
                    break;
                // --- PAINT CASES ---
                case "toggle_paint_mode": RunOnMainThread(() => TogglePaintMode(JsonUtility.FromJson<TogglePaintMessage>(json).active)); break;
                case "apply_wall_color": RunOnMainThread(() => ApplyWallColor(JsonUtility.FromJson<ApplyColorMessage>(json).color)); break;
                case "select_wall_at": RunOnMainThread(() => ApplyWallSelection(JsonUtility.FromJson<SelectWallMessage>(json))); break;
                case "hello_ack": break;
            }
        }
        catch (Exception e) { Debug.LogWarning($"[FurnitureSync] Failed to parse message: {e.Message}\n{json}"); }
    }

    private async Task SendJson(object obj)
    {
        if (_socket == null || _socket.State != WebSocketState.Open) return;
        var bytes = Encoding.UTF8.GetBytes(JsonUtility.ToJson(obj));
        await _socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
    }

    private GameObject LoadPrefab(string prefabPath)
    {
#if UNITY_EDITOR
        return AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
#else
        return Resources.Load<GameObject>(StripToResourcesRelativePath(prefabPath));
#endif
    }

#if !UNITY_EDITOR
    private string StripToResourcesRelativePath(string assetPath)
    {
        const string marker = "Resources/";
        int idx = assetPath.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
        string relative = idx >= 0 ? assetPath.Substring(idx + marker.Length) : assetPath;
        if (relative.EndsWith(".prefab")) relative = relative.Substring(0, relative.Length - ".prefab".Length);
        return relative;
    }
#endif

    private void ApplySwap(SwapFurnitureMessage msg)
    {
        if (msg == null) return;
        if (!_slots.TryGetValue(msg.type_id, out var currentObject) || currentObject == null) return;

        var prefab = LoadPrefab(msg.prefab_path);
        if (prefab == null) return;

        var t = currentObject.transform;
        GameObject instance = Instantiate(prefab, t.position, t.rotation, t.parent);
        instance.transform.localScale = t.localScale;
        instance.name = currentObject.name;

        var slot = instance.GetComponent<FurnitureSlot>();
        if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
        slot.typeId = msg.type_id; slot.styleId = msg.style_id; slot.label = msg.style_name; slot.prefabPath = msg.prefab_path;

        Destroy(currentObject);
        RegisterSlot(msg.type_id, instance);
        _ = SendJson(new SwapResultMessage { type_id = msg.type_id, success = true, message = $"Applied {msg.style_name}" });
    }

    private void ApplyPlacement(PlaceFurnitureMessage msg)
    {
        if (msg == null || streamCamera == null) return;
        var prefab = LoadPrefab(msg.prefab_path);
        if (prefab == null) return;

        Vector3 viewportPoint = new Vector3(msg.viewport_x, 1f - msg.viewport_y, 0f);
        Ray ray = streamCamera.ViewportPointToRay(viewportPoint);

        if (Physics.Raycast(ray, out RaycastHit hit, raycastMaxDistance, floorLayerMask))
        {
            string instanceId = string.IsNullOrEmpty(msg.instance_id) ? Guid.NewGuid().ToString("N") : msg.instance_id;
            GameObject instance = Instantiate(prefab, hit.point, prefab.transform.rotation);
            instance.name = $"{msg.type_name} ({msg.style_name})";

            var slot = instance.GetComponent<FurnitureSlot>();
            if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
            slot.typeId = msg.type_id; slot.styleId = msg.style_id; slot.label = msg.style_name;
            slot.instanceId = instanceId; slot.prefabPath = msg.prefab_path;
            slot.baseScale = instance.transform.localScale; slot.scaleMultiplier = 1f;

            _placedInstances[instanceId] = instance;
            _ = SendJson(new PlaceResultMessage { success = true, instance_id = instanceId, message = $"Placed", world_x = hit.point.x, world_y = hit.point.y, world_z = hit.point.z });

            if (autoSavePlacedInstances) SavePlacedInstances();
        }
    }

    private void ApplyMove(MoveFurnitureMessage msg)
    {
        if (msg == null || streamCamera == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null) return;

        Vector3 viewportPoint = new Vector3(msg.viewport_x, 1f - msg.viewport_y, 0f);
        Ray ray = streamCamera.ViewportPointToRay(viewportPoint);
        if (Physics.Raycast(ray, out RaycastHit hit, raycastMaxDistance, floorLayerMask))
        {
            go.transform.position = hit.point;
            _ = SendJson(new MoveResultMessage { success = true, instance_id = msg.instance_id, message = "Moved" });
            if (autoSavePlacedInstances) SavePlacedInstances();
        }
    }

    private void ApplyRotateInstance(RotateInstanceMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null) return;
        go.transform.Rotate(Vector3.up, msg.degrees, Space.World);
        _ = SendJson(new InstanceTransformResultMessage { success = true, instance_id = msg.instance_id, message = "Rotated" });
        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    private void ApplyScaleInstance(ScaleInstanceMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null) return;

        var slot = go.GetComponent<FurnitureSlot>();
        if (slot == null) slot = go.AddComponent<FurnitureSlot>();
        if (slot.baseScale == Vector3.zero) slot.baseScale = go.transform.localScale;
        if (slot.scaleMultiplier <= 0f) slot.scaleMultiplier = 1f;

        float newMultiplier = Mathf.Clamp(slot.scaleMultiplier * (1f + msg.delta), minInstanceScale, maxInstanceScale);
        slot.scaleMultiplier = newMultiplier;
        go.transform.localScale = slot.baseScale * newMultiplier;

        _ = SendJson(new InstanceTransformResultMessage { success = true, instance_id = msg.instance_id, message = "Scaled" });
        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    private void ApplyCameraPan(CameraPanMessage msg)
    {
        if (streamCamera == null || msg == null) return;
        Vector3 right = streamCamera.transform.right;
        Vector3 forwardFlat = Vector3.ProjectOnPlane(streamCamera.transform.forward, Vector3.up);
        if (forwardFlat.sqrMagnitude < 0.0001f) forwardFlat = Vector3.forward;
        forwardFlat.Normalize();
        streamCamera.transform.position += (right * msg.dx + forwardFlat * msg.dz) * cameraPanSpeed;
    }

    private void ApplyCameraZoom(CameraZoomMessage msg)
    {
        if (streamCamera == null || msg == null) return;
        if (streamCamera.orthographic) streamCamera.orthographicSize = Mathf.Clamp(streamCamera.orthographicSize + msg.delta * cameraZoomSpeed, minOrthographicSize, maxOrthographicSize);
        else streamCamera.transform.position += streamCamera.transform.forward * msg.delta * cameraZoomSpeed;
    }

    private void ApplyCameraRotate(CameraRotateMessage msg)
    {
        if (streamCamera == null || msg == null) return;
        streamCamera.transform.Rotate(Vector3.up, msg.degrees, Space.World);
    }

    private void ApplyRemove(RemoveFurnitureMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null) return;
        Destroy(go); _placedInstances.Remove(msg.instance_id);
        _ = SendJson(new RemoveResultMessage { success = true, instance_id = msg.instance_id, message = "Removed" });
        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    private void ApplySwapInstance(SwapInstanceMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var currentObject) || currentObject == null) return;
        var prefab = LoadPrefab(msg.prefab_path);
        if (prefab == null) return;

        var oldSlot = currentObject.GetComponent<FurnitureSlot>();
        int typeId = oldSlot != null ? oldSlot.typeId : 0;
        float carryMultiplier = (oldSlot != null && oldSlot.scaleMultiplier > 0f) ? oldSlot.scaleMultiplier : 1f;
        var t = currentObject.transform;

        GameObject instance = Instantiate(prefab, t.position, t.rotation, t.parent);
        Vector3 newBaseScale = instance.transform.localScale;
        instance.transform.localScale = newBaseScale * carryMultiplier;

        var slot = instance.GetComponent<FurnitureSlot>();
        if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
        slot.typeId = typeId; slot.styleId = msg.style_id; slot.label = msg.style_name;
        slot.instanceId = msg.instance_id; slot.prefabPath = msg.prefab_path;
        slot.baseScale = newBaseScale; slot.scaleMultiplier = carryMultiplier;

        Destroy(currentObject);
        _placedInstances[msg.instance_id] = instance;
        _ = SendJson(new SwapInstanceResultMessage { success = true, instance_id = msg.instance_id, message = $"Applied {msg.style_name}" });
        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    private void CaptureFullFloorPlan()
    {
        Camera cam = floorPlanCamera != null ? floorPlanCamera : streamCamera;
        if (cam == null) return;
        bool borrowingLiveCamera = floorPlanCamera == null;

        Bounds? bounds = ComputeRoomBounds();
        if (bounds == null) return;

        Vector3 prevPos = cam.transform.position; Quaternion prevRot = cam.transform.rotation;
        bool prevOrtho = cam.orthographic; float prevOrthoSize = cam.orthographicSize; RenderTexture prevTarget = cam.targetTexture;

        Bounds b = bounds.Value;
        const int w = 1280, h = 720;
        float aspect = (float)w / h;
        cam.transform.position = new Vector3(b.center.x, b.max.y + 5f, b.center.z);
        cam.transform.rotation = Quaternion.LookRotation(Vector3.down, Vector3.forward);
        cam.orthographic = true;
        cam.orthographicSize = Mathf.Max(b.extents.z, b.extents.x / aspect) * 1.1f;

        var rt = new RenderTexture(w, h, 24); var tex = new Texture2D(w, h, TextureFormat.RGB24, false); var prevActive = RenderTexture.active;
        cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply(false);
        RenderTexture.active = prevActive; cam.targetTexture = prevTarget;

        if (borrowingLiveCamera) { cam.transform.position = prevPos; cam.transform.rotation = prevRot; cam.orthographic = prevOrtho; cam.orthographicSize = prevOrthoSize; }

        byte[] jpg = tex.EncodeToJPG(88); Destroy(rt); Destroy(tex);

        var allItems = new List<InstanceInfo>();
        foreach (var kvp in _placedInstances)
        {
            if (kvp.Value == null) continue;
            var slot = kvp.Value.GetComponent<FurnitureSlot>();
            Vector3 worldPos = kvp.Value.transform.position;
            allItems.Add(new InstanceInfo
            {
                instance_id = kvp.Key,
                type_id = slot ? slot.typeId : 0,
                style_id = slot ? slot.styleId : 0,
                style_name = slot ? slot.label : "",
                prefab_path = slot ? slot.prefabPath : "",
                world_x = worldPos.x,
                world_y = worldPos.y,
                world_z = worldPos.z,
                rotation_y_deg = kvp.Value.transform.eulerAngles.y,
                scale = kvp.Value.transform.localScale.x,
                scale_multiplier = slot && slot.scaleMultiplier > 0f ? slot.scaleMultiplier : 1f,
            });
        }
        _ = SendJson(new FloorPlanSnapshotMessage { image = Convert.ToBase64String(jpg), width = w, height = h, items = allItems.ToArray() });
    }

    private Bounds? ComputeRoomBounds()
    {
        Bounds? result = null;
        void Encapsulate(Bounds bb) { if (result == null) result = bb; else { var r = result.Value; r.Encapsulate(bb); result = r; } }
        foreach (var kvp in _placedInstances) { if (kvp.Value == null) continue; foreach (var r in kvp.Value.GetComponentsInChildren<Renderer>()) Encapsulate(r.bounds); }
        foreach (var r in FindObjectsOfType<Renderer>()) { if (((1 << r.gameObject.layer) & floorLayerMask) != 0) Encapsulate(r.bounds); }
        return result;
    }

    private IEnumerator StreamFramesLoop()
    {
        var wait = new WaitForSeconds(Mathf.Max(0.05f, 1f / Mathf.Max(0.1f, streamFps)));
        while (true)
        {
            yield return wait;
            if (_socket == null || _socket.State != WebSocketState.Open) continue;
            CaptureAndSendFrame();
            SendInstancesUpdate();
        }
    }

    private void CaptureAndSendFrame()
    {
        var prevTarget = streamCamera.targetTexture; var prevActive = RenderTexture.active;
        streamCamera.targetTexture = _frameRenderTexture; streamCamera.Render(); RenderTexture.active = _frameRenderTexture;
        _frameTexture.ReadPixels(new Rect(0, 0, streamWidth, streamHeight), 0, 0); _frameTexture.Apply(false);
        streamCamera.targetTexture = prevTarget; RenderTexture.active = prevActive;
        byte[] jpg = _frameTexture.EncodeToJPG(streamJpegQuality);
        _ = SendJson(new FrameMessage { image = Convert.ToBase64String(jpg), width = streamWidth, height = streamHeight });
    }

    private void SendInstancesUpdate()
    {
        var list = new List<InstanceInfo>();
        foreach (var kvp in _placedInstances)
        {
            if (kvp.Value == null) continue;

            Vector3 vp = streamCamera.WorldToViewportPoint(kvp.Value.transform.position);

            // --- DEBUGGING ---
            // Temporarily comment out the vp.z < 0 check to force the dots to send
            // if (vp.z < 0) continue; 

            var slot = kvp.Value.GetComponent<FurnitureSlot>();
            Vector3 worldPos = kvp.Value.transform.position;
            list.Add(new InstanceInfo
            {
                instance_id = kvp.Key,
                type_id = slot ? slot.typeId : 0,
                style_id = slot ? slot.styleId : 0,
                style_name = slot ? slot.label : "",
                prefab_path = slot ? slot.prefabPath : "",
                viewport_x = vp.x,
                viewport_y = 1f - vp.y,
                world_x = worldPos.x,
                world_y = worldPos.y,
                world_z = worldPos.z,
                rotation_y_deg = kvp.Value.transform.eulerAngles.y,
                scale = kvp.Value.transform.localScale.x,
                scale_multiplier = slot && slot.scaleMultiplier > 0f ? slot.scaleMultiplier : 1f,
            });
        }

        // ADD THIS LOG
        Debug.Log($"[FurnitureSync] Sending {list.Count} instances to React.");

        _ = SendJson(new InstancesMessage { items = list.ToArray() });
    }

    private void SavePlacedInstances()
    {
        var entries = new List<PlacedInstanceEntry>();
        foreach (var kvp in _placedInstances)
        {
            if (kvp.Value == null) continue;
            var slot = kvp.Value.GetComponent<FurnitureSlot>();
            var t = kvp.Value.transform;
            entries.Add(new PlacedInstanceEntry
            {
                instance_id = kvp.Key,
                type_id = slot ? slot.typeId : 0,
                style_id = slot ? slot.styleId : 0,
                style_name = slot ? slot.label : "",
                prefab_path = slot ? slot.prefabPath : "",
                px = t.position.x,
                py = t.position.y,
                pz = t.position.z,
                rx = t.rotation.x,
                ry = t.rotation.y,
                rz = t.rotation.z,
                rw = t.rotation.w,
                sx = t.localScale.x,
                sy = t.localScale.y,
                sz = t.localScale.z,
                base_sx = slot ? slot.baseScale.x : t.localScale.x,
                base_sy = slot ? slot.baseScale.y : t.localScale.y,
                base_sz = slot ? slot.baseScale.z : t.localScale.z,
                scale_multiplier = slot && slot.scaleMultiplier > 0f ? slot.scaleMultiplier : 1f,
            });
        }
        var file = new PlacedInstancesFile { items = entries.ToArray(), saved_at = DateTime.UtcNow.ToString("o") };
        string path = Path.Combine(Application.persistentDataPath, placedInstancesFileName);
        try { File.WriteAllText(path, JsonUtility.ToJson(file)); } catch (Exception e) { Debug.LogWarning($"[FurnitureSync] Failed to auto-save placed instances: {e.Message}"); }
    }

    private void LoadPlacedInstancesIfPresent()
    {
        string path = Path.Combine(Application.persistentDataPath, placedInstancesFileName);
        if (!File.Exists(path)) return;
        try
        {
            var file = JsonUtility.FromJson<PlacedInstancesFile>(File.ReadAllText(path));
            if (file?.items == null) return;
            foreach (var entry in file.items)
            {
                if (string.IsNullOrEmpty(entry.prefab_path)) continue;
                var prefab = LoadPrefab(entry.prefab_path);
                if (prefab == null) continue;

                var pos = new Vector3(entry.px, entry.py, entry.pz); var rot = new Quaternion(entry.rx, entry.ry, entry.rz, entry.rw);
                var instance = Instantiate(prefab, pos, rot);
                instance.transform.localScale = new Vector3(entry.sx, entry.sy, entry.sz);
                instance.name = $"{entry.style_name}";

                var slot = instance.GetComponent<FurnitureSlot>();
                if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
                slot.typeId = entry.type_id; slot.styleId = entry.style_id; slot.label = entry.style_name;
                slot.instanceId = entry.instance_id; slot.prefabPath = entry.prefab_path;
                bool hasBaseScale = entry.base_sx != 0f || entry.base_sy != 0f || entry.base_sz != 0f;
                slot.baseScale = hasBaseScale ? new Vector3(entry.base_sx, entry.base_sy, entry.base_sz) : instance.transform.localScale;
                slot.scaleMultiplier = entry.scale_multiplier > 0f ? entry.scale_multiplier : 1f;

                _placedInstances[entry.instance_id] = instance;
            }
        }
        catch (Exception e) { Debug.LogWarning($"[FurnitureSync] Failed to load saved placed instances: {e.Message}"); }
    }

    private void SaveLayoutAndSignalVr()
    {
        var allSlots = FindObjectsOfType<FurnitureSlot>();
        var entries = new List<FurnitureLayoutEntry>();
        foreach (var slot in allSlots)
        {
            var t = slot.transform;
            entries.Add(new FurnitureLayoutEntry
            {
                instance_id = slot.instanceId,
                type_id = slot.typeId,
                style_id = slot.styleId,
                prefab_path = slot.prefabPath,
                px = t.position.x,
                py = t.position.y,
                pz = t.position.z,
                rx = t.rotation.x,
                ry = t.rotation.y,
                rz = t.rotation.z,
                rw = t.rotation.w,
                sx = t.localScale.x,
                sy = t.localScale.y,
                sz = t.localScale.z,
            });
        }
        var snapshot = new FurnitureLayoutSnapshot { items = entries.ToArray(), saved_at = DateTime.UtcNow.ToString("o") };
        string path = Path.Combine(Application.persistentDataPath, layoutFileName);

        try { File.WriteAllText(path, JsonUtility.ToJson(snapshot)); _ = SendJson(new LaunchVrReadyMessage { layout_path = path }); }
        catch (Exception e) { _ = SendJson(new StatusMessage { message = "Failed to save layout for VR: " + e.Message }); }
    }

    // ==========================================
    // --- WALL PAINTING LOGIC ---
    // ==========================================

    private void TogglePaintMode(bool active)
    {
        _isPaintMode = active;
        ClearWallSelection();
        Debug.Log($"[FurnitureSync] Paint Mode: {active}");
    }

    private void ApplyWallSelection(SelectWallMessage msg)
    {
        if (!_isPaintMode || streamCamera == null) return;

        // Prevent double-click deselect
        if (Time.time - _lastWallSelectTime < 0.2f) return;
        _lastWallSelectTime = Time.time;

        Vector3 viewportPoint = new Vector3(msg.viewport_x, 1f - msg.viewport_y, 0f);
        Ray ray = streamCamera.ViewportPointToRay(viewportPoint);

        if (Physics.Raycast(ray, out RaycastHit hit, 100f, wallLayerMask))
        {
            // Walk up the hierarchy to find the correct root parent (e.g. "Wall_W001")
            Transform root = hit.collider.transform;
            while (root.parent != null)
            {
                if (root.name.StartsWith("Wall_") || root.name.StartsWith("Window_") || root.name.StartsWith("Door_"))
                {
                    break; // Found the root
                }
                root = root.parent;
            }

            Debug.Log($"[FurnitureSync] Selected: {root.name}");
            ToggleWallSelection(root.gameObject);
        }
        else
        {
            Debug.Log("[FurnitureSync] Raycast missed. Are the walls set to the DX_Walls layer AND do they have MeshColliders?");
        }
    }

    private void ToggleWallSelection(GameObject wallRoot)
    {
        var renderers = wallRoot.GetComponentsInChildren<Renderer>();
        if (renderers.Length == 0) return;

        if (_selectedWalls.Contains(wallRoot))
        {
            // Deselect: Restore original color
            _selectedWalls.Remove(wallRoot);
            if (_originalWallColors.TryGetValue(wallRoot, out Color original))
            {
                foreach (var r in renderers)
                {
                    r.material.color = original;
                    r.material.SetColor("_EmissionColor", Color.black); // Turn off glow
                }
            }
        }
        else
        {
            // Select: Highlight with a BRIGHT CYAN glow
            _selectedWalls.Add(wallRoot);
            if (!_originalWallColors.ContainsKey(wallRoot))
                _originalWallColors[wallRoot] = renderers[0].material.color;

            foreach (var r in renderers)
            {
                r.material.color = new Color(0.0f, 0.8f, 1.0f);
                r.material.EnableKeyword("_EMISSION");
                r.material.SetColor("_EmissionColor", new Color(0.0f, 0.4f, 0.6f));
            }
        }

        Debug.Log($"[FurnitureSync] Wall selected/deselected. Total selected: {_selectedWalls.Count}");
        _ = SendJson(new WallSelectionMessage { count = _selectedWalls.Count });
    }

    private void ApplyWallColor(string hexColor)
    {
        if (ColorUtility.TryParseHtmlString(hexColor, out Color color))
        {
            foreach (var wallRoot in _selectedWalls)
            {
                var renderers = wallRoot.GetComponentsInChildren<Renderer>();
                foreach (var r in renderers)
                {
                    r.material.color = color;
                    r.material.SetColor("_EmissionColor", Color.black); // Turn off glow after painting
                }
                _originalWallColors[wallRoot] = color;
            }
            Debug.Log($"[FurnitureSync] Applied color {hexColor} to {_selectedWalls.Count} walls.");
        }
    }

    private void ClearWallSelection()
    {
        foreach (var wallRoot in _selectedWalls)
        {
            if (wallRoot != null && _originalWallColors.TryGetValue(wallRoot, out Color original))
            {
                var renderers = wallRoot.GetComponentsInChildren<Renderer>();
                foreach (var r in renderers)
                {
                    r.material.color = original;
                    r.material.SetColor("_EmissionColor", Color.black);
                }
            }
        }
        _selectedWalls.Clear();
        _originalWallColors.Clear();
        _ = SendJson(new WallSelectionMessage { count = 0 });
    }
}