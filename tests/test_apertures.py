"""
Unit and Integration Tests for Aperture Detection Engine (Layer 4)
===================================================================
"""

import sys
import os
import unittest
import ezdxf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aperture_engine import ApertureEngine

class TestApertureEngine(unittest.TestCase):
    def test_door_detected_on_door_layer(self):
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_arc(center=(10, 10), radius=1.0, start_angle=0, end_angle=90, dxfattribs={"layer": "DOOR"})
        engine = ApertureEngine(doc, unit_to_meters=1.0)
        doors = engine._detect_doors()
        self.assertEqual(len(doors), 1)

    def test_door_not_detected_on_furniture_layer(self):
        """Door overcounting bug check: Arcs on furniture layer must NOT be detected as doors."""
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_arc(center=(10, 10), radius=1.0, start_angle=0, end_angle=90, dxfattribs={"layer": "FURINTURE"})
        engine = ApertureEngine(doc, unit_to_meters=1.0)
        doors = engine._detect_doors()
        self.assertEqual(len(doors), 0, "Arcs on FURINTURE layer should NOT be detected as door swings")

    def test_door_not_detected_on_layer_0(self):
        """Door overcounting bug check: Arcs on default layer 0 must NOT be automatically detected as doors."""
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_arc(center=(10, 10), radius=1.0, start_angle=0, end_angle=90, dxfattribs={"layer": "0"})
        engine = ApertureEngine(doc, unit_to_meters=1.0)
        doors = engine._detect_doors()
        self.assertEqual(len(doors), 0, "Arcs on layer 0 should NOT be detected as door swings")

    def test_window_merge_parallel_lines(self):
        """Window overcounting bug check: Parallel line pairs forming a single window frame must be merged into 1 opening."""
        doc = ezdxf.new()
        msp = doc.modelspace()
        # Add two parallel window frame lines close together (0.05m apart)
        msp.add_line((0, 0), (1.5, 0), dxfattribs={"layer": "WINDOWS"})
        msp.add_line((0, 0.05), (1.5, 0.05), dxfattribs={"layer": "WINDOWS"})
        engine = ApertureEngine(doc, unit_to_meters=1.0)
        windows = engine._detect_windows()
        self.assertEqual(len(windows), 1, "Parallel window frame lines should be merged into a single window opening candidate")

    def test_door_hosting_finds_nearest_wall(self):
        """Door near a wall should be hosted with the correct host_wall_id."""
        from shapely.geometry import LineString
        wall_edges = [
            {"edge_id": "w1", "p1": (0, 0), "p2": (10, 0), "geometry": LineString([(0, 0), (10, 0)])},
            {"edge_id": "w2", "p1": (0, 10), "p2": (10, 10), "geometry": LineString([(0, 10), (10, 10)])},
        ]
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_arc(center=(5, 0.1), radius=0.9, start_angle=0, end_angle=90, dxfattribs={"layer": "DOOR"})
        engine = ApertureEngine(doc, unit_to_meters=1.0)
        doors, _ = engine.detect_and_host_apertures(wall_edges)
        self.assertEqual(len(doors), 1)
        self.assertEqual(doors[0]["host_wall_id"], "w1")

    def test_door_connection_detects_both_rooms(self):
        """Door between two rooms should report both rooms in `connects`."""
        from shapely.geometry import LineString, Polygon
        wall = {"edge_id": "w1", "p1": (0, 0), "p2": (10, 0), "geometry": LineString([(0, 0), (10, 0)])}
        room_a = {"room_id": "R_A", "polygon": Polygon([(0, 0.1), (10, 0.1), (10, 5), (0, 5)])}
        room_b = {"room_id": "R_B", "polygon": Polygon([(0, -0.1), (10, -0.1), (10, -5), (0, -5)])}
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_arc(center=(5, 0.0), radius=0.9, start_angle=0, end_angle=90, dxfattribs={"layer": "DOOR"})
        engine = ApertureEngine(doc, unit_to_meters=1.0)
        doors, _ = engine.detect_and_host_apertures([wall], room_polygons=[room_a, room_b])
        self.assertEqual(len(doors), 1)
        connects = doors[0]["connects"]
        self.assertIn("R_A", connects)
        self.assertIn("R_B", connects)

    def test_door_connection_count_not_deduplicated(self):
        """Three doors connecting two rooms should produce 3 connected_pairs, not 1."""
        from semantics_engine import SemanticsEngine
        doors = [
            {"opening_id": "d1", "connects": ["R_A", "R_B"]},
            {"opening_id": "d2", "connects": ["R_A", "R_B"]},
            {"opening_id": "d3", "connects": ["R_A", "R_B"]}
        ]
        engine = SemanticsEngine([], unit_to_meters=1.0)
        graph = engine._build_adjacency_graph([], doors)
        self.assertEqual(len(graph["connected_pairs"]), 3)

if __name__ == "__main__":
    unittest.main()
