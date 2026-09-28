"""
Reconstruction Report Generator
===============================
Generates output/reconstruction_report.md summarizing the entire end-to-end 2D architectural reconstruction.
"""

import os

def generate_reconstruction_report(house2d, validation_result, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "reconstruction_report.md")
    
    meta = house2d["metadata"]
    units = house2d["units"]
    comps = house2d["building_components"]
    walls = comps["walls"]
    rooms = comps["rooms"]
    doors = comps["doors"]
    windows = comps["windows"]
    footprint = comps["building_footprint"]
    adj = house2d["room_adjacency"]
    
    md = []
    md.append(f"# Intelligent CAD-to-3D 2D Architectural Reconstruction Report\n")
    md.append(f"**Source File**: `{meta['source_dxf']}`  ")
    md.append(f"**Reconstruction Engine Version**: `{meta['generator']}`  ")
    md.append(f"**Timestamp**: `{meta['created_at']}`\n")
    
    md.append("## Executive Summary")
    md.append("The 2D architectural DXF floor plan was successfully audited, normalized, and reconstructed into a clean, topological, semantically-rich `House2D` model.")
    md.append(f"- **Reconstructed Walls**: `{len(walls)}` topological centerline edges")
    md.append(f"- **Extracted Rooms**: `{len(rooms)}` polygonized room areas")
    md.append(f"- **Hosted Apertures**: `{len(doors)}` doors, `{len(windows)}` windows")
    md.append(f"- **Validation Status**: `{'PASSED' if validation_result['validation_passed'] else 'FAILED'}` ({validation_result['blocking_error_count']} blocking, {validation_result['warning_count']} warnings)\n")

    md.append("## 1. Unit & Scale Calibration")
    md.append(f"- **Calibrated Units**: `{units['unit_name']}`")
    md.append(f"- **Scale-to-Meters Factor**: `{units['scale_to_meters']}`")
    md.append(f"- **Scale Confidence**: `{units['scale_confidence']}` (Source: `{units['scale_source']}`)")
    md.append("### Evidence Chain:")
    for ev in units.get("scale_evidence", []):
        md.append(f"- {ev}")
    md.append("")

    md.append("## 2. Geometry & Topology Reconstruction")
    md.append(f"- **Welded Vertices Count**: `{len(comps['vertices'])}`")
    md.append(f"- **Dynamic Welding Tolerance Used**: `{house2d['diagnostics']['weld_tolerance_used']}` DXF units")
    md.append(f"- **Building Footprint Area**: `{footprint['area']}` sq units (Derivation: `{footprint['derivation_source']}`)\n")
    
    md.append("### Wall Centerlines Summary:")
    md.append("| Wall ID | Class | Length (DXF units) | Nominal Thickness | Status | Confidence |")
    md.append("|---|---|---|---|---|---|")
    for w in walls[:10]:
        md.append(f"| `{w['wall_id']}` | `{w['wall_class']}` | {w['length']:.1f} | {w['thickness']['value']} | {w['status']} | {w['confidence']} |")
    if len(walls) > 10:
        md.append(f"| ... *and {len(walls)-10} more walls* | | | | | |")
    md.append("")

    md.append("## 3. Polygonized Room Reconstruction & Semantics")
    md.append("| Room ID | Semantic Name | Type | Status | Area (sq units) | Parsed DXF Dimensions |")
    md.append("|---|---|---|---|---|---|")
    for r in rooms:
        dims = r.get('parsed_dimensions') or []
        md.append(f"| `{r['room_id']}` | `{r['name']}` | `{r['semantic_type']}` | `{r['status']}` | {r['area']} | {dims} |")
    md.append("")

    md.append("## 4. Room Adjacency & Connectivity")
    md.append(f"- **Adjacent Room Pairs (Shared Boundary)**: `{len(adj['adjacent_pairs'])}`")
    md.append(f"- **Connected Room Pairs (Via Door Aperture)**: `{len(adj['connected_pairs'])}`")
    md.append("")

    md.append("## 5. Aperture Detection & Hosting")
    md.append("| Opening ID | Type | Host Wall | Width | Sill Height | Head Height | Source |")
    md.append("|---|---|---|---|---|---|---|")
    for d in doors:
        md.append(f"| `{d['opening_id']}` | `{d['aperture_type']}` | `{d['host_wall_id']}` | {d['width']} | {d['sill_height']['value']}m | {d['head_height']['value']}m | `{d['source']}` |")
    for w in windows:
        md.append(f"| `{w['opening_id']}` | `{w['aperture_type']}` | `{w['host_wall_id']}` | {w['width']} | {w['sill_height']['value']}m | {w['head_height']['value']}m | `{w['source']}` |")
    md.append("")

    md.append("## 6. Architectural Validation Summary")
    md.append(f"- **Overall Result**: `{'PASSED' if validation_result['validation_passed'] else 'FAILED'}`")
    md.append(f"- **Blocking Errors ({validation_result['blocking_error_count']})**:")
    for err in validation_result['blocking_errors']:
        md.append(f"  - **[{err['category']}]** `{err['code']}`: {err['message']}")
    if not validation_result['blocking_errors']:
        md.append("  - *None! Zero blocking errors.*")
    md.append(f"- **Warnings ({validation_result['warning_count']})**:")
    for wrn in validation_result['warnings']:
        md.append(f"  - **[{wrn['category']}]** `{wrn['code']}`: {wrn['message']}")
    md.append("")

    md.append("## 7. Diagnostic Visualizations")
    md.append("- **Detailed Debug Overlay**: `output/diagnostic_debug.png`")
    md.append("- **Clean Architectural Floor Plan**: `output/diagnostic_clean.png`")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
        
    print(f"[ReconstructionReport] Generated Report: {report_path}")
    return report_path
