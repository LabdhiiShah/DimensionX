"""
DXF Auditor Module
==================
Performs a deep geometric, topological, structural, and semantic audit of DXF floor plans.
Outputs comprehensive json and markdown reports into output/ directory.
"""

import math
import json
import os
import re
from collections import defaultdict
import ezdxf
import numpy as np
from shapely.geometry import LineString, Point, Polygon, MultiLineString
from shapely.ops import unary_union

INSUNITS_MAP = {
    0: "Unspecified",
    1: "Inches",
    2: "Feet",
    3: "Miles",
    4: "Millimeters",
    5: "Centimeters",
    6: "Meters",
    7: "Kilometers",
    8: "Microinches",
    9: "Mils",
    10: "Yards",
    11: "Angstroms",
    12: "Nanometers",
    13: "Microns",
    14: "Decimeters",
    15: "Decameters",
    16: "Hectometers",
    17: "Gigameters",
    18: "Astronomical Units",
    19: "Lightyears",
    20: "Parsecs"
}

def parse_architectural_dim_text(text):
    """
    Parses strings like "9'3\" x 11'0\"" or "7'8\"" into inches or mm if present.
    Returns list of parsed dimensions in inches.
    """
    pattern = r"(\d+)'\s*(\d+(?:\.\d+)?)\"?"
    matches = re.findall(pattern, text)
    dims_inches = []
    for ft, inch in matches:
        val = float(ft) * 12.0 + float(inch)
        dims_inches.append(val)
    return dims_inches

def parse_metric_dim_text(text):
    """
    Parses strings like "0.15", "0.23", "1.65" or "\\A1;0.15".
    """
    clean_text = re.sub(r'\\A\d+;', '', text).strip()
    try:
        val = float(clean_text)
        if 0.05 <= val <= 50.0:
            return val
    except ValueError:
        pass
    return None

class DXFAuditor:
    def __init__(self, dxf_filepath):
        self.filepath = os.path.abspath(dxf_filepath)
        self.filename = os.path.basename(dxf_filepath)
        self.doc = ezdxf.readfile(self.filepath)
        self.msp = self.doc.modelspace()
        
    def run_audit(self):
        print(f"Auditing DXF file: {self.filepath}")
        
        # 1. Header Variables & Units
        header_info = self._audit_header()
        
        # 2. Layers & Colors
        layers_info = self._audit_layers()
        
        # 3. Entity Breakdown & Z-coordinates
        entity_info, z_info = self._audit_entities()
        
        # 4. Blocks & Nesting
        blocks_info = self._audit_blocks()
        
        # 5. Text & Annotations & Room Labels
        text_info, room_labels = self._audit_texts()
        
        # 6. Dimensions
        dim_info = self._audit_dimensions()
        
        # 7. Geometric Extents & Lines/Polylines
        geom_stats = self._audit_geometry()
        
        # 8. Scale & Calibration Analysis
        scale_info = self._calibrate_scale(header_info, dim_info, text_info, geom_stats)
        
        # 9. Layer/Role Classification Assessment
        classification_info = self._classify_layers(layers_info, entity_info)

        report_data = {
            "file_info": {
                "filepath": self.filepath,
                "filename": self.filename,
                "file_size_bytes": os.path.getsize(self.filepath)
            },
            "header": header_info,
            "layers": layers_info,
            "entities": entity_info,
            "z_coordinates": z_info,
            "blocks": blocks_info,
            "texts": text_info,
            "room_labels": room_labels,
            "dimensions": dim_info,
            "geometry_statistics": geom_stats,
            "scale_calibration": scale_info,
            "layer_role_classification": classification_info
        }
        
        return report_data

    def _audit_header(self):
        header = self.doc.header
        insunits_code = header.get("$INSUNITS", 0)
        insunits_desc = INSUNITS_MAP.get(insunits_code, f"Unknown ({insunits_code})")
        
        extmin = header.get("$EXTMIN", None)
        extmax = header.get("$EXTMAX", None)
        insbase = header.get("$INSBASE", (0, 0, 0))
        measurement = header.get("$MEASUREMENT", None)
        lunits = header.get("$LUNITS", None)
        
        return {
            "INSUNITS_code": insunits_code,
            "INSUNITS_description": insunits_desc,
            "INSBASE": list(insbase) if insbase else None,
            "EXTMIN": list(extmin) if extmin else None,
            "EXTMAX": list(extmax) if extmax else None,
            "MEASUREMENT": measurement,
            "LUNITS": lunits
        }

    def _audit_layers(self):
        layers = {}
        layer_entity_counts = defaultdict(int)
        for entity in self.msp:
            layer_entity_counts[entity.dxf.layer] += 1
            
        for layer in self.doc.layers:
            name = layer.dxf.name
            layers[name] = {
                "name": name,
                "color": layer.dxf.color,
                "is_locked": layer.is_locked(),
                "is_off": layer.is_off(),
                "is_frozen": layer.is_frozen(),
                "entity_count": layer_entity_counts.get(name, 0)
            }
        return layers

    def _audit_entities(self):
        entity_counts = defaultdict(int)
        entities_by_layer = defaultdict(lambda: defaultdict(int))
        total_count = 0
        
        non_zero_z_count = 0
        z_values = []
        
        for entity in self.msp:
            total_count += 1
            t = entity.dxftype()
            l = entity.dxf.layer
            entity_counts[t] += 1
            entities_by_layer[l][t] += 1
            
            # Extract Z coordinates
            ez = self._get_entity_z_values(entity)
            for z in ez:
                if abs(z) > 1e-4:
                    non_zero_z_count += 1
                z_values.append(z)
                
        z_stats = {
            "has_non_zero_z": non_zero_z_count > 0,
            "non_zero_z_entity_count": non_zero_z_count,
            "z_min": float(np.min(z_values)) if z_values else 0.0,
            "z_max": float(np.max(z_values)) if z_values else 0.0,
            "z_distinct_values": len(set(round(z, 2) for z in z_values)) if z_values else 0
        }
        
        entity_info = {
            "total_count": total_count,
            "by_type": dict(entity_counts),
            "by_layer_and_type": {k: dict(v) for k, v in entities_by_layer.items()}
        }
        
        return entity_info, z_stats

    def _get_entity_z_values(self, entity):
        zs = []
        t = entity.dxftype()
        if t == 'LINE':
            zs.append(entity.dxf.start[2])
            zs.append(entity.dxf.end[2])
        elif t in ('TEXT', 'MTEXT', 'INSERT'):
            zs.append(entity.dxf.insert[2])
        elif t == 'LWPOLYLINE':
            zs.append(entity.dxf.elevation)
        elif t in ('ARC', 'CIRCLE'):
            zs.append(entity.dxf.center[2])
        elif t == 'POLYLINE':
            zs.extend([v.dxf.location[2] for v in entity.vertices])
        return zs

    def _audit_blocks(self):
        block_defs = []
        user_blocks = 0
        anonymous_blocks = 0
        layout_blocks = 0
        
        insert_counts = defaultdict(int)
        for e in self.msp.query('INSERT'):
            insert_counts[e.dxf.name] += 1

        for block in self.doc.blocks:
            bname = block.name
            is_anon = bname.startswith('*')
            if is_anon:
                anonymous_blocks += 1
            else:
                user_blocks += 1
                
            block_defs.append({
                "name": bname,
                "is_anonymous": is_anon,
                "entity_count": len(block),
                "insert_count": insert_counts.get(bname, 0)
            })
            
        return {
            "total_block_definitions": len(self.doc.blocks),
            "user_block_count": user_blocks,
            "anonymous_block_count": anonymous_blocks,
            "block_list": block_defs
        }

    def _audit_texts(self):
        texts = []
        room_label_candidates = []
        room_keywords = ["BEDROOM", "BED", "KITCHEN", "LIVING", "LIV", "DINING", "DIN", 
                         "TOILET", "TOI", "BATH", "BALCONY", "ENTRY", "HALL", "PASSAGE", "DRAWING"]
        
        for e in self.msp.query('TEXT MTEXT'):
            is_mtext = (e.dxftype() == 'MTEXT')
            txt = e.text if is_mtext else e.dxf.text
            clean_txt = txt.strip()
            layer = e.dxf.layer
            pos = list(e.dxf.insert)
            
            # Check for room keywords
            upper_txt = clean_txt.upper()
            is_room = any(kw in upper_txt for kw in room_keywords)
            
            t_obj = {
                "type": e.dxftype(),
                "text": clean_txt,
                "layer": layer,
                "position": pos,
                "parsed_arch_dims": parse_architectural_dim_text(clean_txt),
                "parsed_metric_dim": parse_metric_dim_text(clean_txt)
            }
            texts.append(t_obj)
            if is_room:
                room_label_candidates.append(t_obj)
                
        return {
            "total_text_count": len(texts),
            "all_texts": texts
        }, room_label_candidates

    def _audit_dimensions(self):
        dims = []
        for e in self.msp.query('DIMENSION'):
            layer = e.dxf.layer
            text_override = getattr(e.dxf, 'text', '')
            actual_measurement = getattr(e.dxf, 'actual_measurement', None)
            dim_type = getattr(e.dxf, 'dimtype', None)
            dims.append({
                "layer": layer,
                "text_override": text_override,
                "actual_measurement": actual_measurement,
                "dim_type": dim_type
            })
        return {
            "dimension_entity_count": len(dims),
            "dimensions": dims
        }

    def _audit_geometry(self):
        lines = []
        for e in self.msp.query('LINE'):
            p1 = (e.dxf.start[0], e.dxf.start[1])
            p2 = (e.dxf.end[0], e.dxf.end[1])
            lines.append((p1, p2, e.dxf.layer, e.dxf.handle))
            
        for e in self.msp.query('LWPOLYLINE'):
            pts = list(e.get_points('xy'))
            for i in range(len(pts)):
                p1 = (pts[i][0], pts[i][1])
                p2 = (pts[i+1][0], pts[i+1][1]) if i+1 < len(pts) else (pts[0][0], pts[0][1])
                if not e.closed and i == len(pts) - 1:
                    continue
                lines.append((p1, p2, e.dxf.layer, e.dxf.handle))

        if not lines:
            return {"error": "No line geometry found"}

        # Calculate bounding box
        all_x = [p[0] for line in lines for p in (line[0], line[1])]
        all_y = [p[1] for line in lines for p in (line[0], line[1])]
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        width = max_x - min_x
        height = max_y - min_y

        # Line lengths
        lengths = []
        wall_lengths = []
        for p1, p2, layer, handle in lines:
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy)
            lengths.append(length)
            if 'WALL' in layer.upper():
                wall_lengths.append(length)

        # Parallel line offsets (candidate wall thicknesses)
        parallel_offsets = self._extract_parallel_offsets(lines, bbox_width=width, bbox_height=height)

        # Endpoint gaps analysis (closest un-welded endpoints)
        gap_stats = self._analyze_endpoint_gaps(lines)

        # Duplicate geometry
        duplicate_count = self._detect_duplicates(lines)

        return {
            "bounding_box": {
                "min_x": round(min_x, 3),
                "max_x": round(max_x, 3),
                "min_y": round(min_y, 3),
                "max_y": round(max_y, 3),
                "width": round(width, 3),
                "height": round(height, 3)
            },
            "total_segment_count": len(lines),
            "line_length_stats": {
                "min": round(min(lengths), 3) if lengths else 0,
                "max": round(max(lengths), 3) if lengths else 0,
                "mean": round(float(np.mean(lengths)), 3) if lengths else 0,
                "median": round(float(np.median(lengths)), 3) if lengths else 0
            },
            "wall_line_length_stats": {
                "count": len(wall_lengths),
                "min": round(min(wall_lengths), 3) if wall_lengths else 0,
                "max": round(max(wall_lengths), 3) if wall_lengths else 0,
                "mean": round(float(np.mean(wall_lengths)), 3) if wall_lengths else 0,
                "median": round(float(np.median(wall_lengths)), 3) if wall_lengths else 0
            },
            "candidate_wall_thicknesses": parallel_offsets,
            "endpoint_gap_stats": gap_stats,
            "duplicate_segment_count": duplicate_count
        }

    def _extract_parallel_offsets(self, lines, bbox_width=1000.0, bbox_height=1000.0):
        """Finds distances between parallel line segments (candidate wall thicknesses) scaled to drawing extents."""
        horizontals = []
        verticals = []
        drawing_span = max(bbox_width, bbox_height, 1.0)
        
        min_line_len = max(drawing_span * 0.002, 0.05)
        min_overlap = max(drawing_span * 0.005, 0.1)
        max_dist = max(drawing_span * 0.05, 1.0)
        
        for p1, p2, layer, handle in lines:
            dx = abs(p2[0] - p1[0])
            dy = abs(p2[1] - p1[1])
            length = math.hypot(dx, dy)
            if length < min_line_len:
                continue
            if dy < 1e-3: # Horizontal
                horizontals.append((min(p1[0], p2[0]), max(p1[0], p2[0]), p1[1]))
            elif dx < 1e-3: # Vertical
                verticals.append((min(p1[1], p2[1]), max(p1[1], p2[1]), p1[0]))

        offsets = defaultdict(int)
        
        # Check horizontal line pairs
        for i in range(len(horizontals)):
            x1_a, x2_a, y_a = horizontals[i]
            for j in range(i + 1, min(i + 150, len(horizontals))):
                x1_b, x2_b, y_b = horizontals[j]
                overlap = min(x2_a, x2_b) - max(x1_a, x1_b)
                if overlap >= min_overlap:
                    dist = abs(y_a - y_b)
                    if 0.01 <= dist <= max_dist:
                        offsets[round(dist, 1)] += 1

        # Check vertical line pairs
        for i in range(len(verticals)):
            y1_a, y2_a, x_a = verticals[i]
            for j in range(i + 1, min(i + 150, len(verticals))):
                y1_b, y2_b, x_b = verticals[j]
                overlap = min(y1_a, y2_b) - max(y1_a, y1_b)
                if overlap >= min_overlap:
                    dist = abs(x_a - x_b)
                    if 0.01 <= dist <= max_dist:
                        offsets[round(dist, 1)] += 1

        sorted_offsets = sorted(offsets.items(), key=lambda x: x[1], reverse=True)
        return [{"offset_distance": k, "frequency": v} for k, v in sorted_offsets[:10]]

    def _analyze_endpoint_gaps(self, lines):
        endpoints = []
        for p1, p2, layer, handle in lines:
            endpoints.append(p1)
            endpoints.append(p2)
            
        gaps = []
        # Sample subset for speed if large
        pts = endpoints[::2] if len(endpoints) > 1000 else endpoints
        for i in range(len(pts)):
            p_a = pts[i]
            for j in range(i + 1, min(i + 50, len(pts))):
                p_b = pts[j]
                d = math.hypot(p_b[0] - p_a[0], p_b[1] - p_a[1])
                if 0.001 < d < 100.0:
                    gaps.append(d)
                    
        return {
            "sample_gaps_count": len(gaps),
            "min_gap": round(min(gaps), 3) if gaps else 0,
            "max_gap": round(max(gaps), 3) if gaps else 0,
            "median_gap": round(float(np.median(gaps)), 3) if gaps else 0,
            "percentile_10": round(float(np.percentile(gaps, 10)), 3) if gaps else 0
        }

    def _detect_duplicates(self, lines):
        seen = set()
        duplicates = 0
        for p1, p2, layer, handle in lines:
            # Normalize line key
            sp1 = (round(p1[0], 2), round(p1[1], 2))
            sp2 = (round(p2[0], 2), round(p2[1], 2))
            key = tuple(sorted([sp1, sp2]))
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
        return duplicates

    def _calibrate_scale(self, header_info, dim_info, text_info, geom_stats):
        """
        Determines units and scale dynamically based on evidence hierarchy:
        1. Dimension callouts in TEXT/MTEXT matched against drawing extent scale
        2. Extent scale priors (e.g. 10,000+ DXF units indicates mm, 10-100 indicates meters)
        3. Wall thickness parallel offsets
        4. $INSUNITS header variable
        """
        evidence = []
        scale_source = "UNRESOLVED"
        scale_confidence = "LOW"
        unit_name = "Millimeters"
        to_meters_factor = 0.001

        bbox = geom_stats.get("bounding_box", {})
        width = bbox.get("width", 0)
        height = bbox.get("height", 0)
        max_span = max(width, height)
        max_coord = max(abs(bbox.get("max_x", 0)), abs(bbox.get("max_y", 0)))

        # Check Text measurement strings (e.g. 9'3" x 11'0" or 0.15)
        texts = text_info.get("all_texts", [])
        arch_dims_found = []
        metric_dims_found = []
        for t in texts:
            if t["parsed_arch_dims"]:
                arch_dims_found.extend(t["parsed_arch_dims"])
            if t["parsed_metric_dim"] is not None:
                metric_dims_found.append(t["parsed_metric_dim"])

        thicknesses = [o["offset_distance"] for o in geom_stats.get("candidate_wall_thicknesses", [])]

        # 1. $INSUNITS header check if explicitly non-zero
        insunits_code = header_info.get("INSUNITS_code", 0)
        if insunits_code in (4, 5, 6, 1, 2):
            if insunits_code == 4:
                unit_name, to_meters_factor = "Millimeters", 0.001
            elif insunits_code == 5:
                unit_name, to_meters_factor = "Centimeters", 0.01
            elif insunits_code == 6:
                unit_name, to_meters_factor = "Meters", 1.0
            elif insunits_code == 1:
                unit_name, to_meters_factor = "Inches", 0.0254
            elif insunits_code == 2:
                unit_name, to_meters_factor = "Feet", 0.3048
            scale_source = "$INSUNITS_HEADER"
            scale_confidence = "HIGH"
            evidence.append(f"Header $INSUNITS explicitly specifies {unit_name} (code {insunits_code}).")

        # 2. Evidence from Text dimensions and Drawing Extents
        elif arch_dims_found or max_span > 1000.0 or max_coord > 5000.0:
            if any(100 <= t <= 350 for t in thicknesses) or max_span > 2000.0 or max_coord > 5000.0:
                unit_name = "Millimeters"
                to_meters_factor = 0.001
                scale_source = "EXTENT_SPAN_AND_WALL_OFFSETS"
                scale_confidence = "HIGH"
                evidence.append(f"Drawing extent span ({max_span:.1f}) and coordinates indicate MILLIMETERS.")
            elif any(10 <= t <= 35 for t in thicknesses) or (200.0 <= max_span <= 2000.0):
                unit_name = "Centimeters"
                to_meters_factor = 0.01
                scale_source = "EXTENT_SPAN_AND_WALL_OFFSETS"
                scale_confidence = "HIGH"
                evidence.append(f"Drawing extent span ({max_span:.1f}) indicates CENTIMETERS.")
            else:
                unit_name = "Millimeters"
                to_meters_factor = 0.001
                scale_source = "EXTENT_SPAN_FALLBACK"
                scale_confidence = "MEDIUM"
                evidence.append("High coordinate values indicate MILLIMETERS.")

        elif metric_dims_found or max_span < 200.0:
            unit_name = "Meters"
            to_meters_factor = 1.0
            scale_source = "METRIC_EXTENT_SPAN"
            scale_confidence = "HIGH"
            evidence.append(f"Drawing extent span ({max_span:.1f}) indicates METERS.")

        return {
            "scale_value_to_meters": to_meters_factor,
            "unit_name": unit_name,
            "scale_source": scale_source,
            "scale_confidence": scale_confidence,
            "evidence": evidence
        }

    def _classify_layers(self, layers_info, entity_info):
        classifications = {}
        for name, ldata in layers_info.items():
            uname = name.upper()
            role = "UNKNOWN"
            confidence = "MEDIUM"
            
            if "WALL" in uname:
                role = "WALL"
                confidence = "HIGH"
            elif "DOOR" in uname:
                role = "DOOR"
                confidence = "HIGH"
            elif "WIN" in uname:
                role = "WINDOW"
                confidence = "HIGH"
            elif "DIM" in uname:
                role = "DIMENSION"
                confidence = "HIGH"
            elif "TEXT" in uname or "TAXT" in uname or "BLDGTEXT" in uname:
                role = "ROOM_LABEL / ANNOTATION"
                confidence = "HIGH"
            elif "FUR" in uname:
                role = "FURNITURE"
                confidence = "HIGH"
            elif "ELE" in uname or "ELC" in uname:
                role = "ELECTRICAL / ANNOTATION"
                confidence = "MEDIUM"
            elif "HATCH" in uname:
                role = "SURFACE_HATCH"
                confidence = "HIGH"
            elif "BEAM" in uname or "COL" in uname:
                role = "STRUCTURAL"
                confidence = "HIGH"
                
            classifications[name] = {
                "assigned_role": role,
                "confidence": confidence,
                "entity_count": ldata["entity_count"]
            }
        return classifications

def generate_markdown_report(data, md_filepath):
    f_info = data["file_info"]
    hdr = data["header"]
    layers = data["layers"]
    ents = data["entities"]
    z_coords = data["z_coordinates"]
    blocks = data["blocks"]
    texts = data["texts"]
    rooms = data["room_labels"]
    dims = data["dimensions"]
    geom = data["geometry_statistics"]
    scale = data["scale_calibration"]
    cls = data["layer_role_classification"]

    md = []
    md.append(f"# DXF Audit Report: {f_info['filename']}\n")
    md.append(f"- **File Path**: `{f_info['filepath']}`")
    md.append(f"- **File Size**: `{f_info['file_size_bytes']} bytes`")
    md.append(f"- **Total Entities**: `{ents['total_count']}`\n")
    
    md.append("## 1. Header Variables & Units Calibration")
    md.append(f"- **$INSUNITS**: `{hdr['INSUNITS_code']}` ({hdr['INSUNITS_description']})")
    md.append(f"- **$EXTMIN**: `{hdr['EXTMIN']}`")
    md.append(f"- **$EXTMAX**: `{hdr['EXTMAX']}`")
    md.append(f"- **$MEASUREMENT**: `{hdr['MEASUREMENT']}`")
    md.append(f"- **$LUNITS**: `{hdr['LUNITS']}`")
    md.append(f"- **Calibrated Units**: `{scale['unit_name']}`")
    md.append(f"- **To-Meters Factor**: `{scale['scale_value_to_meters']}`")
    md.append(f"- **Scale Confidence**: `{scale['scale_confidence']}` (Source: `{scale['scale_source']}`)\n")
    md.append("### Scale Evidence:")
    for ev in scale["evidence"]:
        md.append(f"- {ev}")
    md.append("")

    md.append("## 2. Drawing Extents & Geometry Statistics")
    bbox = geom.get("bounding_box", {})
    md.append(f"- **Extents Width x Height**: `{bbox.get('width')} x {bbox.get('height')}` DXF units")
    md.append(f"- **Bounding Box**: `X:[{bbox.get('min_x')}, {bbox.get('max_x')}], Y:[{bbox.get('min_y')}, {bbox.get('max_y')}]`")
    md.append(f"- **Total Line/Polyline Segments**: `{geom.get('total_segment_count')}`")
    md.append(f"- **Duplicate Segments**: `{geom.get('duplicate_segment_count')}`")
    md.append(f"- **Non-Zero Z-Coordinate Entities**: `{z_coords['non_zero_z_entity_count']}` (Z range: `[{z_coords['z_min']}, {z_coords['z_max']}]`)\n")

    md.append("### Candidate Wall Thicknesses (Parallel Line Pair Offsets):")
    md.append("| Offset Distance (DXF units) | Frequency |")
    md.append("|---|---|")
    for off in geom.get("candidate_wall_thicknesses", []):
        md.append(f"| {off['offset_distance']} | {off['frequency']} |")
    md.append("")

    md.append("## 3. Entity Type Distribution")
    md.append("| Entity Type | Count |")
    md.append("|---|---|")
    for etype, count in sorted(ents["by_type"].items(), key=lambda x: x[1], reverse=True):
        md.append(f"| {etype} | {count} |")
    md.append("")

    md.append("## 4. Layer Analysis & Classification")
    md.append("| Layer Name | Entities | Assigned Role | Confidence | Color | Locked |")
    md.append("|---|---|---|---|---|---|")
    for lname, ldata in layers.items():
        cinfo = cls.get(lname, {})
        md.append(f"| `{lname}` | {ldata['entity_count']} | `{cinfo.get('assigned_role')}` | {cinfo.get('confidence')} | {ldata['color']} | {ldata['is_locked']} |")
    md.append("")

    md.append("## 5. Room Label & Annotation Candidates")
    md.append(f"Found **{len(rooms)}** candidate room text labels in modelspace:\n")
    md.append("| Text Content | Layer | Position (X, Y) | Parsed Arch Dims |")
    md.append("|---|---|---|---|")
    for r in rooms:
        pos_str = f"({r['position'][0]:.1f}, {r['position'][1]:.1f})"
        md.append(f"| `{r['text']}` | `{r['layer']}` | {pos_str} | {r['parsed_arch_dims']} |")
    md.append("")

    md.append("## 6. Block Definitions & References")
    md.append(f"- **Total Block Definitions**: `{blocks['total_block_definitions']}`")
    md.append(f"- **User Block Definitions**: `{blocks['user_block_count']}`")
    md.append(f"- **Anonymous Blocks**: `{blocks['anonymous_block_count']}`\n")

    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Generated Markdown Audit Report: {md_filepath}")

def run_full_audit(dxf_path, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    auditor = DXFAuditor(dxf_path)
    data = auditor.run_audit()
    
    json_path = os.path.join(output_dir, "dxf_audit.json")
    md_path = os.path.join(output_dir, "dxf_audit.md")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Generated JSON Audit Report: {json_path}")
    
    generate_markdown_report(data, md_path)
    return data

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "d:/end game/dwg/sample1.dxf"
    run_full_audit(target)
