import argparse, json, math
from pathlib import Path
import ezdxf
APPID="DIMENSIONX"
SCHEMA_VERSION="1.0"
def xd(entity):
    out={}
    try: tags=entity.get_xdata(APPID)
    except Exception: return out
    for tag in tags:
        if tag.code==1000 and "=" in str(tag.value):
            k,v=str(tag.value).split("=",1);out[k]=v
    return out
def f(v,d=0.0):
    try:return float(v)
    except Exception:return d
def poly_area(p):
    return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2)
def distance(p,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
    if den<1e-12:return math.hypot(p[0]-a[0],p[1]-a[1])
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-(a[0]+t*dx),p[1]-(a[1]+t*dy))
def validate(data):
    wm={w["id"]:w for w in data["walls"]}
    if not data["footprint"] or len(data["footprint"])<3: raise ValueError("Missing footprint")
    for group in ("doors","windows"):
        for o in data[group]:
            if o["wall_id"] not in wm: raise ValueError(f"{group} {o['id']} has missing wall ref")
            w=wm[o["wall_id"]]
            if distance(o["center"],w["start"],w["end"])>.02: raise ValueError(f"{group} {o['id']} is off wall")
            if o["width"]>math.hypot(w["end"][0]-w["start"][0],w["end"][1]-w["start"][1])+.001: raise ValueError(f"{group} {o['id']} wider than wall")
    if int(data["bhk"]) not in (1,2,3): raise ValueError("Invalid BHK metadata")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("dxf");ap.add_argument("--output");args=ap.parse_args()
    src=Path(args.dxf);doc=ezdxf.readfile(src);msp=doc.modelspace();foot=None;meta={};walls=[];doors=[];windows=[];rooms=[];balconies=[]
    for e in msp:
        layer=e.dxf.layer; x=xd(e)
        if layer=="DX_FOOTPRINT" and e.dxftype()=="LWPOLYLINE":
            foot=[[float(p[0]),float(p[1])] for p in e.get_points()];meta=x
        elif layer=="DX_WALL_AXIS" and e.dxftype()=="LINE":
            walls.append({"id":x.get("id",f"W{len(walls)+1:03d}"),"start":[e.dxf.start.x,e.dxf.start.y],"end":[e.dxf.end.x,e.dxf.end.y],"thickness":f(x.get("thickness_ft"),.5),"height":f(x.get("height_ft"),10),"exterior":x.get("exterior","0")=="1","side":x.get("side","interior"),"room_ids":[v for v in x.get("room_ids","").split(",") if v]})
        elif layer in ("DX_DOOR","DX_WINDOW") and e.dxftype()=="POINT":
            isdoor=layer=="DX_DOOR"; dst=doors if isdoor else windows
            dst.append({"id":x.get("id",f"O{len(dst)+1}"),"wall_id":x.get("wall_id",""),"center":[float(e.dxf.location.x),float(e.dxf.location.y)],"width":f(x.get("width_ft"),3 if isdoor else 4),"height":f(x.get("height_ft"),7 if isdoor else 4),"sill_height":f(x.get("sill_height_ft"),0 if isdoor else 3),"role":x.get("role","internal" if isdoor else "window"),"orientation":x.get("orientation","HORIZONTAL"),**({"swing_direction":x.get("swing_direction","interior")} if isdoor else {})})
        elif layer=="DX_ROOM_ZONE" and e.dxftype()=="LWPOLYLINE":
            p=[[float(v[0]),float(v[1])] for v in e.get_points()];rooms.append({"id":x.get("room_id",f"room_{len(rooms)+1}"),"name":x.get("name","Room"),"role":x.get("role","room"),"polygon":p,"area_sqft":f(x.get("area_sqft"),poly_area(p))})
        elif layer=="DX_BALCONY" and e.dxftype()=="LWPOLYLINE":
            p=[[float(v[0]),float(v[1])] for v in e.get_points()];balconies.append({"id":x.get("balcony_id",f"balcony_{len(balconies)+1}"),"name":x.get("name","BALCONY"),"role":x.get("role","balcony"),"polygon":p,"area_sqft":poly_area(p),"depth":f(x.get("depth_ft"),4),"width":f(x.get("width_ft"),6),"attachment_wall_id":x.get("attachment_wall_id",""),"attached_side":x.get("attached_side","")})
    if foot is None:raise ValueError("DX_FOOTPRINT layer not found; this converter expects DimensionX semantic DXF layers")
    data={"schema_version":SCHEMA_VERSION,"generator":"DimensionX Plan Factory","plan_id":meta.get("plan_id",src.stem),"bhk":int(f(meta.get("bhk"),0)),"units":"feet","source_dxf":src.name,"wall_height":f(meta.get("wall_height"),10),"wall_thickness":f(meta.get("wall_thickness"),.5),"floor_thickness":.2,"roof_thickness":.25,"footprint":foot,"walls":walls,"doors":doors,"windows":windows,"rooms":rooms,"balconies":balconies}
    validate(data);out=Path(args.output) if args.output else src.with_name(src.stem+"_architecture.json");out.write_text(json.dumps(data,indent=2),encoding="utf-8");print(f"JSON: {out}");print(f"BHK={data['bhk']} | walls={len(walls)} | doors={len(doors)} | windows={len(windows)} | rooms={len(rooms)} | balconies={len(balconies)}")
if __name__=="__main__":main()
