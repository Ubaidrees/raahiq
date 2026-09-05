import streamlit as st
import openrouteservice
from openrouteservice.exceptions import ApiError
from difflib import SequenceMatcher

# Karachi's approximate bounding box — used to keep geocoding results local
# instead of accidentally matching a same-named place elsewhere in Pakistan/world.
KARACHI_BOUNDS = {"min_lon": 66.60, "max_lon": 67.50, "min_lat": 24.70, "max_lat": 25.20}
KARACHI_FOCUS = [67.0011, 24.8607]  # roughly central Karachi, used to bias ranking

def get_client(api_key):
    return openrouteservice.Client(key=api_key)

def _within_karachi(coords):
    lon, lat = coords[0], coords[1]
    return (KARACHI_BOUNDS["min_lon"] <= lon <= KARACHI_BOUNDS["max_lon"] and
            KARACHI_BOUNDS["min_lat"] <= lat <= KARACHI_BOUNDS["max_lat"])

@st.cache_data
def get_coordinates(place_name, api_key):
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
        if getattr(e, "status", None) == 429:
            raise  # let the caller show a "server busy" message instead of "no internet"
        print(f"Coordinates Error: {e}")
        return None
    except Exception as e:
        print(f"Coordinates Error: {e}")
        return None

@st.cache_data
def get_all_routes(start_coords, end_coords, api_key):
    client = get_client(api_key)
    routes = {}

    try:
        r1 = client.directions([start_coords, end_coords],
                               profile='driving-car',
                               format='geojson',
                               preference='fastest')
        s1 = r1['features'][0]['properties']['summary']
        routes['fastest'] = {'distance': round(s1['distance']/1000, 1), 'duration': round(s1['duration']/60)}
    except Exception as e:
        print(f"Route 1 Error: {e}")
        routes['fastest'] = {'distance': 10, 'duration': 30}

    try:
        r2 = client.directions([start_coords, end_coords],
                               profile='driving-car',
                               format='geojson',
                               preference='shortest')
        s2 = r2['features'][0]['properties']['summary']
        routes['cheapest'] = {'distance': round(s2['distance']/1000, 1), 'duration': round(s2['duration']/60)}
    except Exception as e:
        print(f"Route 2 Error: {e}")
        routes['cheapest'] = {'distance': 12, 'duration': 45}

    try:
        r3 = client.directions([start_coords, end_coords],
                               profile='cycling-regular',
                               format='geojson')
        s3 = r3['features'][0]['properties']['summary']
        routes['balanced'] = {'distance': round(s3['distance']/1000, 1), 'duration': round(s3['duration']/60)}
    except Exception as e:
        print(f"Route 3 Error: {e}")
        routes['balanced'] = {'distance': 11, 'duration': 40}

    return routes

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