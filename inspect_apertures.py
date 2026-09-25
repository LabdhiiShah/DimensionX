import ezdxf

doc = ezdxf.readfile("d:/end game/dwg/sample1.dxf")
msp = doc.modelspace()

arcs = list(msp.query('ARC'))
print(f"Total ARC entities: {len(arcs)}")
for a in arcs[:10]:
    center = (round(a.dxf.center[0], 2), round(a.dxf.center[1], 2))
    print(f"  Layer: {a.dxf.layer}, Center: {center}, Radius: {a.dxf.radius:.2f}, StartAngle: {a.dxf.start_angle:.1f}, EndAngle: {a.dxf.end_angle:.1f}")

inserts = list(msp.query('INSERT'))
print(f"Total INSERT entities: {len(inserts)}")
for i in inserts:
    print(f"  Name: {i.dxf.name}, Layer: {i.dxf.layer}, Pos: ({i.dxf.insert[0]:.2f}, {i.dxf.insert[1]:.2f})")
