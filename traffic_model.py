import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle

# Karachi Traffic Dataset banana
np.random.seed(42)
n_samples = 5000

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
areas = ['Saddar', 'Gulshan', 'Clifton', 'Korangi', 'Lyari', 'Nazimabad', 'Malir', 'DHA', 'North Karachi', 'Orangi']
weather = ['Clear', 'Cloudy', 'Rainy']

data = []

for _ in range(n_samples):
    day = np.random.choice(days)
    hour = np.random.randint(0, 24)
    area = np.random.choice(areas)
    rain = np.random.choice(weather, p=[0.6, 0.25, 0.15])

    # Karachi traffic logic
    is_weekday = day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    is_morning_rush = 7 <= hour <= 10
    is_evening_rush = 16 <= hour <= 20
    is_night = hour >= 23 or hour <= 5
    is_rainy = rain == 'Rainy'
    is_busy_area = area in ['Saddar', 'Clifton', 'Gulshan', 'Nazimabad']

    # Traffic level calculate karo
    score = 0
    if is_weekday: score += 3
    if is_morning_rush: score += 4
    if is_evening_rush: score += 4
    if is_rainy: score += 3
    if is_busy_area: score += 2
    if is_night: score -= 4
    if day == 'Sunday': score -= 3

    if score <= 2:
        traffic = 'Light'
    elif score <= 5:
        traffic = 'Moderate'
    else:
        traffic = 'Heavy'

    data.append([day, hour, area, rain, traffic])

# DataFrame
df = pd.DataFrame(data, columns=['day', 'hour', 'area', 'weather', 'traffic'])

# Encoding
df['day_num'] = pd.Categorical(df['day'], categories=days).codes
df['area_num'] = pd.Categorical(df['area'], categories=areas).codes
df['weather_num'] = pd.Categorical(df['weather'], categories=weather).codes
df['traffic_num'] = pd.Categorical(df['traffic'], categories=['Light', 'Moderate', 'Heavy']).codes

# Features & Target
X = df[['day_num', 'hour', 'area_num', 'weather_num']]
y = df['traffic_num']

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Model Train
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Accuracy
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"✅ Model Trained! Accuracy: {round(acc*100, 2)}%")

# Model Save
with open('traffic_model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Metadata Save
metadata = {
    'days': days,
    'areas': areas,
    'weather': weather,
    'labels': ['Light', 'Moderate', 'Heavy']
}

with open('model_metadata.pkl', 'wb') as f:
    pickle.dump(metadata, f)

print("✅ Model saved — traffic_model.pkl")
print("✅ Metadata saved — model_metadata.pkl")