import { useCallback, useEffect, useRef, useState } from 'react';

// One websocket to bridge-server.js. Identifies as role "web".
// handlers = { onFrame, onInstances, onVrFrame, onVrInstances }  (each receives the raw message)
export function useBridgeSocket(url, handlers) {
  const [state, setState] = useState('idle'); // idle | connecting | connected | error
  const [log, setLog] = useState([]);
  const wsRef = useRef(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;
  const floorPlanResolverRef = useRef(null);

  const addLog = useCallback((text, kind = '') => {
    setLog(prev => [{ id: Date.now() + Math.random(), time: new Date().toLocaleTimeString(), text, kind }, ...prev].slice(0, 60));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) { try { wsRef.current.close(); } catch { /* ignore */ } }
    setState('connecting');
    let socket;
    try { socket = new WebSocket(url); }
    catch (err) { setState('error'); addLog('Could not open socket: ' + err.message, 'err'); return; }
    wsRef.current = socket;

    // Ignore events from a socket that has since been replaced (React StrictMode
    // opens/closes once on purpose in dev, and Reconnect does the same).
    const isCurrent = () => wsRef.current === socket;

    socket.onopen = () => {
      if (!isCurrent()) return;
      setState('connected');
      addLog('Connected to bridge at ' + url);
      socket.send(JSON.stringify({ type: 'hello', role: 'web' }));
    };
    socket.onclose = () => { if (!isCurrent()) return; setState('idle'); addLog('Disconnected from bridge', 'err'); };
    socket.onerror = () => { if (!isCurrent()) return; setState('error'); addLog('Socket error - is bridge-server.js running?', 'err'); };
    socket.onmessage = (evt) => {
      if (!isCurrent()) return;
      let msg;
      try { msg = JSON.parse(evt.data); } catch { return; }
      const h = handlersRef.current || {};
      switch (msg.type) {
        case 'frame': h.onFrame && h.onFrame(msg); return;
        case 'instances': h.onInstances && h.onInstances(msg); return;
        case 'vr_frame': h.onVrFrame && h.onVrFrame(msg); return;
        case 'vr_instances': h.onVrInstances && h.onVrInstances(msg); return;
        case 'floorplan_snapshot':
          if (floorPlanResolverRef.current) {
            floorPlanResolverRef.current({ image: 'data:image/jpeg;base64,' + msg.image, items: msg.items || [] });
            floorPlanResolverRef.current = null;
          }
          return;
        case 'place_result': addLog('Unity ' + (msg.success ? 'placed' : 'rejected placement') + (msg.message ? ' - ' + msg.message : ''), msg.success ? 'ok' : 'err'); return;
        case 'move_result': addLog('Unity ' + (msg.success ? 'moved' : 'rejected move') + (msg.message ? ' - ' + msg.message : ''), msg.success ? 'ok' : 'err'); return;
        case 'remove_result': addLog('Unity ' + (msg.success ? 'removed' : 'rejected removal') + (msg.message ? ' - ' + msg.message : ''), msg.success ? 'ok' : 'err'); return;
        case 'swap_instance_result': addLog('Unity ' + (msg.success ? 'swapped' : 'rejected swap') + (msg.message ? ' - ' + msg.message : ''), msg.success ? 'ok' : 'err'); return;
        case 'instance_transform_result': if (!msg.success) addLog('Unity rejected transform' + (msg.message ? ' - ' + msg.message : ''), 'err'); return;
        case 'status': addLog('Status: ' + (msg.message || JSON.stringify(msg))); return;
        default: return;
      }
    };
  }, [url, addLog]);

  useEffect(() => { connect(); return () => { if (wsRef.current) wsRef.current.close(); }; }, [connect]);

  const send = useCallback((payload) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      return true;
    }
    addLog('Not connected - command not sent', 'err');
    return false;
  }, [addLog]);

  // Asks Unity for a fresh straight-down shot of the whole room + the full furniture list.
  const captureFloorPlan = useCallback((timeoutMs = 6000) => new Promise((resolve) => {
    const finish = (result) => { floorPlanResolverRef.current = null; resolve(result); };
    floorPlanResolverRef.current = finish;
    if (!send({ type: 'capture_floorplan' })) { finish(null); return; }
    setTimeout(() => { if (floorPlanResolverRef.current === finish) finish(null); }, timeoutMs);
  }), [send]);

  return { state, log, send, reconnect: connect, captureFloorPlan };
}
