"""
One-time script to geocode every unique bus stop name in bus_routes.json
and cache the results in stop_coordinates.json.

WHY THIS EXISTS:
Text-only matching (e.g. "Star Gate" vs "Colony Gate") sometimes misses real
bus routes when the user's wording doesn't exactly match a stop name in our
data, even though the actual stops are physically very close. Once every
stop has a known GPS location, the app can also match routes by *proximity*
("is there a stop within ~500m of what the user typed?"), which catches
these cases without needing exact name matches.

HOW TO RUN:
    python build_stop_coordinates.py

- Needs ORS_API_KEY in your .env file (same key the main app uses).
- Takes ~30-45 minutes for ~1750 stops due to free-tier rate limits
  (script waits ~1.6 seconds between requests on purpose — don't reduce this,
  it's what keeps you under OpenRouteService's free-tier limit).
- SAFE TO INTERRUPT: progress is saved after every single stop. If you stop
  the script (Ctrl+C) or your internet drops, just run it again — it will
  skip stops already geocoded and continue from where it left off.
- Run this once locally, then commit the resulting stop_coordinates.json
  to your repo alongside bus_routes.json. The deployed app only READS this
  file — it never re-geocodes stops itself.
"""
import json
import time
import os
from dotenv import load_dotenv
import openrouteservice
from openrouteservice.exceptions import ApiError

load_dotenv()
API_KEY = os.getenv("ORS_API_KEY")

KARACHI_BOUNDS = {"min_lon": 66.60, "max_lon": 67.50, "min_lat": 24.70, "max_lat": 25.20}
KARACHI_FOCUS = [67.0011, 24.8607]

ROUTES_FILE = "bus_routes.json"
OUTPUT_FILE = "stop_coordinates.json"
DELAY_SECONDS = 1.6  # keeps us comfortably under ORS free-tier ~40 requests/min


def within_karachi(coords):
    lon, lat = coords[0], coords[1]
    return (KARACHI_BOUNDS["min_lon"] <= lon <= KARACHI_BOUNDS["max_lon"] and
            KARACHI_BOUNDS["min_lat"] <= lat <= KARACHI_BOUNDS["max_lat"])


def geocode(client, stop_name):
    try:
        result = client.pelias_search(
            text=stop_name + ", Karachi, Pakistan",
            focus_point=KARACHI_FOCUS,
            rect_min_x=KARACHI_BOUNDS["min_lon"],
            rect_min_y=KARACHI_BOUNDS["min_lat"],
            rect_max_x=KARACHI_BOUNDS["max_lon"],
            rect_max_y=KARACHI_BOUNDS["max_lat"],
            country="PAK",
        )
        coords = result["features"][0]["geometry"]["coordinates"]
        if not within_karachi(coords):
            print(f"  Skipped (resolved outside Karachi): {stop_name}")
            return None
        return coords
    except ApiError as e:
        print(f"  ApiError for '{stop_name}': {e}")
        return None
    except Exception as e:
        print(f"  Error for '{stop_name}': {e}")
        return None


def main():
    if not API_KEY:
        print("ORS_API_KEY not found in .env — aborting.")
        return

    with open(ROUTES_FILE, encoding="utf-8") as f:
        data = json.load(f)

    unique_stops = sorted({s for r in data["routes"] for s in r["stops"]})
    print(f"Found {len(unique_stops)} unique stop names across all routes.")

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            results = json.load(f)
        print(f"Resuming — {len(results)} stops already geocoded previously.")
    else:
        results = {}

    client = openrouteservice.Client(key=API_KEY)
    remaining = [s for s in unique_stops if s not in results]
    print(f"{len(remaining)} stops left to geocode. Estimated time: "
          f"~{round(len(remaining) * DELAY_SECONDS / 60, 1)} minutes.\n")

    for i, stop in enumerate(remaining, 1):
        coords = geocode(client, stop)
        if coords:
            results[stop] = coords
            print(f"[{i}/{len(remaining)}] OK      : {stop} -> {coords}")
        else:
            print(f"[{i}/{len(remaining)}] FAILED  : {stop}")

        # Save after every stop so interrupting the script never loses progress
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(DELAY_SECONDS)

    print(f"\nDone. Geocoded {len(results)}/{len(unique_stops)} stops.")
    print(f"Saved to {OUTPUT_FILE} — commit this file to your repo.")


if __name__ == "__main__":
    main()