import { useState } from 'react';
import { ChromePicker } from 'react-color';

export default function PaintSidebar({ bridge, onPaintModeChange, color, setColor }) {
  const [isOpen, setIsOpen] = useState(false);
  const [paintMode, setPaintMode] = useState(false);
  const [showPicker, setShowPicker] = useState(false);

  const toggleSidebar = () => setIsOpen(!isOpen);

  const togglePaintMode = () => {
    const newMode = !paintMode;
    
    if (newMode) {
      bridge.send({ type: 'toggle_paint_mode', active: true });
    } else {
      bridge.send({ type: 'apply_wall_color', color });
      bridge.send({ type: 'toggle_paint_mode', active: false });
    }
    
    setPaintMode(newMode);
    if (onPaintModeChange) onPaintModeChange(newMode);
  };

  const handleColorChange = (newColor) => {
    setColor(newColor.hex);
  };

  const presetColors = [
    '#9E0142', '#D53E4F', '#F46D43', '#FDAE61',
    '#FEE08B', '#E6F598', '#ABDDA4', '#66C2A5',
    '#3288BD', '#5E4FA2', '#66C5CC', '#F6CF71',
    '#F89C74', '#DCB0F2', '#87C55F', '#9EB9F3',
    '#FE88B1', '#B3B3B3', '#2B3A42', '#E8D5B5' 
  ];

  return (
    <div className="paint-tool-container" onClick={(e) => e.stopPropagation()}>
      
      {/* NEW THEME-ALIGNED ICON: Paint Roller */}
      <button className="paint-trigger-btn" onClick={toggleSidebar} title="Wall Color Picker">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="2" width="16" height="6" rx="2" />
          <path d="M18 5h2a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2h-8v3" />
          <path d="M10 15h4v6a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h2z" />
        </svg>
      </button>

      {isOpen && (
        <div className="paint-sidebar">
          <h3>Paint Walls</h3>
          
          <button 
            className={paintMode ? 'active' : ''} 
            onClick={togglePaintMode}
            style={{ 
              backgroundColor: paintMode ? '#2e7d32' : undefined, // Green when active
              color: paintMode ? '#fff' : undefined 
            }}
          >
            {paintMode ? 'APPLY & STOP' : 'PAINT'}
          </button>

          {paintMode && (
            <p style={{ fontSize: '11px', color: '#666', margin: 0, textAlign: 'center' }}>
              Click walls to select them, pick a color, then click APPLY & STOP.
            </p>
          )}

          <div className="paint-color-picker-wrapper" style={{ position: 'relative' }}>
            <label>Custom Color</label>
            
            <div 
              onClick={() => setShowPicker(!showPicker)}
              style={{
                width: '100%',
                height: '40px',
                backgroundColor: color,
                borderRadius: '8px',
                border: '1px solid #ccc',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: color === '#ffffff' || color === '#f5f5dc' ? '#333' : '#fff',
                fontWeight: 'bold',
                fontSize: '12px',
                boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.1)'
              }}
            >
              {color.toUpperCase()}
            </div>

            {showPicker && (
              <div style={{ position: 'absolute', top: '100%', left: -10, zIndex: 9999, marginTop: '10px' }}>
                <div 
                  style={{ position: 'fixed', inset: 0 }} 
                  onClick={() => setShowPicker(false)} 
                />
                <ChromePicker 
                  color={color} 
                  onChangeComplete={handleColorChange} 
                  disableAlpha={true}
                />
              </div>
            )}
          </div>

          <div className="paint-color-picker-wrapper">
            <label>Presets</label>
            <div 
              className="paint-presets" 
              style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(4, 1fr)', 
                gap: '12px 8px' 
              }}
            >
              {presetColors.map((c) => (
                <div key={c} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                  <button
                    className="paint-preset-swatch"
                    style={{ backgroundColor: c, width: '100%', aspectRatio: '1' }}
                    onClick={() => {
                      setColor(c);
                      setShowPicker(false);
                    }}
                    title={c}
                  />
                  <span style={{ fontSize: '9px', color: '#666', fontFamily: 'monospace' }}>{c.toUpperCase()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}