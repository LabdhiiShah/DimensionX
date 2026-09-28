"""
Regression & Target Count Tests for Layer 4 Refinement
======================================================
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestLayer4Regression(unittest.TestCase):
    def test_sample1_baseline_snapshot(self):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output', 'baseline', 'sample1_house2d.json'))
        if not os.path.exists(path):
            self.skipTest("Baseline snapshot for sample1 not found")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        bc = data["building_components"]
        self.assertEqual(len(bc["walls"]), 273)
        self.assertEqual(len(bc["doors"]), 4)
        self.assertEqual(len(bc["windows"]), 3)

    def test_sample2_baseline_snapshot(self):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output', 'baseline', 'sample2_house2d.json'))
        if not os.path.exists(path):
            self.skipTest("Baseline snapshot for sample2 not found")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        bc = data["building_components"]
        self.assertEqual(len(bc["walls"]), 278)
        self.assertEqual(len(bc["doors"]), 3)
        self.assertEqual(len(bc["windows"]), 16)

    def test_sample3_target_counts(self):
        """Layer 4 Overcounting Regression Target: sample3 should contain <= 6 real doors and <= 10 real windows."""
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output', 'baseline', 'sample3_house2d.json'))
        if not os.path.exists(path):
            self.skipTest("Baseline snapshot for sample3 not found")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        bc = data["building_components"]
        num_doors = len(bc.get("doors", []))
        num_windows = len(bc.get("windows", []))
        self.assertLessEqual(num_doors, 6, f"Sample 3 expected <= 6 real doors, found {num_doors}")
        self.assertLessEqual(num_windows, 10, f"Sample 3 expected <= 10 real windows, found {num_windows}")

    def test_sample2_room_areas_are_realistic(self):
        """Verify sample2 room areas are within realistic bounds for the drawing's envelope."""
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output', 'house2d.json'))
        if not os.path.exists(path):
            self.skipTest("house2d.json not found")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("metadata", {}).get("source_dxf") != "sample2.dxf":
            self.skipTest("house2d.json is not from sample2.dxf")
        rooms = data.get("building_components", {}).get("rooms", [])
        self.assertGreater(len(rooms), 0, "sample2 should extract at least 1 room candidate")
        for r in rooms:
            area = r.get("area", 0.0)
            self.assertGreater(area, 0.5, f"Room {r.get('room_id')} area ({area}) should be > 0.5 m²")
            self.assertLessEqual(area, 30.0, f"Room {r.get('room_id')} area ({area}) should be <= 30.0 m²")

if __name__ == "__main__":
    unittest.main()
