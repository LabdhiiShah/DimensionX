"""DimensionX: architecture.json -> GLB (per-wall nodes for Unity painting).

Usage:
    python tools/export_3d.py <json_file_or_folder> [<out_dir>]

Each wall becomes a separate node (Wall_W001, Wall_W002, ...) with its own
material (DX_Wall_W001, DX_Wall_W002, ...). Doors, windows, floor, roof,
and balconies are exported as merged groups.
All geometry in metres (JSON is feet, converted with FT_TO_M=0.3048).
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

FT_TO_M = 0.3048
FLOOR_THICK_M = 0.06
SOCKET_THICK_M = 0.04

# Base material palette — one colour per room-ish grouping. Users override
# at runtime through the design tool, so the default just needs to look OK.
WALL_PALETTE = [
    (0.76, 0.74, 0.70),  # warm grey
    (0.85, 0.78, 0.72),  # beige
    (0.72, 0.78, 0.85),  # soft blue
    (0.85, 0.72, 0.72),  # blush
    (0.78, 0.85, 0.78),  # mint
    (0.85, 0.83, 0.72),  # cream
]

MATERIALS = {
    "DX_Floor":   (0.48, 0.45, 0.40),
    "DX_Door":    (0.48, 0.29, 0.16),
    "DX_Window":  (0.10, 0.32, 0.45),
    "DX_Balcony": (0.42, 0.42, 0.40),
    "DX_Roof":    (0.57, 0.55, 0.52),
}


class ObjBuilder:
    """
    Collects geometry per named element. Walls become individual elements
    (Wall_W001, Wall_W002). Everything else is grouped (Floor, Door_D001, ...).
    Saves GLB with per-node meshes + OBJ as a merged fallback.
    """
    def __init__(self):
        self.elements: dict[str, dict] = {}
        self.current_name: str | None = None
        self.current_mat: str = "DX_Wall"

    def set_element(self, name: str, material: str):
        if name not in self.elements:
            self.elements[name] = {"verts": [], "faces": [], "material": material}
        self.current_name = name
        self.current_mat = material

    def v(self, x, y, z):
        self.elements[self.current_name]["verts"].append((x, z, -y))
        return len(self.elements[self.current_name]["verts"])  # 1-based within element

    def quad(self, i0, i1, i2, i3):
        self.elements[self.current_name]["faces"].append([i0 - 1, i1 - 1, i2 - 1, i3 - 1])

    def tri(self, i0, i1, i2):
        self.elements[self.current_name]["faces"].append([i0 - 1, i1 - 1, i2 - 1])

    # ----------------------------------------------------------------
    def save_glb(self, glb_path: Path):
        import numpy as np
        import trimesh

        scene = trimesh.Scene()
        for name, data in self.elements.items():
            if not data["verts"] or not data["faces"]:
                continue

            # Triangulate mixed tri/quad face lists so numpy can make a
            # uniform array. Polygon slabs mix both; wall boxes use quads only.
            triangles = []
            for face in data["faces"]:
                if len(face) == 3:
                    triangles.append(face)
                elif len(face) == 4:
                    # Split quad ABCD into triangles ABC + ACD
                    triangles.append([face[0], face[1], face[2]])
                    triangles.append([face[0], face[2], face[3]])
            if not triangles:
                continue

            try:
                mesh = trimesh.Trimesh(
                    vertices=np.array(data["verts"], dtype=float),
                    faces=np.array(triangles, dtype=int),
                    process=False,
                )
            except Exception as exc:
                print(f"  WARN: skipped {name}: {exc}")
                continue

            r, g, b = MATERIALS.get(data["material"], (0.8, 0.8, 0.8))
            mesh.visual = trimesh.visual.TextureVisuals(
                material=trimesh.visual.material.PBRMaterial(
                    name=data["material"],
                    baseColorFactor=[r, g, b, 1.0],
                    metallicFactor=0.0,
                    roughnessFactor=0.85,
                )
            )
            scene.add_geometry(mesh, node_name=name, geom_name=name)

        glb_path.parent.mkdir(parents=True, exist_ok=True)
        glb_path.write_bytes(scene.export(file_type="glb"))
        print(f"  Wrote GLB: {glb_path.name} ({len(scene.geometry)} nodes)")

    def save_obj(self, obj_path: Path):
        """Merged OBJ fallback for tools that can't read GLB."""
        with obj_path.open("w") as f:
            f.write(f"mtllib {obj_path.with_suffix('.mtl').name}\n")
            offset = 0
            last_mat = None
            for name, data in self.elements.items():
                for vx, vy, vz in data["verts"]:
                    f.write(f"v {vx:.5f} {vy:.5f} {vz:.5f}\n")
                for face in data["faces"]:
                    if data["material"] != last_mat:
                        f.write(f"usemtl {data['material']}\n")
                        last_mat = data["material"]
                    f.write("f " + " ".join(str(i + 1 + offset) for i in face) + "\n")
                offset += len(data["verts"])

        with obj_path.with_suffix(".mtl").open("w") as f:
            written = set()
            for data in self.elements.values():
                mat = data["material"]
                if mat in written:
                    continue
                r, g, b = MATERIALS.get(mat, (0.8, 0.8, 0.8))
                f.write(f"newmtl {mat}\nKd {r} {g} {b}\nKa 0 0 0\nKs 0 0 0\nNs 10\n\n")
                written.add(mat)


def add_box(b, cx, cy, cz, len_m, thick_m, height_m, angle_rad):
    ca, sa = math.cos(angle_rad), math.sin(angle_rad)
    hx, hy, hz = len_m / 2, thick_m / 2, height_m / 2
    local = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    bot, top = [], []
    for lx, ly in local:
        px = cx + lx * ca - ly * sa
        py = cy + lx * sa + ly * ca
        bot.append(b.v(px, py, cz - hz))
        top.append(b.v(px, py, cz + hz))
    b.quad(bot[3], bot[2], bot[1], bot[0])
    b.quad(top[0], top[1], top[2], top[3])
    b.quad(bot[0], bot[1], top[1], top[0])
    b.quad(bot[1], bot[2], top[2], top[1])
    b.quad(bot[2], bot[3], top[3], top[2])
    b.quad(bot[3], bot[0], top[0], top[3])


def add_polygon_slab(b, poly_m, z_top, z_bot):
    n = len(poly_m)
    cx = sum(p[0] for p in poly_m) / n
    cy = sum(p[1] for p in poly_m) / n
    c_top = b.v(cx, cy, z_top)
    c_bot = b.v(cx, cy, z_bot)
    top = [b.v(p[0], p[1], z_top) for p in poly_m]
    bot = [b.v(p[0], p[1], z_bot) for p in poly_m]
    for i in range(n):
        j = (i + 1) % n
        b.tri(c_top, top[i], top[j])
        b.tri(c_bot, bot[j], bot[i])
        b.quad(top[j], top[i], bot[i], bot[j])


def build_wall(b, wall, doors_by_wall, windows_by_wall, palette_index=0):
    """One wall -> one element with its own material."""
    x1f, y1f = wall["start"]
    x2f, y2f = wall["end"]
    Lf = math.hypot(x2f - x1f, y2f - y1f)
    if Lf < 0.05:
        return

    wall_id = wall["id"]
    mat_name = f"DX_Wall_{wall_id}"
    if mat_name not in MATERIALS:
        MATERIALS[mat_name] = WALL_PALETTE[palette_index % len(WALL_PALETTE)]

    # Wall is a single element; multiple boxes within it stay grouped.
    b.set_element(f"Wall_{wall_id}", mat_name)

    dxf, dyf = (x2f - x1f) / Lf, (y2f - y1f) / Lf
    angle = math.atan2(y2f - y1f, x2f - x1f)
    th = wall["thickness"] * FT_TO_M
    ht = wall["height"] * FT_TO_M
    x1m, y1m = x1f * FT_TO_M, y1f * FT_TO_M
    Lm = Lf * FT_TO_M

    openings = []
    for o in doors_by_wall.get(wall_id, []) + windows_by_wall.get(wall_id, []):
        cxf, cyf = o["center"]
        tf = (cxf - x1f) * dxf + (cyf - y1f) * dyf
        t0f = max(0.0, tf - o["width"] / 2)
        t1f = min(Lf, tf + o["width"] / 2)
        sill = o.get("sill_height", 0.0) * FT_TO_M
        oh = o["height"] * FT_TO_M
        openings.append((t0f * FT_TO_M, t1f * FT_TO_M, sill, oh))
    openings.sort()

    def emit(t0m, t1m, y0, y1):
        if t1m - t0m < 1e-4 or y1 - y0 < 1e-4:
            return
        mid_t = (t0m + t1m) / 2
        cx = x1m + dxf * mid_t
        cy = y1m + dyf * mid_t
        cz = y0 + (y1 - y0) / 2
        add_box(b, cx, cy, cz, t1m - t0m, th, y1 - y0, angle)

    cursor = 0.0
    for t0m, t1m, sill, oh in openings:
        if t0m > cursor + 1e-4:
            emit(cursor, t0m, 0, ht)
        if sill > 1e-4:
            emit(t0m, t1m, 0, sill)
        lb = sill + oh
        if lb < ht - 1e-4:
            emit(t0m, t1m, lb, ht)
        cursor = max(cursor, t1m)
    if cursor < Lm - 1e-4:
        emit(cursor, Lm, 0, ht)


def build_socket(b, opening, walls, mat, prefix):
    wall = next((w for w in walls if w["id"] == opening["wall_id"]), None)
    if wall is None:
        return
    angle = math.atan2(
        wall["end"][1] - wall["start"][1],
        wall["end"][0] - wall["start"][0],
    )
    cx, cy = opening["center"][0] * FT_TO_M, opening["center"][1] * FT_TO_M
    w_m = opening["width"] * FT_TO_M
    h_m = opening["height"] * FT_TO_M
    sill = opening.get("sill_height", 0.0) * FT_TO_M
    b.set_element(f"{prefix}_{opening['id']}", mat)
    add_box(b, cx, cy, sill + h_m / 2, w_m, SOCKET_THICK_M, h_m, angle)


def export_plan(json_path: Path, out_dir: Path):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    plan_id = data.get("plan_id", json_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    b = ObjBuilder()

    # --- FLOOR ---
    b.set_element("Floor", "DX_Floor")
    fp_m = [(p[0] * FT_TO_M, p[1] * FT_TO_M) for p in data["footprint"]]
    add_polygon_slab(b, fp_m, 0.0, -FLOOR_THICK_M)

    # --- ROOF ---
    if data.get("walls"):
        max_h = max(w["height"] * FT_TO_M for w in data["walls"])
    else:
        max_h = 3.0
    b.set_element("Roof", "DX_Roof")
    add_polygon_slab(b, fp_m, max_h + 0.0762, max_h)  # 3 inches thick

    # --- WALLS (one element each) ---
    doors_by_wall, windows_by_wall = {}, {}
    for d in data.get("doors", []):
        doors_by_wall.setdefault(d["wall_id"], []).append(d)
    for win in data.get("windows", []):
        windows_by_wall.setdefault(win["wall_id"], []).append(win)

    # Try to colour walls per room if room_id is present, else cycle palette.
    room_to_index = {}
    for i, room in enumerate(data.get("rooms", [])):
        room_to_index[room.get("id", f"R{i}")] = i

    for wall in data.get("walls", []):
        idx = room_to_index.get(wall.get("room_id", ""), len(room_to_index))
        build_wall(b, wall, doors_by_wall, windows_by_wall, palette_index=idx)

    # --- DOORS ---
    for d in data.get("doors", []):
        build_socket(b, d, data["walls"], "DX_Door", "Door")

    # --- WINDOWS ---
    for win in data.get("windows", []):
        build_socket(b, win, data["walls"], "DX_Window", "Window")

    # --- BALCONIES ---
    for bal in data.get("balconies", []) or []:
        poly_m = [(p[0] * FT_TO_M, p[1] * FT_TO_M) for p in bal["polygon"]]
        if len(poly_m) >= 3:
            b.set_element(f"Balcony_{bal.get('id', 'BAL')}", "DX_Balcony")
            add_polygon_slab(b, poly_m, 0.0, -FLOOR_THICK_M)

    # --- SAVE ---
    glb_path = out_dir / f"{plan_id}.glb"
    b.save_glb(glb_path)
    obj_path = out_dir / f"{plan_id}.obj"
    b.save_obj(obj_path)
    print(f"  {json_path.name} -> {plan_id}.glb + .obj + .mtl "
          f"({len(b.elements)} elements, {sum(len(e['verts']) for e in b.elements.values())} verts)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1]).resolve()
    if src.is_file():
        out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else src.parent / "obj_output"
        export_plan(src, out_dir)
    elif src.is_dir():
        out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else src / "obj_output"
        jsons = sorted(src.rglob("*_architecture.json"))
        if not jsons:
            print(f"No *_architecture.json under {src}")
            sys.exit(1)
        for j in jsons:
            rel = j.parent.relative_to(src)
            export_plan(j, out_dir / rel)
    else:
        print(f"Not found: {src}")
        sys.exit(1)


if __name__ == "__main__":
    main()