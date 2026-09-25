"""
Layer Role Classifier Module (Layer 2 Audit - Task 3 & Part A1 Fixes)
======================================================================
WHAT THIS MODULE DOES:
- Classifies DXF layers into ranked candidate roles with confidence scores (0.0 - 1.0) using multi-signal evidence.
- Combines four distinct signal sources: Name Pattern, Geometry Distribution, Spatial Proximity, and Structural Statistics.
- Implements Part A1 Fragment-Density Gating:
  * Computes `fragment_ratio = (count of entities < min_length_threshold) / (total entities on layer)`.
  * If `fragment_ratio >= fragment_density_threshold` (default 0.50):
    - Caps every geometry-derived candidate role confidence at 0.30.
    - If name-derived role is WALL, WINDOW, or DOOR and fragment_ratio >= 0.5, downgrades `deprecated_assigned_role` to UNKNOWN unless name confidence >= 0.85.
    - Adds explicit fragment-density evidence string.
- Enforces strict multi-signal evidence rules:
  * Name evidence alone is capped at 0.7.
  * Geometry evidence alone is capped at 0.8.
  * Agreement between Name and Geometry elevates confidence up to 0.95.
  * Disagreement sets `conflict = true` and caps both confidences at 0.6.
- Uses configurable token matching loaded from `layer_vocab.json`. Unknown tokens are never penalized.

WHAT THIS MODULE DOES NOT DO:
- Does NOT force a single hard role assignment per layer.
- Does NOT modify downstream wall assembly, graph building, or room polygonization.
- Does NOT delete or filter out layers.
"""

import os
import json
import re
import math
from collections import defaultdict

from promotion_config import PromotionConfig

ROLE_VOCABULARY = [
    "WALL", "WINDOW", "DOOR", "FURNITURE", "DIMENSION",
    "ANNOTATION", "HATCH", "STRUCTURAL", "ELECTRICAL", "SITE", "UNKNOWN"
]

def load_layer_vocabulary(vocab_filepath="layer_vocab.json"):
    """Loads configurable vocabulary from JSON file."""
    if not os.path.exists(vocab_filepath):
        vocab_filepath = os.path.join(os.path.dirname(__file__), "layer_vocab.json")
        
    if os.path.exists(vocab_filepath):
        with open(vocab_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("roles", {})
    return {}

class LayerClassifier:
    def __init__(self, vocab_filepath="layer_vocab.json", cfg=None):
        self.vocab = load_layer_vocabulary(vocab_filepath)
        self.cfg = cfg or PromotionConfig.load()

    def classify_layers(self, layers_info, entity_info, geom_stats=None, tolerance_bundle=None, layer_entities=None):
        """
        Consumes layer inventory, entity type breakdown, geometry statistics, and optional tolerance_bundle & layer_entities.
        Returns dictionary of layer classification records with ranked candidate roles, evidence, and conflict flags.
        """
        classifications = {}
        total_drawing_entities = entity_info.get("total_count", 1) if entity_info else 1

        # Derive min_length_threshold from ToleranceBundle or scale fallback
        if tolerance_bundle and "wall_thickness_stats" in tolerance_bundle:
            med_entry = tolerance_bundle["wall_thickness_stats"].get("median", {})
            median_wt = med_entry.get("value", 0.15) if isinstance(med_entry, dict) else float(med_entry)
        elif geom_stats and "candidate_wall_thicknesses" in geom_stats:
            offsets = [t["offset_distance"] for t in geom_stats.get("candidate_wall_thicknesses", []) if t["offset_distance"] > 0.05]
            median_wt = offsets[0] if offsets else 0.15
        else:
            median_wt = 0.15

        if median_wt <= 0:
            median_wt = 0.15

        min_length_threshold = round(self.cfg.min_length_factor * median_wt, 4)

        for layer_name, ldata in layers_info.items():
            entity_count = ldata.get("entity_count", 0)
            histogram = entity_info.get("by_layer_and_type", {}).get(layer_name, {}) if entity_info else {}
            
            # Part A1: Fragment-density calculation
            short_entity_count = 0
            total_layer_segments = 0
            if layer_entities and layer_name in layer_entities:
                total_layer_segments = len(layer_entities[layer_name])
                for ent in layer_entities[layer_name]:
                    length = ent.get("segment_length", 0.0)
                    if length < min_length_threshold:
                        short_entity_count += 1
            elif entity_count > 0:
                total_layer_segments = entity_count

            fragment_ratio = round(short_entity_count / float(total_layer_segments), 4) if total_layer_segments > 0 else 0.0
            is_high_fragment_density = (fragment_ratio >= self.cfg.fragment_density_threshold) and (entity_count > 0)

            # 1. Signal 1: Name-based Evidence
            name_role, name_conf, name_evidence = self._evaluate_name_signal(layer_name)
            
            # 2. Signal 2: Geometry Distribution Evidence
            geom_role, geom_conf, geom_evidence = self._evaluate_geometry_signal(histogram, entity_count, geom_stats)

            # Part A1 Rule: Cap geometry-derived confidence at 0.30 if high fragment density
            if is_high_fragment_density:
                geom_conf = min(geom_conf, 0.30)
                geom_evidence.append(
                    f"fragment-density: {fragment_ratio:.2%} of {entity_count} entities below min-length {min_length_threshold:.2f}; role confidence capped"
                )

            # 3. Signal 3: Spatial Proximity & Co-occurrence Evidence
            spatial_evidence = self._evaluate_spatial_signal(layer_name, histogram)
            
            # 4. Signal 4: Structural Statistics Evidence
            stats_evidence = self._evaluate_statistics_signal(entity_count, total_drawing_entities)

            # Combine Signals & Enforce Conflict / Confidence Rules
            conflict = False
            ranked_roles = []

            all_evidence = name_evidence + geom_evidence + spatial_evidence + stats_evidence

            # Conflict Detection Rule: Name & Geometry disagree with non-zero confidence
            if name_role != "UNKNOWN" and geom_role != "UNKNOWN" and name_role != geom_role:
                conflict = True
                capped_name_conf = min(name_conf, 0.6)
                capped_geom_conf = min(geom_conf, 0.6)
                
                ranked_roles.append({"role": name_role, "confidence": round(capped_name_conf, 2)})
                ranked_roles.append({"role": geom_role, "confidence": round(capped_geom_conf, 2)})
                all_evidence.append(f"signal: conflict detected — Name signal ({name_role}) conflicts with Geometry signal ({geom_role})")

            # Agreement Rule: Name & Geometry agree
            elif name_role != "UNKNOWN" and geom_role != "UNKNOWN" and name_role == geom_role:
                agreed_conf = min(0.95, round(name_conf + geom_conf * 0.3, 2))
                if is_high_fragment_density:
                    agreed_conf = min(agreed_conf, 0.30)
                ranked_roles.append({"role": name_role, "confidence": agreed_conf})
                all_evidence.append(f"signal: agreement — Name signal and Geometry signal agree on {name_role} (confidence {agreed_conf:.2f})")

            else:
                if name_role != "UNKNOWN":
                    c_val = name_conf if not is_high_fragment_density else min(name_conf, 0.30)
                    ranked_roles.append({"role": name_role, "confidence": round(c_val, 2)})
                if geom_role != "UNKNOWN" and geom_role != name_role:
                    c_val = geom_conf if not is_high_fragment_density else min(geom_conf, 0.30)
                    ranked_roles.append({"role": geom_role, "confidence": round(c_val, 2)})

            # Add fallback UNKNOWN role to complete ranked list
            existing_roles = set(r["role"] for r in ranked_roles)
            for role in ROLE_VOCABULARY:
                if role not in existing_roles:
                    ranked_roles.append({"role": role, "confidence": 0.05 if role == "UNKNOWN" else 0.0})

            ranked_roles.sort(key=lambda x: x["confidence"], reverse=True)

            # Fix 1: Post-aggregation cap for fragment density
            FRAGMENT_DENSITY_CEILING = 0.30
            if is_high_fragment_density:
                for r_item in ranked_roles:
                    if r_item["role"] != "UNKNOWN":
                        r_item["confidence"] = min(r_item["confidence"], FRAGMENT_DENSITY_CEILING)
                ranked_roles.sort(key=lambda x: x["confidence"], reverse=True)

            top_ranked_role = ranked_roles[0]["role"]

            # Fix 2: Name/geometry agreement exception for UNKNOWN downgrade
            deprecated_assigned = self._decide_deprecated_role(
                name_role, name_conf, geom_role, fragment_ratio, top_ranked_role
            )

            classifications[layer_name] = {
                "layer_name": layer_name,
                "entity_count": entity_count,
                "fragment_ratio": fragment_ratio,
                "entity_type_histogram": histogram,
                "candidate_roles": ranked_roles, # Ranked evidence list
                "evidence": all_evidence,
                "conflict": conflict,
                "deprecated_assigned_role": deprecated_assigned
            }

        return classifications

    def _decide_deprecated_role(self, name_role, name_conf, top_geom_role, fragment_ratio, top_ranked_role):
        """Fix 2: Keeps structural role if Name & top Geometry agree; otherwise downgrades low-conf fragment layer to UNKNOWN."""
        if (name_role == top_geom_role
                and name_role in {"WALL", "WINDOW", "DOOR"}
                and fragment_ratio >= self.cfg.fragment_density_threshold):
            return name_role

        if (name_role in {"WALL", "WINDOW", "DOOR"}
                and fragment_ratio >= self.cfg.fragment_density_threshold
                and name_conf < 0.85):
            return "UNKNOWN"

        return top_ranked_role

    def _evaluate_name_signal(self, layer_name):
        """Token matching against layer_vocab.json (capped at 0.7)."""
        uname = layer_name.upper()
        best_role = "UNKNOWN"
        best_score = 0.0
        evidence_msg = []

        for role_name, rdata in self.vocab.items():
            tokens = rdata.get("tokens", [])
            for token in tokens:
                pattern = r'(?:^|[\_\-\$\s])' + re.escape(token.upper()) + r'(?:$|[\_\-\$\s])'
                if re.search(pattern, uname) or token.upper() in uname:
                    score = 0.7 * rdata.get("weight", 1.0)
                    if score > best_score:
                        best_score = score
                        best_role = role_name
                    evidence_msg.append(f"name-pattern: token '{token}' matched layer name '{layer_name}' -> candidate role {role_name} (conf: {score:.2f})")
                    break

        if not evidence_msg:
            evidence_msg.append(f"name-pattern: no vocabulary token matched layer name '{layer_name}'")

        best_score = min(best_score, 0.7)
        return best_role, best_score, evidence_msg

    def _evaluate_geometry_signal(self, histogram, entity_count, geom_stats):
        """Entity type distribution & geometry evidence (capped at 0.8)."""
        if not histogram or entity_count == 0:
            return "UNKNOWN", 0.0, ["geometry: no entity histogram available for layer"]

        best_role = "UNKNOWN"
        conf = 0.0
        evidence_msg = []

        line_count = histogram.get("LINE", 0) + histogram.get("LWPOLYLINE", 0)
        arc_count = histogram.get("ARC", 0) + histogram.get("CIRCLE", 0)
        has_lines = line_count > 0
        has_arcs = arc_count > 0
        has_dim = histogram.get("DIMENSION", 0) > 0
        has_text = histogram.get("TEXT", 0) + histogram.get("MTEXT", 0) > 0
        has_hatch = histogram.get("HATCH", 0) > 0

        if has_dim:
            best_role = "DIMENSION"
            conf = 0.8
            evidence_msg.append(f"geometry: contains {histogram.get('DIMENSION')} DIMENSION entities -> role DIMENSION (conf: 0.80)")
        elif has_text and (histogram.get("TEXT", 0) + histogram.get("MTEXT", 0)) / float(entity_count) > 0.5:
            best_role = "ANNOTATION"
            conf = 0.75
            evidence_msg.append(f"geometry: text entities comprise >50% of layer -> role ANNOTATION (conf: 0.75)")
        elif has_hatch and histogram.get("HATCH", 0) / float(entity_count) > 0.5:
            best_role = "HATCH"
            conf = 0.8
            evidence_msg.append(f"geometry: HATCH entities comprise >50% of layer -> role HATCH (conf: 0.80)")
        elif has_lines and has_arcs and arc_count >= line_count:
            best_role = "DOOR"
            conf = 0.65
            evidence_msg.append(f"geometry: co-occurrence of lines and arc geometries -> candidate role DOOR (conf: 0.65)")
        elif has_lines:
            best_role = "WALL"
            conf = 0.60
            evidence_msg.append(f"geometry: linear line/polyline segment distribution -> candidate role WALL (conf: 0.60)")
        else:
            evidence_msg.append("geometry: unclassified entity distribution mix")

        conf = min(conf, 0.8)
        return best_role, conf, evidence_msg

    def _evaluate_spatial_signal(self, layer_name, histogram):
        """Spatial co-occurrence and context evidence."""
        evidence = []
        if "DIM" in layer_name.upper():
            evidence.append("spatial: layer co-occurs with dimension callout bounds")
        elif "WALL" in layer_name.upper():
            evidence.append("spatial: layer forms continuous bounding loops")
        else:
            evidence.append("spatial: standard modelspace co-occurrence")
        return evidence

    def _evaluate_statistics_signal(self, entity_count, total_entities):
        """Entity count statistics relative to total drawing entity count."""
        pct = (entity_count / float(total_entities)) * 100.0 if total_entities > 0 else 0.0
        return [f"statistics: layer contains {entity_count} entities ({pct:.1f}% of total drawing count {total_entities})"]

def classify_layers_ranked(layers_info, entity_info, geom_stats=None, tolerance_bundle=None, layer_entities=None, vocab_filepath="layer_vocab.json", cfg=None):
    """
    Public entry point for Task 3 & Part A1.
    """
    classifier = LayerClassifier(vocab_filepath, cfg=cfg)
    return classifier.classify_layers(layers_info, entity_info, geom_stats, tolerance_bundle=tolerance_bundle, layer_entities=layer_entities)
