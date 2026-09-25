# DXF Audit Report: sample1.dxf

- **File Path**: `d:\end game\dwg\sample1.dxf`
- **File Size**: `633342 bytes`
- **Total Entities**: `844`

## 1. Header Variables & Units Calibration
- **$INSUNITS**: `0` (Unspecified)
- **$EXTMIN**: `[85748.62698055233, 12957.72821161953, -89665.88688452914]`
- **$EXTMAX**: `[268739.7031051442, 19927.21637488068, 59443.27258156327]`
- **$MEASUREMENT**: `0`
- **$LUNITS**: `4`
- **Calibrated Units**: `Millimeters`
- **To-Meters Factor**: `0.001`
- **Scale Confidence**: `HIGH` (Source: `EXTENT_SPAN_AND_WALL_OFFSETS`)

### Scale Evidence:
- Drawing extent span (562.1) and coordinates indicate MILLIMETERS.

## 2. Drawing Extents & Geometry Statistics
- **Extents Width x Height**: `562.11 x 397.604` DXF units
- **Bounding Box**: `X:[122537.149, 123099.259], Y:[19170.007, 19567.612]`
- **Total Line/Polyline Segments**: `1077`
- **Duplicate Segments**: `400`
- **Non-Zero Z-Coordinate Entities**: `1072` (Z range: `[-89158.08366223545, 0.0051299721417308]`)

### Candidate Wall Thicknesses (Parallel Line Pair Offsets):
| Offset Distance (DXF units) | Frequency |
|---|---|
| 0.3 | 20 |
| 1.0 | 19 |
| 4.9 | 18 |
| 17.7 | 17 |
| 18.0 | 16 |
| 12.8 | 16 |
| 3.0 | 14 |
| 0.5 | 11 |
| 4.0 | 10 |
| 5.9 | 10 |

## 3. Entity Type Distribution
| Entity Type | Count |
|---|---|
| LINE | 570 |
| LWPOLYLINE | 114 |
| ARC | 78 |
| CIRCLE | 30 |
| MTEXT | 19 |
| HATCH | 12 |
| DIMENSION | 9 |
| SPLINE | 8 |
| IMAGE | 2 |
| INSERT | 1 |
| LEADER | 1 |

## 4. Layer Analysis & Classification
| Layer Name | Entities | Assigned Role | Confidence | Color | Locked |
|---|---|---|---|---|---|
| `0` | 7 | `UNKNOWN` | MEDIUM | 252 | False |
| `WALL` | 33 | `WALL` | HIGH | 7 | False |
| `DEFPOINTS` | 0 | `UNKNOWN` | MEDIUM | 4 | False |
| `DIM` | 548 | `DIMENSION` | HIGH | 7 | False |
| `FURINTURE` | 31 | `FURNITURE` | HIGH | 7 | False |
| `BEAM` | 1 | `STRUCTURAL` | HIGH | 251 | False |
| `FUNIRUTURE` | 2 | `UNKNOWN` | MEDIUM | 7 | False |
| `ELEVA` | 3 | `ELECTRICAL / ANNOTATION` | MEDIUM | 8 | False |
| `TAXT` | 13 | `ROOM_LABEL / ANNOTATION` | HIGH | 7 | False |
| `BASEPLAN$0$WALL` | 0 | `WALL` | HIGH | 8 | False |
| `BASEPLAN$0$PARKING` | 0 | `UNKNOWN` | MEDIUM | 8 | False |
| `BASEPLAN$0$4` | 0 | `UNKNOWN` | MEDIUM | 8 | False |
| `HATCH` | 85 | `SURFACE_HATCH` | HIGH | 252 | False |
| `ELE` | 8 | `ELECTRICAL / ANNOTATION` | MEDIUM | 7 | False |
| `BLDGTEXT` | 6 | `ROOM_LABEL / ANNOTATION` | HIGH | 7 | False |
| `WIN_GL` | 3 | `WINDOW` | HIGH | 142 | False |
| `BEAM_FRAME` | 16 | `STRUCTURAL` | HIGH | 3 | False |
| `ELCTRICAL` | 2 | `ELECTRICAL / ANNOTATION` | MEDIUM | 10 | False |
| `CHAJJA` | 9 | `UNKNOWN` | MEDIUM | 8 | False |
| `WALLS_UPDATED` | 61 | `WALL` | HIGH | 7 | False |
| `TREES` | 6 | `UNKNOWN` | MEDIUM | 7 | False |
| `HATCH_ARCHITECTURE` | 10 | `SURFACE_HATCH` | HIGH | 252 | False |

## 5. Room Label & Annotation Candidates
Found **9** candidate room text labels in modelspace:

| Text Content | Layer | Position (X, Y) | Parsed Arch Dims |
|---|---|---|---|
| `{\FTrebuchet MS;\W3.64593; }ENTRY` | `TAXT` | (122934.4, 19271.1) | [] |
| `{\FTrebuchet MS;\W3.43164; }M. Toi. \P{\FTrebuchet MS;\W1.47926; }7'8" x 4'0"` | `TAXT` | (122712.6, 19390.0) | [92.0, 48.0] |
| `{\FTrebuchet MS;\W3.52688; }C. Toi. \P{\FTrebuchet MS;\W1.47926; }4'0" x 7'0"` | `TAXT` | (122830.2, 19352.6) | [48.0, 84.0] |
| `M. Bedroom \P   9'3" x 11'0"` | `TAXT` | (122720.4, 19560.3) | [111.0, 132.0] |
| `{\FTrebuchet MS;\W2.25051; }Liv./Din.\P12'0" x 14'6"` | `TAXT` | (122927.2, 19371.4) | [144.0, 174.0] |
| `{\FTrebuchet MS;\W3.26498; }Kitchen \P{\FTrebuchet MS;\W1.00307; }7'10" x 7'0"` | `TAXT` | (122818.5, 19491.0) | [94.0, 84.0] |
| `{\FTrebuchet MS;\W2.06004; } Balcony\P      9'3" x 3'3"` | `TAXT` | (122921.1, 19537.7) | [111.0, 39.0] |
| `{\FTrebuchet MS;\W2.13146; }LIV./DIN.` | `TAXT` | (122587.0, 19228.8) | [] |
| `{\FTrebuchet MS;\W0.90165; }M. BEDROOM` | `TAXT` | (122575.0, 19381.6) | [] |

## 6. Block Definitions & References
- **Total Block Definitions**: `38`
- **User Block Definitions**: `23`
- **Anonymous Blocks**: `15`
