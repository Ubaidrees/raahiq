import json
from difflib import SequenceMatcher
import streamlit as st
import openrouteservice
from openrouteservice.exceptions import ApiError
from utils import is_quota_or_rate_limit_error
import folium

BUS_SLOWDOWN_FACTOR = 1.35  # buses are slower than cars due to frequent stops/boarding
_ROUTES_CACHE = None


# ─────────────────────────── Loading & fuzzy matching ───────────────────────────

def load_bus_routes(path="bus_routes.json"):
    """Load and cache bus routes from JSON file."""
    global _ROUTES_CACHE
    if _ROUTES_CACHE is None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _ROUTES_CACHE = data["routes"]
    return _ROUTES_CACHE


def _similarity(a, b):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _tokenize(s):
    """Split into lowercase whole-word tokens (splitting on spaces AND hyphens)."""
    import re
    return set(t for t in re.split(r"[\s\-]+", s.lower().strip()) if t)


_GENERIC_SINGLE_WORDS = {
    "tower", "chorangi", "chowk", "mor", "road", "bridge", "colony",
    "market", "town", "stop", "square", "park", "hospital", "school",
    "hotel", "goth", "society", "complex", "station", "gate", "plaza",
}

_CONFUSABLE_WORDS = {"korangi", "orangi", "chorangi"}


def _find_best_stop_match(query, stops, threshold=0.55):
    """
    Find the stop in `stops` that best matches `query`. Returns (stop_name, index, score).
    """
    query_lower = query.lower().strip()
    query_words = _tokenize(query)
    is_generic_query = query_lower in _GENERIC_SINGLE_WORDS
    best_stop, best_idx, best_score = None, None, 0.0

    for idx, stop in enumerate(stops):
        stop_lower = stop.lower()
        stop_words = _tokenize(stop)

        if query_lower == stop_lower:
            return stop, idx, 1.0

        if is_generic_query:
            continue

        shared_words = query_words & stop_words
        ratio = _similarity(query, stop)
        is_subset_match = query_words and stop_words and (query_words <= stop_words or stop_words <= query_words)

        if is_subset_match:
            # One side's words are fully contained in the other's (e.g. "Jama"
            # inside "Jama Cloth", "Gulshan" inside "Gulshan Chorangi") —
            # strong, safe evidence of relatedness.
            score = max(0.9, ratio)
        elif shared_words:
            # Share ONE word, but each side also has a different word that
            # doesn't overlap at all — that differing word is often exactly
            # what makes two real places different (e.g. "Malir Halt" vs
            # "Malir Cantt" — same broad area, genuinely different specific
            # places, 0.76 similarity). Require a high overall similarity,
            # high enough to admit genuine spelling variants (e.g. "Ayesha
            # Manzil"/"Aisha Manzil" = 0.88) while rejecting same-area
            # confusions like the Malir case above. A broad-area name that
            # only loosely matches a specific landmark (e.g. "Gulshan-e-Iqbal"
            # vs "Gulshan Chorangi") is instead caught by proximity matching
            # (real GPS distance) when online — a safer signal than guessing
            # from partial word overlap.
            score = ratio if ratio >= 0.80 else 0.0
        else:
            query_has_confusable = bool(query_words & _CONFUSABLE_WORDS)
            stop_has_confusable = bool(stop_words & _CONFUSABLE_WORDS)
            if query_has_confusable or stop_has_confusable:
                score = 0.0
            else:
                score = ratio if ratio >= 0.90 else 0.0

        if score > best_score:
            best_stop, best_idx, best_score = stop, idx, score

    if best_score >= threshold:
        return best_stop, best_idx, best_score
    return None, None, 0.0


def find_local_coords(query, stop_coords_path="stop_coordinates.json"):
    stop_coords = load_stop_coordinates(stop_coords_path)
    if not stop_coords:
        return None

    all_stop_names = list(stop_coords.keys())
    matched_name, _, score = _find_best_stop_match(query, all_stop_names, threshold=0.75)
    if matched_name:
        return stop_coords[matched_name]
    return None


def find_matching_routes(start_location, end_location, routes_path="bus_routes.json", top_n=15):
    routes = load_bus_routes(routes_path)
    results = []

    for route in routes:
        stops = route["stops"]
        start_stop, start_idx, start_score = _find_best_stop_match(start_location, stops)
        end_stop, end_idx, end_score = _find_best_stop_match(end_location, stops)

        if start_stop is None or end_stop is None or start_idx == end_idx:
            continue

        results.append({
            "route_id": route["id"],
            "category": route["category"],
            "start_stop": start_stop,
            "end_stop": end_stop,
            "direction_ok": start_idx < end_idx,
            "stops_between": abs(end_idx - start_idx),
            "confidence": round((start_score + end_score) / 2, 2),
            "start_score": round(start_score, 2),
            "end_score": round(end_score, 2),
            "match_type": "name",
        })

    results.sort(key=lambda r: (-r["confidence"], not r["direction_ok"], r["stops_between"]))
    return results[:top_n]


_STOP_COORDS_CACHE = None


def load_stop_coordinates(path="stop_coordinates.json"):
    global _STOP_COORDS_CACHE
    if _STOP_COORDS_CACHE is None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                _STOP_COORDS_CACHE = json.load(f)
        except FileNotFoundError:
            _STOP_COORDS_CACHE = {}
    return _STOP_COORDS_CACHE


def _haversine_km(coord1, coord2):
    from math import radians, sin, cos, sqrt, atan2
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def find_proximity_routes(start_coords, end_coords, routes_path="bus_routes.json",
                           stop_coords_path="stop_coordinates.json", threshold_km=0.5, top_n=15):
    stop_coords = load_stop_coordinates(stop_coords_path)
    if not stop_coords:
        return []

    routes = load_bus_routes(routes_path)
    results = []

    for route in routes:
        stops = route["stops"]
        best_start = None
        best_end = None

        for idx, stop in enumerate(stops):
            coords = stop_coords.get(stop)
            if not coords:
                continue
            d_start = _haversine_km(start_coords, coords)
            if d_start <= threshold_km and (best_start is None or d_start < best_start[2]):
                best_start = (idx, stop, d_start)
            d_end = _haversine_km(end_coords, coords)
            if d_end <= threshold_km and (best_end is None or d_end < best_end[2]):
                best_end = (idx, stop, d_end)

        if not best_start or not best_end or best_start[0] == best_end[0]:
            continue

        start_idx, start_stop, start_dist = best_start
        end_idx, end_stop, end_dist = best_end

        results.append({
            "route_id": route["id"],
            "category": route["category"],
            "start_stop": start_stop,
            "end_stop": end_stop,
            "direction_ok": start_idx < end_idx,
            "stops_between": abs(end_idx - start_idx),
            "confidence": round(1.0 - (start_dist + end_dist) / (2 * threshold_km) * 0.3, 2),
            "start_score": None,
            "end_score": None,
            "match_type": "proximity",
            "start_dist_km": round(start_dist, 2),
            "end_dist_km": round(end_dist, 2),
        })

    results.sort(key=lambda r: (-r["confidence"], not r["direction_ok"], r["stops_between"]))
    return results[:top_n]


def find_all_matching_routes(start_location, end_location, start_coords=None, end_coords=None,
                              routes_path="bus_routes.json", top_n=15):
    name_matches = find_matching_routes(start_location, end_location, routes_path, top_n=top_n)
    combined = list(name_matches)

    if start_coords and end_coords:
        seen_ids = {m["route_id"] for m in name_matches}
        proximity_matches = find_proximity_routes(start_coords, end_coords, routes_path, top_n=top_n)
        for m in proximity_matches:
            if m["route_id"] not in seen_ids:
                combined.append(m)
                seen_ids.add(m["route_id"])

    combined.sort(key=lambda r: (-r["confidence"], not r["direction_ok"], r["stops_between"]))
    return combined[:top_n]


def enrich_journey(match, start_coords, end_coords, api_key):
    NAME_MATCH_THRESHOLD = 0.85
    ZERO_LEG = {"distance_km": 0.0, "duration_min": 0}
    known_stop_coords = load_stop_coordinates()

    if match.get("match_type") == "proximity" and known_stop_coords.get(match["start_stop"]):
        stop_start_coords = known_stop_coords[match["start_stop"]]
        walk1 = get_walking_leg(tuple(start_coords), tuple(stop_start_coords), api_key)
    elif (match.get("start_score") or 0) >= NAME_MATCH_THRESHOLD:
        stop_start_coords = start_coords
        walk1 = ZERO_LEG
    elif known_stop_coords.get(match["start_stop"]):
        stop_start_coords = known_stop_coords[match["start_stop"]]
        walk1 = get_walking_leg(tuple(start_coords), tuple(stop_start_coords), api_key)
    else:
        stop_start_coords = geocode_stop(match["start_stop"], api_key)
        walk1 = get_walking_leg(tuple(start_coords), tuple(stop_start_coords), api_key) if stop_start_coords else None

    if match.get("match_type") == "proximity" and known_stop_coords.get(match["end_stop"]):
        stop_end_coords = known_stop_coords[match["end_stop"]]
        walk2 = get_walking_leg(tuple(stop_end_coords), tuple(end_coords), api_key)
    elif (match.get("end_score") or 0) >= NAME_MATCH_THRESHOLD:
        stop_end_coords = end_coords
        walk2 = ZERO_LEG
    elif known_stop_coords.get(match["end_stop"]):
        stop_end_coords = known_stop_coords[match["end_stop"]]
        walk2 = get_walking_leg(tuple(stop_end_coords), tuple(end_coords), api_key)
    else:
        stop_end_coords = geocode_stop(match["end_stop"], api_key)
        walk2 = get_walking_leg(tuple(stop_end_coords), tuple(end_coords), api_key) if stop_end_coords else None

    if not stop_start_coords or not stop_end_coords or not walk1 or not walk2:
        return None

    bus_leg = get_bus_segment_estimate(tuple(stop_start_coords), tuple(stop_end_coords), api_key)
    if not bus_leg:
        return None

    return {
        **match,
        "stop_start_coords": stop_start_coords,
        "stop_end_coords": stop_end_coords,
        "walk_to_stop": walk1,
        "bus_leg": bus_leg,
        "walk_to_dest": walk2,
        "total_time_min": walk1["duration_min"] + bus_leg["duration_min"] + walk2["duration_min"],
    }


def build_ranked_journeys(start_location, end_location, start_coords, end_coords, api_key, candidates_to_check=2):
    candidates = find_matching_routes(start_location, end_location, top_n=candidates_to_check)
    journeys = []
    for c in candidates:
        j = enrich_journey(c, start_coords, end_coords, api_key)
        if j:
            journeys.append(j)
    journeys.sort(key=lambda j: j["total_time_min"])
    return journeys


KARACHI_BOUNDS = {"min_lon": 66.60, "max_lon": 67.50, "min_lat": 24.70, "max_lat": 25.20}
KARACHI_FOCUS = [67.0011, 24.8607]


def _within_karachi(coords):
    lon, lat = coords[0], coords[1]
    return (KARACHI_BOUNDS["min_lon"] <= lon <= KARACHI_BOUNDS["max_lon"] and
            KARACHI_BOUNDS["min_lat"] <= lat <= KARACHI_BOUNDS["max_lat"])


@st.cache_data
def geocode_stop(stop_name, api_key):
    try:
        client = openrouteservice.Client(key=api_key)
        result = client.pelias_search(
            text=stop_name + ", Karachi, Pakistan",
            focus_point=KARACHI_FOCUS,
            rect_min_x=KARACHI_BOUNDS["min_lon"],
            rect_min_y=KARACHI_BOUNDS["min_lat"],
            rect_max_x=KARACHI_BOUNDS["max_lon"],
            rect_max_y=KARACHI_BOUNDS["max_lat"],
            country="PAK",
        )
        coords = result['features'][0]['geometry']['coordinates']
        if not _within_karachi(coords):
            print(f"Stop geocoding error ({stop_name}): resolved outside Karachi ({coords}), rejecting")
            return None
        return coords
    except ApiError as e:
        if is_quota_or_rate_limit_error(e):
            raise
        print(f"Stop geocoding error ({stop_name}): {e}")
        return None
    except Exception as e:
        print(f"Stop geocoding error ({stop_name}): {e}")
        return None


@st.cache_data
def get_walking_leg(from_coords, to_coords, api_key):
    try:
        client = openrouteservice.Client(key=api_key)
        r = client.directions([from_coords, to_coords], profile='foot-walking', format='geojson')
        s = r['features'][0]['properties']['summary']
        return {'distance_km': round(s['distance'] / 1000, 2), 'duration_min': round(s['duration'] / 60)}
    except ApiError as e:
        if is_quota_or_rate_limit_error(e):
            raise
        print(f"Walking leg error: {e}")
        return None
    except Exception as e:
        print(f"Walking leg error: {e}")
        return None


@st.cache_data
def get_bus_segment_estimate(from_coords, to_coords, api_key):
    try:
        client = openrouteservice.Client(key=api_key)
        r = client.directions([from_coords, to_coords], profile='driving-car', format='geojson')
        s = r['features'][0]['properties']['summary']
        distance_km = round(s['distance'] / 1000, 2)
        duration_min = round((s['duration'] / 60) * BUS_SLOWDOWN_FACTOR)
        return {'distance_km': distance_km, 'duration_min': duration_min}
    except ApiError as e:
        if is_quota_or_rate_limit_error(e):
            raise
        print(f"Bus segment estimate error: {e}")
        return None
    except Exception as e:
        print(f"Bus segment estimate error: {e}")
        return None


def build_route_map(user_start_coords, user_end_coords, journey):
    def flip(c):
        return [c[1], c[0]]

    start_pt = flip(user_start_coords)
    end_pt = flip(user_end_coords)
    stop_start_pt = flip(journey["stop_start_coords"])
    stop_end_pt = flip(journey["stop_end_coords"])

    m = folium.Map(location=start_pt, zoom_start=13, tiles="cartodbpositron")

    folium.Marker(start_pt, popup="Your location", icon=folium.Icon(color="blue", icon="user")).add_to(m)
    folium.Marker(stop_start_pt, popup=f"Board {journey['route_id']} at {journey['start_stop']}",
                  icon=folium.Icon(color="green", icon="bus", prefix="fa")).add_to(m)
    folium.Marker(stop_end_pt, popup=f"Alight at {journey['end_stop']}",
                  icon=folium.Icon(color="orange", icon="bus", prefix="fa")).add_to(m)
    folium.Marker(end_pt, popup="Destination", icon=folium.Icon(color="red", icon="flag")).add_to(m)

    folium.PolyLine([start_pt, stop_start_pt], color="gray", weight=3, dash_array="6,8",
                     tooltip=f"Walk {journey['walk_to_stop']['duration_min']} min").add_to(m)
    folium.PolyLine([stop_start_pt, stop_end_pt], color="#1D9E75", weight=5,
                     tooltip=f"{journey['route_id']} — {journey['bus_leg']['duration_min']} min").add_to(m)
    folium.PolyLine([stop_end_pt, end_pt], color="gray", weight=3, dash_array="6,8",
                     tooltip=f"Walk {journey['walk_to_dest']['duration_min']} min").add_to(m)

    bounds = [start_pt, stop_start_pt, stop_end_pt, end_pt]
    m.fit_bounds(bounds, padding=(30, 30))
    return m