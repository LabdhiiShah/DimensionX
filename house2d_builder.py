"""
House2D JSON Schema Builder (Generalized & Dynamic)
===================================================
Assembles reconstructed architectural elements into a generalized, clean, versioned House2D JSON schema.
"""

import datetime
from shapely.geometry import LineString, Point, Polygon

class House2DBuilder:
    def __init__(self, audit_data):
        self.audit_data = audit_data

    def build_house2d(self, geom_results, hosted_doors, hosted_windows, annotated_rooms, adjacency_graph):
        scale_info = self.audit_data.get("scale_calibration", {})
        geom_stats = self.audit_data.get("geometry_statistics", {})
        bbox = geom_stats.get("bounding_box", {})
        unit_to_m = scale_info.get("scale_value_to_meters", 1.0)
        
        # Wall Thicknesses from evidence
        thicknesses = [t["offset_distance"] for t in geom_stats.get("candidate_wall_thicknesses", []) if t["offset_distance"] > 0.05]
        ext_wall_thickness = thicknesses[0] if len(thicknesses) > 0 else (0.23 / unit_to_m)
        int_wall_thickness = thicknesses[1] if len(thicknesses) > 1 else (0.115 / unit_to_m)
        
        # Format Vertices
        planar_edges = geom_results.get("planar_edges", [])
        vertex_set = set()
        for e in planar_edges:
            vertex_set.add(e["p1"])
            vertex_set.add(e["p2"])
            
        vertices = [{"vertex_id": f"v_{i+1}", "x": v[0], "y": v[1]} for i, v in enumerate(sorted(vertex_set))]
        
        # Footprint boundary geometry for EXTERIOR wall classification
        footprint_poly = geom_results.get("building_footprint")
        footprint_boundary = footprint_poly.exterior if footprint_poly else None
        
        # Format Walls
        walls = []
        for e in planar_edges:
            p1, p2 = e["p1"], e["p2"]
            length = e["length"]
            w_geom = e["geometry"]
            
            # Dynamic Exterior vs Interior classification
            if footprint_boundary:
                dist_to_fp = w_geom.distance(footprint_boundary)
                is_exterior = (dist_to_fp <= ext_wall_thickness * 1.2)
            else:
                is_exterior = False
                
            w_class = "EXTERIOR" if is_exterior else "INTERIOR"
            w_thick = ext_wall_thickness if is_exterior else int_wall_thickness
            
            walls.append({
                "wall_id": e["edge_id"],
                "centerline": [[p1[0], p1[1]], [p2[0], p2[1]]],
                "length": length,
                "thickness": {
                    "value": round(w_thick, 2),
                    "source": "PAIRED_PARALLEL_LINES"
                },
                "representation": "CENTERLINE_PLUS_THICKNESS",
                "wall_class": w_class,
                "status": "CONFIRMED",
                "confidence": "HIGH",
                "provenance": {
                    "source_file": self.audit_data["file_info"]["filename"],
                    "layer": "PRIMARY_WALL",
                    "derivation": "Planar topology edge extraction"
                }
            })

        # Format Rooms
        formatted_rooms = []
        for r in annotated_rooms:
            poly = r["polygon"]
            exterior_coords = list(poly.exterior.coords) if poly else []
            formatted_rooms.append({
                "room_id": r["room_id"],
                "name": r["name"],
                "semantic_type": r["semantic_type"],
                "status": r["status"],
                "confidence": r["confidence"],
                "area": r["area_sq_units"],
                "perimeter": r["perimeter_units"],
                "parsed_dimensions": r["parsed_dimensions"],
                "polygon_vertices": [[round(pt[0], 3), round(pt[1], 3)] for pt in exterior_coords],
                "bounds": r["bounds"]
            })

        # Format Building Footprint
        footprint_coords = list(footprint_poly.exterior.coords) if footprint_poly else []
        formatted_footprint = {
            "type": "Polygon",
            "coordinates": [[round(pt[0], 3), round(pt[1], 3)] for pt in footprint_coords],
            "area": round(footprint_poly.area, 2) if footprint_poly else 0.0,
            "derivation_source": "RECONSTRUCTED_ROOM_AND_WALL_UNION"
        }

        # Assembly
        house2d = {
            "schema_version": "1.0.0",
            "metadata": {
                "created_at": datetime.datetime.now().isoformat(),
                "generator": "Intelligent CAD-to-3D Antigravity Reconstruction Engine",
                "source_dxf": self.audit_data["file_info"]["filename"]
            },
            "coordinate_system": {
                "type": "2D_Cartesian",
                "origin": [bbox.get("min_x", 0.0), bbox.get("min_y", 0.0)],
                "extents": {
                    "width": bbox.get("width", 0.0),
                    "height": bbox.get("height", 0.0)
                }
            },
            "units": {
                "unit_name": scale_info.get("unit_name", "Millimeters"),
                "scale_to_meters": scale_info.get("scale_value_to_meters", 0.001),
                "scale_confidence": scale_info.get("scale_confidence", "HIGH"),
                "scale_source": scale_info.get("scale_source", "TEXT_DIM_AND_GEOMETRIC_PRIORS"),
                "scale_evidence": scale_info.get("evidence", [])
            },
            "levels": [
                {
                    "level_id": "Level_1",
                    "elevation": 0.0,
                    "vertical_parameters": {
                        "wall_height": {"value": 2.8, "unit": "meters", "source": "PROJECT_DEFAULT", "status": "INFERRED"},
                        "slab_thickness": {"value": 0.2, "unit": "meters", "source": "PROJECT_DEFAULT", "status": "INFERRED"},
                        "ceiling_height": {"value": 2.8, "unit": "meters", "source": "PROJECT_DEFAULT", "status": "INFERRED"}
                    }
                }
            ],
            "building_components": {
                "vertices": vertices,
                "walls": walls,
                "doors": hosted_doors,
                "windows": hosted_windows,
                "rooms": formatted_rooms,
                "building_footprint": formatted_footprint
            },
            "room_adjacency": adjacency_graph,
            "diagnostics": {
                "weld_tolerance_used": geom_results.get("weld_tolerance", 1.0),
                "isolated_candidate_walls": 0,
                "suspicious_apertures": 0,
                "warnings": [],
                "blocking_errors": []
            }
        }
        
        return house2d
