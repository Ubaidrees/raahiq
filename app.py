import streamlit as st
import base64
import datetime
import plotly.graph_objects as go
from config import API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD
from utils import get_coordinates, get_fastest_route, estimate_cost, get_maps_link, match_area
from ml import predict_traffic, load_model
from bus_finder import find_matching_routes, find_proximity_routes, find_local_coords, enrich_journey, build_route_map
from streamlit_folium import st_folium
from feedback import send_feedback_email

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

# ─── Sidebar: Feedback (always visible, regardless of tab) ───
with st.sidebar:
    st.markdown("### 💬 Feedback / Review")
    st.caption("Koi route galat lage ya koi masla ho to yahan likh dein — humein seedha email mil jayega.")
    fb_text = st.text_area("Aapka feedback", placeholder="e.g. Route X-8 ka stop galat hai...", key="fb_text")
    fb_email = st.text_input("Email (optional, agar reply chahiye)", key="fb_email")
    if st.button("📩 Submit Feedback"):
        if fb_text.strip():
            try:
                send_feedback_email(fb_text, fb_email, GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                st.success("✅ Shukriya! Aapka feedback mil gaya.")
            except Exception as e:
                print(f"Feedback email error: {e}")
                st.error("⚠️ Feedback bhejte waqt masla aaya — dobara try karein.")
        else:
            st.warning("Pehle apna feedback likhein.")

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

    # Persist the search trigger + inputs in session_state so results survive
    # the automatic rerun that st_folium triggers when the map component loads.
    if find:
        if start and end:
            st.session_state['route_search'] = {
                "start": " ".join(start.split()),
                "end": " ".join(end.split()),
                "time": time,
            }
        else:
            st.session_state['route_search'] = None
            st.error("⚠️ Please enter both Starting Location and Destination!")

    search = st.session_state.get('route_search')

    if search:
        s_start, s_end, s_time = search["start"], search["end"], search["time"]

        st.markdown(f"### 📍 {s_start}  →  {s_end}  |  ⏰ {s_time}")
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Step 1: Basic bus route match — works fully offline, no API calls.
        # top_n=15 so users see (almost) every bus serving this route and can
        # pick whichever they prefer, instead of us picking for them. ──
        basic_matches = find_matching_routes(s_start, s_end, top_n=15)

        # ── Step 2: Try internet-dependent features (geocoding, driving, Fastest card) ──
        from openrouteservice.exceptions import ApiError
        from utils import is_quota_or_rate_limit_error
        internet_ok = True
        rate_limited = False
        start_coords, end_coords, f = None, None, None
        try:
            with st.spinner("🔍 Finding best routes..."):
                # Check our own already-geocoded stop database first — avoids a
                # live ORS call for the very common case where the user typed
                # a well-known landmark/chorangi that's already one of our stops.
                start_coords = find_local_coords(s_start) or get_coordinates(s_start, API_KEY)
                end_coords = find_local_coords(s_end) or get_coordinates(s_end, API_KEY)
                if start_coords and end_coords:
                    f = get_fastest_route(tuple(start_coords), tuple(end_coords), API_KEY)
                    # Now that we have real coordinates, also check for routes with a
                    # NEARBY stop even if its name doesn't textually match what was typed
                    # (e.g. "Star Gate" query catching a route that only lists "Colony Gate").
                    seen_ids = {m["route_id"] for m in basic_matches}
                    proximity_matches = find_proximity_routes(start_coords, end_coords, top_n=15)
                    for pm in proximity_matches:
                        if pm["route_id"] not in seen_ids:
                            basic_matches.append(pm)
                            seen_ids.add(pm["route_id"])
                    basic_matches.sort(key=lambda r: (-r["confidence"], not r["direction_ok"], r["stops_between"]))
                else:
                    internet_ok = False
        except ApiError as e:
            if is_quota_or_rate_limit_error(e):
                rate_limited = True
            internet_ok = False
        except Exception as e:
            print(f"Connectivity/route error: {e}")
            internet_ok = False

        col1, col2 = st.columns([1, 2])

        with col1:
            if f and start_coords and end_coords:
                cost = estimate_cost("Rickshaw", f['distance'])
                link_drive = get_maps_link(s_start, s_end, "driving")

                # ── Traffic-aware addition: connect the departure time selector
                # to the existing ML model instead of leaving it unused ──
                current_day = datetime.datetime.now().strftime("%A")
                matched_area = match_area(s_start, areas_list)
                traffic_now = predict_traffic(current_day, s_time, matched_area, "Clear")

                badge_style = {
                    "Light": ("#00bb66", "🟢"),
                    "Moderate": ("#ff9900", "🟡"),
                    "Heavy": ("#ff4444", "🔴"),
                }
                badge_color, badge_emoji = badge_style.get(traffic_now, ("#999", "⚪"))

                st.markdown(f"""
                <div class='route-fastest'>
                    <h2 style='color:#0066ff; margin:0'>⚡ Fastest</h2>
                    <p style='color:#999; margin:5px 0 15px 0'>Via Fastest Route</p>
                    <p class='price' style='color:#0066ff'>{f['duration']} mins</p>
                    <p class='stat'>📏 {f['distance']} km</p>
                    <p class='stat'>🛺 Rickshaw</p>
                    <p class='stat' style='color:#0066ff; font-weight:700; font-size:1.1rem'>Rs. {cost}</p>
                    <p class='stat' style='color:{badge_color}; font-weight:700; margin-top:10px;'>{badge_emoji} {traffic_now} traffic expected at {s_time}</p>
                    <a href='{link_drive}' target='_blank' class='maps-btn-blue'>🗺️ Open in Maps</a>
                </div>
                """, unsafe_allow_html=True)

                # Suggest a better nearby departure time if one exists with lower traffic
                time_order = ["7:00 AM", "8:00 AM", "9:00 AM", "10:00 AM", "12:00 PM", "2:00 PM", "5:00 PM", "7:00 PM"]
                traffic_rank = {"Light": 1, "Moderate": 2, "Heavy": 3}
                if s_time in time_order:
                    idx = time_order.index(s_time)
                    for candidate_time in time_order[idx + 1: idx + 4]:
                        candidate_result = predict_traffic(current_day, candidate_time, matched_area, "Clear")
                        if traffic_rank[candidate_result] < traffic_rank[traffic_now]:
                            st.info(f"💡 Try **{candidate_time}** instead — traffic is expected to drop to **{candidate_result}**.")
                            break
            else:
                st.markdown("""
                <div class='route-fastest'>
                    <h2 style='color:#999; margin:0'>⚡ Fastest</h2>
                    <p style='color:#999; margin:10px 0'>📶 Needs internet connection</p>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### 🚌 Bus Route Options")

            if not internet_ok:
                if rate_limited:
                    st.warning("⏳ Map/route service ka daily limit abhi khatam ho gaya hai (bohot zyada log use kar rahe hain) — kal wapas try karein ya thodi der baad. Neeche bus route names phir bhi dikh rahe hain.")
                else:
                    st.warning("📶 No internet connection detected — showing offline bus route matches only (route number & stops). Connect to internet for walking distance and live map.")

            if basic_matches:
                option_labels = [
                    f"{m['route_id']} · {m['category']}" + (" (nearby stop)" if m.get("match_type") == "proximity" else "")
                    for m in basic_matches
                ]
                chosen_label = st.selectbox(
                    f"🔍 Found {len(basic_matches)} bus route(s) serving this area — select one to see details:",
                    option_labels,
                    key="chosen_bus_route",
                )
                chosen_match = basic_matches[option_labels.index(chosen_label)]

                if internet_ok and start_coords and end_coords:
                    enriched, route_rate_limited = None, False
                    try:
                        with st.spinner("🚌 Getting walking distance & map for this route..."):
                            enriched = enrich_journey(chosen_match, start_coords, end_coords, API_KEY)
                    except ApiError as e:
                        if is_quota_or_rate_limit_error(e):
                            route_rate_limited = True
                    except Exception as e:
                        print(f"Enrich journey error: {e}")

                    if enriched:
                        walk1_min = enriched['walk_to_stop']['duration_min']
                        walk2_min = enriched['walk_to_dest']['duration_min']
                        walk1_text = "" if walk1_min <= 1 else f" (walk {walk1_min} min)"
                        walk2_text = "" if walk2_min <= 1 else f", then walk {walk2_min} min"

                        st.markdown(f"""
                        <div class='route-cheapest' style='padding:18px 25px; margin-top:12px;'>
                            <p style='color:#00bb66; font-weight:700; margin:0 0 6px 0'>Route {enriched['route_id']} ({enriched['category']})</p>
                            <p class='stat'>🚏 Board at: <b>{enriched['start_stop']}</b>{walk1_text}</p>
                            <p class='stat'>🛑 Alight at: <b>{enriched['end_stop']}</b>{walk2_text}</p>
                            <p class='stat' style='color:#00bb66; font-weight:700; font-size:1.05rem'>⏱️ Total est. time: {enriched['total_time_min']} mins</p>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown("##### 🗺️ Route map")
                        route_map = build_route_map(start_coords, end_coords, enriched)
                        st_folium(route_map, width=700, height=400, key="route_map")
                    else:
                        if route_rate_limited:
                            st.caption("⏳ Server thoda busy hai — thodi der baad try karein. Route info: Board near "
                                       f"**{chosen_match['start_stop']}**, alight near **{chosen_match['end_stop']}**.")
                        else:
                            st.caption(f"📍 Board near **{chosen_match['start_stop']}**, alight near **{chosen_match['end_stop']}** — couldn't fetch live walking distance/map for this stop right now.")
                else:
                    st.markdown(f"""
                    <div class='route-cheapest' style='padding:18px 25px; margin-top:12px;'>
                        <p style='color:#00bb66; font-weight:700; margin:0 0 6px 0'>Route {chosen_match['route_id']} ({chosen_match['category']})</p>
                        <p class='stat'>🚏 Board near: <b>{chosen_match['start_stop']}</b></p>
                        <p class='stat'>🛑 Alight near: <b>{chosen_match['end_stop']}</b></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("🚌 No direct bus route found between these two areas — try nearby major roads or landmarks (e.g. a chorangi or well-known stop name).")

        st.markdown("<br>", unsafe_allow_html=True)
        if internet_ok:
            st.success("✅ Real routes found — Powered by OpenRouteService!")

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