import pandas as pd
import numpy as np

WEATHER_FILE = "../data/processed/weather_2021.csv"
STATIC_FILE = "../data/processed/zone_static_features_clean.csv"

OUTPUT_FILE = "../data/processed/training_data.csv"

print("Loading data...")

weather = pd.read_csv(WEATHER_FILE)
static = pd.read_csv(STATIC_FILE)

weather["timestamp"] = pd.to_datetime(weather["timestamp"])

weather = weather.sort_values(
    ["zone_id", "timestamp"]
).reset_index(drop=True)

# ---------------------------------------------------
# 1. RAINFALL FEATURES
# ---------------------------------------------------

print("Creating rainfall features...")

weather["rain_1h"] = weather["precipitation"]

for hours in [3, 6, 12, 24, 48, 72, 144]:

    weather[f"rain_{hours}h"] = (
        weather
        .groupby("zone_id")["precipitation"]
        .transform(
            lambda x: x.rolling(
                window=hours,
                min_periods=hours
            ).sum()
        )
    )

# ---------------------------------------------------
# 2. SOIL MOISTURE FEATURES
# ---------------------------------------------------

print("Creating soil moisture features...")

weather["soil_moisture"] = (
    weather["soil_moisture_0_7"]
    +
    weather["soil_moisture_7_28"]
) / 2

for hours in [3, 6, 12, 24]:

    weather[f"soil_change_{hours}h"] = (
        weather
        .groupby("zone_id")["soil_moisture"]
        .diff(hours)
    )

# ---------------------------------------------------
# 3. MERGE STATIC GIS FEATURES
# ---------------------------------------------------

print("Adding GIS features...")

df = weather.merge(
    static,
    on="zone_id",
    how="left"
)

# ---------------------------------------------------
# 4. CREATE HISTORICAL EVENT LABEL
# ---------------------------------------------------

# Documented Melamchi high-impact dates
EVENT_DATES = {
    pd.Timestamp("2021-06-15").date(),
    pd.Timestamp("2021-07-31").date()
}

df["event_window"] = (
    df["timestamp"]
    .dt.date
    .isin(EVENT_DATES)
    .astype(int)
)

# ---------------------------------------------------
# 5. REMOVE INITIAL ROWS WITHOUT ENOUGH HISTORY
# ---------------------------------------------------

required_features = [
    "rain_1h",
    "rain_3h",
    "rain_6h",
    "rain_12h",
    "rain_24h",
    "rain_48h",
    "rain_72h",
    "rain_144h",

    "soil_moisture",
    "soil_change_3h",
    "soil_change_6h",
    "soil_change_12h",
    "soil_change_24h",

    "elev_mean",
    "slope_mean",
    "slope_max",
    "pre2021_landslide_pct"
]

df = df.dropna(subset=required_features).reset_index(drop=True)

# ---------------------------------------------------
# 6. TIME-BASED TRAIN / TEST SPLIT
# ---------------------------------------------------

# Train sees the June event.
# July event remains unseen for evaluation.

split_date = pd.Timestamp("2021-07-15 00:00:00")

df["dataset_split"] = np.where(
    df["timestamp"] < split_date,
    "train",
    "test"
)

# ---------------------------------------------------
# 7. SAVE
# ---------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n================================")
print("TRAINING DATASET READY")
print("================================")

print("Rows:", len(df))
print("Zones:", df["zone_id"].nunique())

print("\nDate range:")
print(df["timestamp"].min(), "→", df["timestamp"].max())

print("\nTarget distribution:")
print(df["event_window"].value_counts())

print("\nTrain target distribution:")
print(
    df[df["dataset_split"] == "train"]
    ["event_window"]
    .value_counts()
)

print("\nTest target distribution:")
print(
    df[df["dataset_split"] == "test"]
    ["event_window"]
    .value_counts()
)

print("\nFeatures:")
for feature in required_features:
    print("-", feature)

print("\nSaved:")
print(OUTPUT_FILE)