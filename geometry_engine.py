"""
Geometry & Topology Engine (Parallel Line Pair Detection Architecture)
========================================================================
Extracts walls using geometry-first parallel-line pair detection across standard architectural floor plans.
"""

import math
from collections import defaultdict, Counter
from shapely.geometry import LineString, Point, Polygon, MultiPolygon
from shapely.ops import unary_union, polygonize

class GeometryEngine:
    def __init__(self, dxf_doc, audit_data=None):
        self.doc = dxf_doc
        self.msp = dxf_doc.modelspace()
        self.audit_data = audit_data or {}
        
        scale_info = self.audit_data.get("scale_calibration", {})
        self.unit_to_meters = scale_info.get("scale_value_to_meters", 1.0)
        
        tol_bundle = self.audit_data.get("tolerance_bundle", {})
        wt_stats = tol_bundle.get("wall_thickness_stats", {})
        med_entry = wt_stats.get("median", {})
        med_wt = med_entry.get("value") if isinstance(med_entry, dict) else med_entry
        
        if med_wt and med_wt > 0:
            self.min_wall_thickness = float(med_wt)
        else:
            if self.unit_to_meters <= 0.005:    # Millimeters
                self.min_wall_thickness = 114.3
            elif self.unit_to_meters <= 0.015:  # Centimeters
                self.min_wall_thickness = 11.43
            elif self.unit_to_meters <= 0.035:  # Inches (unit_to_meters ~ 0.0254)
                self.min_wall_thickness = 4.7
            elif self.unit_to_meters <= 0.4:    # Feet
                self.min_wall_thickness = 0.5
            else:                               # Meters
                self.min_wall_thickness = 0.115

        self.weld_tolerance = round(self.min_wall_thickness * 0.1, 3)
        print(f"[GeometryEngine] Init: min_wall_thickness={self.min_wall_thickness}, weld_tolerance={self.weld_tolerance}")

    def extract_wall_centerlines_and_boundaries(self):
        # Stage 1: Read all line segments from non-junk layers
        segments = self._read_all_line_segments()
        
        # Stage 2: Find parallel line pairs
        pairs = self._find_parallel_pairs(segments)
        
        # Stage 3: Convert pairs to walls
        walls = self._pairs_to_walls(pairs)
        
        # Stage 4: Merge collinear chains
        merged_walls = self._merge_collinear_chains(walls)
        
        # Stage 5: Filter walls (layer frequency & connectivity)
        filtered_walls = self._filter_walls(merged_walls)
        
        # Format planar edges for downstream engines (House2DBuilder, ApertureEngine, Visualizer2D)
        planar_edges = []
        for idx, w in enumerate(filtered_walls):
            p1, p2 = w["p1"], w["p2"]
            length = w["length"]
            edge_id = w.get("wall_id", f"wall_edge_{idx}")
            planar_edges.append({
                "edge_id": edge_id,
                "wall_id": edge_id,
                "p1": p1,
                "p2": p2,
                "length": round(length, 3),
                "thickness": round(w.get("thickness", self.min_wall_thickness), 3),
                "source_layer": w.get("source_layer", "WALL"),
                "layer": w.get("source_layer", "WALL"),
                "geometry": LineString([p1, p2]),
                "source_handles": w.get("source_handles", [])
            })
            
        # Stage 6: Polygonize rooms & extract building footprint
        macro_rooms, wall_voids, footprint = self._polygonize_and_extract_footprint(planar_edges, filtered_walls, raw_segments=segments)

        print(f"[GeometryEngine] Pipeline complete: {len(segments)} segments -> {len(pairs)} pairs -> {len(filtered_walls)} walls -> {len(macro_rooms)} rooms")

        return {
            "raw_wall_lines": segments,
            "welded_lines": pairs,
            "planar_edges": planar_edges,
            "unmerged_planar_edges": planar_edges,
            "room_polygons": macro_rooms,
            "wall_voids": wall_voids,
            "building_footprint": footprint,
            "weld_tolerance": self.weld_tolerance
        }

    def _read_all_line_segments(self):
        segments = []
        min_len = self.weld_tolerance * 0.5
        junk_kws = ["TITLE", "LEGEND", "BORDER", "STAMP", "REVISION", "SHEET", "FRAME", 
                    "SCALE", "DIM", "DEFPOINTS", "HATCH", "FURNITURE", "FURINTURE", "ELE", "TREE"]

        for e in self.msp.query('LINE LWPOLYLINE POLYLINE'):
            layer = e.dxf.layer
            layer_u = layer.upper()
            handle = e.dxf.handle
            
            if any(kw in layer_u for kw in junk_kws):
                continue

            if e.dxftype() == 'LINE':
                p1 = (e.dxf.start[0], e.dxf.start[1])
                p2 = (e.dxf.end[0], e.dxf.end[1])
                length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if length >= min_len:
                    segments.append({'p1': p1, 'p2': p2, 'layer': layer, 'handle': handle, 'length': length})
            elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                pts = list(e.get_points('xy'))
                closed = e.closed
                n = len(pts)
                for i in range(n if closed else n - 1):
                    p1 = (pts[i][0], pts[i][1])
                    p2 = (pts[(i+1)%n][0], pts[(i+1)%n][1])
                    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                    if length >= min_len:
                        segments.append({'p1': p1, 'p2': p2, 'layer': layer, 'handle': handle, 'length': length})

        return segments

    def _find_parallel_pairs(self, segments):
        max_thickness = max(self.min_wall_thickness * 2.5, 0.35 / self.unit_to_meters if self.unit_to_meters > 0 else 12.0)
        grid_size = max_thickness * 2.0
        
        grid = defaultdict(list)
        for idx, s in enumerate(segments):
            mx = (s['p1'][0] + s['p2'][0]) / 2.0
            my = (s['p1'][1] + s['p2'][1]) / 2.0
            gx, gy = int(math.floor(mx / grid_size)), int(math.floor(my / grid_size))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    grid[(gx + dx, gy + dy)].append(idx)

        pairs = []
        seen = set()

        def angle_of(s):
            return math.atan2(s['p2'][1] - s['p1'][1], s['p2'][0] - s['p1'][0])

        def angle_diff(a1, a2):
            d = abs(a1 - a2) % math.pi
            return min(d, math.pi - d)

        min_len_req = self.min_wall_thickness * 0.4

        for i, s1 in enumerate(segments):
            if s1['length'] < min_len_req:
                continue
            mx = (s1['p1'][0] + s1['p2'][0]) / 2.0
            my = (s1['p1'][1] + s1['p2'][1]) / 2.0
            gx, gy = int(math.floor(mx / grid_size)), int(math.floor(my / grid_size))

            for j in grid[(gx, gy)]:
                if j <= i or (i, j) in seen:
                    continue
                seen.add((i, j))

                s2 = segments[j]
                if s1['handle'] == s2['handle'] or s2['length'] < min_len_req:
                    continue

                a1, a2 = angle_of(s1), angle_of(s2)
                if angle_diff(a1, a2) > 0.052: # 3 degrees
                    continue

                dx = (s1['p2'][0] - s1['p1'][0]) / s1['length']
                dy = (s1['p2'][1] - s1['p1'][1]) / s1['length']
                mx2 = (s2['p1'][0] + s2['p2'][0]) / 2.0
                my2 = (s2['p1'][1] + s2['p2'][1]) / 2.0
                vx, vy = mx2 - s1['p1'][0], my2 - s1['p1'][1]
                perp = abs(vx * dy - vy * dx)

                if perp < self.min_wall_thickness * 0.4 or perp > max_thickness:
                    continue

                t1 = (s2['p1'][0] - s1['p1'][0]) * dx + (s2['p1'][1] - s1['p1'][1]) * dy
                t2 = (s2['p2'][0] - s1['p1'][0]) * dx + (s2['p2'][1] - s1['p1'][1]) * dy
                t_min, t_max = min(t1, t2), max(t1, t2)
                overlap = max(0.0, min(s1['length'], t_max) - max(0.0, t_min))

                shorter = min(s1['length'], s2['length'])
                if shorter < 1e-6 or (overlap / shorter) < 0.4:
                    continue

                o_start = max(0.0, t_min)
                o_end = min(s1['length'], t_max)
                cp1 = (s1['p1'][0] + o_start * dx, s1['p1'][1] + o_start * dy)
                cp2 = (s1['p1'][0] + o_end * dx, s1['p1'][1] + o_end * dy)

                pairs.append({
                    'p1': cp1, 'p2': cp2,
                    'thickness': perp,
                    'length': o_end - o_start,
                    'layer_1': s1['layer'], 'layer_2': s2['layer'],
                    'handle_1': s1['handle'], 'handle_2': s2['handle']
                })

        return pairs

    def _pairs_to_walls(self, pairs):
        walls = []
        for i, pair in enumerate(pairs):
            layers = [pair['layer_1'], pair['layer_2']]
            w_layers = [l for l in layers if 'WALL' in l.upper()]
            source_layer = w_layers[0] if w_layers else layers[0]
            walls.append({
                'wall_id': f'wall_{i}',
                'p1': pair['p1'],
                'p2': pair['p2'],
                'length': pair['length'],
                'thickness': pair['thickness'],
                'source_layer': source_layer,
                'source_layers': layers,
                'source_handles': [pair['handle_1'], pair['handle_2']],
                'merge_count': 1,
            })
        return walls

    def _merge_collinear_chains(self, walls):
        if not walls:
            return []
            
        gap_tol = self.min_wall_thickness * 1.5
        angle_tol = 0.087 # ~5 deg

        def close(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1]) <= gap_tol

        def angle_of(w):
            return math.atan2(w['p2'][1] - w['p1'][1], w['p2'][0] - w['p1'][0])

        def angle_diff(a1, a2):
            d = abs(a1 - a2) % math.pi
            return min(d, math.pi - d)

        used = [False] * len(walls)
        merged = []

        for i, wall in enumerate(walls):
            if used[i]:
                continue
            chain = [wall]
            used[i] = True

            grew = True
            iterations = 0
            while grew and iterations < 50:
                grew = False
                iterations += 1
                head, tail = chain[0], chain[-1]

                for j, other in enumerate(walls):
                    if used[j]:
                        continue

                    if close(other['p1'], tail['p2']) and angle_diff(angle_of(tail), angle_of(other)) < angle_tol:
                        chain.append(other)
                        used[j] = True
                        grew = True
                        break

                    if close(other['p2'], head['p1']) and angle_diff(angle_of(head), angle_of(other)) < angle_tol:
                        rev = dict(other)
                        rev['p1'], rev['p2'] = other['p2'], other['p1']
                        chain.insert(0, rev)
                        used[j] = True
                        grew = True
                        break

            p1 = chain[0]['p1']
            p2 = chain[-1]['p2']
            length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            avg_thick = sum(c['thickness'] for c in chain) / len(chain)
            
            merged.append({
                'wall_id': f"{wall['wall_id']}_chain",
                'p1': p1, 'p2': p2,
                'length': length,
                'thickness': avg_thick,
                'source_layer': wall['source_layer'],
                'source_layers': sum([c.get('source_layers', []) for c in chain], []),
                'source_handles': sum([c.get('source_handles', []) for c in chain], []),
                'merge_count': len(chain),
            })

        return merged

    def _filter_walls(self, walls):
        if not walls:
            return []

        # 5A: Layer frequency filter
        counts = Counter(w['source_layer'] for w in walls)
        total = len(walls)
        min_count = max(3, int(total * 0.15))
        evidence_layers = {layer for layer, c in counts.items() if c >= min_count}
        if not evidence_layers:
            evidence_layers = set(counts.keys())

        walls_a = [w for w in walls if w['source_layer'] in evidence_layers]
        if len(walls_a) <= 1:
            return walls_a

        # 5B: Connectivity / isolated wall filter
        max_thickness = max(self.min_wall_thickness * 2.5, 0.35 / self.unit_to_meters if self.unit_to_meters > 0 else 12.0)
        node_tol = max_thickness * 1.5
        
        connected = []
        for i, w1 in enumerate(walls_a):
            has_nbr = False
            p1_1, p1_2 = w1['p1'], w1['p2']
            for j, w2 in enumerate(walls_a):
                if i == j: continue
                p2_1, p2_2 = w2['p1'], w2['p2']
                if min(math.hypot(p1_1[0]-p2_1[0], p1_1[1]-p2_1[1]),
                       math.hypot(p1_1[0]-p2_2[0], p1_1[1]-p2_2[1]),
                       math.hypot(p1_2[0]-p2_1[0], p1_2[1]-p2_1[1]),
                       math.hypot(p1_2[0]-p2_2[0], p1_2[1]-p2_2[1])) <= node_tol:
                    has_nbr = True
                    break
            if has_nbr:
                connected.append(w1)

        return connected if connected else walls_a

    def _polygonize_and_extract_footprint(self, planar_edges, filtered_walls=None, raw_segments=None):
        if not planar_edges:
            return [], [], None

        edge_geoms = [e["geometry"] for e in planar_edges]

        # Boundary lines for room extraction
        boundary_lines = []
        if raw_segments:
            for s in raw_segments:
                boundary_lines.append(LineString([s["p1"], s["p2"]]))
        else:
            boundary_lines = list(edge_geoms)

        # Include door/window aperture lines from DXF if present
        aperture_lines = []
        for e in self.msp.query('LINE LWPOLYLINE POLYLINE'):
            layer = e.dxf.layer.upper()
            if any(kw in layer for kw in ['WIN', 'DOOR', 'DR', 'OPEN']):
                if e.dxftype() == 'LINE':
                    aperture_lines.append(LineString([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])]))
                elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    pts = list(e.get_points('xy'))
                    for i in range(len(pts)-1):
                        aperture_lines.append(LineString([(pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])]))

        # Directional door gap bridging along collinear wall segments
        bridges = []
        max_gap = 1.3 / self.unit_to_meters if self.unit_to_meters > 0 else 52.0
        
        segments_for_bridge = raw_segments if raw_segments else [
            {'p1': e['p1'], 'p2': e['p2'], 'length': e['length']} for e in planar_edges
        ]

        def angle_of(s):
            return math.atan2(s['p2'][1] - s['p1'][1], s['p2'][0] - s['p1'][0])

        def angle_diff(a1, a2):
            d = abs(a1 - a2) % math.pi
            return min(d, math.pi - d)

        for i, s1 in enumerate(segments_for_bridge):
            p1a, p1b = s1['p1'], s1['p2']
            len1 = s1.get('length', math.hypot(p1b[0]-p1a[0], p1b[1]-p1a[1]))
            if len1 < 1e-5: continue
            u1 = ((p1b[0]-p1a[0])/len1, (p1b[1]-p1a[1])/len1)

            for j in range(i+1, len(segments_for_bridge)):
                s2 = segments_for_bridge[j]
                p2a, p2b = s2['p1'], s2['p2']
                len2 = s2.get('length', math.hypot(p2b[0]-p2a[0], p2b[1]-p2a[1]))
                if len2 < 1e-5: continue
                u2 = ((p2b[0]-p2a[0])/len2, (p2b[1]-p2a[1])/len2)

                if angle_diff(angle_of(s1), angle_of(s2)) < 0.10:
                    for ep1 in (p1a, p1b):
                        for ep2 in (p2a, p2b):
                            d = math.hypot(ep1[0]-ep2[0], ep1[1]-ep2[1])
                            if self.min_wall_thickness * 0.8 <= d <= max_gap:
                                dv = ((ep2[0]-ep1[0])/d, (ep2[1]-ep1[1])/d)
                                if abs(dv[0]*u1[0] + dv[1]*u1[1]) > 0.90:
                                    bridges.append(LineString([ep1, ep2]))

        all_geoms = boundary_lines + aperture_lines + bridges
        noded = unary_union(all_geoms)
        polys = list(polygonize(noded))
        polys_sorted = sorted(polys, key=lambda p: p.area, reverse=True)

        min_room_area = 2.0 / (self.unit_to_meters ** 2) if self.unit_to_meters > 0 else 50.0
        max_room_area = 60.0 / (self.unit_to_meters ** 2) if self.unit_to_meters > 0 else 500000.0

        macro_rooms = []
        wall_voids = []

        for p in polys_sorted:
            if min_room_area <= p.area <= max_room_area and len(p.interiors) == 0:
                b = p.bounds
                macro_rooms.append({
                    "room_id": f"room_candidate_{len(macro_rooms)+1}",
                    "polygon": p,
                    "area": round(p.area, 3),
                    "perimeter": round(p.length, 3),
                    "bounds": [round(x, 3) for x in b]
                })
            else:
                wall_voids.append(p)

        # Fallback to planar_edges polygonize if no rooms extracted from boundary lines
        if not macro_rooms:
            planar_noded = unary_union(edge_geoms + bridges)
            planar_polys = list(polygonize(planar_noded))
            for p in sorted(planar_polys, key=lambda p: p.area, reverse=True):
                if min_room_area <= p.area <= max_room_area:
                    b = p.bounds
                    macro_rooms.append({
                        "room_id": f"room_candidate_{len(macro_rooms)+1}",
                        "polygon": p,
                        "area": round(p.area, 3),
                        "perimeter": round(p.length, 3),
                        "bounds": [round(x, 3) for x in b]
                    })
                else:
                    wall_voids.append(p)

        # Footprint envelope
        buffer_dist = max(self.min_wall_thickness, 0.2 / self.unit_to_meters if self.unit_to_meters > 0 else 10.0)
        wall_buffers = [ls.buffer(buffer_dist) for ls in edge_geoms]
        room_polys = [r["polygon"] for r in macro_rooms]
        all_envelope = unary_union(wall_buffers + room_polys)

        if isinstance(all_envelope, Polygon):
            building_footprint = all_envelope
        elif isinstance(all_envelope, MultiPolygon):
            building_footprint = max(all_envelope.geoms, key=lambda p: p.area)
        else:
            building_footprint = None

        return macro_rooms, wall_voids, building_footprint
