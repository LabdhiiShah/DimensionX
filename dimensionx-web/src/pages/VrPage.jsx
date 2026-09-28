import { useState } from 'react';
import DesignStudio from '../components/DesignStudio.jsx';
import VrView from '../components/VrView.jsx';
import AssetTray from '../components/AssetTray.jsx';
import ActivityLog from '../components/ActivityLog.jsx';

// Screen 4: left = live VR walkthrough (driven by the headset/simulator in Unity),
// right = the drag-and-drop view (driven by this website), and SAVE DESIGN below.
export default function VrPage({ bridge, frameSrc, vrFrameSrc, instances, onBack }) {
  const [saving, setSaving] = useState(false);

  async function saveDesign() {
    setSaving(true);
    try {
      // Fresh straight-down shot of the whole room + the complete furniture list.
      const captured = await bridge.captureFloorPlan();
      const items = captured && captured.items && captured.items.length > 0 ? captured.items : instances;
      const { downloadDesignPdf } = await import('../lib/pdf.js'); // loaded only when needed (jsPDF is big)
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
        <DesignStudio bridge={bridge} frameSrc={frameSrc} instances={instances} tag="3D MODEL FOR CHANGES" />
      </div>
      <AssetTray />
      <button className="save-bar" onClick={saveDesign} disabled={saving || bridge.state !== 'connected'}>
        {saving ? 'CAPTURING FLOOR PLAN...' : 'SAVE DESIGN'}
      </button>
      <ActivityLog log={bridge.log} />
    </main>
  );
}
