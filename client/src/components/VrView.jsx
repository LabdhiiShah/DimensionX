// Spectate-only: the headset / XR simulator camera streamed from Unity.
// Nothing here talks back to Unity - the person in the headset is in control.
export default function VrView({ frameSrc, connected, tag = 'USER POV OF THE WALKTHRU' }) {
  return (
    <div className="studio">
      <div className="stage">
        {frameSrc
          ? <img className="stage-img" src={frameSrc} alt="Live VR walkthrough" draggable={false} />
          : (
            <div className="stage-placeholder">
              <strong>{tag}</strong>
              <span>{connected ? 'waiting for the VR camera to stream...' : 'bridge offline - start bridge-server.js'}</span>
            </div>
          )}
        {frameSrc && <span className="stage-tag">{tag}</span>}
      </div>
      <div className="studio-controls">
        <div className="studio-tools">
          <p className="studio-hint">Spectate only. This view follows whoever is in the headset (or the XR Device Simulator) inside Unity.</p>
        </div>
      </div>
    </div>
  );
}
