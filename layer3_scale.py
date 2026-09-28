"""
Layer 3 Scale Resolution Module (Task 6 - ScaleBundle & Scale Resolution)
========================================================================
Resolves DXF scale factor and unit name by testing each candidate unit
against physical plausibility (wall thickness primary, extent secondary, $INSUNITS bonus).
"""

import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class ScaleBundle:
    unit_name: str
    units_per_meter: float
    scale_to_meters: float
    confidence: str
    source: str
    notes: List[str] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def resolve_scale(
    doc: Any = None,
    tolerance_bundle: Optional[Dict[str, Any]] = None,
    layer_classifications: Optional[Dict[str, Any]] = None
) -> ScaleBundle:
    """
    Resolve drawing units by testing each candidate against physical plausibility.
    Returns ScaleBundle with unit_name, units_per_meter, scale_to_meters, confidence, source, notes.
    """
    # Step 1 — Gather evidence
    wall_med = None
    if tolerance_bundle:
        wt_stats = tolerance_bundle.get("wall_thickness_stats", {})
        med_entry = wt_stats.get("median", {})
        wall_med = med_entry.get("value") if isinstance(med_entry, dict) else med_entry

    extent_diagonal = None
    if tolerance_bundle:
        ext = tolerance_bundle.get("drawing_extent", {})
        extent_diagonal = ext.get("diagonal", {}).get("value") if isinstance(ext.get("diagonal"), dict) else None
        if extent_diagonal is None:
            w_val = ext.get("width", {}).get("value") if isinstance(ext.get("width"), dict) else ext.get("width")
            h_val = ext.get("height", {}).get("value") if isinstance(ext.get("height"), dict) else ext.get("height")
            if w_val and h_val:
                try:
                    extent_diagonal = math.hypot(float(w_val), float(h_val))
                except Exception:
                    pass

    header_insunits = None
    if doc is not None and hasattr(doc, "header"):
        try:
            header_insunits = doc.header.get("$INSUNITS", None)
        except Exception:
            header_insunits = None

    # Step 2 — Define candidate units (units_per_meter = how many of THIS unit = 1 meter)
    CANDIDATES = [
        {"unit_name": "mm",      "units_per_meter": 1000.0,  "scale_to_meters": 0.001},
        {"unit_name": "cm",      "units_per_meter": 100.0,   "scale_to_meters": 0.01},
        {"unit_name": "inches",  "units_per_meter": 39.3701, "scale_to_meters": 0.0254},
        {"unit_name": "feet",    "units_per_meter": 3.28084, "scale_to_meters": 0.3048},
        {"unit_name": "meters",  "units_per_meter": 1.0,     "scale_to_meters": 1.0},
    ]

    # Step 3 — Plausibility checks
    results = []
    for c in CANDIDATES:
        plausible = True
        reasons = []

        # Wall thickness check (PRIMARY)
        wall_mm = None
        if wall_med is not None and wall_med > 0:
            wall_mm = wall_med * c["scale_to_meters"] * 1000.0  # mm
            if 50.0 <= wall_mm <= 500.0:
                reasons.append(f"wall_thickness {wall_med:.2f} {c['unit_name']} = {wall_mm:.1f} mm ✓")
            else:
                reasons.append(f"wall_thickness {wall_med:.2f} {c['unit_name']} = {wall_mm:.1f} mm ✗ (outside 50-500 mm)")
                plausible = False
        else:
            reasons.append("wall_thickness unknown — skipping check")

        # Extent check (secondary)
        extent_m = None
        if extent_diagonal is not None and extent_diagonal > 0:
            extent_m = extent_diagonal * c["scale_to_meters"]
            if 2.0 <= extent_m <= 500.0:
                reasons.append(f"extent {extent_diagonal:.1f} {c['unit_name']} = {extent_m:.1f} m ✓")
            else:
                reasons.append(f"extent {extent_diagonal:.1f} {c['unit_name']} = {extent_m:.1f} m ✗ (outside 2-500 m)")
                # extent is a weaker signal, don't disqualify — just note

        # Header bonus
        header_match = False
        if header_insunits is not None:
            # INSUNITS: 1=inches, 2=feet, 4=mm, 5=cm, 6=m
            insunits_map = {1: "inches", 2: "feet", 4: "mm", 5: "cm", 6: "meters"}
            expected = insunits_map.get(header_insunits)
            if expected == c["unit_name"]:
                header_match = True
                reasons.append(f"$INSUNITS={header_insunits} matches {c['unit_name']} ✓")

        # Candidate score
        score = 0.0
        if wall_med and 50.0 <= (wall_med * c["scale_to_meters"] * 1000.0) <= 500.0:
            score += 1.0
        if extent_m and 2.0 <= extent_m <= 500.0:
            score += 0.4
        if header_match:
            score += 0.3

        results.append({
            "unit_name": c["unit_name"],
            "units_per_meter": c["units_per_meter"],
            "scale_to_meters": c["scale_to_meters"],
            "plausible": plausible,
            "score": score,
            "reasons": reasons,
            "wall_mm": wall_mm,
            "extent_m": extent_m,
        })

    def _safe_print(msg: str) -> None:
        try:
            print(msg)
        except UnicodeEncodeError:
            safe_msg = msg.replace("✓", "[OK]").replace("✗", "[X]")
            print(safe_msg.encode('ascii', errors='replace').decode('ascii'))

    # Step 4 — Choose best
    plausible_candidates = [r for r in results if r["plausible"]]
    if not plausible_candidates:
        # Nothing plausible — this is an ERROR, not a default
        _safe_print("[ScaleResolver] ERROR — no plausible unit candidate:")
        for r in results:
            _safe_print(f"  {r['unit_name']}: score={r['score']:.2f}")
            for reason in r["reasons"]:
                _safe_print(f"    {reason}")
        # Return UNSPECIFIED — do not invent a value
        return ScaleBundle(
            unit_name="UNSPECIFIED",
            units_per_meter=1.0,
            scale_to_meters=1.0,
            confidence="UNSPECIFIED",
            source="no_plausible_candidate",
            notes=["All unit candidates rejected by plausibility checks — drawing units unknown"],
            candidates=results,
            evidence=["All unit candidates rejected by plausibility checks — drawing units unknown"]
        )

    plausible_candidates.sort(key=lambda r: r["score"], reverse=True)
    chosen = plausible_candidates[0]

    # Confidence based on margin
    if len(plausible_candidates) == 1:
        confidence = "HIGH"
    elif chosen["score"] - plausible_candidates[1]["score"] >= 0.4:
        confidence = "HIGH"
    elif chosen["score"] - plausible_candidates[1]["score"] >= 0.2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Step 5 — Log the decision
    def _safe_print(msg: str) -> None:
        try:
            print(msg)
        except UnicodeEncodeError:
            safe_msg = msg.replace("✓", "[OK]").replace("✗", "[X]")
            print(safe_msg.encode('ascii', errors='replace').decode('ascii'))

    _safe_print("[ScaleResolver] Unit candidates:")
    for r in results:
        mark = "→ CHOSEN" if r is chosen else ""
        _safe_print(f"  {r['unit_name']:8s} score={r['score']:.2f} plausible={r['plausible']} {mark}")
        for reason in r["reasons"]:
            _safe_print(f"      {reason}")
    _safe_print(f"[ScaleResolver] Decision: {chosen['unit_name']} (confidence={confidence})")

    all_reasons = [r for reason_list in [c["reasons"] for c in results] for r in reason_list]

    return ScaleBundle(
        unit_name=chosen["unit_name"],
        units_per_meter=chosen["units_per_meter"],
        scale_to_meters=chosen["scale_to_meters"],
        confidence=confidence,
        source="plausibility_vote",
        notes=all_reasons,
        candidates=results,
        evidence=all_reasons
    )
