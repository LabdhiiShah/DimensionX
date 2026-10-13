import { memo, useMemo, useRef, useState } from 'react';
import FurnitureCard from './FurnitureCard.jsx';
import { DATA, STYLES_BY_TYPE, prettyType } from '../data/catalog.js';

// The row of furniture cards (picture + name). Scrolls sideways; filter chips on top.
function AssetTray() {
  const [filter, setFilter] = useState('all');
  const scrollerRef = useRef(null);

  const chips = useMemo(
    () => DATA.types.filter(t => (STYLES_BY_TYPE[t.type_id] || []).length > 0),
    []
  );
  const styles = filter === 'all' ? DATA.styles : (STYLES_BY_TYPE[filter] || []);

  const scrollBy = (dx) => scrollerRef.current && scrollerRef.current.scrollBy({ left: dx, behavior: 'smooth' });

  return (
    <section className="asset-tray" aria-label="Furniture catalog">
      <div className="asset-chips">
        <button className={'chip' + (filter === 'all' ? ' active' : '')} onClick={() => setFilter('all')}>All</button>
        {chips.map(t => (
          <button key={t.type_id} className={'chip' + (filter === t.type_id ? ' active' : '')} onClick={() => setFilter(t.type_id)}>
            {prettyType(t.type_name)}
          </button>
        ))}
      </div>
      <div className="asset-row-wrap">
        <button className="asset-arrow left" onClick={() => scrollBy(-440)} aria-label="Scroll left">&#8249;</button>
        <div className="asset-row" ref={scrollerRef}>
          {styles.map(s => <FurnitureCard key={s.style_id} style={s} />)}
        </div>
        <button className="asset-arrow right" onClick={() => scrollBy(440)} aria-label="Scroll right">&#8250;</button>
      </div>
    </section>
  );
}

export default memo(AssetTray);
