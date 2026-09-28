"""
Preflight validation for DXF floor plans.
Runs after audit + scale resolution but before geometry extraction.
If the drawing doesn't meet minimum architectural standards, the pipeline
refuses to continue and returns a structured failure report.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class PreflightIssue:
    gate: str           # e.g. "G1_wall_layer"
    severity: str       # "block" or "warn"
    message: str        # human-readable
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreflightReport:
    passed: bool
    issues: List[PreflightIssue]
    readiness_score: float  # 0.0 – 1.0
    summary: str            # one-line human message


def check_preflight(
    audit_data: Dict[str, Any],
    scale_bundle: Any,            # ScaleBundle from layer3_scale
    tolerance_bundle: Dict[str, Any],
    layer_classifications: Dict[str, Any],
) -> PreflightReport:
    """
    Runs the six gates. Returns a PreflightReport.
    Never raises — always returns a report with issues.
    """
    issues: List[PreflightIssue] = []
    details: Dict[str, Any] = {}

    # --- G1 — Wall layer exists ---
    wall_layers = []
    for layer_name, cls in (layer_classifications or {}).items():
        top_role = None
        conf = 0.0
        roles = cls.get("candidate_roles", [])
        if roles:
            top_role = roles[0].get("role")
            conf = roles[0].get("confidence", 0.0)
        # Accept either high-confidence WALL role, or "WALL" token in name with any confidence
        if top_role == "WALL" and conf >= 0.4:
            wall_layers.append(layer_name)
        elif "WALL" in layer_name.upper() and cls.get("entity_count", 0) > 0:
            wall_layers.append(layer_name)

    wall_layers = list(set(wall_layers))
    details["wall_layers"] = wall_layers

    if not wall_layers:
        issues.append(PreflightIssue(
            gate="G1_wall_layer",
            severity="block",
            message="No wall layer detected. This drawing doesn't appear to contain architectural walls.",
            details={"checked_layers": list((layer_classifications or {}).keys())},
        ))

    # --- G2 — Wall entities ---
    wall_entity_count = 0
    for layer_name in wall_layers:
        cls = (layer_classifications or {}).get(layer_name, {})
        wall_entity_count += cls.get("entity_count", 0)
    details["wall_entity_count"] = wall_entity_count

    if wall_entity_count < 20:
        issues.append(PreflightIssue(
            gate="G2_wall_entities",
            severity="block",
            message=f"Too few wall entities ({wall_entity_count}). Minimum is 20. "
                    f"This looks like a partial/detail drawing, not a full floor plan.",
            details={"wall_entity_count": wall_entity_count},
        ))

    # --- G3 — Unit resolvable ---
    unit_name = getattr(scale_bundle, "unit_name", "UNSPECIFIED")
    confidence = getattr(scale_bundle, "confidence", "UNSPECIFIED")
    details["unit"] = {"name": unit_name, "confidence": confidence}

    if unit_name == "UNSPECIFIED" or confidence == "UNSPECIFIED":
        issues.append(PreflightIssue(
            gate="G3_units",
            severity="block",
            message="Cannot determine drawing units. Wall thickness and extent are both implausible under any standard unit.",
            details=details["unit"],
        ))

    # --- G4 — Wall thickness plausible ---
    wt_stats = (tolerance_bundle or {}).get("wall_thickness_stats", {})
    med_entry = wt_stats.get("median", {})
    wall_med = med_entry.get("value") if isinstance(med_entry, dict) else med_entry

    scale_to_m = getattr(scale_bundle, "scale_to_meters", 1.0)
    wall_mm = None
    if wall_med and wall_med > 0:
        wall_mm = wall_med * scale_to_m * 1000.0
    details["wall_thickness_mm"] = wall_mm

    if wall_mm is None or not (50.0 <= wall_mm <= 400.0):
        wall_str = f"{wall_mm:.1f}" if wall_mm is not None else "None"
        issues.append(PreflightIssue(
            gate="G4_wall_thickness",
            severity="block",
            message=f"Wall thickness ({wall_str} mm) is outside the plausible architectural range [50, 400] mm.",
            details={"wall_thickness_mm": wall_mm, "raw_value": wall_med, "unit": unit_name},
        ))

    # --- G5 — Extent plausible ---
    ext = (tolerance_bundle or {}).get("drawing_extent", {})
    diag_entry = ext.get("diagonal", {})
    diag_raw = diag_entry.get("value") if isinstance(diag_entry, dict) else diag_entry
    diag_m = None
    if diag_raw and diag_raw > 0:
        diag_m = diag_raw * scale_to_m
    details["extent_diagonal_m"] = diag_m

    if diag_m is None or not (3.0 <= diag_m <= 200.0):
        extent_str = f"{diag_m:.1f}" if diag_m is not None else "None"
        issues.append(PreflightIssue(
            gate="G5_extent",
            severity="block",
            message=f"Drawing extent ({extent_str} m) is outside the house-scale range [3, 200] m.",
            details={"extent_diagonal_m": diag_m, "raw_value": diag_raw, "unit": unit_name},
        ))

    # --- G6 — Dominated by single junk layer ---
    total_entities = 0
    layer_counts: Dict[str, int] = {}
    for layer_name, cls in (layer_classifications or {}).items():
        c = cls.get("entity_count", 0)
        if c > 0:
            layer_counts[layer_name] = c
            total_entities += c

    dominator = None
    if total_entities > 0:
        for layer_name, c in layer_counts.items():
            # Ignore layers that ARE wall layers
            if layer_name in wall_layers:
                continue
            ratio = c / total_entities
            if ratio > 0.70:
                dominator = (layer_name, ratio, c)
                break

    if dominator:
        issues.append(PreflightIssue(
            gate="G6_domination",
            severity="block",
            message=f"Drawing is dominated by non-wall layer '{dominator[0]}' ({dominator[1]*100:.1f}% of all entities). "
                    f"This is likely not an architectural floor plan.",
            details={"layer": dominator[0], "ratio": dominator[1], "entity_count": dominator[2]},
        ))

    # --- Compute readiness score ---
    # Weight each gate; block failures zero the score
    block_failures = [i for i in issues if i.severity == "block"]
    if block_failures:
        readiness = 0.0
    else:
        # All gates pass — compute a soft score for ranking
        readiness = 1.0
        # Reduce score for borderline values
        if wall_mm is not None and (wall_mm < 80 or wall_mm > 300):
            readiness -= 0.1
        if diag_m is not None and (diag_m < 5 or diag_m > 100):
            readiness -= 0.1
        if wall_entity_count < 50:
            readiness -= 0.1
        readiness = max(0.0, readiness)

    # --- Summary ---
    if block_failures:
        first = block_failures[0]
        summary = f"REJECTED — {first.message}"
    else:
        summary = f"OK — drawing looks like a valid floor plan (readiness {readiness:.2f})"

    return PreflightReport(
        passed=(len(block_failures) == 0),
        issues=issues,
        readiness_score=readiness,
        summary=summary,
    )


def check_geometry_sanity(house2d_data: Dict[str, Any]) -> PreflightReport:
    """
    Preflight gate G7 — Geometry Sanity Check.
    Runs after geometry extraction and house2d assembly.
    Verifies:
    1. Total wall count >= 20
    2. Total room count >= 2
    3. Junk wall ratio <= 0.10 (0, DIM, DEFPOINTS, HATCH, FURNITURE, ELE, TREE)
    4. All rooms have positive area (> 0)
    """
    issues: List[PreflightIssue] = []
    
    b_comps = (house2d_data or {}).get("building_components", {})
    walls = b_comps.get("walls", [])
    rooms = b_comps.get("rooms", [])

    wall_count = len(walls)
    room_count = len(rooms)

    # 1. Wall count check
    if wall_count < 20:
        issues.append(PreflightIssue(
            gate="G7_wall_count",
            severity="block",
            message=f"Too few walls extracted ({wall_count}). Minimum required is 20.",
            details={"wall_count": wall_count}
        ))

    # 2. Room count check
    if room_count < 2:
        issues.append(PreflightIssue(
            gate="G7_room_count",
            severity="block",
            message=f"Too few rooms extracted ({room_count}). Minimum required is 2.",
            details={"room_count": room_count}
        ))

    # 3. Junk wall ratio check
    junk_kws = ["0", "DIM", "DEFPOINTS", "HATCH", "FURNITURE", "FURINTURE", "ELE", "TREE"]
    junk_count = 0
    for w in walls:
        prov = w.get("provenance", {})
        layer = (prov.get("source_layer") or prov.get("layer") or "WALL").upper()
        if layer == "0" or any(kw in layer for kw in ["DIM", "DEFPOINTS", "HATCH", "FURNITURE", "FURINTURE", "ELE", "TREE"]):
            junk_count += 1

    junk_ratio = (junk_count / wall_count) if wall_count > 0 else 1.0
    if junk_ratio > 0.10:
        issues.append(PreflightIssue(
            gate="G7_junk_walls",
            severity="block",
            message=f"Junk wall ratio ({junk_ratio * 100:.1f}%) exceeds maximum allowed threshold of 10.0%.",
            details={"junk_count": junk_count, "total_walls": wall_count, "junk_ratio": junk_ratio}
        ))

    # 4. Room area check
    invalid_rooms = [r for r in rooms if r.get("area", 0.0) <= 0]
    if invalid_rooms:
        issues.append(PreflightIssue(
            gate="G7_invalid_room_area",
            severity="block",
            message=f"{len(invalid_rooms)} rooms have non-positive area.",
            details={"invalid_room_ids": [r.get("room_id") for r in invalid_rooms]}
        ))

    block_failures = [i for i in issues if i.severity == "block"]
    passed = len(block_failures) == 0

    if passed:
        summary = f"OK — Geometry sanity passed (walls={wall_count}, rooms={room_count}, junk_ratio={junk_ratio*100:.1f}%)"
    else:
        summary = f"REJECTED — {block_failures[0].message}"

    return PreflightReport(
        passed=passed,
        issues=issues,
        readiness_score=1.0 if passed else 0.0,
        summary=summary
    )

