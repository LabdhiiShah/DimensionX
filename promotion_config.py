"""
PromotionConfig Module (Layer 1 & 2 Audit Promotion Configuration)
===================================================================
WHAT THIS MODULE DOES:
- Encapsulates configurable parameters, geometric thresholds, and score weights for non-layer wall promotion.
- Loads overrides from `config/promotion.yaml` if present.
- Validates that weights sum to 1.0, tolerances are non-negative, and parameters reside within valid mathematical bounds.

WHAT THIS MODULE DOES NOT DO:
- Does NOT perform non-layer wall candidate evaluation or scoring logic.
- Does NOT hardcode layer names or drawing-specific numeric constants.
"""

import os
from dataclasses import dataclass, asdict

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

@dataclass
class PromotionConfig:
    min_length_factor: float = 1.5
    parallel_angle_tol_deg: float = 5.0
    thickness_match_rel_tol: float = 0.35
    min_overlap_ratio: float = 0.10
    min_connectivity: int = 1
    min_promotion_score: float = 0.45

    # Part A Additions
    fragment_density_threshold: float = 0.50
    min_layer_confidence_for_role: float = 0.65
    structural_requires_geometry_agreement: bool = True

    length_weight: float = 0.30
    parallel_weight: float = 0.40
    connectivity_weight: float = 0.20
    layer_role_weight: float = 0.10

    max_skipped_log: int = 500

    def validate(self):
        """Validates configuration parameters."""
        if self.min_length_factor <= 0:
            raise ValueError(f"min_length_factor must be > 0, got {self.min_length_factor}")
        if self.parallel_angle_tol_deg < 0 or self.parallel_angle_tol_deg > 90:
            raise ValueError(f"parallel_angle_tol_deg must be in [0, 90], got {self.parallel_angle_tol_deg}")
        if self.thickness_match_rel_tol < 0 or self.thickness_match_rel_tol > 1.0:
            raise ValueError(f"thickness_match_rel_tol must be in [0, 1.0], got {self.thickness_match_rel_tol}")
        if self.min_overlap_ratio < 0 or self.min_overlap_ratio > 1.0:
            raise ValueError(f"min_overlap_ratio must be in [0, 1.0], got {self.min_overlap_ratio}")
        if self.min_connectivity < 0:
            raise ValueError(f"min_connectivity must be >= 0, got {self.min_connectivity}")
        if self.min_promotion_score < 0.0 or self.min_promotion_score > 1.0:
            raise ValueError(f"min_promotion_score must be in [0, 1.0], got {self.min_promotion_score}")

        if self.fragment_density_threshold < 0.0 or self.fragment_density_threshold > 1.0:
            raise ValueError(f"fragment_density_threshold must be in [0, 1.0], got {self.fragment_density_threshold}")
        if self.min_layer_confidence_for_role < 0.0 or self.min_layer_confidence_for_role > 1.0:
            raise ValueError(f"min_layer_confidence_for_role must be in [0, 1.0], got {self.min_layer_confidence_for_role}")

        if any(w < 0.0 for w in [self.length_weight, self.parallel_weight, self.connectivity_weight, self.layer_role_weight]):
            raise ValueError("All score weights must be >= 0")

        total_weight = self.length_weight + self.parallel_weight + self.connectivity_weight + self.layer_role_weight
        if abs(total_weight - 1.0) > 1e-4:
            raise ValueError(f"Score weights must sum to 1.0, got {total_weight:.4f}")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def load(cls, config_path=None):
        """Loads configuration from YAML file or defaults."""
        if config_path is None:
            base_dir = os.path.dirname(__file__)
            config_path = os.path.join(base_dir, "config", "promotion.yaml")

        cfg = cls()

        if HAS_YAML and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if hasattr(cfg, k):
                                setattr(cfg, k, v)
            except Exception as e:
                print(f"[PromotionConfig] Warning: Failed to load '{config_path}': {e}. Using defaults.")

        cfg.validate()
        return cfg
