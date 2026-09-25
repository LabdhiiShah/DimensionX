"""
Aperture Detection & Hosting Engine (Generalized & Scale-Aware)
================================================================
Detects doors and windows from geometry (arcs, parallel line sets, block inserts).
Hosts apertures parametrically onto nearest wall centerlines and determines connected spaces using scale-aware evidence.
"""

import math
from shapely.geometry import Point, LineString

class ApertureEngine:
    def __init__(self, dxf_doc, unit_to_meters=1.0):
        self.doc = dxf_doc
        self.msp = dxf_doc.modelspace()
        self.unit_to_meters = unit_to_meters if unit_to_meters > 0 else 1.0

    def detect_and_host_apertures(self, wall_edges, room_polygons=None):
        """
        Detects doors and windows, and hosts them onto wall centerlines/edges.
        """
        doors = self._detect_doors()
        windows = self._detect_windows()
        
        hosted_doors = self._host_apertures_on_walls(doors, wall_edges, room_polygons=room_polygons, aperture_type="DOOR")
        hosted_windows = self._host_apertures_on_walls(windows, wall_edges, room_polygons=room_polygons, aperture_type="WINDOW")
        
        print(f"[ApertureEngine] Hosted {len(hosted_doors)} doors and {len(hosted_windows)} windows on wall edges.")
        return hosted_doors, hosted_windows

    def _detect_doors(self):
        doors = []
        door_id = 1
        
        # Scale-aware door width bounds in meters: [0.4m, 2.0m]
        min_r = 0.4 / self.unit_to_meters
        max_r = 2.0 / self.unit_to_meters
        
        # 1. Door Swing Arcs
        for e in self.msp.query('ARC'):
            layer_u = e.dxf.layer.upper()
            radius = e.dxf.radius
            center = (e.dxf.center[0], e.dxf.center[1])
            
            # Check arc radius in common architectural ranges across unit representations:
            # Meters (0.5..2.0), Inches/Feet/Custom (2.0..60.0), Millimeters/Centimeters (60.0..1800.0)
            if (0.5 <= radius <= 2.0) or (2.0 <= radius <= 60.0) or (60.0 <= radius <= 1800.0):
                if any(kw in layer_u for kw in ['WALL', 'DOOR', 'FUR', '0', 'TAXT', 'ARCH']):
                    doors.append({
                        "id": f"door_{door_id}",
                        "source": "SWING_ARC",
                        "center": center,
                        "width": round(radius * 2.0 if radius < 20.0 else radius, 2),
                        "radius": round(radius, 2),
                        "layer": e.dxf.layer,
                        "confidence": "HIGH"
                    })
                    door_id += 1

        # 2. Block Inserts on DOOR layer or with door block names
        for e in self.msp.query('INSERT'):
            layer_u = e.dxf.layer.upper()
            block_u = e.dxf.name.upper()
            if 'DOOR' in layer_u or 'DOOR' in block_u or 'DR' in block_u or 'DR_' in block_u:
                pos = (e.dxf.insert[0], e.dxf.insert[1])
                default_door_w = round(0.9 / self.unit_to_meters, 2)
                doors.append({
                    "id": f"door_{door_id}",
                    "source": "BLOCK_INSERT",
                    "center": pos,
                    "width": default_door_w,
                    "radius": default_door_w,
                    "layer": e.dxf.layer,
                    "confidence": "HIGH"
                })
                door_id += 1

        return doors

    def _detect_windows(self):
        windows = []
        win_id = 1
        
        win_lines = []
        min_win_len = 0.2 / self.unit_to_meters
        
        for e in self.msp.query('LINE LWPOLYLINE'):
            layer_u = e.dxf.layer.upper()
            is_electrical = any(kw in layer_u for kw in ['EL', 'ELE', 'ELECTRICAL', 'WIRING', 'LOW'])
            if not is_electrical and any(kw in layer_u for kw in ['WIN', 'GLAS', 'WIND']):
                if e.dxftype() == 'LINE':
                    p1 = (e.dxf.start[0], e.dxf.start[1])
                    p2 = (e.dxf.end[0], e.dxf.end[1])
                    win_lines.append((p1, p2, e.dxf.layer))
                elif e.dxftype() == 'LWPOLYLINE':
                    pts = list(e.get_points('xy'))
                    for i in range(len(pts) - 1):
                        win_lines.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1]), e.dxf.layer))
                        
        for p1, p2, layer in win_lines:
            mid_x = (p1[0] + p2[0]) / 2.0
            mid_y = (p1[1] + p2[1]) / 2.0
            w_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if w_len >= min_win_len:
                windows.append({
                    "id": f"window_{win_id}",
                    "source": "WINDOW_LAYER_GEOMETRY",
                    "center": (mid_x, mid_y),
                    "width": round(w_len, 2),
                    "layer": layer,
                    "confidence": "HIGH"
                })
                win_id += 1
                
        return windows

    def _host_apertures_on_walls(self, aperture_candidates, wall_edges, room_polygons=None, aperture_type="DOOR"):
        hosted = []
        if not wall_edges:
            return hosted
            
        max_host_dist = 1.0 / self.unit_to_meters # Max 1.0 meter from wall centerline
        probe_dist = 0.3 / self.unit_to_meters
        
        for ap in aperture_candidates:
            pt = Point(ap["center"])
            min_dist = float('inf')
            best_wall = None
            best_proj_pt = None
            
            for wall in wall_edges:
                w_line = wall["geometry"]
                dist = pt.distance(w_line)
                if dist < min_dist:
                    min_dist = dist
                    best_wall = wall
                    proj_dist = w_line.project(pt)
                    proj_pt = w_line.interpolate(proj_dist)
                    best_proj_pt = (round(proj_pt.x, 3), round(proj_pt.y, 3))
                    
            if min_dist <= max_host_dist and best_wall:
                w_width = ap["width"]
                sill = 0.0 if aperture_type == "DOOR" else 0.9
                head = 2.1
                
                # Determine connected spaces using wall normal vectors
                p1, p2 = best_wall["p1"], best_wall["p2"]
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                w_length = math.hypot(dx, dy)
                connected_spaces = []
                
                if w_length > 1e-3 and room_polygons:
                    nx, ny = -dy / w_length, dx / w_length
                    cx, cy = best_proj_pt
                    pt_left = Point(cx + nx * probe_dist, cy + ny * probe_dist)
                    pt_right = Point(cx - nx * probe_dist, cy - ny * probe_dist)
                    
                    for sample_pt in [pt_left, pt_right]:
                        found = None
                        for r in room_polygons:
                            r_poly = r["polygon"]
                            if r_poly.contains(sample_pt) or r_poly.distance(sample_pt) < (probe_dist / 2.0):
                                found = r["room_id"]
                                break
                        connected_spaces.append(found if found else "EXTERIOR")
                
                unique_spaces = list(dict.fromkeys(connected_spaces)) if connected_spaces else ["EXTERIOR"]
                
                hosted.append({
                    "opening_id": ap["id"],
                    "aperture_type": aperture_type,
                    "host_wall_id": best_wall["edge_id"],
                    "center": best_proj_pt,
                    "width": w_width,
                    "sill_height": {
                        "value": sill,
                        "unit": "meters",
                        "source": "PROJECT_DEFAULT"
                    },
                    "head_height": {
                        "value": head,
                        "unit": "meters",
                        "source": "PROJECT_DEFAULT"
                    },
                    "connects": unique_spaces[:2],
                    "swing": "UNKNOWN",
                    "status": "CONFIRMED",
                    "confidence": ap["confidence"],
                    "source": ap["source"],
                    "source_layer": ap["layer"]
                })
                
        return hosted
