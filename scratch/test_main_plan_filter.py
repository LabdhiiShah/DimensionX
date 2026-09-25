"""
Test Main House Plan Filter (X >= 122670) for sample1.dxf
"""

import ezdxf
import math
from collections import defaultdict
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiLineString
from shapely.ops import unary_union, polygonize

doc = ezdxf.readfile("d:/end game/dwg/sample1.dxf")
msp = doc.modelspace()

raw_wall_lines = []
for e in msp.query('LINE LWPOLYLINE POLYLINE'):
    layer_u = e.dxf.layer.upper()
    h = e.dxf.handle
    
    is_primary_wall = ('WALL' in layer_u or layer_u in ('0', 'BASEPLAN$0$WALL'))
    is_dim_wall = (layer_u == 'DIM')
    
    if is_primary_wall or is_dim_wall:
        if e.dxftype() == 'LINE':
            p1 = (e.dxf.start[0], e.dxf.start[1])
            p2 = (e.dxf.end[0], e.dxf.end[1])
            length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            
            # Filter out title block / legend frame (Y < 19230 or X < 122670)
            if min(p1[1], p2[1]) < 19230.0 and max(p1[1], p2[1]) < 19230.0: continue
            if min(p1[0], p2[0]) < 122670.0 and max(p1[0], p2[0]) < 122670.0: continue
            
            if is_primary_wall and length > 0.5:
                raw_wall_lines.append((p1, p2, e.dxf.layer))
            elif is_dim_wall and length >= 15.0:
                raw_wall_lines.append((p1, p2, e.dxf.layer))

        elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
            pts = list(e.get_points('xy'))
            for i in range(len(pts)):
                p1 = (pts[i][0], pts[i][1])
                p2 = (pts[i+1][0], pts[i+1][1]) if i+1 < len(pts) else (pts[0][0], pts[0][1])
                if not e.closed and i == len(pts) - 1: continue
                length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                if min(p1[1], p2[1]) < 19230.0 and max(p1[1], p2[1]) < 19230.0: continue
                if min(p1[0], p2[0]) < 122670.0 and max(p1[0], p2[0]) < 122670.0: continue
                
                if is_primary_wall and length > 0.5:
                    raw_wall_lines.append((p1, p2, e.dxf.layer))
                elif is_dim_wall and length >= 15.0:
                    raw_wall_lines.append((p1, p2, e.dxf.layer))

print(f"Extracted Wall Segments (filtering legend X < 122670): {len(raw_wall_lines)}")

# Weld
tol = 0.50
vertices = [p for seg in raw_wall_lines for p in (seg[0], seg[1])]
welded_map = {}
used = [False] * len(vertices)
for i in range(len(vertices)):
    if used[i]: continue
    v_i = vertices[i]
    cluster = [v_i]
    used[i] = True
    for j in range(i + 1, len(vertices)):
        if not used[j]:
            v_j = vertices[j]
            if math.hypot(v_j[0]-v_i[0], v_j[1]-v_i[1]) <= tol:
                cluster.append(v_j)
                used[j] = True
    wv = (round(sum(v[0] for v in cluster)/len(cluster), 2), round(sum(v[1] for v in cluster)/len(cluster), 2))
    for v in cluster: welded_map[v] = wv

welded_lines = []
seen = set()
for p1, p2, l in raw_wall_lines:
    wp1, wp2 = welded_map[p1], welded_map[p2]
    if wp1 == wp2: continue
    key = tuple(sorted([wp1, wp2]))
    if key not in seen:
        seen.add(key)
        welded_lines.append(LineString([wp1, wp2]))

multi = MultiLineString(welded_lines)
noded = unary_union(multi)
lines_list = list(noded.geoms) if isinstance(noded, MultiLineString) else [noded]
clean_edges = [ls for ls in lines_list if ls.length >= 0.5]

polys = list(polygonize(clean_edges))
polys_sorted = sorted(polys, key=lambda p: p.area, reverse=True)

macro_rooms = [p for p in polys_sorted if p.area >= 100.0]
print(f"Macro Rooms in House Plan: {len(macro_rooms)}")
for idx, p in enumerate(macro_rooms):
    b = p.bounds
    w, h = round(b[2]-b[0], 1), round(b[3]-b[1], 1)
    print(f"  Room {idx+1}: Area={p.area:.1f} sq units | WxH={w} x {h} | Bounds=({b[0]:.1f}, {b[1]:.1f}) to ({b[2]:.1f}, {b[3]:.1f})")
