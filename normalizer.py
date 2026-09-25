"""
Entity Normalizer Module (Layer 1 Ingestion - Task 2)
=====================================================
WHAT THIS MODULE DOES:
- Converts curved entities (ARC, CIRCLE, SPLINE) into polylines using a drawing-derived chord tolerance.
- Computes chord tolerance using the derived rule: tolerance = (median_wall_thickness) / 4.0, falling back to (drawing_extent_diagonal) / 2000.0 if unavailable.
- Preserves original entity handles on all generated polylines to maintain provenance.
- Preserves `width` attributes on LWPOLYLINEs without discarding them.
- Emits a complete report of the chord tolerance used and its exact derivation source.

WHAT THIS MODULE DOES NOT DO:
- Does NOT merge colinear or overlapping line segments.
- Does NOT split lines at geometric intersections.
- Does NOT snap endpoints or perform vertex welding.
- Does NOT filter, reorder, or deduplicate entities.
"""

import math
import numpy as np

def compute_chord_tolerance(wall_thickness_stats, extent_stats):
    """
    Computes chord tolerance dynamically using the explicit derived rule:
    tolerance = (median_wall_thickness) / 4.0
    Fallback: (drawing_extent_diagonal) / 2000.0
    """
    def get_val(item):
        if hasattr(item, 'value'):
            return float(item.value)
        elif isinstance(item, dict):
            return float(item.get("value", 0.0))
        try:
            return float(item)
        except (ValueError, TypeError):
            return 0.0

    median_t = get_val(wall_thickness_stats.get("median", 0.0) if wall_thickness_stats else 0.0)
    extent_diag = get_val(extent_stats.get("diagonal", 0.0) if extent_stats else 0.0)

    if median_t > 0.01:
        tolerance = round(median_t / 4.0, 4)
        source = f"derived_rule: (median_wall_thickness = {median_t:.2f}) / 4.0"
    elif extent_diag > 0.1:
        tolerance = round(extent_diag / 2000.0, 4)
        source = f"fallback_rule: (drawing_extent_diagonal = {extent_diag:.2f}) / 2000.0"
    else:
        # Emergency fallback if both extent and wall thickness statistics are zero
        tolerance = 0.025
        source = "fallback_rule: default_minimum_geometric_resolution"

    return tolerance, source

def arc_to_polyline(center, radius, start_deg, end_deg, chord_tolerance):
    """
    Converts an ARC or CIRCLE to a polyline using chord tolerance h:
    h = R * (1 - cos(theta / 2))  =>  cos(theta / 2) = 1 - h / R
    => theta = 2 * acos(1 - h / R)
    """
    if radius <= 0:
        return [center]

    ratio = max(0.0, min(1.0, 1.0 - (chord_tolerance / radius)))
    theta_step = 2.0 * math.acos(ratio)
    # Clamp step to between 2 degrees and 30 degrees for smooth rendering
    theta_step = max(math.radians(2.0), min(math.radians(30.0), theta_step))

    start_rad = math.radians(start_deg)
    end_rad = math.radians(end_deg)
    if end_rad < start_rad:
        end_rad += 2.0 * math.pi

    span = end_rad - start_rad
    num_steps = max(8, int(math.ceil(span / theta_step)))

    angles = np.linspace(start_rad, end_rad, num=num_steps)
    points = [(round(center[0] + radius * math.cos(a), 4), round(center[1] + radius * math.sin(a), 4)) for a in angles]
    return points

def spline_to_polyline(spline_entity, chord_tolerance):
    """Converts a SPLINE entity or B-spline representation to polyline points."""
    try:
        if hasattr(spline_entity, 'flattening'):
            pts = list(spline_entity.flattening(distance=chord_tolerance))
            return [(round(p[0], 4), round(p[1], 4)) for p in pts]
        elif hasattr(spline_entity, 'control_points'):
            pts = list(spline_entity.control_points)
            return [(round(p[0], 4), round(p[1], 4)) for p in pts]
    except Exception:
        pass
    return []

class EntityNormalizer:
    def __init__(self, wall_thickness_stats=None, extent_stats=None):
        self.wall_thickness_stats = wall_thickness_stats or {}
        self.extent_stats = extent_stats or {}
        self.chord_tolerance, self.tolerance_source = compute_chord_tolerance(
            self.wall_thickness_stats, self.extent_stats
        )
        self.converted_curved_count = 0

    def normalize(self, entities):
        """
        Normalizes a list of entities without merging, snapping, or filtering.
        Converts ARC, CIRCLE, SPLINE to polylines.
        Preserves original handle and LWPOLYLINE width attributes.
        """
        normalized = []
        self.converted_curved_count = 0

        for item in entities:
            # Handle wrapped expanded objects vs raw ezdxf entities
            if isinstance(item, dict):
                etype = item["entity_type"]
                handle = item["handle"]
                layer = item["layer"]
                prov = item.get("provenance", {})
                dxf_entity = item.get("dxf_entity", None)
            else:
                etype = item.dxftype()
                handle = item.dxf.handle
                layer = item.dxf.layer
                prov = {"source_file": "UNKNOWN", "nesting_path": ["*Model_Space"]}
                dxf_entity = item

            # 1. LINE entities pass through
            if etype == 'LINE':
                if isinstance(item, dict) and "p1" in item:
                    p1, p2 = item["p1"], item["p2"]
                else:
                    p1 = (round(dxf_entity.dxf.start[0], 4), round(dxf_entity.dxf.start[1], 4))
                    p2 = (round(dxf_entity.dxf.end[0], 4), round(dxf_entity.dxf.end[1], 4))
                normalized.append({
                    "entity_type": "LINE",
                    "handle": handle,
                    "layer": layer,
                    "p1": p1, "p2": p2,
                    "provenance": prov
                })

            # 2. LWPOLYLINE / POLYLINE entities with width attribute preservation
            elif etype in ('LWPOLYLINE', 'POLYLINE'):
                if isinstance(item, dict) and "points" in item:
                    pts = item["points"]
                    closed = item.get("closed", False)
                    width = item.get("width", 0.0)
                else:
                    raw_pts = list(dxf_entity.get_points('xy'))
                    pts = [(round(p[0], 4), round(p[1], 4)) for p in raw_pts]
                    closed = dxf_entity.closed
                    const_w = getattr(dxf_entity.dxf, 'const_width', 0.0)
                    start_w = getattr(dxf_entity.dxf, 'start_width', 0.0)
                    width = const_w if const_w > 0 else (start_w if start_w > 0 else 0.0)

                normalized.append({
                    "entity_type": "LWPOLYLINE",
                    "handle": handle,
                    "layer": layer,
                    "points": pts,
                    "closed": closed,
                    "width": round(width, 4), # Width preserved explicitly as required by Task 2
                    "provenance": prov
                })

            # 3. ARC / CIRCLE entities converted to Polylines
            elif etype in ('ARC', 'CIRCLE'):
                self.converted_curved_count += 1
                if isinstance(item, dict) and "center" in item:
                    center = item["center"]
                    radius = item["radius"]
                    start_deg = item.get("start_angle", 0.0)
                    end_deg = item.get("end_angle", 360.0)
                else:
                    center = (round(dxf_entity.dxf.center[0], 4), round(dxf_entity.dxf.center[1], 4))
                    radius = round(dxf_entity.dxf.radius, 4)
                    start_deg = getattr(dxf_entity.dxf, 'start_angle', 0.0)
                    end_deg = getattr(dxf_entity.dxf, 'end_angle', 360.0) if etype == 'ARC' else 360.0

                poly_pts = arc_to_polyline(center, radius, start_deg, end_deg, self.chord_tolerance)
                normalized.append({
                    "entity_type": "LWPOLYLINE",
                    "handle": handle, # Original entity handle preserved
                    "layer": layer,
                    "points": poly_pts,
                    "closed": (etype == 'CIRCLE'),
                    "width": 0.0,
                    "converted_from_curved": etype,
                    "chord_tolerance_used": self.chord_tolerance,
                    "provenance": prov
                })

            # 4. SPLINE entities converted to Polylines
            elif etype == 'SPLINE':
                self.converted_curved_count += 1
                poly_pts = spline_to_polyline(dxf_entity, self.chord_tolerance) if dxf_entity else []
                normalized.append({
                    "entity_type": "LWPOLYLINE",
                    "handle": handle, # Original handle preserved
                    "layer": layer,
                    "points": poly_pts,
                    "closed": getattr(dxf_entity, 'closed', False) if dxf_entity else False,
                    "width": 0.0,
                    "converted_from_curved": "SPLINE",
                    "chord_tolerance_used": self.chord_tolerance,
                    "provenance": prov
                })

            # 5. TEXT / MTEXT annotations
            elif etype in ('TEXT', 'MTEXT'):
                if isinstance(item, dict) and "text" in item:
                    txt = item["text"]
                    pos = item["position"]
                else:
                    txt = dxf_entity.text if etype == 'MTEXT' else dxf_entity.dxf.text
                    pos = (round(dxf_entity.dxf.insert[0], 4), round(dxf_entity.dxf.insert[1], 4))
                normalized.append({
                    "entity_type": etype,
                    "handle": handle,
                    "layer": layer,
                    "text": txt,
                    "position": pos,
                    "provenance": prov
                })

            else:
                # Other non-curved entities passed through
                normalized.append(item if isinstance(item, dict) else {
                    "entity_type": etype,
                    "handle": handle,
                    "layer": layer,
                    "provenance": prov
                })

        return {
            "normalized_entities": normalized,
            "converted_curved_entity_count": self.converted_curved_count,
            "chord_tolerance_used": self.chord_tolerance,
            "chord_tolerance_source": self.tolerance_source
        }

def normalize_entities(entities, wall_thickness_stats=None, extent_stats=None):
    """
    Public entry point for Task 2.
    Takes expanded entities, wall thickness statistics, and extent statistics.
    Returns normalized entity list and derivation report.
    """
    normalizer = EntityNormalizer(wall_thickness_stats, extent_stats)
    return normalizer.normalize(entities)
