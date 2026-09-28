"""
Unit and Integration Tests for Semantics Engine (Layer 4)
==========================================================
"""

import sys
import os
import unittest
from shapely.geometry import Polygon

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from semantics_engine import (
    clean_cad_text,
    strip_mtext_formatting,
    extract_room_name_and_dimensions,
    derive_semantic_category,
    SemanticsEngine
)

class TestSemanticsEngine(unittest.TestCase):
    def test_mtext_formatting_stripped(self):
        raw = r'\pi18.40708;{\fTrebuchet MS|b0|i0|c0|p34;dining }'
        result = strip_mtext_formatting(raw)
        self.assertEqual(result, "dining")

    def test_clean_cad_text(self):
        text = "\\A1;M. Bedroom 9'3\" x 11'0\""
        cleaned = clean_cad_text(text)
        self.assertIn("M. Bedroom", cleaned)

    def test_extract_room_name_and_dimensions(self):
        title, dims = extract_room_name_and_dimensions("Master Bedroom 9'3\" x 11'0\"")
        self.assertEqual(title, "Master Bedroom")
        self.assertEqual(len(dims), 2)
        self.assertAlmostEqual(dims[0], 111.0) # 9*12 + 3

    def test_derive_semantic_category(self):
        self.assertEqual(derive_semantic_category("Master Bedroom"), "MASTER_BEDROOM")
        self.assertEqual(derive_semantic_category("Kitchen"), "KITCHEN")
        self.assertEqual(derive_semantic_category("Living / Dining"), "LIVING_DINING")
        self.assertEqual(derive_semantic_category("Master Toilet"), "MASTER_TOILET")
        self.assertEqual(derive_semantic_category("Entrance"), "ENTRANCE")

    def test_entrance_label_matched(self):
        """Test that ENTRANCE label is matched to a room candidate polygon rather than remaining unmapped."""
        labels = [{
            "text": "ENTRANCE 6'0\" x 8'0\"",
            "position": [5.0, 5.0],
            "layer": "TEXT"
        }]
        engine = SemanticsEngine(labels, unit_to_meters=0.0254)
        poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        room_candidates = [{
            "room_id": "room_candidate_1",
            "polygon": poly,
            "vertices": list(poly.exterior.coords),
            "area": poly.area,
            "perimeter": poly.length,
            "bounds": poly.bounds
        }]
        annotated_rooms, adj, unmapped, meaningful_count, semantic_count = engine.process_room_semantics(room_candidates, [])
        self.assertNotIn("ENTRANCE", [u.upper() for u in unmapped], "ENTRANCE label should be matched to room polygon")
        self.assertEqual(semantic_count, 1)
        self.assertEqual(annotated_rooms[0]["semantic_type"], "ENTRANCE")

    def test_balcony_label_matched(self):
        """Semantics gap check: BALCONY text label must be matched to a room candidate polygon rather than remaining unmapped."""
        labels = [{
            "text": "BALCONY 4'0\" x 8'0\"",
            "position": [5.0, 5.0],
            "layer": "TEXT"
        }]
        engine = SemanticsEngine(labels, unit_to_meters=0.0254)
        poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        room_candidates = [{
            "room_id": "room_candidate_1",
            "polygon": poly,
            "vertices": list(poly.exterior.coords),
            "area": poly.area,
            "perimeter": poly.length,
            "bounds": poly.bounds
        }]
        annotated_rooms, adj, unmapped, meaningful_count, semantic_count = engine.process_room_semantics(room_candidates, [])
        self.assertNotIn("BALCONY", [u.upper() for u in unmapped], "BALCONY label should be matched to room polygon")
        self.assertEqual(semantic_count, 1)

    def test_toilet_label_matched(self):
        labels = [{
            "text": "M. TOILET 5'0\" x 7'0\"",
            "position": [2.0, 2.0],
            "layer": "TEXT"
        }]
        engine = SemanticsEngine(labels, unit_to_meters=0.0254)
        poly = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])
        room_candidates = [{
            "room_id": "room_candidate_1",
            "polygon": poly,
            "vertices": list(poly.exterior.coords),
            "area": poly.area,
            "perimeter": poly.length,
            "bounds": poly.bounds
        }]
        annotated_rooms, adj, unmapped, meaningful_count, semantic_count = engine.process_room_semantics(room_candidates, [])
        self.assertEqual(semantic_count, 1)
        self.assertIn(annotated_rooms[0]["semantic_type"], ("MASTER_TOILET", "TOILET"))

    def test_abbreviated_labels_matched(self):
        """Test that 'C. Bed', 'M. Toi', 'Ltr./Din.' are matched to correct categories."""
        labels = [
            {"text": "C. Bed 9'0\" x 11'3\"", "position": [5.0, 5.0], "layer": "TEXT"},
            {"text": "M. Toi. 4'3\" x 7'4\"", "position": [15.0, 5.0], "layer": "TEXT"},
            {"text": "Ltr./Din. 12'0\" x 14'6\"", "position": [25.0, 5.0], "layer": "TEXT"}
        ]
        engine = SemanticsEngine(labels, unit_to_meters=0.0254)
        r1 = {"room_id": "r1", "polygon": Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]), "area": 100, "perimeter": 40, "bounds": (0, 0, 10, 10)}
        r2 = {"room_id": "r2", "polygon": Polygon([(10, 0), (20, 0), (20, 10), (10, 10)]), "area": 100, "perimeter": 40, "bounds": (10, 0, 20, 10)}
        r3 = {"room_id": "r3", "polygon": Polygon([(20, 0), (30, 0), (30, 10), (20, 10)]), "area": 100, "perimeter": 40, "bounds": (20, 0, 30, 10)}
        
        annotated_rooms, _, unmapped, _, semantic_count = engine.process_room_semantics([r1, r2, r3], [])
        self.assertEqual(semantic_count, 3)
        cat_map = {r["room_id"]: r["semantic_type"] for r in annotated_rooms}
        self.assertEqual(cat_map["r1"], "CHILDREN_BEDROOM")
        self.assertEqual(cat_map["r2"], "MASTER_TOILET")
        self.assertEqual(cat_map["r3"], "LIVING_DINING")

    def test_geometric_fallback_small_room_is_bathroom(self):
        """A 3 m² room with no text should be inferred as BATHROOM."""
        engine = SemanticsEngine([], unit_to_meters=1.0)
        r1 = {"room_id": "r1", "polygon": Polygon([(0, 0), (1.5, 0), (1.5, 2.0), (0, 2.0)]), "area": 3.0, "perimeter": 7.0, "bounds": (0, 0, 1.5, 2.0)}
        r2 = {"room_id": "r2", "polygon": Polygon([(0, 0), (5, 0), (5, 4), (0, 4)]), "area": 20.0, "perimeter": 18.0, "bounds": (0, 0, 5, 4)}
        
        annotated_rooms, _, _, _, semantic_count = engine.process_room_semantics([r1, r2], [])
        cat_map = {r["room_id"]: r["semantic_type"] for r in annotated_rooms}
        self.assertEqual(cat_map["r1"], "BATHROOM")

    def test_geometric_fallback_largest_room_is_living(self):
        """Largest unlabeled room should default to LIVING."""
        engine = SemanticsEngine([], unit_to_meters=1.0)
        r1 = {"room_id": "r1", "polygon": Polygon([(0, 0), (3, 0), (3, 3), (0, 3)]), "area": 9.0, "perimeter": 12.0, "bounds": (0, 0, 3, 3)}
        r2 = {"room_id": "r2", "polygon": Polygon([(0, 0), (6, 0), (6, 5), (0, 5)]), "area": 30.0, "perimeter": 22.0, "bounds": (0, 0, 6, 5)}
        
        annotated_rooms, _, _, _, semantic_count = engine.process_room_semantics([r1, r2], [])
        cat_map = {r["room_id"]: r["semantic_type"] for r in annotated_rooms}
        self.assertEqual(cat_map["r2"], "LIVING_DINING")

if __name__ == "__main__":
    unittest.main()
