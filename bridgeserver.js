/**
 * Furniture Sync Bridge Server
 * ------------------------------------------------------------
 * Relays messages between the web control panel and Unity, and — new —
 * launches your native VR build when asked to.
 *
 * Message types relayed:
 *   web -> unity : swap_furniture, place_furniture, launch_vr, load_floorplan,
 *                  toggle_paint_mode, apply_wall_color, select_wall_at
 *   web -> vr    : enter_vr, exit_vr
 *   unity -> web : swap_result, place_result, status, frame (live view),
 *                  floorplan_status (house loading / ready / error)
 *   vr -> web    : vr_frame, vr_status
 *   unity -> bridge : launch_vr_ready (bridge spawns the VR exe on this)
 *
 * Run it with:
 *   npm install ws
 *   VR_BUILD_PATH="C:\path\to\YourVrBuild.exe" node bridge-server.js
 *
 * VR_BUILD_PATH is optional — if unset, "launch_vr" still saves the
 * layout (Unity does that part) but the bridge just logs a reminder
 * instead of launching anything.
 * ------------------------------------------------------------
 */

const WebSocket = require('ws');
const { execFile } = require('child_process');

const PORT = process.env.PORT || 8765;
const VR_BUILD_PATH = process.env.VR_BUILD_PATH || '';

const wss = new WebSocket.Server({ port: PORT });
const clients = new Map(); // ws -> role ("web" | "unity" | "vr" | "unknown")

// The most recent load_floorplan request. Unity may start (or reconnect) AFTER the
// website uploaded a DXF, so we replay this to it as soon as it says hello.
let lastFloorplan = null;

function countRole(role) {
  let n = 0;
  for (const r of clients.values()) if (r === role) n++;
  return n;
}

function broadcastTo(role, payload) {
  const message = JSON.stringify(payload);
  for (const [socket, r] of clients.entries()) {
    if (r === role && socket.readyState === WebSocket.OPEN) {
      socket.send(message);
    }
  }
}

function broadcastToRoles(roles, payload) {
  roles.forEach(role => broadcastTo(role, payload));
}

function launchVrBuild(layoutPath) {
  if (!VR_BUILD_PATH) {
    // Same-scene mode: the VR rig already lives in the Unity scene (see enterEmbeddedVr),
    // so there is no separate .exe to launch.
    console.log('[bridge] layout saved; VR_BUILD_PATH not set, so VR runs inside the Unity scene.');
    return;
  }
  console.log(`[bridge] Launching VR build: ${VR_BUILD_PATH} "${layoutPath}"`);
  execFile(VR_BUILD_PATH, [layoutPath], (err) => {
    if (err) {
      console.error('[bridge] Failed to launch VR build:', err.message);
      broadcastTo('web', { type: 'status', message: 'Failed to launch VR build: ' + err.message });
    }
  });
  broadcastTo('web', { type: 'status', message: 'Launching VR headset app…' });
}

// "View in VR" without an external build: tell the VrSyncManager that is already
// running inside the Unity scene to start the XR-simulator walkthrough.
function enterEmbeddedVr() {
  if (countRole('vr') === 0) {
    broadcastTo('web', { type: 'status', message: 'No VR client connected. Is VrSyncManager in the Unity scene and Play mode running?' });
    return;
  }
  console.log('[bridge] enter_vr -> vr');
  broadcastTo('vr', { type: 'enter_vr' });
}

wss.on('connection', (ws) => {
  console.log('[bridge] client connected');
  clients.set(ws, 'unknown');

  ws.on('message', (raw) => {
    let msg;
    try {
      msg = JSON.parse(raw.toString());
    } catch (err) {
      console.error('[bridge] received invalid JSON, dropping:', raw.toString().slice(0, 200));
      return;
    }

    if (msg.type === 'hello' && (msg.role === 'web' || msg.role === 'unity' || msg.role === 'vr')) {
      clients.set(ws, msg.role);
      console.log(`[bridge] client identified as "${msg.role}"`);
      ws.send(JSON.stringify({ type: 'hello_ack', role: msg.role }));
      if (msg.role === 'unity' && lastFloorplan) {
        console.log('[bridge] replaying load_floorplan to the newly connected Unity');
        ws.send(JSON.stringify(lastFloorplan));
      }
      return;
    }

    switch (msg.type) {
      // Web -> Unity ONLY (these involve raycasting against whichever
      // camera the click came from — the design camera — so they'd land
      // in the wrong spot if also applied against the VR camera).
      case 'swap_furniture':
      case 'place_furniture':
      case 'move_furniture':
      case 'rotate_instance':
      case 'scale_instance':
      case 'camera_pan':
      case 'camera_zoom':
      case 'camera_rotate':
      case 'capture_floorplan':
      // --- WALL PAINTING MESSAGES ---
      case 'toggle_paint_mode':
      case 'apply_wall_color':
      case 'select_wall_at':
        if (msg.type !== 'camera_pan' && msg.type !== 'camera_rotate') {
          console.log(`[bridge] ${msg.type} -> unity`, 
            ['place_furniture','move_furniture','rotate_instance','scale_instance','select_wall_at','apply_wall_color'].includes(msg.type) 
            ? { instance_id: msg.instance_id, degrees: msg.degrees, delta: msg.delta, color: msg.color, x: msg.viewport_x, y: msg.viewport_y } 
            : msg
          );
        }
        broadcastTo('unity', msg);
        break;

      // Web -> Unity: build the house from the uploaded DXF's GLB (remembered for late joiners)
      case 'load_floorplan':
        lastFloorplan = msg;
        console.log('[bridge] load_floorplan -> unity', msg.glb_url);
        if (countRole('unity') === 0) {
          broadcastTo('web', { type: 'floorplan_status', state: 'waiting', message: 'Waiting for Unity to connect...' });
        }
        broadcastTo('unity', msg);
        break;

      // Web -> Unity (snapshot the layout) AND, when there is no external VR build,
      // start the in-scene XR simulator walkthrough.
      case 'launch_vr':
        console.log('[bridge] launch_vr -> unity');
        broadcastTo('unity', msg);
        if (!VR_BUILD_PATH) enterEmbeddedVr();
        break;

      // Web -> VR client only (the XR rig lives in the VR client)
      case 'enter_vr':
        enterEmbeddedVr();
        break;
      case 'exit_vr':
        console.log('[bridge] exit_vr -> vr');
        broadcastTo('vr', msg);
        break;

      // Web -> BOTH Unity and VR — these just reference an instance_id
      // and swap/remove it, no camera-relative math involved, so it's
      // safe (and desired) to mirror the change into a live VR session too.
      case 'swap_instance':
      case 'remove_furniture':
        console.log(`[bridge] ${msg.type} -> unity + vr`, { instance_id: msg.instance_id, style_id: msg.style_id });
        broadcastToRoles(['unity', 'vr'], msg);
        break;

      // Unity/VR -> Web
      case 'swap_result':
      case 'place_result':
      case 'move_result':
      case 'remove_result':
      case 'swap_instance_result':
      case 'instance_transform_result':
      case 'floorplan_status':
      case 'vr_status':
      case 'status':
      case 'wall_selection': // <--- Added so React receives wall count
        console.log('[bridge] result ->', msg);
        broadcastTo('web', msg);
        break;

      // Unity -> Web (high-frequency or carries a full image — don't log every one)
      case 'frame':
      case 'instances':
      case 'floorplan_snapshot':
        broadcastTo('web', msg);
        break;

      // VR -> Web (high-frequency, separate stream from the design app's)
      case 'vr_frame':
      case 'vr_instances':
        broadcastTo('web', msg);
        break;

      // Unity -> Bridge (bridge itself acts on this one)
      case 'launch_vr_ready':
        console.log('[bridge] launch_vr_ready, layout at', msg.layout_path);
        launchVrBuild(msg.layout_path);
        break;

      default:
        console.warn('[bridge] unrecognized message type:', msg.type);
    }
  });

  ws.on('close', () => {
    console.log(`[bridge] client disconnected (role: ${clients.get(ws)})`);
    clients.delete(ws);
  });

  ws.on('error', (err) => {
    console.error('[bridge] socket error:', err.message);
  });
});

console.log(`[bridge] Furniture sync bridge listening on ws://localhost:${PORT}`);
console.log(`[bridge] VR_BUILD_PATH is ${VR_BUILD_PATH ? VR_BUILD_PATH : '(not set)'}`);