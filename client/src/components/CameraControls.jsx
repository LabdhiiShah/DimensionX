// The website's D-pad. These messages only ever move the Interior Camera in Unity
// (the bridge never forwards them to the VR camera).
export default function CameraControls({ send }) {
  const pan = (dx, dz) => send({ type: 'camera_pan', dx, dz });
  const zoom = (delta) => send({ type: 'camera_zoom', delta });
  const rotate = (degrees) => send({ type: 'camera_rotate', degrees });

  return (
    <div className="cam-controls" aria-label="Camera controls">
      <div className="cam-dpad">
        <span />
        <button onClick={() => pan(0, 1)} aria-label="Move camera forward">&uarr;</button>
        <span />
        <button onClick={() => pan(-1, 0)} aria-label="Move camera left">&larr;</button>
        <span className="cam-center">CAM</span>
        <button onClick={() => pan(1, 0)} aria-label="Move camera right">&rarr;</button>
        <span />
        <button onClick={() => pan(0, -1)} aria-label="Move camera back">&darr;</button>
        <span />
      </div>
      <div className="cam-side">
        <div className="cam-pair">
          <button onClick={() => rotate(-15)} title="Turn left" aria-label="Turn camera left">&#10226;</button>
          <button onClick={() => rotate(15)} title="Turn right" aria-label="Turn camera right">&#10227;</button>
        </div>
        <div className="cam-pair">
          <button onClick={() => zoom(1)} title="Zoom in" aria-label="Zoom in">+</button>
          <button onClick={() => zoom(-1)} title="Zoom out" aria-label="Zoom out">&minus;</button>
        </div>
      </div>
    </div>
  );
}
