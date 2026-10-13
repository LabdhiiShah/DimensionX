import { useCallback, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar.jsx';
import DashboardPage from './DashboardPage.jsx';
import DesignPage from './DesignPage.jsx';
import VrPage from './VrPage.jsx';
import { useBridgeSocket } from '../hooks/useBridgeSocket.js';
import { clearSession } from '../lib/api.js';

// Set VITE_BRIDGE_URL in a .env file if your bridge isn't on this machine.
const BRIDGE_URL = import.meta.env.VITE_BRIDGE_URL || 'ws://localhost:8765';

// This is the old Unity-module App.jsx, unchanged except: LOGOUT now really logs out,
// and there is a link back to the project list.
export default function StudioPage() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const project = state?.project;

  const [page, setPage] = useState('dashboard'); // 'dashboard' | 'design' | 'vr'
  const [frameSrc, setFrameSrc] = useState(null);       // Interior Camera (drag and drop view)
  const [instances, setInstances] = useState([]);       // pieces placed via this website
  const [vrFrameSrc, setVrFrameSrc] = useState(null);   // headset / simulator camera

  const handlers = {
    onFrame: useCallback((m) => setFrameSrc('data:image/jpeg;base64,' + m.image), []),
    onInstances: useCallback((m) => setInstances(m.items || []), []),
    onVrFrame: useCallback((m) => setVrFrameSrc('data:image/jpeg;base64,' + m.image), []),
    onVrInstances: useCallback(() => {}, []),
  };
  const bridge = useBridgeSocket(BRIDGE_URL, handlers);

  const generateVr = () => {
    bridge.send({ type: 'launch_vr' }); // Unity saves the layout and signals the bridge
    setPage('vr');
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
      {page === 'dashboard' && <DashboardPage frameSrc={frameSrc} bridgeState={bridge.state} onStart={() => setPage('design')} />}
      {page === 'design' && <DesignPage bridge={bridge} frameSrc={frameSrc} instances={instances} onGenerateVr={generateVr} />}
      {page === 'vr' && <VrPage bridge={bridge} frameSrc={frameSrc} vrFrameSrc={vrFrameSrc} instances={instances} onBack={() => setPage('design')} />}
    </div>
  );
}
