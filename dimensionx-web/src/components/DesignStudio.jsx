import { useEffect, useRef, useState } from 'react';
import CameraControls from './CameraControls.jsx';
import SelectionBar from './SelectionBar.jsx';

// The "drag and drop frame from Unity": shows the Interior Camera's live stream,
// accepts furniture cards dropped onto it, and lets you pick / move / edit placed pieces.
//
//  - drop a card         -> place_furniture   (viewport x/y as 0..1 fractions of this box)
//  - click a dot         -> select that piece
//  - click the room      -> move_furniture    (while a piece is selected)
export default function DesignStudio({ bridge, frameSrc, instances, tag = '3D VIEW FROM UNITY' }) {
  const { send } = bridge;
  const stageRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [dropMarker, setDropMarker] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [hidden, setHidden] = useState(() => new Set()); // deleted locally, until Unity confirms

  const list = instances || [];
  const selectedInfo = list.find(i => i.instance_id === selectedId) || null;
  const visible = list.filter(i => !hidden.has(i.instance_id));

  // Forget hidden ids once Unity's broadcast no longer contains them.
  useEffect(() => {
    if (hidden.size === 0) return;
    const present = new Set(list.map(i => i.instance_id));
    setHidden(prev => {
      const next = new Set([...prev].filter(id => present.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [instances]); // eslint-disable-line react-hooks/exhaustive-deps

  const fractionOf = (ev) => {
    const r = stageRef.current.getBoundingClientRect();
    return { x: (ev.clientX - r.left) / r.width, y: (ev.clientY - r.top) / r.height };
  };

  function onDragOver(ev) {
    ev.preventDefault();
    ev.dataTransfer.dropEffect = 'copy';
    setDragOver(true);
    const f = fractionOf(ev);
    setDropMarker({ x: f.x * 100, y: f.y * 100 });
  }
  function onDrop(ev) {
    ev.preventDefault();
    setDragOver(false); setDropMarker(null);
    let style;
    try { style = JSON.parse(ev.dataTransfer.getData('application/json')); } catch { return; }
    const f = fractionOf(ev);
    send({
      type: 'place_furniture',
      type_id: style.type_id, type_name: style.type_name,
      style_id: style.style_id, style_name: style.style_name,
      prefab_path: style.prefab_path,
      viewport_x: f.x, viewport_y: f.y,
    });
  }
  function onStageClick(ev) {
    if (!selectedId) return;
    const f = fractionOf(ev);
    send({ type: 'move_furniture', instance_id: selectedId, viewport_x: f.x, viewport_y: f.y });
    setSelectedId(null);
  }
  function onMarkerClick(ev, id) {
    ev.stopPropagation();
    setSelectedId(prev => (prev === id ? null : id));
  }
  function deleteSelected() {
    if (!selectedId) return;
    setHidden(prev => new Set(prev).add(selectedId)); // vanish instantly, don't wait for Unity's next broadcast
    send({ type: 'remove_furniture', instance_id: selectedId });
    setSelectedId(null);
  }

  return (
    <div className="studio">
      <div
        ref={stageRef}
        className={'stage' + (dragOver ? ' drag-over' : '') + (selectedId ? ' placing' : '')}
        onDragOver={onDragOver}
        onDragLeave={() => { setDragOver(false); setDropMarker(null); }}
        onDrop={onDrop}
        onClick={onStageClick}
      >
        {frameSrc
          ? <img className="stage-img" src={frameSrc} alt="Live design view from Unity" draggable={false} />
          : (
            <div className="stage-placeholder">
              <strong>{tag}</strong>
              <span>{bridge.state === 'connected' ? 'waiting for a frame from Unity...' : 'bridge offline - start bridge-server.js'}</span>
            </div>
          )}
        {frameSrc && <span className="stage-tag">{tag}</span>}
        {visible.map(inst => (
          <button
            key={inst.instance_id}
            className={'marker' + (inst.instance_id === selectedId ? ' selected' : '')}
            style={{ left: inst.viewport_x * 100 + '%', top: inst.viewport_y * 100 + '%' }}
            title={(inst.style_name || 'Piece') + (inst.instance_id === selectedId ? ' - click a spot to move it here' : ' - click to select')}
            onClick={(ev) => onMarkerClick(ev, inst.instance_id)}
          />
        ))}
        {dropMarker && <div className="drop-marker" style={{ left: dropMarker.x + '%', top: dropMarker.y + '%' }} />}
      </div>

      <div className="studio-controls">
        <div className="studio-tools">
          {selectedInfo
            ? <SelectionBar info={selectedInfo} send={send} onDelete={deleteSelected} onDeselect={() => setSelectedId(null)} />
            : <p className="studio-hint">Drag a piece from the catalog onto the view. Click a dot to select a placed piece, then rotate, resize, swap its style, move or delete it.</p>}
        </div>
        <CameraControls send={send} />
      </div>
    </div>
  );
}
