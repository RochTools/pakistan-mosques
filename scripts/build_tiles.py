#!/usr/bin/env python3
"""OSM (geojsonseq) -> مسجدوں کی چھوٹی tile فائلیں۔

ان پٹ : osmium export کی geojsonseq فائل (صرف مسجد والی)
آؤٹ پٹ: data/tiles/<y>_<x>.json  — ہر فائل [[lat, lon, "نام"], ...]
         data/index.json        — {size, bbox, tiles:[...], count, built}
Tile سائز 0.2 ڈگری (~22 کلومیٹر): ایپ صرف اپنے آس پاس کی 1-4 tile اٹھاتی ہے۔
"""
import json, math, os, sys, time, collections

SIZE = 0.2
src, out = sys.argv[1], sys.argv[2]
tiles_dir = os.path.join(out, "tiles")
os.makedirs(tiles_dir, exist_ok=True)
for f in os.listdir(tiles_dir):
    os.remove(os.path.join(tiles_dir, f))

def center(geom):
    t = geom.get("type")
    c = geom.get("coordinates")
    if t == "Point":
        return c[1], c[0]
    pts = []
    def walk(x):
        if x and isinstance(x[0], (int, float)):
            pts.append(x)
        else:
            for y in x:
                walk(y)
    walk(c)
    if not pts:
        return None
    lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
    return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2

def is_mosque(tags):
    rel = (tags.get("religion") or "").lower()
    if tags.get("amenity") == "mosque" or tags.get("building") == "mosque":
        return True
    if tags.get("amenity") == "place_of_worship":
        return rel in ("muslim", "islam") or (not rel and tags.get("denomination") in ("sunni", "shia", "ahmadiyya"))
    return False

seen = set()
buckets = collections.defaultdict(list)
total = 0
with open(src, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip().lstrip("\x1e")
        if not line:
            continue
        try:
            ft = json.loads(line)
        except Exception:
            continue
        tags = ft.get("properties") or {}
        if not is_mosque(tags):
            continue
        ctr = center(ft.get("geometry") or {})
        if not ctr:
            continue
        lat, lon = ctr
        key = (round(lat, 4), round(lon, 4))   # ~11m — node/way کی نقل ختم
        if key in seen:
            continue
        seen.add(key)
        name = tags.get("name") or tags.get("name:ur") or tags.get("name:en") or tags.get("alt_name") or ""
        name = " ".join(name.split())[:80]
        ty, tx = math.floor(lat / SIZE), math.floor(lon / SIZE)
        buckets[(ty, tx)].append([round(lat, 5), round(lon, 5), name])
        total += 1

names = []
for (ty, tx), items in buckets.items():
    fn = f"{ty}_{tx}.json"
    with open(os.path.join(tiles_dir, fn), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))
    names.append(fn[:-5])

lats = [k[0] for k in buckets]; lons = [k[1] for k in buckets]
index = {
    "size": SIZE,
    "count": total,
    "tiles": sorted(names),
    "bbox": [min(lats) * SIZE, min(lons) * SIZE, (max(lats) + 1) * SIZE, (max(lons) + 1) * SIZE] if buckets else None,
    "built": time.strftime("%Y-%m-%d"),
}
with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
print(f"mosques={total} tiles={len(names)}")
