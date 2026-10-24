"""
prepare_dataset.py — RaahIQ dataset ki poori tayyari, EK hi file, EK hi command.

    python prepare_dataset.py

Ye 4 steps khud chalata hai:
  STEP 1  Geocode  — Photon se saare stops ke coordinates (no API key, resume-supported)
  STEP 2  Auto-fix — bare duplicate groups (geocoder fallbacks) ko route-context se theek karna
  STEP 3  Hand-fix — 25 hand-checked corrections jo neeche FIXES mein hain
  STEP 4  Validate — coverage / duplicates / bounds ki final report (validation_report.txt)

Baaki helper scripts (photon_geocode.py, fix_fallbacks.py, apply_fixes.py,
validate_dataset.py) ki ab zaroorat nahi — ye file un sab ka kaam karti hai.
"""
import json
import math
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict

# ---------------------------------------------------------------- config
BOUNDS = (66.60, 24.70, 67.50, 25.20)        # min_lon, min_lat, max_lon, max_lat
CENTER = (67.0011, 24.8607)                  # Karachi (lon, lat)
DELAY = 1.1                                  # free services ke saath politeness
UA = "RaahIQ-Dataset/1.0 (https://github.com/Ubaidrees/raahiq)"
ROUTES_FILE = "bus_routes.json"
COORDS_FILE = "stop_coordinates.json"
REPORT_FILE = "validation_report.txt"
PHOTON_URL = "https://photon.komoot.io/api/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# ------------------------------------------------- STEP 3: hand-checked fixes
FIXES = {
    "Bilal Chorangi": [67.146196, 24.844202],
    "Brooks Chorangi": [67.099985, 24.833862],
    "Veta Chorangi": [67.133741, 24.841284],
    "Singer Chorangi": [67.15963, 24.847085],
    "Murtaza Chorangi": [67.118606, 24.83148],
    "4K Chorangi": [67.064436, 25.00646],
    "Punjab Chorangi": [67.040142, 24.831885],
    "Jail Chorangi": [67.061079, 24.890792],
    "Johar Chorangi": [67.139922, 24.920771],
    "Kamran Chorangi": [67.139273, 24.923061],
    "Khaibar Chowk": [67.018519, 24.865553],
    "Pareshan Chowk": [67.018519, 24.865553],
    "Tori Chowk": [67.018519, 24.865553],
    "Qayoomabad": [67.080696, 24.823074],
    "Metrowel": [66.994253, 24.920423],
    "Reegal": [67.024266, 24.860637],
    "Chakiwarah": [66.999863, 24.864025],
    "Dental College": [67.060186, 24.94265],
    "Ghareebabad": [67.041517, 24.908679],
    "Bhens Colony": [67.2629334, 24.8240238],
    "Bhens Colony Mor": [67.2629334, 24.8240238],
    "Guromandar": [67.0083172, 24.8543031],
    "Meranaka": [67.0912547, 24.8728956],
    "Saoodabad": [67.2033252, 24.9010045],
    "Sherin Jinnah": [66.9957814, 24.8173568],
}
# Ab bhi unresolved (map pe pin kar lo ya limitations mein disclose karo):
#   Chamra Chorangi, Hospital Chorangi, Indus Chorangi,
#   Mosamiyat / Mausamiyat Chorangi / Mosmiat, Khaibarabad,
#   Pakhtunabad, Khudad Colony, Orangi Zahoor Chowk 11½


# ---------------------------------------------------------------- helpers
def in_bbox(c):
    return BOUNDS[0] <= c[0] <= BOUNDS[2] and BOUNDS[1] <= c[1] <= BOUNDS[3]


def hav_km(a, b):
    r = 6371.0
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp = math.radians(b[1] - a[1])
    dl = math.radians(b[0] - a[0])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def save(coords):
    with open(COORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(coords, f, ensure_ascii=False, indent=2)


def photon_candidates(name, limit):
    q = urllib.parse.urlencode({
        "q": f"{name}, Karachi, Pakistan", "limit": limit,
        "lat": CENTER[1], "lon": CENTER[0],
        "bbox": f"{BOUNDS[0]},{BOUNDS[1]},{BOUNDS[2]},{BOUNDS[3]}"})
    try:
        data = get_json(PHOTON_URL + "?" + q)
        return [f["geometry"]["coordinates"] for f in data.get("features", [])]
    except Exception as e:
        print(f"    photon error for '{name}': {e}")
        return []


def nominatim_candidates(name, limit=5):
    q = urllib.parse.urlencode({
        "q": f"{name}, Karachi, Pakistan", "format": "jsonv2", "limit": limit,
        "viewbox": f"{BOUNDS[0]},{BOUNDS[3]},{BOUNDS[2]},{BOUNDS[1]}",
        "bounded": 1})
    try:
        data = get_json(NOMINATIM_URL + "?" + q)
        return [[float(d["lon"]), float(d["lat"])] for d in data]
    except Exception as e:
        print(f"    nominatim error for '{name}': {e}")
        return []


# ---------------------------------------------------------------- STEP 1
def step1_geocode(routes, coords):
    print("\n=== STEP 1: Geocoding (Photon, resume) ===")
    unique = sorted({s for r in routes for s in r["stops"]})
    remaining = [s for s in unique if s not in coords]
    print(f"{len(unique)} unique stops, {len(coords)} already done, "
          f"{len(remaining)} remaining (~{round(len(remaining) * DELAY / 60, 1)} min)")
    for i, stop in enumerate(remaining, 1):
        cands = [c for c in photon_candidates(stop, 5) if in_bbox(c)]
        if cands:
            coords[stop] = cands[0]
            print(f"[{i}/{len(remaining)}] OK      : {stop} -> {cands[0]}")
        else:
            print(f"[{i}/{len(remaining)}] FAILED  : {stop}")
        save(coords)
        time.sleep(DELAY)
    return coords


# ---------------------------------------------------------------- STEP 2
def step2_fix_fallbacks(routes, coords):
    print("\n=== STEP 2: Route-context fallback fix ===")
    by_coord = defaultdict(list)
    for n, c in coords.items():
        by_coord[(round(c[0], 6), round(c[1], 6))].append(n)
    bad = set()
    for names in by_coord.values():
        if len(names) >= 4:
            bad.update(names)
    print(f"Flagged {len(bad)} stops in duplicate groups of 4+.")
    if not bad:
        return coords

    refs = defaultdict(set)
    for r in routes:
        for s in r["stops"]:
            if s in bad:
                for t in r["stops"]:
                    if t not in bad and t in coords:
                        refs[s].add(tuple(coords[t]))

    fixed = 0
    for stop in sorted(bad):
        ref_pts = [list(p) for p in refs.get(stop, [])]
        cur = coords.get(stop)
        cands = [c for c in photon_candidates(stop, 10) if in_bbox(c)]
        time.sleep(DELAY)
        if not cands:
            cands = [c for c in nominatim_candidates(stop) if in_bbox(c)]
            time.sleep(DELAY)
        uniq = []
        for c in cands:
            if cur and hav_km(c, cur) < 0.05:
                continue
            if all(hav_km(c, u) > 0.05 for u in uniq):
                uniq.append(c)
        if not uniq or not ref_pts:
            print(f"  ?? {stop}: no usable candidates — left unchanged")
            continue
        best = min(uniq, key=lambda c: min(hav_km(c, rp) for rp in ref_pts))
        d = min(hav_km(best, rp) for rp in ref_pts)
        if d <= 20:
            coords[stop] = best
            fixed += 1
            print(f"  OK {stop}: -> {best} (route neighbour {d:.1f} km)")
        else:
            print(f"  ?? {stop}: best candidate {d:.1f} km away — left unchanged")
        save(coords)
    print(f"Auto-fixed {fixed}/{len(bad)}.")
    return coords


# ---------------------------------------------------------------- STEP 3
def step3_hand_fixes(coords):
    print("\n=== STEP 3: Hand-checked fixes ===")
    changed = 0
    for name, new in FIXES.items():
        if coords.get(name) != new:
            coords[name] = new
            changed += 1
            print(f"  {name} -> {new}")
    save(coords)
    print(f"Applied {changed} hand fixes.")
    return coords


# ---------------------------------------------------------------- STEP 4
def step4_validate(routes, coords):
    print("\n=== STEP 4: Validation ===")
    unique = sorted({s for r in routes for s in r["stops"]})
    missing = [s for s in unique if s not in coords]
    by_coord = defaultdict(list)
    for n, c in coords.items():
        by_coord[(round(c[0], 6), round(c[1], 6))].append(n)
    dup_groups = {k: v for k, v in by_coord.items() if len(v) > 1}
    outside = [n for n, c in coords.items() if not in_bbox(c)]

    lines = ["RaahIQ dataset validation report", "=" * 40,
             f"Routes                         : {len(routes)}",
             f"Unique stop names              : {len(unique)}",
             f"Stops with coordinates         : {len(coords)}",
             f"Coverage                       : {len(coords) / len(unique) * 100:.1f}%",
             "", f"[1] Missing coordinates: {len(missing)}"]
    lines += [f"    - {s}" for s in missing]
    lines.append(f"\n[2] Duplicate-coordinate groups: {len(dup_groups)}")
    for (lon, lat), names in sorted(dup_groups.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"    [{lon}, {lat}] shared by {len(names)} stops:")
        lines += [f"        - {n}" for n in names]
    lines.append(f"\n[3] Coordinates outside Karachi bbox: {len(outside)}")
    lines += [f"    - {s} -> {coords[s]}" for s in outside]
    big = [v for v in dup_groups.values() if len(v) >= 4]
    lines.append("")
    lines.append("READY TO PUBLISH ✔" if not missing and not big and not outside
                 else "Note: choti variant-groups (2-3) theek hain; "
                      "bare groups (>=4) ya missing stops review karo.")
    report = "\n".join(lines)
    print(report)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to {REPORT_FILE}")


def main():
    with open(ROUTES_FILE, encoding="utf-8") as f:
        routes = json.load(f)["routes"]
    coords = {}
    if os.path.exists(COORDS_FILE):
        with open(COORDS_FILE, encoding="utf-8") as f:
            coords = json.load(f)
    coords = step1_geocode(routes, coords)
    coords = step2_fix_fallbacks(routes, coords)
    coords = step3_hand_fixes(coords)
    step4_validate(routes, coords)
    print("\nDone. Ab README numbers theek karo, commit karo, phir Zenodo upload.")


if __name__ == "__main__":
    main()
