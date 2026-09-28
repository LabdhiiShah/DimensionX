import { STYLES_BY_TYPE, displayName } from '../data/catalog.js';

// Shown under the 3D view when a placed piece (a dot) is selected:
// rotate, resize (+ / -), swap style, delete.
export default function SelectionBar({ info, send, onDelete, onDeselect }) {
  const siblings = STYLES_BY_TYPE[info.type_id] || [];
  const id = info.instance_id;

  return (
    <div className="selection-bar">
      <div className="selection-row">
        <span className="selection-title">
          {info.style_name || 'Piece'} selected <em>- click the room to move it</em>
        </span>
        <button className="ghost-button" onClick={onDeselect}>Done</button>
      </div>
      <div className="selection-row">
        <div className="tool-group">
          <span className="tool-label">Rotate</span>
          <button onClick={() => send({ type: 'rotate_instance', instance_id: id, degrees: -15 })} aria-label="Rotate left">&#10226;</button>
          <button onClick={() => send({ type: 'rotate_instance', instance_id: id, degrees: 15 })} aria-label="Rotate right">&#10227;</button>
        </div>
        <div className="tool-group">
          <span className="tool-label">Size</span>
          <button onClick={() => send({ type: 'scale_instance', instance_id: id, delta: -0.1 })} aria-label="Make smaller">&minus;</button>
          <button onClick={() => send({ type: 'scale_instance', instance_id: id, delta: 0.1 })} aria-label="Make bigger">+</button>
        </div>
        <button className="danger-button" onClick={onDelete}>Delete</button>
      </div>
      {siblings.length > 1 && (
        <div className="selection-row">
          <span className="tool-label">Swap style</span>
          <div className="style-pills">
            {siblings.map(s => (
              <button
                key={s.style_id}
                className={'style-pill' + (s.style_name === info.style_name ? ' current' : '')}
                title={displayName(s)}
                onClick={() => send({ type: 'swap_instance', instance_id: id, style_id: s.style_id, style_name: s.style_name, prefab_path: s.prefab_path })}
              >{s.style_name}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
