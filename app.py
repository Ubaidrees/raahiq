import streamlit as st
import datetime
import plotly.graph_objects as go
from config import API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD
from utils import get_coordinates, get_fastest_route, estimate_cost, get_maps_link, match_area
from ml import predict_traffic, load_model
from bus_finder import find_matching_routes, find_proximity_routes, find_local_coords, enrich_journey, build_route_map, load_bus_routes
from streamlit_folium import st_folium
from feedback import send_feedback_email
from translations import get_translator

st.set_page_config(page_title="RaahIQ", page_icon="🗺️", layout="wide")

# ─── Language toggle (English / Urdu) ───
if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

_lang_col1, _lang_col2 = st.columns([6, 1])
with _lang_col2:
    _lang_choice = st.radio("🌐", ["EN", "اردو"], horizontal=True, label_visibility="collapsed", key="lang_toggle")
    st.session_state["lang"] = "en" if _lang_choice == "EN" else "ur"

lang = st.session_state["lang"]
t = get_translator(lang)

if lang == "ur":
    st.markdown("""
    <style>
    html, body, [class*="css"], .stApp, p, span, div, label,
    h1, h2, h3, h4, .stat, .price, .route-badge,
    .stMarkdown, .stButton button, .stSelectbox, .stRadio,
    .stTextInput input, .stTextArea textarea, .stCaption {
        font-family: 'Noto Nastaliq Urdu', 'Manrope', sans-serif !important;
        line-height: 2.1 !important;
    }
    .header h1 { font-family: 'Space Grotesk', sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

traffic_model, metadata = load_model()
days_list = metadata['days']
areas_list = metadata['areas']
weather_list = metadata['weather']

# Route-category colors lifted from the real Karachi transit-guide signage
# this app's data was compiled from — makes the color carry information
# (which kind of bus) instead of being pure decoration.
CATEGORY_COLORS = {
    "Mini Bus": "#12857A",
    "Coach": "#6B4FA0",
    "Other Bus": "#D4901F",
    "Red Bus": "#C1443D",
    "EV Bus": "#2E9B63",
    "BRT": "#2E5FA3",
}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Manrope:wght@400;500;600;700&family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap');

    :root {
        --teal-900: #0B4F4A;
        --teal-700: #0F6F68;
        --teal-600: #12857A;
        --amber-500: #E8A33D;
        --amber-600: #C98826;
        --paper: #FAF6EF;
        --card: #FFFFFF;
        --ink: #22221D;
        --ink-soft: #6B6A61;
        --line: #E7E1D3;
    }

    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    .stApp { background: var(--paper); }

    h1, h2, h3, .price, .route-badge-number {
        font-family: 'Space Grotesk', sans-serif !important;
    }

    /* ── Header: solid teal field with a dotted route-line motif instead
       of a photo+gradient hero — lighter to load, and grounded in the
       idea of a transit line rather than a generic map wash. ── */
    .header {
        background:
            radial-gradient(circle at 8px 8px, rgba(255,255,255,0.14) 1.5px, transparent 1.5px),
            linear-gradient(135deg, var(--teal-900), var(--teal-700));
        background-size: 22px 22px, cover;
        padding: 46px 40px;
        border-radius: 18px;
        text-align: center;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
        border-bottom: 4px solid var(--amber-500);
    }
    .header h1 {
        color: white; font-size: 2.6rem; font-weight: 700; margin: 0;
        letter-spacing: 0.5px; font-family: 'Space Grotesk', sans-serif;
    }
    .header p {
        color: rgba(255,255,255,0.88); font-size: 1rem; margin: 8px 0 0 0;
        font-weight: 500;
    }

    .card {
        background: var(--card);
        padding: 25px;
        border-radius: 14px;
        border: 1px solid var(--line);
        margin-bottom: 20px;
    }

    /* ── Fastest card: styled like a ticket stub, since that's literally
       the subject matter — a dashed perforation instead of a generic
       colored top-border card. ── */
    .route-fastest {
        background: var(--card);
        border-radius: 16px 16px 4px 4px;
        border: 1px solid var(--line);
        padding: 22px 24px 0 24px;
        text-align: center;
        position: relative;
    }
    .route-fastest .stub-bottom {
        border-top: 2px dashed var(--line);
        margin-top: 18px;
        padding: 16px 0 20px 0;
    }

    .route-cheapest {
        background: var(--card);
        border-radius: 4px 14px 14px 4px;
        border: 1px solid var(--line);
        border-left: 5px solid var(--teal-600);
        padding: 20px 22px;
    }

    .petrol-card {
        background: var(--card);
        border-radius: 4px 14px 14px 4px;
        padding: 22px;
        border: 1px solid var(--line);
        border-left: 5px solid var(--amber-500);
        margin-top: 15px;
    }

    .maps-btn-blue, .maps-btn-green, .maps-btn-orange {
        display: inline-block;
        margin: 4px 0 18px 0;
        padding: 9px 22px;
        background: var(--teal-700);
        color: white !important;
        border-radius: 8px;
        text-decoration: none !important;
        font-weight: 600;
        font-size: 0.88rem;
    }

    .stTextInput input, .stTextArea textarea {
        border-radius: 8px !important;
        border: 1.5px solid var(--line) !important;
        padding: 11px !important;
        font-size: 1rem !important;
    }
    .stButton button {
        background: var(--amber-500) !important;
        color: var(--ink) !important;
        border-radius: 8px !important;
        padding: 13px 40px !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        border: none !important;
        width: 100% !important;
        transition: background 0.15s ease;
    }
    .stButton button:hover { background: var(--amber-600) !important; }

    .stSelectbox div[data-baseweb="select"] { cursor: pointer !important; }
    .stSelectbox div[data-baseweb="select"] * { cursor: pointer !important; }

    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1.5px solid var(--line) !important;
        gap: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        font-weight: 600 !important;
        font-size: 0.98rem !important;
        padding: 10px 22px !important;
        color: var(--ink-soft) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--teal-600) !important;
        color: white !important;
    }

    label { color: var(--ink) !important; font-weight: 600 !important; font-size: 0.93rem !important; }
    .stat { font-size: 0.95rem; color: var(--ink-soft); margin: 6px 0; }
    .price { font-size: 1.7rem; font-weight: 700; margin: 8px 0; }

    /* Bus route number shown as a signage-style badge */
    .route-badge {
        display: inline-block;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 0.95rem;
        padding: 3px 12px;
        border-radius: 6px;
        color: white;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(f"""
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
        <p>{t("app_subtitle")}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar: Feedback (always visible, regardless of tab) ───
with st.sidebar:
    st.markdown(f"### {t('feedback_header')}")
    st.caption(t("feedback_caption"))
    fb_text = st.text_area(t("feedback_label"), placeholder=t("feedback_placeholder"), key="fb_text")
    fb_email = st.text_input(t("feedback_email_label"), key="fb_email")
    if st.button(t("feedback_submit")):
        if fb_text.strip():
            try:
                send_feedback_email(fb_text, fb_email, GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                st.success(t("feedback_success"))
            except Exception as e:
                print(f"Feedback email error: {e}")
                st.error(t("feedback_error"))
        else:
            st.warning(t("feedback_empty_warning"))

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    t("tab_route_planner"),
    t("tab_traffic_ai"),
    t("tab_forecast"),
    t("tab_petrol"),
    t("tab_carpool"),
])

# ─── TAB 1 — Route Planner ───
with tab1:
    st.markdown(f"### {t('route_planner_heading')}")
    st.markdown(t("route_planner_subheading"))

    known_stops = sorted({s for r in load_bus_routes() for s in r["stops"]})
    MANUAL_ENTRY_LABEL = t("manual_entry_label")
    location_options = [MANUAL_ENTRY_LABEL] + known_stops

    col1, col2, col3 = st.columns(3)
    with col1:
        start_choice = st.selectbox(t("starting_location_label"), location_options, index=None, key="start_choice",
                                     placeholder=t("select_placeholder"), help=t("location_help"))
        if start_choice == MANUAL_ENTRY_LABEL:
            start = st.text_input(t("type_start_manual"), placeholder=t("placeholder_start"), key="start_manual")
        else:
            start = start_choice or ""
    with col2:
        end_choice = st.selectbox(t("destination_label"), location_options, index=None, key="end_choice",
                                   placeholder=t("select_placeholder"), help=t("location_help"))
        if end_choice == MANUAL_ENTRY_LABEL:
            end = st.text_input(t("type_end_manual"), placeholder=t("placeholder_end"), key="end_manual")
        else:
            end = end_choice or ""
    with col3:
        departure_time_obj = st.time_input(t("departure_time_label"), value=datetime.time(7, 0))
        # Build "H:MM AM/PM" without a leading zero on the hour (matches format
        # the ML model expects) — done manually rather than via strftime's
        # locale-specific %-I flag, since that isn't reliably supported on Windows.
        hour_12 = departure_time_obj.hour % 12 or 12
        period = "AM" if departure_time_obj.hour < 12 else "PM"
        time = f"{hour_12}:{departure_time_obj.minute:02d} {period}"
    st.markdown("<br>", unsafe_allow_html=True)
    find = st.button(t("find_routes_button"))

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
            st.error(t("error_missing_fields"))

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
            with st.spinner(t("finding_routes_spinner")):
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

        traffic_display = {
            "Light": t("traffic_light"),
            "Moderate": t("traffic_moderate"),
            "Heavy": t("traffic_heavy"),
        }

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
                    "Light": ("#2E9B63", "🟢"),
                    "Moderate": ("#C98826", "🟡"),
                    "Heavy": ("#C1443D", "🔴"),
                }
                badge_color, badge_emoji = badge_style.get(traffic_now, ("#999", "⚪"))

                st.markdown(f"""
                <div class='route-fastest'>
                    <h2 style='color:var(--teal-700); margin:0; font-size:1.3rem;'>{t("fastest_card_title")}</h2>
                    <p style='color:var(--ink-soft); margin:5px 0 12px 0; font-size:0.9rem;'>{t("via_fastest_route")}</p>
                    <p class='price' style='color:var(--ink)'>{f['duration']} {t("mins_suffix")}</p>
                    <p class='stat'>📏 {f['distance']} km</p>
                    <p class='stat'>{t("rickshaw_label")}</p>
                    <p class='stat' style='color:var(--teal-700); font-weight:700; font-size:1.1rem'>Rs. {cost}</p>
                    <p class='stat' style='color:{badge_color}; font-weight:700; margin-top:10px;'>{badge_emoji} {traffic_display.get(traffic_now, traffic_now)} {t("traffic_expected")} {s_time}</p>
                    <div class='stub-bottom'>
                        <a href='{link_drive}' target='_blank' class='maps-btn-blue'>{t("open_in_maps")}</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Suggest a better departure time (next few hours) if one exists with lower traffic.
                # Works for ANY custom time now, not just a fixed list of slots.
                def _parse_12h(time_str):
                    time_part, period = time_str.split(" ")
                    h, m = map(int, time_part.split(":"))
                    if period == "AM" and h == 12:
                        h = 0
                    elif period == "PM" and h != 12:
                        h += 12
                    return h, m

                def _format_12h(hour24, minute):
                    h12 = hour24 % 12 or 12
                    suffix = "AM" if hour24 < 12 else "PM"
                    return f"{h12}:{minute:02d} {suffix}"

                traffic_rank = {"Light": 1, "Moderate": 2, "Heavy": 3}
                base_hour, base_minute = _parse_12h(s_time)
                for offset in (1, 2, 3):
                    candidate_hour = (base_hour + offset) % 24
                    candidate_time = _format_12h(candidate_hour, base_minute)
                    candidate_result = predict_traffic(current_day, candidate_time, matched_area, "Clear")
                    if traffic_rank[candidate_result] < traffic_rank[traffic_now]:
                        st.info(t("try_time_suggestion", time=candidate_time, level=traffic_display.get(candidate_result, candidate_result)))
                        break
            else:
                st.markdown(f"""
                <div class='route-fastest'>
                    <h2 style='color:var(--ink-soft); margin:0; font-size:1.3rem;'>{t("fastest_card_title")}</h2>
                    <div class='stub-bottom'>
                        <p style='color:var(--ink-soft); margin:0'>{t("needs_internet")}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"#### {t('bus_route_options_heading')}")

            if not internet_ok:
                if rate_limited:
                    st.warning(t("quota_warning"))
                else:
                    st.warning(t("no_internet_warning"))

            if basic_matches:
                option_labels = [
                    f"{m['route_id']} · {m['category']}" + (t("nearby_stop_suffix") if m.get("match_type") == "proximity" else "")
                    for m in basic_matches
                ]
                chosen_label = st.selectbox(
                    t("found_routes_label", n=len(basic_matches)),
                    option_labels,
                    key="chosen_bus_route",
                )
                chosen_match = basic_matches[option_labels.index(chosen_label)]

                if internet_ok and start_coords and end_coords:
                    enriched, route_rate_limited = None, False
                    try:
                        with st.spinner(t("getting_walk_spinner")):
                            enriched = enrich_journey(chosen_match, start_coords, end_coords, API_KEY)
                    except ApiError as e:
                        if is_quota_or_rate_limit_error(e):
                            route_rate_limited = True
                    except Exception as e:
                        print(f"Enrich journey error: {e}")

                    if enriched:
                        walk1_min = enriched['walk_to_stop']['duration_min']
                        walk2_min = enriched['walk_to_dest']['duration_min']
                        walk1_text = "" if walk1_min <= 1 else f" ({t('walk_suffix', n=walk1_min)})"
                        walk2_text = "" if walk2_min <= 1 else t("then_walk_suffix", n=walk2_min)
                        cat_color = CATEGORY_COLORS.get(enriched['category'], "#12857A")

                        st.markdown(f"""
                        <div class='route-cheapest' style='border-left-color:{cat_color}; margin-top:12px;'>
                            <span class='route-badge' style='background:{cat_color};'>{enriched['route_id']} · {enriched['category']}</span>
                            <p class='stat'>{t("board_at")} <b>{enriched['start_stop']}</b>{walk1_text}</p>
                            <p class='stat'>{t("alight_at")} <b>{enriched['end_stop']}</b>{walk2_text}</p>
                            <p class='stat' style='color:{cat_color}; font-weight:700; font-size:1.05rem'>{t("total_est_time", n=enriched['total_time_min'])}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(f"##### {t('route_map_heading')}")
                        route_map = build_route_map(start_coords, end_coords, enriched)
                        st_folium(route_map, width=700, height=400, key="route_map")
                    else:
                        if route_rate_limited:
                            st.caption(f"{t('server_busy_caption')} **{chosen_match['start_stop']}**, "
                                       f"{t('alight_near').lower()} **{chosen_match['end_stop']}**.")
                        else:
                            st.caption(f"{t('board_near')} **{chosen_match['start_stop']}**, "
                                       f"{t('alight_near').lower()} **{chosen_match['end_stop']}** — {t('no_live_data_caption')}")
                else:
                    cat_color = CATEGORY_COLORS.get(chosen_match['category'], "#12857A")
                    st.markdown(f"""
                    <div class='route-cheapest' style='border-left-color:{cat_color}; margin-top:12px;'>
                        <span class='route-badge' style='background:{cat_color};'>{chosen_match['route_id']} · {chosen_match['category']}</span>
                        <p class='stat'>{t("board_near")} <b>{chosen_match['start_stop']}</b></p>
                        <p class='stat'>{t("alight_near")} <b>{chosen_match['end_stop']}</b></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(t("no_route_found"))

        st.markdown("<br>", unsafe_allow_html=True)
        if internet_ok:
            st.success(t("success_message"))

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
        traffic_color = "#C1443D"
        traffic_emoji = "🔴"
        traffic_msg = "Leave early — heavy traffic ahead!"
    elif traffic_result == "Moderate":
        traffic_color = "#C98826"
        traffic_emoji = "🟡"
        traffic_msg = "Expect some delays on the road!"
    else:
        traffic_color = "#2E9B63"
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
        colors.append("#2E9B63" if result == "Light" else "#C98826" if result == "Moderate" else "#C1443D")

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
        <h3 style='color:#C98826; margin:0 0 15px 0'>⛽ Fuel Summary</h3>
        <p style='font-size:1.1rem; color:#333; margin:8px 0'>📏 Distance: <b>{petrol_distance} km</b></p>
        <p style='font-size:1.1rem; color:#333; margin:8px 0'>🛢️ Fuel Required: <b>{liters_needed} liters</b></p>
        <p style='font-size:1.1rem; color:#333; margin:8px 0'>💰 Per Trip Cost: <b>Rs. {total_cost}</b></p>
        <hr style='border-color:#eee; margin:15px 0'>
        <p style='font-size:1.4rem; color:#C98826; font-weight:900; margin:0'>💸 Monthly Cost: Rs. {monthly_cost}</p>
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