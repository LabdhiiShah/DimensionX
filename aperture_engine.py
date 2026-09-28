"""
Aperture Detection & Hosting Engine (Generalized & Scale-Aware)
================================================================
Detects doors and windows from geometry (arcs, parallel line sets, block inserts).
Hosts apertures parametrically onto nearest wall centerlines and determines connected spaces using scale-aware evidence.
"""

import os
import math
from collections import defaultdict
from shapely.geometry import Point, LineString

class ApertureEngine:
    def __init__(self, dxf_doc, unit_to_meters=1.0, layer_classifications=None):
        self.doc = dxf_doc
        self.msp = dxf_doc.modelspace()
        self.unit_to_meters = unit_to_meters if unit_to_meters > 0 else 1.0
        self.layer_classifications = layer_classifications or {}
        self._reject_reasons = {}   # layer_name -> reason string

    def _reject_log(self, layer_name, reason):
        self._reject_reasons[layer_name] = reason

    def _calc_layer_fragment_ratio(self, layer_name):
        min_len = min(0.5 / self.unit_to_meters, 0.5)
        total_segs = 0
        short_segs = 0
        for e in self.msp:
            if getattr(e.dxf, 'layer', '') == layer_name:
                if e.dxftype() == 'LINE':
                    p1 = (e.dxf.start[0], e.dxf.start[1])
                    p2 = (e.dxf.end[0], e.dxf.end[1])
                    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                    total_segs += 1
                    if length < min_len:
                        short_segs += 1
                elif e.dxftype() == 'LWPOLYLINE':
                    pts = list(e.get_points('xy'))
                    for i in range(len(pts) - 1):
                        length = math.hypot(pts[i+1][0] - pts[i][0], pts[i+1][1] - pts[i][1])
                        total_segs += 1
                        if length < min_len:
                            short_segs += 1
        return (short_segs / float(total_segs)) if total_segs > 0 else 0.0

    def detect_and_host_apertures(self, wall_edges, room_polygons=None):
        """
        Detects doors and windows, and hosts them onto wall centerlines/edges.
        """
        doors = self._detect_doors()
        windows = self._detect_windows()
        
        print(f"[ApertureEngine] Detected {len(doors)} doors, {len(windows)} windows (pre-host).")
        
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
                if any(kw in layer_u for kw in ['WALL', 'DOOR', 'DR_', '_DR', 'OPENING']):
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

    def _is_window_layer(self, layer_name):
        c_info = self.layer_classifications.get(layer_name, {})
        roles = c_info.get("candidate_roles", [])
        top_role = roles[0]["role"] if roles else (c_info.get("top_role") or c_info.get("assigned_role"))
        top_conf = roles[0]["confidence"] if roles else (1.0 if c_info.get("confidence") == "HIGH" else (0.5 if c_info.get("confidence") == "MEDIUM" else 0.0))

        fragment_ratio = c_info.get("fragment_ratio")
        if fragment_ratio is None:
            fragment_ratio = self._calc_layer_fragment_ratio(layer_name)

        conflict = c_info.get("conflict", False)

        # Primary: use classifier role, but require confidence + sanity gates
        if top_role == "WINDOW":
            if top_conf < 0.5:
                self._reject_log(layer_name, f"WINDOW role but confidence {top_conf:.2f} < 0.5")
                return False
            if fragment_ratio > 0.5:
                self._reject_log(layer_name, f"WINDOW role but fragment_ratio {fragment_ratio:.3f} > 0.5")
                return False
            if conflict:
                self._reject_log(layer_name, "WINDOW role but classifier reports conflict")
                return False
            return True

        # Fallback: name-based
        layer_u = layer_name.upper()
        is_electrical = any(kw in layer_u for kw in
            ['ELECTRICAL', 'WIRING', 'LIGHTING', 'POWER', 'ELE_', '_ELE', 'EL_', '_EL'])
        if is_electrical:
            self._reject_log(layer_name, "electrical layer keyword")
            return False
        if any(kw in layer_u for kw in ['WIN', 'GLAS', 'GLAZ']):
            return True
        self._reject_log(layer_name, "not window role / keyword")
        return False

    def _merge_parallel_window_lines(self, win_lines):
        """
        Merge collinear, parallel, close-together window frame lines into one cluster.
        Each cluster = one physical window.
        """
        clusters = []
        used = [False] * len(win_lines)
        max_perp = max(0.5 / self.unit_to_meters, 0.5)

        for i, (p1_i, p2_i, layer_i) in enumerate(win_lines):
            if used[i]:
                continue
            group = [(p1_i, p2_i, layer_i)]
            used[i] = True

            angle_i = math.degrees(math.atan2(p2_i[1]-p1_i[1], p2_i[0]-p1_i[0])) % 180
            length_i = math.hypot(p2_i[0]-p1_i[0], p2_i[1]-p1_i[1])

            for j in range(i + 1, len(win_lines)):
                if used[j]:
                    continue
                p1_j, p2_j, layer_j = win_lines[j]
                if layer_j != layer_i:
                    continue

                angle_j = math.degrees(math.atan2(p2_j[1]-p1_j[1], p2_j[0]-p1_j[0])) % 180
                angle_diff = abs(angle_i - angle_j) % 180
                angle_diff = min(angle_diff, 180 - angle_diff)
                if angle_diff > 5.0:
                    continue

                # Perpendicular offset from line i to midpoint of line j
                mx = (p1_j[0] + p2_j[0]) / 2.0
                my = (p1_j[1] + p2_j[1]) / 2.0
                dx = (p2_i[0] - p1_i[0]) / max(length_i, 1e-6)
                dy = (p2_i[1] - p1_i[1]) / max(length_i, 1e-6)
                # Vector from p1_i to midpoint
                vx, vy = mx - p1_i[0], my - p1_i[1]
                # Perpendicular distance = cross product magnitude
                perp_dist = abs(vx * dy - vy * dx)
                if perp_dist > max_perp:
                    continue

                # Projection overlap along line i
                t1_j = (p1_j[0] - p1_i[0]) * dx + (p1_j[1] - p1_i[1]) * dy
                t2_j = (p2_j[0] - p1_i[0]) * dx + (p2_j[1] - p1_i[1]) * dy
                t_min = min(t1_j, t2_j)
                t_max = max(t1_j, t2_j)
                if t_max < -0.1 or t_min > length_i + 0.1:
                    continue

                group.append((p1_j, p2_j, layer_j))
                used[j] = True

            clusters.append(group)

        return clusters

    def _detect_windows(self):
        windows = []
        win_id = 1
        
        win_lines = []
        min_win_len = min(0.2 / self.unit_to_meters, 0.1)
        
        layer_counts = defaultdict(int)
        layer_decisions = {}
        
        all_entities = list(self.msp.query('LINE LWPOLYLINE'))
        print(f"[ApertureEngine] Scanning {len(all_entities)} LINE/LWPOLYLINE entities for window geometry...")
        
        for e in all_entities:
            layer = e.dxf.layer
            layer_counts[layer] += 1
            if layer not in layer_decisions:
                layer_decisions[layer] = self._is_window_layer(layer)
                
            if layer_decisions[layer]:
                if e.dxftype() == 'LINE':
                    p1 = (e.dxf.start[0], e.dxf.start[1])
                    p2 = (e.dxf.end[0], e.dxf.end[1])
                    win_lines.append((p1, p2, layer))
                elif e.dxftype() == 'LWPOLYLINE':
                    pts = list(e.get_points('xy'))
                    for i in range(len(pts) - 1):
                        win_lines.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1]), layer))
                        
        print("[ApertureEngine] Layer Scanning Diagnostics:")
        sorted_layers = sorted(layer_counts.items(), key=lambda x: x[1], reverse=True)
        for layer, count in sorted_layers[:10]:
            is_win = layer_decisions[layer]
            status = "ACCEPTED" if is_win else "REJECTED"
            reason = self._reject_reasons.get(layer, "")
            reason_str = f" ({reason})" if reason else ""
            print(f"  - Layer '{layer}': {count} entities -> {status}{reason_str}")

        # Cluster parallel, close-together window lines
        clusters = self._merge_parallel_window_lines(win_lines)

        layer_raw_counts = defaultdict(int)
        for _, _, l_name in win_lines:
            layer_raw_counts[l_name] += 1

        layer_merged_counts = defaultdict(int)
        for cluster in clusters:
            if cluster:
                layer_merged_counts[cluster[0][2]] += 1

        for lname in layer_raw_counts:
            raw_c = layer_raw_counts[lname]
            merged_c = layer_merged_counts[lname]
            print(f"[ApertureEngine] WIN {lname}: {raw_c} raw lines -> {merged_c} merged windows")

        for cluster in clusters:
            all_points = []
            for p1, p2, _ in cluster:
                all_points.extend([p1, p2])
            xs = [p[0] for p in all_points]
            ys = [p[1] for p in all_points]
            cx = (min(xs) + max(xs)) / 2.0
            cy = (min(ys) + max(ys)) / 2.0
            span = max(max(xs) - min(xs), max(ys) - min(ys))
            if span >= min_win_len:
                windows.append({
                    "id": f"window_{win_id}",
                    "source": "WINDOW_LAYER_GEOMETRY",
                    "center": (cx, cy),
                    "width": round(span, 2),
                    "layer": cluster[0][2],
                    "confidence": "HIGH"
                })
                win_id += 1
                
        return windows

    def _host_apertures_on_walls(self, aperture_candidates, wall_edges, room_polygons=None, aperture_type="DOOR"):
        hosted = []
        if not wall_edges:
            return hosted
            
        max_host_dist = 1.0 / self.unit_to_meters # Max 1.0 meter from wall centerline
        probe_dist_base = max(0.4 / self.unit_to_meters, 0.4 / self.unit_to_meters)
        
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

                    probe_distances_m = [0.25, 0.4, 0.6, 0.8, 1.2, 1.5]
                    best_spaces = ["EXTERIOR", "EXTERIOR"]
                    best_score = -1
                    best_pt_l, best_pt_r = Point(cx, cy), Point(cx, cy)
                    best_p_dist = 0.4 / self.unit_to_meters

                    for p_dist_m in probe_distances_m:
                        p_dist = p_dist_m / self.unit_to_meters
                        pt_l = Point(cx + nx * p_dist, cy + ny * p_dist)
                        pt_r = Point(cx - nx * p_dist, cy - ny * p_dist)
                        dist_tol = max(p_dist * 0.75, 0.5 / self.unit_to_meters)

                        spaces = []
                        for sample_pt in [pt_l, pt_r]:
                            found = None
                            min_r_dist = float('inf')
                            for r in room_polygons:
                                r_poly = r["polygon"]
                                if r_poly.contains(sample_pt):
                                    found = r["room_id"]
                                    break
                                d = r_poly.distance(sample_pt)
                                if d < dist_tol and d < min_r_dist:
                                    min_r_dist = d
                                    found = r["room_id"]
                            spaces.append(found if found else "EXTERIOR")

                        non_ext = [s for s in spaces if s != "EXTERIOR"]
                        score = len(set(non_ext))
                        if score > best_score:
                            best_score = score
                            best_spaces = spaces
                            best_pt_l, best_pt_r = pt_l, pt_r
                            best_p_dist = p_dist
                            if score == 2:
                                break
                        elif score == best_score and len(non_ext) > len([s for s in best_spaces if s != "EXTERIOR"]):
                            best_spaces = spaces
                            best_pt_l, best_pt_r = pt_l, pt_r
                            best_p_dist = p_dist

                    connected_spaces = best_spaces
                    pt_left, pt_right = best_pt_l, best_pt_r
                    probe_dist_base = best_p_dist

                    if os.environ.get("APERTURE_DEBUG"):
                        unique_sp = list(dict.fromkeys(connected_spaces)) if connected_spaces else ["EXTERIOR"]
                        print(f"[ApertureEngine] {ap['id']} ({aperture_type}):")
                        print(f"  center = {ap['center']}")
                        print(f"  host_wall = {best_wall.get('edge_id')}, p1={best_wall.get('p1')}, p2={best_wall.get('p2')}")
                        print(f"  wall_length = {w_length:.3f}")
                        print(f"  probe_dist = {probe_dist_base:.3f}")
                        print(f"  probe_left = ({pt_left.x:.3f}, {pt_left.y:.3f})")
                        print(f"  probe_right = ({pt_right.x:.3f}, {pt_right.y:.3f})")
                        print(f"  rooms_containing_left = {[r['room_id'] for r in (room_polygons or []) if r['polygon'].contains(pt_left)]}")
                        print(f"  rooms_containing_right = {[r['room_id'] for r in (room_polygons or []) if r['polygon'].contains(pt_right)]}")
                        print(f"  connects = {unique_sp}")

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
