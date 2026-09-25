# Changelog

## [1.2.0] - 2026-09-25 - Layer 1 & 2 Non-Layer Promotion Hardening & Layer 3 Scale Resolution

### Added
- **Part A1 Fragment-Density Skip Rule & Rescue Criteria**:
  - Implemented `fragment_density_threshold: 0.50` gating to cap geometry role confidence at 0.30 on high-fragment layers.
  - Implemented 0.90 fragment density skip rule with strict rescue criteria (requires WALL layer parallel partner, matching thickness offset, overlap ratio, and elevated promotion score).
- **Part A2 Role Confidence Floor & Conflict Gating**:
  - Added `min_layer_confidence_for_role: 0.65` floor. Roles below 0.65 or with signal conflict are treated as unconfirmed and gated behind strict geometry checks.
- **Part A3 Structural Layer Promotion Guard**:
  - Enforced `structural_requires_geometry_agreement` on `STRUCTURAL` layers and added dedicated `promoted_structural_segments` sub-list in JSON report.
- **Part A4 100% Layer Diagnostics & Layer Warnings Schema**:
  - Added `layer_diagnostics` covering 100% of classified layers and `layer_warnings` collecting fragment density and conflict warning messages.
- **Part B Layer 3 Scale Resolution (`layer3_scale.py`)**:
  - Created `Layer3Scale` module featuring `ScaleBundle`, `ScaleCandidate`, and `ScaleConfig`.
  - Implemented evidence extraction from `$INSUNITS`, `$MEASUREMENT`, `DIMENSION` entity overrides, `TEXT/MTEXT` dimension callout regex, and wall thickness heuristics.
  - Added 5% relative tolerance evidence clustering to resolve `units_per_meter`, `unit_name`, and `confidence`.
  - Added `task_6_scale_resolution` block to `layer1_layer2_report.json` and updated `tolerance_bundle.scale`.
- **Part C Comprehensive Unit, Property & Regression Test Suite**:
  - Implemented unit tests for A1–A3, B1–B5, property tests, and regression assertions in `tests/test_promotion.py`.

### Verified
- **Part D Acceptance Criteria**:
  - `sample1.dxf`: Promoted non-wall count = 6 ($\le 15$).
  - `sample2.dxf`: Promoted non-wall count = 17 ($\le 25$).
  - 0 promoted segments violate `promotion_threshold_used.value`.
  - `ELWIN` fragment density warning present in `sample2.dxf` report.
  - `task_6_scale_resolution` block present and valid for both sample files.
