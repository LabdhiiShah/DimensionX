import { useState } from 'react';
import DesignStudio from '../components/DesignStudio.jsx';
import VrView from '../components/VrView.jsx';
import AssetTray from '../components/AssetTray.jsx';
import ActivityLog from '../components/ActivityLog.jsx';

export default function VrPage({ bridge, frameSrc, vrFrameSrc, instances, onBack }) {
  const [saving, setSaving] = useState(false);

  async function saveDesign() {
    setSaving(true);
    try {
      const captured = await bridge.captureFloorPlan();
      const items = captured && captured.items && captured.items.length > 0 ? captured.items : instances;
      const { downloadDesignPdf } = await import('../lib/pdf.js'); 
      downloadDesignPdf(items, captured ? captured.image : frameSrc);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page">
      <button className="back-link" onClick={onBack}>&larr; Back to design</button>
      <div className="two-up">
        <VrView frameSrc={vrFrameSrc} connected={bridge.state === 'connected'} />
        
        {/* Added showPaintTools={false} here */}
        <DesignStudio 
          bridge={bridge} 
          frameSrc={frameSrc} 
          instances={instances} 
          tag="3D MODEL FOR CHANGES" 
          showPaintTools={false} 
        />
      </div>
      <AssetTray />
      <button className="save-bar" onClick={saveDesign} disabled={saving || bridge.state !== 'connected'}>
        {saving ? 'CAPTURING FLOOR PLAN...' : 'SAVE DESIGN'}
      </button>
      <ActivityLog log={bridge.log} />
    </main>
  );
}