# 🗺️ RaahIQ — Karachi ka Smart AI Commute Planner

An AI-powered smart commute planner built specifically for Karachi, Pakistan.
Designed for the general public of Karachi to help them plan smarter daily commutes,
save time, reduce fuel costs and avoid heavy traffic.

## Features

- 🗺️ **Route Planner** — Find the fastest driving route using real map data, with a live traffic badge for your chosen departure time and a smarter-time suggestion when heavy traffic is expected.
- 🚌 **Bus Route Finder** — Matches your start and destination against real Karachi bus, coach, Red Bus, EV Bus, and BRT route data (70+ routes). Shows every bus that plausibly serves your route so you can pick the one you prefer, along with walking distance to the nearest stop and an interactive map — works even without internet, falling back to offline route-name matching.
- 🧠 **Traffic AI** — ML-powered traffic prediction for any area, time and weather.
- 📊 **Full Day Forecast** — Visual traffic forecast chart for the entire day.
- ⛽ **Petrol Calculator** — Calculate exact fuel cost for bike riders.
- 🚗 **Carpool** — Coming soon!

> **Note:** Fares are not shown for bus routes since real-time fare data isn't available — only route, boarding/alighting stops, and estimated time are shown to avoid displaying misleading numbers.

## Tech Stack

- **Frontend:** Streamlit
- **ML Model:** Random Forest Classifier (Scikit-learn)
- **Maps and Routes:** OpenRouteService API (driving directions, walking directions, geocoding — constrained to Karachi's bounding box for accuracy)
- **Bus Route Matching:** Custom fuzzy-matching engine over a structured dataset of real Karachi public transport routes
- **Interactive Maps:** Folium + streamlit-folium
- **Charts:** Plotly
- **Dataset:** Custom synthetic Karachi traffic dataset (5,000 samples) + real Karachi public transport route data (Mini Bus, Coach, Red Bus, EV Bus, BRT)

## Project Structure

- `app.py` — Main Streamlit app and UI
- `utils.py` — Route/coordinate helpers (OpenRouteService integration)
- `ml.py` / `traffic_model.py` — Traffic prediction model training & inference
- `bus_finder.py` — Bus route matching, walking-distance calculation, and map generation
- `bus_routes.json` — Structured dataset of real Karachi bus/coach/BRT routes and stops

## Setup

Install dependencies:
```
pip install -r requirements.txt
```

Add your OpenRouteService API key to a `.env` file:
```
ORS_API_KEY=your_api_key_here
```

Get a free API key at: https://openrouteservice.org

Run the app:
```
streamlit run app.py
```
(On Windows, if the `streamlit` command isn't recognized, use `python -m streamlit run app.py` instead.)

## ML Model

The traffic prediction model is trained on a synthetic dataset of 5,000 Karachi traffic samples.
It uses day, time, area, and weather as features to predict Light, Moderate, or Heavy traffic.

To retrain the model:
```
python traffic_model.py
```

## Bus Route Data

Bus route data was manually compiled from real Karachi public transport route guides, covering Mini Bus, Coach, Other Bus, Red Bus, EV Bus, and BRT (Green/Orange Line) routes — 70+ routes in total, stored in `bus_routes.json`. The matching engine fuzzy-matches user-entered locations against stop names, so exact spelling isn't required (e.g. "Gulshan-e-Iqbal" correctly matches nearby stops like "Gulshan Chorangi").

## Known Limitations

- Bus fares are not shown since live fare data isn't available.
- Weather input for the traffic-aware time suggestion currently defaults to "Clear" — live weather API integration is a future improvement.
- Full offline mode only covers bus route name/stop matching; live map, walking distance, and the Fastest route card require an internet connection.

## Built by

Muhammad Ubaid Idrees — BS AI Student
Dawood University of Engineering & Technology, Karachi