/**
 * Furniture Sync Bridge Server
 * ------------------------------------------------------------
 * Relays messages between the web control panel and Unity, and — new —
 * launches your native VR build when asked to.
 *
 * Message types relayed:
 *   web -> unity : swap_furniture, place_furniture, launch_vr
 *   unity -> web : swap_result, place_result, status, frame (live view)
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
const clients = new Map(); // ws -> role ("web" | "unity" | "unknown")

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
    console.warn('[bridge] launch_vr_ready received, but VR_BUILD_PATH is not set — set it as an env var to actually launch your VR build.');
    broadcastTo('web', { type: 'status', message: 'Layout saved, but VR_BUILD_PATH isn\'t configured on the bridge server — see README.' });
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
      case 'launch_vr':
      case 'capture_floorplan':
        if (msg.type !== 'camera_pan' && msg.type !== 'camera_rotate') {
          console.log(`[bridge] ${msg.type} -> unity`, ['place_furniture','move_furniture','rotate_instance','scale_instance'].includes(msg.type) ? { instance_id: msg.instance_id, degrees: msg.degrees, delta: msg.delta } : msg);
        }
        broadcastTo('unity', msg);
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
      case 'status':
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