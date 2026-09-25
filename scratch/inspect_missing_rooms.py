"""
Targeted Forensic Inspector for Missing Room Boundaries in sample1.dxf
"""

import ezdxf
import math

doc = ezdxf.readfile("d:/end game/dwg/sample1.dxf")
msp = doc.modelspace()

print("=== INSPECTING GEOMETRY NEAR MASTER BEDROOM (X ~ 122680-122780, Y ~ 19500-19600) ===")
for e in msp.query('LINE LWPOLYLINE POLYLINE ARC'):
    layer = e.dxf.layer
    t = e.dxftype()
    if t == 'LINE':
        p1 = (e.dxf.start[0], e.dxf.start[1])
        p2 = (e.dxf.end[0], e.dxf.end[1])
        if 122650 <= min(p1[0], p2[0]) <= 122800 and 19480 <= min(p1[1], p2[1]) <= 19600:
            length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            print(f"  [{layer}] Handle '{e.dxf.handle}': LINE P1=({p1[0]:.1f}, {p1[1]:.1f}) -> P2=({p2[0]:.1f}, {p2[1]:.1f}), Len={length:.1f}")
    elif t == 'LWPOLYLINE':
        pts = list(e.get_points('xy'))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if 122650 <= min(xs) <= 122800 and 19480 <= min(ys) <= 19600:
            print(f"  [{layer}] Handle '{e.dxf.handle}': LWPOLYLINE pts={len(pts)}, closed={e.closed}, bounds=({min(xs):.1f}, {min(ys):.1f}) to ({max(xs):.1f}, {max(ys):.1f})")
            for i in range(len(pts)-(0 if e.closed else 1)):
                p1 = pts[i]
                p2 = pts[(i+1)%len(pts)]
                print(f"     Segment {i}: ({p1[0]:.1f}, {p1[1]:.1f}) -> ({p2[0]:.1f}, {p2[1]:.1f})")

print("\n=== INSPECTING GEOMETRY NEAR LIVING/DINING (X ~ 122850-123020, Y ~ 19300-19500) ===")
for e in msp.query('LINE LWPOLYLINE POLYLINE ARC'):
    layer = e.dxf.layer
    t = e.dxftype()
    if t == 'LINE':
        p1 = (e.dxf.start[0], e.dxf.start[1])
        p2 = (e.dxf.end[0], e.dxf.end[1])
        if 122850 <= min(p1[0], p2[0]) <= 123050 and 19300 <= min(p1[1], p2[1]) <= 19500:
            length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            print(f"  [{layer}] Handle '{e.dxf.handle}': LINE P1=({p1[0]:.1f}, {p1[1]:.1f}) -> P2=({p2[0]:.1f}, {p2[1]:.1f}), Len={length:.1f}")
    elif t == 'LWPOLYLINE':
        pts = list(e.get_points('xy'))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if 122850 <= min(xs) <= 123050 and 19300 <= min(ys) <= 19500:
            print(f"  [{layer}] Handle '{e.dxf.handle}': LWPOLYLINE pts={len(pts)}, closed={e.closed}, bounds=({min(xs):.1f}, {min(ys):.1f}) to ({max(xs):.1f}, {max(ys):.1f})")
            for i in range(len(pts)-(0 if e.closed else 1)):
                p1 = pts[i]
                p2 = pts[(i+1)%len(pts)]
                print(f"     Segment {i}: ({p1[0]:.1f}, {p1[1]:.1f}) -> ({p2[0]:.1f}, {p2[1]:.1f})")
