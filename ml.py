import pickle
import streamlit as st

@st.cache_resource
def load_model():
    with open('traffic_model.pkl', 'rb') as f:
        traffic_model = pickle.load(f)
    with open('model_metadata.pkl', 'rb') as f:
        metadata = pickle.load(f)
    return traffic_model, metadata

def convert_time_to_hour(time_str):
    try:
        time_part, period = time_str.split(" ")
        hour = int(time_part.split(":")[0])
        if period == "AM":
            if hour == 12:
                hour = 0
        elif period == "PM":
            if hour != 12:
                hour += 12
        return hour
    except Exception as e:
        print(f"Time conversion error: {e}")
        return 8

def predict_traffic(day, time_str, area, weather):
    try:
        traffic_model, metadata = load_model()
        days_list = metadata['days']
        areas_list = metadata['areas']
        weather_list = metadata['weather']
        labels = metadata['labels']

        hour = convert_time_to_hour(time_str)
        day_num = days_list.index(day)
        area_num = areas_list.index(area) if area in areas_list else 0
        weather_num = weather_list.index(weather)
        prediction = traffic_model.predict([[day_num, hour, area_num, weather_num]])[0]
        return labels[prediction]
    except Exception as e:
        print(f"ML Error: {e}")
        return "Moderate"