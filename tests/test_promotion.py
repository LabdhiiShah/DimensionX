"""
Unit, Property, and Regression Tests for Layer 1, 2, and 3 Engine (Tasks A, B, C, D)
=====================================================================================
"""

import sys
import os
import random
import unittest
from shapely.geometry import LineString, Point

# Add parent directory to path to import project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from promotion_config import PromotionConfig
from non_layer_promoter import (
    is_long_enough,
    compute_segment_angle_deg,
    compute_angle_diff_deg,
    compute_parallel_geometry,
    evaluate_promotion_score,
    inspect_non_layer_promotions
)
from layer_classifier import classify_layers_ranked
from layer3_scale import (
    resolve_scale,
    propose_wall_thickness_candidates,
    ScaleBundle,
    ScaleConfig,
    ScaleCandidate
)
from layer1_layer2_runner import run_layer1_layer2

class TestPromotionConfig(unittest.TestCase):
    def test_default_config_valid(self):
        cfg = PromotionConfig()
        cfg.validate()
        self.assertEqual(cfg.min_length_factor, 1.5)
        self.assertEqual(cfg.parallel_angle_tol_deg, 5.0)
        self.assertEqual(cfg.min_promotion_score, 0.45)
        self.assertEqual(cfg.fragment_density_threshold, 0.50)
        self.assertEqual(cfg.min_layer_confidence_for_role, 0.65)
        self.assertTrue(cfg.structural_requires_geometry_agreement)

    def test_invalid_weights_sum(self):
        cfg = PromotionConfig(length_weight=0.5, parallel_weight=0.5, connectivity_weight=0.5)
        with self.assertRaises(ValueError):
            cfg.validate()

class TestIsLongEnough(unittest.TestCase):
    """1. is_long_enough Unit Tests & Property Fixtures"""

    def test_threshold_calculation(self):
        cfg = PromotionConfig(min_length_factor=1.5)
        median_thickness = 4.45

        # Test short segment
        seg_len_short = 0.75
        passed, thresh = is_long_enough(seg_len_short, median_thickness, cfg)
        self.assertFalse(passed)
        self.assertEqual(thresh, 6.675)

        # Test long segment
        seg_len_long = 6.675
        passed, thresh = is_long_enough(seg_len_long, median_thickness, cfg)
        self.assertTrue(passed)
        self.assertEqual(thresh, 6.675)

    def test_randomized_property(self):
        """
        Property Test: For positive x and t,
        is_long_enough(x, t, cfg)[0] == (x >= cfg.min_length_factor * t)
        """
        cfg = PromotionConfig(min_length_factor=1.5)
        random.seed(42)
        for _ in range(500):
            x = round(random.uniform(0.001, 1000.0), 4)
            t = round(random.uniform(0.001, 100.0), 4)
            passed, thresh = is_long_enough(x, t, cfg)
            expected = (x >= round(cfg.min_length_factor * t, 4))
            self.assertEqual(passed, expected, f"Failed for x={x}, t={t}, thresh={thresh}")

class TestParallelPartnerDetection(unittest.TestCase):
    """2. Parallel Partner Detection Tests"""

    def test_parallel_partner_success(self):
        cfg = PromotionConfig(parallel_angle_tol_deg=5.0, thickness_match_rel_tol=0.35, min_overlap_ratio=0.10)
        median_thickness = 4.45

        cand = {
            "p1": (0.0, 0.0), "p2": (10.0, 0.0),
            "segment_length": 10.0,
            "geometry": LineString([(0.0, 0.0), (10.0, 0.0)])
        }

        part = {
            "p1": (0.0, 4.45), "p2": (10.0, 4.45),
            "segment_length": 10.0,
            "geometry": LineString([(0.0, 4.45), (10.0, 4.45)])
        }

        is_valid, offset, angle_diff, overlap = compute_parallel_geometry(cand, part, median_thickness, cfg)
        self.assertTrue(is_valid)
        self.assertAlmostEqual(offset, 4.45, places=2)
        self.assertAlmostEqual(angle_diff, 0.0, places=2)
        self.assertAlmostEqual(overlap, 1.0, places=2)

    def test_parallel_partner_perpendicular_fails(self):
        cfg = PromotionConfig(parallel_angle_tol_deg=5.0)
        median_thickness = 4.45

        cand = {
            "p1": (0.0, 0.0), "p2": (10.0, 0.0),
            "segment_length": 10.0,
            "geometry": LineString([(0.0, 0.0), (10.0, 0.0)])
        }

        part = {
            "p1": (5.0, 0.0), "p2": (5.0, 10.0),
            "segment_length": 10.0,
            "geometry": LineString([(5.0, 0.0), (5.0, 10.0)])
        }

        is_valid, offset, angle_diff, overlap = compute_parallel_geometry(cand, part, median_thickness, cfg)
        self.assertFalse(is_valid)

class TestPartAUnits(unittest.TestCase):
    """3. Part A1 - A4 Unit Tests"""

    def test_fragment_density_gates_high_fragment_layer(self):
        """Part A1: High fragment density layer (>=0.90) skips promotion unless rescued."""
        cfg = PromotionConfig()
        raw_lines = [
            {"p1": (0.0, 0.0), "p2": (10.0, 0.0), "layer": "ELWIN", "handle": "h1"}
        ]
        layer_cls = {
            "ELWIN": {
                "entity_count": 100,
                "fragment_ratio": 0.95,
                "candidate_roles": [{"role": "UNKNOWN", "confidence": 0.2}],
                "conflict": False
            }
        }
        tol_bundle = {
            "wall_thickness_stats": {"median": {"value": 4.45}},
            "weld_tolerance": {"value": 0.25}
        }

        res = inspect_non_layer_promotions(raw_lines, layer_cls, tol_bundle, cfg)
        self.assertEqual(res["promoted_non_wall_segments_count"], 0)
        self.assertEqual(res["skipped_non_wall_segments_count"], 1)
        self.assertIn("high fragment-density layer", res["skipped_segments"][0]["skip_reason"])

    def test_fragment_density_caps_aggregated_top_confidence(self):
        """Fix 1: Synthetic layer with high fragment_ratio and a name signal -> top_confidence <= 0.30."""
        layers_info = {"TEST_WALL": {"entity_count": 100}}
        entity_info = {"total_count": 100, "by_layer_and_type": {"TEST_WALL": {"LINE": 100}}}
        layer_entities = {"TEST_WALL": [{"segment_length": 0.01} for _ in range(95)] + [{"segment_length": 10.0} for _ in range(5)]}
        tol = {"wall_thickness_stats": {"median": {"value": 4.45}}}

        res = classify_layers_ranked(layers_info, entity_info, tolerance_bundle=tol, layer_entities=layer_entities)
        top_conf = res["TEST_WALL"]["candidate_roles"][0]["confidence"]
        self.assertLessEqual(top_conf, 0.30)

    def test_name_geometry_agreement_keeps_wall(self):
        """Fix 2: Synthetic layer with name=WALL and geom=WALL, high fragment_ratio -> deprecated_role = WALL."""
        layers_info = {"WALL": {"entity_count": 100}}
        entity_info = {"total_count": 100, "by_layer_and_type": {"WALL": {"LWPOLYLINE": 100}}}
        layer_entities = {"WALL": [{"segment_length": 0.01} for _ in range(90)] + [{"segment_length": 10.0} for _ in range(10)]}
        tol = {"wall_thickness_stats": {"median": {"value": 4.45}}}

        res = classify_layers_ranked(layers_info, entity_info, tolerance_bundle=tol, layer_entities=layer_entities)
        self.assertEqual(res["WALL"]["deprecated_assigned_role"], "WALL")
        self.assertLessEqual(res["WALL"]["candidate_roles"][0]["confidence"], 0.30)

    def test_layer_confidence_floor_blocks_promotion(self):
        """Part A2: Low role confidence (<0.65) requires strict geometry."""
        cfg = PromotionConfig(min_layer_confidence_for_role=0.65)
        raw_lines = [
            {"p1": (0.0, 0.0), "p2": (10.0, 0.0), "layer": "WEAK_LAYER", "handle": "h1"}
        ]
        layer_cls = {
            "WEAK_LAYER": {
                "candidate_roles": [{"role": "UNKNOWN", "confidence": 0.30}],
                "fragment_ratio": 0.1,
                "conflict": False
            }
        }
        tol_bundle = {
            "wall_thickness_stats": {"median": {"value": 4.45}},
            "weld_tolerance": {"value": 0.25}
        }

        res = inspect_non_layer_promotions(raw_lines, layer_cls, tol_bundle, cfg)
        self.assertEqual(res["promoted_non_wall_segments_count"], 0)
        self.assertEqual(res["skipped_non_wall_segments_count"], 1)

    def test_structural_layer_requires_wall_anchor(self):
        """Part A3: Structural layer promotion guard."""
        cfg = PromotionConfig(structural_requires_geometry_agreement=True)
        raw_lines = [
            {"p1": (0.0, 0.0), "p2": (10.0, 0.0), "layer": "BEAM_FRAME", "handle": "h1"}
        ]
        layer_cls = {
            "BEAM_FRAME": {
                "candidate_roles": [{"role": "STRUCTURAL", "confidence": 0.85}],
                "fragment_ratio": 0.0,
                "conflict": False
            }
        }
        tol_bundle = {
            "wall_thickness_stats": {"median": {"value": 4.45}},
            "weld_tolerance": {"value": 0.25}
        }

        res = inspect_non_layer_promotions(raw_lines, layer_cls, tol_bundle, cfg)
        self.assertEqual(res["promoted_non_wall_segments_count"], 0)
        self.assertEqual(res["promoted_structural_segments"], [])

    def test_report_schema_is_complete(self):
        """Part A4: Complete schema & 100% layer diagnostics presence."""
        cfg = PromotionConfig()
        raw_lines = []
        layer_cls = {
            "LAYER1": {"entity_count": 10, "fragment_ratio": 0.1, "candidate_roles": [{"role": "WALL", "confidence": 0.9}], "conflict": False},
            "ELWIN": {"entity_count": 500, "fragment_ratio": 0.92, "candidate_roles": [{"role": "ELECTRICAL", "confidence": 0.8}], "conflict": False}
        }
        tol_bundle = {"wall_thickness_stats": {"median": {"value": 4.45}}, "weld_tolerance": {"value": 0.25}}

        res = inspect_non_layer_promotions(raw_lines, layer_cls, tol_bundle, cfg)
        self.assertIn("promoted_non_wall_segments_count", res)
        self.assertIn("skipped_non_wall_segments_count", res)
        self.assertIn("promotion_config_used", res)
        self.assertIn("promoted_segments", res)
        self.assertIn("skipped_segments", res)
        self.assertIn("promoted_structural_segments", res)
        self.assertIn("layer_warnings", res)
        self.assertIn("layer_diagnostics", res)

        self.assertIn("LAYER1", res["layer_diagnostics"])
        self.assertIn("ELWIN", res["layer_diagnostics"])
        self.assertEqual(len(res["layer_warnings"]), 1)
        self.assertIn("ELWIN", res["layer_warnings"][0])

class TestLayer3Scale(unittest.TestCase):
    """4. Part B Unit Tests for Scale Resolution"""

    def test_scale_from_insunits(self):
        """Header $INSUNITS = 4 -> mm (1000.0, HIGH)."""
        class MockHeader:
            def get(self, key, default=None):
                if key == "$INSUNITS": return 4
                return default
        class MockDoc:
            header = MockHeader()

        scale = resolve_scale(doc=MockDoc())
        self.assertEqual(scale.units_per_meter, 1000.0)
        self.assertEqual(scale.unit_name, "mm")
        self.assertEqual(scale.confidence, "HIGH")

    def test_wall_thickness_proposes_feet(self):
        """Fix 3: median_thickness = 0.5 with imperial header -> candidate list includes ft at weight >= 0.6, excludes in."""
        cands = propose_wall_thickness_candidates(0.50, measurement_flag=0)
        unit_names = [c.unit_name for c in cands]
        self.assertIn("ft", unit_names)
        self.assertNotIn("inch", unit_names)
        ft_cand = next(c for c in cands if c.unit_name == "ft")
        self.assertGreaterEqual(ft_cand.weight, 0.6)

    def test_extent_sanity_rejects_implausible(self):
        """Fix 5: Candidate at 39.37 u/m with 1.0 diagonal -> implied extent 0.03m -> rejected as < 2m."""
        tol = {"drawing_extent": {"diagonal": 1.0}, "wall_thickness_stats": {"median": {"value": 0.50}}}
        class MockHeader:
            def get(self, k, d=None):
                if k == "$MEASUREMENT": return 0
                return 0
        class MockDoc:
            header = MockHeader()

        scale = resolve_scale(doc=MockDoc(), tolerance_bundle=tol)
        rejected_notes = [n for n in scale.notes if "rejected" in n]
        self.assertTrue(any("implied extent" in n for n in rejected_notes))

    def test_fixture_size_rejected(self):
        """Fix 5: Candidate from text 7'8" x 4'0" -> rejected with fixture-size reason."""
        class MockText:
            def plain_text(self): return "7'8\" x 4'0\""
            class dxf: text = "7'8\" x 4'0\""
        class MockMSP:
            def query(self, q): return [MockText()]
        class MockDoc:
            header = None
            def modelspace(self): return MockMSP()

        scale = resolve_scale(doc=MockDoc())
        self.assertTrue(any("fixture/object size" in n for n in scale.notes))

    def test_notes_populated(self):
        """Fix 4: After a run with >= 1 rejected candidate, notes is non-empty and each rejection has a note."""
        tol = {"drawing_extent": {"diagonal": 1.0}, "wall_thickness_stats": {"median": {"value": 0.50}}}
        scale = resolve_scale(tolerance_bundle=tol)
        self.assertIsInstance(scale.notes, list)
        self.assertGreater(len(scale.notes), 0)

    def test_scale_unspecified_falls_back(self):
        """No evidence -> UNSPECIFIED, 1.0 m."""
        scale = resolve_scale()
        self.assertEqual(scale.units_per_meter, 1.0)
        self.assertEqual(scale.unit_name, "m")
        self.assertEqual(scale.confidence, "UNSPECIFIED")

class TestRegressionAndAcceptance(unittest.TestCase):
    """5. Part D Regression Assertions on sample1.dxf and sample2.dxf"""

    def test_sample1_sample2_acceptance_criteria(self):
        dxf1 = "d:/end game/dwg/sample1.dxf"
        dxf2 = "d:/end game/dwg/sample2.dxf"

        if not os.path.exists(dxf1) or not os.path.exists(dxf2):
            self.skipTest("Sample DXF files not found")

        r1 = run_layer1_layer2(dxf1)
        p1 = r1["task_5_non_layer_wall_promotion"]
        # Promoted <= 15
        self.assertLessEqual(p1["promoted_non_wall_segments_count"], 15)

        # Zero length threshold violations
        for seg in p1["promoted_segments"]:
            len_used = seg["promotion_threshold_used"]["value"]
            self.assertGreaterEqual(seg["segment_length"], len_used)

        r2 = run_layer1_layer2(dxf2)
        p2 = r2["task_5_non_layer_wall_promotion"]
        # Promoted <= 25
        self.assertLessEqual(p2["promoted_non_wall_segments_count"], 25)

        for seg in p2["promoted_segments"]:
            len_used = seg["promotion_threshold_used"]["value"]
            self.assertGreaterEqual(seg["segment_length"], len_used)

        # ELWIN warning present in sample2
        warnings = p2["layer_warnings"]
        has_elwin_warning = any("ELWIN" in w for w in warnings)
        self.assertTrue(has_elwin_warning, "ELWIN layer fragment warning missing in sample2")

        # Scale resolution block valid
        s1 = r1["task_6_scale_resolution"]
        self.assertIn("units_per_meter", s1)
        self.assertNotEqual(s1["confidence"], "UNSPECIFIED")

        s2 = r2["task_6_scale_resolution"]
        self.assertIn("units_per_meter", s2)
        self.assertNotEqual(s2["confidence"], "UNSPECIFIED")

if __name__ == '__main__':
    unittest.main()
