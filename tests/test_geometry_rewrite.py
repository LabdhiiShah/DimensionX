import pytest
import ezdxf
from geometry_engine import GeometryEngine

def create_mock_doc(lines, unit_to_meters=1.0, wall_thickness=0.2):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    for line in lines:
        p1, p2, layer = line[0], line[1], line[2] if len(line) > 2 else "WALL"
        msp.add_line(p1, p2, dxfattribs={"layer": layer})
    
    audit_data = {
        "scale_calibration": {"scale_value_to_meters": unit_to_meters},
        "tolerance_bundle": {"wall_thickness_stats": {"median": {"value": wall_thickness}}}
    }
    return doc, audit_data

def test_single_wall_pair_detected():
    lines = [
        ((0.0, 0.0), (4.0, 0.0), "WALL"),
        ((0.0, 0.2), (4.0, 0.2), "WALL")
    ]
    doc, audit_data = create_mock_doc(lines, unit_to_meters=1.0, wall_thickness=0.2)
    engine = GeometryEngine(doc, audit_data)
    results = engine.extract_wall_centerlines_and_boundaries()
    
    assert len(results["planar_edges"]) == 1
    wall = results["planar_edges"][0]
    assert abs(wall["thickness"] - 0.2) < 0.05

def test_perpendicular_lines_not_walls():
    lines = [
        ((0.0, 0.0), (4.0, 0.0), "WALL"),
        ((0.0, 0.0), (0.0, 4.0), "WALL")
    ]
    doc, audit_data = create_mock_doc(lines, unit_to_meters=1.0, wall_thickness=0.2)
    engine = GeometryEngine(doc, audit_data)
    results = engine.extract_wall_centerlines_and_boundaries()
    
    assert len(results["planar_edges"]) == 0

def test_rectangle_room():
    lines = [
        # Bottom wall pair
        ((0.0, 0.0), (5.0, 0.0), "WALL"),
        ((0.2, 0.2), (4.8, 0.2), "WALL"),
        # Top wall pair
        ((0.0, 4.0), (5.0, 4.0), "WALL"),
        ((0.2, 3.8), (4.8, 3.8), "WALL"),
        # Left wall pair
        ((0.0, 0.0), (0.0, 4.0), "WALL"),
        ((0.2, 0.2), (0.2, 3.8), "WALL"),
        # Right wall pair
        ((5.0, 0.0), (5.0, 4.0), "WALL"),
        ((4.8, 0.2), (4.8, 3.8), "WALL"),
    ]
    doc, audit_data = create_mock_doc(lines, unit_to_meters=1.0, wall_thickness=0.2)
    engine = GeometryEngine(doc, audit_data)
    results = engine.extract_wall_centerlines_and_boundaries()
    
    assert len(results["planar_edges"]) == 4
    assert len(results["room_polygons"]) == 1
    room = results["room_polygons"][0]
    assert room["area"] > 10.0
