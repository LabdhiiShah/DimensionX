"""Check that each DXF's semantic CAD entities agree with its JSON partner."""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
import ezdxf

ROOT = Path(__file__).resolve().parents[1]
APPID = "DIMENSIONX"
SEMANTIC_LAYERS = {
    "DX_FOOTPRINT", "DX_WALL_AXIS", "DX_DOOR", "DX_WINDOW",
    "DX_ROOM_ZONE", "DX_BALCONY",
}

def xdata(entity):
    try:
        tags = entity.get_xdata(APPID)
    except Exception:
        return {}
    result = {}
    for tag in tags:
        if tag.code == 1000 and "=" in str(tag.value):
            key, value = str(tag.value).split("=", 1)
            result[key] = value
    return result

def dist(p, q):
    return math.hypot(float(p[0]) - float(q[0]), float(p[1]) - float(q[1]))

def near(p, q, tol=1e-5):
    return dist(p, q) <= tol

def line_matches(e, wall):
    a = [e.dxf.start.x, e.dxf.start.y]
    b = [e.dxf.end.x, e.dxf.end.y]
    return (near(a, wall["start"]) and near(b, wall["end"])) or (near(a, wall["end"]) and near(b, wall["start"]))

def main():
    rows = []
    for dxf in sorted((ROOT / "plans").rglob("*.dxf")):
        relative = dxf.relative_to(ROOT / "plans")
        json_path = ROOT / "generated_json" / relative.parent / (dxf.stem + "_architecture.json")
        issues = []
        if not json_path.exists():
            rows.append({"plan_id": dxf.stem, "bhk": "", "dxf_units_feet": False, "semantic_counts_match": False, "metadata_matches": False, "PASS": False, "issues": "missing JSON partner"})
            continue
        data = json.loads(json_path.read_text(encoding="utf-8"))
        doc = ezdxf.readfile(dxf)
        msp = doc.modelspace()
        layer_entities = {name: [e for e in msp if e.dxf.layer == name] for name in SEMANTIC_LAYERS}
        units_ok = int(doc.header.get("$INSUNITS", 0)) == 2
        if not units_ok:
            issues.append("$INSUNITS is not feet (2)")
        missing = sorted(layer for layer in SEMANTIC_LAYERS if layer not in doc.layers)
        if missing:
            issues.append("missing layers: " + ",".join(missing))
        expected_counts = {
            "DX_FOOTPRINT": 1,
            "DX_WALL_AXIS": len(data["walls"]),
            "DX_DOOR": len(data["doors"]),
            "DX_WINDOW": len(data["windows"]),
            "DX_ROOM_ZONE": len(data["rooms"]),
            "DX_BALCONY": len(data.get("balconies", [])),
        }
        count_ok = True
        for layer, expected in expected_counts.items():
            actual = len(layer_entities.get(layer, []))
            if actual != expected:
                count_ok = False
                issues.append(f"{layer} count {actual} != {expected}")
        meta_ok = True
        wall_by_id = {w["id"]: w for w in data["walls"]}
        parsed_walls = {}
        for e in layer_entities.get("DX_WALL_AXIS", []):
            xd = xdata(e)
            wid = xd.get("id")
            if not wid or wid in parsed_walls or wid not in wall_by_id:
                meta_ok = False
                issues.append(f"invalid/duplicate/unmatched wall ID: {wid}")
                continue
            parsed_walls[wid] = e
            if not line_matches(e, wall_by_id[wid]):
                meta_ok = False
                issues.append(f"wall geometry mismatch: {wid}")
        for group, layer in (("doors", "DX_DOOR"), ("windows", "DX_WINDOW")):
            expected = {o["id"]: o for o in data[group]}
            seen = set()
            for e in layer_entities.get(layer, []):
                xd = xdata(e)
                oid = xd.get("id")
                if not oid or oid in seen or oid not in expected:
                    meta_ok = False
                    issues.append(f"invalid/duplicate/unmatched {group[:-1]} ID: {oid}")
                    continue
                seen.add(oid)
                obj = expected[oid]
                actual_center = [e.dxf.location.x, e.dxf.location.y]
                if not near(actual_center, obj["center"]):
                    meta_ok = False
                    issues.append(f"opening center mismatch: {oid}")
                if xd.get("wall_id") != obj.get("wall_id"):
                    meta_ok = False
                    issues.append(f"opening wall_id mismatch: {oid}")
                if xd.get("wall_id") not in wall_by_id:
                    meta_ok = False
                    issues.append(f"opening references missing wall: {oid}")
        # All DXF opening centers must be on their referenced wall axes.
        for group in ("doors", "windows"):
            for op in data[group]:
                wall = wall_by_id.get(op.get("wall_id"))
                if not wall:
                    meta_ok = False
                    continue
                a, b, p = wall["start"], wall["end"], op["center"]
                dx, dy = b[0]-a[0], b[1]-a[1]
                den = dx*dx + dy*dy
                t = 0 if den == 0 else max(0, min(1, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / den))
                projected = [a[0]+t*dx, a[1]+t*dy]
                if dist(p, projected) > 0.02:
                    meta_ok = False
                    issues.append(f"off-wall opening: {op['id']}")
        passed = units_ok and count_ok and meta_ok and not missing
        rows.append({
            "plan_id": data.get("plan_id", dxf.stem),
            "bhk": data.get("bhk", ""),
            "dxf_units_feet": units_ok,
            "semantic_counts_match": count_ok,
            "metadata_matches": meta_ok,
            "PASS": passed,
            "issues": "; ".join(issues),
        })
    out = ROOT / "generated_json" / "dxf_json_pair_validation.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(bool(r["PASS"]) for r in rows)
    print(f"DXF/JSON pair validation: {passed}/{len(rows)} PASS")
    if passed != len(rows):
        for r in rows:
            if not r["PASS"]:
                print(r["plan_id"], r["issues"])
        raise SystemExit(1)
    print(f"Report: {out}")

if __name__ == "__main__":
    main()
