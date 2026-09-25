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
