"""
Forensic Pipeline Tracer for sample1.dxf
=========================================
Traces entity handles, layers, geometry, node splitting, room polygonization,
text point-in-polygon matching, and footprint derivation without modifying pipeline code.
"""

import ezdxf
import math
from collections import defaultdict
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiLineString
from shapely.ops import unary_union, polygonize

def run_forensic_trace(dxf_path="d:/end game/dwg/sample1.dxf"):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    print("==================================================")
    print("STAGE 1: DXF ENTITIES AUDIT & LAYER BREAKDOWN")
    print("==================================================")
    
    layer_counts = defaultdict(lambda: defaultdict(int))
    entity_handles_by_layer = defaultdict(list)
    total_entities = 0

    for e in msp:
        total_entities += 1
        l = e.dxf.layer
        t = e.dxftype()
        layer_counts[l][t] += 1
        entity_handles_by_layer[l].append((e.dxf.handle, t))

    print(f"Total Modelspace Entities: {total_entities}")
    print("\nLayer Entity Counts:")
    for l, counts in sorted(layer_counts.items(), key=lambda x: sum(x[1].values()), reverse=True):
        print(f"  Layer '{l}': total {sum(counts.values())} -> {dict(counts)}")

    wall_layers = ['WALL', 'WALLS_UPDATED']
    print(f"\nEntities on Wall Layers ({wall_layers}):")
    wall_layer_entities = []
    for l in wall_layers:
        ents = entity_handles_by_layer[l]
        print(f"  Layer '{l}': {len(ents)} entities")
        for h, t in ents:
            wall_layer_entities.append((l, h, t))

    print("\n==================================================")
    print("STAGE 2 & 3: ARCHITECTURAL EXTRACTION & WALL CANDIDATES")
    print("==================================================")

    # Re-run extraction logic exactly as geometry_engine.py does
    raw_wall_lines = []
    wall_polygons = []
    ignored_entities = []

    for e in msp.query('LINE LWPOLYLINE POLYLINE'):
        layer_upper = e.dxf.layer.upper()
        # Filtering check in geometry_engine.py:
        is_wall_layer = ('WALL' in layer_upper or layer_upper in ('0', 'BASEPLAN$0$WALL'))
        
        if is_wall_layer:
            if e.dxftype() == 'LINE':
                p1 = (e.dxf.start[0], e.dxf.start[1])
                p2 = (e.dxf.end[0], e.dxf.end[1])
                # Title block filter in geometry_engine.py: min(y1,y2) < 19230
                if min(p1[1], p2[1]) < 19230.0 and max(p1[1], p2[1]) < 19230.0:
                    ignored_entities.append((e.dxf.handle, e.dxf.layer, e.dxftype(), "FILTERED_TITLE_BLOCK_Y_COORD"))
                    continue
                if math.hypot(p2[0]-p1[0], p2[1]-p1[1]) > 0.1:
                    raw_wall_lines.append({
                        "p1": p1, "p2": p2, 
                        "layer": e.dxf.layer, 
                        "handle": e.dxf.handle,
                        "type": "LINE"
                    })
                else:
                    ignored_entities.append((e.dxf.handle, e.dxf.layer, e.dxftype(), "REJECTED_ZERO_LENGTH"))
            elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                pts = list(e.get_points('xy'))
                if e.closed and len(pts) >= 3:
                    poly = Polygon(pts)
                    if poly.is_valid and poly.area > 1.0:
                        wall_polygons.append({
                            "polygon": poly,
                            "layer": e.dxf.layer,
                            "handle": e.dxf.handle
                        })
                for i in range(len(pts)):
                    p1 = (pts[i][0], pts[i][1])
                    p2 = (pts[i+1][0], pts[i+1][1]) if i+1 < len(pts) else (pts[0][0], pts[0][1])
                    if not e.closed and i == len(pts) - 1:
                        continue
                    if min(p1[1], p2[1]) < 19230.0 and max(p1[1], p2[1]) < 19230.0:
                        ignored_entities.append((e.dxf.handle, e.dxf.layer, e.dxftype(), "FILTERED_TITLE_BLOCK_Y_COORD"))
                        continue
                    if math.hypot(p2[0]-p1[0], p2[1]-p1[1]) > 0.1:
                        raw_wall_lines.append({
                            "p1": p1, "p2": p2,
                            "layer": e.dxf.layer,
                            "handle": e.dxf.handle,
                            "type": e.dxftype()
                        })
                    else:
                        ignored_entities.append((e.dxf.handle, e.dxf.layer, e.dxftype(), "REJECTED_ZERO_LENGTH"))
        else:
            ignored_entities.append((e.dxf.handle, e.dxf.layer, e.dxftype(), "IGNORED_NON_WALL_LAYER"))

    print(f"Extracted Raw Wall Segments: {len(raw_wall_lines)}")
    print(f"Extracted Closed Wall Boundary Polygons: {len(wall_polygons)}")
    print(f"Total Ignored/Rejected Entities: {len(ignored_entities)}")

    print("\nBreakdown of Extracted Raw Segments by Layer:")
    raw_by_layer = defaultdict(int)
    for seg in raw_wall_lines:
        raw_by_layer[seg["layer"]] += 1
    for l, c in raw_by_layer.items():
        print(f"  Layer '{l}': {c} line segments")

    print("\n==================================================")
    print("STAGE 4: ENDPOINT WELDING & WELDED LINES")
    print("==================================================")
    
    tol = 0.25
    vertices = []
    for obj in raw_wall_lines:
        vertices.append(obj["p1"])
        vertices.append(obj["p2"])
        
    welded_vertex_map = {}
    used = [False] * len(vertices)
    for i in range(len(vertices)):
        if used[i]: continue
        v_i = vertices[i]
        cluster = [v_i]
        used[i] = True
        for j in range(i + 1, len(vertices)):
            if not used[j]:
                v_j = vertices[j]
                if math.hypot(v_j[0] - v_i[0], v_j[1] - v_i[1]) <= tol:
                    cluster.append(v_j)
                    used[j] = True
        avg_x = sum(v[0] for v in cluster) / len(cluster)
        avg_y = sum(v[1] for v in cluster) / len(cluster)
        welded_v = (round(avg_x, 3), round(avg_y, 3))
        for v in cluster:
            welded_vertex_map[v] = welded_v

    welded_lines = []
    seen = set()
    for obj in raw_wall_lines:
        wp1 = welded_vertex_map[obj["p1"]]
        wp2 = welded_vertex_map[obj["p2"]]
        if wp1 == wp2: continue
        key = tuple(sorted([wp1, wp2]))
        if key not in seen:
            seen.add(key)
            welded_lines.append({
                "p1": wp1, "p2": wp2,
                "layer": obj["layer"],
                "handles": [obj["handle"]]
            })
        else:
            for wl in welded_lines:
                if tuple(sorted([wl["p1"], wl["p2"]])) == key:
                    wl["handles"].append(obj["handle"])
                    break

    print(f"Welded {len(raw_wall_lines)} raw segments down to {len(welded_lines)} unique line segments.")

    print("\n==================================================")
    print("STAGE 5: PLANAR GRAPH NODE SPLITTING ANALYSIS")
    print("==================================================")
    
    shapely_lines = [LineString([obj["p1"], obj["p2"]]) for obj in welded_lines]
    multi_line = MultiLineString(shapely_lines)
    noded_lines = unary_union(multi_line)

    planar_edges = []
    if isinstance(noded_lines, LineString):
        lines_list = [noded_lines]
    elif isinstance(noded_lines, MultiLineString):
        lines_list = list(noded_lines.geoms)
    else:
        lines_list = []

    edge_id = 0
    nodes = set()
    for ls in lines_list:
        if ls.length < 0.05: continue
        coords = list(ls.coords)
        for i in range(len(coords) - 1):
            p1 = (round(coords[i][0], 3), round(coords[i][1], 3))
            p2 = (round(coords[i+1][0], 3), round(coords[i+1][1], 3))
            edge_len = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            if p1 != p2 and edge_len >= 0.05:
                nodes.add(p1)
                nodes.add(p2)
                planar_edges.append({
                    "edge_id": f"wall_edge_{edge_id}",
                    "p1": p1, "p2": p2,
                    "length": round(edge_len, 3),
                    "geometry": LineString([p1, p2])
                })
                edge_id += 1

    print(f"Planar Graph Nodes: {len(nodes)}")
    print(f"Planar Graph Edges: {len(planar_edges)}")
    print(f"-> EXPLANATION OF EDGE EXPANSION: {len(welded_lines)} input segments intersected & split into {len(planar_edges)} noded edges at T-junctions, cross intersections, and parallel boundary offsets.")

    print("\n==================================================")
    print("STAGE 6: POLYGONIZATION & ROOM CANNIDATES FORENSICS")
    print("==================================================")

    edge_geoms = [e["geometry"] for e in planar_edges]
    polys = list(polygonize(edge_geoms))
    print(f"Raw Polygons from Polygonize: {len(polys)}")

    polys_sorted = sorted(polys, key=lambda p: p.area, reverse=True)
    print("\nTop 15 Polygons by Area:")
    for idx, p in enumerate(polys_sorted[:15]):
        b = p.bounds
        w = round(b[2]-b[0], 2)
        h = round(b[3]-b[1], 2)
        print(f"  [{idx+1}] Area: {p.area:.2f} sq units | Width x Height: {w} x {h} | Bounds: ({b[0]:.1f}, {b[1]:.1f}) to ({b[2]:.1f}, {b[3]:.1f})")

    print("\nTiny Polygons (< 50 sq units):")
    tiny_count = sum(1 for p in polys if p.area < 50.0)
    large_count = sum(1 for p in polys if p.area >= 50.0)
    print(f"  Tiny polygons (area < 50): {tiny_count}")
    print(f"  Large polygons (area >= 50): {large_count}")

    print("\n==================================================")
    print("STAGE 7: TEXT ROOM LABEL POINT-IN-POLYGON FORENSICS")
    print("==================================================")

    room_keywords = ["BEDROOM", "BED", "KITCHEN", "LIVING", "LIV", "DINING", "DIN", 
                     "TOILET", "TOI", "BATH", "BALCONY", "ENTRY", "HALL", "PASSAGE", "DRAWING"]
    text_objs = []
    for e in msp.query('TEXT MTEXT'):
        is_mtext = (e.dxftype() == 'MTEXT')
        txt = e.text if is_mtext else e.dxf.text
        clean_txt = txt.strip()
        layer = e.dxf.layer
        pos = list(e.dxf.insert)
        upper_txt = clean_txt.upper()
        if any(kw in upper_txt for kw in room_keywords):
            text_objs.append((clean_txt, layer, (pos[0], pos[1]), e.dxf.handle))

    print(f"Found {len(text_objs)} Room Text Callouts in DXF:")
    for txt, l, pos, h in text_objs:
        pt = Point(pos)
        containing_faces = []
        for p_idx, p in enumerate(polys_sorted):
            if p.contains(pt):
                containing_faces.append((p_idx+1, p.area))
            elif p.distance(pt) < 15.0:
                containing_faces.append((f"{p_idx+1} (dist {p.distance(pt):.1f})", p.area))
        print(f"  Handle '{h}': [{l}] '{txt}' at ({pos[0]:.1f}, {pos[1]:.1f}) -> Matches Faces: {containing_faces[:4]}")

    print("\n==================================================")
    print("STAGE 8: SAMPLE ENTITY HANDLE TRACE (10 REPRESENTATIVE ENTITIES)")
    print("==================================================")

    sample_handles = ['F1', 'F4', 'F5', 'F6', 'F8', 'FA', 'FC', '109', '10A', '10B']
    for h in sample_handles:
        try:
            ent = doc.entitydb.get(h)
            if ent:
                l = ent.dxf.layer
                t = ent.dxftype()
                if t == 'LINE':
                    p1 = (round(ent.dxf.start[0],1), round(ent.dxf.start[1],1))
                    p2 = (round(ent.dxf.end[0],1), round(ent.dxf.end[1],1))
                    length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                    print(f"  Handle '{h}': Layer='{l}', Type='{t}', P1={p1}, P2={p2}, Len={length:.1f}")
                elif t == 'LWPOLYLINE':
                    pts = list(ent.get_points('xy'))
                    print(f"  Handle '{h}': Layer='{l}', Type='{t}', Points={len(pts)}, Closed={ent.closed}")
            else:
                print(f"  Handle '{h}': NOT FOUND in database")
        except Exception as err:
            print(f"  Handle '{h}': Error reading handle ({err})")

if __name__ == "__main__":
    run_forensic_trace()
