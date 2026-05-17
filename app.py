import streamlit as st
import base64
import plotly.graph_objects as go
from config import API_KEY
from utils import get_coordinates, get_all_routes, estimate_cost, get_maps_link
from ml import predict_traffic, load_model

st.set_page_config(page_title="RaahIQ", page_icon="🗺️", layout="wide")

traffic_model, metadata = load_model()
days_list = metadata['days']
areas_list = metadata['areas']
weather_list = metadata['weather']

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        print(f"Image Error: {e}")
        return ""

map_bg = get_base64_image("map_bg.png")

st.markdown(f"""
<style>
    .stApp {{ background: #f0f4f8; }}
    .header {{
        background: linear-gradient(135deg, rgba(0,102,255,0.65), rgba(0,153,255,0.65)),
                    url("data:image/png;base64,{map_bg}") center/cover no-repeat;
        padding: 50px 40px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,102,255,0.3);
        position: relative;
        overflow: hidden;
    }}
    .header h1 {{ color: white; font-size: 3rem; font-weight: 900; margin: 0; letter-spacing: 2px; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }}
    .header p {{ color: rgba(255,255,255,0.95); font-size: 1.1rem; margin: 10px 0 0 0; letter-spacing: 4px; text-transform: uppercase; text-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
    .card {{
        background: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }}
    .route-fastest {{
        background: white;
        border-radius: 20px;
        padding: 25px;
        border-top: 5px solid #0066ff;
        box-shadow: 0 4px 20px rgba(0,102,255,0.15);
        text-align: center;
    }}
    .route-cheapest {{
        background: white;
        border-radius: 20px;
        padding: 25px;
        border-top: 5px solid #00bb66;
        box-shadow: 0 4px 20px rgba(0,187,102,0.15);
        text-align: center;
    }}
    .route-balanced {{
        background: white;
        border-radius: 20px;
        padding: 25px;
        border-top: 5px solid #ff9900;
        box-shadow: 0 4px 20px rgba(255,153,0,0.15);
        text-align: center;
    }}
    .petrol-card {{
        background: white;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border-left: 5px solid #ff4500;
        margin-top: 15px;
    }}
    .maps-btn-blue {{
        display: inline-block;
        margin-top: 15px;
        padding: 10px 25px;
        background: linear-gradient(90deg, #0066ff, #0099ff);
        color: white !important;
        border-radius: 25px;
        text-decoration: none !important;
        font-weight: 700;
        font-size: 0.9rem;
    }}
    .maps-btn-green {{
        display: inline-block;
        margin-top: 15px;
        padding: 10px 25px;
        background: linear-gradient(90deg, #00bb66, #00dd77);
        color: white !important;
        border-radius: 25px;
        text-decoration: none !important;
        font-weight: 700;
        font-size: 0.9rem;
    }}
    .maps-btn-orange {{
        display: inline-block;
        margin-top: 15px;
        padding: 10px 25px;
        background: linear-gradient(90deg, #ff9900, #ffbb00);
        color: white !important;
        border-radius: 25px;
        text-decoration: none !important;
        font-weight: 700;
        font-size: 0.9rem;
    }}
    .stTextInput input {{
        border-radius: 10px !important;
        border: 2px solid #e0e0e0 !important;
        padding: 12px !important;
        font-size: 1rem !important;
    }}
    .stButton button {{
        background: linear-gradient(90deg, #0066ff, #0099ff) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 14px 40px !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        border: none !important;
        width: 100% !important;
    }}
    .stSelectbox div[data-baseweb="select"] {{
        cursor: pointer !important;
    }}
    .stSelectbox div[data-baseweb="select"] * {{
        cursor: pointer !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        background: white !important;
        border-radius: 15px !important;
        padding: 5px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
        gap: 5px !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 10px 25px !important;
        letter-spacing: 0.5px !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(90deg, #0066ff, #0099ff) !important;
        color: white !important;
    }}
    label {{ color: #333 !important; font-weight: 600 !important; font-size: 0.95rem !important; }}
    .stat {{ font-size: 0.95rem; color: #666; margin: 6px 0; }}
    .price {{ font-size: 1.6rem; font-weight: 900; margin: 10px 0; }}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class='header'>
    <div style="position:relative; z-index:1;">
        <div style="display:inline-flex; align-items:center; gap:15px; margin-bottom:10px;">
            <svg width="55" height="55" viewBox="0 0 55 55" xmlns="http://www.w3.org/2000/svg">
                <circle cx="27.5" cy="27.5" r="27.5" fill="white" opacity="0.2"/>
                <circle cx="27.5" cy="27.5" r="20" fill="none" stroke="white" stroke-width="2.5"/>
                <line x1="27.5" y1="7.5" x2="27.5" y2="47.5" stroke="white" stroke-width="2.5"/>
                <line x1="7.5" y1="27.5" x2="47.5" y2="27.5" stroke="white" stroke-width="2.5"/>
                <circle cx="27.5" cy="27.5" r="5" fill="white"/>
                <circle cx="27.5" cy="14" r="3" fill="white" opacity="0.7"/>
                <circle cx="41" cy="27.5" r="3" fill="white" opacity="0.7"/>
            </svg>
            <h1>RaahIQ</h1>
        </div>
        <p>Karachi ka Smart AI Commute Planner</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Route Planner",
    "🧠 Traffic AI",
    "📊 Forecast",
    "⛽ Petrol Calc",
    "🚗 Carpool"
])

# ─── TAB 1 — Route Planner ───
with tab1:
    st.markdown("### 🗺️ Find Your Best Route")
    st.markdown("*Enter your locations and find the best route!*")
    col1, col2, col3 = st.columns(3)
    with col1:
        start = st.text_input("📍 Starting Location", placeholder="e.g. Gulshan-e-Iqbal")
    with col2:
        end = st.text_input("🏁 Destination", placeholder="e.g. Saddar")
    with col3:
        time = st.selectbox("⏰ Departure Time", [
            "7:00 AM", "8:00 AM", "9:00 AM", "10:00 AM",
            "12:00 PM", "2:00 PM", "5:00 PM", "7:00 PM"
        ])
    st.markdown("<br>", unsafe_allow_html=True)
    find = st.button("🔍 Find Best Routes")

    if find:
        if start and end:
            with st.spinner("🔍 Finding best routes..."):
                start_coords = get_coordinates(start, API_KEY)
                end_coords = get_coordinates(end, API_KEY)

                if start_coords and end_coords:
                    routes = get_all_routes(tuple(start_coords), tuple(end_coords), API_KEY)
                    f = routes['fastest']
                    c = routes['cheapest']
                    b = routes['balanced']

                    link_drive = get_maps_link(start, end, "driving")
                    link_transit = get_maps_link(start, end, "transit")
                    link_bike = get_maps_link(start, end, "bicycling")

                    st.markdown(f"### 📍 {start}  →  {end}  |  ⏰ {time}")
                    st.markdown("<br>", unsafe_allow_html=True)

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        cost = estimate_cost("Rickshaw", f['distance'])
                        st.markdown(f"""
                        <div class='route-fastest'>
                            <h2 style='color:#0066ff; margin:0'>⚡ Fastest</h2>
                            <p style='color:#999; margin:5px 0 15px 0'>Via Fastest Route</p>
                            <p class='price' style='color:#0066ff'>{f['duration']} mins</p>
                            <p class='stat'>📏 {f['distance']} km</p>
                            <p class='stat'>🛺 Rickshaw</p>
                            <p class='stat' style='color:#0066ff; font-weight:700; font-size:1.1rem'>Rs. {cost}</p>
                            <a href='{link_drive}' target='_blank' class='maps-btn-blue'>🗺️ Open in Maps</a>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"""
                        <div class='route-cheapest'>
                            <h2 style='color:#00bb66; margin:0'>💰 Cheapest</h2>
                            <p style='color:#999; margin:5px 0 15px 0'>Via Bus Route</p>
                            <p class='price' style='color:#00bb66'>{c['duration']} mins</p>
                            <p class='stat'>📏 {c['distance']} km</p>
                            <p class='stat'>🚌 Bus + Walk</p>
                            <p class='stat' style='color:#00bb66; font-weight:700; font-size:1.1rem'>Rs. 30</p>
                            <a href='{link_transit}' target='_blank' class='maps-btn-green'>🗺️ Open in Maps</a>
                        </div>
                        """, unsafe_allow_html=True)

                    with col3:
                        bike_cost = estimate_cost("Bike Taxi", b['distance'])
                        st.markdown(f"""
                        <div class='route-balanced'>
                            <h2 style='color:#ff9900; margin:0'>⚖️ Balanced</h2>
                            <p style='color:#999; margin:5px 0 15px 0'>Via Alternate Route</p>
                            <p class='price' style='color:#ff9900'>{b['duration']} mins</p>
                            <p class='stat'>📏 {b['distance']} km</p>
                            <p class='stat'>🛵 Bike Taxi</p>
                            <p class='stat' style='color:#ff9900; font-weight:700; font-size:1.1rem'>Rs. {bike_cost}</p>
                            <a href='{link_bike}' target='_blank' class='maps-btn-orange'>🗺️ Open in Maps</a>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.success("✅ Real routes found — Powered by OpenRouteService!")
                else:
                    st.error("⚠️ Location not found — please enter a valid Karachi area!")
        else:
            st.error("⚠️ Please enter both Starting Location and Destination!")

# ─── TAB 2 — Traffic AI ───
with tab2:
    st.markdown("### 🧠 AI Traffic Prediction")
    st.markdown("*Select your travel details — ML will predict traffic conditions!*")

    time_options = [
        "12:00 AM", "1:00 AM", "2:00 AM", "3:00 AM", "4:00 AM", "5:00 AM",
        "6:00 AM", "7:00 AM", "8:00 AM", "9:00 AM", "10:00 AM", "11:00 AM",
        "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM",
        "6:00 PM", "7:00 PM", "8:00 PM", "9:00 PM", "10:00 PM", "11:00 PM"
    ]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_day = st.selectbox("📅 Day", days_list)
    with col2:
        selected_time = st.selectbox("⏰ Time", time_options, index=8)
    with col3:
        selected_area = st.selectbox("📍 Area", areas_list)
    with col4:
        selected_weather = st.selectbox("🌤️ Weather", weather_list)

    traffic_result = predict_traffic(selected_day, selected_time, selected_area, selected_weather)

    if traffic_result == "Heavy":
        traffic_color = "#ff4444"
        traffic_emoji = "🔴"
        traffic_msg = "Leave early — heavy traffic ahead!"
    elif traffic_result == "Moderate":
        traffic_color = "#ff9900"
        traffic_emoji = "🟡"
        traffic_msg = "Expect some delays on the road!"
    else:
        traffic_color = "#00bb66"
        traffic_emoji = "🟢"
        traffic_msg = "Great time to travel — smooth roads!"

    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {traffic_color}15, {traffic_color}30);
         padding: 20px; border-radius: 15px; margin-top: 15px;
         border: 2px solid {traffic_color}; text-align: center;'>
        <h2 style='color:{traffic_color}; margin:0'>{traffic_emoji} {traffic_result} Traffic</h2>
        <p style='color:#555; margin:8px 0 0 0; font-size:1.1rem'>{traffic_msg}</p>
        <p style='color:#999; margin:5px 0 0 0; font-size:0.85rem'>🤖 Powered by Random Forest ML Model</p>
    </div>
    """, unsafe_allow_html=True)

# ─── TAB 3 — Forecast ───
with tab3:
    st.markdown("### 📊 Traffic Forecast — Full Day")

    col1, col2, col3 = st.columns(3)
    with col1:
        forecast_day = st.selectbox("📅 Day", days_list, key="forecast_day")
    with col2:
        forecast_area = st.selectbox("📍 Area", areas_list, key="forecast_area")
    with col3:
        forecast_weather = st.selectbox("🌤️ Weather", weather_list, key="forecast_weather")

    st.markdown(f"*Traffic prediction for **{forecast_day}** in **{forecast_area}** — {forecast_weather} weather*")

    time_labels = [
        "12AM","1AM","2AM","3AM","4AM","5AM",
        "6AM","7AM","8AM","9AM","10AM","11AM",
        "12PM","1PM","2PM","3PM","4PM","5PM",
        "6PM","7PM","8PM","9PM","10PM","11PM"
    ]

    traffic_levels = []
    colors = []

    for i, label in enumerate(time_labels):
        if i == 0:
            t = "12:00 AM"
        elif i < 12:
            t = f"{i}:00 AM"
        elif i == 12:
            t = "12:00 PM"
        else:
            t = f"{i-12}:00 PM"
        result = predict_traffic(forecast_day, t, forecast_area, forecast_weather)
        traffic_levels.append({"Light": 1, "Moderate": 2, "Heavy": 3}[result])
        colors.append("#00bb66" if result == "Light" else "#ff9900" if result == "Moderate" else "#ff4444")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=time_labels,
        y=traffic_levels,
        marker_color=colors,
        text=["🟢 Light" if t == 1 else "🟡 Moderate" if t == 2 else "🔴 Heavy" for t in traffic_levels],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Traffic: %{text}<extra></extra>'
    ))

    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        yaxis=dict(
            tickvals=[1, 2, 3],
            ticktext=["🟢 Light", "🟡 Moderate", "🔴 Heavy"],
            gridcolor='#f0f0f0',
            range=[0, 3.8]
        ),
        xaxis=dict(gridcolor='#f0f0f0'),
        height=400,
        margin=dict(t=30, b=30),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

# ─── TAB 4 — Petrol Calculator ───
with tab4:
    st.markdown("### ⛽ Petrol Calculator")
    st.markdown("*Travelling by bike? Calculate your exact fuel cost!*")

    col1, col2 = st.columns(2)
    with col1:
        petrol_distance = st.number_input("📏 Distance (km)", min_value=1.0, max_value=200.0, value=10.0)
        bike_avg = st.number_input("🏍️ Bike Average (km/liter)", min_value=10, max_value=80, value=40)
    with col2:
        petrol_price = st.number_input("💰 Petrol Price (Rs/liter)", min_value=200, max_value=500, value=415)
        trips = st.number_input("🔄 Trips per Month", min_value=1, max_value=60, value=22)

    liters_needed = round(petrol_distance / bike_avg, 2)
    total_cost = round(liters_needed * petrol_price)
    monthly_cost = round(total_cost * trips)

    st.markdown(f"""
    <div class='petrol-card'>
        <h3 style='color:#ff4500; margin:0 0 15px 0'>⛽ Fuel Summary</h3>
        <p style='font-size:1.1rem; color:#333; margin:8px 0'>📏 Distance: <b>{petrol_distance} km</b></p>
        <p style='font-size:1.1rem; color:#333; margin:8px 0'>🛢️ Fuel Required: <b>{liters_needed} liters</b></p>
        <p style='font-size:1.1rem; color:#333; margin:8px 0'>💰 Per Trip Cost: <b>Rs. {total_cost}</b></p>
        <hr style='border-color:#eee; margin:15px 0'>
        <p style='font-size:1.4rem; color:#ff4500; font-weight:900; margin:0'>💸 Monthly Cost: Rs. {monthly_cost}</p>
    </div>
    """, unsafe_allow_html=True)

# ─── TAB 5 — Carpool ───
with tab5:
    st.markdown("### 🚗 Carpool — Coming Soon!")
    st.markdown("*Find people going your way and share the ride!*")
    st.info("🚀 Carpool feature is under development — coming in the next update!")
    st.markdown("""
    **Planned Features:**
    - 🔍 Find riders going your route
    - 💰 Split fuel costs automatically
    - ⭐ Rate your co-passengers
    - 🔒 Verified profiles only
    - 📍 Live location sharing
    """)