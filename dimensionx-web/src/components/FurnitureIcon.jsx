// Line-drawn stand-ins shown on a furniture card until a real thumbnail
// exists in public/furniture/. Keyed by lower-cased type name.
const ICONS = {
  bed: (<><rect x="6" y="24" width="52" height="10" rx="2" /><path d="M6 12v28M58 28v12" /><rect x="11" y="18" width="16" height="6" rx="3" /></>),
  sofa: (<><rect x="10" y="12" width="44" height="14" rx="5" /><rect x="8" y="26" width="48" height="10" rx="3" /><rect x="3" y="20" width="9" height="18" rx="3" /><rect x="52" y="20" width="9" height="18" rx="3" /><path d="M12 38v5M52 38v5" /></>),
  chair: (<><rect x="20" y="5" width="24" height="18" rx="3" /><rect x="16" y="23" width="32" height="7" rx="2" /><path d="M20 30v14M44 30v14" /></>),
  desk: (<><rect x="6" y="14" width="52" height="5" rx="1.5" /><path d="M10 19v25M54 19v25" /><rect x="36" y="19" width="18" height="12" /><circle cx="45" cy="25" r="1" /></>),
  table: (<><ellipse cx="32" cy="16" rx="24" ry="6" /><path d="M16 20l-3 24M48 20l3 24M32 22v22" /></>),
  wardrobe: (<><rect x="14" y="4" width="36" height="38" rx="2" /><path d="M32 4v38M18 42v4M46 42v4" /><circle cx="28" cy="24" r="1.2" /><circle cx="36" cy="24" r="1.2" /></>),
  sink: (<><rect x="10" y="26" width="44" height="18" rx="2" /><path d="M14 22h36l-4 6H18z" /><path d="M32 22V12h8v4" /></>),
  stove: (<><rect x="8" y="8" width="48" height="36" rx="3" /><circle cx="22" cy="19" r="5" /><circle cx="42" cy="19" r="5" /><rect x="14" y="30" width="36" height="9" rx="1.5" /></>),
  shower: (<><path d="M12 44V8h20" /><path d="M28 8h14l-3 6h-8z" /><path d="M31 19v5M36 19v7M41 19v5" /><path d="M8 44h48" /></>),
  toilet: (<><rect x="20" y="5" width="24" height="14" rx="2" /><path d="M14 22h36c0 10-6 16-18 16S14 32 14 22z" /><path d="M26 38v6h12v-6" /></>),
  tv: (<><rect x="5" y="7" width="54" height="29" rx="2" /><path d="M22 44h20M32 36v8" /></>),
  drawer: (<><rect x="10" y="5" width="44" height="37" rx="2" /><path d="M10 17h44M10 29h44M28 11h8M28 23h8M28 35h8M14 42v4M50 42v4" /></>),
  lamp: (<><path d="M20 7h24l6 17H14z" /><path d="M32 24v19M22 44h20" /></>),
};

export default function FurnitureIcon({ typeName }) {
  const key = String(typeName || '').toLowerCase();
  return (
    <svg className="furniture-icon" viewBox="0 0 64 48" fill="none" stroke="currentColor"
         strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[key] || <rect x="10" y="10" width="44" height="30" rx="3" />}
    </svg>
  );
}
