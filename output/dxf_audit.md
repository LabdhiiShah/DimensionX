# DXF Audit Report: sample3_2bhk.dxf

- **File Path**: `d:\end game\dwg\sample3_2bhk.dxf`
- **File Size**: `821969 bytes`
- **Total Entities**: `660`

## 1. Header Variables & Units Calibration
- **$INSUNITS**: `0` (Unspecified)
- **$EXTMIN**: `[123228.9101554203, 19120.78590330186, -24460.03655417496]`
- **$EXTMAX**: `[123791.020333975, 19591.22093677564, 1.5248631e-08]`
- **$MEASUREMENT**: `0`
- **$LUNITS**: `4`
- **Calibrated Units**: `Millimeters`
- **To-Meters Factor**: `0.001`
- **Scale Confidence**: `HIGH` (Source: `EXTENT_SPAN_AND_WALL_OFFSETS`)

### Scale Evidence:
- Drawing extent span (562.1) and coordinates indicate MILLIMETERS.

## 2. Drawing Extents & Geometry Statistics
- **Extents Width x Height**: `562.11 x 470.435` DXF units
- **Bounding Box**: `X:[123228.91, 123791.02], Y:[19120.786, 19591.221]`
- **Total Line/Polyline Segments**: `940`
- **Duplicate Segments**: `61`
- **Non-Zero Z-Coordinate Entities**: `20` (Z range: `[-24460.03655417496, 0.0]`)

### Candidate Wall Thicknesses (Parallel Line Pair Offsets):
| Offset Distance (DXF units) | Frequency |
|---|---|
| 5.9 | 28 |
| 0.5 | 24 |
| 1.0 | 23 |
| 2.0 | 19 |
| 4.0 | 19 |
| 3.0 | 18 |
| 7.9 | 13 |
| 5.4 | 13 |
| 21.1 | 11 |
| 6.4 | 11 |

## 3. Entity Type Distribution
| Entity Type | Count |
|---|---|
| LINE | 379 |
| LWPOLYLINE | 131 |
| ARC | 71 |
| CIRCLE | 30 |
| MTEXT | 21 |
| SPLINE | 14 |
| DIMENSION | 13 |
| INSERT | 1 |

## 4. Layer Analysis & Classification
| Layer Name | Entities | Assigned Role | Confidence | Color | Locked |
|---|---|---|---|---|---|
| `0` | 9 | `UNKNOWN` | MEDIUM | 252 | False |
| `WALL` | 53 | `WALL` | HIGH | 7 | False |
| `DefPoints` | 0 | `UNKNOWN` | MEDIUM | 4 | False |
| `dim` | 336 | `DIMENSION` | HIGH | 7 | False |
| `FURINTURE` | 73 | `FURNITURE` | HIGH | 7 | False |
| `BEAM` | 5 | `STRUCTURAL` | HIGH | 251 | False |
| `Funiruture` | 2 | `UNKNOWN` | MEDIUM | 7 | False |
| `eleva` | 3 | `ELECTRICAL / ANNOTATION` | MEDIUM | 8 | False |
| `TAXT` | 15 | `ROOM_LABEL / ANNOTATION` | HIGH | 7 | False |
| `BASEPLAN$0$WALL` | 0 | `WALL` | HIGH | 8 | False |
| `BASEPLAN$0$PARKING` | 0 | `UNKNOWN` | MEDIUM | 8 | False |
| `BASEPLAN$0$4` | 0 | `UNKNOWN` | MEDIUM | 8 | False |
| `HATCH` | 87 | `SURFACE_HATCH` | HIGH | 252 | False |
| `ele` | 22 | `ELECTRICAL / ANNOTATION` | MEDIUM | 7 | False |
| `BLDGTEXT` | 6 | `ROOM_LABEL / ANNOTATION` | HIGH | 7 | False |
| `WIN GL` | 14 | `WINDOW` | HIGH | 142 | False |
| `BEAM FRAME` | 0 | `STRUCTURAL` | HIGH | 3 | False |
| `elctrical` | 2 | `ELECTRICAL / ANNOTATION` | MEDIUM | 10 | False |
| `CHAJJA` | 11 | `UNKNOWN` | MEDIUM | 8 | False |
| `WALLS UPDATED` | 16 | `WALL` | HIGH | 7 | False |
| `TREES` | 6 | `UNKNOWN` | MEDIUM | 7 | False |
| `Hatch architecture` | 0 | `SURFACE_HATCH` | HIGH | 252 | False |
| `COLUMNS UPDATED` | 0 | `STRUCTURAL` | HIGH | 1 | False |

## 5. Room Label & Annotation Candidates
Found **9** candidate room text labels in modelspace:

| Text Content | Layer | Position (X, Y) | Parsed Arch Dims |
|---|---|---|---|
| `\pi37.71182;{\fTrebuchet MS|b0|i0|c0|p34;ENTRY }` | `TAXT` | (123277.6, 19183.6) | [] |
| `\pi18.40708;{\fTrebuchet MS|b0|i0|c0|p34;dining }` | `TAXT` | (123392.0, 19292.2) | [] |
| `\pi21.27951,t28.27951;{\fTrebuchet MS|b0|i0|c0|p34;Balcony\P\pi0,tz;       3'6" x 3'0"}` | `TAXT` | (123336.6, 19503.8) | [42.0, 36.0] |
| `\pi18.07122;{\fTrebuchet MS|b1|i0|c0|p34;Kitchen \P\pi13.38367;7'0" x 8'3"}` | `TAXT` | (123447.9, 19419.6) | [84.0, 99.0] |
| `\pi12.90443;{\fTrebuchet MS|b1|i0|c0|p34;M. Bedroom \P\pi12.01806;11'4" x 10'8"}` | `TAXT` | (123593.5, 19364.2) | [136.0, 128.0] |
| `\pi14.29062;{\fTrebuchet MS|b1|i0|c0|p34;C. Bedroom\P\pi15.01419;9'0" x 11'3"}` | `TAXT` | (123543.6, 19548.8) | [108.0, 135.0] |
| `\pi24.02713;{\fTrebuchet MS|b1|i0|c0|p34;M. Toi. \P\pi17.58666;4'3" x 7'4"}` | `TAXT` | (123519.9, 19287.5) | [51.0, 88.0] |
| `\pi24.23894;{\fTrebuchet MS|b1|i0|c0|p34;C. Toi. \P\pi26.13641;6'0" x \P\pi30.08675;7'4"}` | `TAXT` | (123439.8, 19326.5) | [72.0, 88.0] |
| `\pi18.98153,t25.98153;{\fTrebuchet MS|b1|i0|c0|p34;Liv./Din.\P\pi10.05123,t17.05123;12'0" x 14'6"}` | `TAXT` | (123320.7, 19302.1) | [144.0, 174.0] |

## 6. Block Definitions & References
- **Total Block Definitions**: `25`
- **User Block Definitions**: `6`
- **Anonymous Blocks**: `19`
