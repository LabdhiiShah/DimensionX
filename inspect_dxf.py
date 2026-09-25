import ezdxf
import os
import sys

def inspect_file(filepath):
    print(f"=== Inspecting {filepath} ===")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    
    header = doc.header
    print("Header variables:")
    for var in ["$INSUNITS", "$INSBASE", "$EXTMIN", "$EXTMAX", "$MEASUREMENT", "$LUNITS"]:
        if var in header:
            print(f"  {var}: {header[var]}")
        else:
            print(f"  {var}: NOT SPECIFIED")
            
    layers = list(doc.layers)
    print(f"Total layers: {len(layers)}")
    for l in layers:
        print(f"  Layer '{l.dxf.name}': color={l.dxf.color}, lock={l.is_locked()}")
        
    counts = {}
    z_non_zero = 0
    total_entities = 0
    paper_space_entities = 0
    
    for entity in msp:
        total_entities += 1
        t = entity.dxftype()
        counts[t] = counts.get(t, 0) + 1
        # Check z coordinates
        if hasattr(entity.dxf, 'insert') and len(entity.dxf.insert) == 3 and entity.dxf.insert[2] != 0:
            z_non_zero += 1
        elif hasattr(entity.dxf, 'start') and len(entity.dxf.start) == 3 and entity.dxf.start[2] != 0:
            z_non_zero += 1
            
    print(f"Modelspace total entities: {total_entities}")
    print("Entity types count:")
    for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k}: {v}")
    print(f"Non-zero Z entities: {z_non_zero}")
    
    # Check block definitions
    print(f"Block definitions count: {len(doc.blocks)}")
    non_layout_blocks = [b for b in doc.blocks if not b.name.startswith('*')]
    print(f"User block definitions: {len(non_layout_blocks)}")
    for b in non_layout_blocks[:15]:
        print(f"  Block '{b.name}': {len(b)} entities")

if __name__ == "__main__":
    inspect_file("d:/end game/dwg/sample1.dxf")
    print("\n" + "="*50 + "\n")
    inspect_file("d:/end game/dwg/sample2.dxf")
