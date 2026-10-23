import DesignStudio from '../components/DesignStudio.jsx';
import AssetTray from '../components/AssetTray.jsx';
import ActivityLog from '../components/ActivityLog.jsx';

// Screens 2 + 3: the Unity drag-and-drop view, the furniture cards below it, then GENERATE VR.
export default function DesignPage({ bridge, frameSrc, instances, onGenerateVr, onSaveLayout }) {
  return (
    <main className="page">
      <div className="page-narrow">
        <DesignStudio bridge={bridge} frameSrc={frameSrc} instances={instances} />
        <AssetTray />
        
        {/* Added a flex container for the two buttons */}
        <div className="center-row" style={{ display: 'flex', gap: '16px', justifyContent: 'center', marginTop: '20px', marginBottom: '20px' }}>
          <button 
            className="big-button" 
            onClick={onSaveLayout} 
            disabled={bridge.state !== 'connected'}
          >
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