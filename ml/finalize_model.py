import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier


DATA_FILE = "../data/processed/spatial_training_data.csv"

MODEL_FILE = "../models/spatial_random_forest_final.joblib"
ZONE_FILE = "../data/processed/zone_susceptibility_final.csv"
CELL_FILE = "../data/processed/cell_susceptibility_final.csv"


FEATURES = [
    "elevation",
    "slope",
    "distance_to_river_m",
    "pre2021_landslide_pct",
    "distance_to_old_landslide_m"
]

TARGET = "impacted_2021"


df = pd.read_csv(DATA_FILE)

X = df[FEATURES]
y = df[TARGET]


model = RandomForestClassifier(
    n_estimators=500,
    max_depth=12,
    min_samples_leaf=4,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

print("Training final Random Forest...")

model.fit(X, y)

df["susceptibility_probability"] = (
    model.predict_proba(X)[:, 1]
)


zone_risk = (
    df.groupby("zone_id")
    .agg(
        mean_susceptibility=(
            "susceptibility_probability",
            "mean"
        ),
        max_susceptibility=(
            "susceptibility_probability",
            "max"
        ),
        impacted_cells=(
            "impacted_2021",
            "sum"
        ),
        total_cells=(
            "cell_id",
            "count"
        )
    )
    .reset_index()
)


zone_risk["historical_impact_rate"] = (
    zone_risk["impacted_cells"]
    /
    zone_risk["total_cells"]
)


def classify(value):

    if value >= 0.65:
        return "HIGH"

    if value >= 0.35:
        return "MODERATE"

    return "LOW"


zone_risk["susceptibility_class"] = (
    zone_risk["mean_susceptibility"]
    .apply(classify)
)


zone_risk = zone_risk.sort_values(
    "zone_id"
)


joblib.dump(
    model,
    MODEL_FILE
)


df[
    [
        "cell_id",
        "zone_id",
        "susceptibility_probability"
    ]
].to_csv(
    CELL_FILE,
    index=False
)


zone_risk.to_csv(
    ZONE_FILE,
    index=False
)


print("\n================================")
print("FINAL RANDOM FOREST READY")
print("================================")

print(
    zone_risk.to_string(
        index=False
    )
)

print("\nSaved model:")
print(MODEL_FILE)

print("\nSaved zone susceptibility:")
print(ZONE_FILE)

print("\nSaved cell susceptibility:")
print(CELL_FILE)