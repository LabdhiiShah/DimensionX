"""
Test Script for Room Semantics & Door Association Fixes on sample1.dxf
"""

import sys
import math
import re
from collections import defaultdict
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiLineString
from shapely.ops import unary_union, polygonize

sys.path.append("d:/end game/haha")
import ezdxf
from dxf_auditor import run_full_audit
from geometry_engine import GeometryEngine
from aperture_engine import ApertureEngine

def test_semantics():
    dxf_path = "d:/end game/dwg/sample1.dxf"
    doc = ezdxf.readfile(dxf_path)
    audit_data = run_full_audit(dxf_path, output_dir="output")

    geom_engine = GeometryEngine(doc, audit_data=audit_data)
    geom_results = geom_engine.extract_wall_centerlines_and_boundaries()

    raw_rooms = geom_results["room_polygons"]
    planar_edges = geom_results["planar_edges"]

    # Step 1: Classify Room Candidates into MEANINGFUL_SPACE vs MICRO_GEOMETRY / WALL_RETURN / UNKNOWN_FRAGMENT
    meaningful_rooms = []
    micro_geometries = []
    wall_returns = []
    unknown_fragments = []

    for r in raw_rooms:
        poly = r["polygon"]
        b = r["bounds"]
        w = b[2] - b[0]
        h = b[3] - b[1]
        aspect = max(w, h) / max(min(w, h), 1e-3)
        area = r["area"]

        if area < 50.0:
            micro_geometries.append(r)
        elif min(w, h) <= 12.0 or aspect > 6.0:
            wall_returns.append(r)
        elif area < 150.0:
            unknown_fragments.append(r)
        else:
            meaningful_rooms.append(r)

    print("==================================================")
    print("STEP 1: ROOM CANDIDATE CLASSIFICATION")
    print("==================================================")
    print(f"Meaningful Room Candidates: {len(meaningful_rooms)}")
    print(f"Micro Geometries (< 50 sq units): {len(micro_geometries)}")
    print(f"Wall Returns / Narrow Voids: {len(wall_returns)}")
    print(f"Unknown Fragments (50-150 sq units): {len(unknown_fragments)}")

    print("\nMeaningful Room Candidates List:")
    for r in meaningful_rooms:
        b = r["bounds"]
        print(f"  [{r['room_id']}] Area={r['area']:.1f} sq units | Bounds=({b[0]:.1f}, {b[1]:.1f}) to ({b[2]:.1f}, {b[3]:.1f})")

    # Step 2: Extract & Merge CAD Room Text Callouts (No Synthetic Geometry!)
    msp = doc.modelspace()
    room_keywords = ["BEDROOM", "BED", "KITCHEN", "LIVING", "LIV", "DINING", "DIN", 
                     "TOILET", "TOI", "BATH", "BALCONY", "ENTRY", "HALL", "PASSAGE"]
    
    raw_texts = []
    for e in msp.query('TEXT MTEXT'):
        is_mtext = (e.dxftype() == 'MTEXT')
        txt = e.text if is_mtext else e.dxf.text
        clean_txt = txt.strip()
        pos = (e.dxf.insert[0], e.dxf.insert[1])
        upper = clean_txt.upper()
        if any(kw in upper for kw in room_keywords):
            clean_name = re.sub(r'\{[^{}]*\}', '', clean_txt)
            clean_name = re.sub(r'\\P', ' ', clean_name).strip()
            
            # Extract dimensions if present (e.g. 9'3" x 11'0")
            dims_pattern = r"(\d+)'\s*(\d+(?:\.\d+)?)\"?"
            matches = re.findall(dims_pattern, clean_txt)
            dims_inches = [float(ft)*12.0 + float(inch) for ft, inch in matches]
            
            raw_texts.append({
                "clean_name": clean_name,
                "upper_name": upper,
                "pos": pos,
                "declared_dims": dims_inches,
                "layer": e.dxf.layer,
                "handle": e.dxf.handle
            })

    # Group duplicate text callouts by semantic category to assign uniquely
    semantic_groups = defaultdict(list)
    for t in raw_texts:
        if "BEDROOM" in t["upper_name"] or "BED" in t["upper_name"]:
            group_key = "MASTER_BEDROOM"
        elif "LIV" in t["upper_name"] or "DIN" in t["upper_name"]:
            group_key = "LIVING_DINING"
        elif "KITCHEN" in t["upper_name"]:
            group_key = "KITCHEN"
        elif "M. TOI" in t["upper_name"] or ("TOILET" in t["upper_name"] and "7'8" in t["clean_name"]):
            group_key = "MASTER_TOILET"
        elif "C. TOI" in t["upper_name"] or ("TOILET" in t["upper_name"] and "4'0" in t["clean_name"]):
            group_key = "COMMON_TOILET"
        elif "BALCONY" in t["upper_name"]:
            group_key = "BALCONY"
        elif "ENTRY" in t["upper_name"]:
            group_key = "ENTRANCE"
        else:
            group_key = "ROOM"
        semantic_groups[group_key].append(t)

    print("\n==================================================")
    print("STEP 2: SEMANTIC GROUPING & RANKED ASSIGNMENT")
    print("==================================================")
    print(f"Unique Semantic Groups: {list(semantic_groups.keys())}")

    assigned_rooms = {} # room_id -> semantic_info
    unmapped_labels = []

    for group_key, callouts in semantic_groups.items():
        # Prefer callout with explicit declared dimensions
        best_callout = max(callouts, key=lambda c: len(c["declared_dims"]))
        
        # Rank meaningful room candidates for this callout
        candidates = []
        for r in meaningful_rooms:
            if r["room_id"] in assigned_rooms:
                continue
            r_poly = r["polygon"]
            c_pt = r_poly.centroid
            
            # Check all callout positions in group
            best_score = -999.0
            for c_obj in callouts:
                pt = Point(c_obj["pos"])
                is_inside = r_poly.contains(pt)
                dist_b = r_poly.distance(pt)
                dist_c = pt.distance(c_pt)
                
                score = 0.0
                if is_inside:
                    score += 100.0 - (dist_c * 0.05)
                elif dist_b < 50.0:
                    score += 50.0 - dist_b
                else:
                    score = -1.0
                if score > best_score:
                    best_score = score
                    
            if best_score > 0:
                candidates.append((best_score, r))
                
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        if candidates:
            best_score, best_room = candidates[0]
            assigned_rooms[best_room["room_id"]] = {
                "name": best_callout["clean_name"],
                "semantic_type": group_key,
                "declared_dimensions": best_callout["declared_dims"],
                "score": round(best_score, 1),
                "status": "CONFIRMED"
            }
            print(f"  Assigned '{group_key}' -> [{best_room['room_id']}] '{best_callout['clean_name']}' (Area {best_room['area']:.1f}, Score {best_score:.1f})")
        else:
            unmapped_labels.append(group_key)
            print(f"  UNMAPPED Group '{group_key}' (No plausible meaningful room candidate within range)")

    # Step 3: Door to Room Association (Host wall normal vector sampling)
    aperture_engine = ApertureEngine(doc, unit_to_meters=audit_data["scale_calibration"]["scale_value_to_meters"])
    doors, windows = aperture_engine.detect_and_host_apertures(planar_edges)

    edge_lookup = {e["edge_id"]: e for e in planar_edges}
    
    print("\n==================================================")
    print("STEP 3: APERTURE TO ROOM ASSOCIATION FORENSICS")
    print("==================================================")
    
    refined_doors = []
    door_pair_connections = []

    for d in doors:
        h_id = d["host_wall_id"]
        h_wall = edge_lookup.get(h_id)
        if not h_wall: continue
        
        w_line = h_wall["geometry"]
        p1, p2 = h_wall["p1"], h_wall["p2"]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 1e-3: continue
        
        # Normal vectors
        nx, ny = -dy / length, dx / length
        cx, cy = d["center"]
        
        # Sample left and right side points at offset delta = 15.0 units
        pt_left = Point(cx + nx * 15.0, cy + ny * 15.0)
        pt_right = Point(cx - nx * 15.0, cy - ny * 15.0)
        
        connected_spaces = []
        for side_pt in [pt_left, pt_right]:
            found_room = None
            for r in meaningful_rooms:
                if r["polygon"].contains(side_pt) or r["polygon"].distance(side_pt) < 5.0:
                    found_room = r["room_id"]
                    break
            connected_spaces.append(found_room if found_room else "EXTERIOR")

        # De-duplicate side assignments
        unique_connected = list(dict.fromkeys(connected_spaces))
        
        d_copy = dict(d)
        d_copy["connects"] = unique_connected
        refined_doors.append(d_copy)
        
        if len(unique_connected) == 2 and "EXTERIOR" not in unique_connected:
            door_pair_connections.append((unique_connected[0], unique_connected[1], d["opening_id"]))

        print(f"  Door '{d['opening_id']}' (Host '{h_id}') -> Connects: {unique_connected}")

    # Summary Report
    print("\n==================================================")
    print("FINAL SUMMARY OF RECONSTRUCTED MODEL")
    print("==================================================")
    print(f"Meaningful room candidates: {len(meaningful_rooms)}")
    print(f"Semantic rooms: {len(assigned_rooms)}")
    print(f"Unmapped labels: {len(unmapped_labels)} ({unmapped_labels})")
    print(f"Merged candidates: 0")
    print(f"Door connections: {len(door_pair_connections)}")
    print(f"Window connections: {len(windows)}")
    print(f"Synthetic rooms created from text: 0")

if __name__ == "__main__":
    test_semantics()
