# 🗺️ RaahIQ — Karachi ka Smart AI Commute Planner

An AI-powered smart commute planner built specifically for Karachi, Pakistan.
Designed for the general public of Karachi to help them plan smarter daily commutes,
save time, reduce fuel costs and avoid heavy traffic.

## Features
- 🗺️ Route Planner — Find fastest, cheapest and balanced routes using real map data
- 🧠 Traffic AI — ML-powered traffic prediction for any area, time and weather
- 📊 Full Day Forecast — Visual traffic forecast chart for entire day
- ⛽ Petrol Calculator — Calculate exact fuel cost for bike riders
- 🚗 Carpool — Coming soon!

## Tech Stack
- Frontend: Streamlit
- ML Model: Random Forest Classifier (Scikit-learn)
- Maps and Routes: OpenRouteService API
- Charts: Plotly
- Dataset: Custom synthetic Karachi traffic dataset (5000 samples)

## Setup

Install dependencies:
pip install -r requirements.txt

Add your OpenRouteService API key to .env file:
ORS_API_KEY=your_api_key_here

Get a free API key at: https://openrouteservice.org

Run the app:
streamlit run app.py

## ML Model
The traffic prediction model is trained on a synthetic dataset of 5000 Karachi traffic samples.
It uses day, time, area and weather as features to predict Light, Moderate or Heavy traffic.

To retrain the model:
python traffic_model.py

## Built by
Muhammad Ubaid Idrees — BS AI Student
Dawood University of Engineering & Technology, Karachi