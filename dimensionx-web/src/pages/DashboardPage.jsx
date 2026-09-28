// Screen 1: info panel on the left, live 3D view from Unity on the right.
export default function DashboardPage({ frameSrc, bridgeState, onStart }) {
  return (
    <main className="page">
      <div className="dash-grid">
        <aside className="info-panel">
          <h2>Design it. Walk through it. Build it.</h2>
          <ol>
            <li>Your CAD floor plan is turned into a 3D house in Unity.</li>
            <li>Drag furniture from the catalog into the rooms, then rotate, resize or swap styles.</li>
            <li>Generate VR to walk through the design in a headset while you watch it live here.</li>
            <li>Save the design as a PDF build sheet with the top view and every piece's details.</li>
          </ol>
          <button className="light-button" onClick={onStart}>Start designing</button>
        </aside>
        <section className="dash-view">
          {frameSrc
            ? <img src={frameSrc} alt="3D view from Unity" draggable={false} />
            : (
              <div className="stage-placeholder">
                <strong>3D VIEW FROM UNITY</strong>
                <span>{bridgeState === 'connected' ? 'waiting for a frame from Unity...' : 'bridge offline - start bridge-server.js'}</span>
              </div>
            )}
        </section>
      </div>
    </main>
  );
}
