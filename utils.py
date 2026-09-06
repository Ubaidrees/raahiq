import streamlit as st
import openrouteservice
from openrouteservice.exceptions import ApiError
from difflib import SequenceMatcher

# Karachi's approximate bounding box — used to keep geocoding results local
# instead of accidentally matching a same-named place elsewhere in Pakistan/world.
KARACHI_BOUNDS = {"min_lon": 66.60, "max_lon": 67.50, "min_lat": 24.70, "max_lat": 25.20}
KARACHI_FOCUS = [67.0011, 24.8607]  # roughly central Karachi, used to bias ranking

def is_quota_or_rate_limit_error(e):
    """
    True if this ORS ApiError indicates the request quota/rate limit was hit —
    covers both 429 (too many requests per minute) and 403 with 'Quota exceeded'
    (daily/monthly free-tier quota used up). Both mean "try again later", not
    "no internet".
    """
    return getattr(e, "status", None) in (403, 429)


def get_client(api_key):
    return openrouteservice.Client(key=api_key)

def _within_karachi(coords):
    lon, lat = coords[0], coords[1]
    return (KARACHI_BOUNDS["min_lon"] <= lon <= KARACHI_BOUNDS["max_lon"] and
            KARACHI_BOUNDS["min_lat"] <= lat <= KARACHI_BOUNDS["max_lat"])

@st.cache_data
def get_coordinates(place_name, api_key):
    place_name = " ".join(place_name.split()).lower()  # normalize for better cache hit rate across users
    try:
        client = get_client(api_key)
        result = client.pelias_search(
            text=place_name + ", Karachi, Pakistan",
            focus_point=KARACHI_FOCUS,
            rect_min_x=KARACHI_BOUNDS["min_lon"],
            rect_min_y=KARACHI_BOUNDS["min_lat"],
            rect_max_x=KARACHI_BOUNDS["max_lon"],
            rect_max_y=KARACHI_BOUNDS["max_lat"],
            country="PAK",
        )
        coords = result['features'][0]['geometry']['coordinates']
        if not _within_karachi(coords):
            print(f"Coordinates Error: '{place_name}' resolved outside Karachi ({coords}), rejecting")
            return None
        return coords
    except ApiError as e:
        if is_quota_or_rate_limit_error(e):
            raise  # let the caller show a "server busy" message instead of "no internet"
        print(f"Coordinates Error: {e}")
        return None
    except Exception as e:
        print(f"Coordinates Error: {e}")
        return None

@st.cache_data
def get_fastest_route(start_coords, end_coords, api_key):
    """
    Fetch only the fastest driving route — this is the only route type the UI
    actually displays. (Previously this fetched fastest/cheapest/balanced —
    3 ORS calls per search — even though 2 of those were never shown, which
    wasted a third of our free-tier quota on every single search.)
    """
    client = get_client(api_key)
    try:
        r = client.directions([start_coords, end_coords],
                               profile='driving-car',
                               format='geojson',
                               preference='fastest')
        s = r['features'][0]['properties']['summary']
        return {'distance': round(s['distance'] / 1000, 1), 'duration': round(s['duration'] / 60)}
    except ApiError as e:
        if is_quota_or_rate_limit_error(e):
            raise
        print(f"Fastest route error: {e}")
        return None
    except Exception as e:
        print(f"Fastest route error: {e}")
        return None

def estimate_cost(mode, distance):
    if mode == "Rickshaw":
        return max(80, round(distance * 25))
    elif mode == "Bus":
        return 30
    elif mode == "Bike Taxi":
        return max(60, round(distance * 15))
    return 0

def get_maps_link(start, end, mode="driving"):
    start_enc = start.replace(" ", "+") + ",+Karachi"
    end_enc = end.replace(" ", "+") + ",+Karachi"
    return f"https://www.google.com/maps/dir/?api=1&origin={start_enc}&destination={end_enc}&travelmode={mode}"

def match_area(location_text, areas_list):
    """
    Fuzzy-match a free-text location (e.g. what the user typed in Starting Location)
    to the closest known area in the traffic model's area list (e.g. 'Saddar', 'Gulshan').
    Falls back to the first area in the list if nothing matches reasonably well,
    since the ML model always needs *some* area value to predict on.
    """
    location_lower = location_text.lower().strip()
    best_area, best_score = areas_list[0], 0.0

    for area in areas_list:
        area_lower = area.lower()
        if area_lower in location_lower or location_lower in area_lower:
            return area  # strong substring match, good enough
        score = SequenceMatcher(None, location_lower, area_lower).ratio()
        if score > best_score:
            best_area, best_score = area, score

    return best_area