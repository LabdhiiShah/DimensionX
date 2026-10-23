import subprocess
import os
import trimesh
from pathlib import Path

BASE_DIR = Path("DimensionX_generated_json")
BHK_TYPES = ["1BHK", "2BHK", "3BHK"]

print("=" * 80)
print("STEP 1: RE-EXPORTING ALL PLANS WITH LATEST CODE")
print("=" * 80)

for bhk in BHK_TYPES:
    print(f"\nExporting {bhk}...")
    subprocess.run(["python", "tools/export_3d.py", f"{BASE_DIR}/{bhk}"])

print("\n" + "=" * 80)
print("STEP 2: VERIFYING GLB CONTENTS")
print("=" * 80)

passed = 0
failed = 0

print(f"{'File':<20} | {'Nodes':<6} | {'Walls':<6} | {'Floor':<6} | {'Roof':<6} | {'Doors':<6} | {'Windows':<7} | Status")
print("-" * 80)

for bhk in BHK_TYPES:
    obj_dir = BASE_DIR / bhk / "obj_output"
    if not obj_dir.exists():
        print(f"Folder missing: {obj_dir}")
        continue
        
    for i in range(1, 11):
        glb_name = f"{bhk}_{i:02d}.glb"
        glb_path = obj_dir / glb_name
        
        if not glb_path.exists():
            print(f"{glb_name:<20} | NOT FOUND")
            failed += 1
            continue
            
        try:
            scene = trimesh.load(glb_path)
            nodes = list(scene.geometry.keys())
            
            # Count categories based on our naming convention
            walls = [n for n in nodes if n.startswith("Wall_")]
            doors = [n for n in nodes if n.startswith("Door_")]
            windows = [n for n in nodes if n.startswith("Window_")]
            has_floor = "Floor" in nodes
            has_roof = "Roof" in nodes
            
            # A correct model should have walls, a floor, and a roof
            # (Some 1BHKs might have 0 doors/windows depending on the DXF)
            is_valid = (len(walls) > 0) and has_floor and has_roof
            
            status = "✅ PASS" if is_valid else "❌ FAIL"
            if is_valid:
                passed += 1
            else:
                failed += 1
                
            print(f"{glb_name:<20} | {len(nodes):<6} | {len(walls):<6} | {str(has_floor):<6} | {str(has_roof):<6} | {len(doors):<6} | {len(windows):<7} | {status}")
            
        except Exception as e:
            print(f"{glb_name:<20} | ERROR: {e}")
            failed += 1

print("-" * 80)
print(f"\nSUMMARY: {passed} Passed, {failed} Failed out of 30 files.")