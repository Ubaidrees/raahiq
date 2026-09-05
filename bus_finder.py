import json
from difflib import SequenceMatcher
import streamlit as st
import openrouteservice
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


# Common Karachi place-name words that appear inside MANY unrelated compound
# names (e.g. "Tower" alone vs "Clock Tower DHA" vs "PIDC Tower" are all
# different places). If the user's query is just one of these generic words,
# we require an EXACT stop-name match rather than loose substring matching —
# otherwise "tower" would wrongly match any stop containing that word.
_GENERIC_SINGLE_WORDS = {
    "tower", "chorangi", "chowk", "mor", "road", "bridge", "colony",
    "market", "town", "stop", "square", "park", "hospital", "school",
    "hotel", "goth", "society", "complex", "station", "gate", "plaza",
}


def _find_best_stop_match(query, stops, threshold=0.55):
    """Find the stop in `stops` that best matches `query`. Returns (stop_name, index, score)."""
    query_lower = query.lower().strip()
    is_generic_query = query_lower in _GENERIC_SINGLE_WORDS
    best_stop, best_idx, best_score = None, None, 0.0

    for idx, stop in enumerate(stops):
        stop_lower = stop.lower()

        if query_lower == stop_lower:
            return stop, idx, 1.0

        if is_generic_query:
            # Too ambiguous for partial matching — skip anything that isn't an exact match
            continue

        if query_lower in stop_lower or stop_lower in query_lower:
            score = 0.9
        else:
            score = _similarity(query, stop)
        if score > best_score:
            best_stop, best_idx, best_score = stop, idx, score

    if best_score >= threshold:
        return best_stop, best_idx, best_score
    return None, None, 0.0


def find_matching_routes(start_location, end_location, routes_path="bus_routes.json", top_n=15):
    """
    Cheap first pass: find candidate routes where both locations fuzzy-match a stop.
    Returns list sorted by confidence, direction correctness, and directness.
    top_n=15 by default so users can see (almost) every bus that plausibly serves
    their route and pick whichever they prefer, rather than us picking for them.
    """
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
        })

    results.sort(key=lambda r: (-r["confidence"], not r["direction_ok"], r["stops_between"]))
    return results[:top_n]


def enrich_journey(match, start_coords, end_coords, api_key):
    """
    Given ONE basic route match (from find_matching_routes), compute the real
    walking + bus legs for it. Only call this for the route the user actually
    selects, to avoid burning API calls on every candidate.

    If the matched stop name is nearly identical to what the user typed
    (e.g. user typed "ayesha manzil" and the stop is "Aisha Manzil"), we skip
    re-geocoding that end separately and just reuse the user's own coordinates.
    Independently geocoding two near-identical spellings can otherwise return
    slightly different points and produce a bogus "extra walk" for what is
    really the same place.

    Returns an enriched journey dict, or None if any leg couldn't be computed
    (e.g. no internet, or a stop couldn't be geocoded).
    """
    NAME_MATCH_THRESHOLD = 0.85
    ZERO_LEG = {"distance_km": 0.0, "duration_min": 0}

    if match.get("start_score", 0) >= NAME_MATCH_THRESHOLD:
        stop_start_coords = start_coords
        walk1 = ZERO_LEG
    else:
        stop_start_coords = geocode_stop(match["start_stop"], api_key)
        walk1 = get_walking_leg(tuple(start_coords), tuple(stop_start_coords), api_key) if stop_start_coords else None

    if match.get("end_score", 0) >= NAME_MATCH_THRESHOLD:
        stop_end_coords = end_coords
        walk2 = ZERO_LEG
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
    """
    Kept for backward compatibility: fuzzy-matches candidates then enriches the
    top few and ranks by total time. Prefer find_matching_routes() + enrich_journey()
    for the "let the user pick" flow.
    """
    candidates = find_matching_routes(start_location, end_location, top_n=candidates_to_check)
    journeys = []
    for c in candidates:
        j = enrich_journey(c, start_coords, end_coords, api_key)
        if j:
            journeys.append(j)
    journeys.sort(key=lambda j: j["total_time_min"])
    return journeys


# ─────────────────────────── Geocoding & real travel legs ───────────────────────────

KARACHI_BOUNDS = {"min_lon": 66.60, "max_lon": 67.50, "min_lat": 24.70, "max_lat": 25.20}
KARACHI_FOCUS = [67.0011, 24.8607]


def _within_karachi(coords):
    lon, lat = coords[0], coords[1]
    return (KARACHI_BOUNDS["min_lon"] <= lon <= KARACHI_BOUNDS["max_lon"] and
            KARACHI_BOUNDS["min_lat"] <= lat <= KARACHI_BOUNDS["max_lat"])


@st.cache_data
def geocode_stop(stop_name, api_key):
    """Geocode a bus stop name to [lon, lat] using ORS, constrained to Karachi's bounding box."""
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
    except Exception as e:
        print(f"Stop geocoding error ({stop_name}): {e}")
        return None


@st.cache_data
def get_walking_leg(from_coords, to_coords, api_key):
    """Real walking distance/time between two [lon, lat] points using ORS foot-walking profile."""
    try:
        client = openrouteservice.Client(key=api_key)
        r = client.directions([from_coords, to_coords], profile='foot-walking', format='geojson')
        s = r['features'][0]['properties']['summary']
        return {'distance_km': round(s['distance'] / 1000, 2), 'duration_min': round(s['duration'] / 60)}
    except Exception as e:
        print(f"Walking leg error: {e}")
        return None


@st.cache_data
def get_bus_segment_estimate(from_coords, to_coords, api_key):
    """
    Estimate the in-bus travel leg using ORS driving-car distance/duration as a base,
    then apply a slowdown factor for stop-and-go bus behaviour.
    """
    try:
        client = openrouteservice.Client(key=api_key)
        r = client.directions([from_coords, to_coords], profile='driving-car', format='geojson')
        s = r['features'][0]['properties']['summary']
        distance_km = round(s['distance'] / 1000, 2)
        duration_min = round((s['duration'] / 60) * BUS_SLOWDOWN_FACTOR)
        return {'distance_km': distance_km, 'duration_min': duration_min}
    except Exception as e:
        print(f"Bus segment estimate error: {e}")
        return None



# ─────────────────────────── Map rendering ───────────────────────────

def build_route_map(user_start_coords, user_end_coords, journey):
    """
    Build a folium map showing: user start -> walk -> board stop -> bus leg
    -> alight stop -> walk -> destination.
    All coords are [lon, lat] (ORS order); folium needs [lat, lon].
    """
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