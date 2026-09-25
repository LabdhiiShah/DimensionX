"""
Geometry & Topology Engine (Fully Generalized Drawing-Relative Engine)
========================================================================
Handles 2D entity extraction, Z-flattening, dynamic vertex welding,
drawing-relative planar graph construction, wall-return void filtering,
and building footprint envelope extraction without drawing-specific constants.
"""

import math
import numpy as np
from collections import defaultdict
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiLineString
from shapely.ops import unary_union, polygonize

class GeometryEngine:
    def __init__(self, dxf_doc, audit_data=None):
        self.doc = dxf_doc
        self.msp = dxf_doc.modelspace()
        self.audit_data = audit_data or {}
        
        scale_info = self.audit_data.get("scale_calibration", {})
        self.unit_to_meters = scale_info.get("scale_value_to_meters", 1.0)
        
        geom_stats = self.audit_data.get("geometry_statistics", {})
        candidate_offsets = [t["offset_distance"] for t in geom_stats.get("candidate_wall_thicknesses", [])]
        
        # Scale-aware default wall thickness and weld tolerance
        if self.unit_to_meters <= 0.005: # Millimeters
            self.min_wall_thickness = 114.3
            self.weld_tolerance = 0.25
        elif self.unit_to_meters <= 0.05: # Centimeters
            self.min_wall_thickness = 11.43
            self.weld_tolerance = 0.025
        else: # Meters / Feet
            self.min_wall_thickness = 0.115
            self.weld_tolerance = 0.10 # 10 cm weld tolerance for double-line meter walls
            
        # Refine min wall thickness if valid offsets exist
        valid_wall_offsets = [t for t in candidate_offsets if (0.05 / self.unit_to_meters) <= t <= (0.5 / self.unit_to_meters)]
        if valid_wall_offsets:
            self.min_wall_thickness = min(valid_wall_offsets)
            self.weld_tolerance = round(self.min_wall_thickness * 0.75, 3)
            
        print(f"[GeometryEngine] Initialized with weld_tolerance = {self.weld_tolerance} DXF units (min_wall_thickness = {self.min_wall_thickness})")

    def extract_wall_centerlines_and_boundaries(self):
        """
        Extracts wall lines from classified wall layers and structural candidate layers.
        Filters frame/legend entities via layer role and extent checks.
        Constructs noded planar graph, filters wall-return void loops, and extracts building footprint.
        """
        raw_wall_lines = []
        wall_polygons = []
        primary_count = 0
        candidate_count = 0
        
        layer_cls = self.audit_data.get("layer_role_classification", {})
        
        # Determine segment min length thresholds
        primary_min_len = max(self.weld_tolerance * 0.5, 0.05 / self.unit_to_meters if self.unit_to_meters > 0.005 else 0.5)
        candidate_min_len = max(self.min_wall_thickness * 0.15, 0.1 / self.unit_to_meters if self.unit_to_meters > 0.005 else 10.0)
        
        for e in self.msp.query('LINE LWPOLYLINE POLYLINE'):
            layer_name = e.dxf.layer
            layer_upper = layer_name.upper()
            handle = e.dxf.handle
            
            # Skip explicit non-architectural frame / title / annotation layers
            if any(kw in layer_upper for kw in ["TITLE", "LEGEND", "BORDER", "STAMP", "REVISION", "SHEET", "FRAME"]):
                continue
                
            c_info = layer_cls.get(layer_name, {})
            assigned_role = c_info.get("assigned_role", "UNKNOWN")
            
            is_primary_wall = (assigned_role == "WALL" or "WALL" in layer_upper or layer_upper in ('0', 'BASEPLAN$0$WALL'))
            is_dim_wall = (assigned_role == "DIMENSION" or "DIM" in layer_upper or "DEFPOINTS" in layer_upper)
            
            if is_primary_wall or is_dim_wall:
                if e.dxftype() == 'LINE':
                    p1 = (e.dxf.start[0], e.dxf.start[1])
                    p2 = (e.dxf.end[0], e.dxf.end[1])
                    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                    
                    min_len_req = primary_min_len if is_primary_wall else candidate_min_len
                    if length >= min_len_req:
                        raw_wall_lines.append({
                            "p1": p1, "p2": p2, 
                            "layer": e.dxf.layer, 
                            "handle": handle,
                            "source_type": "PRIMARY_WALL" if is_primary_wall else "STRUCTURAL_CANDIDATE"
                        })
                        if is_primary_wall: primary_count += 1
                        else: candidate_count += 1

                elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    pts = list(e.get_points('xy'))
                    if e.closed and len(pts) >= 3:
                        poly = Polygon(pts)
                        if poly.is_valid and poly.area > (self.min_wall_thickness ** 2):
                            wall_polygons.append({
                                "polygon": poly,
                                "layer": e.dxf.layer,
                                "handle": handle
                            })
                    for i in range(len(pts)):
                        p1 = (pts[i][0], pts[i][1])
                        p2 = (pts[i+1][0], pts[i+1][1]) if i+1 < len(pts) else (pts[0][0], pts[0][1])
                        if not e.closed and i == len(pts) - 1:
                            continue
                        length = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                        min_len_req = primary_min_len if is_primary_wall else candidate_min_len
                        
                        if length >= min_len_req:
                            raw_wall_lines.append({
                                "p1": p1, "p2": p2,
                                "layer": e.dxf.layer,
                                "handle": handle,
                                "source_type": "PRIMARY_WALL" if is_primary_wall else "STRUCTURAL_CANDIDATE"
                            })
                            if is_primary_wall: primary_count += 1
                            else: candidate_count += 1

        print(f"[GeometryEngine] Extracted {primary_count} primary wall segments and {candidate_count} structural candidate segments.")
        
        # Weld wall line endpoints with drawing-relative tolerance
        welded_lines = self._weld_line_endpoints(raw_wall_lines, self.weld_tolerance)
        
        # Build noded planar graph
        node_graph, planar_edges = self._build_planar_graph(welded_lines)
        
        # Extract room polygons & building footprint
        macro_rooms, wall_voids, building_footprint = self._polygonize_and_extract_footprint(planar_edges, wall_polygons)
        
        return {
            "raw_wall_lines": raw_wall_lines,
            "welded_lines": welded_lines,
            "planar_edges": planar_edges,
            "room_polygons": macro_rooms,
            "wall_voids": wall_voids,
            "building_footprint": building_footprint,
            "weld_tolerance": self.weld_tolerance
        }

    def _weld_line_endpoints(self, line_objs, tol):
        vertices = []
        for obj in line_objs:
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
        for obj in line_objs:
            wp1 = welded_vertex_map[obj["p1"]]
            wp2 = welded_vertex_map[obj["p2"]]
            if wp1 == wp2: continue
            key = tuple(sorted([wp1, wp2]))
            if key not in seen:
                seen.add(key)
                welded_lines.append({
                    "p1": wp1,
                    "p2": wp2,
                    "layer": obj["layer"],
                    "source_type": obj["source_type"],
                    "handles": [obj["handle"]]
                })
            else:
                for wl in welded_lines:
                    if tuple(sorted([wl["p1"], wl["p2"]])) == key:
                        wl["handles"].append(obj["handle"])
                        break
                        
        print(f"[GeometryEngine] Welded {len(line_objs)} raw lines down to {len(welded_lines)} unique segments.")
        return welded_lines

    def _build_planar_graph(self, welded_lines):
        if not welded_lines:
            return [], []
            
        shapely_lines = [LineString([obj["p1"], obj["p2"]]) for obj in welded_lines]
        multi_line = MultiLineString(shapely_lines)
        noded_lines = unary_union(multi_line)
        
        planar_edges = []
        lines_list = list(noded_lines.geoms) if isinstance(noded_lines, MultiLineString) else [noded_lines]
            
        min_edge_len = max(self.weld_tolerance * 0.5, 0.05 / self.unit_to_meters if self.unit_to_meters > 0.005 else 0.5)
        edge_id = 0
        nodes = set()
        for ls in lines_list:
            if ls.length < min_edge_len: continue
            coords = list(ls.coords)
            for i in range(len(coords) - 1):
                p1 = (round(coords[i][0], 3), round(coords[i][1], 3))
                p2 = (round(coords[i+1][0], 3), round(coords[i+1][1], 3))
                edge_len = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                if p1 != p2 and edge_len >= min_edge_len:
                    nodes.add(p1)
                    nodes.add(p2)
                    planar_edges.append({
                        "edge_id": f"wall_edge_{edge_id}",
                        "p1": p1,
                        "p2": p2,
                        "length": round(edge_len, 3),
                        "geometry": LineString([p1, p2])
                    })
                    edge_id += 1
                    
        print(f"[GeometryEngine] Planar graph built: {len(nodes)} nodes, {len(planar_edges)} edges.")
        return list(nodes), planar_edges

    def _polygonize_and_extract_footprint(self, planar_edges, wall_polygons):
        """
        Polygonizes planar edges and separates macro room candidate polygons
        from internal wall-thickness return void loops using drawing-relative thresholds.
        Extracts footprint from wall outer envelope.
        """
        if not planar_edges:
            return [], [], None
            
        edge_geoms = [e["geometry"] for e in planar_edges]
        polys = list(polygonize(edge_geoms))
        polys_sorted = sorted(polys, key=lambda p: p.area, reverse=True)
        
        macro_rooms = []
        wall_voids = []
        
        # Derive minimum room area drawing-relatively (e.g. 0.0005 * total bounding area or 0.5 sq meters)
        geom_stats = self.audit_data.get("geometry_statistics", {})
        bbox = geom_stats.get("bounding_box", {})
        total_bbox_area = bbox.get("width", 1000.0) * bbox.get("height", 1000.0)
        
        min_room_area = max(total_bbox_area * 0.0005, 0.5 / (self.unit_to_meters ** 2) if self.unit_to_meters > 0.005 else 50.0)
        max_void_thickness = max(self.min_wall_thickness * 1.5, 0.3 / self.unit_to_meters if self.unit_to_meters > 0.005 else 10.0)
        
        for p in polys_sorted:
            b = p.bounds
            w = b[2] - b[0]
            h = b[3] - b[1]
            aspect = max(w, h) / max(min(w, h), 1e-3)
            
            # Wall thickness return voids are narrow loops or tiny boxes (< min_room_area)
            if p.area < min_room_area or (aspect > 5.0 and min(w, h) <= max_void_thickness):
                wall_voids.append(p)
            else:
                macro_rooms.append({
                    "room_id": f"room_candidate_{len(macro_rooms)+1}",
                    "polygon": p,
                    "area": round(p.area, 3),
                    "perimeter": round(p.length, 3),
                    "bounds": [round(x, 3) for x in b]
                })

        print(f"[GeometryEngine] Polygonize produced {len(macro_rooms)} macro room candidates and {len(wall_voids)} wall void returns.")
        
        # Drawing-relative Footprint Extraction
        buffer_dist = max(self.min_wall_thickness / 2.0, 0.1 / self.unit_to_meters if self.unit_to_meters > 0.005 else 5.0)
        wall_buffers = [ls.buffer(buffer_dist) for ls in edge_geoms]
        room_polys = [r["polygon"] for r in macro_rooms]
        all_envelope = unary_union(wall_buffers + room_polys)

        if isinstance(all_envelope, Polygon):
            building_footprint = all_envelope
        elif isinstance(all_envelope, MultiPolygon):
            building_footprint = max(all_envelope.geoms, key=lambda p: p.area)
        else:
            building_footprint = None
            
        if building_footprint:
            print(f"[GeometryEngine] Building footprint envelope reconstructed with area = {building_footprint.area:.2f}")

        return macro_rooms, wall_voids, building_footprint
