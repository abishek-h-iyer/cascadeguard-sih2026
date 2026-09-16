import pandas as pd
import requests
import time

COORD_FILE = "../data/processed/zone_coordinates.csv"
OUTPUT_FILE = "../data/processed/weather_2021.csv"

START_DATE = "2021-05-15"
END_DATE = "2021-08-15"

zones = pd.read_csv(COORD_FILE)

all_rows = []

for _, zone in zones.iterrows():

    zone_id = zone["zone_id"]
    lat = zone["latitude"]
    lon = zone["longitude"]

    print(f"Downloading {zone_id}...")

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,

        "hourly": ",".join([
            "precipitation",
            "soil_moisture_0_to_7cm",
            "soil_moisture_7_to_28cm"
        ]),

        "timezone": "Asia/Kathmandu"
    }

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()["hourly"]

    df = pd.DataFrame({
        "timestamp": data["time"],
        "precipitation": data["precipitation"],
        "soil_moisture_0_7": data["soil_moisture_0_to_7cm"],
        "soil_moisture_7_28": data["soil_moisture_7_to_28cm"]
    })

    df["zone_id"] = zone_id

    all_rows.append(df)

    time.sleep(0.5)

weather = pd.concat(all_rows, ignore_index=True)

weather.to_csv(OUTPUT_FILE, index=False)

print("\n============================")
print("DOWNLOAD COMPLETE")
print("============================")
print("Rows:", len(weather))
print("Zones:", weather["zone_id"].nunique())
print("Start:", weather["timestamp"].min())
print("End:", weather["timestamp"].max())

print("\nMissing values:")
print(weather.isnull().sum())

print("\nSaved:")
print(OUTPUT_FILE)