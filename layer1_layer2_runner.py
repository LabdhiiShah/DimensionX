"""
Layer 1 (Ingestion) & Layer 2 (Audit) & Layer 3 (Scale) Master Runner
======================================================================
Executes Tasks 1 through 6 on residential DXF floor plans:
1. Block Expansion (block_expander.py)
2. Normalization & Curve-to-Polyline Conversion (normalizer.py)
3. Layer Role Classification as Ranked Evidence (layer_classifier.py)
4. ToleranceBundle Exporter (tolerance_bundle.py)
5. Non-Layer Wall Promotion Debug Inspection (non_layer_promoter.py)
6. Scale Resolution Engine (layer3_scale.py)

Generates:
- output/layer1_layer2_report.json
- output/normalization_debug_overlay.png (Visual verification overlay)
"""

import os
import json
import math
from collections import defaultdict
import ezdxf
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from dxf_auditor import DXFAuditor
from block_expander import expand_blocks
from normalizer import normalize_entities
from layer_classifier import classify_layers_ranked
from tolerance_bundle import build_tolerance_bundle
from non_layer_promoter import inspect_non_layer_promotions
from layer3_scale import resolve_scale

def run_layer1_layer2(dxf_path, output_dir="output"):
    print(f"\n======================================================================")
    print(f"RUNNING LAYER 1 (INGESTION), LAYER 2 (AUDIT), & LAYER 3 (SCALE) ENGINE")
    print(f"Target DXF File: {dxf_path}")
    print(f"======================================================================")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Base DXF Audit
    auditor = DXFAuditor(dxf_path)
    base_audit_data = auditor.run_audit()
    
    # Step 2: Task 1 - Block / INSERT Expansion
    doc = ezdxf.readfile(dxf_path)
    block_expansion_results = expand_blocks(doc)
    expanded_entities = block_expansion_results["expanded_entities"]
    
    print(f"[Task 1] Block Expansion: {block_expansion_results['expanded_insert_count']} INSERTs expanded, max depth = {block_expansion_results['max_nesting_depth']}")

    # Extract line segments from expanded entities for tolerance bundle calculation
    extracted_lines = []
    for item in expanded_entities:
        etype = item["entity_type"]
        if etype == "LINE" and "p1" in item:
            extracted_lines.append(item)
        elif etype == "LWPOLYLINE" and "points" in item and len(item["points"]) >= 2:
            extracted_lines.append(item)

    # Step 3: Task 4 - Structural Statistics as ToleranceBundle
    tolerance_bundle = build_tolerance_bundle(
        extracted_lines, base_audit_data["header"], base_audit_data["geometry_statistics"]
    )
    print(f"[Task 4] ToleranceBundle: weld_tolerance = {tolerance_bundle['weld_tolerance']['value']} ({tolerance_bundle['weld_tolerance']['source']})")

    # Step 4: Task 2 - Entity Normalization (Chord tolerance derived rule)
    normalization_results = normalize_entities(
        expanded_entities, 
        wall_thickness_stats=tolerance_bundle["wall_thickness_stats"],
        extent_stats=tolerance_bundle["drawing_extent"]
    )
    normalized_entities = normalization_results["normalized_entities"]
    print(f"[Task 2] Normalization: Converted {normalization_results['converted_curved_entity_count']} curved entities using chord_tolerance = {normalization_results['chord_tolerance_used']} ({normalization_results['chord_tolerance_source']})")

    # Generate geometry candidate lines for non-layer promotion analysis and fragment density
    raw_wall_lines = []
    layer_entities = defaultdict(list)
    for item in normalized_entities:
        etype = item["entity_type"]
        layer = item["layer"]
        if etype == "LINE" and "p1" in item:
            p1, p2 = item["p1"], item["p2"]
            length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            raw_wall_lines.append({"p1": p1, "p2": p2, "layer": layer, "source_type": "PRIMARY_WALL", "handle": item["handle"]})
            layer_entities[layer].append({"segment_length": length})
        elif etype == "LWPOLYLINE" and "points" in item:
            pts = item["points"]
            for k in range(len(pts) - 1):
                p1, p2 = pts[k], pts[k+1]
                length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                raw_wall_lines.append({"p1": p1, "p2": p2, "layer": layer, "source_type": "PRIMARY_WALL", "handle": item["handle"]})
                layer_entities[layer].append({"segment_length": length})

    # Step 5: Task 3 - Layer Role Classification as Ranked Evidence
    layer_classifications = classify_layers_ranked(
        base_audit_data["layers"],
        base_audit_data["entities"],
        base_audit_data["geometry_statistics"],
        tolerance_bundle=tolerance_bundle,
        layer_entities=layer_entities
    )
    print(f"[Task 3] Ranked Layer Classification completed for {len(layer_classifications)} layers.")

    # Step 6: Task 5 - Non-Layer Wall Promotion Debug Inspector
    promotion_results = inspect_non_layer_promotions(raw_wall_lines, layer_classifications, tolerance_bundle)
    print(f"[Task 5] Non-Layer Wall Promotion: {promotion_results['promoted_non_wall_segments_count']} non-WALL segments promoted.")

    # Step 7: Task 6 - Scale Resolution Engine
    scale_bundle = resolve_scale(doc, tolerance_bundle, layer_classifications)
    print(f"[Task 6] Scale Resolution: units_per_meter = {scale_bundle.units_per_meter} ({scale_bundle.unit_name}), confidence = {scale_bundle.confidence} ({scale_bundle.source})")

    if scale_bundle.confidence != "UNSPECIFIED":
        tolerance_bundle["scale"] = scale_bundle.to_dict()

    # Render Visual Overlay for Task 2 (Normalizer Verification)
    render_normalization_debug_overlay(normalized_entities, output_dir=output_dir)

    report = {
        "file_info": base_audit_data["file_info"],
        "task_1_block_expansion": {
            "expanded_insert_count": block_expansion_results["expanded_insert_count"],
            "max_nesting_depth": block_expansion_results["max_nesting_depth"],
            "circular_references_detected": block_expansion_results["circular_references_detected"] if block_expansion_results["circular_references_detected"] else "none",
            "skipped_dimension_anonymous_blocks_count": block_expansion_results["skipped_dimension_anonymous_blocks_count"]
        },
        "task_2_entity_normalization": {
            "total_normalized_entities_count": len(normalized_entities),
            "converted_curved_entities_count": normalization_results["converted_curved_entity_count"],
            "chord_tolerance_used": normalization_results["chord_tolerance_used"],
            "chord_tolerance_source": normalization_results["chord_tolerance_source"]
        },
        "task_3_ranked_layer_classification": layer_classifications,
        "task_4_tolerance_bundle": tolerance_bundle,
        "task_5_non_layer_wall_promotion": promotion_results,
        "task_6_scale_resolution": scale_bundle.to_dict()
    }

    return report

def render_normalization_debug_overlay(normalized_entities, output_dir="output"):
    """
    Renders visual debug overlay confirming original curved entities vs normalized polylines.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_facecolor('#1e1e1e')

    lines_std = []
    lines_curved = []

    for item in normalized_entities:
        etype = item["entity_type"]
        if etype == "LINE" and "p1" in item:
            lines_std.append([item["p1"], item["p2"]])
        elif etype == "LWPOLYLINE" and "points" in item and len(item["points"]) >= 2:
            pts = item["points"]
            seg_list = [[pts[k], pts[k+1]] for k in range(len(pts) - 1)]
            if item.get("converted_from_curved"):
                lines_curved.extend(seg_list)
            else:
                lines_std.extend(seg_list)

    if lines_std:
        lc_std = LineCollection(lines_std, colors='#3498db', linewidths=0.8, alpha=0.7, label='Standard Polyline/Line')
        ax.add_collection(lc_std)
    if lines_curved:
        lc_curved = LineCollection(lines_curved, colors='#e74c3c', linewidths=1.5, alpha=0.9, label='Normalized Polyline (from Arc/Circle/Spline)')
        ax.add_collection(lc_curved)

    ax.autoscale()
    ax.set_aspect('equal')
    ax.set_title("Layer 1/Layer 2 Normalization Verification Overlay", color='white', fontsize=12)
    ax.legend(loc='upper right', facecolor='#2c3e50', edgecolor='none', labelcolor='white')
    ax.axis('off')

    overlay_path = os.path.join(output_dir, "normalization_debug_overlay.png")
    plt.savefig(overlay_path, dpi=200, bbox_inches='tight', facecolor='#1e1e1e')
    plt.close()
    print(f"[Visualizer] Generated Normalization Verification Overlay: {overlay_path}")

def main():
    dxf_files = ["d:/end game/dwg/sample1.dxf", "d:/end game/dwg/sample2.dxf"]
    combined_reports = {}

    for dxf_file in dxf_files:
        if os.path.exists(dxf_file):
            fname = os.path.basename(dxf_file)
            report = run_layer1_layer2(dxf_file)
            combined_reports[fname] = report

    report_path = os.path.join("output", "layer1_layer2_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(combined_reports, f, indent=2)
    print(f"\n[Master Runner] Generated Master Verification Report: {report_path}")

if __name__ == "__main__":
    main()
