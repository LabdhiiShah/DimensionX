# Intelligent CAD-to-3D 2D Architectural Reconstruction Report

**Source File**: `sample3_2bhk.dxf`  
**Reconstruction Engine Version**: `Intelligent CAD-to-3D Antigravity Reconstruction Engine`  
**Timestamp**: `2026-09-25T18:04:56.207672`

## Executive Summary
The 2D architectural DXF floor plan was successfully audited, normalized, and reconstructed into a clean, topological, semantically-rich `House2D` model.
- **Reconstructed Walls**: `324` topological centerline edges
- **Extracted Rooms**: `13` polygonized room areas
- **Hosted Apertures**: `10` doors, `16` windows
- **Validation Status**: `PASSED` (0 blocking, 1 warnings)

## 1. Unit & Scale Calibration
- **Calibrated Units**: `Millimeters`
- **Scale-to-Meters Factor**: `0.001`
- **Scale Confidence**: `HIGH` (Source: `EXTENT_SPAN_AND_WALL_OFFSETS`)
### Evidence Chain:
- Drawing extent span (562.1) and coordinates indicate MILLIMETERS.

## 2. Geometry & Topology Reconstruction
- **Welded Vertices Count**: `327`
- **Dynamic Welding Tolerance Used**: `0.25` DXF units
- **Building Footprint Area**: `266822.72` sq units (Derivation: `RECONSTRUCTED_ROOM_AND_WALL_UNION`)

### Wall Centerlines Summary:
| Wall ID | Class | Length (DXF units) | Nominal Thickness | Status | Confidence |
|---|---|---|---|---|---|
| `wall_edge_0` | `INTERIOR` | 29.4 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_1` | `INTERIOR` | 5.9 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_2` | `INTERIOR` | 31.9 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_3` | `INTERIOR` | 53.0 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_4` | `INTERIOR` | 1.1 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_5` | `INTERIOR` | 2.8 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_6` | `INTERIOR` | 0.7 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_7` | `INTERIOR` | 2.8 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_8` | `INTERIOR` | 0.7 | 0.5 | CONFIRMED | HIGH |
| `wall_edge_9` | `INTERIOR` | 5.9 | 0.5 | CONFIRMED | HIGH |
| ... *and 314 more walls* | | | | | |

## 3. Polygonized Room Reconstruction & Semantics
| Room ID | Semantic Name | Type | Status | Area (sq units) | Parsed DXF Dimensions |
|---|---|---|---|---|---|
| `room_candidate_1` | `\pi21.27951,t28.27951;` | `PI21_27951_T28_27951` | `CONFIRMED` | 4533.214 | [] |
| `room_candidate_2` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 2048.189 | [] |
| `room_candidate_3` | `\pi37.71182;` | `PI37_71182` | `CONFIRMED` | 1967.1 | [] |
| `room_candidate_4` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 1232.985 | [] |
| `room_candidate_5` | `\pi18.07122;` | `PI18_07122` | `CONFIRMED` | 1133.888 | [] |
| `room_candidate_6` | `\pi18.40708;` | `PI18_40708` | `CONFIRMED` | 1066.456 | [] |
| `room_candidate_7` | `\pi14.29062;` | `PI14_29062` | `CONFIRMED` | 946.38 | [] |
| `room_candidate_8` | `\pi12.90443;` | `PI12_90443` | `CONFIRMED` | 914.442 | [] |
| `room_candidate_9` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 735.137 | [] |
| `room_candidate_10` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 397.885 | [] |
| `room_candidate_11` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 318.048 | [] |
| `room_candidate_12` | `\pi24.02713;` | `PI24_02713` | `CONFIRMED` | 293.026 | [] |
| `room_candidate_13` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 292.622 | [] |

## 4. Room Adjacency & Connectivity
- **Adjacent Room Pairs (Shared Boundary)**: `3`
- **Connected Room Pairs (Via Door Aperture)**: `2`

## 5. Aperture Detection & Hosting
| Opening ID | Type | Host Wall | Width | Sill Height | Head Height | Source |
|---|---|---|---|---|---|---|
| `door_1` | `DOOR` | `wall_edge_151` | 4.0 | 0.0m | 2.1m | `SWING_ARC` |
| `door_2` | `DOOR` | `wall_edge_83` | 15.99 | 0.0m | 2.1m | `SWING_ARC` |
| `door_3` | `DOOR` | `wall_edge_278` | 14.0 | 0.0m | 2.1m | `SWING_ARC` |
| `door_4` | `DOOR` | `wall_edge_278` | 16.0 | 0.0m | 2.1m | `SWING_ARC` |
| `door_5` | `DOOR` | `wall_edge_136` | 11.21 | 0.0m | 2.1m | `SWING_ARC` |
| `door_6` | `DOOR` | `wall_edge_16` | 16.0 | 0.0m | 2.1m | `SWING_ARC` |
| `door_7` | `DOOR` | `wall_edge_278` | 14.0 | 0.0m | 2.1m | `SWING_ARC` |
| `door_8` | `DOOR` | `wall_edge_278` | 16.0 | 0.0m | 2.1m | `SWING_ARC` |
| `door_9` | `DOOR` | `wall_edge_136` | 11.21 | 0.0m | 2.1m | `SWING_ARC` |
| `door_10` | `DOOR` | `wall_edge_177` | 14.58 | 0.0m | 2.1m | `SWING_ARC` |
| `window_1` | `WINDOW` | `wall_edge_252` | 24.2 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_2` | `WINDOW` | `wall_edge_1` | 23.62 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_3` | `WINDOW` | `wall_edge_302` | 0.23 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_4` | `WINDOW` | `wall_edge_143` | 43.48 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_5` | `WINDOW` | `wall_edge_29` | 40.37 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_6` | `WINDOW` | `wall_edge_104` | 91.93 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_7` | `WINDOW` | `wall_edge_282` | 73.26 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_8` | `WINDOW` | `wall_edge_278` | 0.59 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_9` | `WINDOW` | `wall_edge_278` | 39.43 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_10` | `WINDOW` | `wall_edge_278` | 0.59 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_11` | `WINDOW` | `wall_edge_104` | 91.93 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_12` | `WINDOW` | `wall_edge_104` | 91.93 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_13` | `WINDOW` | `wall_edge_302` | 0.23 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_14` | `WINDOW` | `wall_edge_143` | 43.48 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_15` | `WINDOW` | `wall_edge_143` | 43.48 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |
| `window_16` | `WINDOW` | `wall_edge_286` | 23.0 | 0.9m | 2.1m | `WINDOW_LAYER_GEOMETRY` |

## 6. Architectural Validation Summary
- **Overall Result**: `PASSED`
- **Blocking Errors (0)**:
  - *None! Zero blocking errors.*
- **Warnings (1)**:
  - **[SEMANTICS]** `UNASSIGNED_ROOM_LABELS`: 6 room polygons lack explicit DXF text callouts and were designated UNKNOWN_SPACE.

## 7. Diagnostic Visualizations
- **Detailed Debug Overlay**: `output/diagnostic_debug.png`
- **Clean Architectural Floor Plan**: `output/diagnostic_clean.png`