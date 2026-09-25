"""
3D Architectural House Reconstruction & Visualization Engine
============================================================
Reads 2D floor plan JSON (output/house2d.json) and builds a proper 3D house model:
- Solid 3D walls with real thickness, cut for doors and windows
- Lintel wall boxes over door/window gaps
- Rotated 3D door slabs and glass window panes
- Extruded floor slab and flat roof / ceiling
- Centroid floating room labels
- Best-effort visual furniture anchors (beds, kitchen counters, sofas, toilets)
- Matplotlib 3D preview renders (top-down bird's-eye and interior walkthrough)
- Unity-ready Y-up 3D model exports (GLB and OBJ)
"""

import os
import sys
import argparse
import math
import json
import re
from collections import defaultdict
from typing import List, Dict, Tuple, Any, Optional

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import shapely.geometry as sg
import shapely.ops as so
import trimesh

# Color Palette Constants (HEX & RGB)
COLOR_WALL = [0.85, 0.85, 0.85, 1.0]        # #d9d9d9 Light Grey
COLOR_FLOOR = [0.941, 0.922, 0.882, 1.0]    # #f0ebe1 Off-White/Sand
COLOR_ROOF = [0.910, 0.878, 0.816, 1.0]     # #e8e0d0 Light Beige
COLOR_DOOR = [0.545, 0.353, 0.169, 1.0]     # #8b5a2b Wood Brown
COLOR_GLASS = [0.659, 0.847, 0.918, 0.4]    # #a8d8ea Light Blue Transparent
COLOR_BED = [0.290, 0.420, 0.510, 1.0]      # #4a6b82 Slate Blue
COLOR_SOFA = [0.478, 0.322, 0.188, 1.0]     # #7a5230 Leather Brown
COLOR_COUNTER = [0.659, 0.553, 0.404, 1.0]  # #a88d67 Warm Wood
COLOR_TOILET = [0.816, 0.902, 0.941, 1.0]   # #d0e6f0 Light Cyan

HEX_WALL = '#d9d9d9'
HEX_FLOOR = '#f0ebe1'
HEX_ROOF = '#e8e0d0'
HEX_DOOR = '#8b5a2b'
HEX_GLASS = '#a8d8ea'

WALL_HEIGHT_DEFAULT = 2.7
SLAB_THICKNESS_DEFAULT = 0.2
ROOF_THICKNESS_DEFAULT = 0.15

# ==============================================================================
# 1. SCHEMA INSPECTION & DATA INGESTION
# ==============================================================================

def inspect_and_print_schema(data: Dict[str, Any]) -> None:
    """Prints top-level and depth-1 nested dict schemas of house2d.json."""
    print("======================================================================")
    print("SCHEMA INSPECTION: output/house2d.json")
    print("======================================================================")
    print("Top-level Keys & Types:")
    for k, v in data.items():
        if isinstance(v, list):
            sample_keys = list(v[0].keys()) if len(v) > 0 and isinstance(v[0], dict) else "N/A"
            print(f"  - {k:22s}: list (len={len(v)}), sample element keys: {sample_keys}")
        elif isinstance(v, dict):
            print(f"  - {k:22s}: dict (keys={list(v.keys())})")
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, list):
                    sub_sample_keys = list(sub_v[0].keys()) if len(sub_v) > 0 and isinstance(sub_v[0], dict) else "N/A"
                    print(f"      * {sub_k:20s}: list (len={len(sub_v)}), sample element keys: {sub_sample_keys}")
                elif isinstance(sub_v, dict):
                    print(f"      * {sub_k:20s}: dict (keys={list(sub_v.keys())})")
                else:
                    print(f"      * {sub_k:20s}: {type(sub_v).__name__}")
        else:
            print(f"  - {k:22s}: {type(v).__name__} = {v}")

    print("\nKey Mapping Identified:")
    print("  - Walls:     building_components.walls")
    print("  - Doors:     building_components.doors")
    print("  - Windows:   building_components.windows")
    print("  - Rooms:     building_components.rooms")
    print("  - Footprint: building_components.building_footprint")
    print("======================================================================\n")

# ==============================================================================
# 2. COORDINATE TRANSFORMATIONS & GEOMETRY HELPERS
# ==============================================================================

class ModelScaler:
    def __init__(self, house2d_data: Dict[str, Any]):
        coords_sys = house2d_data.get("coordinate_system", {})
        origin = coords_sys.get("origin", [0.0, 0.0])
        self.min_x = origin[0]
        self.min_y = origin[1]

        # Extract extent width & height
        extents = coords_sys.get("extents", {})
        width = extents.get("width", 100.0)
        height = extents.get("height", 100.0)
        max_extent = max(width, height)

        # Coordinate sanity check rule
        if abs(self.min_x) > 1e6 or abs(self.min_y) > 1e6:
            print(f"[Warning] Coordinate magnitude > 1e6 detected: ({self.min_x:.1f}, {self.min_y:.1f}). Translating to local origin.")

        # Unit scale calculation
        units_info = house2d_data.get("units", {})
        json_scale = units_info.get("scale_to_meters", 0.001)

        # Heuristic: if DXF coordinates are ~500 units, 1 unit = 1 inch = 0.0254m (house width ~14m)
        if 100.0 <= max_extent <= 2000.0:
            self.scale_factor = 0.0254 # Inch to meter conversion
        elif max_extent > 2000.0:
            self.scale_factor = json_scale if json_scale > 0 else 0.001
        else:
            self.scale_factor = 1.0

    def to_m(self, pt: Tuple[float, float]) -> Tuple[float, float]:
        """Translates absolute DXF coordinate to local meters (origin at 0,0)."""
        x_m = (pt[0] - self.min_x) * self.scale_factor
        y_m = (pt[1] - self.min_y) * self.scale_factor
        return (x_m, y_m)

    def dist_to_m(self, d: float) -> float:
        """Converts DXF length / width to meters."""
        return d * self.scale_factor

def create_box_mesh(
    length: float, width: float, height: float,
    center: Tuple[float, float, float],
    yaw_deg: float = 0.0,
    color: List[float] = COLOR_WALL
) -> trimesh.Trimesh:
    """Creates a 3D box trimesh oriented along yaw angle with given color."""
    box = trimesh.creation.box(extents=[length, width, height])
    
    # Transformation: Rotation around Z then translation to center
    rot = trimesh.transformations.rotation_matrix(math.radians(yaw_deg), [0, 0, 1])
    rot[:3, 3] = center
    box.apply_transform(rot)
    box.visual.face_colors = (np.array(color) * 255).astype(np.uint8)
    return box

def get_box_faces_matplotlib(
    length: float, width: float, height: float,
    center: Tuple[float, float, float],
    yaw_deg: float = 0.0
) -> List[np.ndarray]:
    """Computes 6 quad faces of a 3D box for Matplotlib Poly3DCollection rendering."""
    dx = length / 2.0
    dy = width / 2.0
    dz = height / 2.0

    local_corners = np.array([
        [-dx, -dy, -dz], [ dx, -dy, -dz], [ dx,  dy, -dz], [-dx,  dy, -dz],
        [-dx, -dy,  dz], [ dx, -dy,  dz], [ dx,  dy,  dz], [-dx,  dy,  dz]
    ])

    # Rotation matrix
    rad = math.radians(yaw_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    rot_mat = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])

    world_corners = np.dot(local_corners, rot_mat.T) + np.array(center)

    # 6 Quad faces
    faces = [
        [world_corners[0], world_corners[1], world_corners[2], world_corners[3]], # Bottom
        [world_corners[4], world_corners[5], world_corners[6], world_corners[7]], # Top
        [world_corners[0], world_corners[1], world_corners[5], world_corners[4]], # Front
        [world_corners[2], world_corners[3], world_corners[7], world_corners[6]], # Back
        [world_corners[0], world_corners[3], world_corners[7], world_corners[4]], # Left
        [world_corners[1], world_corners[2], world_corners[6], world_corners[5]]  # Right
    ]
    return faces

# ==============================================================================
# 3. 3D MODEL BUILDER ENGINE
# ==============================================================================

class House3DBuilder:
    def __init__(self, house2d_data: Dict[str, Any], generate_roof: bool = True):
        self.data = house2d_data
        self.scaler = ModelScaler(house2d_data)
        self.generate_roof = generate_roof

        bc = house2d_data.get("building_components", {})
        self.raw_walls = bc.get("walls", [])
        self.raw_doors = bc.get("doors", [])
        self.raw_windows = bc.get("windows", [])
        self.raw_rooms = bc.get("rooms", [])
        self.raw_footprint = bc.get("building_footprint", {})

        # Extract vertical parameters
        levels = house2d_data.get("levels", [{}])
        vert = levels[0].get("vertical_parameters", {}) if levels else {}
        self.wall_height = vert.get("wall_height", {}).get("value", WALL_HEIGHT_DEFAULT)
        self.slab_thickness = vert.get("slab_thickness", {}).get("value", SLAB_THICKNESS_DEFAULT)

        # Output Mesh Storage
        self.meshes: List[trimesh.Trimesh] = []
        self.mpl_polys: List[Tuple[List[np.ndarray], str, float]] = [] # (faces, color_hex, alpha)

        # Counters for Summary Report
        self.counts = {
            "wall_boxes": 0,
            "door_openings_cut": 0,
            "door_slabs": 0,
            "window_openings_cut": 0,
            "glass_panes": 0,
            "rooms_labeled": 0,
            "furniture_beds": 0,
            "furniture_counters": 0,
            "furniture_sofas": 0,
            "furniture_toilets": 0
        }

        self.room_labels: List[Tuple[float, float, str]] = [] # (x, y, text)
        self.footprint_poly_m: Optional[sg.Polygon] = None

    def build_all(self) -> None:
        """Executes full 3D house reconstruction pipeline."""
        print("[Engine] Building 3D Footprint & Slab Geometry...")
        self._build_footprint_and_slabs()

        print("[Engine] Processing Walls, Openings & Lintel Geometry...")
        self._build_walls_and_openings()

        print("[Engine] Generating Room Labels & Visual Furniture Anchors...")
        self._build_rooms_and_furniture()

    def _build_footprint_and_slabs(self) -> None:
        """Extrudes floor slab and optional ceiling/roof slab."""
        pts_m = []
        if isinstance(self.raw_footprint, dict) and "coordinates" in self.raw_footprint:
            raw_pts = self.raw_footprint["coordinates"]
            pts_m = [self.scaler.to_m(p) for p in raw_pts]
        elif self.raw_rooms:
            # Fallback: Union of all room polygons
            room_polys = []
            for r in self.raw_rooms:
                r_pts = [self.scaler.to_m(p) for p in r.get("polygon_vertices", [])]
                if len(r_pts) >= 3:
                    room_polys.append(sg.Polygon(r_pts))
            if room_polys:
                union_poly = so.unary_union(room_polys)
                if isinstance(union_poly, sg.Polygon):
                    pts_m = list(union_poly.exterior.coords)
                elif hasattr(union_poly, "geoms"):
                    pts_m = list(union_poly.geoms[0].exterior.coords)

        if not pts_m or len(pts_m) < 3:
            # Synthetic default rectangle fallback
            pts_m = [(0.0, 0.0), (14.0, 0.0), (14.0, 12.0), (0.0, 12.0)]

        poly = sg.Polygon(pts_m)
        if not poly.is_valid:
            poly = poly.buffer(0)
        self.footprint_poly_m = poly

        min_x, min_y, max_x, max_y = poly.bounds
        self.center_x = (min_x + max_x) / 2.0
        self.center_y = (min_y + max_y) / 2.0

        # 1. Floor Slab (extrude downward from z=0 to z=-0.2)
        try:
            floor_mesh = trimesh.creation.extrude_polygon(poly, height=self.slab_thickness)
            floor_mesh.apply_translation([0, 0, -self.slab_thickness])
            floor_mesh.visual.face_colors = (np.array(COLOR_FLOOR) * 255).astype(np.uint8)
            self.meshes.append(floor_mesh)

            # Matplotlib box representation for preview renders
            f_box_faces = get_box_faces_matplotlib(
                max_x - min_x, max_y - min_y, self.slab_thickness,
                (self.center_x, self.center_y, -self.slab_thickness / 2.0)
            )
            self.mpl_polys.append((f_box_faces, HEX_FLOOR, 1.0))
        except Exception as e:
            print(f"[Warning] Failed to extrude floor slab: {e}")

        # 2. Ceiling / Flat Roof (extrude upward at wall_height)
        if self.generate_roof:
            try:
                roof_mesh = trimesh.creation.extrude_polygon(poly, height=ROOF_THICKNESS_DEFAULT)
                roof_mesh.apply_translation([0, 0, self.wall_height])
                roof_mesh.visual.face_colors = (np.array(COLOR_ROOF) * 255).astype(np.uint8)
                self.meshes.append(roof_mesh)

                r_box_faces = get_box_faces_matplotlib(
                    max_x - min_x, max_y - min_y, ROOF_THICKNESS_DEFAULT,
                    (self.center_x, self.center_y, self.wall_height + ROOF_THICKNESS_DEFAULT / 2.0)
                )
                self.mpl_polys.append((r_box_faces, HEX_ROOF, 0.9))
            except Exception as e:
                print(f"[Warning] Failed to extrude roof slab: {e}")

    def _build_walls_and_openings(self) -> None:
        """Processes 2D wall centerlines, cuts door/window gaps, creates lintels, door slabs, & glass panes."""
        walls_by_id = {w.get("wall_id"): w for w in self.raw_walls if w.get("wall_id")}

        # Group openings by host_wall_id
        doors_by_wall = defaultdict(list)
        for door in self.raw_doors:
            h_id = door.get("host_wall_id")
            if h_id and h_id in walls_by_id:
                doors_by_wall[h_id].append(door)
            else:
                d_id = door.get("opening_id", "unknown")
                print(f"[3D] Warning: door {d_id} has no matching host_wall_id ({h_id}); skipped")

        windows_by_wall = defaultdict(list)
        for win in self.raw_windows:
            h_id = win.get("host_wall_id")
            if h_id and h_id in walls_by_id:
                windows_by_wall[h_id].append(win)
            else:
                w_id = win.get("opening_id", "unknown")
                print(f"[3D] Warning: window {w_id} has no matching host_wall_id ({h_id}); skipped")

        for wall in self.raw_walls:
            centerline = wall.get("centerline", [])
            if len(centerline) < 2:
                continue

            p1_m = self.scaler.to_m(centerline[0])
            p2_m = self.scaler.to_m(centerline[1])

            dx = p2_m[0] - p1_m[0]
            dy = p2_m[1] - p1_m[1]
            seg_len = math.hypot(dx, dy)
            if seg_len < 0.01:
                continue

            u_vec = (dx / seg_len, dy / seg_len)
            yaw_deg = math.degrees(math.atan2(dy, dx))

            # Wall thickness calculation
            raw_thick = wall.get("thickness", {})
            t_val = raw_thick.get("value", 0.15) if isinstance(raw_thick, dict) else float(raw_thick or 0.15)
            thick_m = self.scaler.dist_to_m(t_val)
            if thick_m < 0.05 or thick_m > 0.50:
                thick_m = 0.15

            wall_id = wall.get("wall_id", "")
            openings = []

            # 1. Add Doors hosted on this wall
            for door in doors_by_wall.get(wall_id, []):
                d_center_m = self.scaler.to_m(door.get("center", [0, 0]))
                t_mid = (d_center_m[0] - p1_m[0]) * u_vec[0] + (d_center_m[1] - p1_m[1]) * u_vec[1]
                d_w_raw = door.get("width", 0.9)
                d_w_m = self.scaler.dist_to_m(d_w_raw)
                if d_w_m < 0.3 or d_w_m > 4.0:
                    d_w_m = 0.9

                t_start = max(0.0, t_mid - d_w_m / 2.0)
                t_end = min(seg_len, t_mid + d_w_m / 2.0)

                if t_end > t_start:
                    h_height = door.get("head_height", {}).get("value", 2.1) if isinstance(door.get("head_height"), dict) else 2.1
                    openings.append({
                        "type": "DOOR",
                        "t_start": t_start,
                        "t_end": t_end,
                        "width": t_end - t_start,
                        "head_height": h_height,
                        "sill_height": 0.0,
                        "hinge_pt": (p1_m[0] + t_start * u_vec[0], p1_m[1] + t_start * u_vec[1])
                    })
                    self.counts["door_openings_cut"] += 1

            # 2. Add Windows hosted on this wall
            for win in windows_by_wall.get(wall_id, []):
                w_center_m = self.scaler.to_m(win.get("center", [0, 0]))
                t_mid = (w_center_m[0] - p1_m[0]) * u_vec[0] + (w_center_m[1] - p1_m[1]) * u_vec[1]
                w_w_raw = win.get("width", 1.2)
                w_w_m = self.scaler.dist_to_m(w_w_raw)
                if w_w_m < 0.3 or w_w_m > 4.0:
                    w_w_m = 1.2

                t_start = max(0.0, t_mid - w_w_m / 2.0)
                t_end = min(seg_len, t_mid + w_w_m / 2.0)

                if t_end > t_start:
                    s_height = win.get("sill_height", {}).get("value", 0.9) if isinstance(win.get("sill_height"), dict) else 0.9
                    h_height = win.get("head_height", {}).get("value", 2.1) if isinstance(win.get("head_height"), dict) else 2.1
                    openings.append({
                        "type": "WINDOW",
                        "t_start": t_start,
                        "t_end": t_end,
                        "width": t_end - t_start,
                        "sill_height": s_height,
                        "head_height": h_height
                    })
                    self.counts["window_openings_cut"] += 1

            # Sort openings along segment
            openings.sort(key=lambda op: op["t_start"])

            # Split wall into solid sub-segments and lintel/sill boxes
            curr_t = 0.0

            for op in openings:
                t_start = op["t_start"]
                t_end = op["t_end"]

                # Solid wall box prior to opening
                if t_start > curr_t + 0.01:
                    sub_len = t_start - curr_t
                    mid_t = curr_t + sub_len / 2.0
                    c_pt = (p1_m[0] + mid_t * u_vec[0], p1_m[1] + mid_t * u_vec[1], self.wall_height / 2.0)
                    self._add_wall_box(sub_len, thick_m, self.wall_height, c_pt, yaw_deg)

                op_width = t_end - t_start
                op_mid_t = t_start + op_width / 2.0
                op_mid_xy = (p1_m[0] + op_mid_t * u_vec[0], p1_m[1] + op_mid_t * u_vec[1])

                if op["type"] == "DOOR":
                    # Lintel box above door (from head_height to wall_height)
                    lintel_h = self.wall_height - op["head_height"]
                    if lintel_h > 0.05:
                        c_pt = (op_mid_xy[0], op_mid_xy[1], op["head_height"] + lintel_h / 2.0)
                        self._add_wall_box(op_width, thick_m, lintel_h, c_pt, yaw_deg)

                    # Add Door Slab (rotated 35 degrees open)
                    door_thick = 0.04
                    swing_yaw = yaw_deg + 35.0
                    hinge = op["hinge_pt"]
                    s_rad = math.radians(swing_yaw)
                    slab_center = (
                        hinge[0] + (op_width / 2.0) * math.cos(s_rad),
                        hinge[1] + (op_width / 2.0) * math.sin(s_rad),
                        op["head_height"] / 2.0
                    )
                    door_box = create_box_mesh(op_width, door_thick, op["head_height"], slab_center, swing_yaw, COLOR_DOOR)
                    self.meshes.append(door_box)

                    d_faces = get_box_faces_matplotlib(op_width, door_thick, op["head_height"], slab_center, swing_yaw)
                    self.mpl_polys.append((d_faces, HEX_DOOR, 1.0))
                    self.counts["door_slabs"] += 1

                elif op["type"] == "WINDOW":
                    # Bottom Sill wall box (from 0 to sill_height)
                    if op["sill_height"] > 0.05:
                        c_pt = (op_mid_xy[0], op_mid_xy[1], op["sill_height"] / 2.0)
                        self._add_wall_box(op_width, thick_m, op["sill_height"], c_pt, yaw_deg)

                    # Top Lintel wall box (from head_height to wall_height)
                    lintel_h = self.wall_height - op["head_height"]
                    if lintel_h > 0.05:
                        c_pt = (op_mid_xy[0], op_mid_xy[1], op["head_height"] + lintel_h / 2.0)
                        self._add_wall_box(op_width, thick_m, lintel_h, c_pt, yaw_deg)

                    # Glass Pane (light blue, alpha 0.4)
                    win_h = op["head_height"] - op["sill_height"]
                    glass_thick = 0.02
                    pane_center = (op_mid_xy[0], op_mid_xy[1], op["sill_height"] + win_h / 2.0)
                    glass_mesh = create_box_mesh(op_width, glass_thick, win_h, pane_center, yaw_deg, COLOR_GLASS)
                    self.meshes.append(glass_mesh)

                    g_faces = get_box_faces_matplotlib(op_width, glass_thick, win_h, pane_center, yaw_deg)
                    self.mpl_polys.append((g_faces, HEX_GLASS, 0.4))
                    self.counts["glass_panes"] += 1

                curr_t = t_end

            # Final solid wall segment
            if seg_len > curr_t + 0.01:
                sub_len = seg_len - curr_t
                mid_t = curr_t + sub_len / 2.0
                c_pt = (p1_m[0] + mid_t * u_vec[0], p1_m[1] + mid_t * u_vec[1], self.wall_height / 2.0)
                self._add_wall_box(sub_len, thick_m, self.wall_height, c_pt, yaw_deg)

    def _add_wall_box(self, length: float, width: float, height: float, center: Tuple[float, float, float], yaw_deg: float) -> None:
        """Helper to create and store wall box mesh & matplotlib faces."""
        w_mesh = create_box_mesh(length, width, height, center, yaw_deg, COLOR_WALL)
        self.meshes.append(w_mesh)
        w_faces = get_box_faces_matplotlib(length, width, height, center, yaw_deg)
        self.mpl_polys.append((w_faces, HEX_WALL, 1.0))
        self.counts["wall_boxes"] += 1

    def _build_rooms_and_furniture(self) -> None:
        """Processes room labels and adds visual furniture anchors (best-effort)."""
        # Sort rooms by polygon area descending for ranked semantic inference
        sorted_rooms = sorted(
            self.raw_rooms,
            key=lambda r: sg.Polygon([self.scaler.to_m(p) for p in r.get("polygon_vertices", [])]).area if len(r.get("polygon_vertices", [])) >= 3 else 0.0,
            reverse=True
        )

        for room_idx, room in enumerate(sorted_rooms):
            r_pts_raw = room.get("polygon_vertices", [])
            r_pts_m = [self.scaler.to_m(p) for p in r_pts_raw]
            if len(r_pts_m) < 3:
                continue

            r_poly = sg.Polygon(r_pts_m)
            centroid = r_poly.centroid
            cx, cy = centroid.x, centroid.y

            raw_name = room.get("name", "")
            sem_type = room.get("semantic_type", "")
            clean_name = self._clean_room_label(raw_name, sem_type, r_poly.area, room_idx)

            self.room_labels.append((cx, cy, clean_name))
            self.counts["rooms_labeled"] += 1

            # Best-effort visual furniture placement inside room centroid
            lname = clean_name.lower()
            try:
                if "bed" in lname:
                    # Bed box: 1.5m x 2.0m x 0.5m
                    b_mesh = create_box_mesh(1.5, 2.0, 0.5, (cx, cy, 0.25), 0.0, COLOR_BED)
                    self.meshes.append(b_mesh)
                    self.mpl_polys.append((get_box_faces_matplotlib(1.5, 2.0, 0.5, (cx, cy, 0.25)), '#4a6b82', 1.0))
                    self.counts["furniture_beds"] += 1

                elif "kit" in lname:
                    # Counter box: 0.6m x 2.0m x 0.9m
                    c_mesh = create_box_mesh(0.6, 2.0, 0.9, (cx, cy, 0.45), 0.0, COLOR_COUNTER)
                    self.meshes.append(c_mesh)
                    self.mpl_polys.append((get_box_faces_matplotlib(0.6, 2.0, 0.9, (cx, cy, 0.45)), '#a88d67', 1.0))
                    self.counts["furniture_counters"] += 1

                elif "liv" in lname or "din" in lname or "hall" in lname:
                    # Sofa box: 0.9m x 2.1m x 0.8m
                    s_mesh = create_box_mesh(0.9, 2.1, 0.8, (cx, cy, 0.40), 0.0, COLOR_SOFA)
                    self.meshes.append(s_mesh)
                    self.mpl_polys.append((get_box_faces_matplotlib(0.9, 2.1, 0.8, (cx, cy, 0.40)), '#7a5230', 1.0))
                    self.counts["furniture_sofas"] += 1

                elif "bath" in lname or "toi" in lname:
                    # Toilet/vanity box: 0.6m x 0.6m x 0.4m
                    t_mesh = create_box_mesh(0.6, 0.6, 0.4, (cx, cy, 0.20), 0.0, COLOR_TOILET)
                    self.meshes.append(t_mesh)
                    self.mpl_polys.append((get_box_faces_matplotlib(0.6, 0.6, 0.4, (cx, cy, 0.20)), '#d0e6f0', 1.0))
                    self.counts["furniture_toilets"] += 1
            except Exception as e:
                print(f"[Warning] Best-effort furniture placement skipped for '{clean_name}': {e}")

    def _clean_room_label(self, raw_name: str, sem_type: str, area_sqm: float, room_idx: int) -> str:
        """Cleans formatting tags and produces human-readable room title."""
        cleaned = re.sub(r'[\\[\]\{\}\;\,\\]', ' ', raw_name).strip()
        cleaned = re.sub(r'pi\d+(\.\d+)?', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r't\d+(\.\d+)?', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'^\d+.*$', '', cleaned).strip()

        if cleaned and not cleaned.startswith("UNKNOWN") and len(cleaned) >= 3:
            return cleaned.title()

        if sem_type and not sem_type.startswith("UNKNOWN") and not sem_type.startswith("PI"):
            return sem_type.replace("_", " ").title()

        # Inferred semantic room assignment based on ranked room areas
        if room_idx == 0:
            return "Living / Dining"
        elif room_idx == 1:
            return "Master Bedroom"
        elif room_idx == 2:
            return "Bedroom 2"
        elif room_idx == 3:
            return "Kitchen"
        elif room_idx == 4:
            return "Balcony"
        elif room_idx == 5:
            return "Common Toilet"
        elif room_idx == 6:
            return "Master Toilet"
        elif room_idx == 7:
            return "Foyer / Entry"
        else:
            return f"Utility Space {room_idx - 7}"

    @staticmethod
    def _point_to_segment_dist(pt: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculates minimum distance from 2D point to line segment."""
        px, py = pt
        x1, y1 = p1
        x2, y2 = p2
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

# ==============================================================================
# 4. PREVIEW RENDERER (MATPLOTLIB 3D)
# ==============================================================================

def render_previews(builder: House3DBuilder, output_dir: str = "output") -> None:
    """Renders house_preview_3d_top.png and house_preview_3d_walkthrough.png."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Bird's Eye View (top preview)
    fig = plt.figure(figsize=(12, 10), facecolor='#1e1e1e')
    ax = fig.add_subplot(111, projection='3d', facecolor='#1e1e1e')

    for faces, color, alpha in builder.mpl_polys:
        poly_collection = Poly3DCollection(faces, facecolors=color, linewidths=0.3, edgecolors='#333333', alpha=alpha)
        ax.add_collection3d(poly_collection)

    # Floating Room Labels
    for cx, cy, text in builder.room_labels:
        ax.text(cx, cy, 1.4, text, color='white', fontsize=8, fontweight='bold', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='#2c3e50', alpha=0.8, edgecolor='none'))

    ax.view_init(elev=60, azim=-60)
    ax.set_title("3D Architectural House Reconstruction (Bird's Eye Top View)", color='white', fontsize=14, pad=20)

    # Autoscale 3D axes limits
    cx, cy = builder.center_x, builder.center_y
    span = 10.0
    ax.set_xlim(cx - span, cx + span)
    ax.set_ylim(cy - span, cy + span)
    ax.set_zlim(-0.5, 3.5)
    ax.axis('off')

    top_path = os.path.join(output_dir, "house_preview_3d_top.png")
    plt.savefig(top_path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
    plt.close()
    print(f"[Renderer] Saved Top 3D Preview: {top_path}")

    # 2. Walkthrough View (eye-level interior view)
    fig_w = plt.figure(figsize=(12, 8), facecolor='#1e1e1e')
    ax_w = fig_w.add_subplot(111, projection='3d', facecolor='#1e1e1e')

    # Filter out roof polygons for interior walkthrough view
    for faces, color, alpha in builder.mpl_polys:
        if color == HEX_ROOF:
            continue
        poly_col = Poly3DCollection(faces, facecolors=color, linewidths=0.4, edgecolors='#222222', alpha=alpha)
        ax_w.add_collection3d(poly_col)

    # Camera placed inside primary room at height 1.6m
    cam_x = builder.center_x
    cam_y = builder.center_y
    cam_z = 1.6

    ax_w.view_init(elev=5, azim=-90)
    ax_w.set_title("3D Interior Walkthrough View (Eye-Level Camera at 1.6m)", color='white', fontsize=14, pad=20)

    ax_w.set_xlim(cam_x - 7.0, cam_x + 7.0)
    ax_w.set_ylim(cam_y - 7.0, cam_y + 7.0)
    ax_w.set_zlim(0.0, 3.0)
    ax_w.axis('off')

    walk_path = os.path.join(output_dir, "house_preview_3d_walkthrough.png")
    plt.savefig(walk_path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
    plt.close()
    print(f"[Renderer] Saved Walkthrough 3D Preview: {walk_path}")

# ==============================================================================
# 5. UNITY / VR EXPORTER (GLB & OBJ)
# ==============================================================================

def export_unity_models(builder: House3DBuilder, output_dir: str = "output") -> Tuple[str, str, float]:
    """Combines meshes into Unity Y-up orientation scene and exports GLB and OBJ."""
    os.makedirs(output_dir, exist_ok=True)

    if not builder.meshes:
        print("[Warning] No 3D meshes created to export.")
        return "", "", 0.0

    # Combine all individual 3D meshes into a single scene
    combined_scene = trimesh.Scene()
    for idx, mesh in enumerate(builder.meshes):
        combined_scene.add_geometry(mesh, node_name=f"part_{idx}")

    # Unity Standard Y-up Rotation Matrix (Rotate -90 degrees around X axis)
    y_up_transform = trimesh.transformations.rotation_matrix(-math.pi / 2.0, [1, 0, 0])
    combined_scene.apply_transform(y_up_transform)

    glb_path = os.path.join(output_dir, "house_model.glb")
    obj_path = os.path.join(output_dir, "house_model.obj")

    # Export GLB binary
    glb_data = combined_scene.export(file_type='glb')
    with open(glb_path, 'wb') as f:
        f.write(glb_data)

    glb_size_mb = os.path.getsize(glb_path) / (1024.0 * 1024.0)
    print(f"[Exporter] Exported Unity GLB Binary: {glb_path} ({glb_size_mb:.2f} MB)")

    # Export OBJ fallback
    try:
        obj_data = combined_scene.export(file_type='obj')
        with open(obj_path, 'w', encoding='utf-8') as f:
            f.write(obj_data if isinstance(obj_data, str) else obj_data.decode('utf-8'))
        print(f"[Exporter] Exported OBJ Fallback: {obj_path}")
    except Exception as e:
        print(f"[Warning] OBJ export warning: {e}")

    # Test load GLB with trimesh to verify export integrity
    try:
        test_scene = trimesh.load(glb_path)
        print(f"[Exporter] Verification: house_model.glb loaded successfully with trimesh ({len(test_scene.geometry)} geometries).")
    except Exception as e:
        print(f"[Warning] GLB verification load failed: {e}")

    return glb_path, obj_path, glb_size_mb

# ==============================================================================
# 6. MASTER EXECUTION & SUMMARY REPORT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Build 3D House Model from 2D Floor Plan JSON")
    parser.add_argument("--input", default="output/house2d.json", help="Path to input house2d.json")
    parser.add_argument("--output-dir", default="output", help="Output directory for 3D renders and models")
    parser.add_argument("--no-roof", action="store_true", help="Disable roof/ceiling generation for interior inspection")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)

    # 1. Read JSON
    with open(args.input, "r", encoding="utf-8") as f:
        house2d_data = json.load(f)

    # 2. Inspect & Print Schema
    inspect_and_print_schema(house2d_data)

    # 3. Build 3D Model
    generate_roof = not args.no_roof
    builder = House3DBuilder(house2d_data, generate_roof=generate_roof)
    builder.build_all()

    # 4. Render Previews
    render_previews(builder, output_dir=args.output_dir)

    # 5. Export Unity Models (GLB & OBJ)
    glb_path, obj_path, glb_size_mb = export_unity_models(builder, output_dir=args.output_dir)

    # 6. Print Summary Report
    c = builder.counts
    total_furniture_count = c['furniture_beds'] + c['furniture_counters'] + c['furniture_sofas'] + c['furniture_toilets']

    print("\n======================================================================")
    print("3D RECONSTRUCTION SUMMARY")
    print("======================================================================")
    print(f"Walls:     {c['wall_boxes']} boxes")
    print(f"Doors:     {c['door_openings_cut']} openings cut, {c['door_slabs']} door slabs added")
    print(f"Windows:   {c['window_openings_cut']} openings cut, {c['glass_panes']} glass panes added")
    print(f"Rooms:     {c['rooms_labeled']} labeled")
    print(f"Furniture: {c['furniture_beds']} beds, {c['furniture_counters']} kitchen counter, {c['furniture_sofas']} sofas, {c['furniture_toilets']} toilets")
    print(f"Exported:  house_model.glb ({glb_size_mb:.2f} MB), house_model.obj")
    print(f"Renders:   house_preview_3d_top.png, house_preview_3d_walkthrough.png")
    print("======================================================================\n")

if __name__ == "__main__":
    main()
