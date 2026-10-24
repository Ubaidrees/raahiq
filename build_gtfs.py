"""
Convert RaahIQ's bus_routes.json + stop_coordinates.json into a GTFS static feed
(the international standard format for public-transit data).

USAGE (run in the folder containing both JSON files):
    python build_gtfs.py

OUTPUT:
    gtfs/                       -> the individual GTFS .txt files
    raahiq_karachi_gtfs.zip     -> the zip you publish (files are at the zip root, as GTFS requires)

HONEST LIMITATIONS (also documented in DATASET_CARD.md):
  * The source guide has NO timetable data. stop_times.txt therefore contains
    stop ORDER (stop_sequence) but blank arrival/departure times. Official
    GTFS validators will warn about this; that is expected and accurate for
    unscheduled / informal transit, and is better than inventing fake times.
  * Each route lists stops in ONE direction only (origin -> terminus), so one
    trip (direction_id=0) is generated per route. Return direction is not in
    the source data.
  * calendar.txt marks service as every day because the source says nothing
    about operating days. This is an ASSUMPTION, labelled as such.
  * Stops that could not be geocoded are omitted from the feed and reported.
"""
import csv
import json
import os
import re
import sys
import zipfile
from datetime import date

ROUTES_FILE = "bus_routes.json"
COORDS_FILE = "stop_coordinates.json"
OUT_DIR = "gtfs"
ZIP_NAME = "raahiq_karachi_gtfs.zip"

FEED_VERSION = "1.0"
FEED_START = "20260101"   # placeholder validity window - edit if you wish
FEED_END = "20271231"
SERVICE_ID = "DAILY_ASSUMED"

# Route colours (hex without '#'), matching the RaahIQ app's category palette
CATEGORY_COLORS = {
    "Mini Bus": "12857A",
    "Coach": "6B4FA0",
    "Other Bus": "D4901F",
    "Red Bus": "C1443D",
    "EV Bus": "2E9B63",
    "BRT": "2E5FA3",
}


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def write_csv(name, header, rows):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    for p in (ROUTES_FILE, COORDS_FILE):
        if not os.path.exists(p):
            sys.exit(f"Missing {p} - run this script inside the folder that contains it.")

    with open(ROUTES_FILE, encoding="utf-8") as f:
        routes = json.load(f)["routes"]
    with open(COORDS_FILE, encoding="utf-8") as f:
        coords = json.load(f)

    os.makedirs(OUT_DIR, exist_ok=True)

    # ---- stops.txt : one row per unique stop that has coordinates ----
    all_names = sorted({s for r in routes for s in r["stops"]})
    stop_id = {}
    stops_rows = []
    missing = []
    for i, name in enumerate(all_names, 1):
        c = coords.get(name)
        if not c:
            missing.append(name)
            continue
        sid = f"S{i:04d}"
        stop_id[name] = sid
        lon, lat = c
        stops_rows.append([sid, name, f"{lat:.6f}", f"{lon:.6f}"])
    write_csv("stops.txt", ["stop_id", "stop_name", "stop_lat", "stop_lon"], stops_rows)

    # ---- agency.txt ----
    write_csv(
        "agency.txt",
        ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"],
        [["KHI_MIXED", "Karachi public transit (mixed operators)",
          "https://raahiq.streamlit.app", "Asia/Karachi", "en"]],
    )

    # ---- routes.txt / trips.txt / stop_times.txt ----
    routes_rows, trips_rows, st_rows = [], [], []
    skipped_routes = []
    for r in routes:
        rid = slug(r["id"])
        usable = [s for s in r["stops"] if s in stop_id]
        if len(usable) < 2:
            skipped_routes.append(r["id"])
            continue
        first, last = usable[0], usable[-1]
        routes_rows.append([
            rid, "KHI_MIXED", r["id"], f"{first} - {last}", r["category"],
            3, CATEGORY_COLORS.get(r["category"], "12857A"), "FFFFFF",
        ])
        trip_id = f"{rid}_0"
        trips_rows.append([rid, SERVICE_ID, trip_id, last, 0])
        for seq, s in enumerate(usable, 1):
            # blank arrival/departure = unknown times; timepoint 0 = approximate
            st_rows.append([trip_id, "", "", stop_id[s], seq, 0])

    write_csv("routes.txt",
              ["route_id", "agency_id", "route_short_name", "route_long_name",
               "route_desc", "route_type", "route_color", "route_text_color"],
              routes_rows)
    write_csv("trips.txt",
              ["route_id", "service_id", "trip_id", "trip_headsign", "direction_id"],
              trips_rows)
    write_csv("stop_times.txt",
              ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "timepoint"],
              st_rows)

    # ---- calendar.txt (ASSUMPTION: daily service) ----
    write_csv("calendar.txt",
              ["service_id", "monday", "tuesday", "wednesday", "thursday",
               "friday", "saturday", "sunday", "start_date", "end_date"],
              [[SERVICE_ID, 1, 1, 1, 1, 1, 1, 1, FEED_START, FEED_END]])

    # ---- feed_info.txt ----
    write_csv("feed_info.txt",
              ["feed_publisher_name", "feed_publisher_url", "feed_lang",
               "feed_start_date", "feed_end_date", "feed_version"],
              [["RaahIQ (M. Ubaid Idrees)", "https://raahiq.streamlit.app", "en",
                FEED_START, FEED_END, f"{FEED_VERSION}-{date.today().isoformat()}"]])

    # ---- zip (files must sit at the zip root) ----
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(OUT_DIR)):
            z.write(os.path.join(OUT_DIR, fn), arcname=fn)

    print(f"Routes written : {len(routes_rows)} of {len(routes)}")
    print(f"Stops written  : {len(stops_rows)} of {len(all_names)}")
    print(f"stop_times rows: {len(st_rows)}")
    if missing:
        print(f"\n{len(missing)} stops had NO coordinates and were left out:")
        for m in missing:
            print("   -", m)
    if skipped_routes:
        print(f"\nRoutes skipped (<2 usable stops): {skipped_routes}")
    print(f"\nDone -> {ZIP_NAME}")


if __name__ == "__main__":
    main()