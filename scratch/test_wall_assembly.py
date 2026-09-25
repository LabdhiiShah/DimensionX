"""
Test Wall Assembly & Enclosure Topology Generator for sample1.dxf
"""

import ezdxf
import math
from collections import defaultdict
from shapely.geometry import LineString, Point, Polygon, MultiLineString
from shapely.ops import unary_union, polygonize

def test_wall_assembly(dxf_path="d:/end game/dwg/sample1.dxf"):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Step 1: Extract Wall Candidates from WALL, WALLS_UPDATED, 0, and DIM (structural length >= 15)
    wall_lines = []
    for e in msp.query('LINE LWPOLYLINE POLYLINE'):
        layer_u = e.dxf.layer.upper()
        h = e.dxf.handle
        
        is_wall_layer = ('WALL' in layer_u or layer_u in ('0', 'BASEPLAN$0$WALL'))
        is_dim_wall = (layer_u == 'DIM')
        
        if e.dxftype() == 'LINE':
            p1 = (e.dxf.start[0], e.dxf.start[1])
            p2 = (e.dxf.end[0], e.dxf.end[1])
            length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            if min(p1[1], p2[1]) < 19230.0 and max(p1[1], p2[1]) < 19230.0:
                continue
            if is_wall_layer and length > 0.5:
                wall_lines.append((p1, p2, e.dxf.layer, h, "PRIMARY_WALL"))
            elif is_dim_wall and length >= 15.0:
                wall_lines.append((p1, p2, e.dxf.layer, h, "DIM_WALL_CANDIDATE"))

        elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
            pts = list(e.get_points('xy'))
            for i in range(len(pts)):
                p1 = (pts[i][0], pts[i][1])
                p2 = (pts[i+1][0], pts[i+1][1]) if i+1 < len(pts) else (pts[0][0], pts[0][1])
                if not e.closed and i == len(pts) - 1:
                    continue
                length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                if min(p1[1], p2[1]) < 19230.0 and max(p1[1], p2[1]) < 19230.0:
                    continue
                if is_wall_layer and length > 0.5:
                    wall_lines.append((p1, p2, e.dxf.layer, h, "PRIMARY_WALL"))
                elif is_dim_wall and length >= 15.0:
                    wall_lines.append((p1, p2, e.dxf.layer, h, "DIM_WALL_CANDIDATE"))

    print(f"Total Extracted Line Segments (including DIM candidates): {len(wall_lines)}")

    # Step 2: Weld Endpoints
    tol = 0.50
    vertices = []
    for p1, p2, l, h, role in wall_lines:
        vertices.append(p1)
        vertices.append(p2)
        
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
        avg_x = sum(v[0] for v in cluster) / len(cluster)
        avg_y = sum(v[1] for v in cluster) / len(cluster)
        wv = (round(avg_x, 2), round(avg_y, 2))
        for v in cluster:
            welded_map[v] = wv

    welded_lines = []
    seen = set()
    for p1, p2, l, h, role in wall_lines:
        wp1, wp2 = welded_map[p1], welded_map[p2]
        if wp1 == wp2: continue
        key = tuple(sorted([wp1, wp2]))
        if key not in seen:
            seen.add(key)
            welded_lines.append(LineString([wp1, wp2]))

    print(f"Welded Line Segments: {len(welded_lines)}")

    # Step 3: Noded Planar Graph & Polygonization
    multi_line = MultiLineString(welded_lines)
    noded = unary_union(multi_line)
    
    if isinstance(noded, LineString):
        lines_list = [noded]
    elif isinstance(noded, MultiLineString):
        lines_list = list(noded.geoms)
    else:
        lines_list = []

    clean_edges = []
    for ls in lines_list:
        if ls.length >= 0.5:
            clean_edges.append(ls)

    print(f"Clean Noded Edges: {len(clean_edges)}")

    # Step 4: Polygonize
    polys = list(polygonize(clean_edges))
    print(f"Polygonize found {len(polys)} total closed faces.")

    polys_sorted = sorted(polys, key=lambda p: p.area, reverse=True)
    
    # Filter out wall thickness returns (small rect loops with area < 40 sq units)
    macro_rooms = [p for p in polys_sorted if p.area >= 50.0]
    micro_returns = [p for p in polys_sorted if p.area < 50.0]
    
    print(f"Macro Room Spaces (area >= 50): {len(macro_rooms)}")
    print(f"Micro Wall Returns/Jambs (area < 50): {len(micro_returns)}")

    print("\nMacro Room Candidates Details:")
    for idx, p in enumerate(macro_rooms):
        b = p.bounds
        w = round(b[2]-b[0], 1)
        h = round(b[3]-b[1], 1)
        print(f"  Room {idx+1}: Area={p.area:.1f} sq units | Width={w} x Height={h} | Bounds=({b[0]:.1f}, {b[1]:.1f}) to ({b[2]:.1f}, {b[3]:.1f})")

if __name__ == "__main__":
    test_wall_assembly()
