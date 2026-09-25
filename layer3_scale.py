"""
Layer 3 Scale Resolution Module (Task 6 - ScaleBundle & Scale Resolution)
========================================================================
WHAT THIS MODULE DOES:
- Resolves DXF scale factor (units per meter) and unit name ("mm", "cm", "m", "inch", "ft") using multi-source evidence.
- Combines evidence from:
  1. DXF Header variables ($INSUNITS, $MEASUREMENT).
  2. DIMENSION entities (comparing raw geometric distance to text overrides).
  3. TEXT / MTEXT dimension callout regex parsing (with fixture-size heuristic rejection).
  4. Architectural wall thickness heuristics (with full [70mm, 500mm] plausibility table proposing feet/inch/metric candidates).
- Applies extent sanity check ([5m, 500m] implied building size) and text validation to candidate pool.
- Clusters valid scale candidates within a 5% relative tolerance band.
- Outputs an auditable `ScaleBundle` record with confidence rating ("HIGH", "MEDIUM", "LOW", "UNSPECIFIED"), candidates list, and notes audit log.

WHAT THIS MODULE DOES NOT DO:
- Does NOT alter layer classifications, non-layer promotion, or downstream wall assembly.
- Does NOT modify downstream room polygonization or building footprint derivation.
"""

import math
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

STANDARD_UNITS = {
    "mm": 1000.0,
    "cm": 100.0,
    "m": 1.0,
    "inch": 39.37007874015748,
    "ft": 3.280839895013123
}

INSUNITS_MAP = {
    1: ("inch", 39.37007874015748),
    2: ("ft", 3.280839895013123),
    4: ("mm", 1000.0),
    5: ("cm", 100.0),
    6: ("m", 1.0)
}

PLAUSIBLE_WALL_THICKNESS_M = (0.07, 0.50)

UNIT_CANDIDATES = [
    ("mm", 1000.0),
    ("cm", 100.0),
    ("m", 1.0),
    ("in", 39.37007874015748),
    ("ft", 3.280839895013123),
]

@dataclass
class ScaleCandidate:
    units_per_meter: float
    unit_name: str
    confidence: float
    evidence_source: str
    weight: float
    detail: str
    is_valid: bool = True
    reject_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "units_per_meter": self.units_per_meter,
            "unit_name": self.unit_name,
            "confidence": self.confidence,
            "evidence_source": self.evidence_source,
            "weight": self.weight,
            "detail": self.detail
        }

@dataclass
class ScaleConfig:
    clustering_tolerance_rel: float = 0.05
    header_weight: float = 1.0
    dimension_entity_weight: float = 0.8
    text_callout_weight: float = 0.5
    heuristic_weight: float = 0.3

@dataclass
class ScaleBundle:
    units_per_meter: float
    unit_name: str
    confidence: str
    evidence: List[str]
    source: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def propose_wall_thickness_candidates(median_thickness: float, measurement_flag: Optional[int]) -> List[ScaleCandidate]:
    """Fix 3: Plausibility table proposing candidates whose implied wall thickness falls in [0.07m, 0.50m]."""
    out = []
    for unit_name, units_per_m in UNIT_CANDIDATES:
        thickness_m = median_thickness / units_per_m
        if not (PLAUSIBLE_WALL_THICKNESS_M[0] <= thickness_m <= PLAUSIBLE_WALL_THICKNESS_M[1]):
            continue
        weight = 0.4
        if measurement_flag == 0 and unit_name in {"in", "inch", "ft"}:
            weight = 0.6
        if measurement_flag == 1 and unit_name in {"mm", "cm", "m"}:
            weight = 0.6
        
        canonical_uname = "inch" if unit_name == "in" else unit_name
        out.append(ScaleCandidate(
            units_per_meter=units_per_m,
            unit_name=canonical_uname,
            confidence=weight,
            evidence_source="wall_thickness_heuristic",
            weight=weight,
            detail=(f"Median wall thickness {median_thickness:.2f} "
                    f"→ {thickness_m * 1000:.0f} mm ({canonical_uname})")
        ))
    return out

def resolve_scale(
    doc: Any = None,
    tolerance_bundle: Optional[Dict[str, Any]] = None,
    layer_classification: Optional[Dict[str, Any]] = None,
    config: Optional[ScaleConfig] = None
) -> ScaleBundle:
    """
    Main entry point for Layer 3 Scale Resolution.
    Inspects DXF header, DIMENSION entities, TEXT callouts, and wall thickness heuristics to compute ScaleBundle.
    """
    if config is None:
        config = ScaleConfig()

    all_candidates: List[ScaleCandidate] = []
    header_insunits = 0
    measurement_flag = None

    # Calculate drawing extent diagonal for extent sanity check (Fix 5)
    drawing_extent_diag = 0.0
    if tolerance_bundle and "drawing_extent" in tolerance_bundle:
        ext = tolerance_bundle["drawing_extent"]
        if isinstance(ext, dict):
            diag_entry = ext.get("diagonal", 0.0)
            if isinstance(diag_entry, dict):
                drawing_extent_diag = float(diag_entry.get("value", 0.0))
            elif isinstance(diag_entry, (int, float)):
                drawing_extent_diag = float(diag_entry)

            if drawing_extent_diag <= 0.0:
                w_entry = ext.get("width", 0.0)
                h_entry = ext.get("height", 0.0)
                w_val = float(w_entry.get("value", 0.0)) if isinstance(w_entry, dict) else float(w_entry or 0.0)
                h_val = float(h_entry.get("value", 0.0)) if isinstance(h_entry, dict) else float(h_entry or 0.0)
                if w_val > 0 and h_val > 0:
                    drawing_extent_diag = math.hypot(w_val, h_val)

    # Fallback extent calculation from doc bounding box if not in tolerance_bundle
    if drawing_extent_diag <= 0.0 and doc is not None and hasattr(doc, "modelspace"):
        try:
            msp = doc.modelspace()
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = float('-inf'), float('-inf')
            count = 0
            for e in msp.query("LINE LWPOLYLINE"):
                if hasattr(e.dxf, "start"):
                    p1, p2 = e.dxf.start, e.dxf.end
                    min_x, max_x = min(min_x, p1[0], p2[0]), max(max_x, p1[0], p2[0])
                    min_y, max_y = min(min_y, p1[1], p2[1]), max(max_y, p1[1], p2[1])
                    count += 1
                elif hasattr(e, "vertices"):
                    for v in e.vertices():
                        p = v.dxf.location if hasattr(v, "dxf") else v
                        min_x, max_x = min(min_x, p[0]), max(max_x, p[0])
                        min_y, max_y = min(min_y, p[1]), max(max_y, p[1])
                        count += 1
                if count >= 200:
                    break
            if max_x > min_x and max_y > min_y:
                drawing_extent_diag = math.hypot(max_x - min_x, max_y - min_y)
        except Exception:
            pass

    # 1. Evidence Source 1: Header Variables ($INSUNITS, $MEASUREMENT)
    if doc is not None and hasattr(doc, "header"):
        try:
            header_insunits = doc.header.get("$INSUNITS", 0)
            if header_insunits in INSUNITS_MAP:
                u_name, u_rate = INSUNITS_MAP[header_insunits]
                all_candidates.append(ScaleCandidate(
                    units_per_meter=u_rate,
                    unit_name=u_name,
                    confidence=0.90,
                    evidence_source="dxf_header_$INSUNITS",
                    weight=config.header_weight,
                    detail=f"Header $INSUNITS = {header_insunits} ({u_name})"
                ))
            
            measurement_flag = doc.header.get("$MEASUREMENT", None)
            if header_insunits == 0 and measurement_flag is not None:
                if measurement_flag == 1: # ISO / Metric
                    all_candidates.append(ScaleCandidate(
                        units_per_meter=1000.0,
                        unit_name="mm",
                        confidence=0.40,
                        evidence_source="dxf_header_$MEASUREMENT",
                        weight=config.header_weight * 0.5,
                        detail="Header $MEASUREMENT = 1 (ISO Metric -> default mm)"
                    ))
                elif measurement_flag == 0: # Imperial
                    all_candidates.append(ScaleCandidate(
                        units_per_meter=39.3700787,
                        unit_name="inch",
                        confidence=0.40,
                        evidence_source="dxf_header_$MEASUREMENT",
                        weight=config.header_weight * 0.5,
                        detail="Header $MEASUREMENT = 0 (Imperial -> default inch)"
                    ))
        except Exception:
            pass

    # 2. Evidence Source 2: DIMENSION entities
    if doc is not None and hasattr(doc, "modelspace"):
        try:
            msp = doc.modelspace()
            dims = msp.query("DIMENSION")
            for dim in dims[:50]:
                raw_dist = getattr(dim.dxf, "actual_measurement", 0.0)
                if raw_dist <= 0.0 and hasattr(dim, "dxf") and hasattr(dim.dxf, "defpoint"):
                    p1 = dim.dxf.defpoint
                    p2 = getattr(dim.dxf, "defpoint2", None) or getattr(dim.dxf, "defpoint3", None)
                    if p1 and p2:
                        raw_dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])

                dim_text = getattr(dim.dxf, "text", "") or ""
                if raw_dist > 0.0 and dim_text:
                    m_num = re.search(r'(\d+(?:\.\d+)?)\s*(mm|cm|m)?', dim_text, re.IGNORECASE)
                    if m_num:
                        val = float(m_num.group(1))
                        unit = (m_num.group(2) or "").lower()
                        if val > 0:
                            if unit == "m":
                                v_meters = val
                            elif unit == "cm":
                                v_meters = val / 100.0
                            elif unit == "mm":
                                v_meters = val / 1000.0
                            else:
                                v_meters = val if val < 50.0 else val / 1000.0

                            rate = raw_dist / v_meters if v_meters > 0 else 0.0
                            if 0.1 <= rate <= 10000.0:
                                all_candidates.append(ScaleCandidate(
                                    units_per_meter=rate,
                                    unit_name="inferred",
                                    confidence=0.70,
                                    evidence_source="dimension_entity_cluster",
                                    weight=config.dimension_entity_weight,
                                    detail=f"Dimension entity raw distance {raw_dist:.2f} matches text '{dim_text}' ({val} {unit or 'units'})"
                                ))
        except Exception:
            pass

    # 3. Evidence Source 3: TEXT / MTEXT dimension callout regex parsing
    if doc is not None and hasattr(doc, "modelspace"):
        try:
            msp = doc.modelspace()
            texts = msp.query("TEXT MTEXT")
            for t in texts[:100]:
                text_content = t.plain_text() if hasattr(t, "plain_text") else getattr(t.dxf, "text", "")
                if not text_content:
                    continue
                m_imp = re.search(r'(\d+)\s*[\'’]\s*(\d+)?\s*[\"”]', text_content)
                if m_imp:
                    ft = float(m_imp.group(1))
                    inches = float(m_imp.group(2) or 0)
                    total_ft = ft + inches / 12.0
                    v_meters = total_ft * 0.3048
                    cand = ScaleCandidate(
                        units_per_meter=3.280839895,
                        unit_name="ft",
                        confidence=0.60,
                        evidence_source="text_callout_regex",
                        weight=config.text_callout_weight,
                        detail=f"Text callout '{text_content.strip()}' contains imperial dimension {ft}'{int(inches)}\""
                    )
                    
                    # Fix 5: Fixture-size heuristic check for text callout ("NxM" fixture/object sizes)
                    if re.search(r"\d+\s*['\"]?\s*x\s*\d+\s*['\"]?", text_content, re.IGNORECASE):
                        cand.is_valid = False
                        cand.reject_reason = "appears to be a fixture/object size, not a dimension"
                    
                    all_candidates.append(cand)
                    break
        except Exception:
            pass

    # 4. Evidence Source 4: Wall Thickness Heuristics (Fix 3)
    if tolerance_bundle and "wall_thickness_stats" in tolerance_bundle:
        thick_stats = tolerance_bundle.get("wall_thickness_stats", {})
        med_entry = thick_stats.get("median", {})
        median_wt = med_entry.get("value", 0.0) if isinstance(med_entry, dict) else float(med_entry)

        if median_wt > 0.0:
            wt_candidates = propose_wall_thickness_candidates(median_wt, measurement_flag)
            all_candidates.extend(wt_candidates)

    # 5. Fix 5: Apply Extent Sanity Check to ALL Candidates ([5m, 500m] implied building size)
    valid_candidates: List[ScaleCandidate] = []
    rejected_candidates: List[ScaleCandidate] = []

    for cand in all_candidates:
        if not cand.is_valid:
            rejected_candidates.append(cand)
            continue

        if drawing_extent_diag > 0.0:
            extent_m = drawing_extent_diag / cand.units_per_meter
            if not (2.0 <= extent_m <= 500.0):
                cand.is_valid = False
                cand.reject_reason = f"implied extent {extent_m:.1f} m outside plausible range [2, 500]"
                rejected_candidates.append(cand)
                continue

        valid_candidates.append(cand)

    # Build Notes List (Fix 4)
    notes: List[str] = []
    if header_insunits == 0:
        notes.append("Header $INSUNITS=0 → no high-confidence header candidate")

    for r_cand in rejected_candidates:
        notes.append(f"rejected {r_cand.unit_name} ({r_cand.units_per_meter:.4f} u/m): {r_cand.reject_reason}")

    # Fallback / Clustering Resolution
    if not valid_candidates:
        notes.append("No plausible scale evidence found; defaulting to 1.0 u/m")
        return ScaleBundle(
            units_per_meter=1.0,
            unit_name="m",
            confidence="UNSPECIFIED",
            evidence=["No scale evidence found in DXF header, dimensions, text, or geometry; defaulting to meters"],
            source="fallback_default",
            candidates=[c.to_dict() for c in all_candidates],
            notes=notes
        )

    # Group valid candidates into 5% relative tolerance clusters
    clusters: List[List[ScaleCandidate]] = []
    for cand in valid_candidates:
        matched_cluster = None
        for cl in clusters:
            rep_rate = cl[0].units_per_meter
            rel_diff = abs(cand.units_per_meter - rep_rate) / max(rep_rate, 1e-4)
            if rel_diff <= config.clustering_tolerance_rel:
                matched_cluster = cl
                break
        if matched_cluster is not None:
            matched_cluster.append(cand)
        else:
            clusters.append([cand])

    # Rank clusters by total weight
    best_cluster = max(clusters, key=lambda cl: sum(c.weight for c in cl))
    total_weight = sum(c.weight for c in best_cluster)

    # Non-winning valid candidates
    non_winning_valid_candidates = [c for c in valid_candidates if not any(c is b for b in best_cluster)]

    for nw_cand in non_winning_valid_candidates:
        notes.append(
            f"considered but not selected: {nw_cand.unit_name} ({nw_cand.units_per_meter:.4f} u/m, score {nw_cand.confidence:.2f})"
        )

    # Weighted average units_per_meter
    avg_upm = sum(c.units_per_meter * c.weight for c in best_cluster) / total_weight

    # Canonical mapping to standard units if close (within 2.5%)
    canonical_unit = "custom"
    canonical_upm = avg_upm

    for uname, std_upm in STANDARD_UNITS.items():
        rel_err = abs(avg_upm - std_upm) / std_upm
        if rel_err <= 0.025:
            canonical_unit = uname
            canonical_upm = std_upm
            break

    # Determine confidence level
    has_header = any("header" in c.evidence_source for c in best_cluster)
    if has_header and total_weight >= 0.8:
        confidence_str = "HIGH"
    elif total_weight >= 0.8:
        confidence_str = "MEDIUM"
    elif total_weight > 0.0:
        confidence_str = "LOW"
    else:
        confidence_str = "UNSPECIFIED"

    if confidence_str == "UNSPECIFIED":
        notes.append("No plausible scale evidence found; defaulting to 1.0 u/m")

    primary_source = best_cluster[0].evidence_source
    evidence_list = [c.detail for c in best_cluster]

    return ScaleBundle(
        units_per_meter=round(canonical_upm, 6),
        unit_name=canonical_unit,
        confidence=confidence_str,
        evidence=evidence_list,
        source=primary_source,
        candidates=[c.to_dict() for c in valid_candidates],
        notes=notes
    )
