import { useEffect, useRef, useState } from 'react';
import CameraControls from './CameraControls.jsx';
import SelectionBar from './SelectionBar.jsx';
import PaintSidebar from './PaintSidebar.jsx';

export default function DesignStudio({ 
  bridge, 
  frameSrc, 
  instances, 
  tag = '3D VIEW FROM UNITY', 
  onPaintModeChange, 
  showPaintTools = true // <-- NEW: Defaults to true
}) {
  const { send } = bridge;
  const stageRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [dropMarker, setDropMarker] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [hidden, setHidden] = useState(() => new Set()); 
  const [isPaintMode, setIsPaintMode] = useState(false);
  const [paintColor, setPaintColor] = useState('#ffffff');
  const clickLockRef = useRef(false);

  useEffect(() => {
    if (onPaintModeChange) onPaintModeChange(isPaintMode);
  }, [isPaintMode, onPaintModeChange]);

  const list = instances || [];
  const selectedInfo = list.find(i => i.instance_id === selectedId) || null;
  const visible = list.filter(i => !hidden.has(i.instance_id));

  useEffect(() => {
    if (hidden.size === 0) return;
    const present = new Set(list.map(i => i.instance_id));
    setHidden(prev => {
      const next = new Set([...prev].filter(id => present.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [instances]);

  const fractionOf = (ev) => {
    const r = stageRef.current.getBoundingClientRect();
    return { x: (ev.clientX - r.left) / r.width, y: (ev.clientY - r.top) / r.height };
  };

  function onDragOver(ev) {
    if (isPaintMode) return;
    ev.preventDefault();
    ev.dataTransfer.dropEffect = 'copy';
    setDragOver(true);
    const f = fractionOf(ev);
    setDropMarker({ x: f.x * 100, y: f.y * 100 });
  }
  
  function onDrop(ev) {
    if (isPaintMode) return;
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
    if (clickLockRef.current) return;
    clickLockRef.current = true;
    setTimeout(() => { clickLockRef.current = false; }, 250);

    const f = fractionOf(ev);
    if (isPaintMode) {
      send({ type: 'select_wall_at', viewport_x: f.x, viewport_y: f.y });
      return;
    }

    if (!selectedId) return;
    send({ type: 'move_furniture', instance_id: selectedId, viewport_x: f.x, viewport_y: f.y });
    setSelectedId(null);
  }
  
  function onMarkerClick(ev, id) {
    if (isPaintMode) return;
    ev.stopPropagation();
    setSelectedId(prev => (prev === id ? null : id));
  }
  
  function deleteSelected() {
    if (!selectedId) return;
    setHidden(prev => new Set(prev).add(selectedId)); 
    send({ type: 'remove_furniture', instance_id: selectedId });
    setSelectedId(null);
  }

  return (
    <div className="studio" style={{ position: 'relative' }}>
      
      {/* CONDITIONALLY RENDER THE PAINT SIDEBAR */}
      {showPaintTools && (
        <PaintSidebar 
          bridge={bridge} 
          onPaintModeChange={setIsPaintMode} 
          color={paintColor} 
          setColor={setPaintColor} 
        />
      )}

      <div
        ref={stageRef}
        className={'stage' + (dragOver ? ' drag-over' : '') + (selectedId ? ' placing' : '')}
        style={{ cursor: isPaintMode ? 'crosshair' : 'default', userSelect: 'none' }}
        onDragOver={onDragOver}
        onDragLeave={() => { if (!isPaintMode) { setDragOver(false); setDropMarker(null); } }}
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
            style={{ 
              left: inst.viewport_x * 100 + '%', 
              top: inst.viewport_y * 100 + '%', 
              opacity: isPaintMode ? 0 : 1,
              pointerEvents: isPaintMode ? 'none' : 'auto'
            }}
            title={inst.style_name || 'Piece'}
            onClick={(ev) => onMarkerClick(ev, inst.instance_id)}
          />
        ))}
        {dropMarker && !isPaintMode && <div className="drop-marker" style={{ left: dropMarker.x + '%', top: dropMarker.y + '%' }} />}
      </div>

      <div className="studio-controls">
        <div className="studio-tools">
          {selectedInfo && !isPaintMode
            ? <SelectionBar info={selectedInfo} send={send} onDelete={deleteSelected} onDeselect={() => setSelectedId(null)} />
            : <p className="studio-hint">{isPaintMode ? 'Click walls in the 3D view to select them (they turn grey), pick a color, then click APPLY & STOP.' : 'Drag a piece from the catalog onto the view. Click a dot to select a placed piece, then rotate, resize, swap its style, move or delete it.'}</p>}
        </div>
        <CameraControls send={send} />
      </div>
    </div>
  );
}