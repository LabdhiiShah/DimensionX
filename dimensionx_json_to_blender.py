"""DimensionX: architecture.json -> Blender architectural shell -> FBX.

Run with Blender 5.2 (not regular Python):
  blender.exe --background --python dimensionx_json_to_blender.py -- path/to/architecture.json

JSON coordinates/dimensions are in feet. Geometry is converted to metres so
FBX imports into Unity at the expected real-world scale (1 Unity unit = 1 m).

Supported schema: DimensionX architecture_schema.json, schema version 1.0.
Generates footprint floor, wall solids with boolean door/window openings,
Unity-replaceable door/window socket meshes, balcony slabs, optional roof,
and a preview camera/light. No ezdxf/numpy dependency inside Blender.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


FT_TO_M = 0.3048
COLLECTION_NAME = "DimensionX_Generated"
BOOLEAN_PADDING_FT = 0.40
DEFAULT_WALL_HEIGHT_FT = 10.0
DEFAULT_WALL_THICKNESS_FT = 0.50
DEFAULT_DOOR_WIDTH_FT = 3.0
DEFAULT_DOOR_HEIGHT_FT = 7.0
DEFAULT_WINDOW_WIDTH_FT = 4.0
DEFAULT_WINDOW_HEIGHT_FT = 4.0
DEFAULT_WINDOW_SILL_FT = 3.0


def cli_args():
    """Only parse arguments after Blender's -- separator when present."""
    argv = sys.argv
    user_args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    parser = argparse.ArgumentParser(
        description="Generate a DimensionX Blender model from architecture JSON."
    )
    parser.add_argument("json_file", help="Path to the JSON produced by the DXF scanner")
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Output folder (default: a blender_output folder beside the JSON)",
    )
    parser.add_argument(
        "--no-roof", action="store_true",
        help="Skip roof slab for an unobstructed interior view",
    )
    return parser.parse_args(user_args)


def safe_name(value):
    value = str(value or "plan")
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "plan"


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def point2(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must be [x, y]")
    return [number(value[0], f"{label}[0]"), number(value[1], f"{label}[1]")]


def distance_point_segment(point, a, b):
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def validate_architecture(data):
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    bhk = int(number(data.get("bhk", 0), "bhk"))
    if bhk not in (1, 2, 3):
        raise ValueError("bhk must be 1, 2, or 3")
    if str(data.get("units", "feet")).lower() not in ("feet", "ft"):
        raise ValueError("This generator expects JSON units='feet'")

    footprint = data.get("footprint")
    if not isinstance(footprint, list) or len(footprint) < 3:
        raise ValueError("footprint must contain at least three [x, y] points")
    data["footprint"] = [point2(p, f"footprint[{i}]") for i, p in enumerate(footprint)]

    walls = data.get("walls")
    if not isinstance(walls, list) or not walls:
        raise ValueError("walls must be a non-empty list")
    wall_ids = set()
    cleaned_walls = []
    for i, raw in enumerate(walls):
        if not isinstance(raw, dict):
            raise ValueError(f"walls[{i}] must be an object")
        wall = dict(raw)
        wall["id"] = str(wall.get("id", f"W{i + 1:03d}"))
        if wall["id"] in wall_ids:
            raise ValueError(f"Duplicate wall id: {wall['id']}")
        wall_ids.add(wall["id"])
        wall["start"] = point2(wall.get("start"), f"walls[{i}].start")
        wall["end"] = point2(wall.get("end"), f"walls[{i}].end")
        wall["thickness"] = number(
            wall.get("thickness", data.get("wall_thickness", DEFAULT_WALL_THICKNESS_FT)),
            f"walls[{i}].thickness",
        )
        wall["height"] = number(
            wall.get("height", data.get("wall_height", DEFAULT_WALL_HEIGHT_FT)),
            f"walls[{i}].height",
        )
        if math.dist(wall["start"], wall["end"]) < 0.05:
            raise ValueError(f"Wall {wall['id']} is too short or has identical endpoints")
        if wall["thickness"] <= 0 or wall["height"] <= 0:
            raise ValueError(f"Wall {wall['id']} height/thickness must be positive")
        cleaned_walls.append(wall)
    data["walls"] = cleaned_walls

    for group, default_width, default_height in (
        ("doors", DEFAULT_DOOR_WIDTH_FT, DEFAULT_DOOR_HEIGHT_FT),
        ("windows", DEFAULT_WINDOW_WIDTH_FT, DEFAULT_WINDOW_HEIGHT_FT),
    ):
        items = data.get(group, []) or []
        if not isinstance(items, list):
            raise ValueError(f"{group} must be a list")
        cleaned = []
        for i, raw in enumerate(items):
            if not isinstance(raw, dict):
                raise ValueError(f"{group}[{i}] must be an object")
            item = dict(raw)
            item["id"] = str(item.get("id", f"{group[:-1].upper()}{i + 1:02d}"))
            item["center"] = point2(item.get("center"), f"{group}[{i}].center")
            item["width"] = number(item.get("width", default_width), f"{group}[{i}].width")
            item["height"] = number(item.get("height", default_height), f"{group}[{i}].height")
            item["sill_height"] = number(
                item.get("sill_height", 0.0 if group == "doors" else DEFAULT_WINDOW_SILL_FT),
                f"{group}[{i}].sill_height",
            )
            if item["width"] <= 0 or item["height"] <= 0 or item["sill_height"] < 0:
                raise ValueError(f"Invalid size/sill for {group} item {item['id']}")
            requested_wall = str(item.get("wall_id", "")).strip()
            if requested_wall and requested_wall not in wall_ids:
                raise ValueError(f"{group} {item['id']} references missing wall id {requested_wall}")
            item["wall_id"] = requested_wall
            cleaned.append(item)
        data[group] = cleaned

    # Ensure every opening lies along its assigned wall and fits within it.
    wall_by_id = {w["id"]: w for w in data["walls"]}
    for group in ("doors", "windows"):
        for opening in data[group]:
            if opening["wall_id"]:
                wall = wall_by_id[opening["wall_id"]]
            else:
                wall = min(
                    data["walls"],
                    key=lambda w: distance_point_segment(
                        opening["center"], w["start"], w["end"]
                    ),
                )
                opening["wall_id"] = wall["id"]
            wall_length = math.dist(wall["start"], wall["end"])
            if distance_point_segment(opening["center"], wall["start"], wall["end"]) > 0.05:
                raise ValueError(
                    f"{group} {opening['id']} is not on wall {wall['id']}"
                )
            dx = wall["end"][0] - wall["start"][0]
            dy = wall["end"][1] - wall["start"][1]
            length = math.hypot(dx, dy)
            t = ((opening["center"][0] - wall["start"][0]) * dx +
                 (opening["center"][1] - wall["start"][1]) * dy) / (length * length)
            half_t = opening["width"] / (2 * length)
            if opening["width"] > wall_length + 1e-4 or t - half_t < -1e-4 or t + half_t > 1 + 1e-4:
                raise ValueError(
                    f"{group} {opening['id']} does not fit within wall {wall['id']}"
                )
    return data


def ensure_collection():
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    return collection


def clean_scene():
    # This is a generated-output scene; do not touch or save over a source .blend.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def link_object(obj, collection):
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def material(name, color, metallic=0.0, roughness=0.75):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = (color[0], color[1], color[2], 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.node_tree else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_materials():
    return {
        "wall": material("DX_Wall_Material", (0.76, 0.74, 0.70), roughness=0.82),
        "floor": material("DX_Floor_Material", (0.48, 0.45, 0.40), roughness=0.92),
        "roof": material("DX_Roof_Material", (0.57, 0.55, 0.52), roughness=0.88),
        "door": material("DX_Door_Socket_Material", (0.48, 0.29, 0.16), roughness=0.56),
        "window": material("DX_Window_Socket_Material", (0.10, 0.32, 0.45), metallic=0.08, roughness=0.28),
        "balcony": material("DX_Balcony_Material", (0.42, 0.42, 0.40), roughness=0.90),
    }


def set_material(obj, mat):
    if obj and obj.type == "MESH":
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def add_cube(name, loc_m, dims_m, rotation_z, mat, collection):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc_m)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims_m
    obj.rotation_euler[2] = rotation_z
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    link_object(obj, collection)
    set_material(obj, mat)
    return obj


def add_prism(name, polygon_ft, z_m, height_m, mat, collection):
    polygon_m = [(p[0] * FT_TO_M, p[1] * FT_TO_M) for p in polygon_ft]
    n = len(polygon_m)
    vertices = [(x, y, z_m) for x, y in polygon_m]
    vertices += [(x, y, z_m + height_m) for x, y in polygon_m]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + ((i + 1) % n), n + i) for i in range(n)]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    # Recalculate normals for consistent top/bottom/side orientation.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    if bm.faces:
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    set_material(obj, mat)
    obj["dx_type"] = "BALCONY_SLAB" if name.startswith("DX_BALCONY") else name.replace("DX_", "")
    return obj


def wall_angle(wall):
    dx = wall["end"][0] - wall["start"][0]
    dy = wall["end"][1] - wall["start"][1]
    return math.atan2(dy, dx)


def create_wall(wall, floor_top_m, wall_mat, collection):
    x1, y1 = wall["start"]
    x2, y2 = wall["end"]
    height_m = wall["height"] * FT_TO_M
    thickness_m = wall["thickness"] * FT_TO_M
    length_m = math.hypot(x2 - x1, y2 - y1) * FT_TO_M
    cx_m = (x1 + x2) * 0.5 * FT_TO_M
    cy_m = (y1 + y2) * 0.5 * FT_TO_M
    obj = add_cube(
        f"DX_WALL_{safe_name(wall['id'])}",
        (cx_m, cy_m, floor_top_m + height_m * 0.5),
        (length_m, thickness_m, height_m),
        wall_angle(wall), wall_mat, collection,
    )
    obj["dx_type"] = "WALL"
    obj["dx_id"] = str(wall["id"])
    obj["wall_id"] = str(wall["id"])
    obj["thickness_ft"] = float(wall["thickness"])
    obj["height_ft"] = float(wall["height"])
    obj["exterior"] = bool(wall.get("exterior", False))
    return obj


def apply_boolean_opening(wall_obj, cutter):
    modifier = None
    try:
        bpy.ops.object.select_all(action="DESELECT")
        wall_obj.select_set(True)
        bpy.context.view_layer.objects.active = wall_obj
        modifier = wall_obj.modifiers.new(name="DX_Opening_Cut", type="BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        bpy.context.view_layer.update()
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        wall_obj.select_set(False)
        return True, ""
    except Exception as exc:
        if modifier is not None:
            try:
                wall_obj.modifiers.remove(modifier)
            except Exception:
                pass
        wall_obj.select_set(False)
        return False, str(exc)


def opening_wall_map(openings, walls):
    wall_map = {w["id"]: w for w in walls}
    return [(item, wall_map[item["wall_id"]]) for item in openings]


def create_opening(opening, kind, wall, wall_obj, floor_top_m, mats, collection):
    center_x_m = opening["center"][0] * FT_TO_M
    center_y_m = opening["center"][1] * FT_TO_M
    width_m = opening["width"] * FT_TO_M
    height_m = opening["height"] * FT_TO_M
    sill_m = opening["sill_height"] * FT_TO_M
    wall_thickness_m = wall["thickness"] * FT_TO_M
    angle = wall_angle(wall)
    padding_m = BOOLEAN_PADDING_FT * FT_TO_M

    # Remove a rectangular volume from the center-line wall solid.
    cutter = add_cube(
        f"DX_CUTTER_{kind.upper()}_{safe_name(opening['id'])}",
        (center_x_m, center_y_m, floor_top_m + sill_m + height_m * 0.5),
        (width_m, wall_thickness_m + padding_m, height_m),
        angle, None, collection,
    )
    ok, error = apply_boolean_opening(wall_obj, cutter)
    bpy.data.objects.remove(cutter, do_unlink=True)

    # A colored socket marks the aperture and is named for Unity replacement.
    socket_name = f"DX_SOCKET_{kind.upper()}_{safe_name(opening['id'])}_{safe_name(wall['id'])}"
    socket = add_cube(
        socket_name,
        (center_x_m, center_y_m, floor_top_m + sill_m + height_m * 0.5),
        (width_m, max(0.035, 0.06 * FT_TO_M), height_m),
        angle, mats["door" if kind == "door" else "window"], collection,
    )
    socket["dx_type"] = kind.upper()
    socket["dx_id"] = str(opening["id"])
    socket["wall_id"] = str(wall["id"])
    socket["replace_in_unity"] = True
    socket["width_ft"] = float(opening["width"])
    socket["height_ft"] = float(opening["height"])
    socket["sill_height_ft"] = float(opening["sill_height"])
    socket["role"] = str(opening.get("role", kind))
    socket["orientation"] = str(opening.get("orientation", ""))
    socket["opening_cut_success"] = bool(ok)
    if not ok:
        print(f"WARNING: Boolean cut failed for {kind} {opening['id']} on {wall['id']}: {error}")
    return ok


def build_camera_light(footprint, wall_height_m, collection):
    pts = [(p[0] * FT_TO_M, p[1] * FT_TO_M) for p in footprint]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    cx, cy = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5
    span = max(max_x - min_x, max_y - min_y, 5.0)

    bpy.ops.object.camera_add(location=(cx + span * 0.9, cy - span * 0.9, wall_height_m + span * 0.5))
    camera = bpy.context.object
    camera.name = "DX_Camera"
    camera.data.lens = 48
    direction = Vector((cx, cy, wall_height_m * 0.35)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    link_object(camera, collection)
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(cx, cy, wall_height_m + span * 0.6))
    light = bpy.context.object
    light.name = "DX_KeyLight"
    light.data.energy = 1800
    light.data.shape = "DISK"
    light.data.size = max(span * 0.7, 3.0)
    direction = Vector((cx, cy, 0.0)) - light.location
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    link_object(light, collection)


def export_fbx(fbx_path, collection):
    bpy.ops.object.select_all(action="DESELECT")
    export_objs = [o for o in collection.objects if o.type == "MESH"]
    for obj in export_objs:
        obj.select_set(True)
    if export_objs:
        bpy.context.view_layer.objects.active = export_objs[0]
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        apply_unit_scale=True,
        bake_space_transform=False,
        axis_forward="-Z",
        axis_up="Y",
        use_custom_props=True,
        add_leaf_bones=False,
    )
    bpy.ops.object.select_all(action="DESELECT")


def main():
    args = cli_args()
    json_path = Path(args.json_file).expanduser().resolve()
    if not json_path.is_file():
        raise FileNotFoundError(f"Architecture JSON not found: {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data = validate_architecture(data)

    plan_id = safe_name(data.get("plan_id") or json_path.stem.replace("_architecture", ""))
    out_dir = args.output_dir.expanduser().resolve() if args.output_dir else json_path.parent / "blender_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    blend_path = out_dir / f"{plan_id}_generated.blend"
    fbx_path = out_dir / f"{plan_id}_generated.fbx"

    print("\n====================================================")
    print("DimensionX - architecture.json -> Blender -> FBX")
    print("====================================================")
    print(f"Plan: {plan_id} | BHK: {data['bhk']} | source DXF: {data.get('source_dxf', 'unknown')}")
    print(f"Walls: {len(data['walls'])} | doors: {len(data['doors'])} | windows: {len(data['windows'])} | balconies: {len(data.get('balconies', []))}")
    print("Scale: JSON feet -> Blender metres -> Unity metres")

    clean_scene()
    collection = ensure_collection()
    mats = make_materials()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene["dx_plan_id"] = plan_id
    scene["dx_bhk"] = int(data["bhk"])
    scene["dx_source_dxf"] = str(data.get("source_dxf", ""))
    scene["dx_source_units"] = "feet"

    floor_thickness_m = float(data.get("floor_thickness", 0.20)) * FT_TO_M
    roof_thickness_m = float(data.get("roof_thickness", 0.25)) * FT_TO_M
    default_wall_height = float(data.get("wall_height", DEFAULT_WALL_HEIGHT_FT))
    max_wall_height = max(float(w["height"]) for w in data["walls"])
    wall_height_m = max_wall_height * FT_TO_M
    floor_top_m = floor_thickness_m

    print("Building floor footprint...")
    floor = add_prism("DX_FLOOR", data["footprint"], 0.0, floor_thickness_m, mats["floor"], collection)
    floor["dx_type"] = "FLOOR"

    print("Building walls and cutting openings...")
    wall_objects = {}
    for wall in data["walls"]:
        wall_obj = create_wall(wall, floor_top_m, mats["wall"], collection)
        wall_objects[wall["id"]] = wall_obj

    opening_count = 0
    cut_failures = []
    for kind, group_name in (("door", "doors"), ("window", "windows")):
        for opening, wall in opening_wall_map(data[group_name], data["walls"]):
            ok = create_opening(
                opening, kind, wall, wall_objects[wall["id"]],
                floor_top_m, mats, collection,
            )
            opening_count += 1
            if not ok:
                cut_failures.append(f"{kind}:{opening['id']}@{wall['id']}")

    print("Building balcony slabs...")
    for balcony in data.get("balconies", []) or []:
        poly = balcony.get("polygon", [])
        if not isinstance(poly, list) or len(poly) < 3:
            print(f"WARNING: skipping invalid balcony polygon {balcony.get('id', '?')}")
            continue
        obj = add_prism(
            f"DX_BALCONY_{safe_name(balcony.get('id', 'BAL'))}",
            poly, 0.0, floor_thickness_m, mats["balcony"], collection,
        )
        obj["dx_id"] = str(balcony.get("id", ""))
        obj["role"] = str(balcony.get("role", "balcony"))
        obj["attachment_wall_id"] = str(balcony.get("attachment_wall_id", ""))

    if not args.no_roof:
        print("Building roof slab...")
        roof = add_prism(
            "DX_ROOF", data["footprint"], floor_top_m + wall_height_m,
            roof_thickness_m, mats["roof"], collection,
        )
        roof["dx_type"] = "ROOF"
        roof["toggle_in_unity"] = True

    print("Adding Blender preview camera and light...")
    build_camera_light(data["footprint"], wall_height_m + floor_top_m, collection)

    # Save the editable Blender scene first, then export only generated meshes.
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    export_fbx(fbx_path, collection)

    print("\n====================================================")
    print("GENERATION COMPLETE")
    print("====================================================")
    print(f"BLEND: {blend_path}")
    print(f"FBX:   {fbx_path}")
    print(f"Opening sockets created: {opening_count}")
    print(f"Boolean opening failures: {len(cut_failures)}")
    if cut_failures:
        print("Review these openings before using the model:")
        for item in cut_failures:
            print(f"  - {item}")
    print("Unity replacement objects use names like DX_SOCKET_DOOR_D01_W004 and custom properties.")
    print("NOTE: Inspect the FBX in Unity; this automated shell generator is a development MVP, not a construction validator.")


if __name__ == "__main__":
    main()
