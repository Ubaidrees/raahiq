import streamlit as st
import openrouteservice

def get_client(api_key):
    return openrouteservice.Client(key=api_key)

@st.cache_data
def get_coordinates(place_name, api_key):
    try:
        client = get_client(api_key)
        result = client.pelias_search(text=place_name + ", Karachi, Pakistan")
        coords = result['features'][0]['geometry']['coordinates']
        return coords
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