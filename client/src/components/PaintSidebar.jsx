import { useState } from 'react';

export default function PaintSidebar({ bridge, onPaintModeChange, color, setColor }) {
  const [isOpen, setIsOpen] = useState(false);
  const [paintMode, setPaintMode] = useState(false);

  const toggleSidebar = () => setIsOpen(!isOpen);

  const togglePaintMode = () => {
    const newMode = !paintMode;
    
    if (newMode) {
      // Entering paint mode
      bridge.send({ type: 'toggle_paint_mode', active: true });
    } else {
      // Exiting paint mode: Apply the selected color first, then exit
      bridge.send({ type: 'apply_wall_color', color });
      bridge.send({ type: 'toggle_paint_mode', active: false });
    }
    
    setPaintMode(newMode);
    if (onPaintModeChange) onPaintModeChange(newMode);
  };

  const handleColorChange = (newColor) => {
    setColor(newColor); // Just update the local state, don't send to Unity yet
  };

  const presetColors = [
    '#ffffff', '#f5f5dc', '#e6e6fa', '#ffdab9', 
    '#cdeef3', '#a3c2c2', '#87ceeb', '#b0c4de', 
    '#ffb6c1', '#ffa07a', '#f08080', '#800a1d', 
    '#90ee90', '#556b2f', '#d3d3d3', '#4a4a4a'  
  ];

  return (
    <div className="paint-tool-container" onClick={(e) => e.stopPropagation()}>
      <button className="paint-trigger-btn" onClick={toggleSidebar} title="Wall Color Picker">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" strokeWidth="1.5" />
          <path d="M12 3v2m0 14v2M3 12h2m14 0h2" strokeWidth="1.5"/>
          <path d="M18.5 5.5l-6 6" strokeWidth="2" />
          <path d="M15.5 3.5l5 5-1.5 1.5-5-5z" fill="currentColor"/>
          <path d="M12 12l-2 2" strokeWidth="2" />
        </svg>
      </button>

      {isOpen && (
        <div className="paint-sidebar">
          <h3>Paint Walls</h3>
          
          {/* Changed button text */}
          <button 
            className={paintMode ? 'active' : ''} 
            onClick={togglePaintMode}
          >
            {paintMode ? 'APPLY & STOP' : 'PAINT'}
          </button>

          {paintMode && (
            <p style={{ fontSize: '11px', color: '#666', margin: 0, textAlign: 'center' }}>
              Click walls to select them (they turn grey), pick a color, then click APPLY & STOP.
            </p>
          )}

          <div className="paint-color-picker-wrapper">
            <label>Custom Color</label>
            <input 
              type="color" 
              className="paint-color-input"
              value={color} 
              onChange={(e) => handleColorChange(e.target.value)} 
            />
          </div>

          <div className="paint-color-picker-wrapper">
            <label>Presets</label>
            <div className="paint-presets">
              {presetColors.map((c) => (
                <button
                  key={c}
                  className="paint-preset-swatch"
                  style={{ backgroundColor: c }}
                  onClick={() => handleColorChange(c)}
                  title={c}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}