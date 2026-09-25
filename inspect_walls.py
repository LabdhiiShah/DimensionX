import ezdxf
import math

doc = ezdxf.readfile("d:/end game/dwg/sample1.dxf")
msp = doc.modelspace()

wall_lines = []
for e in msp.query('LINE LWPOLYLINE'):
    if 'WALL' in e.dxf.layer.upper():
        if e.dxftype() == 'LINE':
            p1 = (e.dxf.start[0], e.dxf.start[1])
            p2 = (e.dxf.end[0], e.dxf.end[1])
            wall_lines.append((p1, p2, e.dxf.layer, e.dxf.handle))
        elif e.dxftype() == 'LWPOLYLINE':
            pts = list(e.get_points('xy'))
            for i in range(len(pts) - (0 if e.closed else 1)):
                p1 = (pts[i][0], pts[i][1])
                p2 = (pts[(i+1)%len(pts)][0], pts[(i+1)%len(pts)][1])
                wall_lines.append((p1, p2, e.dxf.layer, e.dxf.handle))

print(f"Total wall segments extracted: {len(wall_lines)}")
for idx, (p1, p2, layer, handle) in enumerate(wall_lines[:15]):
    length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
    print(f"  [{idx}] Layer: {layer}, Handle: {handle}, P1: ({p1[0]:.2f}, {p1[1]:.2f}), P2: ({p2[0]:.2f}, {p2[1]:.2f}), Len: {length:.2f}")
