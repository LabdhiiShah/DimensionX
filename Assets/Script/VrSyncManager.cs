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
/// Lives in your VR scene. Does two jobs:
///
///   1. On Start, loads the room layout saved by the design app's
///      "View in VR" action and spawns the furniture (same job the old
///      VrLayoutLoader did).
///   2. Connects to the SAME bridge server as role "vr" (separate from the
///      design app's "unity" role), streams the VR camera's view back as
///      "vr_frame" messages a few times a second, and listens for
///      "swap_instance" / "remove_furniture" commands so a designer
///      watching the feed can change styles or delete furniture while
///      someone's walking through in the headset — the design app gets
///      the same update at the same time, since the bridge mirrors these
///      two commands to both.
///
/// SAME-SCENE MODE (automatic): if a FurnitureSyncManager is in this scene too (design app and XR rig
/// sharing one Unity scene, like the generated-house setup), this script does NOT reload
/// current_layout.json (the furniture already exists), and only streams while the website has asked
/// for a walkthrough ("enter_vr" / "exit_vr"). On "enter_vr" it moves the XR rig to the house's entrance
/// (FloorplanLoader.SpawnPosition) so the XR Device Simulator / headset starts inside the house.
///
/// Setup:
/// - Put this on an empty GameObject in your VR scene (replaces the old
///   VrLayoutLoader component — remove that if it's still there).
/// - Assign Stream Camera: for OpenXR/XR Origin, that's the "Main Camera"
///   under XR Origin > Camera Offset. Note this captures a normal MONO
///   view (not stereo) — it's a monitoring feed for the designer, not
///   meant to represent exactly what's rendered per-eye in the headset.
/// - This scene should NOT already contain the design-time furniture
///   objects — this script is the only thing that should populate them,
///   same rule as the old VrLayoutLoader.
/// - Furniture prefabs still need to exist under a Resources folder for
///   this to work in a real build — see the placement-path note below.
/// </summary>
public class VrSyncManager : MonoBehaviour
{
    [Header("Bridge connection")]
    public string bridgeUrl = "ws://localhost:8765";
    public bool autoReconnect = true;
    public float reconnectDelaySeconds = 3f;

    [Header("Layout loading")]
    [Tooltip("Used only if no command-line argument is provided (e.g. testing by pressing Play directly in this scene).")]
    public string fallbackFileName = "current_layout.json";
    [Tooltip("Parent transform new furniture gets spawned under. Leave empty to spawn at the scene root.")]
    public Transform spawnParent;

    [Header("Live view streaming")]
    [Tooltip("Usually the Main Camera under your XR Origin > Camera Offset. Captures a mono preview, not the stereo headset view.")]
    public Camera streamCamera;
    public int streamWidth = 640;
    public int streamHeight = 360;
    public float streamFps = 5f;
    [Range(1, 100)] public int streamJpegQuality = 70;

    [Header("Same-scene (XR Device Simulator) mode")]
    [Tooltip("The XR Origin (VR) object. On 'View in VR' it is moved to the generated house's entrance. Leave empty to keep it wherever the scene placed it.")]
    public Transform xrRig;
    [Tooltip("Added to the rig's Y when placing it. The old static scene had the rig at y = -1.15, which hints the simulator adds height on top of Camera Y Offset. If the eyes end up too high or too low, tune this.")]
    public float rigHeightOffset = 0f;
    [Tooltip("Stream from a mono spectator camera parented to Stream Camera instead of the XR camera itself (avoids stereo/XR side effects).")]
    public bool useSpectatorCamera = true;

    private ClientWebSocket _socket;
    private CancellationTokenSource _cts;
    private readonly Dictionary<string, GameObject> _placedInstances = new Dictionary<string, GameObject>();
    private readonly Queue<Action> _mainThreadQueue = new Queue<Action>();
    private readonly object _queueLock = new object();

    private Texture2D _frameTexture;
    private RenderTexture _frameRenderTexture;

    private bool _embedded;      // true when the design app (FurnitureSyncManager) lives in this same scene
    private bool _vrActive;      // embedded mode only streams while a walkthrough is running
    private Camera _captureCam;  // what we actually render for the website

    // ---------------- Message shapes ----------------

    [Serializable] private class MessageEnvelope { public string type; }
    [Serializable] private class HelloMessage { public string type; public string role; }

    [Serializable] private class SwapInstanceMessage { public string type; public string instance_id; public int style_id; public string style_name; public string prefab_path; }
    [Serializable] private class SwapInstanceResultMessage { public string type = "swap_instance_result"; public bool success; public string instance_id; public string message; }

    [Serializable] private class RemoveFurnitureMessage { public string type; public string instance_id; }
    [Serializable] private class RemoveResultMessage { public string type = "remove_result"; public bool success; public string instance_id; public string message; }

    [Serializable] private class VrFrameMessage { public string type = "vr_frame"; public string image; public int width; public int height; }

    [Serializable]
    private class VrInstanceInfo { public string instance_id; public int type_id; public string style_name; public float viewport_x; public float viewport_y; }
    [Serializable]
    private class VrInstancesMessage { public string type = "vr_instances"; public VrInstanceInfo[] items; }

    [Serializable]
    private class VrStatusMessage { public string type = "vr_status"; public bool active; public string message; }

    void Awake()
    {
        DontDestroyOnLoad(gameObject);
    }

    async void Start()
    {
        _embedded = FurnitureSyncManager.Instance != null;
        _vrActive = !_embedded; // a standalone VR build streams from the start, as before

        if (_embedded)
        {
            Debug.Log("[VrSync] Same-scene mode: the design app already owns the furniture, so the layout file is not reloaded.");
            if (FloorplanLoader.Instance != null) FloorplanLoader.Instance.OnHouseReady += MoveRigToSpawn;
        }
        else LoadInitialLayout();

        _cts = new CancellationTokenSource();
        _frameTexture = new Texture2D(streamWidth, streamHeight, TextureFormat.RGB24, false);
        _frameRenderTexture = new RenderTexture(streamWidth, streamHeight, 24);

        if (streamCamera != null) { SetUpCaptureCamera(); StartCoroutine(StreamLoop()); }
        else Debug.LogWarning("[VrSync] No Stream Camera assigned — the website's VR View tab won't receive anything.");

        await ConnectLoop(_cts.Token);
    }

    void OnDestroy()
    {
        if (FloorplanLoader.Instance != null) FloorplanLoader.Instance.OnHouseReady -= MoveRigToSpawn;
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

    // ---------------- Initial layout load ----------------

    private void LoadInitialLayout()
    {
        string path = ResolveLayoutPath();
        if (string.IsNullOrEmpty(path) || !File.Exists(path))
        {
            Debug.LogWarning($"[VrSync] No layout file found at '{path}'. Nothing will be spawned.");
            return;
        }

        FurnitureLayoutSnapshot snapshot;
        try { snapshot = JsonUtility.FromJson<FurnitureLayoutSnapshot>(File.ReadAllText(path)); }
        catch (Exception e) { Debug.LogError($"[VrSync] Failed to parse layout file: {e.Message}"); return; }

        if (snapshot?.items == null) { Debug.LogWarning("[VrSync] Layout file had no items."); return; }

        int spawned = 0;
        foreach (var entry in snapshot.items)
        {
            if (string.IsNullOrEmpty(entry.prefab_path)) continue;
            var prefab = LoadPrefab(entry.prefab_path);
            if (prefab == null)
            {
                Debug.LogWarning($"[VrSync] Couldn't load prefab '{entry.prefab_path}' — is it duplicated under Assets/Resources/?");
                continue;
            }

            var pos = new Vector3(entry.px, entry.py, entry.pz);
            var rot = new Quaternion(entry.rx, entry.ry, entry.rz, entry.rw);
            var instance = Instantiate(prefab, pos, rot, spawnParent);
            instance.transform.localScale = new Vector3(entry.sx, entry.sy, entry.sz);

            var slot = instance.GetComponent<FurnitureSlot>();
            if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
            slot.typeId = entry.type_id;
            slot.styleId = entry.style_id;
            slot.prefabPath = entry.prefab_path;
            slot.instanceId = entry.instance_id;

            if (!string.IsNullOrEmpty(entry.instance_id))
                _placedInstances[entry.instance_id] = instance; // trackable for live swap_instance/remove_furniture

            spawned++;
        }
        Debug.Log($"[VrSync] Spawned {spawned} of {snapshot.items.Length} furniture item(s) from {path}.");
    }

    private string ResolveLayoutPath()
    {
        var args = Environment.GetCommandLineArgs();
        for (int i = 1; i < args.Length; i++)
        {
            if (!args[i].StartsWith("-") && File.Exists(args[i])) return args[i];
        }
        return Path.Combine(Application.persistentDataPath, fallbackFileName);
    }

    private GameObject LoadPrefab(string prefabPath)
    {
#if UNITY_EDITOR
        return AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
#else
        return Resources.Load<GameObject>(ToResourcesRelativePath(prefabPath));
#endif
    }

    private string ToResourcesRelativePath(string assetPath)
    {
        string relative = assetPath;
        const string assetsPrefix = "Assets/";
        if (relative.StartsWith(assetsPrefix)) relative = relative.Substring(assetsPrefix.Length);
        if (relative.EndsWith(".prefab")) relative = relative.Substring(0, relative.Length - ".prefab".Length);
        return relative;
    }

    // ---------------- WebSocket connection ----------------

    private async Task ConnectLoop(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                _socket = new ClientWebSocket();
                Debug.Log($"[VrSync] Connecting to {bridgeUrl} ...");
                await _socket.ConnectAsync(new Uri(bridgeUrl), token);
                Debug.Log("[VrSync] Connected to bridge.");
                await SendJson(new HelloMessage { type = "hello", role = "vr" });
                await ReceiveLoop(token);
            }
            catch (Exception e) { Debug.LogWarning($"[VrSync] Connection error: {e.Message}"); }

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
                if (result.MessageType == WebSocketMessageType.Close) { Debug.LogWarning("[VrSync] Bridge closed the connection."); return; }
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
                case "swap_instance":
                    var swap = JsonUtility.FromJson<SwapInstanceMessage>(json);
                    RunOnMainThread(() => ApplySwapInstance(swap));
                    break;
                case "remove_furniture":
                    var remove = JsonUtility.FromJson<RemoveFurnitureMessage>(json);
                    RunOnMainThread(() => ApplyRemove(remove));
                    break;
                case "enter_vr":
                    RunOnMainThread(EnterVr);
                    break;
                case "exit_vr":
                    RunOnMainThread(ExitVr);
                    break;
                case "hello_ack":
                    Debug.Log("[VrSync] Bridge acknowledged handshake.");
                    break;
                default:
                    // Silently ignore other message types (place/move/camera/etc)
                    // — those are for the design app only, see bridge-server.js.
                    break;
            }
        }
        catch (Exception e) { Debug.LogWarning($"[VrSync] Failed to parse message: {e.Message}\n{json}"); }
    }

    private async Task SendJson(object obj)
    {
        if (_socket == null || _socket.State != WebSocketState.Open) return;
        var bytes = Encoding.UTF8.GetBytes(JsonUtility.ToJson(obj));
        await _socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
    }

    // ---------------- "View in VR" (same-scene walkthrough) ----------------

    private void EnterVr()
    {
        if (_embedded) MoveRigToSpawn();
        _vrActive = true;
        SendStatus(true, _embedded
            ? "VR walkthrough running. Click the Unity Game view and move with the XR Device Simulator controls; this page mirrors what you see."
            : "VR session started.");
    }

    private void ExitVr()
    {
        _vrActive = false;
        SendStatus(false, "VR walkthrough stopped.");
    }

    // Drops the XR rig just inside the generated house's entrance, facing in. Also runs whenever a
    // new house finishes loading, so the Game view never sits outside the house.
    private void MoveRigToSpawn()
    {
        var loader = FloorplanLoader.Instance;
        if (xrRig == null || loader == null || !loader.HasHouse) return; // static room: leave the rig where it is

        // A CharacterController would fight a direct position change, so pause it for the move.
        var cc = xrRig.GetComponent<CharacterController>();
        if (cc != null) cc.enabled = false;
        xrRig.SetPositionAndRotation(loader.SpawnPosition + Vector3.up * rigHeightOffset, Quaternion.Euler(0f, loader.SpawnYaw, 0f));
        if (cc != null) cc.enabled = true;

        Debug.Log($"[VrSync] XR rig placed at {xrRig.position}, facing yaw {loader.SpawnYaw:0}.");
    }

    private void SendStatus(bool active, string message)
    {
        _ = SendJson(new VrStatusMessage { active = active, message = message });
    }

    // The XR camera renders per-eye into the headset; rendering it by hand into a texture is safer from a
    // plain mono copy that rides along with it (same pose, never drawn to the display).

    private void SetUpCaptureCamera()
    {
        if (streamCamera == null)
        {
            Debug.LogError("[VrSync] Stream Camera is not assigned!");
            return;
        }

        _captureCam = streamCamera;

        if (!useSpectatorCamera) return;

        var go = new GameObject("VR Spectator Camera");
        go.transform.SetParent(streamCamera.transform, false);

        var cam = go.AddComponent<Camera>();
        cam.CopyFrom(streamCamera);

        // Reset the projection matrices on the actual source camera.
        streamCamera.ResetProjectionMatrix();
        streamCamera.ResetCullingMatrix();

        //cam.stereoTargetEye = StereoTargetEyeMask.None;
        cam.enabled = false; // Rendered manually for the website stream.

        _captureCam = cam;

        Debug.Log("[VrSync] Spectator camera configured successfully.");
    }


    // ---------------- Applying live swap/remove ----------------

    private void ApplySwapInstance(SwapInstanceMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var currentObject) || currentObject == null)
        {
            // Not an error — this VR session may simply not have this
            // instance tracked (see the note in LoadInitialLayout).
            return;
        }

        var prefab = LoadPrefab(msg.prefab_path);
        if (prefab == null) { Debug.LogWarning($"[VrSync] swap_instance: prefab not found {msg.prefab_path}"); return; }

        var oldSlot = currentObject.GetComponent<FurnitureSlot>();
        int typeId = oldSlot != null ? oldSlot.typeId : 0;
        var t = currentObject.transform;
        Vector3 position = t.position; Quaternion rotation = t.rotation; Vector3 localScale = t.localScale; Transform parent = t.parent;

        Destroy(currentObject);

        GameObject instance = Instantiate(prefab, position, rotation, parent);
        instance.transform.localScale = localScale;

        var slot = instance.GetComponent<FurnitureSlot>();
        if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
        slot.typeId = typeId; slot.styleId = msg.style_id; slot.label = msg.style_name;
        slot.instanceId = msg.instance_id; slot.prefabPath = msg.prefab_path;

        _placedInstances[msg.instance_id] = instance;
        Debug.Log($"[VrSync] Live-swapped instance {msg.instance_id} -> {msg.style_name}");
    }

    private void ApplyRemove(RemoveFurnitureMessage msg)
    {
        if (msg == null) return;
        if (!_placedInstances.TryGetValue(msg.instance_id, out var go) || go == null) return;
        Destroy(go);
        _placedInstances.Remove(msg.instance_id);
        Debug.Log($"[VrSync] Live-removed instance {msg.instance_id}");
    }

    // ---------------- Streaming ----------------

    private IEnumerator StreamLoop()
    {
        var wait = new WaitForSeconds(Mathf.Max(0.05f, 1f / Mathf.Max(0.1f, streamFps)));
        while (true)
        {
            yield return wait;
            if (_socket == null || _socket.State != WebSocketState.Open) continue;
            if (!_vrActive) continue; // same-scene mode: only stream during a walkthrough
            CaptureAndSendFrame();
            SendInstancesUpdate();
        }
    }

    private void CaptureAndSendFrame()
    {
        Camera cam = _captureCam != null ? _captureCam : streamCamera;
        var prevTarget = cam.targetTexture;
        var prevActive = RenderTexture.active;

        cam.targetTexture = _frameRenderTexture;
        cam.Render();
        RenderTexture.active = _frameRenderTexture;
        _frameTexture.ReadPixels(new Rect(0, 0, streamWidth, streamHeight), 0, 0);
        _frameTexture.Apply(false);

        cam.targetTexture = prevTarget;
        RenderTexture.active = prevActive;

        byte[] jpg = _frameTexture.EncodeToJPG(streamJpegQuality);
        _ = SendJson(new VrFrameMessage { image = Convert.ToBase64String(jpg), width = streamWidth, height = streamHeight });
    }

    private void SendInstancesUpdate()
    {
        var list = new List<VrInstanceInfo>();
        foreach (var kvp in _placedInstances)
        {
            if (kvp.Value == null) continue;
            Vector3 vp = streamCamera.WorldToViewportPoint(kvp.Value.transform.position);
            if (vp.z < 0) continue;
            var slot = kvp.Value.GetComponent<FurnitureSlot>();
            list.Add(new VrInstanceInfo
            {
                instance_id = kvp.Key,
                type_id = slot ? slot.typeId : 0,
                style_name = slot ? slot.label : "",
                viewport_x = vp.x,
                viewport_y = 1f - vp.y,
            });
        }
        _ = SendJson(new VrInstancesMessage { items = list.ToArray() });
    }
}
