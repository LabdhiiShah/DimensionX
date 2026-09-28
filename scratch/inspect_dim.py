"""
DIM Layer Entity Inspector for sample1.dxf
"""

import ezdxf
import math

doc = ezdxf.readfile("d:/end game/dwg/sample1.dxf")
msp = doc.modelspace()

dim_entities = list(msp.query('*[layer=="DIM"]'))
print(f"Total entities on layer 'DIM': {len(dim_entities)}")

lines_and_polys = [e for e in dim_entities if e.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE')]
print(f"LINE/LWPOLYLINE/POLYLINE on 'DIM': {len(lines_and_polys)}")

# Analyze lengths, parallel pairing, and enclosure behavior
boundary_candidates = []
dim_annotations = []

for e in lines_and_polys:
    t = e.dxftype()
    handle = e.dxf.handle
    if t == 'LINE':
        p1 = (e.dxf.start[0], e.dxf.start[1])
        p2 = (e.dxf.end[0], e.dxf.end[1])
        length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
        # Dimension extension/tick lines are very short (< 5.0 DXF units)
        # Wall boundary lines on DIM are long structural segments (e.g. > 15.0 or 20.0 DXF units)
        if length >= 15.0:
            boundary_candidates.append((handle, t, length, [p1, p2]))
        else:
            dim_annotations.append((handle, t, length))
    elif t in ('LWPOLYLINE', 'POLYLINE'):
        pts = list(e.get_points('xy'))
        if len(pts) >= 2:
            total_len = 0
            for i in range(len(pts)-1):
                total_len += math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])
            if total_len >= 15.0:
                boundary_candidates.append((handle, t, total_len, pts))
            else:
                dim_annotations.append((handle, t, total_len))

print(f"Boundary Candidates on DIM (length >= 15.0): {len(boundary_candidates)}")
print(f"Short Dimension Annotations on DIM (length < 15.0): {len(dim_annotations)}")

print("\nSample Boundary Candidates on DIM:")
for h, t, l, pts in boundary_candidates[:15]:
    print(f"  Handle '{h}': Type={t}, Length={l:.1f}, P1=({pts[0][0]:.1f}, {pts[0][1]:.1f})")
