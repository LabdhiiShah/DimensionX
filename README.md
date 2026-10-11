# DimensionX — 30 structured DXF floor plans

This bundle contains **30 synthetic development floor plans**: 10 each for 1BHK, 2BHK and 3BHK. The uploaded reference drawings informed room relationships and common features; the layouts in this set are new variants drafted with a consistent machine-readable CAD convention.

**The JSON outputs are deliberately NOT included.** They are generated from the DXF files when you run the scanner. DXF is the source of truth.

These are development/test assets, not construction documents or architect-certified plans.

## Package contents

- `plans/1BHK`, `plans/2BHK`, `plans/3BHK`: 30 DXF files. There are no ready-made architecture JSON files in these folders.
- `tools/scan_dxf_folder.py`: scans DXF files recursively and creates JSON outputs.
- `tools/dimensionx_dxf_to_json.py`: converts one DXF to one JSON file.
- `tools/validate_plan_set.py`: checks door/window-to-wall links and room-zone area coverage after conversion.
- `tools/validate_dxf_json_pairs.py`: checks that DXF semantic entities and generated JSON agree.
- `tools/dimensionx_plan_factory.py`: reproducible plan-generation source.
- `architecture_schema.json`: output JSON schema.
- `previews/`: plan previews and contact sheets.
- `plan_catalog.csv` and `validation_report.csv`: static reference/QA summaries from the dataset-generation pass. They are not the JSON output consumed by Blender.

## How extraction is designed

All 30 DXFs use the DimensionX semantic CAD contract:

- `$INSUNITS = 2`: XY coordinates are in feet.
- `DX_FOOTPRINT`: closed building-core footprint polygon.
- `DX_WALL_AXIS`: wall centerline `LINE` entities. `DIMENSIONX` XDATA stores wall ID, thickness, height, exterior/interior classification and adjacent room IDs.
- `DX_WALL_FACE`: visual wall bands for drawing display; the converter uses `DX_WALL_AXIS`.
- `DX_DOOR` and `DX_WINDOW`: semantic `POINT` entities. XDATA stores opening ID, exact `wall_id`, width, height, sill height, role and orientation.
- `DX_ROOM_ZONE`: room polygons and room metadata.
- `DX_BALCONY`: balcony/utility polygons and attachment metadata.
- Symbol, label and dimension layers are for visual presentation.

This means the converter can retrieve exact encoded properties rather than guessing from visual linework.

## 1. Install the dependency

Use the Python environment that will run the converter (not Blender's internal Python):

```bash
python -m pip install ezdxf
```

## 2. Generate JSON from all DXFs

From the extracted package folder:

```bash
python tools/scan_dxf_folder.py
```

The script scans `plans/` recursively and generates JSON only then, under:

```text
generated_json/
  1BHK/1BHK_01_architecture.json
  1BHK/1BHK_02_architecture.json
  ...
  2BHK/...
  3BHK/...
```

Specify another input/output folder when needed:

```bash
python tools/scan_dxf_folder.py --input "C:/DimensionX/my_dxf_plans" --output "C:/DimensionX/generated_json"
```

Convert just one DXF:

```bash
python tools/dimensionx_dxf_to_json.py "plans/1BHK/1BHK_01.dxf" --output "generated_json/1BHK_01_architecture.json"
```

## 3. Validate generated outputs

After running the scanner:

```bash
python tools/validate_plan_set.py
python tools/validate_dxf_json_pairs.py
```

Reports will be written under `generated_json/`.

## Blender / Unity hand-off

The JSON contract has `bhk`, `units`, `footprint`, `walls`, `doors`, `windows`, `rooms` and `balconies`. Doors/windows each reference their wall using `wall_id` and include the coordinates and dimensions needed to produce architectural openings. The Blender generator can create the building shell and openings; Unity can later replace the exported `DX_SOCKET_DOOR_*` and `DX_SOCKET_WINDOW_*` placeholders with selected catalogue assets.

## Important limitation

The scanner extracts meaning from the **DimensionX semantic DXF convention used by the 30 files in this package**. It is not yet the AI detector for any arbitrary third-party DXF with unknown layer names or no semantic metadata. Such files need an additional inference step (heuristics/AI plus review) to recognize walls, doors and windows before they can be converted reliably.

## Safety / use note

The plans are synthetic development fixtures. They have not been reviewed for structural engineering, building regulations, accessibility, fire egress, ventilation, plumbing, waterproofing or construction details. Have a qualified architect/engineer review and approve any design before real-world use.
