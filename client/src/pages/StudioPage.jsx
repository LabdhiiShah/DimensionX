import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar.jsx';
import DashboardPage from './DashboardPage.jsx';
import DesignPage from './DesignPage.jsx';
import VrPage from './VrPage.jsx';
import { useBridgeSocket } from '../hooks/useBridgeSocket.js';
import { clearSession, projectsApi, getUser } from '../lib/api.js';

const BRIDGE_URL = import.meta.env.VITE_BRIDGE_URL || 'ws://localhost:8765';
const ASSET_ORIGIN = (import.meta.env.VITE_ASSET_ORIGIN || import.meta.env.VITE_API_URL || 'http://localhost:4000/api').replace(/\/api\/?$/, '');

export default function StudioPage() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const user = getUser();
  const project = state?.project;
  
  // Fallback to the database fields if state wasn't passed
  const glbPath = state?.glbUrl || project?.glb_url || null;   
  const plan = state?.plan || project?.plan || null;        

  const [page, setPage] = useState('dashboard'); 
  const [frameSrc, setFrameSrc] = useState(null);       
  const [instances, setInstances] = useState([]);       
  const [vrFrameSrc, setVrFrameSrc] = useState(null);   
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

  useEffect(() => {
    if (!glbPath) {
        setFloorplan({ state: 'error', message: 'No 3D model (GLB) was found for this project. Upload a floor plan first.' });
        return;
    }
    
    if (bridgeState !== 'connected') return;

    setFloorplan({ state: 'loading', message: 'Sending floor plan to Unity...' });
    bridgeSend({
      type: 'load_floorplan',
      glb_url: ASSET_ORIGIN + glbPath,
      project_id: String(project?.id ?? 'temp'),
      plan,
      // NEW: Send the saved furniture layout to Unity
      saved_furniture: project?.furniture_layout || [] 
    });
  }, [glbPath, bridgeState]);

  // NEW: Function to save layout to database
  const saveLayout = async () => {
    if (!project?.id) return;
    try {
      await projectsApi.saveLayout(project.id, instances);
      alert("Layout saved successfully to the database!");
    } catch (err) {
      alert("Failed to save layout: " + err.message);
    }
  };
  
  const generateVr = () => {
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
        <button className="back-link" onClick={() => navigate(user?.isAdmin ? '/admin' : '/projects')}>&larr; All projects</button>
        {project && <span className="studio-hint"> {project.projectName} for {project.clientName}</span>}
      </div>
      
      {page === 'dashboard' && <DashboardPage frameSrc={frameSrc} bridgeState={bridge.state} floorplan={floorplan} onStart={() => setPage('design')} />}
      
      {page === 'design' && (
        <DesignPage 
          bridge={bridge} 
          frameSrc={frameSrc} 
          instances={instances} 
          onGenerateVr={generateVr} 
          onSaveLayout={saveLayout} // <-- Pass the save function
        />
      )}
      
      {page === 'vr' && <VrPage bridge={bridge} frameSrc={frameSrc} vrFrameSrc={vrFrameSrc} instances={instances} onBack={leaveVr} />}
    </div>
  );
}