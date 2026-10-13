import { memo, useState } from 'react';
import FurnitureIcon from './FurnitureIcon.jsx';
import { displayName, thumbUrl, typeNameFor } from '../data/catalog.js';

// One draggable furniture tile: picture on top, name underneath.
// The picture is public/furniture/<parent-folder>_<prefab-name>.png; if that
// file doesn't exist yet, a line drawing of the furniture type is shown instead.
function FurnitureCard({ style }) {
  const [imgFailed, setImgFailed] = useState(false);
  const name = displayName(style);

  function onDragStart(ev) {
    const payload = Object.assign({}, style, { type_name: typeNameFor(style.type_id) });
    ev.dataTransfer.setData('application/json', JSON.stringify(payload));
    ev.dataTransfer.effectAllowed = 'copy';
  }

  return (
    <div className="asset-card" draggable onDragStart={onDragStart} title={'Drag "' + name + '" onto the 3D view'}>
      <div className="asset-thumb">
        {imgFailed
          ? <FurnitureIcon typeName={typeNameFor(style.type_id)} />
          : <img src={thumbUrl(style)} alt={name} draggable={false} onError={() => setImgFailed(true)} />}
      </div>
      <div className="asset-name">{name}</div>
    </div>
  );
}

export default memo(FurnitureCard);
