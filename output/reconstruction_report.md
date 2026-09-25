# Intelligent CAD-to-3D 2D Architectural Reconstruction Report

**Source File**: `sample1.dxf`  
**Reconstruction Engine Version**: `Intelligent CAD-to-3D Antigravity Reconstruction Engine`  
**Timestamp**: `2026-09-25T12:07:05.283855`

## Executive Summary
The 2D architectural DXF floor plan was successfully audited, normalized, and reconstructed into a clean, topological, semantically-rich `House2D` model.
- **Reconstructed Walls**: `273` topological centerline edges
- **Extracted Rooms**: `15` polygonized room areas
- **Hosted Apertures**: `4` doors, `0` windows
- **Validation Status**: `PASSED` (0 blocking, 1 warnings)

## 1. Unit & Scale Calibration
- **Calibrated Units**: `Millimeters`
- **Scale-to-Meters Factor**: `0.001`
- **Scale Confidence**: `HIGH` (Source: `EXTENT_SPAN_AND_WALL_OFFSETS`)
### Evidence Chain:
- Drawing extent span (562.1) and coordinates indicate MILLIMETERS.

## 2. Geometry & Topology Reconstruction
- **Welded Vertices Count**: `279`
- **Dynamic Welding Tolerance Used**: `0.25` DXF units
- **Building Footprint Area**: `276500.65` sq units (Derivation: `RECONSTRUCTED_ROOM_AND_WALL_UNION`)

### Wall Centerlines Summary:
| Wall ID | Class | Length (DXF units) | Nominal Thickness | Status | Confidence |
|---|---|---|---|---|---|
| `wall_edge_0` | `INTERIOR` | 35.6 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_1` | `INTERIOR` | 35.0 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_2` | `INTERIOR` | 180.0 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_3` | `INTERIOR` | 5.9 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_4` | `INTERIOR` | 180.0 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_5` | `INTERIOR` | 21.7 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_6` | `INTERIOR` | 5.9 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_7` | `INTERIOR` | 7.0 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_8` | `INTERIOR` | 18.6 | 1.0 | CONFIRMED | HIGH |
| `wall_edge_9` | `INTERIOR` | 10.2 | 1.0 | CONFIRMED | HIGH |
| ... *and 263 more walls* | | | | | |

## 3. Polygonized Room Reconstruction & Semantics
| Room ID | Semantic Name | Type | Status | Area (sq units) | Parsed DXF Dimensions |
|---|---|---|---|---|---|
| `room_candidate_1` | `M. Bedroom` | `BEDROOM` | `CONFIRMED` | 16752.65 | [111.0, 132.0] |
| `room_candidate_2` | `Liv./Din.` | `LIVING_DINING` | `CONFIRMED` | 14004.539 | [144.0, 174.0] |
| `room_candidate_3` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 2478.36 | [] |
| `room_candidate_4` | `M. Toi.` | `TOILET` | `CONFIRMED` | 1710.526 | [92.0, 48.0] |
| `room_candidate_5` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 1457.567 | [] |
| `room_candidate_6` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 1377.0 | [] |
| `room_candidate_7` | `ENTRY` | `ENTRANCE` | `CONFIRMED` | 980.405 | [] |
| `room_candidate_8` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 735.137 | [] |
| `room_candidate_9` | `Kitchen` | `KITCHEN` | `CONFIRMED` | 663.183 | [94.0, 84.0] |
| `room_candidate_10` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 586.924 | [] |
| `room_candidate_11` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 470.976 | [] |
| `room_candidate_12` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 435.725 | [] |
| `room_candidate_13` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 375.117 | [] |
| `room_candidate_14` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 359.044 | [] |
| `room_candidate_15` | `UNKNOWN_SPACE` | `UNKNOWN_SPACE` | `UNASSIGNED` | 339.584 | [] |

## 4. Room Adjacency & Connectivity
- **Adjacent Room Pairs (Shared Boundary)**: `7`
- **Connected Room Pairs (Via Door Aperture)**: `7`

## 5. Aperture Detection & Hosting
| Opening ID | Type | Host Wall | Width | Sill Height | Head Height | Source |
|---|---|---|---|---|---|---|
| `door_1` | `DOOR` | `wall_edge_93` | 15.99 | 0.0m | 2.1m | `SWING_ARC` |
| `door_2` | `DOOR` | `wall_edge_120` | 14.37 | 0.0m | 2.1m | `SWING_ARC` |
| `door_3` | `DOOR` | `wall_edge_60` | 15.93 | 0.0m | 2.1m | `SWING_ARC` |
| `door_4` | `DOOR` | `wall_edge_255` | 8.0 | 0.0m | 2.1m | `SWING_ARC` |

## 6. Architectural Validation Summary
- **Overall Result**: `PASSED`
- **Blocking Errors (0)**:
  - *None! Zero blocking errors.*
- **Warnings (1)**:
  - **[SEMANTICS]** `UNASSIGNED_ROOM_LABELS`: 10 room polygons lack explicit DXF text callouts and were designated UNKNOWN_SPACE.

## 7. Diagnostic Visualizations
- **Detailed Debug Overlay**: `output/diagnostic_debug.png`
- **Clean Architectural Floor Plan**: `output/diagnostic_clean.png`