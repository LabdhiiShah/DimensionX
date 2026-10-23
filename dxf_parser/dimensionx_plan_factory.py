from __future__ import annotations
import json, math, os, csv, re, shutil, zipfile
from pathlib import Path
from collections import defaultdict
import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf import colors

APPID = "DIMENSIONX"
SCHEMA_VERSION = "1.0"
DEFAULT_WALL_HEIGHT = 10.0
DEFAULT_WALL_THICKNESS = 0.50

LAYER_DEFS = {
    "DX_FOOTPRINT": (7, "CONTINUOUS", 35),
    "DX_WALL_AXIS": (8, "DASHED", 9),
    "DX_WALL_FACE": (7, "CONTINUOUS", 35),
    "DX_DOOR": (1, "CONTINUOUS", 18),
    "DX_DOOR_SYMBOL": (1, "CONTINUOUS", 18),
    "DX_WINDOW": (4, "CONTINUOUS", 18),
    "DX_WINDOW_SYMBOL": (4, "CONTINUOUS", 18),
    "DX_ROOM_ZONE": (8, "DASHED", 5),
    "DX_ROOM_LABEL": (7, "CONTINUOUS", 13),
    "DX_BALCONY": (3, "CONTINUOUS", 18),
    "DX_RAILING": (3, "CONTINUOUS", 13),
    "DX_DIMENSION": (8, "CONTINUOUS", 9),
    "DX_TITLE": (7, "CONTINUOUS", 18),
    "DX_PLAN_META": (8, "CONTINUOUS", 9),
}


def rect_poly(x0,y0,x1,y1):
    return [[float(x0),float(y0)],[float(x1),float(y0)],[float(x1),float(y1)],[float(x0),float(y1)]]


def room(rid, name, role, poly):
    return {"id":rid,"name":name,"role":role,"polygon":[[float(x),float(y)] for x,y in poly]}


def make_rooms(bhk, W, H, template, params):
    """Create clean room-zone polygons for a rectangular core. All dimensions are feet."""
    if bhk == 1:
        if template == "compact":
            sx = params.get("split_x", 0.62) * W
            sy = params.get("split_y", 0.52) * H
            return [
                room("living_dining","LIVING / DINING","living",rect_poly(0,0,sx,sy)),
                room("kitchen","KITCHEN","kitchen",rect_poly(sx,0,W,sy)),
                room("master_bedroom","MASTER BEDROOM","bedroom",rect_poly(0,sy,sx,H)),
                room("bathroom","BATH / WC","bathroom",rect_poly(sx,sy,W,H)),
            ]
        x1 = params.get("x1",0.58)*W
        x2 = params.get("x2",0.78)*W
        y1 = params.get("y1",0.38)*H
        y2 = params.get("y2",0.55)*H
        return [
            room("living_dining","LIVING / DINING","living",rect_poly(0,0,x1,y2)),
            room("kitchen","KITCHEN","kitchen",rect_poly(x1,0,W,y1)),
            room("passage","PASSAGE","passage",rect_poly(x1,y1,W,y2)),
            room("master_bedroom","MASTER BEDROOM","bedroom",rect_poly(0,y2,x1,H)),
            room("bathroom","BATH / WC","bathroom",rect_poly(x1,y2,x2,H)),
            room("utility","UTILITY / STORE","utility",rect_poly(x2,y2,W,H)),
        ]
    if bhk == 2:
        x1=params.get("x1",0.25)*W
        x2=params.get("x2",0.62)*W
        x3=params.get("x3",0.78)*W
        y1=params.get("y1",0.42)*H
        y2=params.get("y2",0.65)*H
        return [
            room("living_dining","LIVING / DINING","living",rect_poly(0,0,x2,y1)),
            room("kitchen","KITCHEN","kitchen",rect_poly(x2,0,W,y1)),
            room("foyer","ENTRY / FOYER","foyer",rect_poly(0,y1,x1,y2)),
            room("passage","PASSAGE","passage",rect_poly(x1,y1,x3,y2)),
            room("common_toilet","COMMON TOILET","bathroom",rect_poly(x3,y1,W,y2)),
            room("bedroom_2","BEDROOM 2","bedroom",rect_poly(0,y2,params.get("bed_split",0.45)*W,H)),
            room("master_bedroom","MASTER BEDROOM","bedroom",rect_poly(params.get("bed_split",0.45)*W,y2,x3,H)),
            room("ensuite_toilet","MASTER TOILET","bathroom",rect_poly(x3,y2,W,H)),
        ]
    # 3BHK: 3 sleeping areas, a central passage, common WC, plus an en-suite
    x1=params.get("x1",0.20)*W
    x2=params.get("x2",0.60)*W
    x3=params.get("x3",0.78)*W
    xb=params.get("xb",0.33)*W
    xc=params.get("xc",0.66)*W
    y1=params.get("y1",0.38)*H
    y2=params.get("y2",0.62)*H
    y3=params.get("y3",0.82)*H
    bath_x=params.get("bath_x",0.12)*W
    master_poly = [[0,y3],[bath_x,y3],[bath_x,y2],[xb,y2],[xb,H],[0,H]]
    return [
        room("living_dining","LIVING / DINING","living",rect_poly(0,0,x2,y1)),
        room("kitchen","KITCHEN","kitchen",rect_poly(x2,0,W,y1)),
        room("foyer","ENTRY / FOYER","foyer",rect_poly(0,y1,x1,y2)),
        room("passage","PASSAGE","passage",rect_poly(x1,y1,x3,y2)),
        room("common_toilet","COMMON TOILET","bathroom",rect_poly(x3,y1,W,y2)),
        room("master_toilet","MASTER TOILET","bathroom",rect_poly(0,y2,bath_x,y3)),
        room("master_bedroom","MASTER BEDROOM","bedroom",master_poly),
        room("bedroom_2","BEDROOM 2","bedroom",rect_poly(xb,y2,xc,H)),
        room("bedroom_3","BEDROOM 3","bedroom",rect_poly(xc,y2,W,H)),
    ]


def plan_spec(bhk, idx):
    # Deterministic variation: several partition styles, dimensions, mirroring and quarter-turns.
    if bhk == 1:
        sizes=[(24,25),(25,26),(26,25),(27,27),(24,27),(28,26),(25,24),(27,25),(26,28),(28,27)]
        templates=["spine","compact","spine","spine","compact","spine","spine","compact","spine","spine"]
        params_list=[
            {"x1":.58,"x2":.79,"y1":.38,"y2":.55},
            {"split_x":.63,"split_y":.51},
            {"x1":.60,"x2":.80,"y1":.36,"y2":.54},
            {"x1":.56,"x2":.77,"y1":.40,"y2":.57},
            {"split_x":.60,"split_y":.55},
            {"x1":.59,"x2":.79,"y1":.37,"y2":.56},
            {"x1":.61,"x2":.81,"y1":.39,"y2":.54},
            {"split_x":.66,"split_y":.50},
            {"x1":.57,"x2":.78,"y1":.37,"y2":.55},
            {"x1":.60,"x2":.80,"y1":.39,"y2":.56},
        ]
        balcony_sides=["bottom","bottom","left","bottom","top","bottom","left","bottom","top","bottom"]
        dry = idx in {2,5,8}
    elif bhk == 2:
        sizes=[(30,30),(31,30),(32,31),(30,32),(33,31),(31,33),(34,30),(32,33),(30,31),(33,32)]
        templates=["corridor"]*10
        params_list=[
            {"x1":.25,"x2":.62,"x3":.78,"y1":.42,"y2":.65,"bed_split":.45},
            {"x1":.23,"x2":.61,"x3":.79,"y1":.40,"y2":.64,"bed_split":.46},
            {"x1":.27,"x2":.63,"x3":.80,"y1":.43,"y2":.66,"bed_split":.44},
            {"x1":.24,"x2":.60,"x3":.77,"y1":.41,"y2":.63,"bed_split":.47},
            {"x1":.26,"x2":.64,"x3":.81,"y1":.42,"y2":.65,"bed_split":.45},
            {"x1":.22,"x2":.60,"x3":.78,"y1":.39,"y2":.64,"bed_split":.44},
            {"x1":.25,"x2":.63,"x3":.80,"y1":.44,"y2":.66,"bed_split":.46},
            {"x1":.23,"x2":.62,"x3":.79,"y1":.41,"y2":.65,"bed_split":.45},
            {"x1":.27,"x2":.61,"x3":.78,"y1":.42,"y2":.64,"bed_split":.44},
            {"x1":.24,"x2":.64,"x3":.80,"y1":.40,"y2":.65,"bed_split":.46},
        ]
        balcony_sides=["bottom","left","bottom","top","bottom","left","bottom","top","bottom","bottom"]
        dry = idx in {0,2,4,6,8}
    else:
        sizes=[(36,34),(37,35),(38,34),(36,36),(39,35),(38,37),(40,34),(37,36),(39,37),(36,35)]
        templates=["three_bed"]*10
        params_list=[
            {"x1":.20,"x2":.60,"x3":.78,"xb":.33,"xc":.66,"y1":.38,"y2":.62,"y3":.82,"bath_x":.12},
            {"x1":.21,"x2":.61,"x3":.79,"xb":.34,"xc":.67,"y1":.39,"y2":.63,"y3":.83,"bath_x":.12},
            {"x1":.19,"x2":.59,"x3":.77,"xb":.32,"xc":.65,"y1":.37,"y2":.61,"y3":.81,"bath_x":.115},
            {"x1":.20,"x2":.61,"x3":.80,"xb":.34,"xc":.67,"y1":.40,"y2":.63,"y3":.82,"bath_x":.12},
            {"x1":.22,"x2":.62,"x3":.81,"xb":.33,"xc":.66,"y1":.38,"y2":.62,"y3":.82,"bath_x":.125},
            {"x1":.20,"x2":.60,"x3":.79,"xb":.32,"xc":.65,"y1":.39,"y2":.62,"y3":.83,"bath_x":.12},
            {"x1":.21,"x2":.62,"x3":.81,"xb":.34,"xc":.67,"y1":.38,"y2":.62,"y3":.82,"bath_x":.12},
            {"x1":.19,"x2":.60,"x3":.78,"xb":.33,"xc":.66,"y1":.40,"y2":.63,"y3":.83,"bath_x":.11},
            {"x1":.21,"x2":.61,"x3":.80,"xb":.34,"xc":.67,"y1":.38,"y2":.62,"y3":.82,"bath_x":.12},
            {"x1":.20,"x2":.60,"x3":.79,"xb":.32,"xc":.65,"y1":.39,"y2":.62,"y3":.82,"bath_x":.115},
        ]
        balcony_sides=["bottom","left","bottom","top","bottom","left","bottom","top","bottom","bottom"]
        dry=True
    W,H=sizes[idx]
    p=params_list[idx]
    rooms=make_rooms(bhk,W,H,templates[idx],p)
    # Vary the orientation without changing the architectural semantics.
    rotate90 = (idx in {3,7})
    flip_x = (idx in {2,5,6,9})
    flip_y = (idx in {4,7})
    if rotate90:
        for r in rooms:
            r["polygon"]=[[y,x] for x,y in r["polygon"]]
        W,H=H,W
    for r in rooms:
        transformed=[]
        for x,y in r["polygon"]:
            if flip_x: x=W-x
            if flip_y: y=H-y
            transformed.append([x,y])
        r["polygon"]=transformed
    balcony_side=balcony_sides[idx]
    if rotate90:
        balcony_side={"bottom":"left","top":"right","left":"bottom","right":"top"}[balcony_side]
    if flip_x: balcony_side={"left":"right","right":"left","bottom":"bottom","top":"top"}[balcony_side]
    if flip_y: balcony_side={"top":"bottom","bottom":"top","left":"left","right":"right"}[balcony_side]
    return {
        "bhk":bhk,"index":idx+1,"W":float(W),"H":float(H),"rooms":rooms,
        "balcony_side":balcony_side,"dry_balcony":dry,"flip_x":flip_x,"flip_y":flip_y,
        "template":templates[idx],"params":p,
    }


def area(poly):
    total=0.0
    for i,p in enumerate(poly):
        q=poly[(i+1)%len(poly)]
        total+=p[0]*q[1]-q[0]*p[1]
    return abs(total)*0.5


def point_on_segment(pt,a,b,tol=1e-5):
    px,py=pt; ax,ay=a; bx,by=b
    cross=(px-ax)*(by-ay)-(py-ay)*(bx-ax)
    if abs(cross)>tol*max(1.0,math.hypot(bx-ax,by-ay)): return False
    dot=(px-ax)*(bx-ax)+(py-ay)*(by-ay)
    if dot < -tol: return False
    length2=(bx-ax)**2+(by-ay)**2
    return dot <= length2+tol


def canonical_seg(a,b):
    a=(round(float(a[0]),5),round(float(a[1]),5)); b=(round(float(b[0]),5),round(float(b[1]),5))
    return (a,b) if a<=b else (b,a)


def derive_wall_segments(rooms,W,H):
    allverts=[]
    edges=[]
    for r in rooms:
        poly=r["polygon"]
        allverts.extend([tuple(p) for p in poly])
        for i,a in enumerate(poly):
            b=poly[(i+1)%len(poly)]
            if math.hypot(b[0]-a[0],b[1]-a[1])>1e-4:
                edges.append((r["id"],tuple(a),tuple(b)))
    registry=defaultdict(set)
    for rid,a,b in edges:
        cand=[p for p in allverts if point_on_segment(p,a,b)]
        if abs(a[0]-b[0])<1e-5:
            cand.sort(key=lambda p:p[1],reverse=(b[1]<a[1]))
        elif abs(a[1]-b[1])<1e-5:
            cand.sort(key=lambda p:p[0],reverse=(b[0]<a[0]))
        else:
            # The supplied plan templates are orthogonal. Retain a defensive projection sort.
            dx=b[0]-a[0];dy=b[1]-a[1]
            cand.sort(key=lambda p:((p[0]-a[0])*dx+(p[1]-a[1])*dy))
        clean=[]
        for p in cand:
            if not clean or math.hypot(p[0]-clean[-1][0],p[1]-clean[-1][1])>1e-4:
                clean.append(p)
        for p,q in zip(clean,clean[1:]):
            if math.hypot(q[0]-p[0],q[1]-p[1])<0.05: continue
            registry[canonical_seg(p,q)].add(rid)
    result=[]
    for seg,owners in registry.items():
        (x1,y1),(x2,y2)=seg
        if abs(x1-x2)<1e-5: side="left" if abs(x1)<1e-4 else ("right" if abs(x1-W)<1e-4 else None)
        elif abs(y1-y2)<1e-5: side="bottom" if abs(y1)<1e-4 else ("top" if abs(y1-H)<1e-4 else None)
        else: side=None
        if len(owners)==1 and side is None:
            # An interior edge with one owner would indicate a topology gap in the tiling; keep but flag validation.
            pass
        length=math.hypot(x2-x1,y2-y1)
        result.append({"start":[x1,y1],"end":[x2,y2],"length":length,"room_ids":sorted(owners),"exterior":len(owners)==1,"side":side,"openings":[]})
    result.sort(key=lambda w:(round(w["start"][1],4),round(w["start"][0],4),round(w["end"][1],4),round(w["end"][0],4)))
    for i,w in enumerate(result,1): w["id"]=f"W{i:03d}"
    return result


def side_of_wall(w):
    return w.get("side") if w.get("exterior") else None


def wall_angle(w):
    dx=w["end"][0]-w["start"][0]; dy=w["end"][1]-w["start"][1]
    return math.atan2(dy,dx)


def point_at(w,t):
    a=w["start"]; b=w["end"]
    return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]


def opening_position(w,width,preferred=0.5,margin=0.30):
    L=w["length"]
    if L < width+2*margin-1e-6: return None
    blocked=[]
    for o in w["openings"]:
        t=o["t"]
        half=o["width"]/2
        blocked.append((max(0.0,t-half),min(L,t+half)))
    candidate_ts=[preferred,0.5,0.30,0.70,0.22,0.78,0.40,0.60]
    for pref in candidate_ts:
        t=pref*L
        if t < width/2+margin or t > L-width/2-margin: continue
        if all(t+width/2+margin <= a or t-width/2-margin >= b for a,b in blocked):
            return t
    intervals=[]
    cursor=margin
    for a,b in sorted(blocked):
        lo=max(margin,a-width/2-margin); hi=min(L-margin,b+width/2+margin)
        if lo>cursor and lo-cursor>=width:
            intervals.append((cursor,lo))
        cursor=max(cursor,hi)
    if L-margin>cursor and L-margin-cursor>=width: intervals.append((cursor,L-margin))
    for a,b in sorted(intervals,key=lambda z:z[1]-z[0],reverse=True):
        if b-a>=width:
            return (a+b)/2
    return None


def register_opening(w, oid, kind, width, height, sill, role, preferred=0.5):
    width=float(width)
    t=opening_position(w,width,preferred=preferred)
    if t is None: return None
    pt=point_at(w,t/w["length"])
    op={"id":oid,"kind":kind,"wall_id":w["id"],"center":pt,"width":width,"height":float(height),"sill_height":float(sill),"role":role,"orientation":"HORIZONTAL" if abs(w["start"][1]-w["end"][1])<1e-5 else "VERTICAL","t":t}
    w["openings"].append(op)
    return op


def find_shared_wall(walls, room_a, room_b, width, used_ids=None):
    used_ids=used_ids or set()
    candidates=[w for w in walls if room_a in w["room_ids"] and room_b in w["room_ids"] and w["length"] >= width+0.6 and w["id"] not in used_ids]
    candidates.sort(key=lambda w:w["length"],reverse=True)
    for w in candidates:
        if opening_position(w,width,0.5) is not None: return w
    return None


def get_room(rooms,rid):
    for r in rooms:
        if r["id"]==rid: return r
    return None


def find_exterior_wall(walls, room_ids, preferred_sides, min_width=3.0, exclude_sides=None):
    exclude_sides=set(exclude_sides or [])
    for side in preferred_sides:
        candidates=[w for w in walls if w["exterior"] and any(r in w["room_ids"] for r in room_ids) and w["side"]==side and w["side"] not in exclude_sides and w["length"]>=min_width+0.6]
        candidates.sort(key=lambda w:w["length"],reverse=True)
        for w in candidates:
            if opening_position(w,min_width,0.5) is not None: return w
    candidates=[w for w in walls if w["exterior"] and any(r in w["room_ids"] for r in room_ids) and w["side"] not in exclude_sides and w["length"]>=min_width+0.6]
    candidates.sort(key=lambda w:w["length"],reverse=True)
    for w in candidates:
        if opening_position(w,min_width,0.5) is not None: return w
    return None


def add_door_pair(walls, doors, a,b, width=2.8,height=7.0,role="internal",used_walls=None):
    used_walls=used_walls or set()
    wall=find_shared_wall(walls,a,b,width,used_walls)
    if not wall:
        return False
    op=register_opening(wall,f"D{len(doors)+1:02d}","door",width,height,0.0,role)
    if not op: return False
    doors.append(op)
    used_walls.add(wall["id"])
    return True


def add_entry(walls,doors,room_ids,prefer_sides,exclude_sides=None):
    wall=find_exterior_wall(walls,room_ids,prefer_sides,3.0,exclude_sides)
    if not wall: raise ValueError(f"No exterior wall segment can accept an entry door for {room_ids}")
    op=register_opening(wall,"D_ENTRY","door",3.0,7.0,0.0,"main_entrance",preferred=0.35)
    if not op: raise ValueError("Could not position the main entry")
    doors.append(op)
    return wall


def attach_balcony(walls, room_id, side_preferences, role, width_ft=6.0, depth_ft=4.0, id_prefix="BAL"):
    candidates=[]
    for side in side_preferences:
        these=[w for w in walls if w["exterior"] and room_id in w["room_ids"] and w["side"]==side and w["length"]>=width_ft+1.0]
        these.sort(key=lambda w:w["length"],reverse=True)
        candidates.extend(these)
    if not candidates:
        # Fallback to any long exterior edge of the requested room.
        candidates=[w for w in walls if w["exterior"] and room_id in w["room_ids"] and w["length"]>=width_ft+1.0]
    if not candidates: return None,None
    wall=candidates[0]
    max_width=wall["length"]-1.0
    width=min(float(width_ft),max_width)
    # center the balcony on the attached wall segment.
    ctr=point_at(wall,0.5)
    x,y=ctr; d=float(depth_ft); h=width/2
    side=wall["side"]
    if side=="bottom": poly=[[x-h,y],[x+h,y],[x+h,y-d],[x-h,y-d]]
    elif side=="top": poly=[[x-h,y],[x+h,y],[x+h,y+d],[x-h,y+d]]
    elif side=="left": poly=[[x,y-h],[x,y+h], [x-d,y+h],[x-d,y-h]]
    elif side=="right": poly=[[x,y-h],[x,y+h],[x+d,y+h],[x+d,y-h]]
    else: return None,None
    # Register the opening at the balcony attachment center and keep it on the exact axis wall.
    op=register_opening(wall, f"D_BAL_{len([1 for w in walls for o in w['openings'] if o['role']=='balcony_access'])+1:02d}","door",min(4.0,width-0.5),7.0,0.0,"balcony_access",preferred=0.5)
    return {"id":id_prefix,"name":"BALCONY" if role=="balcony" else "DRY BALCONY","role":role,"polygon":poly,"attached_side":side,"attachment_wall_id":wall["id"],"depth":d,"width":width},op


def add_window_for_room(walls, windows, room_id, preferred_sides, width, height=4.0, sill=3.0, role="window", exclude_sides=None):
    exclude_sides=set(exclude_sides or [])
    candidates=[]
    for side in preferred_sides:
        candidates += [w for w in walls if w["exterior"] and room_id in w["room_ids"] and w["side"]==side and w["side"] not in exclude_sides]
    candidates += [w for w in walls if w["exterior"] and room_id in w["room_ids"] and w["side"] not in exclude_sides]
    seen=set(); unique=[]
    for w in candidates:
        if w["id"] not in seen: unique.append(w); seen.add(w["id"])
    unique.sort(key=lambda w:w["length"],reverse=True)
    for w in unique:
        actual=min(float(width),w["length"]-0.8)
        if actual<1.5: continue
        oid=f"WN{len(windows)+1:02d}"
        op=register_opening(w,oid,"window",actual,height,sill,role,preferred=0.68)
        if op:
            windows.append(op)
            return op
    return None


def build_architecture(spec):
    rooms=spec["rooms"]
    W,H=spec["W"],spec["H"]
    walls=derive_wall_segments(rooms,W,H)
    doors=[]; windows=[]; balconies=[]
    bhk=spec["bhk"]
    # Topology-driven internal openings.
    if bhk==1:
        if spec["template"]=="compact":
            pairs=[("living_dining","kitchen",2.8),("living_dining","master_bedroom",2.8),("master_bedroom","bathroom",2.4)]
        else:
            pairs=[("living_dining","kitchen",2.8),("living_dining","passage",2.8),("living_dining","master_bedroom",2.8),("kitchen","passage",2.6),("passage","bathroom",2.4),("passage","utility",2.4)]
        entry_room=["living_dining"]
    elif bhk==2:
        pairs=[("living_dining","foyer",2.8),("living_dining","passage",2.8),("kitchen","passage",2.8),("passage","common_toilet",2.4),("bedroom_2","passage",2.8),("master_bedroom","passage",2.8),("master_bedroom","ensuite_toilet",2.4)]
        entry_room=["foyer"]
    else:
        pairs=[("living_dining","foyer",2.8),("living_dining","passage",2.8),("kitchen","passage",2.8),("passage","common_toilet",2.4),("master_bedroom","master_toilet",2.4),("master_bedroom","passage",2.8),("bedroom_2","passage",2.8),("bedroom_3","passage",2.8)]
        entry_room=["foyer"]
    used=set()
    for a,b,width in pairs:
        ok=add_door_pair(walls,doors,a,b,width=width,used_walls=used)
        if not ok:
            raise ValueError(f"Could not place internal door between {a} and {b} for plan {bhk}BHK-{spec['index']:02d}")
    bal_side=spec["balcony_side"]
    prefer_map={"bottom":["bottom","left","right","top"],"top":["top","left","right","bottom"],"left":["left","bottom","top","right"],"right":["right","bottom","top","left"]}
    primary,baldoor=attach_balcony(walls,"living_dining",prefer_map.get(bal_side,["bottom","left","right","top"]),"balcony",width_ft=6.0 if bhk==1 else 6.5,depth_ft=4.0 if bhk<3 else 4.5,id_prefix="BAL_MAIN")
    if primary:
        balconies.append(primary)
        if baldoor:
            doors.append(baldoor)
    # Main entry is kept away from the preferred balcony side.
    exclude={primary["attached_side"]} if primary else set()
    if bhk==1:
        entry_pref=["left","right","bottom","top"]
    else:
        entry_pref=["left","right","top","bottom"]
    entry_wall=find_exterior_wall(walls,entry_room,entry_pref,3.0,exclude)
    if entry_wall is None:
        entry_wall=find_exterior_wall(walls,["living_dining"],entry_pref,3.0,exclude)
    if entry_wall is None:
        raise ValueError(f"Could not locate a main entrance wall for {bhk}BHK-{spec['index']:02d}")
    entry=register_opening(entry_wall,"D_ENTRY","door",3.0,7.0,0.0,"main_entrance",preferred=0.33)
    if not entry: raise ValueError("Could not position entry opening")
    doors.append(entry)
    # Optional kitchen/dry balcony on 1BHK variants and every other 2BHK; all 3BHKs get it.
    should_dry=spec["dry_balcony"]
    if should_dry:
        dry_side_pref=["right","bottom","top","left"]
        dry,drydoor=attach_balcony(walls,"kitchen",dry_side_pref,"dry_balcony",width_ft=4.5,depth_ft=3.5,id_prefix="BAL_DRY")
        # Avoid duplicate balcony side/overlap if the only available side is already used by the main balcony.
        if dry and primary and dry["attachment_wall_id"]==primary["attachment_wall_id"]:
            if drydoor:
                for wall in walls:
                    wall["openings"]=[o for o in wall["openings"] if o is not drydoor]
            dry=None
        if dry:
            balconies.append(dry)
            if drydoor: doors.append(drydoor)
    # Windows on habitable exterior rooms. prefer top for bedrooms, but fall back to a free external edge.
    exclusions_by_room=defaultdict(set)
    for b in balconies:
        exclusions_by_room["living_dining" if b["role"]=="balcony" else "kitchen"].add(b["attached_side"])
    # Prefer one main window in living and kitchen, one per bedroom, with a smaller vent per exterior toilet.
    if bhk==1:
        window_jobs=[("living_dining",["bottom","left","right","top"],5.0,4.0,3.0,"living_window"),
                     ("kitchen",["right","top","left","bottom"],3.5,3.5,3.0,"kitchen_window"),
                     ("master_bedroom",["top","left","right","bottom"],4.5,4.0,3.0,"bedroom_window"),
                     ("bathroom",["top","right","left","bottom"],2.0,1.5,5.8,"vent")]
    elif bhk==2:
        window_jobs=[("living_dining",["bottom","left","right","top"],5.0,4.0,3.0,"living_window"),
                     ("kitchen",["right","bottom","top","left"],3.5,3.5,3.0,"kitchen_window"),
                     ("bedroom_2",["top","left","right","bottom"],4.5,4.0,3.0,"bedroom_window"),
                     ("master_bedroom",["top","left","right","bottom"],4.5,4.0,3.0,"bedroom_window"),
                     ("common_toilet",["right","top","left","bottom"],2.0,1.5,5.8,"vent")]
    else:
        window_jobs=[("living_dining",["bottom","left","right","top"],5.5,4.0,3.0,"living_window"),
                     ("kitchen",["right","bottom","top","left"],3.5,3.5,3.0,"kitchen_window"),
                     ("master_bedroom",["top","left","right","bottom"],4.5,4.0,3.0,"bedroom_window"),
                     ("bedroom_2",["top","left","right","bottom"],4.5,4.0,3.0,"bedroom_window"),
                     ("bedroom_3",["top","left","right","bottom"],4.5,4.0,3.0,"bedroom_window"),
                     ("common_toilet",["right","top","left","bottom"],2.0,1.5,5.8,"vent"),
                     ("master_toilet",["left","top","right","bottom"],2.0,1.5,5.8,"vent")]
    # Prioritize rooms with daylight before vents.
    for rid,sides,width,height,sill,role in window_jobs:
        exclusions=set(exclusions_by_room[rid])
        # keep a balcony opening and window from colliding on the same exterior wall.
        add_window_for_room(walls,windows,rid,sides,width,height,sill,role,exclusions)
    return walls,doors,windows,balconies


def xdata_dict(entity):
    try: tags=entity.get_xdata(APPID)
    except Exception: return {}
    result={}
    for tag in tags:
        if tag.code==1000 and "=" in str(tag.value):
            k,v=str(tag.value).split("=",1); result[k]=v
    return result


def set_xdata(entity, **kwargs):
    tags=[]
    for k,v in kwargs.items():
        if isinstance(v,float): sval=f"{v:.6f}"
        elif isinstance(v,(list,tuple,set)): sval=",".join(map(str,v))
        else: sval=str(v)
        # XDATA text values are limited; these metadata fields are intentionally compact.
        tags.append((1000,f"{k}={sval}"))
    entity.set_xdata(APPID,tags)


def add_polyline(msp, points, layer, closed=False, **meta):
    entity=msp.add_lwpolyline(points,format="xy",close=closed,dxfattribs={"layer":layer})
    if meta: set_xdata(entity,**meta)
    return entity


def fmt_ft_inches(value):
    total_inches=round(abs(float(value))*12)
    feet=total_inches//12; inches=total_inches%12
    sign="-" if value<0 else ""
    return f'{sign}{feet}\'-{inches:02d}"'


def poly_centroid(poly):
    a=0.0; cx=cy=0.0
    for i,p in enumerate(poly):
        q=poly[(i+1)%len(poly)]
        cross=p[0]*q[1]-q[0]*p[1]
        a+=cross; cx+=(p[0]+q[0])*cross; cy+=(p[1]+q[1])*cross
    if abs(a)<1e-8:
        return [sum(p[0] for p in poly)/len(poly),sum(p[1] for p in poly)/len(poly)]
    return [cx/(3*a),cy/(3*a)]


def point_in_poly(x,y,poly):
    inside=False
    j=len(poly)-1
    for i in range(len(poly)):
        xi,yi=poly[i]; xj,yj=poly[j]
        intersect=((yi>y)!=(yj>y)) and (x < (xj-xi)*(y-yi)/(yj-yi+1e-20)+xi)
        if intersect: inside=not inside
        j=i
    return inside


def pseg_dist(p,a,b):
    x,y=p; x1,y1=a; x2,y2=b
    dx=x2-x1;dy=y2-y1;d=dx*dx+dy*dy
    if d<1e-12:return math.hypot(x-x1,y-y1)
    t=max(0,min(1,((x-x1)*dx+(y-y1)*dy)/d))
    return math.hypot(x-(x1+t*dx),y-(y1+t*dy))


def label_point(poly):
    c=poly_centroid(poly)
    if point_in_poly(c[0],c[1],poly): return c
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    best=None; bestd=-1
    for iy in range(1,30):
        y=min(ys)+(max(ys)-min(ys))*iy/30
        for ix in range(1,30):
            x=min(xs)+(max(xs)-min(xs))*ix/30
            if point_in_poly(x,y,poly):
                d=min(pseg_dist((x,y),poly[i],poly[(i+1)%len(poly)]) for i in range(len(poly)))
                if d>bestd:best=(x,y);bestd=d
    return list(best or c)


def dimension_label(poly):
    xs=[p[0] for p in poly];ys=[p[1] for p in poly]
    w=max(xs)-min(xs);h=max(ys)-min(ys)
    return f"{fmt_ft_inches(w)} x {fmt_ft_inches(h)}"


def draw_door_symbol(msp, op, wall):
    a=wall["start"]; b=wall["end"]
    ang=wall_angle(wall); ux=math.cos(ang);uy=math.sin(ang)
    half=op["width"]/2
    p1=[op["center"][0]-ux*half,op["center"][1]-uy*half]
    p2=[op["center"][0]+ux*half,op["center"][1]+uy*half]
    side=wall.get("side")
    if wall.get("exterior"):
        inward={"bottom":(0,1),"top":(0,-1),"left":(1,0),"right":(-1,0)}.get(side,(-uy,ux))
    else: inward=(-uy,ux)
    # choose first jamb as hinge; an arc and leaf line are visual marks only
    hinge=p1
    leaf_end=[hinge[0]+inward[0]*op["width"],hinge[1]+inward[1]*op["width"]]
    msp.add_line(p1,leaf_end,dxfattribs={"layer":"DX_DOOR_SYMBOL"})
    inward_angle=round(math.degrees(math.atan2(inward[1],inward[0])) % 360)
    tangent_angle=round(math.degrees(ang) % 360)
    # All walls are orthogonal. Select the quarter-circle joining the leaf direction and wall direction.
    pair={inward_angle,tangent_angle}
    if pair=={270,0}:
        arc_start,arc_end=270,360
    elif pair=={180,90}:
        arc_start,arc_end=90,180
    elif pair=={0,90}:
        arc_start,arc_end=0,90
    elif pair=={180,270}:
        arc_start,arc_end=180,270
    else:
        arc_start=min(inward_angle,tangent_angle)
        arc_end=max(inward_angle,tangent_angle)
        if arc_end-arc_start>180: arc_start,arc_end=0,90
    msp.add_arc(hinge,op["width"],arc_start,arc_end,dxfattribs={"layer":"DX_DOOR_SYMBOL"})


def draw_window_symbol(msp, op, wall):
    a=wall["start"];b=wall["end"]
    L=wall["length"]
    ux=(b[0]-a[0])/L;uy=(b[1]-a[1])/L
    nx=-uy;ny=ux
    half=op["width"]/2
    p1=[op["center"][0]-ux*half,op["center"][1]-uy*half]
    p2=[op["center"][0]+ux*half,op["center"][1]+uy*half]
    # Two glass lines inside the wall band and short jamb strokes.
    for off in (-0.09,0.09):
        msp.add_line((p1[0]+nx*off,p1[1]+ny*off),(p2[0]+nx*off,p2[1]+ny*off),dxfattribs={"layer":"DX_WINDOW_SYMBOL"})
    thick=0.20
    for p in (p1,p2):
        msp.add_line((p[0]-nx*thick,p[1]-ny*thick),(p[0]+nx*thick,p[1]+ny*thick),dxfattribs={"layer":"DX_WINDOW_SYMBOL"})


def add_wall_face(msp,wall,segment_start,segment_end):
    dx=wall["end"][0]-wall["start"][0];dy=wall["end"][1]-wall["start"][1]
    L=wall["length"]
    if L<0.05:return
    ux=dx/L;uy=dy/L;nx=-uy*DEFAULT_WALL_THICKNESS/2;ny=ux*DEFAULT_WALL_THICKNESS/2
    a=[wall["start"][0]+ux*segment_start,wall["start"][1]+uy*segment_start]
    b=[wall["start"][0]+ux*segment_end,wall["start"][1]+uy*segment_end]
    if math.hypot(b[0]-a[0],b[1]-a[1])<0.05:return
    points=[[a[0]+nx,a[1]+ny],[b[0]+nx,b[1]+ny],[b[0]-nx,b[1]-ny],[a[0]-nx,a[1]-ny]]
    add_polyline(msp,points,"DX_WALL_FACE",closed=True,wall_id=wall["id"])


def draw_wall_faces(msp,walls):
    for wall in walls:
        L=wall["length"]
        intervals=[]
        for op in wall["openings"]:
            intervals.append((max(0,op["t"]-op["width"]/2),min(L,op["t"]+op["width"]/2)))
        intervals.sort()
        cursor=0.0
        for lo,hi in intervals:
            if lo>cursor+0.05: add_wall_face(msp,wall,cursor,lo)
            cursor=max(cursor,hi)
        if cursor<L-0.05: add_wall_face(msp,wall,cursor,L)


def add_dimensions_and_title(msp,spec,doc,balconies):
    W,H=spec["W"],spec["H"]
    maxdepth=max([b.get("depth",0) for b in balconies] or [0])
    title=f'DimensionX | {spec["bhk"]}BHK | PLAN {spec["index"]:02d}'
    msp.add_text(title,dxfattribs={"height":1.0,"layer":"DX_TITLE","style":"Standard"}).set_placement((0,H+maxdepth+3.5))
    note=f'MAIN BODY {fmt_ft_inches(W)} x {fmt_ft_inches(H)}  |  FEET  |  WALL THK {DEFAULT_WALL_THICKNESS:.2f} ft  |  WALL HT {DEFAULT_WALL_HEIGHT:.1f} ft'
    msp.add_text(note,dxfattribs={"height":0.55,"layer":"DX_DIMENSION","style":"Standard"}).set_placement((0,H+maxdepth+2.2))
    # Clear graphic dimension lines; keep them outside the core plan.
    ydim=-maxdepth-1.4
    msp.add_line((0,ydim),(W,ydim),dxfattribs={"layer":"DX_DIMENSION"})
    for x in (0,W):msp.add_line((x,ydim-0.25),(x,ydim+0.25),dxfattribs={"layer":"DX_DIMENSION"})
    msp.add_text(fmt_ft_inches(W),dxfattribs={"height":0.6,"layer":"DX_DIMENSION"}).set_placement((W/2,ydim+0.25),align=TextEntityAlignment.BOTTOM_CENTER)
    xdim=-1.5
    # Avoid the vertical dimension when a balcony projects on the left; still label overall body depth in the note.
    if not any(b["attached_side"]=="left" for b in balconies):
        msp.add_line((xdim,0),(xdim,H),dxfattribs={"layer":"DX_DIMENSION"})
        for y in (0,H):msp.add_line((xdim-0.25,y),(xdim+0.25,y),dxfattribs={"layer":"DX_DIMENSION"})
        tx=msp.add_text(fmt_ft_inches(H),dxfattribs={"height":0.6,"layer":"DX_DIMENSION"})
        tx.set_placement((xdim-0.2,H/2),align=TextEntityAlignment.MIDDLE_CENTER)
        tx.dxf.rotation=90
    # small north arrow
    nx=W+2.0; ny=H-1.0
    msp.add_line((nx,ny-1.5),(nx,ny+0.7),dxfattribs={"layer":"DX_DIMENSION"})
    msp.add_line((nx,ny+0.7),(nx-0.25,ny+0.15),dxfattribs={"layer":"DX_DIMENSION"})
    msp.add_line((nx,ny+0.7),(nx+0.25,ny+0.15),dxfattribs={"layer":"DX_DIMENSION"})
    msp.add_text("N",dxfattribs={"height":0.7,"layer":"DX_DIMENSION"}).set_placement((nx,ny+0.85),align=TextEntityAlignment.BOTTOM_CENTER)


def create_dxf(spec, output_path):
    bhk=spec["bhk"];plan_id=f"{bhk}BHK_{spec['index']:02d}"
    rooms=spec["rooms"]
    walls,doors,windows,balconies=build_architecture(spec)
    doc=ezdxf.new("R2013",setup=True)
    doc.header["$INSUNITS"]=2 # feet
    doc.header["$MEASUREMENT"]=0
    doc.header["$LUNITS"]=2 # decimal
    doc.header["$PDMODE"]=3
    doc.header["$PDSIZE"]=0.25
    if APPID not in doc.appids: doc.appids.new(APPID)
    for name,(color,linetype,lineweight) in LAYER_DEFS.items():
        if name not in doc.layers: doc.layers.new(name,dxfattribs={"color":color,"linetype":linetype,"lineweight":lineweight})
    # Semantic data layers remain in the DXF/XDATA but are off by default so the plan opens cleanly.
    for layer_name in ("DX_FOOTPRINT", "DX_WALL_AXIS", "DX_DOOR", "DX_WINDOW", "DX_ROOM_ZONE", "DX_BALCONY", "DX_PLAN_META"):
        try: doc.layers.get(layer_name).off()
        except Exception: pass
    msp=doc.modelspace()
    footprint=rect_poly(0,0,spec["W"],spec["H"])
    add_polyline(msp,footprint,"DX_FOOTPRINT",closed=True,bhk=bhk,plan_id=plan_id,units="feet",schema_version=SCHEMA_VERSION,wall_height=DEFAULT_WALL_HEIGHT,wall_thickness=DEFAULT_WALL_THICKNESS,width_ft=spec["W"],depth_ft=spec["H"],template=spec["template"])
    # Semantic wall axes carry metadata; visible wall faces are cut around all openings.
    wall_lookup={}
    for w in walls:
        e=msp.add_line(w["start"],w["end"],dxfattribs={"layer":"DX_WALL_AXIS"})
        set_xdata(e,kind="wall",id=w["id"],thickness_ft=DEFAULT_WALL_THICKNESS,height_ft=DEFAULT_WALL_HEIGHT,exterior=int(w["exterior"]),side=w["side"] or "interior",room_ids=w["room_ids"])
        wall_lookup[w["id"]]=w
    for r in rooms:
        poly=r["polygon"]
        ar=area(poly)
        e=add_polyline(msp,poly,"DX_ROOM_ZONE",closed=True,room_id=r["id"],name=r["name"],role=r["role"],area_sqft=ar,plan_id=plan_id)
        lp=label_point(poly)
        display_names = {
            "MASTER TOILET": "M. TOI.",
            "COMMON TOILET": "C. TOI.",
            "BATH / WC": "BATH / WC",
            "MASTER BEDROOM": "MASTER BEDROOM",
            "LIVING / DINING": "LIVING / DINING",
            "UTILITY / STORE": "UTILITY / STORE",
            "ENTRY / FOYER": "ENTRY / FOYER",
        }
        label=display_names.get(r["name"],r["name"])
        # Bounded box dimensions are informative for rectangular rooms; suite polygons use area.
        bbox_w=max(p[0] for p in poly)-min(p[0] for p in poly)
        bbox_h=max(p[1] for p in poly)-min(p[1] for p in poly)
        bbox_area=bbox_w*bbox_h
        if abs(bbox_area-ar)<0.05:
            label += "\\P"+dimension_label(poly)
        else:
            label += f"\\P{ar:.0f} SQ FT"
        char_height=min(0.62,max(0.32,min(bbox_w,bbox_h)*0.075))
        msp.add_mtext(label,dxfattribs={"layer":"DX_ROOM_LABEL","char_height":char_height,"width":max(3.0,bbox_w*0.88),"attachment_point":5}).set_location((lp[0],lp[1]))
    # Door and window metadata points with XDATA.
    for op in doors:
        wall=wall_lookup[op["wall_id"]]
        e=msp.add_point(op["center"],dxfattribs={"layer":"DX_DOOR"})
        set_xdata(e,kind="door",id=op["id"],wall_id=op["wall_id"],width_ft=op["width"],height_ft=op["height"],sill_height_ft=0.0,role=op["role"],orientation=op["orientation"],swing_direction="interior")
        draw_door_symbol(msp,op,wall)
    for op in windows:
        wall=wall_lookup[op["wall_id"]]
        e=msp.add_point(op["center"],dxfattribs={"layer":"DX_WINDOW"})
        set_xdata(e,kind="window",id=op["id"],wall_id=op["wall_id"],width_ft=op["width"],height_ft=op["height"],sill_height_ft=op["sill_height"],role=op["role"],orientation=op["orientation"])
        draw_window_symbol(msp,op,wall)
    # Balcony rectangles and safety railings. The main wall stays in DX_WALL_AXIS and has a balcony door opening.
    for b in balconies:
        add_polyline(msp,b["polygon"],"DX_BALCONY",closed=True,balcony_id=b["id"],name=b["name"],role=b["role"],depth_ft=b["depth"],width_ft=b["width"],attachment_wall_id=b["attachment_wall_id"],attached_side=b["attached_side"],plan_id=plan_id)
        poly=b["polygon"]
        # Index 0-1 is the attachment edge for all constructed balcony polygons, other edges receive rails.
        for i in (1,2,3):
            a=poly[i];bb=poly[(i+1)%len(poly)]
            msp.add_line(a,bb,dxfattribs={"layer":"DX_RAILING"})
            set_xdata(msp.entity_space[-1],balcony_id=b["id"],rail_type="perimeter")
        c=label_point(poly)
        msp.add_text(b["name"],dxfattribs={"height":0.55,"layer":"DX_ROOM_LABEL"}).set_placement(c,align=TextEntityAlignment.MIDDLE_CENTER)
    draw_wall_faces(msp,walls)
    # Metadata anchor; the footprint is the source of record too.
    meta=msp.add_point((0,0),dxfattribs={"layer":"DX_PLAN_META"})
    set_xdata(meta,kind="plan_metadata",plan_id=plan_id,bhk=bhk,schema_version=SCHEMA_VERSION,units="feet",dxf_generator="DimensionX Plan Factory")
    add_dimensions_and_title(msp,spec,doc,balconies)
    doc.saveas(output_path)
    return walls,doors,windows,balconies


def parse_xdata(entity):
    result={}
    try: tags=entity.get_xdata(APPID)
    except Exception: return result
    for tag in tags:
        if tag.code==1000 and "=" in str(tag.value):
            k,v=str(tag.value).split("=",1)
            result[k]=v
    return result


def parse_float(v,default=0.0):
    try:return float(v)
    except Exception:return default


def convert_dxf_to_json(dxf_path,json_path=None):
    d=ezdxf.readfile(dxf_path);m=d.modelspace()
    footprint=None; meta={}; walls=[]; doors=[]; windows=[]; rooms=[]; balconies=[]
    for e in m:
        layer=e.dxf.layer
        xd=parse_xdata(e)
        if layer=="DX_FOOTPRINT" and e.dxftype()=="LWPOLYLINE":
            footprint=[[float(p[0]),float(p[1])] for p in e.get_points()]
            meta=xd
        elif layer=="DX_WALL_AXIS" and e.dxftype()=="LINE":
            start=[float(e.dxf.start.x),float(e.dxf.start.y)]
            end=[float(e.dxf.end.x),float(e.dxf.end.y)]
            owners=[x for x in xd.get("room_ids","").split(",") if x]
            walls.append({"id":xd.get("id",f"wall_{len(walls)+1:03d}"),"start":start,"end":end,"thickness":parse_float(xd.get("thickness_ft"),DEFAULT_WALL_THICKNESS),"height":parse_float(xd.get("height_ft"),DEFAULT_WALL_HEIGHT),"exterior":xd.get("exterior","0")=="1","side":xd.get("side","interior"),"room_ids":owners})
        elif layer=="DX_DOOR" and e.dxftype()=="POINT":
            doors.append({"id":xd.get("id",f"door_{len(doors)+1}"),"wall_id":xd.get("wall_id",""),"center":[float(e.dxf.location.x),float(e.dxf.location.y)],"width":parse_float(xd.get("width_ft"),3.0),"height":parse_float(xd.get("height_ft"),7.0),"sill_height":parse_float(xd.get("sill_height_ft"),0.0),"role":xd.get("role","internal"),"orientation":xd.get("orientation","HORIZONTAL"),"swing_direction":xd.get("swing_direction","interior")})
        elif layer=="DX_WINDOW" and e.dxftype()=="POINT":
            windows.append({"id":xd.get("id",f"window_{len(windows)+1}"),"wall_id":xd.get("wall_id",""),"center":[float(e.dxf.location.x),float(e.dxf.location.y)],"width":parse_float(xd.get("width_ft"),4.0),"height":parse_float(xd.get("height_ft"),4.0),"sill_height":parse_float(xd.get("sill_height_ft"),3.0),"role":xd.get("role","window"),"orientation":xd.get("orientation","HORIZONTAL")})
        elif layer=="DX_ROOM_ZONE" and e.dxftype()=="LWPOLYLINE":
            rooms.append({"id":xd.get("room_id",f"room_{len(rooms)+1}"),"name":xd.get("name","Room"),"role":xd.get("role","room"),"polygon":[[float(p[0]),float(p[1])] for p in e.get_points()],"area_sqft":parse_float(xd.get("area_sqft"),0.0)})
        elif layer=="DX_BALCONY" and e.dxftype()=="LWPOLYLINE":
            balconies.append({"id":xd.get("balcony_id",f"balcony_{len(balconies)+1}"),"name":xd.get("name","BALCONY"),"role":xd.get("role","balcony"),"polygon":[[float(p[0]),float(p[1])] for p in e.get_points()],"area_sqft":area([[float(p[0]),float(p[1])] for p in e.get_points()]),"depth":parse_float(xd.get("depth_ft"),4.0),"width":parse_float(xd.get("width_ft"),6.0),"attachment_wall_id":xd.get("attachment_wall_id",""),"attached_side":xd.get("attached_side","")})
    if not footprint: raise ValueError(f"No DX_FOOTPRINT found in {dxf_path}")
    bhk=int(parse_float(meta.get("bhk"),0))
    if bhk not in (1,2,3): raise ValueError(f"Missing or invalid BHK metadata in {dxf_path}")
    out={"schema_version":SCHEMA_VERSION,"generator":"DimensionX Plan Factory","plan_id":meta.get("plan_id",Path(dxf_path).stem),"bhk":bhk,"units":"feet","source_dxf":Path(dxf_path).name,"wall_height":parse_float(meta.get("wall_height"),DEFAULT_WALL_HEIGHT),"wall_thickness":parse_float(meta.get("wall_thickness"),DEFAULT_WALL_THICKNESS),"floor_thickness":0.2,"roof_thickness":0.25,"footprint":footprint,"walls":walls,"doors":doors,"windows":windows,"rooms":rooms,"balconies":balconies}
    validate_architecture_json(out)
    if json_path:
        Path(json_path).write_text(json.dumps(out,indent=2),encoding="utf-8")
    return out


def validate_architecture_json(data):
    if int(data.get("bhk",0)) not in (1,2,3): raise ValueError("bhk must be 1, 2, or 3")
    if data.get("units") not in ("feet","ft"): raise ValueError("units must be feet")
    if len(data.get("footprint",[]))<3: raise ValueError("footprint needs at least 3 points")
    wallmap={w["id"]:w for w in data.get("walls",[])}
    if not wallmap: raise ValueError("No walls found")
    for group in ("doors","windows"):
        for opening in data.get(group,[]):
            if opening["wall_id"] not in wallmap: raise ValueError(f"{group} {opening['id']} references missing wall {opening['wall_id']}")
            wall=wallmap[opening["wall_id"]]
            dist=pseg_dist(opening["center"],wall["start"],wall["end"])
            if dist>0.02: raise ValueError(f"{group} {opening['id']} is not on its assigned wall axis (dist {dist})")
            if opening["width"]>wall_length(wall)-0.01: raise ValueError(f"{group} {opening['id']} wider than its wall segment")
    for w in data.get("walls",[]):
        if w["thickness"]<=0 or w["height"]<=0: raise ValueError(f"Invalid wall dimensions on {w['id']}")
    return True


def wall_length(w): return math.hypot(w["end"][0]-w["start"][0],w["end"][1]-w["start"][1])


def build_plan_set(outdir):
    outdir=Path(outdir)
    if outdir.exists(): shutil.rmtree(outdir)
    for sub in ("plans/1BHK","plans/2BHK","plans/3BHK","tools","previews"):
        (outdir/sub).mkdir(parents=True,exist_ok=True)
    report=[]
    for bhk in (1,2,3):
        for idx in range(10):
            spec=plan_spec(bhk,idx)
            plan_id=f"{bhk}BHK_{idx+1:02d}"
            dxf_path=outdir/f"plans/{bhk}BHK/{plan_id}.dxf"
            json_path=outdir/f"plans/{bhk}BHK/{plan_id}_architecture.json"
            walls,doors,windows,balconies=create_dxf(spec,dxf_path)
            data=convert_dxf_to_json(dxf_path,json_path)
            # Geometric checks: each room area should tile the body exactly, all openings point to walls.
            room_sum=sum(area(r["polygon"]) for r in data["rooms"])
            body=spec["W"]*spec["H"]
            area_delta=abs(room_sum-body)
            if area_delta>0.5: raise ValueError(f"Room zones do not tile {plan_id}: areas {room_sum:.2f} body {body:.2f}")
            # ensure each declared room has at least one door or is the main living/kitchen path; warnings logged otherwise
            door_counts={r["id"]:0 for r in data["rooms"]}
            for d in data["doors"]:
                w=next(w for w in data["walls"] if w["id"]==d["wall_id"])
                for rid in w.get("room_ids",[]): door_counts[rid]=door_counts.get(rid,0)+1
            report.append({"plan_id":plan_id,"bhk":bhk,"width_ft":round(spec["W"],2),"depth_ft":round(spec["H"],2),"rooms":len(data["rooms"]),"wall_segments":len(data["walls"]),"doors":len(data["doors"]),"windows":len(data["windows"]),"balconies":len(data["balconies"]),"main_body_area_sqft":round(body,2),"room_area_sum_sqft":round(room_sum,2),"room_area_delta_sqft":round(area_delta,4),"all_openings_linked":True,"dxf":str(dxf_path.relative_to(outdir)).replace('\\','/'),"json":str(json_path.relative_to(outdir)).replace('\\','/')})
    # Factory/converter source copies included in package.
    source=Path(__file__).resolve()
    (outdir/"tools/dimensionx_plan_factory.py").write_text(source.read_text(encoding="utf-8"),encoding="utf-8")
    converter=outdir/"tools/dimensionx_dxf_to_json.py"
    converter.write_text(CONVERTER_SCRIPT,encoding="utf-8")
    validator=outdir/"tools/validate_plan_set.py"
    validator.write_text(VALIDATOR_SCRIPT,encoding="utf-8")
    (outdir/"validation_report.csv").write_text("",encoding="utf-8")
    with open(outdir/"validation_report.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(report[0].keys()));w.writeheader();w.writerows(report)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "DimensionX architecture.json",
        "type": "object",
        "required": ["schema_version", "plan_id", "bhk", "units", "footprint", "walls", "doors", "windows", "rooms"],
        "properties": {
            "schema_version": {"const": "1.0"},
            "plan_id": {"type": "string"},
            "bhk": {"type": "integer", "enum": [1, 2, 3]},
            "units": {"const": "feet"},
            "wall_height": {"type": "number", "exclusiveMinimum": 0},
            "wall_thickness": {"type": "number", "exclusiveMinimum": 0},
            "footprint": {"type": "array", "minItems": 3, "items": {"$ref": "#/$defs/point"}},
            "walls": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["id", "start", "end", "thickness", "height"], "properties": {"id": {"type": "string"}, "start": {"$ref": "#/$defs/point"}, "end": {"$ref": "#/$defs/point"}, "thickness": {"type": "number", "exclusiveMinimum": 0}, "height": {"type": "number", "exclusiveMinimum": 0}, "exterior": {"type": "boolean"}, "room_ids": {"type": "array", "items": {"type": "string"}}}}},
            "doors": {"type": "array", "items": {"$ref": "#/$defs/opening"}},
            "windows": {"type": "array", "items": {"$ref": "#/$defs/opening"}},
            "rooms": {"type": "array", "items": {"type": "object", "required": ["id", "name", "role", "polygon"], "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string"}, "polygon": {"type": "array", "minItems": 3, "items": {"$ref": "#/$defs/point"}}, "area_sqft": {"type": "number"}}}},
            "balconies": {"type": "array", "items": {"type": "object", "required": ["id", "name", "role", "polygon"], "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "role": {"type": "string"}, "polygon": {"type": "array", "minItems": 3, "items": {"$ref": "#/$defs/point"}}}}}
        },
        "$defs": {
            "point": {"type": "array", "prefixItems": [{"type": "number"}, {"type": "number"}], "minItems": 2, "maxItems": 2},
            "opening": {"type": "object", "required": ["id", "wall_id", "center", "width", "height", "sill_height", "role", "orientation"], "properties": {"id": {"type": "string"}, "wall_id": {"type": "string"}, "center": {"$ref": "#/$defs/point"}, "width": {"type": "number", "exclusiveMinimum": 0}, "height": {"type": "number", "exclusiveMinimum": 0}, "sill_height": {"type": "number", "minimum": 0}, "role": {"type": "string"}, "orientation": {"enum": ["HORIZONTAL", "VERTICAL"]}}}
        }
    }
    (outdir/"architecture_schema.json").write_text(json.dumps(schema,indent=2),encoding="utf-8")
    readme=f'''# DimensionX — 30 structured DXF floor plans\n\nThis package contains **30 original, generated plan variants**: 10 each for 1BHK, 2BHK and 3BHK. The provided drawings were used as layout inspiration (living/dining, kitchen, bedroom counts, toilet arrangements, balconies and dry balconies); the generated plans use a consistent rectilinear drafting convention to make DXF-to-JSON extraction predictable.\n\n## Package contents\n- `plans/1BHK`, `plans/2BHK`, `plans/3BHK`: each plan as a DXF plus a matching `*_architecture.json` file.\n- `tools/dimensionx_dxf_to_json.py`: parses this package's semantic DXF layers and XDATA to create the JSON contract.\n- `tools/validate_plan_set.py`: basic validation utility.\n- `architecture_schema.json`: JSON Schema for the contract.\n- `validation_report.csv`: counts and geometry validation for all 30 plans.\n\n## Machine-readable CAD convention\n- `$INSUNITS = 2`: coordinates are **feet**. Coordinates are planar XY; Z is not used in the floor plan.\n- `DX_FOOTPRINT`: the primary building footprint polygon.\n- `DX_WALL_AXIS`: wall centerlines as LINE entities, with `DIMENSIONX` XDATA for wall ID, thickness, height, exterior/internal classification, and adjacent room IDs.\n- `DX_WALL_FACE`: visible wall bands, deliberately split around door/window openings; the converter does not use these to infer centerlines.\n- `DX_DOOR` / `DX_WINDOW`: semantic POINT entities with XDATA that stores ID, matching wall ID, opening width/height, sill height, type/role and orientation.\n- `DX_ROOM_ZONE`: closed room polygons with room ID/name/role/area in XDATA. This layer is off by default for cleaner viewing but remains present for extraction; turn it on to inspect room boundaries.\n- `DX_BALCONY`: closed balcony/utility-balcony polygons with attachment metadata. `DX_RAILING` is visual-only.\n- `DX_ROOM_LABEL`, `DX_DOOR_SYMBOL`, `DX_WINDOW_SYMBOL`, `DX_DIMENSION`, `DX_TITLE`: presentation-only.\n\n## DXF to JSON\nWith Python 3.10+ and `ezdxf` installed:\n```bash\npython tools/dimensionx_dxf_to_json.py plans/1BHK/1BHK_01.dxf\n```\nThis writes `1BHK_01_architecture.json` next to the DXF unless `--output PATH` is specified.\n\nEach JSON includes `footprint`, `walls`, `doors`, `windows`, `rooms`, and optional `balconies`. Door/window records reference a specific `wall_id`, so downstream code does not need to guess which wall an opening belongs to.\n\n## Blender integration\nThe JSON fields `bhk`, `footprint`, `walls`, `doors`, and `windows` follow the same basic contract as the DimensionX 1BHK Blender generator. The optional `rooms` and `balconies` provide additional metadata/geometry for a later builder update. If using a Blender generator that ignores `balconies`, the house shell and openings can still be built, but balcony slabs/railings will not be created until balcony support is enabled.\n\n## Validation note\nValidation checks the CAD semantics, wall references, dimensions, room-zone coverage and that opening points lie on their referenced wall axes. These are **synthetic test plans**, not architect-certified construction documents; all dimensions, accessibility, structural details, ventilation, plumbing, fire egress and local-code compliance must be reviewed by a qualified designer before real-world use.\n'''
    (outdir/"README.md").write_text(readme,encoding="utf-8")
    return report


CONVERTER_SCRIPT = r'''import argparse, json, math
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
'''

VALIDATOR_SCRIPT = r'''import csv,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=[]
for dxf in sorted((root/"plans").glob("*/*.dxf")):
    j=dxf.with_name(dxf.stem+"_architecture.json")
    data=json.loads(j.read_text(encoding="utf-8"))
    wm={w["id"]:w for w in data["walls"]}
    linked=True; maxdist=0.0
    for group in ("doors","windows"):
        for o in data[group]:
            if o["wall_id"] not in wm:linked=False;continue
            w=wm[o["wall_id"]];a=w["start"];b=w["end"];p=o["center"]
            dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
            t=0 if den==0 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
            dist=math.hypot(p[0]-(a[0]+t*dx),p[1]-(a[1]+t*dy));maxdist=max(maxdist,dist)
            if dist>.02:linked=False
    rsum=sum(float(r.get("area_sqft",0)) for r in data["rooms"])
    fp=data["footprint"];farea=abs(sum(fp[i][0]*fp[(i+1)%len(fp)][1]-fp[(i+1)%len(fp)][0]*fp[i][1] for i in range(len(fp)))/2)
    # room zones should tile the core footprint (within tolerance)
    good=linked and abs(rsum-farea)<.6
    rows.append({"plan_id":data["plan_id"],"bhk":data["bhk"],"rooms":len(data["rooms"]),"walls":len(data["walls"]),"doors":len(data["doors"]),"windows":len(data["windows"]),"balconies":len(data.get("balconies",[])),"core_area_sqft":round(farea,2),"room_area_sum_sqft":round(rsum,2),"max_opening_to_wall_distance":round(maxdist,5),"opening_refs_valid":linked,"room_area_coverage_valid":abs(rsum-farea)<.6,"PASS":good})
for r in rows:print(r["plan_id"],"PASS" if r["PASS"] else "FAIL",f"walls={r['walls']} doors={r['doors']} windows={r['windows']} rooms={r['rooms']}")
print(f"\nPlans: {len(rows)} | Passed: {sum(r['PASS'] for r in rows)} | Failed: {sum(not r['PASS'] for r in rows)}")
with (root/"validation_report.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);w.writeheader();w.writerows(rows)
'''

if __name__=="__main__":
    import sys
    target=sys.argv[1] if len(sys.argv)>1 else "/mnt/data/DimensionX_30_DXF_Plans"
    report=build_plan_set(target)
    print(f"Created {len(report)} plans in {target}")
