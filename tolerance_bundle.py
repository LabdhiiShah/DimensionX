"""
Tolerance Bundle Module (Layer 2 Audit - Task 4)
=================================================
WHAT THIS MODULE DOES:
- Computes an actionable `ToleranceBundle` containing all derived numeric tolerances required for geometric reconstruction.
- Derives `weld_tolerance` using nearest-endpoint gap distribution analysis (midpoint of largest gap below 90th percentile, falling back to 0.5 * median_wall_thickness).
- Derives `thickness_tolerance` (0.5 * median_wall_thickness).
- Defines explicit named constants for `merge_angle_tolerance_deg` and `merge_overlap_ratio` with documented architectural justifications.
- Emits header scale parameters ($INSUNITS, $MEASUREMENT, $LUNITS) without drawing extent span assumptions.
- Attaches explicit `source` strings to EVERY numeric field.

WHAT THIS MODULE DOES NOT DO:
- Does NOT perform wall assembly or topological graph edge construction.
- Does NOT wire tolerances into downstream consumers.
"""

import math
import numpy as np
from dataclasses import dataclass, field, asdict

@dataclass
class ValWithSource:
    value: float
    source: str

    def to_dict(self):
        return {"value": self.value, "source": self.source}

def compute_endpoint_gaps_and_weld_tolerance(lines, median_wall_thickness):
    """
    Computes nearest-endpoint gap distribution and derives weld_tolerance:
    1. Collect all nearest-endpoint distances between distinct segments.
    2. Sort ascending.
    3. Find largest gap between consecutive samples below 90th percentile.
    4. weld_tolerance = midpoint of that gap.
    5. If unimodal/no gap, set weld_tolerance = 0.5 * median_wall_thickness with source="fallback".
    """
    endpoints = []
    for l in lines:
        if isinstance(l, dict):
            if "p1" in l and "p2" in l:
                endpoints.append(l["p1"])
                endpoints.append(l["p2"])
            elif "points" in l and len(l["points"]) >= 2:
                endpoints.append(l["points"][0])
                endpoints.append(l["points"][-1])
                
    if len(endpoints) < 4:
        fallback_val = round(0.5 * median_wall_thickness if median_wall_thickness > 0 else 0.25, 4)
        return {
            "weld_tolerance": ValWithSource(fallback_val, "fallback: insufficient endpoints (< 4), set to 0.5 * median_wall_thickness"),
            "gap_stats": {
                "median": ValWithSource(0.0, "insufficient data"),
                "p10": ValWithSource(0.0, "insufficient data"),
                "p90": ValWithSource(0.0, "insufficient data")
            },
            "histogram": []
        }

    # Sample endpoints for pairwise nearest distance calculation
    pts = endpoints[::2] if len(endpoints) > 1000 else endpoints
    gaps = []
    
    for i in range(len(pts)):
        p_a = pts[i]
        min_dist_to_other = float('inf')
        for j in range(len(pts)):
            if i == j: continue
            p_b = pts[j]
            d = math.hypot(p_b[0] - p_a[0], p_b[1] - p_a[1])
            if 0.0001 < d < min_dist_to_other:
                min_dist_to_other = d
        if min_dist_to_other < float('inf'):
            gaps.append(min_dist_to_other)

    if not gaps:
        fallback_val = round(0.5 * median_wall_thickness if median_wall_thickness > 0 else 0.25, 4)
        return {
            "weld_tolerance": ValWithSource(fallback_val, "fallback: no endpoint gaps measured, set to 0.5 * median_wall_thickness"),
            "gap_stats": {
                "median": ValWithSource(0.0, "no gaps measured"),
                "p10": ValWithSource(0.0, "no gaps measured"),
                "p90": ValWithSource(0.0, "no gaps measured")
            },
            "histogram": []
        }

    gaps.sort()
    med_gap = float(np.median(gaps))
    p10_gap = float(np.percentile(gaps, 10))
    p90_gap = float(np.percentile(gaps, 90))

    # Filter samples below 90th percentile
    gaps_sub_p90 = [g for g in gaps if g <= p90_gap]
    
    largest_consecutive_gap = 0.0
    weld_tol_value = None
    gap_source = ""

    if len(gaps_sub_p90) >= 2:
        for i in range(len(gaps_sub_p90) - 1):
            diff = gaps_sub_p90[i+1] - gaps_sub_p90[i]
            if diff > largest_consecutive_gap and diff > 0.001:
                largest_consecutive_gap = diff
                weld_tol_value = (gaps_sub_p90[i+1] + gaps_sub_p90[i]) / 2.0
                gap_source = f"derived_rule: midpoint of largest consecutive gap ({diff:.4f}) below 90th percentile ({p90_gap:.4f})"

    if weld_tol_value is None or largest_consecutive_gap < 0.001:
        # Unimodal fallback
        fallback_val = round(0.5 * median_wall_thickness if median_wall_thickness > 0 else (med_gap * 0.5), 4)
        weld_tol_value = fallback_val
        gap_source = f"fallback: unimodal endpoint gap distribution, set to 0.5 * median_wall_thickness ({fallback_val:.4f})"

    # Calculate gap distribution histogram for verification report
    hist_counts, hist_edges = np.histogram(gaps_sub_p90, bins=10)
    histogram = [{"bin_min": round(hist_edges[k], 4), "bin_max": round(hist_edges[k+1], 4), "count": int(hist_counts[k])} for k in range(len(hist_counts))]

    return {
        "weld_tolerance": ValWithSource(round(weld_tol_value, 4), gap_source),
        "gap_stats": {
            "median": ValWithSource(round(med_gap, 4), "statistical_sample: median endpoint distance"),
            "p10": ValWithSource(round(p10_gap, 4), "statistical_sample: 10th percentile endpoint distance"),
            "p90": ValWithSource(round(p90_gap, 4), "statistical_sample: 90th percentile endpoint distance")
        },
        "histogram": histogram
    }

def compute_wall_thickness_stats(geom_stats, header_info):
    """Computes median, p10, p90 wall thickness statistics from candidate wall thickness offsets."""
    offsets = [t["offset_distance"] for t in geom_stats.get("candidate_wall_thicknesses", []) if t["offset_distance"] > 0.01]
    
    if offsets:
        med_t = float(np.median(offsets))
        p10_t = float(np.percentile(offsets, 10))
        p90_t = float(np.percentile(offsets, 90))
        src = "statistical_sample: extracted parallel line pair offsets"
    else:
        # Scale-dependent fallback
        insunits = header_info.get("INSUNITS_code", 0)
        if insunits == 4: # Millimeters
            med_t, p10_t, p90_t = 114.3, 100.0, 230.0
            src = "fallback: standard architectural wall priors for Millimeter drawings"
        elif insunits == 6: # Meters
            med_t, p10_t, p90_t = 0.115, 0.100, 0.230
            src = "fallback: standard architectural wall priors for Meter drawings"
        else:
            med_t, p10_t, p90_t = 0.15, 0.10, 0.23
            src = "fallback: default nominal architectural wall thickness"

    return {
        "median": ValWithSource(round(med_t, 4), src),
        "p10": ValWithSource(round(p10_t, 4), src),
        "p90": ValWithSource(round(p90_t, 4), src)
    }

def build_tolerance_bundle(lines, header_info, geom_stats):
    """
    Public entry point for Task 4.
    Constructs actionable ToleranceBundle with sources attached to EVERY numeric field.
    """
    bbox = geom_stats.get("bounding_box", {})
    w = bbox.get("width", 0.0)
    h = bbox.get("height", 0.0)
    diag = math.hypot(w, h)

    # 1. Wall Thickness Statistics
    wt_stats = compute_wall_thickness_stats(geom_stats, header_info)
    median_wt = wt_stats["median"].value

    # 2. Weld Tolerance & Endpoint Gap Statistics
    weld_data = compute_endpoint_gaps_and_weld_tolerance(lines, median_wt)
    weld_tol = weld_data["weld_tolerance"]
    gap_stats = weld_data["gap_stats"]
    histogram = weld_data["histogram"]

    # 3. Thickness Tolerance
    thick_tol = ValWithSource(round(0.5 * median_wt, 4), f"derived_rule: 0.5 * (median_wall_thickness = {median_wt:.4f})")

    # 4. Named Constants with Documented Architectural Justifications
    merge_angle_deg = ValWithSource(
        5.0, 
        "named_constant: 5.0 degrees angular tolerance typical for hand-drafted or vector CAD wall segment alignment"
    )
    merge_overlap_ratio = ValWithSource(
        0.10, 
        "named_constant: 10% minimum overlap ratio required to confirm colinear wall segment continuity"
    )

    # 5. Header Scale Parameters (Task 4 Requirement: Emit only what header states)
    insunits_code = header_info.get("INSUNITS_code", 0)
    measurement = header_info.get("MEASUREMENT", None)
    lunits = header_info.get("LUNITS", None)

    scale_guess = "UNSPECIFIED"
    scale_source = "header: $INSUNITS=0 (unspecified)"
    scale_confidence = "LOW"

    if insunits_code != 0:
        scale_guess = header_info.get("INSUNITS_description", f"Code_{insunits_code}")
        scale_source = f"header: $INSUNITS explicitly set to code {insunits_code}"
        # Set scale_confidence to LOW unless $INSUNITS is nonzero and consistent with $MEASUREMENT
        if (insunits_code in (4, 5, 6) and measurement == 1) or (insunits_code in (1, 2) and measurement == 0):
            scale_confidence = "HIGH"
        else:
            scale_confidence = "MEDIUM"

    bundle_dict = {
        "weld_tolerance": weld_tol.to_dict(),
        "thickness_tolerance": thick_tol.to_dict(),
        "merge_angle_tolerance_deg": merge_angle_deg.to_dict(),
        "merge_overlap_ratio": merge_overlap_ratio.to_dict(),
        "scale": {
            "scale_guess": scale_guess,
            "scale_source": scale_source,
            "scale_confidence": scale_confidence,
            "INSUNITS_code": insunits_code,
            "MEASUREMENT": measurement,
            "LUNITS": lunits
        },
        "wall_thickness_stats": {
            "median": wt_stats["median"].to_dict(),
            "p10": wt_stats["p10"].to_dict(),
            "p90": wt_stats["p90"].to_dict()
        },
        "endpoint_gap_stats": {
            "median": gap_stats["median"].to_dict(),
            "p10": gap_stats["p10"].to_dict(),
            "p90": gap_stats["p90"].to_dict(),
            "gap_histogram_sub_p90": histogram
        },
        "drawing_extent": {
            "min_x": ValWithSource(bbox.get("min_x", 0.0), "geometry_statistics: minimum X coordinate").to_dict(),
            "max_x": ValWithSource(bbox.get("max_x", 0.0), "geometry_statistics: maximum X coordinate").to_dict(),
            "min_y": ValWithSource(bbox.get("min_y", 0.0), "geometry_statistics: minimum Y coordinate").to_dict(),
            "max_y": ValWithSource(bbox.get("max_y", 0.0), "geometry_statistics: maximum Y coordinate").to_dict(),
            "width": ValWithSource(round(w, 4), "geometry_statistics: extent width").to_dict(),
            "height": ValWithSource(round(h, 4), "geometry_statistics: extent height").to_dict(),
            "diagonal": ValWithSource(round(diag, 4), "geometry_statistics: extent bounding box diagonal").to_dict()
        }
    }

    return bundle_dict
