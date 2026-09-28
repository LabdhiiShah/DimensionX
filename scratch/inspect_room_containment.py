"""
Room Polygon & Text Spatial Containment Inspector for sample1.dxf
"""

import ezdxf
import math
from collections import defaultdict
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiLineString
from shapely.ops import unary_union, polygonize
import sys
sys.path.append("d:/end game/haha")
from geometry_engine import GeometryEngine
from dxf_auditor import run_full_audit

doc = ezdxf.readfile("d:/end game/dwg/sample1.dxf")
audit_data = run_full_audit("d:/end game/dwg/sample1.dxf", output_dir="output")

geom_engine = GeometryEngine(doc, audit_data=audit_data)
geom_results = geom_engine.extract_wall_centerlines_and_boundaries()

room_polys = geom_results["room_polygons"]
print(f"Total Macro Room Candidates extracted by GeometryEngine: {len(room_polys)}")

print("\nMacro Room Candidate Details:")
for idx, r in enumerate(room_polys):
    p = r["polygon"]
    b = r["bounds"]
    w = round(b[2]-b[0], 1)
    h = round(b[3]-b[1], 1)
    c = p.centroid
    print(f"  [{r['room_id']}] Area: {r['area']:.1f} | WxH: {w} x {h} | Centroid: ({c.x:.1f}, {c.y:.1f}) | Bounds: ({b[0]:.1f}, {b[1]:.1f}) to ({b[2]:.1f}, {b[3]:.1f})")

print("\n==================================================")
print("INSPECTING ALL TEXT CALLOUTS IN DXF & CONTAINMENT")
print("==================================================")
msp = doc.modelspace()
for e in msp.query('TEXT MTEXT'):
    is_mtext = (e.dxftype() == 'MTEXT')
    txt = e.text if is_mtext else e.dxf.text
    clean_txt = txt.strip()
    pos = (e.dxf.insert[0], e.dxf.insert[1])
    pt = Point(pos)
    
    containing_rooms = []
    nearest_room = None
    min_dist = float('inf')
    
    for r in room_polys:
        p = r["polygon"]
        if p.contains(pt):
            containing_rooms.append((r["room_id"], r["area"]))
        d = p.distance(pt)
        if d < min_dist:
            min_dist = d
            nearest_room = (r["room_id"], d, r["area"])
            
    import re
    clean = re.sub(r'\{[^{}]*\}', '', clean_txt)
    clean = re.sub(r'\\P', ' ', clean).strip()
    print(f"Handle '{e.dxf.handle}': [{e.dxf.layer}] '{clean}' at ({pos[0]:.1f}, {pos[1]:.1f})")
    print(f"  -> Strictly Inside: {containing_rooms}")
    print(f"  -> Nearest Room: {nearest_room}")
