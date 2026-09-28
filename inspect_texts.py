import ezdxf

def inspect_texts(filepath):
    print(f"=== Texts in {filepath} ===")
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    
    texts = []
    for e in msp.query('TEXT MTEXT'):
        if e.dxftype() == 'TEXT':
            txt = e.dxf.text
            pos = e.dxf.insert
        else:
            txt = e.text
            pos = e.dxf.insert
        layer = e.dxf.layer
        texts.append((txt.strip(), layer, (round(pos[0], 2), round(pos[1], 2), round(pos[2], 2))))
        
    print(f"Found {len(texts)} text entities:")
    for t in texts:
        print(f"  [{t[1]}] '{t[0]}' at {t[2]}")

if __name__ == "__main__":
    inspect_texts("d:/end game/dwg/sample1.dxf")
    print("\n" + "="*50 + "\n")
    inspect_texts("d:/end game/dwg/sample2.dxf")
