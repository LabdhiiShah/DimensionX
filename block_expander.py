"""
Block / INSERT Expander Module (Layer 1 Ingestion - Task 1)
===========================================================
WHAT THIS MODULE DOES:
- Recursively expands nested INSERT entities in a DXF modelspace to modelspace coordinate frame.
- Applies affine transformations: translation, rotation, 2D/3D scaling, and mirroring.
- Handles non-uniform scaling (Sx != Sy) on ARCs/CIRCLEs by approximating them as elliptical polylines tagged with `approximated: true`.
- Detects circular block references without infinite loops and skips anonymous blocks referenced only by DIMENSION entities.
- Attaches complete provenance records (block name, parent INSERT handle, nesting path).

WHAT THIS MODULE DOES NOT DO:
- Does NOT perform curve-to-polyline chord tolerance normalization for unscaled modelspace entities (handled by `normalizer.py`).
- Does NOT perform topological vertex welding, line merging, or endpoint snapping.
- Does NOT perform wall, door, or window role classification.
- Does NOT construct room polygons or building footprints.
"""

import math
import numpy as np
from collections import defaultdict
import ezdxf
from ezdxf.math import Matrix44

def transform_point_2d(pt, matrix):
    """Applies a 4x4 transformation matrix to a 2D point (x, y)."""
    v = matrix.transform((pt[0], pt[1], 0.0))
    return (round(v.x, 4), round(v.y, 4))

def approximate_scaled_arc(center, radius, start_angle_deg, end_angle_deg, matrix, num_segments=16):
    """
    Approximates an arc/circle under non-uniform scaling matrix by sampling points along the transformed curve.
    Returns list of 2D points representing the resulting polyline.
    """
    start_rad = math.radians(start_angle_deg)
    end_rad = math.radians(end_angle_deg)
    if end_rad < start_rad:
        end_rad += 2.0 * math.pi
        
    angles = np.linspace(start_rad, end_rad, num=num_segments)
    points = []
    for a in angles:
        local_x = center[0] + radius * math.cos(a)
        local_y = center[1] + radius * math.sin(a)
        pt_trans = transform_point_2d((local_x, local_y), matrix)
        points.append(pt_trans)
        
    return points

class BlockExpander:
    def __init__(self, doc):
        self.doc = doc
        self.msp = doc.modelspace()
        self.blocks = doc.blocks
        self.expanded_entities = []
        self.expanded_count = 0
        self.max_nesting_depth = 0
        self.circular_refs_detected = []
        self.skipped_dimension_anonymous_blocks = 0

        # Build mapping of anonymous blocks referenced by DIMENSION entities
        self.dim_anonymous_blocks = set()
        for e in self.msp.query('DIMENSION'):
            block_name = getattr(e.dxf, 'geometry', None) or getattr(e.dxf, 'name', None)
            if block_name and block_name.startswith('*D'):
                self.dim_anonymous_blocks.add(block_name.upper())

    def expand_all(self):
        """
        Processes all modelspace entities. Non-INSERT entities are passed through.
        INSERT entities are expanded recursively.
        """
        self.expanded_entities = []
        self.expanded_count = 0
        self.max_nesting_depth = 0
        self.circular_refs_detected = []
        self.skipped_dimension_anonymous_blocks = 0

        for entity in self.msp:
            if entity.dxftype() == 'INSERT':
                self._expand_insert(entity, transform_matrix=Matrix44(), nesting_stack=[("*Model_Space", entity.dxf.handle)], current_depth=1)
            else:
                self.expanded_entities.append(self._wrap_modelspace_entity(entity))

        return {
            "expanded_entities": self.expanded_entities,
            "expanded_insert_count": self.expanded_count,
            "max_nesting_depth": self.max_nesting_depth,
            "circular_references_detected": self.circular_refs_detected,
            "skipped_dimension_anonymous_blocks_count": self.skipped_dimension_anonymous_blocks
        }

    def _wrap_modelspace_entity(self, entity):
        """Wraps a standard un-expanded modelspace entity into a uniform normalized dictionary."""
        return {
            "entity_type": entity.dxftype(),
            "handle": entity.dxf.handle,
            "layer": entity.dxf.layer,
            "dxf_entity": entity,
            "is_expanded_from_block": False,
            "provenance": {
                "source_file": getattr(self.doc, 'filename', 'UNKNOWN'),
                "nesting_path": ["*Model_Space"],
                "block_name": None,
                "parent_insert_handle": None
            },
            "approximated": False,
            "approximation_reason": None
        }

    def _expand_insert(self, insert_entity, transform_matrix, nesting_stack, current_depth):
        block_name = insert_entity.dxf.name
        block_name_upper = block_name.upper()

        # Update max depth metric
        if current_depth > self.max_nesting_depth:
            self.max_nesting_depth = current_depth

        # Task 1 Requirement: Skip anonymous blocks referenced only by DIMENSION entities
        if block_name_upper.startswith('*D') or block_name_upper in self.dim_anonymous_blocks:
            self.skipped_dimension_anonymous_blocks += 1
            return

        # Task 1 Requirement: Detect and flag circular block references
        visited_block_names = [item[0] for item in nesting_stack]
        if block_name in visited_block_names:
            self.circular_refs_detected.append({
                "block_name": block_name,
                "insert_handle": insert_entity.dxf.handle,
                "nesting_stack": list(nesting_stack)
            })
            print(f"[BlockExpander] WARNING: Circular block reference detected for '{block_name}' at stack {nesting_stack}. Stopping recursion.")
            return

        if block_name not in self.blocks:
            print(f"[BlockExpander] WARNING: Referenced block '{block_name}' not found in DXF block table.")
            return

        block_def = self.blocks[block_name]
        self.expanded_count += 1

        # Compute affine transformation matrix for INSERT
        insert_pos = insert_entity.dxf.insert
        scale_x = getattr(insert_entity.dxf, 'xscale', 1.0)
        scale_y = getattr(insert_entity.dxf, 'yscale', 1.0)
        scale_z = getattr(insert_entity.dxf, 'zscale', 1.0)
        rotation_deg = getattr(insert_entity.dxf, 'rotation', 0.0)

        # Build local transformation matrix: Scale -> Rotate -> Translate
        local_matrix = Matrix44.chain(
            Matrix44.scale(scale_x, scale_y, scale_z),
            Matrix44.z_rotate(math.radians(rotation_deg)),
            Matrix44.translate(insert_pos[0], insert_pos[1], insert_pos[2])
        )

        # Combine with parent transformation matrix
        combined_matrix = local_matrix * transform_matrix

        is_non_uniform_scale = abs(abs(scale_x) - abs(scale_y)) > 1e-4
        new_stack = nesting_stack + [(block_name, insert_entity.dxf.handle)]

        for e in block_def:
            etype = e.dxftype()

            if etype == 'INSERT':
                # Recursive expansion of nested INSERT
                self._expand_insert(e, combined_matrix, new_stack, current_depth + 1)
            else:
                expanded_obj = self._transform_block_entity(
                    e, combined_matrix, is_non_uniform_scale, block_name, insert_entity.dxf.handle, new_stack
                )
                if expanded_obj:
                    self.expanded_entities.append(expanded_obj)

    def _transform_block_entity(self, entity, matrix, is_non_uniform_scale, block_name, parent_handle, nesting_path):
        etype = entity.dxftype()
        layer = entity.dxf.layer
        handle = entity.dxf.handle

        prov = {
            "source_file": getattr(self.doc, 'filename', 'UNKNOWN'),
            "nesting_path": [item[0] for item in nesting_path],
            "block_name": block_name,
            "parent_insert_handle": parent_handle,
            "original_entity_handle": handle
        }

        # LINE entity transformation
        if etype == 'LINE':
            p1 = transform_point_2d((entity.dxf.start[0], entity.dxf.start[1]), matrix)
            p2 = transform_point_2d((entity.dxf.end[0], entity.dxf.end[1]), matrix)
            return {
                "entity_type": "LINE",
                "handle": handle,
                "layer": layer,
                "p1": p1, "p2": p2,
                "is_expanded_from_block": True,
                "provenance": prov,
                "approximated": False,
                "approximation_reason": None
            }

        # LWPOLYLINE entity transformation
        elif etype in ('LWPOLYLINE', 'POLYLINE'):
            pts = list(entity.get_points('xy'))
            trans_pts = [transform_point_2d((pt[0], pt[1]), matrix) for pt in pts]
            
            # Preserve width attribute if present
            start_width = getattr(entity.dxf, 'const_width', None) or getattr(entity.dxf, 'start_width', 0.0)
            
            return {
                "entity_type": "LWPOLYLINE",
                "handle": handle,
                "layer": layer,
                "points": trans_pts,
                "closed": entity.closed,
                "width": start_width if start_width > 0 else 0.0,
                "is_expanded_from_block": True,
                "provenance": prov,
                "approximated": False,
                "approximation_reason": None
            }

        # ARC / CIRCLE entity transformation (Task 1 Requirement for Non-uniform scale)
        elif etype in ('ARC', 'CIRCLE'):
            center = (entity.dxf.center[0], entity.dxf.center[1])
            radius = entity.dxf.radius
            start_deg = getattr(entity.dxf, 'start_angle', 0.0)
            end_deg = getattr(entity.dxf, 'end_angle', 360.0) if etype == 'ARC' else 360.0

            if is_non_uniform_scale:
                # Approximate ellipse resulting from non-uniform scaling as a polyline
                poly_pts = approximate_scaled_arc(center, radius, start_deg, end_deg, matrix)
                return {
                    "entity_type": "LWPOLYLINE",
                    "handle": handle,
                    "layer": layer,
                    "points": poly_pts,
                    "closed": (etype == 'CIRCLE'),
                    "is_expanded_from_block": True,
                    "provenance": prov,
                    "approximated": True,
                    "approximation_reason": f"Non-uniform scale (Sx!=Sy) on curved {etype} inside block '{block_name}' converted arc to polyline"
                }
            else:
                # Uniform scale: transform center and scale radius
                trans_center = transform_point_2d(center, matrix)
                v0 = matrix.transform((0.0, 0.0, 0.0))
                v1 = matrix.transform((1.0, 0.0, 0.0))
                sx = math.hypot(v1.x - v0.x, v1.y - v0.y)
                trans_radius = round(radius * sx, 4)
                return {
                    "entity_type": etype,
                    "handle": handle,
                    "layer": layer,
                    "center": trans_center,
                    "radius": trans_radius,
                    "start_angle": start_deg,
                    "end_angle": end_deg,
                    "is_expanded_from_block": True,
                    "provenance": prov,
                    "approximated": False,
                    "approximation_reason": None
                }

        # TEXT / MTEXT entity transformation
        elif etype in ('TEXT', 'MTEXT'):
            txt = entity.text if etype == 'MTEXT' else entity.dxf.text
            pos = transform_point_2d((entity.dxf.insert[0], entity.dxf.insert[1]), matrix)
            return {
                "entity_type": etype,
                "handle": handle,
                "layer": layer,
                "text": txt,
                "position": pos,
                "is_expanded_from_block": True,
                "provenance": prov,
                "approximated": False,
                "approximation_reason": None
            }

        else:
            # Fallback for other block sub-entities
            return {
                "entity_type": etype,
                "handle": handle,
                "layer": layer,
                "is_expanded_from_block": True,
                "provenance": prov,
                "approximated": False,
                "approximation_reason": None
            }

def expand_blocks(doc):
    """
    Public entry point for Task 1.
    Takes a parsed DXF document and returns the expanded entity list and execution summary.
    """
    expander = BlockExpander(doc)
    return expander.expand_all()
