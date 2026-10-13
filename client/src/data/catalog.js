// Mirrors the dimensionsx Postgres tables: type, style.
export const DATA = {
  types: [
    { type_id: 1, type_name: 'Bed' }, { type_id: 2, type_name: 'Sofa' }, { type_id: 3, type_name: 'Chair' },
    { type_id: 4, type_name: 'Desk' }, { type_id: 5, type_name: 'Table' }, { type_id: 6, type_name: 'Wadrobe' },
    { type_id: 7, type_name: 'Sink' }, { type_id: 8, type_name: 'Stove' }, { type_id: 9, type_name: 'Shower' },
    { type_id: 10, type_name: 'Toilet' }, { type_id: 11, type_name: 'TV' }, { type_id: 12, type_name: 'Drawer' },
    { type_id: 13, type_name: 'Lamp' },
  ],
  styles: [
    { style_id: 1, type_id: 1, style_name: 'Modern', prefab_path: 'Assets/Furniture/Bed/bedsc.prefab' },
    { style_id: 2, type_id: 1, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/Bed/Bunkbedsc.prefab' },
    { style_id: 3, type_id: 2, style_name: 'Modern', prefab_path: 'Assets/Furniture/Sofa/Couch_Large1.prefab' },
    { style_id: 4, type_id: 2, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/Sofa/Couch_Medium2.prefab' },
    { style_id: 5, type_id: 2, style_name: 'Minimal', prefab_path: 'Assets/Furniture/Sofa/Couch_Small1.prefab' },
    { style_id: 6, type_id: 3, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/chair/Sc.prefab' },
    { style_id: 8, type_id: 4, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/Desk/sc.prefab' },
    { style_id: 9, type_id: 12, style_name: 'Modern', prefab_path: 'Assets/Furniture/drawer/Drawer_mo.prefab' },
    { style_id: 10, type_id: 12, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/drawer/drawersc.prefab' },
    { style_id: 11, type_id: 5, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/table/ScanndinavianSideTable.prefab' },
    { style_id: 12, type_id: 7, style_name: 'Modern', prefab_path: 'Assets/Furniture/sink/bathroomSinkSquare.prefab' },
    { style_id: 13, type_id: 7, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/sink/WoodSink1KitchenCabinet1.prefab' },
    { style_id: 14, type_id: 7, style_name: 'Minimal', prefab_path: 'Assets/Furniture/sink/SteelSink1KitchenCabinet1.prefab' },
    { style_id: 15, type_id: 8, style_name: 'Modern', prefab_path: 'Assets/Furniture/stove/GasStove1.prefab' },
    { style_id: 16, type_id: 8, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/stove/Kitchen_Oven_Large.prefab' },
    { style_id: 17, type_id: 8, style_name: 'Minimal', prefab_path: 'Assets/Furniture/stove/model.prefab' },
    { style_id: 18, type_id: 9, style_name: 'Modern', prefab_path: 'Assets/Furniture/shower/showerRound.prefab' },
    { style_id: 21, type_id: 10, style_name: 'Modern', prefab_path: 'Assets/Furniture/toilet/Bathroom_Toilet.prefab' },
    { style_id: 22, type_id: 10, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/toilet/SIEFRING_Toilet_LP.prefab' },
    { style_id: 23, type_id: 10, style_name: 'Minimal', prefab_path: 'Assets/Furniture/toilet/toiletSquare.prefab' },
    { style_id: 24, type_id: 11, style_name: 'Modern', prefab_path: 'Assets/Furniture/tv/TV.prefab' },
    { style_id: 25, type_id: 11, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/tv/TV_01.prefab' },
    { style_id: 26, type_id: 13, style_name: 'Modern', prefab_path: 'Assets/Furniture/lamp/FloorLamp1.prefab' },
    { style_id: 27, type_id: 13, style_name: 'Scandinavian', prefab_path: 'Assets/Furniture/lamp/Light_Ceiling2.prefab' },
    { style_id: 28, type_id: 13, style_name: 'Minimal', prefab_path: 'Assets/Furniture/lamp/Light_Ceiling4.prefab' },
    { style_id: 29, type_id: 13, style_name: 'Industrial', prefab_path: 'Assets/Furniture/lamp/Light_Cube2.prefab' },
  ],
};

export const TYPE_BY_ID = Object.fromEntries(DATA.types.map(t => [t.type_id, t]));

export const STYLES_BY_TYPE = DATA.styles.reduce((map, s) => {
  (map[s.type_id] = map[s.type_id] || []).push(s);
  return map;
}, {});

// The DB spells it "Wadrobe" - fix it for anything a human reads.
const PRETTY_TYPE = { Wadrobe: 'Wardrobe' };
export function prettyType(typeName) { return PRETTY_TYPE[typeName] || typeName; }

export function typeNameFor(typeId) {
  const t = TYPE_BY_ID[typeId];
  return t ? prettyType(t.type_name) : 'Type ' + typeId;
}

// "Scandinavian Sofa" - the name shown on a furniture card.
export function displayName(style) {
  return style.style_name + ' ' + typeNameFor(style.type_id);
}

// Thumbnail file name for a catalog entry: <parent folder>_<prefab name>, lowercased.
//   Assets/Furniture/Sofa/Couch_Large1.prefab  ->  sofa_couch_large1
// (The folder is part of the name because "sc.prefab" exists in both chair/ and Desk/.)
// FurnitureThumbnailExporter.cs in Unity writes files with this exact naming.
export function prefabSlug(prefabPath) {
  const parts = prefabPath.split('/');
  const file = (parts[parts.length - 1] || '').replace(/\.prefab$/i, '');
  const folder = parts[parts.length - 2] || '';
  return (folder + '_' + file).toLowerCase();
}

export function thumbUrl(style) {
  return import.meta.env.BASE_URL + 'furniture/' + prefabSlug(style.prefab_path) + '.png';
}
