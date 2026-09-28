"""
CAD-to-3D Architectural Reconstruction Pipeline (House2D-lite Master Orchestrator)
================================================================================
Orchestrates end-to-end DXF audit, geometry extraction, topology graph construction,
room polygonization, aperture hosting, room semantics association, House2D-lite generation,
validation, 2D diagnostic rendering, and markdown reporting.
"""

import sys
import os
import json
import ezdxf

from dxf_auditor import run_full_audit
from geometry_engine import GeometryEngine
from aperture_engine import ApertureEngine
from semantics_engine import SemanticsEngine
from house2d_builder import House2DBuilder
from house2d_lite_builder import House2DLiteBuilder
from validator import House2DValidator
from visualizer_2d import Visualizer2D
from reconstruction_report import generate_reconstruction_report

def run_pipeline(dxf_filepath, output_dir="output"):
    print("=" * 70)
    print("STARTING HOUSE2D-LITE ARCHITECTURAL RECONSTRUCTION PIPELINE")
    print(f"Target DXF File: {dxf_filepath}")
    print("=" * 70)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Audit DXF
    print("\n[Step 1/8] Running DXF Audit...")
    audit_data = run_full_audit(dxf_filepath, output_dir=output_dir)
    
    # Step 2: Geometry & Topology Engine
    print("\n[Step 2/8] Running Geometry & Topology Engine...")
    doc = ezdxf.readfile(dxf_filepath)
    if "tolerance_bundle" not in audit_data:
        try:
            from tolerance_bundle import build_tolerance_bundle
            extracted_lines = []
            for e in doc.modelspace().query('LINE LWPOLYLINE POLYLINE'):
                if e.dxftype() == 'LINE':
                    extracted_lines.append({"p1": (e.dxf.start[0], e.dxf.start[1]), "p2": (e.dxf.end[0], e.dxf.end[1])})
                elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    pts = list(e.get_points('xy'))
                    if len(pts) >= 2:
                        extracted_lines.append({"points": [(p[0], p[1]) for p in pts]})
            tb = build_tolerance_bundle(extracted_lines, audit_data.get("header", {}), audit_data.get("geometry_statistics", {}))
            audit_data["tolerance_bundle"] = tb
        except Exception:
            pass
    from layer3_scale import resolve_scale
    from preflight_check import check_preflight

    tolerance_bundle = audit_data.get("tolerance_bundle", {})
    layer_classifications = audit_data.get("layer_role_classification", {})
    scale_bundle = resolve_scale(doc, tolerance_bundle, layer_classifications)

    # Update scale_calibration in audit_data with scale_bundle result
    audit_data["scale_calibration"] = {
        "scale_value_to_meters": scale_bundle.scale_to_meters,
        "unit_name": scale_bundle.unit_name,
        "scale_source": scale_bundle.source,
        "scale_confidence": scale_bundle.confidence,
        "evidence": scale_bundle.notes
    }

    # Run Preflight Check
    preflight = check_preflight(
        audit_data=audit_data,
        scale_bundle=scale_bundle,
        tolerance_bundle=tolerance_bundle,
        layer_classifications=layer_classifications,
    )

    # Write machine-readable report
    os.makedirs(output_dir, exist_ok=True)
    report_file = os.path.join(output_dir, "preflight_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "passed": preflight.passed,
            "readiness_score": preflight.readiness_score,
            "summary": preflight.summary,
            "issues": [
                {
                    "gate": i.gate,
                    "severity": i.severity,
                    "message": i.message,
                    "details": i.details,
                }
                for i in preflight.issues
            ],
            "input_dxf": dxf_filepath,
        }, f, indent=2)

    # Print human-readable summary
    def _safe_print(msg: str) -> None:
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode('ascii', errors='replace').decode('ascii'))

    _safe_print("\n" + "=" * 70)
    _safe_print("PREFLIGHT CHECK")
    _safe_print("=" * 70)
    _safe_print(preflight.summary)
    if preflight.issues:
        _safe_print("\nIssues:")
        for issue in preflight.issues:
            marker = "[BLOCK]" if issue.severity == "block" else "[WARN]"
            _safe_print(f"  {marker} {issue.gate}: {issue.message}")
    _safe_print("=" * 70 + "\n")

    if not preflight.passed:
        _safe_print("Pipeline aborted — the drawing failed preflight validation.")
        _safe_print(f"See {report_file} for details.")
        sys.exit(2)   # distinct exit code for "drawing rejected"

    geom_engine = GeometryEngine(doc, audit_data=audit_data)
    geom_results = geom_engine.extract_wall_centerlines_and_boundaries()
    
    # Step 3: Semantics Engine (Geometry-First Room Candidate Classification & Ranked Assignment)
    print("\n[Step 3/8] Running Semantics Engine...")
    unit_to_m = audit_data["scale_calibration"]["scale_value_to_meters"]
    semantics_engine = SemanticsEngine(audit_data["room_labels"], unit_to_meters=unit_to_m)
    annotated_rooms, adjacency_graph, unmapped_labels, meaningful_count, semantic_count = semantics_engine.process_room_semantics(
        geom_results["room_polygons"], []
    )
    
    # Step 4: Aperture Detection & Hosting
    print("\n[Step 4/8] Running Aperture Engine (Doors & Windows)...")
    layer_classifications = audit_data.get("layer_role_classification", {})
    aperture_engine = ApertureEngine(
        doc,
        unit_to_meters=audit_data["scale_calibration"]["scale_value_to_meters"],
        layer_classifications=layer_classifications
    )
    doors, windows = aperture_engine.detect_and_host_apertures(geom_results["planar_edges"], room_polygons=annotated_rooms)
    
    # Re-build adjacency graph with hosted doors
    annotated_rooms, adjacency_graph, unmapped_labels, meaningful_count, semantic_count = semantics_engine.process_room_semantics(
        geom_results["room_polygons"], doors
    )

    # Step 5: Assemble Full House2D Schema
    print("\n[Step 5/8] Assembling Full House2D Schema...")
    builder = House2DBuilder(audit_data)
    house2d = builder.build_house2d(geom_results, doors, windows, annotated_rooms, adjacency_graph)
    
    house2d_path = os.path.join(output_dir, "house2d.json")
    with open(house2d_path, "w", encoding="utf-8") as f:
        json.dump(house2d, f, indent=2)
    print(f"[Pipeline] Generated Full House2D Model: {house2d_path}")

    # Step 5B: Run Preflight Geometry Sanity Check (Gate G7)
    from preflight_check import check_geometry_sanity
    g7_report = check_geometry_sanity(house2d)
    _safe_print("\n" + "=" * 70)
    _safe_print("PREFLIGHT GEOMETRY SANITY CHECK (GATE G7)")
    _safe_print("=" * 70)
    _safe_print(g7_report.summary)
    if g7_report.issues:
        _safe_print("\nIssues:")
        for issue in g7_report.issues:
            marker = "[BLOCK]" if issue.severity == "block" else "[WARN]"
            _safe_print(f"  {marker} {issue.gate}: {issue.message}")
    _safe_print("=" * 70 + "\n")

    if not g7_report.passed:
        _safe_print("Pipeline aborted — geometry extraction failed sanity check (Gate G7).")
        sys.exit(3)

    # Step 6: Assemble House2D-lite (Normalized [0,1] Schema for Unity)
    print("\n[Step 6/8] Assembling House2D-lite (Normalized [0,1] Schema)...")
    lite_builder = House2DLiteBuilder(audit_data)
    house2d_lite = lite_builder.build_house2d_lite(geom_results, doors, windows, annotated_rooms, adjacency_graph)
    
    house2d_lite_path = os.path.join(output_dir, "house2d_lite.json")
    with open(house2d_lite_path, "w", encoding="utf-8") as f:
        json.dump(house2d_lite, f, indent=2)
    print(f"[Pipeline] Generated House2D-lite Model: {house2d_lite_path}")
    
    # Step 7: Validate House2D
    print("\n[Step 7/8] Validating House2D Reconstruction Model...")
    validator = House2DValidator(house2d)
    val_report = validator.validate()
    
    val_path = os.path.join(output_dir, "validation.json")
    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(val_report, f, indent=2)
    print(f"[Pipeline] Generated Validation Report: {val_path}")
    
    # Step 8: Visual Diagnostics & Markdown Reporting
    print("\n[Step 8/8] Generating 2D Visual Diagnostics & Reconstruction Report...")
    visualizer = Visualizer2D(house2d, geom_results=geom_results, output_dir=output_dir)
    visualizer.render_all()
    
    generate_reconstruction_report(house2d, val_report, output_dir=output_dir)
    
    # Door connections count
    door_conn_count = len(adjacency_graph.get("connected_pairs", []))
    
    print("\n" + "=" * 70)
    print("RECONSTRUCTION EXECUTION SUMMARY:")
    print(f"Meaningful room candidates: {meaningful_count}")
    print(f"Semantic rooms: {semantic_count}")
    print(f"Unmapped labels: {len(unmapped_labels)} ({unmapped_labels})")
    print(f"Merged candidates: 0")
    print(f"Door connections: {door_conn_count}")
    print(f"Window connections: {len(windows)}")
    print(f"Synthetic rooms created from text: 0")
    print("=" * 70)

if __name__ == "__main__":
    target_dxf = sys.argv[1] if len(sys.argv) > 1 else "d:/end game/dwg/sample1.dxf"
    run_pipeline(target_dxf)
