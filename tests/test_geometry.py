"""
Unit and Integration Tests for Geometry Engine (Layer 4)
=========================================================
"""

import sys
import os
import unittest
import ezdxf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from geometry_engine import GeometryEngine

class TestGeometryEngine(unittest.TestCase):
    def test_geometry_engine_init(self):
        doc = ezdxf.new()
        engine = GeometryEngine(doc)
        self.assertGreater(engine.weld_tolerance, 0.0)
        self.assertGreater(engine.min_wall_thickness, 0.0)

    def test_weld_tolerance_scaling_mm(self):
        doc = ezdxf.new()
        audit_mm = {"scale_calibration": {"scale_value_to_meters": 0.001}}
        engine_mm = GeometryEngine(doc, audit_data=audit_mm)
        self.assertEqual(engine_mm.min_wall_thickness, 114.3)
        self.assertEqual(engine_mm.weld_tolerance, 0.25)

    def test_weld_tolerance_scaling_m(self):
        doc = ezdxf.new()
        audit_m = {"scale_calibration": {"scale_value_to_meters": 1.0}}
        engine_m = GeometryEngine(doc, audit_data=audit_m)
        self.assertAlmostEqual(engine_m.min_wall_thickness, 0.115)
        self.assertAlmostEqual(engine_m.weld_tolerance, 0.10)

    def test_extract_wall_lines(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "WALL"})
        msp.add_line((10, 0), (10, 10), dxfattribs={"layer": "WALL"})
        msp.add_line((10, 10), (0, 10), dxfattribs={"layer": "WALL"})
        msp.add_line((0, 10), (0, 0), dxfattribs={"layer": "WALL"})

        audit_data = {
            "scale_calibration": {"scale_value_to_meters": 1.0},
            "geometry_statistics": {"bounding_box": {"width": 20.0, "height": 20.0}},
            "layer_role_classification": {"WALL": {"assigned_role": "WALL"}}
        }
        engine = GeometryEngine(doc, audit_data=audit_data)
        results = engine.extract_wall_centerlines_and_boundaries()
        self.assertIn("planar_edges", results)
        self.assertIn("room_polygons", results)
        self.assertGreaterEqual(len(results["room_polygons"]), 1)

if __name__ == "__main__":
    unittest.main()
