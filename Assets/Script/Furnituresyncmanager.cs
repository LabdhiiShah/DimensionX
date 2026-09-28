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

/// <summary>
/// Connects to the Node.js bridge server as a WebSocket client. Handles:
///
///   1. "swap_furniture"  — swap the prefab in a tagged slot (catalog demo).
///   2. "place_furniture" — drag-and-drop a NEW piece from the website's
///      live view. Multiple instances of the same type_id are supported.
///   3. "move_furniture"  — reposition an EXISTING placed piece (by its
///      instance_id) by dragging its marker to a new spot on the live view.
///   4. "camera_pan" / "camera_zoom" — move the stream camera around, sent
///      from D-pad/zoom controls on the website.
///   5. "launch_vr"       — saves the full room layout and hands off to the
///      bridge server, which launches your native VR build.
///
/// It streams a low-res JPEG of streamCamera's view to the website a few
/// times a second, plus a list of where each placed instance currently
/// projects onto that view (so the website can show draggable markers).
///
/// Persistence: every placement/move auto-saves the current set of
/// drag-placed instances to disk, and reloads them on the next Start() —
/// so a Play-mode session's edits survive stopping and restarting Play.
/// This is separate from anything you placed via the Placement Tool while
/// NOT in Play mode, which is already part of the saved Scene as normal.
/// </summary>
public class FurnitureSyncManager : MonoBehaviour
{
    public static FurnitureSyncManager Instance { get; private set; }

    [Header("Bridge connection")]
    public string bridgeUrl = "ws://localhost:8765";
    public bool autoReconnect = true;
    public float reconnectDelaySeconds = 3f;

    [Header("Live view streaming")]
    [Tooltip("The LIVE camera used for the Design Room: drag-and-drop placement raycasts from this camera, and the website's arrow/zoom/rotate controls move THIS camera. Give it its own plain GameObject with nothing else on it (no XR/simulator scripts) — an in-room, roughly eye-level or elevated interior view works well for placing furniture precisely.")]
    public Camera streamCamera;
    [Tooltip("Optional — a SEPARATE, dedicated top-down camera used only when \"Save Design\" is pressed, to capture the whole room from directly above for the PDF. It is never shown live and is safe to leave with its Camera component permanently unchecked/disabled — capture still works, since it's rendered on demand via code. If left empty, streamCamera is temporarily borrowed and restored instead (works, but briefly repositions your live view while capturing).")]
    public Camera floorPlanCamera;
    public int streamWidth = 640;
    public int streamHeight = 360;
    [Tooltip("Frames per second sent to the website. Keep this low (3-8) — it's a design preview, not gameplay video.")]
    public float streamFps = 5f;
    [Range(1, 100)] public int streamJpegQuality = 70;

    [Header("Drag-and-drop placement")]
    [Tooltip("Only colliders on this layer are considered a valid drop surface.")]
    public LayerMask floorLayerMask = ~0;
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

    // ---------------- Message shapes ----------------

    [Serializable] private class MessageEnvelope { public string type; }

    [Serializable]
    private class SwapFurnitureMessage
    {
        public string type;
        public int type_id;
        public string type_name;
        public int style_id;
        public string style_name;
        public string prefab_path;
        public string requested_at;
    }

    [Serializable]
    private class SwapResultMessage
    {
        public string type = "swap_result";
        public int type_id;
        public bool success;
        public string message;
    }

    [Serializable]
    private class PlaceFurnitureMessage
    {
        public string type;
        public int type_id;
        public string type_name;
        public int style_id;
        public string style_name;
        public string prefab_path;
        public float viewport_x; // image-space, 0..1, origin top-left
        public float viewport_y;
        public string instance_id; // optional — server generates one if blank
    }

    [Serializable]
    private class PlaceResultMessage
    {
        public string type = "place_result";
        public bool success;
        public string instance_id;
        public string message;
        public float world_x, world_y, world_z;
    }

    [Serializable]
    private class MoveFurnitureMessage
    {
        public string type;
        public string instance_id;
        public float viewport_x;
        public float viewport_y;
    }

    [Serializable]
    private class MoveResultMessage
    {
        public string type = "move_result";
        public bool success;
        public string instance_id;
        public string message;
    }

    [Serializable]
    private class CameraPanMessage { public string type; public float dx; public float dz; }

    [Serializable]
    private class CameraZoomMessage { public string type; public float delta; }

    [Serializable]
    private class CameraRotateMessage { public string type; public float degrees; }

    [Serializable]
    private class RemoveFurnitureMessage { public string type; public string instance_id; }

    [Serializable]
    private class RemoveResultMessage { public string type = "remove_result"; public bool success; public string instance_id; public string message; }

    [Serializable]
    private class SwapInstanceMessage { public string type; public string instance_id; public int style_id; public string style_name; public string prefab_path; }

    [Serializable]
    private class SwapInstanceResultMessage { public string type = "swap_instance_result"; public bool success; public string instance_id; public string message; }

    [Serializable]
    private class RotateInstanceMessage { public string type; public string instance_id; public float degrees; }

    [Serializable]
    private class ScaleInstanceMessage { public string type; public string instance_id; public float delta; } // e.g. +0.1 = grow 10%, -0.1 = shrink 10%

    [Serializable]
    private class InstanceTransformResultMessage { public string type = "instance_transform_result"; public bool success; public string instance_id; public string message; }

    [Serializable]
    private class InstanceInfo
    {
        public string instance_id;
        public int type_id;
        public string style_name;
        public float viewport_x;
        public float viewport_y;
        // World-space details, added so the website's "Save Design" PDF
        // export can list real placement/orientation/size instead of just
        // the on-screen marker position.
        public float world_x;
        public float world_y;
        public float world_z;
        public float rotation_y_deg; // yaw only — matches ApplyRotateInstance, which only rotates around world-up
        public float scale;          // absolute local scale x — exact number, useful for rebuilding
        public float scale_multiplier; // size relative to this piece's own base/authored scale — 1 = original size, human-readable
    }

    [Serializable]
    private class InstancesMessage { public string type = "instances"; public InstanceInfo[] items; }

    [Serializable]
    private class FrameMessage { public string type = "frame"; public string image; public int width; public int height; }

    [Serializable]
    private class HelloMessage { public string type; public string role; }

    [Serializable]
    private class LaunchVrReadyMessage { public string type = "launch_vr_ready"; public string layout_path; }

    [Serializable]
    private class StatusMessage { public string type = "status"; public string message; }

    [Serializable]
    private class FloorPlanSnapshotMessage { public string type = "floorplan_snapshot"; public string image; public int width; public int height; public InstanceInfo[] items; }

    // Full-room snapshot, written when you click "View in VR" (everything,
    // including catalog-swap slots — the VR build wants the whole room).
    // LayoutEntry/LayoutSnapshot are now shared with the VR build — see
    // FurnitureLayoutModels.cs (FurnitureLayoutEntry / FurnitureLayoutSnapshot).

    // Lightweight snapshot of just the drag-placed instances, auto-saved
    // after every placement/move so a Play session's edits survive a
    // Stop + Play cycle.
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

        if (autoLoadPlacedInstancesOnStart) LoadPlacedInstancesIfPresent();

        if (streamCamera != null)
        {
            StartCoroutine(StreamFramesLoop());
            WarnIfStreamCameraLooksShared();
        }
        else Debug.LogWarning("[FurnitureSync] No Stream Camera assigned — live view won't be sent to the website.");

        await ConnectLoop(_cts.Token);
    }

    // The single most common setup bug: the design camera should be a
    // plain, dedicated Camera that ONLY this script moves (via camera_pan
    // / camera_zoom / camera_rotate). If it's the same camera your XR
    // Device Simulator (or a real headset) drives, the two will fight —
    // the website nudges it one way, the simulator's input yanks it back.
    // This can't know about XR packages specifically without depending on
    // them, but it CAN tell you, generically, if anything else is on this
    // GameObject that might be moving it.
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

    public void RegisterSlot(int typeId, GameObject go)
    {
        _slots[typeId] = go;
        Debug.Log($"[FurnitureSync] Registered slot for type_id {typeId}: {go.name}");
    }

    public void UnregisterSlot(int typeId, GameObject go)
    {
        if (_slots.TryGetValue(typeId, out var current) && current == go) _slots.Remove(typeId);
    }

    // ---------------- WebSocket connection ----------------

    private async Task ConnectLoop(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                _socket = new ClientWebSocket();
                Debug.Log($"[FurnitureSync] Connecting to {bridgeUrl} ...");
                await _socket.ConnectAsync(new Uri(bridgeUrl), token);
                Debug.Log("[FurnitureSync] Connected to bridge.");
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
                case "swap_furniture":
                    var swap = JsonUtility.FromJson<SwapFurnitureMessage>(json);
                    RunOnMainThread(() => ApplySwap(swap));
                    break;
                case "place_furniture":
                    var place = JsonUtility.FromJson<PlaceFurnitureMessage>(json);
                    RunOnMainThread(() => ApplyPlacement(place));
                    break;
                case "move_furniture":
                    var move = JsonUtility.FromJson<MoveFurnitureMessage>(json);
                    RunOnMainThread(() => ApplyMove(move));
                    break;
                case "camera_pan":
                    var pan = JsonUtility.FromJson<CameraPanMessage>(json);
                    RunOnMainThread(() => ApplyCameraPan(pan));
                    break;
                case "camera_zoom":
                    var zoom = JsonUtility.FromJson<CameraZoomMessage>(json);
                    RunOnMainThread(() => ApplyCameraZoom(zoom));
                    break;
                case "camera_rotate":
                    var rotate = JsonUtility.FromJson<CameraRotateMessage>(json);
                    RunOnMainThread(() => ApplyCameraRotate(rotate));
                    break;
                case "remove_furniture":
                    var remove = JsonUtility.FromJson<RemoveFurnitureMessage>(json);
                    RunOnMainThread(() => ApplyRemove(remove));
                    break;
                case "swap_instance":
                    var swapInst = JsonUtility.FromJson<SwapInstanceMessage>(json);
                    RunOnMainThread(() => ApplySwapInstance(swapInst));
                    break;
                case "rotate_instance":
                    var rotateInst = JsonUtility.FromJson<RotateInstanceMessage>(json);
                    RunOnMainThread(() => ApplyRotateInstance(rotateInst));
                    break;
                case "scale_instance":
                    var scaleInst = JsonUtility.FromJson<ScaleInstanceMessage>(json);
                    RunOnMainThread(() => ApplyScaleInstance(scaleInst));
                    break;
                case "launch_vr":
                    RunOnMainThread(SaveLayoutAndSignalVr);
                    break;
                case "capture_floorplan":
                    RunOnMainThread(CaptureFullFloorPlan);
                    break;
                case "hello_ack":
                    Debug.Log("[FurnitureSync] Bridge acknowledged handshake.");
                    break;
                default:
                    Debug.Log($"[FurnitureSync] Unhandled message type: {envelope.type}");
                    break;
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

    // ---------------- Prefab loading ----------------

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

    // ---------------- Swapping an existing slot (catalog demo) ----------------

    private void ApplySwap(SwapFurnitureMessage msg)
    {
        if (msg == null) return;

        if (!_slots.TryGetValue(msg.type_id, out var currentObject) || currentObject == null)
        {
            Debug.LogWarning($"[FurnitureSync] No registered slot for type_id {msg.type_id} ({msg.type_name}).");
            _ = SendJson(new SwapResultMessage { type_id = msg.type_id, success = false, message = "No slot registered for this type_id" });
            return;
        }

        var prefab = LoadPrefab(msg.prefab_path);
        if (prefab == null)
        {
            Debug.LogError($"[FurnitureSync] Could not load prefab at path: {msg.prefab_path}");
            _ = SendJson(new SwapResultMessage { type_id = msg.type_id, success = false, message = "Prefab not found: " + msg.prefab_path });
            return;
        }

        var t = currentObject.transform;
        Vector3 position = t.position;
        Quaternion rotation = t.rotation; // preserve whatever rotation was already set for this slot
        Vector3 localScale = t.localScale;
        Transform parent = t.parent;
        int siblingIndex = t.GetSiblingIndex();
        string previousName = currentObject.name;

        Destroy(currentObject);

        GameObject instance = Instantiate(prefab, position, rotation, parent);
        instance.transform.localScale = localScale;
        instance.transform.SetSiblingIndex(siblingIndex);
        instance.name = previousName;

        var slot = instance.GetComponent<FurnitureSlot>();
        if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
        slot.typeId = msg.type_id;
        slot.styleId = msg.style_id;
        slot.label = msg.style_name;
        slot.prefabPath = msg.prefab_path;

        RegisterSlot(msg.type_id, instance);

        Debug.Log($"[FurnitureSync] Swapped type_id {msg.type_id} -> {msg.style_name} at pos {position}");
        _ = SendJson(new SwapResultMessage { type_id = msg.type_id, success = true, message = $"Applied {msg.style_name}" });
    }

    // ---------------- Drag-and-drop placement (new instances) ----------------

    private void ApplyPlacement(PlaceFurnitureMessage msg)
    {
        if (msg == null) return;

        if (streamCamera == null)
        {
            _ = SendJson(new PlaceResultMessage { success = false, message = "No stream camera configured on the Unity side" });
            return;
        }

        var prefab = LoadPrefab(msg.prefab_path);
        if (prefab == null)
        {
            Debug.LogError($"[FurnitureSync] Could not load prefab at path: {msg.prefab_path}");
            _ = SendJson(new PlaceResultMessage { success = false, message = "Prefab not found: " + msg.prefab_path });
            return;
        }

        Vector3 viewportPoint = new Vector3(msg.viewport_x, 1f - msg.viewport_y, 0f); // image-space -> viewport-space
        Ray ray = streamCamera.ViewportPointToRay(viewportPoint);

        if (!Physics.Raycast(ray, out RaycastHit hit, raycastMaxDistance, floorLayerMask))
        {
            _ = SendJson(new PlaceResultMessage { success = false, message = "Drop point didn't land on the floor" });
            return;
        }

        string instanceId = string.IsNullOrEmpty(msg.instance_id) ? Guid.NewGuid().ToString("N") : msg.instance_id;

        // Use the PREFAB's own default rotation, not world-identity — a
        // prefab's resting orientation is whatever the artist modeled it
        // at, and forcing identity here is what caused pieces to look
        // tilted for prefabs that weren't authored perfectly upright.
        GameObject instance = Instantiate(prefab, hit.point, prefab.transform.rotation);
        instance.name = $"{msg.type_name} ({msg.style_name}) [{instanceId.Substring(0, 6)}]";

        var slot = instance.GetComponent<FurnitureSlot>();
        if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
        slot.typeId = msg.type_id;
        slot.styleId = msg.style_id;
        slot.label = msg.style_name;
        slot.instanceId = instanceId;
        slot.prefabPath = msg.prefab_path;
        slot.baseScale = instance.transform.localScale; // whatever the prefab's own authored scale is
        slot.scaleMultiplier = 1f;

        _placedInstances[instanceId] = instance;

        Debug.Log($"[FurnitureSync] Placed {msg.type_name}/{msg.style_name} (instance {instanceId}) at {hit.point}");
        _ = SendJson(new PlaceResultMessage { success = true, instance_id = instanceId, message = $"Placed {msg.style_name}", world_x = hit.point.x, world_y = hit.point.y, world_z = hit.point.z });

        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    // ---------------- Repositioning an existing instance ----------------

    private void ApplyMove(MoveFurnitureMessage msg)
    {
        if (msg == null) return;

        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null)
        {
            _ = SendJson(new MoveResultMessage { success = false, instance_id = msg.instance_id, message = "Unknown instance_id — was it placed this session?" });
            return;
        }
        if (streamCamera == null)
        {
            _ = SendJson(new MoveResultMessage { success = false, instance_id = msg.instance_id, message = "No stream camera configured" });
            return;
        }

        Vector3 viewportPoint = new Vector3(msg.viewport_x, 1f - msg.viewport_y, 0f);
        Ray ray = streamCamera.ViewportPointToRay(viewportPoint);
        if (!Physics.Raycast(ray, out RaycastHit hit, raycastMaxDistance, floorLayerMask))
        {
            _ = SendJson(new MoveResultMessage { success = false, instance_id = msg.instance_id, message = "Drop point didn't land on the floor" });
            return;
        }

        go.transform.position = hit.point; // rotation/scale untouched — just relocating
        Debug.Log($"[FurnitureSync] Moved instance {msg.instance_id} to {hit.point}");
        _ = SendJson(new MoveResultMessage { success = true, instance_id = msg.instance_id, message = "Moved" });

        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    // ---------------- Rotating/scaling a specific placed instance ----------------

    private void ApplyRotateInstance(RotateInstanceMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null)
        {
            Debug.LogWarning($"[FurnitureSync] rotate_instance: unknown instance_id {msg?.instance_id}");
            _ = SendJson(new InstanceTransformResultMessage { success = false, instance_id = msg.instance_id, message = "Unknown instance_id" });
            return;
        }
        go.transform.Rotate(Vector3.up, msg.degrees, Space.World);
        Debug.Log($"[FurnitureSync] Rotated instance {msg.instance_id} by {msg.degrees}°, now facing {go.transform.eulerAngles}");
        _ = SendJson(new InstanceTransformResultMessage { success = true, instance_id = msg.instance_id, message = "Rotated" });
        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    private void ApplyScaleInstance(ScaleInstanceMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null)
        {
            Debug.LogWarning($"[FurnitureSync] scale_instance: unknown instance_id {msg?.instance_id}");
            _ = SendJson(new InstanceTransformResultMessage { success = false, instance_id = msg.instance_id, message = "Unknown instance_id" });
            return;
        }

        var slot = go.GetComponent<FurnitureSlot>();
        if (slot == null) slot = go.AddComponent<FurnitureSlot>();

        // Safety net for instances that existed before baseScale was tracked
        // (e.g. reloaded from an older save file): treat the CURRENT scale
        // as the base, so resizing starts behaving correctly from here on.
        if (slot.baseScale == Vector3.zero) slot.baseScale = go.transform.localScale;
        if (slot.scaleMultiplier <= 0f) slot.scaleMultiplier = 1f;

        // Resize relative to this instance's OWN base scale, not an
        // absolute number — different prefabs are very often authored at
        // wildly different native scales, so clamping an absolute value
        // either jumped huge amounts or got permanently stuck at the clamp
        // on the very first click. A multiplier of the piece's own base
        // scale behaves sensibly no matter what that base scale is.
        float newMultiplier = Mathf.Clamp(slot.scaleMultiplier * (1f + msg.delta), minInstanceScale, maxInstanceScale);
        slot.scaleMultiplier = newMultiplier;
        go.transform.localScale = slot.baseScale * newMultiplier;

        Debug.Log($"[FurnitureSync] Scaled instance {msg.instance_id} by delta={msg.delta}, now {newMultiplier:0.00}x base ({go.transform.localScale})");
        _ = SendJson(new InstanceTransformResultMessage { success = true, instance_id = msg.instance_id, message = "Scaled" });
        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    // ---------------- Camera pan/zoom ----------------

    private void ApplyCameraPan(CameraPanMessage msg)
    {
        if (streamCamera == null) { Debug.LogWarning("[FurnitureSync] camera_pan received but no Stream Camera assigned."); return; }
        if (msg == null) return;
        Vector3 right = streamCamera.transform.right;
        Vector3 forwardFlat = Vector3.ProjectOnPlane(streamCamera.transform.forward, Vector3.up);
        if (forwardFlat.sqrMagnitude < 0.0001f) forwardFlat = Vector3.forward; // camera looking straight down
        forwardFlat.Normalize();
        Vector3 before = streamCamera.transform.position;
        streamCamera.transform.position += (right * msg.dx + forwardFlat * msg.dz) * cameraPanSpeed;
        Debug.Log($"[FurnitureSync] camera_pan dx={msg.dx} dz={msg.dz} -> camera moved {before} to {streamCamera.transform.position}");
    }

    private void ApplyCameraZoom(CameraZoomMessage msg)
    {
        if (streamCamera == null) { Debug.LogWarning("[FurnitureSync] camera_zoom received but no Stream Camera assigned."); return; }
        if (msg == null) return;
        if (streamCamera.orthographic)
        {
            float before = streamCamera.orthographicSize;
            streamCamera.orthographicSize = Mathf.Clamp(streamCamera.orthographicSize + msg.delta * cameraZoomSpeed, minOrthographicSize, maxOrthographicSize);
            Debug.Log($"[FurnitureSync] camera_zoom delta={msg.delta} -> orthographicSize {before} to {streamCamera.orthographicSize}");
        }
        else
        {
            streamCamera.transform.position += streamCamera.transform.forward * msg.delta * cameraZoomSpeed;
            Debug.Log($"[FurnitureSync] camera_zoom delta={msg.delta} -> camera (perspective) dollied, now at {streamCamera.transform.position}");
        }
    }

    private void ApplyCameraRotate(CameraRotateMessage msg)
    {
        if (streamCamera == null) { Debug.LogWarning("[FurnitureSync] camera_rotate received but no Stream Camera assigned."); return; }
        if (msg == null) return;
        // Turns the camera in place around the world up-axis, like turning
        // your head — lets you look around without moving position.
        streamCamera.transform.Rotate(Vector3.up, msg.degrees, Space.World);
        Debug.Log($"[FurnitureSync] camera_rotate degrees={msg.degrees} -> camera now facing {streamCamera.transform.eulerAngles}");
    }

    // ---------------- Removing a placed instance ----------------

    private void ApplyRemove(RemoveFurnitureMessage msg)
    {
        if (msg == null) return;

        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null)
        {
            Debug.LogWarning($"[FurnitureSync] remove_furniture: unknown instance_id {msg?.instance_id}");
            _ = SendJson(new RemoveResultMessage { success = false, instance_id = msg.instance_id, message = "Unknown instance_id — was it placed this session?" });
            return;
        }

        Destroy(go);
        _placedInstances.Remove(msg.instance_id);
        Debug.Log($"[FurnitureSync] Removed instance {msg.instance_id}");
        _ = SendJson(new RemoveResultMessage { success = true, instance_id = msg.instance_id, message = "Removed" });

        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    // ---------------- Swapping the style of ONE specific placed instance ----------------
    // Unlike ApplySwap (which targets a single type-keyed demo slot), this
    // targets an exact instance_id — so it stays unambiguous even when
    // multiple pieces of the same type_id exist (e.g. two beds).

    private void ApplySwapInstance(SwapInstanceMessage msg)
    {
        if (msg == null) return;

        if (!_placedInstances.TryGetValue(msg.instance_id, out var currentObject) || currentObject == null)
        {
            Debug.LogWarning($"[FurnitureSync] swap_instance: unknown instance_id {msg?.instance_id}");
            _ = SendJson(new SwapInstanceResultMessage { success = false, instance_id = msg.instance_id, message = "Unknown instance_id" });
            return;
        }

        var prefab = LoadPrefab(msg.prefab_path);
        if (prefab == null)
        {
            Debug.LogError($"[FurnitureSync] Could not load prefab at path: {msg.prefab_path}");
            _ = SendJson(new SwapInstanceResultMessage { success = false, instance_id = msg.instance_id, message = "Prefab not found: " + msg.prefab_path });
            return;
        }

        var oldSlot = currentObject.GetComponent<FurnitureSlot>();
        int typeId = oldSlot != null ? oldSlot.typeId : 0;
        float carryMultiplier = (oldSlot != null && oldSlot.scaleMultiplier > 0f) ? oldSlot.scaleMultiplier : 1f;

        var t = currentObject.transform;
        Vector3 position = t.position;
        Quaternion rotation = t.rotation; // preserve however this instance was rotated/placed
        Transform parent = t.parent;

        Destroy(currentObject);

        GameObject instance = Instantiate(prefab, position, rotation, parent);
        Vector3 newBaseScale = instance.transform.localScale; // this style's own authored/default scale
        instance.transform.localScale = newBaseScale * carryMultiplier;
        instance.name = $"{msg.style_name} [{msg.instance_id.Substring(0, Math.Min(6, msg.instance_id.Length))}]";

        var slot = instance.GetComponent<FurnitureSlot>();
        if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
        slot.typeId = typeId;
        slot.styleId = msg.style_id;
        slot.label = msg.style_name;
        slot.instanceId = msg.instance_id;
        slot.prefabPath = msg.prefab_path;
        slot.baseScale = newBaseScale;
        slot.scaleMultiplier = carryMultiplier;

        _placedInstances[msg.instance_id] = instance;

        Debug.Log($"[FurnitureSync] Swapped instance {msg.instance_id} -> {msg.style_name}");
        _ = SendJson(new SwapInstanceResultMessage { success = true, instance_id = msg.instance_id, message = $"Applied {msg.style_name}" });

        if (autoSavePlacedInstances) SavePlacedInstances();
    }

    // ---------------- On-demand full floor plan capture (for Save Design) ----------------
    // Unlike the regular streamed frame (whatever the design camera is
    // currently panned/zoomed to), this temporarily snaps the camera to a
    // straight-down view that fits the WHOLE room, grabs one high-res
    // shot, then puts the camera back exactly where it was.

    private void CaptureFullFloorPlan()
    {
        Camera cam = floorPlanCamera != null ? floorPlanCamera : streamCamera;
        if (cam == null)
        {
            _ = SendJson(new StatusMessage { message = "Can't capture a floor plan — assign a Floor Plan Camera (or at least a Stream Camera)." });
            return;
        }
        bool borrowingLiveCamera = floorPlanCamera == null; // only true if we had to repurpose the live design camera

        Bounds? bounds = ComputeRoomBounds();
        if (bounds == null)
        {
            _ = SendJson(new StatusMessage { message = "Nothing to capture yet — place some furniture, or check that the floor's Layer is included in floorLayerMask." });
            return;
        }

        // Only save/restore camera state if we're temporarily borrowing the
        // LIVE design camera — a dedicated Floor Plan Camera is never seen
        // live, so there's nothing that needs preserving on it.
        Vector3 prevPos = cam.transform.position;
        Quaternion prevRot = cam.transform.rotation;
        bool prevOrtho = cam.orthographic;
        float prevOrthoSize = cam.orthographicSize;
        RenderTexture prevTarget = cam.targetTexture;

        Bounds b = bounds.Value;
        const int w = 1280, h = 720;
        float aspect = (float)w / h;

        cam.transform.position = new Vector3(b.center.x, b.max.y + 5f, b.center.z);
        cam.transform.rotation = Quaternion.LookRotation(Vector3.down, Vector3.forward);
        cam.orthographic = true;
        // pick whichever axis needs more room, with ~10% padding, so the whole room fits either way
        cam.orthographicSize = Mathf.Max(b.extents.z, b.extents.x / aspect) * 1.1f;

        var rt = new RenderTexture(w, h, 24);
        var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
        var prevActive = RenderTexture.active;

        cam.targetTexture = rt;
        cam.Render();
        RenderTexture.active = rt;
        tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
        tex.Apply(false);

        RenderTexture.active = prevActive;
        cam.targetTexture = prevTarget;

        if (borrowingLiveCamera)
        {
            cam.transform.position = prevPos;
            cam.transform.rotation = prevRot;
            cam.orthographic = prevOrtho;
            cam.orthographicSize = prevOrthoSize;
        }

        byte[] jpg = tex.EncodeToJPG(88);
        Destroy(rt);
        Destroy(tex);

        // Gather EVERY currently-placed instance, fresh, with no
        // behind-camera or off-screen filtering — this is what makes the
        // PDF's furniture schedule always complete, regardless of what the
        // live design camera happens to be framing at the time.
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
                style_name = slot ? slot.label : "",
                world_x = worldPos.x,
                world_y = worldPos.y,
                world_z = worldPos.z,
                rotation_y_deg = kvp.Value.transform.eulerAngles.y,
                scale = kvp.Value.transform.localScale.x,
                scale_multiplier = slot && slot.scaleMultiplier > 0f ? slot.scaleMultiplier : 1f,
            });
        }

        Debug.Log($"[FurnitureSync] Captured full floor plan ({w}x{h}, room bounds {b.size}, {allItems.Count} furniture item(s)) using {(borrowingLiveCamera ? "Stream Camera (temporarily repositioned)" : "dedicated Floor Plan Camera")}.");
        _ = SendJson(new FloorPlanSnapshotMessage { image = Convert.ToBase64String(jpg), width = w, height = h, items = allItems.ToArray() });
    }

    private Bounds? ComputeRoomBounds()
    {
        Bounds? result = null;
        void Encapsulate(Bounds bb) { if (result == null) result = bb; else { var r = result.Value; r.Encapsulate(bb); result = r; } }

        foreach (var kvp in _placedInstances)
        {
            if (kvp.Value == null) continue;
            foreach (var r in kvp.Value.GetComponentsInChildren<Renderer>()) Encapsulate(r.bounds);
        }
        // Also include whatever's on the floor's layer, so an empty room
        // still frames sensibly instead of capturing nothing.
        foreach (var r in FindObjectsOfType<Renderer>())
        {
            if (((1 << r.gameObject.layer) & floorLayerMask) != 0) Encapsulate(r.bounds);
        }
        return result;
    }



    // ---------------- Live view streaming ----------------

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
        var prevTarget = streamCamera.targetTexture;
        var prevActive = RenderTexture.active;

        streamCamera.targetTexture = _frameRenderTexture;
        streamCamera.Render();
        RenderTexture.active = _frameRenderTexture;
        _frameTexture.ReadPixels(new Rect(0, 0, streamWidth, streamHeight), 0, 0);
        _frameTexture.Apply(false);

        streamCamera.targetTexture = prevTarget;
        RenderTexture.active = prevActive;

        byte[] jpg = _frameTexture.EncodeToJPG(streamJpegQuality);
        _ = SendJson(new FrameMessage { image = Convert.ToBase64String(jpg), width = streamWidth, height = streamHeight });
    }

    private int _instanceUpdateLogCounter = 0;
    private void SendInstancesUpdate()
    {
        var list = new List<InstanceInfo>();
        foreach (var kvp in _placedInstances)
        {
            if (kvp.Value == null) continue;
            Vector3 vp = streamCamera.WorldToViewportPoint(kvp.Value.transform.position);
            if (vp.z < 0) continue; // behind the camera, don't show a marker for it
            var slot = kvp.Value.GetComponent<FurnitureSlot>();
            Vector3 worldPos = kvp.Value.transform.position;
            list.Add(new InstanceInfo
            {
                instance_id = kvp.Key,
                type_id = slot ? slot.typeId : 0,
                style_name = slot ? slot.label : "",
                viewport_x = vp.x,
                viewport_y = 1f - vp.y, // viewport-space -> image-space
                world_x = worldPos.x,
                world_y = worldPos.y,
                world_z = worldPos.z,
                rotation_y_deg = kvp.Value.transform.eulerAngles.y,
                scale = kvp.Value.transform.localScale.x,
                scale_multiplier = slot && slot.scaleMultiplier > 0f ? slot.scaleMultiplier : 1f,
            });
        }
        // Log roughly once a second (every ~5 calls at 5fps) instead of every frame, so it's visible but not spammy.
        _instanceUpdateLogCounter++;
        if (_instanceUpdateLogCounter % 5 == 0)
            Debug.Log($"[FurnitureSync] Sending instances update: {_placedInstances.Count} tracked, {list.Count} in view.");
        _ = SendJson(new InstancesMessage { items = list.ToArray() });
    }

    // ---------------- Persistence for placed instances ----------------

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
        try { File.WriteAllText(path, JsonUtility.ToJson(file)); }
        catch (Exception e) { Debug.LogWarning($"[FurnitureSync] Failed to auto-save placed instances: {e.Message}"); }
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
                if (prefab == null) { Debug.LogWarning($"[FurnitureSync] Couldn't reload saved prefab: {entry.prefab_path}"); continue; }

                var pos = new Vector3(entry.px, entry.py, entry.pz);
                var rot = new Quaternion(entry.rx, entry.ry, entry.rz, entry.rw);
                var instance = Instantiate(prefab, pos, rot);
                instance.transform.localScale = new Vector3(entry.sx, entry.sy, entry.sz);
                instance.name = $"{entry.style_name} [{entry.instance_id.Substring(0, Math.Min(6, entry.instance_id.Length))}]";

                var slot = instance.GetComponent<FurnitureSlot>();
                if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
                slot.typeId = entry.type_id;
                slot.styleId = entry.style_id;
                slot.label = entry.style_name;
                slot.instanceId = entry.instance_id;
                slot.prefabPath = entry.prefab_path;
                // Fall back to the saved final scale (as if scale_multiplier were
                // always 1) for entries written before base scale was tracked.
                bool hasBaseScale = entry.base_sx != 0f || entry.base_sy != 0f || entry.base_sz != 0f;
                slot.baseScale = hasBaseScale ? new Vector3(entry.base_sx, entry.base_sy, entry.base_sz) : instance.transform.localScale;
                slot.scaleMultiplier = entry.scale_multiplier > 0f ? entry.scale_multiplier : 1f;

                _placedInstances[entry.instance_id] = instance;
            }
            Debug.Log($"[FurnitureSync] Restored {file.items.Length} previously placed instances from a past session.");
        }
        catch (Exception e) { Debug.LogWarning($"[FurnitureSync] Failed to load saved placed instances: {e.Message}"); }
    }

    // ---------------- VR handoff (full-room snapshot) ----------------

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

        try
        {
            File.WriteAllText(path, JsonUtility.ToJson(snapshot));
            Debug.Log($"[FurnitureSync] Layout saved ({entries.Count} items) to {path}");
            _ = SendJson(new LaunchVrReadyMessage { layout_path = path });
        }
        catch (Exception e)
        {
            Debug.LogError($"[FurnitureSync] Failed to save layout: {e.Message}");
            _ = SendJson(new StatusMessage { message = "Failed to save layout for VR: " + e.Message });
        }
    }
}