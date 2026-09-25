"""
House2D-Lite Builder Module (Generalized & Scale-Aware)
======================================================
Converts 2D architectural reconstruction into a normalized [0,1] x [0,1] global coordinate frame.
Generates clean House2D-lite JSON for procedural 3D generation in Unity.
"""

import datetime
from shapely.geometry import Polygon, Point

class House2DLiteBuilder:
    def __init__(self, audit_data):
        self.audit_data = audit_data

    def build_house2d_lite(self, geom_results, hosted_doors, hosted_windows, annotated_rooms, adjacency_graph):
        scale_info = self.audit_data.get("scale_calibration", {})
        geom_stats = self.audit_data.get("geometry_statistics", {})
        bbox = geom_stats.get("bounding_box", {})
        unit_to_m = scale_info.get("scale_value_to_meters", 1.0)
        
        min_x = bbox.get("min_x", 0.0)
        max_x = bbox.get("max_x", 1.0)
        min_y = bbox.get("min_y", 0.0)
        max_y = bbox.get("max_y", 1.0)
        
        span_x = max(max_x - min_x, 1e-3)
        span_y = max(max_y - min_y, 1e-3)
        max_span = max(span_x, span_y)
        
        def norm_pt(p):
            nx = round((p[0] - min_x) / max_span, 4)
            ny = round((p[1] - min_y) / max_span, 4)
            return [nx, ny]

        # 1. House Metadata & Footprint Category
        footprint_poly = geom_results.get("building_footprint")
        footprint_coords = [norm_pt(pt) for pt in list(footprint_poly.exterior.coords)] if footprint_poly else []
        footprint_boundary = footprint_poly.exterior if footprint_poly else None
        
        # Categorize Footprint Shape
        shape_category = "IRREGULAR"
        if footprint_poly:
            rect_area = span_x * span_y
            fp_area = footprint_poly.area
            ratio = fp_area / rect_area if rect_area > 0 else 0
            if ratio > 0.85:
                shape_category = "RECTANGULAR"
            elif ratio > 0.60:
                shape_category = "L_SHAPED"

        # Wall Thicknesses from evidence
        thicknesses = [t["offset_distance"] for t in geom_stats.get("candidate_wall_thicknesses", []) if t["offset_distance"] > 0.05]
        ext_wall_thickness = thicknesses[0] if len(thicknesses) > 0 else (0.23 / unit_to_m)
        int_wall_thickness = thicknesses[1] if len(thicknesses) > 1 else (0.115 / unit_to_m)

        # 2. Normalized Walls
        planar_edges = geom_results.get("planar_edges", [])
        walls = []
        wall_lookup = {}
        for e in planar_edges:
            p1_n = norm_pt(e["p1"])
            p2_n = norm_pt(e["p2"])
            length_n = round(e["length"] / max_span, 4)
            w_geom = e["geometry"]
            
            if footprint_boundary:
                dist_to_fp = w_geom.distance(footprint_boundary)
                is_exterior = (dist_to_fp <= ext_wall_thickness * 1.2)
            else:
                is_exterior = False
                
            w_class = "EXTERIOR" if is_exterior else "INTERIOR"
            raw_thick = ext_wall_thickness if is_exterior else int_wall_thickness
            norm_thick = round(raw_thick / max_span, 4)
            
            wall_obj = {
                "id": e["edge_id"],
                "class": w_class,
                "normalized_centerline": [p1_n, p2_n],
                "length_normalized": length_n,
                "thickness_normalized": max(norm_thick, 0.005),
                "status": "CONFIRMED",
                "confidence": 0.95
            }
            walls.append(wall_obj)
            wall_lookup[e["edge_id"]] = (e["p1"], e["p2"], e["geometry"])

        # 3. Normalized Rooms
        rooms = []
        room_poly_map = {}
        for r in annotated_rooms:
            poly = r["polygon"]
            room_poly_map[r["room_id"]] = poly
            ext_n = [norm_pt(pt) for pt in list(poly.exterior.coords)] if poly else []
            r_bounds = r["bounds"] # minx, miny, maxx, maxy
            
            w_n = round((r_bounds[2] - r_bounds[0]) / max_span, 4)
            h_n = round((r_bounds[3] - r_bounds[1]) / max_span, 4)
            cx_n = round(((r_bounds[0] + r_bounds[2]) / 2.0 - min_x) / max_span, 4)
            cy_n = round(((r_bounds[1] + r_bounds[3]) / 2.0 - min_y) / max_span, 4)
            
            rooms.append({
                "id": r["room_id"],
                "name": r["name"],
                "type": r["semantic_type"],
                "position": [cx_n, cy_n],
                "size": [w_n, h_n],
                "shape": "POLYGON",
                "normalized_polygon": ext_n,
                "area_normalized": round(poly.area / (max_span**2), 4) if poly else 0.0,
                "confidence": 0.90 if r["status"] == "CONFIRMED" else 0.50,
                "parsed_dimensions": r["parsed_dimensions"]
            })

        # 4. Normalized Openings (Doors & Windows)
        openings = []
        all_apertures = [(d, "DOOR") for d in hosted_doors] + [(w, "WINDOW") for w in hosted_windows]
        
        probe_dist = 1.0 / unit_to_m
        for ap, ap_type in all_apertures:
            h_wall_id = ap["host_wall_id"]
            center_n = norm_pt(ap["center"])
            w_norm = round(ap["width"] / max_span, 4)
            
            # Find connected rooms
            connected_rooms = []
            ap_pt = Point(ap["center"])
            for r_id, r_poly in room_poly_map.items():
                if r_poly.distance(ap_pt) <= probe_dist:
                    connected_rooms.append(r_id)

            openings.append({
                "id": ap["opening_id"],
                "type": ap_type,
                "host_wall": h_wall_id,
                "position_t": 0.5, # mid-wall segment position
                "normalized_center": center_n,
                "width_normalized": w_norm,
                "connects": connected_rooms[:2],
                "swing": ap.get("swing", "UNKNOWN"),
                "confidence": 0.90 if ap["confidence"] == "HIGH" else 0.70
            })

        # 5. Normalized Connections
        connections = []
        for adj in adjacency_graph.get("adjacent_pairs", []):
            connections.append({
                "from": adj["room_a"],
                "to": adj["room_b"],
                "connection": "ADJACENT",
                "via_opening": None
            })
            
        for conn in adjacency_graph.get("connected_pairs", []):
            connections.append({
                "from": conn["room_a"],
                "to": conn["room_b"],
                "connection": "DOOR",
                "via_opening": conn.get("via_aperture")
            })

        # Calculate house real-world estimated scale
        scale_val = round(span_x * unit_to_m, 2)
        if scale_val < 3.0 or scale_val > 500.0:
            scale_val = 15.0 # fallback default real-world house span in meters

        house2d_lite = {
            "schema_version": "1.0-lite",
            "metadata": {
                "created_at": datetime.datetime.now().isoformat(),
                "generator": "Intelligent CAD-to-3D Antigravity Reconstruction Engine",
                "source_dxf": self.audit_data["file_info"]["filename"]
            },
            "house": {
                "coordinate_system": "NORMALIZED_2D",
                "aspect_ratio": round(span_x / span_y, 3),
                "global_bounding_box": {
                    "min_x": min_x, "max_x": max_x,
                    "min_y": min_y, "max_y": max_y
                },
                "scale": {
                    "value": scale_val,
                    "unit": "meters",
                    "source": scale_info.get("scale_source", "APPROXIMATE_PROJECT_SCALE"),
                    "confidence": scale_info.get("scale_confidence", "HIGH")
                },
                "footprint": {
                    "shape_category": shape_category,
                    "normalized_polygon": footprint_coords,
                    "area_normalized": round(footprint_poly.area / (max_span**2), 4) if footprint_poly else 0.0
                }
            },
            "walls": walls,
            "rooms": rooms,
            "openings": openings,
            "connections": connections,
            "diagnostics": {
                "weld_tolerance_used": geom_results.get("weld_tolerance", 0.25),
                "isolated_candidate_walls": 0,
                "warnings": [],
                "blocking_errors": []
            }
        }
        
        return house2d_lite
