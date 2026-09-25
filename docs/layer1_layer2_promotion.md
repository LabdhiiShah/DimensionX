# Layer 1, Layer 2 & Layer 3 Reconstruction Pipeline Architecture

## Overview
Non-layer wall promotion is a conservative, multi-signal audit mechanism operating in Layer 2. Its primary function is to identify linear line segments on non-`WALL` layers (such as structural `BEAM_FRAME` or layer `0` elements) that exhibit strong geometric evidence of being architectural walls. Layer 3 Scale Resolution determines unit scale factors and standard unit names from multi-signal evidence.

> [!IMPORTANT]
> **Scope Disclaimer**: Layer 2 promotion and Layer 3 scale resolution identify plausible wall candidates and physical drawing unit scale. They do **NOT** create final walls, perform topological centerline extraction, or build room polygons.

---

## Architecture & Signal Pipeline

### 1. `PromotionConfig`
All promotion parameters, geometric tolerances, and score weights are centralized in `PromotionConfig` and loaded from `config/promotion.yaml`:
- `min_length_factor`: `1.5` (Threshold = `1.5 * median_wall_thickness`)
- `parallel_angle_tol_deg`: `5.0°` (Maximum angular deviation for parallel partner matching)
- `thickness_match_rel_tol`: `0.35` (35% relative tolerance on nominal wall thickness)
- `min_overlap_ratio`: `0.10` (10% minimum 1D projected overlap ratio)
- `min_connectivity`: `1` (Minimum candidate network neighbor count)
- `min_promotion_score`: `0.45` (Minimum combined score required for promotion)
- `fragment_density_threshold`: `0.50` (Threshold ratio of short entities triggering fragment density capping)
- `min_layer_confidence_for_role`: `0.65` (Minimum confidence required for role-based promotion without strict geometry)
- `structural_requires_geometry_agreement`: `true` (Enforces wall anchor or thickness match for structural segments)
- `weights`: `length_weight: 0.30`, `parallel_weight: 0.40`, `connectivity_weight: 0.20`, `layer_role_weight: 0.10` (Sum = `1.0`)

---

### 2. Part A1: Fragment-Density Skip Rule & Rescue Criteria
Computes $\text{fragment\_ratio} = \frac{\text{short entities count}}{\text{total layer entity count}}$.
- If $\text{fragment\_ratio} \ge 0.50$, role confidence derived from geometry is capped at $0.30$.
- If $\text{fragment\_ratio} \ge 0.90$, all segments on the layer are skipped by default unless rescued by meeting ALL rescue criteria:
  1. Has a valid parallel partner on a `WALL`-role layer.
  2. Perpendicular offset matches nominal wall thickness within tolerance.
  3. Overlap ratio $\ge \text{cfg.min\_overlap\_ratio}$.
  4. Composite promotion score $\ge \text{cfg.min\_promotion\_score} + 0.15$.

---

### 3. Part A2: Role Confidence Floor & Conflict Gating
- Top candidate role confidence must be $\ge 0.65$ (`min_layer_confidence_for_role`).
- If top confidence $< 0.65$ or if a signal conflict exists (`conflict == true`), role-based promotion is withheld; candidate segments must satisfy **STRICT** geometric criteria (valid parallel partner AND length $\ge$ threshold AND score $\ge 0.45$).
- **FORBIDDEN Role** (`DIMENSION`, `ANNOTATION`, `HATCH`, `ELECTRICAL`, `FURNITURE`, `SITE`): Rejected immediately.

---

### 4. Part A3: Structural Layer Promotion Guard
Segments on `STRUCTURAL` layers are promoted only if they have a parallel partner on a `WALL` layer or match nominal wall thickness within tolerance. Promoted structural segments are recorded in both `promoted_segments` and `promoted_structural_segments`.

---

### 5. Part A4: 100% Layer Diagnostics & Warnings Schema
The JSON output from Task 5 provides full auditability:
- `layer_diagnostics`: Maps 100% of classified layers to `entity_count`, `fragment_ratio`, `top_role`, `top_confidence`, `conflict`, `promoted_count`, `skipped_count`, and `warning`.
- `layer_warnings`: List of warning messages covering high fragment density or signal conflict layers.

---

## Layer 3: Scale Resolution (`layer3_scale.py`)

### Evidence Sources & Clustering
Layer 3 scale resolution resolves `units_per_meter` and `unit_name` ("mm", "cm", "m", "inch", "ft"):
1. **DXF Header Variables**: `$INSUNITS` and `$MEASUREMENT` (Weight = 1.0).
2. **DIMENSION Entities**: Ratio between raw geometric distance and text overrides (Weight = 0.8).
3. **TEXT / MTEXT Callout Parsing**: Regex extraction of imperial callouts like `9'3" x 11'0"` (Weight = 0.5).
4. **Wall Thickness Heuristics**: Compares median wall thickness to standard ranges (Weight = 0.3).

Evidence candidates are clustered within a 5% relative tolerance band. The winning cluster's weighted average is mapped to standard units and assigned a confidence rating (`HIGH`, `MEDIUM`, `LOW`, `UNSPECIFIED`).
