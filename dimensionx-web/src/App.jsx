import { useCallback, useState } from 'react';
import NavBar from './components/NavBar.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import DesignPage from './pages/DesignPage.jsx';
import VrPage from './pages/VrPage.jsx';
import { useBridgeSocket } from './hooks/useBridgeSocket.js';

// Set VITE_BRIDGE_URL in a .env file if your bridge isn't on this machine.
const BRIDGE_URL = import.meta.env.VITE_BRIDGE_URL || 'ws://localhost:8765';

export default function App() {
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
  // There's no login backend in this module - LOGOUT just returns to the dashboard.
  const logout = () => setPage('dashboard');

  return (
    <div className="app">
      <NavBar
        bridgeState={bridge.state}
        onReconnect={bridge.reconnect}
        onDashboard={() => setPage('dashboard')}
        onLogout={logout}
      />
      {page === 'dashboard' && <DashboardPage frameSrc={frameSrc} bridgeState={bridge.state} onStart={() => setPage('design')} />}
      {page === 'design' && <DesignPage bridge={bridge} frameSrc={frameSrc} instances={instances} onGenerateVr={generateVr} />}
      {page === 'vr' && <VrPage bridge={bridge} frameSrc={frameSrc} vrFrameSrc={vrFrameSrc} instances={instances} onBack={() => setPage('design')} />}
    </div>
  );
}
