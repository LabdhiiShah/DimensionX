"""
Test Script for Fixes 1-5 on sample1.dxf
"""

import ezdxf
import math
from collections import defaultdict
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiLineString
from shapely.ops import unary_union, polygonize

def test_full_fixes(dxf_path="d:/end game/dwg/sample1.dxf"):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # FIX 1: Smart DIM Layer Wall Extraction
    raw_wall_lines = []
    dim_wall_count = 0
    primary_wall_count = 0

    for e in msp.query('LINE LWPOLYLINE POLYLINE'):
        layer_u = e.dxf.layer.upper()
        h = e.dxf.handle
        
        is_wall_layer = ('WALL' in layer_u or layer_u in ('0', 'BASEPLAN$0$WALL'))
        is_dim_wall = (layer_u == 'DIM')
        
        if e.dxftype() == 'LINE':
            p1 = (e.dxf.start[0], e.dxf.start[1])
            p2 = (e.dxf.end[0], e.dxf.end[1])
            length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
            # Title block filter
            if min(p1[1], p2[1]) < 19230.0 and max(p1[1], p2[1]) < 19230.0:
                continue
            if is_wall_layer and length > 0.5:
                raw_wall_lines.append({
                    "p1": p1, "p2": p2, "layer": e.dxf.layer, "handle": h, "source": "PRIMARY_WALL"
                })
                primary_wall_count += 1
            elif is_dim_wall and length >= 15.0:
                raw_wall_lines.append({
                    "p1": p1, "p2": p2, "layer": e.dxf.layer, "handle": h, "source": "DIM_WALL_CANDIDATE"
                })
                dim_wall_count += 1

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
                    raw_wall_lines.append({
                        "p1": p1, "p2": p2, "layer": e.dxf.layer, "handle": h, "source": "PRIMARY_WALL"
                    })
                    primary_wall_count += 1
                elif is_dim_wall and length >= 15.0:
                    raw_wall_lines.append({
                        "p1": p1, "p2": p2, "layer": e.dxf.layer, "handle": h, "source": "DIM_WALL_CANDIDATE"
                    })
                    dim_wall_count += 1

    print("==================================================")
    print("FIX 1: EXTRACTION SUMMARY")
    print("==================================================")
    print(f"Primary Wall Segments Extracted: {primary_wall_count}")
    print(f"DIM Layer Wall Candidate Segments Extracted: {dim_wall_count}")
    print(f"Total Raw Wall Candidates: {len(raw_wall_lines)}")

    # FIX 2: Endpoint Welding & Planar Topology Assembly
    tol = 0.50
    vertices = []
    for obj in raw_wall_lines:
        vertices.append(obj["p1"])
        vertices.append(obj["p2"])
        
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
    for obj in raw_wall_lines:
        wp1, wp2 = welded_map[obj["p1"]], welded_map[obj["p2"]]
        if wp1 == wp2: continue
        key = tuple(sorted([wp1, wp2]))
        if key not in seen:
            seen.add(key)
            welded_lines.append(LineString([wp1, wp2]))

    # Noded Planar Graph
    multi_line = MultiLineString(welded_lines)
    noded = unary_union(multi_line)
    lines_list = list(noded.geoms) if isinstance(noded, MultiLineString) else [noded]

    clean_edges = [ls for ls in lines_list if ls.length >= 0.5]
    print(f"\nPlanar Wall Graph Edges: {len(clean_edges)}")

    # Polygonize
    raw_polys = list(polygonize(clean_edges))
    print(f"Raw Polygons from Polygonizer: {len(raw_polys)}")

    # Separate Macro Rooms vs Internal Wall Return Voids
    macro_rooms = []
    wall_voids = []
    
    for p in raw_polys:
        b = p.bounds
        w = b[2] - b[0]
        h = b[3] - b[1]
        aspect = max(w, h) / max(min(w, h), 1e-3)
        # Internal wall thickness void polygons are narrow rects or tiny loops
        if p.area < 100.0 or (aspect > 6.0 and min(w, h) <= 10.0):
            wall_voids.append(p)
        else:
            macro_rooms.append({
                "room_id": f"room_{len(macro_rooms)+1}",
                "polygon": p,
                "area": round(p.area, 1),
                "bounds": [round(x, 1) for x in b]
            })

    print("==================================================")
    print("FIX 2: ROOM CANDIDATES SUMMARY")
    print("==================================================")
    print(f"Valid Macro Rooms: {len(macro_rooms)}")
    print(f"Filtered Wall Return Voids: {len(wall_voids)}")
    
    for r in macro_rooms:
        b = r["bounds"]
        print(f"  {r['room_id']}: Area={r['area']} sq units | Bounds=({b[0]}, {b[1]}) to ({b[2]}, {b[3]})")

    # FIX 3: Ranked Semantic Label Assignment
    room_keywords = ["BEDROOM", "BED", "KITCHEN", "LIVING", "LIV", "DINING", "DIN", 
                     "TOILET", "TOI", "BATH", "BALCONY", "ENTRY", "HALL", "PASSAGE"]
    
    text_labels = []
    for e in msp.query('TEXT MTEXT'):
        is_mtext = (e.dxftype() == 'MTEXT')
        txt = e.text if is_mtext else e.dxf.text
        clean_txt = txt.strip()
        layer = e.dxf.layer
        pos = (e.dxf.insert[0], e.dxf.insert[1])
        upper_txt = clean_txt.upper()
        if any(kw in upper_txt for kw in room_keywords):
            # Clean MTEXT formatting tags
            import re
            clean = re.sub(r'\{[^{}]*\}', '', clean_txt)
            clean = re.sub(r'\\P', ' ', clean).strip()
            text_labels.append({
                "raw_text": clean_txt,
                "clean_name": clean,
                "pos": pos,
                "layer": layer,
                "handle": e.dxf.handle
            })

    print("\n==================================================")
    print("FIX 3: RANKED SEMANTIC LABEL ASSIGNMENT")
    print("==================================================")
    print(f"Found {len(text_labels)} CAD Room Text Callouts.")

    # Candidate scoring matrix
    assignments = {} # room_id -> label
    assigned_labels = set()

    # Score every (label, room) pair
    scored_pairs = []
    for l_idx, lbl in enumerate(text_labels):
        l_pt = Point(lbl["pos"])
        for r in macro_rooms:
            r_poly = r["polygon"]
            centroid = r_poly.centroid
            dist_to_centroid = l_pt.distance(centroid)
            is_inside = r_poly.contains(l_pt)
            dist_to_boundary = r_poly.distance(l_pt)
            
            if is_inside or dist_to_boundary < 60.0:
                score = 0.0
                if is_inside:
                    score += 100.0 - (dist_to_centroid * 0.1)
                else:
                    score += 50.0 - dist_to_boundary
                scored_pairs.append((score, l_idx, r["room_id"]))

    # Sort descending by score
    scored_pairs.sort(key=lambda x: x[0], reverse=True)

    assigned_room_ids = set()
    assigned_label_indices = set()

    for score, l_idx, r_id in scored_pairs:
        if l_idx in assigned_label_indices or r_id in assigned_room_ids:
            continue
        lbl = text_labels[l_idx]
        assignments[r_id] = {
            "name": lbl["clean_name"],
            "score": round(score, 1),
            "status": "CONFIRMED"
        }
        assigned_label_indices.add(l_idx)
        assigned_room_ids.add(r_id)

    for r in macro_rooms:
        r_id = r["room_id"]
        if r_id in assignments:
            info = assignments[r_id]
            print(f"  {r_id} (Area {r['area']}) -> ASSIGNED '{info['name']}' (Score: {info['score']})")
        else:
            print(f"  {r_id} (Area {r['area']}) -> UNASSIGNED")

    unassigned_texts = [text_labels[i]["clean_name"] for i in range(len(text_labels)) if i not in assigned_label_indices]
    if unassigned_texts:
        print(f"\nUnassigned CAD Text Callouts: {unassigned_texts}")

    # FIX 4: Building Footprint from Wall Outer Envelope
    print("\n==================================================")
    print("FIX 4: BUILDING FOOTPRINT SUMMARY")
    print("==================================================")
    wall_buffers = [ls.buffer(5.0) for ls in clean_edges]
    room_polys = [r["polygon"] for r in macro_rooms]
    all_envelope = unary_union(wall_buffers + room_polys)

    if isinstance(all_envelope, Polygon):
        footprint_poly = all_envelope
    elif isinstance(all_envelope, MultiPolygon):
        footprint_poly = max(all_envelope.geoms, key=lambda p: p.area)
    else:
        footprint_poly = None

    if footprint_poly:
        ext_coords = list(footprint_poly.exterior.coords)
        print(f"Footprint Reconstructed Successfully!")
        print(f"  Footprint Area: {footprint_poly.area:.1f} sq units")
        print(f"  Footprint Perimeter: {footprint_poly.length:.1f} units")
        print(f"  Exterior Vertices Count: {len(ext_coords)}")

    # FIX 5: Architectural Validation
    print("\n==================================================")
    print("FIX 5: ARCHITECTURAL VALIDATION SUMMARY")
    print("==================================================")
    blocking_errors = []
    warnings = []

    # Check unmapped major callouts
    major_keywords = ["BEDROOM", "LIVING", "KITCHEN", "TOILET", "BALCONY", "ENTRY"]
    for txt_obj in text_labels:
        txt = txt_obj["clean_name"].upper()
        if any(kw in txt for kw in major_keywords):
            if txt_obj["clean_name"] in unassigned_texts:
                blocking_errors.append({
                    "category": "SEMANTICS",
                    "code": "UNMAPPED_MAJOR_ROOM_TEXT",
                    "message": f"Major CAD room callout '{txt_obj['clean_name']}' failed to map to a room candidate."
                })

    # Check footprint coverage
    all_x = [ls.coords[0][0] for ls in clean_edges] + [ls.coords[1][0] for ls in clean_edges]
    all_y = [ls.coords[0][1] for ls in clean_edges] + [ls.coords[1][1] for ls in clean_edges]
    bbox_w = max(all_x) - min(all_x)
    bbox_h = max(all_y) - min(all_y)
    bbox_area = bbox_w * bbox_h
    
    if footprint_poly:
        coverage_ratio = footprint_poly.area / bbox_area
        print(f"Footprint Bounding Box Coverage Ratio: {coverage_ratio:.2%}")
        if coverage_ratio < 0.35:
            blocking_errors.append({
                "category": "FOOTPRINT",
                "code": "FRAGMENTED_BUILDING_FOOTPRINT",
                "message": f"Building footprint covers only {coverage_ratio:.1%} of drawing extents."
            })

    # Check micro polygon ratio
    if len(raw_polys) > 0:
        void_ratio = len(wall_voids) / len(raw_polys)
        if void_ratio > 0.40:
            warnings.append({
                "category": "TOPOLOGY",
                "code": "HIGH_WALL_VOID_RATIO",
                "message": f"{void_ratio:.1%} of raw faces were internal wall-thickness voids."
            })

    is_passed = len(blocking_errors) == 0
    print(f"Validation Status: {'PASSED' if is_passed else 'FAILED'}")
    print(f"Blocking Errors ({len(blocking_errors)}): {blocking_errors}")
    print(f"Warnings ({len(warnings)}): {warnings}")

if __name__ == "__main__":
    test_full_fixes()
