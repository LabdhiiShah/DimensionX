import sys, os, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from layer3_scale import resolve_scale


class TestScaleResolution(unittest.TestCase):

    def test_inches_drawing(self):
        """Wall thickness 4.7 → inches (119 mm)"""
        tol = {
            "wall_thickness_stats": {"median": {"value": 4.7}},
            "drawing_extent": {"diagonal": {"value": 688.5}},
        }
        scale = resolve_scale(tolerance_bundle=tol)
        self.assertEqual(scale.unit_name, "inches")
        self.assertAlmostEqual(scale.scale_to_meters, 0.0254, places=4)
        self.assertIn(scale.confidence, ["HIGH", "MEDIUM"])

    def test_mm_drawing(self):
        """Wall thickness 150 → mm (150 mm)"""
        tol = {
            "wall_thickness_stats": {"median": {"value": 150.0}},
            "drawing_extent": {"diagonal": {"value": 12000.0}},
        }
        scale = resolve_scale(tolerance_bundle=tol)
        self.assertEqual(scale.unit_name, "mm")

    def test_meters_drawing(self):
        """Wall thickness 0.15 → meters (150 mm)"""
        tol = {
            "wall_thickness_stats": {"median": {"value": 0.15}},
            "drawing_extent": {"diagonal": {"value": 15.0}},
        }
        scale = resolve_scale(tolerance_bundle=tol)
        self.assertEqual(scale.unit_name, "meters")

    def test_feet_drawing(self):
        """Wall thickness 0.5 → feet (152 mm)"""
        tol = {
            "wall_thickness_stats": {"median": {"value": 0.5}},
            "drawing_extent": {"diagonal": {"value": 40.0}},
        }
        scale = resolve_scale(tolerance_bundle=tol)
        # 0.5 ft = 152 mm plausible; 0.5 m = 500 mm at boundary; 0.5 in = 12.7 mm too thin
        self.assertIn(scale.unit_name, ["feet", "meters"])

    def test_cm_drawing(self):
        """Wall thickness 15 → cm (150 mm)"""
        tol = {
            "wall_thickness_stats": {"median": {"value": 15.0}},
            "drawing_extent": {"diagonal": {"value": 1500.0}},
        }
        scale = resolve_scale(tolerance_bundle=tol)
        self.assertEqual(scale.unit_name, "cm")

    def test_no_wall_stats_falls_back_to_extent(self):
        """No wall thickness → use extent as primary"""
        tol = {
            "wall_thickness_stats": {"median": {"value": 0.0}},
            "drawing_extent": {"diagonal": {"value": 15000.0}},
        }
        scale = resolve_scale(tolerance_bundle=tol)
        # 15000 mm = 15 m (plausible), 15000 inches = 381 m (implausible)
        self.assertEqual(scale.unit_name, "mm")

    def test_unresolvable_returns_unspecified(self):
        """Wall thickness 5000 → nothing plausible"""
        tol = {
            "wall_thickness_stats": {"median": {"value": 5000.0}},
            "drawing_extent": {"diagonal": {"value": 999999.0}},
        }
        scale = resolve_scale(tolerance_bundle=tol)
        self.assertEqual(scale.unit_name, "UNSPECIFIED")

    def test_header_insunits_4_mm(self):
        """$INSUNITS=4 with ambiguous wall thickness → header wins"""
        class MockHeader:
            def get(self, key, default=None):
                return 4 if key == "$INSUNITS" else default
        class MockDoc:
            header = MockHeader()

        tol = {
            "wall_thickness_stats": {"median": {"value": 100.0}},  # plausible as mm or cm
            "drawing_extent": {"diagonal": {"value": 10000.0}},
        }
        scale = resolve_scale(doc=MockDoc(), tolerance_bundle=tol)
        self.assertEqual(scale.unit_name, "mm")


if __name__ == "__main__":
    unittest.main()
