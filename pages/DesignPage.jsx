import { useState } from 'react';
import DesignStudio from '../components/DesignStudio.jsx';
import AssetTray from '../components/AssetTray.jsx';
import ActivityLog from '../components/ActivityLog.jsx';

export default function DesignPage({ bridge, frameSrc, instances, onGenerateVr, onSaveLayout }) {
  const [isPainting, setIsPainting] = useState(false);

  return (
    <main className="page">
      <div className="page-narrow">
        <DesignStudio 
          bridge={bridge} 
          frameSrc={frameSrc} 
          instances={instances} 
          onPaintModeChange={setIsPainting} 
        />
        
        {!isPainting && <AssetTray />}

        <div className="center-row" style={{ display: 'flex', gap: '16px', justifyContent: 'center', marginTop: '20px', marginBottom: '20px' }}>
          <button className="big-button" onClick={onSaveLayout} disabled={bridge.state !== 'connected'}>
            SAVE LAYOUT
          </button>
          <button className="big-button" onClick={onGenerateVr} disabled={bridge.state !== 'connected'}>
            GENERATE VR
          </button>
        </div>
        
        <ActivityLog log={bridge.log} />
      </div>
    </main>
  );
}