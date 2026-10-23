import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar.jsx';
import DashboardPage from './DashboardPage.jsx';
import DesignPage from './DesignPage.jsx';
import VrPage from './VrPage.jsx';
import { useBridgeSocket } from '../hooks/useBridgeSocket.js';
import { clearSession } from '../lib/api.js';

// Set VITE_BRIDGE_URL in a .env file if your bridge isn't on this machine.
const BRIDGE_URL = import.meta.env.VITE_BRIDGE_URL || 'ws://localhost:8765';

// Unity downloads the generated GLB over HTTP from the Express server, so it needs an ABSOLUTE
// url. Defaults to the API host minus "/api". Set VITE_ASSET_ORIGIN if Unity runs on another machine.
const ASSET_ORIGIN = (import.meta.env.VITE_ASSET_ORIGIN || import.meta.env.VITE_API_URL || 'http://localhost:4000/api').replace(/\/api\/?$/, '');

// This is the old Unity-module App.jsx, unchanged except: LOGOUT now really logs out,
// and there is a link back to the project list.
export default function StudioPage() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const project = state?.project;
  const glbPath = state?.glbUrl || null;   // set by UploadDxfPage after the DXF was converted
  const plan = state?.plan || null;        // spawn point / footprint centre for the cameras

  const [page, setPage] = useState('dashboard'); // 'dashboard' | 'design' | 'vr'
  const [frameSrc, setFrameSrc] = useState(null);       // Interior Camera (drag and drop view)
  const [instances, setInstances] = useState([]);       // pieces placed via this website
  const [vrFrameSrc, setVrFrameSrc] = useState(null);   // headset / simulator camera
  // none = opened without an upload (old static room) | waiting | loading | ready | error
  const [floorplan, setFloorplan] = useState({ state: glbPath ? 'loading' : 'none', message: '' });

  const handlers = {
    onFrame: useCallback((m) => setFrameSrc('data:image/jpeg;base64,' + m.image), []),
    onInstances: useCallback((m) => setInstances(m.items || []), []),
    onVrFrame: useCallback((m) => setVrFrameSrc('data:image/jpeg;base64,' + m.image), []),
    onVrInstances: useCallback(() => {}, []),
    onFloorplan: useCallback((m) => setFloorplan({ state: m.state, message: m.message || '' }), []),
    onVrStatus: useCallback(() => {}, []),
  };
  const bridge = useBridgeSocket(BRIDGE_URL, handlers);
  const { send: bridgeSend, state: bridgeState } = bridge;

  // Hand the uploaded floor plan to Unity as soon as the bridge is up (and again after a reconnect;
  // Unity ignores a model it already has and just re-announces "ready").
  useEffect(() => {
    if (!glbPath || bridgeState !== 'connected') return;
    setFloorplan({ state: 'loading', message: 'Sending floor plan to Unity...' });
    bridgeSend({
      type: 'load_floorplan',
      glb_url: ASSET_ORIGIN + glbPath,
      project_id: String(project?.id ?? 'temp'),
      plan,
    });
  }, [glbPath, bridgeState]); // eslint-disable-line react-hooks/exhaustive-deps

  const generateVr = () => {
    // Unity snapshots the layout; the bridge also tells the in-scene VR rig to start the walkthrough.
    bridge.send({ type: 'launch_vr' });
    setPage('vr');
  };
  const leaveVr = () => {
    bridge.send({ type: 'exit_vr' });
    setPage('design');
  };
  const logout = () => { clearSession(); navigate('/'); };

  return (
    <div className="app">
      <NavBar
        bridgeState={bridge.state}
        onReconnect={bridge.reconnect}
        onDashboard={() => setPage('dashboard')}
        onLogout={logout}
      />
      <div className="page" style={{ marginBottom: -10 }}>
        <button className="back-link" onClick={() => navigate('/projects')}>&larr; All projects</button>
        {project && <span className="studio-hint"> {project.projectName} for {project.clientName}</span>}
      </div>
      {page === 'dashboard' && <DashboardPage frameSrc={frameSrc} bridgeState={bridge.state} floorplan={floorplan} onStart={() => setPage('design')} />}
      {page === 'design' && <DesignPage bridge={bridge} frameSrc={frameSrc} instances={instances} onGenerateVr={generateVr} />}
      {page === 'vr' && <VrPage bridge={bridge} frameSrc={frameSrc} vrFrameSrc={vrFrameSrc} instances={instances} onBack={leaveVr} />}
    </div>
  );
}
