"""
Non-Layer Wall Promoter Module (Layer 1 & 2 Audit Promotion Engine)
====================================================================
WHAT THIS MODULE DOES:
- Evaluates non-WALL-layer segments for wall promotion using multi-signal geometric and layer-role criteria.
- Implements Part A1 Fragment-Density Skip Rule & Rescue Criteria.
- Implements Part A2 Role Confidence Floor & Conflict Gating.
- Implements Part A3 Structural Layer Promotion Guard & Promoted Structural Sub-list.
- Implements Part A4 100% Layer Diagnostics & Layer Warnings Reporting Schema.
- Fixes the length threshold reporting bug by computing `threshold = cfg.min_length_factor * median_wall_thickness` once before comparison.
- Uses spatial indexing (Shapely STRtree) for deterministic parallel partner detection (matching thickness, overlap ratio, and angular alignment).
- Computes candidate network connectivity prior to promotion decision.
- Computes auditable promotion scores in [0.0, 1.0] based on validated weights.
- Generates detailed promotion reasons and skipped segment audit logs.

WHAT THIS MODULE DOES NOT DO:
- Does NOT perform downstream wall assembly, centerline extraction, or topological graph construction.
- Does NOT modify downstream room polygonization or building footprint derivation.
- Does NOT alter Layer 1 block expansion or entity normalization outputs.
"""

import math
import numpy as np
from collections import defaultdict
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from promotion_config import PromotionConfig

FORBIDDEN_ROLES = {"DIMENSION", "ANNOTATION", "HATCH", "ELECTRICAL", "FURNITURE", "SITE"}
STRICT_ROLES = {"STRUCTURAL"}

def is_long_enough(seg_len, median_thickness, cfg):
    """
    Computes minimum length threshold once and tests segment length.
    Threshold = cfg.min_length_factor * median_thickness.
    """
    threshold = round(cfg.min_length_factor * median_thickness, 4)
    return seg_len >= threshold, threshold

def compute_segment_angle_deg(p1, p2):
    """Computes direction angle of line segment in degrees [0, 180)."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle = math.degrees(math.atan2(dy, dx)) % 180.0
    return angle

def compute_angle_diff_deg(angle1, angle2):
    """Computes minimum angular difference between two line directions in [0, 90]."""
    diff = abs(angle1 - angle2) % 180.0
    if diff > 90.0:
        diff = 180.0 - diff
    return round(diff, 3)

def compute_parallel_geometry(candidate, partner, median_thickness, cfg):
    """
    Evaluates geometric alignment between candidate segment and a potential parallel partner.
    Returns (is_valid, offset, angle_diff, overlap_ratio).
    """
    p1, p2 = candidate["p1"], candidate["p2"]
    q1, q2 = partner["p1"], partner["p2"]
    
    cand_len = candidate["segment_length"]
    if cand_len < 1e-4:
        return False, 0.0, 0.0, 0.0

    # 1. Angle Difference
    a_cand = compute_segment_angle_deg(p1, p2)
    a_part = compute_segment_angle_deg(q1, q2)
    angle_diff = compute_angle_diff_deg(a_cand, a_part)

    if angle_diff > cfg.parallel_angle_tol_deg:
        return False, 0.0, angle_diff, 0.0

    # 2. Perpendicular Offset
    cand_line = candidate["geometry"]
    part_mid = Point((q1[0] + q2[0]) / 2.0, (q1[1] + q2[1]) / 2.0)
    offset = round(cand_line.distance(part_mid), 4)

    min_offset = median_thickness * (1.0 - cfg.thickness_match_rel_tol)
    max_offset = median_thickness * (1.0 + cfg.thickness_match_rel_tol)

    if not (min_offset <= offset <= max_offset):
        return False, offset, angle_diff, 0.0

    # 3. Projected Overlap Ratio
    dx = (p2[0] - p1[0]) / cand_len
    dy = (p2[1] - p1[1]) / cand_len

    # Project partner endpoints onto candidate line vector
    t_q1 = (q1[0] - p1[0]) * dx + (q1[1] - p1[1]) * dy
    t_q2 = (q2[0] - p1[0]) * dx + (q2[1] - p1[1]) * dy

    t_min = min(t_q1, t_q2)
    t_max = max(t_q1, t_q2)

    overlap_start = max(0.0, t_min)
    overlap_end = min(cand_len, t_max)
    overlap_len = max(0.0, overlap_end - overlap_start)
    overlap_ratio = round(overlap_len / cand_len, 4)

    if overlap_ratio < cfg.min_overlap_ratio:
        return False, offset, angle_diff, overlap_ratio

    return True, offset, angle_diff, overlap_ratio

def find_best_parallel_partner(candidate, spatial_index, all_segments, median_thickness, cfg):
    """
    Searches spatial index for parallel partners and deterministically ranks valid partners:
    1. Closest thickness error (|offset - median_thickness|)
    2. Highest overlap ratio
    3. Smallest angle difference
    """
    cand_geom = candidate["geometry"]
    search_radius = median_thickness * (1.0 + cfg.thickness_match_rel_tol)
    search_box = cand_geom.buffer(search_radius)

    # Query spatial index
    possible_indices = spatial_index.query(search_box)
    valid_partners = []

    for idx in possible_indices:
        partner = all_segments[idx]
        # Do not partner with self or identical segment handles
        if partner["candidate_id"] == candidate["candidate_id"]:
            continue
        if set(partner["handles"]).issubset(set(candidate["handles"])):
            continue

        is_valid, offset, angle_diff, overlap_ratio = compute_parallel_geometry(
            candidate, partner, median_thickness, cfg
        )

        if is_valid:
            thick_err = abs(offset - median_thickness)
            partner_handle = partner["handles"][0] if partner["handles"] else "UNKNOWN"
            valid_partners.append({
                "partner_handle": partner_handle,
                "partner_layer": partner["source_layer"],
                "partner_top_role": partner["assigned_layer_top_role"],
                "offset": offset,
                "angle_diff": angle_diff,
                "overlap_ratio": overlap_ratio,
                "thick_err": thick_err
            })

    if not valid_partners:
        return None

    # Deterministic ranking
    valid_partners.sort(key=lambda p: (p["thick_err"], -p["overlap_ratio"], p["angle_diff"]))
    return valid_partners[0]

def compute_candidate_connectivity(candidates, weld_tolerance):
    """
    Computes connectivity counts among the COMPLETE eligible candidate network.
    Two candidates are connected if their endpoints are within weld_tolerance.
    """
    tol = max(weld_tolerance, 1e-4)

    for c in candidates:
        p1 = (round(c["p1"][0] / tol) * tol, round(c["p1"][1] / tol) * tol)
        p2 = (round(c["p2"][0] / tol) * tol, round(c["p2"][1] / tol) * tol)
        c["grid_p1"] = p1
        c["grid_p2"] = p2

    for c in candidates:
        p1, p2 = c["p1"], c["p2"]
        count = 0
        for other in candidates:
            if other["candidate_id"] == c["candidate_id"]: continue
            op1, op2 = other["p1"], other["p2"]
            
            d11 = math.hypot(p1[0]-op1[0], p1[1]-op1[1])
            d12 = math.hypot(p1[0]-op2[0], p1[1]-op2[1])
            d21 = math.hypot(p2[0]-op1[0], p2[1]-op1[1])
            d22 = math.hypot(p2[0]-op2[0], p2[1]-op2[1])

            if min(d11, d12, d21, d22) <= tol:
                count += 1
        c["connectivity_count"] = count

def evaluate_promotion_score(seg_len, median_thickness, has_partner, conn_count, layer_role, cfg):
    """
    Computes promotion score clamped to [0.0, 1.0]:
    score = length_weight * length_score + parallel_weight * parallel_score + connectivity_weight * connectivity_score + layer_role_weight * layer_role_score
    """
    length_score = min(1.0, seg_len / (3.0 * median_thickness)) if median_thickness > 0 else 0.5
    parallel_score = 1.0 if has_partner else 0.0
    connectivity_score = min(1.0, conn_count / 3.0)

    if layer_role == "WALL":
        role_score = 1.0
    elif layer_role in STRICT_ROLES:
        role_score = 0.2
    elif layer_role == "UNKNOWN":
        role_score = 0.5
    else:
        role_score = 0.1

    raw_score = (
        cfg.length_weight * length_score +
        cfg.parallel_weight * parallel_score +
        cfg.connectivity_weight * connectivity_score +
        cfg.layer_role_weight * role_score
    )

    clamped_score = max(0.0, min(1.0, round(raw_score, 4)))
    return clamped_score

def inspect_non_layer_promotions(raw_wall_lines, layer_classifications, tolerance_bundle, cfg=None):
    """
    Public entry point for Task 5.
    Evaluates non-layer wall promotion using multi-signal geometric and layer-role rules.
    """
    if cfg is None:
        cfg = PromotionConfig.load()

    thick_stats = tolerance_bundle.get("wall_thickness_stats", {})
    med_entry = thick_stats.get("median", {})
    median_wt = med_entry.get("value", 0.15) if isinstance(med_entry, dict) else float(med_entry)
    if median_wt <= 0:
        median_wt = 0.15

    weld_entry = tolerance_bundle.get("weld_tolerance", {})
    weld_tol = weld_entry.get("value", 0.25) if isinstance(weld_entry, dict) else float(weld_entry)

    # 1. Candidate Generation
    all_candidates = []
    cand_id = 0
    for obj in raw_wall_lines:
        p1, p2 = obj.get("p1"), obj.get("p2")
        if not p1 or not p2 or p1 == p2:
            continue
            
        length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if length < 1e-4:
            continue

        layer_name = obj.get("layer", "UNKNOWN")
        c_info = layer_classifications.get(layer_name, {})
        ranked_roles = c_info.get("candidate_roles", [])
        top_role = ranked_roles[0]["role"] if ranked_roles else "UNKNOWN"
        top_conf = ranked_roles[0]["confidence"] if ranked_roles else 0.0

        handles = obj.get("handles", [obj.get("handle", f"h_{cand_id}")])

        all_candidates.append({
            "candidate_id": cand_id,
            "handles": handles,
            "source_layer": layer_name,
            "assigned_layer_top_role": top_role,
            "top_confidence": top_conf,
            "segment_length": round(length, 4),
            "p1": p1, "p2": p2,
            "geometry": LineString([p1, p2]),
            "provenance": obj.get("provenance", {})
        })
        cand_id += 1

    # Initialize Diagnostics for 100% of Classified Layers
    layer_diagnostics = {}
    layer_warnings_set = set()

    for l_name, l_info in layer_classifications.items():
        top_r = l_info.get("candidate_roles", [{}])[0].get("role", "UNKNOWN") if l_info.get("candidate_roles") else "UNKNOWN"
        top_c = l_info.get("candidate_roles", [{}])[0].get("confidence", 0.0) if l_info.get("candidate_roles") else 0.0
        f_ratio = l_info.get("fragment_ratio", 0.0)
        conf_flag = l_info.get("conflict", False)
        
        warn_msg = None
        if f_ratio >= 0.90:
            warn_msg = f"high fragment-density layer (fragment_ratio {f_ratio:.3f} >= 0.90 threshold)"
            layer_warnings_set.add(f"Layer {l_name}: fragment_ratio {f_ratio:.3f} >= 0.90 threshold, high fragment density skip rule active")
        elif f_ratio >= 0.50:
            warn_msg = f"fragment_ratio {f_ratio:.3f} >= 0.50 threshold, confidence capped"
            layer_warnings_set.add(f"Layer {l_name}: fragment_ratio {f_ratio:.3f} >= 0.50 threshold, confidence capped")

        if conf_flag:
            layer_warnings_set.add(f"Layer {l_name}: role conflict detected between Name and Geometry signals")

        layer_diagnostics[l_name] = {
            "entity_count": l_info.get("entity_count", 0),
            "fragment_ratio": f_ratio,
            "top_role": top_r,
            "top_confidence": top_c,
            "conflict": conf_flag,
            "promoted_count": 0,
            "skipped_count": 0,
            "warning": warn_msg
        }

    if not all_candidates:
        return {
            "promoted_non_wall_segments_count": 0,
            "skipped_non_wall_segments_count": 0,
            "promotion_config_used": cfg.to_dict(),
            "promoted_segments": [],
            "skipped_segments": [],
            "promoted_structural_segments": [],
            "layer_warnings": sorted(list(layer_warnings_set)),
            "layer_diagnostics": layer_diagnostics
        }

    # 2. Build Spatial Index for Parallel Partner Search
    geoms = [c["geometry"] for c in all_candidates]
    spatial_index = STRtree(geoms)

    # 3. Compute Network Connectivity
    compute_candidate_connectivity(all_candidates, weld_tol)

    promoted_records = []
    promoted_structural_records = []
    skipped_records = []
    total_skipped_count = 0

    # 4. Evaluate Promotion Gates
    for c in all_candidates:
        layer_name = c["source_layer"]
        top_role = c["assigned_layer_top_role"]
        top_conf = c.get("top_confidence", 0.0)
        seg_len = c["segment_length"]
        conn_count = c["connectivity_count"]

        c_info = layer_classifications.get(layer_name, {})
        fragment_ratio = c_info.get("fragment_ratio", 0.0)
        conflict = c_info.get("conflict", False)

        is_wall_layer = ("WALL" in layer_name.upper() or top_role == "WALL")
        
        # Non-wall promotion only evaluates non-wall-layer segments
        if is_wall_layer:
            continue

        failed_checks = []

        # Section B: Length Threshold Test
        len_passed, len_threshold = is_long_enough(seg_len, median_wt, cfg)

        if not len_passed:
            failed_checks.append(f"below length threshold: {seg_len:.3f} < {len_threshold:.3f}")

        # Section D: Parallel Partner Search
        best_partner = find_best_parallel_partner(c, spatial_index, all_candidates, median_wt, cfg)
        has_partner = (best_partner is not None)

        if not has_partner:
            failed_checks.append("no valid parallel wall partner found")

        # Compute promotion score
        score = evaluate_promotion_score(seg_len, median_wt, has_partner, conn_count, top_role, cfg)

        # Part A1: Fragment-Density Skip Rule (fragment_ratio >= 0.90)
        if fragment_ratio >= 0.90:
            # Check rescue criteria:
            # 1. Partner exists and is on a WALL layer (top_role == WALL or "WALL" in layer name)
            # 2. Parallel offset matches median_wt within thickness_match_rel_tol (guaranteed by best_partner)
            # 3. Overlap ratio >= min_overlap_ratio (guaranteed by best_partner)
            # 4. Score >= min_promotion_score + 0.15
            is_rescued = False
            if best_partner and (best_partner.get("partner_top_role") == "WALL" or "WALL" in best_partner.get("partner_layer", "").upper()):
                if score >= (cfg.min_promotion_score + 0.15):
                    is_rescued = True
            
            if not is_rescued:
                failed_checks.append("high fragment-density layer (fragment_ratio >= 0.90) without rescue parallel partner")

        # Part A2: Role Confidence Floor & Conflict Gating
        if top_role in FORBIDDEN_ROLES:
            failed_checks.append(f"forbidden layer role '{top_role}'")

        if (top_conf < cfg.min_layer_confidence_for_role) or conflict:
            # Low role confidence or signal conflict: require STRICT geometry (len_passed AND has_partner AND score >= min)
            if not len_passed or not has_partner or score < cfg.min_promotion_score:
                failed_checks.append(f"low role confidence ({top_conf:.2f}) or conflict requires strict geometry (length AND parallel partner)")

        # Gating for STRICT roles (e.g. STRUCTURAL)
        if top_role in STRICT_ROLES:
            if not len_passed or not has_partner:
                failed_checks.append("strict role requirement failed (requires length AND parallel partner)")

        # Part A3: Structural Layer Promotion Guard
        if cfg.structural_requires_geometry_agreement and top_role == "STRUCTURAL":
            # Must have parallel partner on WALL layer or matching thickness
            has_wall_anchor = (best_partner is not None) and (best_partner.get("partner_top_role") == "WALL" or "WALL" in best_partner.get("partner_layer", "").upper())
            thick_matches = (best_partner is not None) # best_partner offset already matches median_wt within tolerance
            if not (has_wall_anchor or thick_matches):
                failed_checks.append("structural role requires wall anchor or matching thickness")

        # Score Threshold Check
        if score < cfg.min_promotion_score:
            failed_checks.append(f"promotion score {score:.2f} < min threshold {cfg.min_promotion_score:.2f}")

        # Decision
        is_promoted = (len(failed_checks) == 0)

        if is_promoted:
            partner_h = best_partner["partner_handle"] if best_partner else "none"
            offset_val = best_partner["offset"] if best_partner else 0.0
            angle_val = best_partner["angle_diff"] if best_partner else 0.0
            overlap_val = best_partner["overlap_ratio"] if best_partner else 0.0

            reason = (
                f"length {seg_len:.3f} >= threshold {len_threshold:.3f}; "
                f"parallel partner found handle {partner_h}; "
                f"offset {offset_val:.3f}; "
                f"overlap {overlap_val:.2f}; "
                f"connectivity {conn_count}; "
                f"layer role {top_role}; "
                f"score {score:.2f}"
            )

            rec = {
                "handles": c["handles"],
                "source_layer": layer_name,
                "assigned_layer_top_role": top_role,
                "segment_length": seg_len,
                "p1": [c["p1"][0], c["p1"][1]],
                "p2": [c["p2"][0], c["p2"][1]],
                "promotion_score": score,
                "promotion_reason": reason,
                "parallel_partner_handle": partner_h,
                "parallel_offset": offset_val,
                "parallel_angle_difference_deg": angle_val,
                "parallel_overlap_ratio": overlap_val,
                "connectivity_count": conn_count,
                "promotion_threshold_used": {
                    "value": len_threshold,
                    "source": "derived_rule: min_length_factor * median_wall_thickness"
                }
            }
            promoted_records.append(rec)
            
            if top_role == "STRUCTURAL":
                promoted_structural_records.append(rec)

            if layer_name in layer_diagnostics:
                layer_diagnostics[layer_name]["promoted_count"] += 1
        else:
            total_skipped_count += 1
            if layer_name in layer_diagnostics:
                layer_diagnostics[layer_name]["skipped_count"] += 1

            if len(skipped_records) < cfg.max_skipped_log:
                skip_reason = "; ".join(failed_checks) if failed_checks else "rejected by promotion gates"
                skipped_records.append({
                    "handles": c["handles"],
                    "source_layer": layer_name,
                    "segment_length": seg_len,
                    "skip_reason": skip_reason,
                    "layer_top_role": top_role,
                    "failed_checks": failed_checks
                })

    return {
        "promoted_non_wall_segments_count": len(promoted_records),
        "skipped_non_wall_segments_count": total_skipped_count,
        "promotion_config_used": cfg.to_dict(),
        "promoted_segments": promoted_records,
        "skipped_segments": skipped_records,
        "promoted_structural_segments": promoted_structural_records,
        "layer_warnings": sorted(list(layer_warnings_set)),
        "layer_diagnostics": layer_diagnostics
    }
