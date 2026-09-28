# DimensionX web (React + Vite)

## Run it
```
npm install        # first time only
npm run dev        # opens http://localhost:5173
```
Keep `node bridge-server.js` running and Unity in Play mode. (Open it through the dev server -
double-clicking index.html won't work with React/Vite.)

If the bridge isn't on this machine, create a `.env` file: `VITE_BRIDGE_URL=ws://192.168.1.20:8765`

## Pages
| Screen | What it shows |
|---|---|
| Dashboard | Info panel + live 3D view from Unity |
| Design (drag and drop) | Unity's Interior Camera stream. Drag a furniture card onto it. Click a dot to rotate / resize (+ -) / swap style / move / delete. Arrow pad moves the camera. **GENERATE VR** goes to the next page |
| VR walkthrough | Left: live headset/simulator camera. Right: the drag-and-drop view. **SAVE DESIGN** downloads the PDF |

## Furniture pictures
Each card looks for `public/furniture/<parent-folder>_<prefab-name>.png` (lower-case), e.g.
`Assets/Furniture/Sofa/Couch_Large1.prefab` -> `public/furniture/sofa_couch_large1.png`.
Until a picture exists, a line drawing of that furniture type is shown.

To generate all pictures automatically: copy `unity/FurnitureThumbnailExporter.cs` to `Assets/Editor/`
in Unity, then **DimensionsX > Export Furniture Thumbnails** and choose this project's `public/furniture` folder.

Adding a new piece: add a row to `src/data/catalog.js` (and the same row in your database).

## Project map
```
src/App.jsx                     page switching + Unity frame state
src/hooks/useBridgeSocket.js    websocket to bridge-server.js
src/components/DesignStudio.jsx the Unity drag-and-drop window
src/components/FurnitureCard.jsx / AssetTray.jsx   picture + name cards
src/pages/*                     Dashboard, Design, VR
src/lib/pdf.js                  build-sheet PDF
```
