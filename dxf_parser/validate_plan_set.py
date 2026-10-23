import csv,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=[]
for dxf in sorted((root/"plans").rglob("*.dxf")):
    rel=dxf.relative_to(root/"plans")
    j=root/"generated_json"/rel.parent/(dxf.stem+"_architecture.json")
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
(root/"generated_json").mkdir(parents=True,exist_ok=True)
with (root/"generated_json"/"validation_report.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);w.writeheader();w.writerows(rows)
