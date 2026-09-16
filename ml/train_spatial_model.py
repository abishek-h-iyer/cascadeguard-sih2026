import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score
)

from xgboost import XGBClassifier


DATA_FILE = "../data/processed/spatial_training_data.csv"

RF_MODEL_FILE = "../models/spatial_random_forest.joblib"
XGB_MODEL_FILE = "../models/spatial_xgboost.json"

ZONE_OUTPUT = "../data/processed/zone_susceptibility.csv"


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
groups = df["zone_id"]

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.25,
    random_state=42
)

train_idx, test_idx = next(
    splitter.split(X, y, groups)
)

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]

y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]

train_zones = sorted(
    df.iloc[train_idx]["zone_id"].unique()
)

test_zones = sorted(
    df.iloc[test_idx]["zone_id"].unique()
)

negative = (y_train == 0).sum()
positive = (y_train == 1).sum()

scale_pos_weight = negative / positive


print("\nTRAIN ZONES:")
print(train_zones)

print("\nTEST ZONES:")
print(test_zones)

print("\nTRAIN SAMPLES:", len(X_train))
print("TEST SAMPLES:", len(X_test))

print("\nTRAIN POSITIVES:", positive)
print("TRAIN NEGATIVES:", negative)

print("\nscale_pos_weight:", scale_pos_weight)


rf = RandomForestClassifier(
    n_estimators=400,
    max_depth=12,
    min_samples_leaf=4,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

rf.fit(
    X_train,
    y_train
)

rf_prob = rf.predict_proba(X_test)[:, 1]
rf_pred = (rf_prob >= 0.5).astype(int)


xgb = XGBClassifier(
    n_estimators=500,
    max_depth=5,
    learning_rate=0.04,
    subsample=0.85,
    colsample_bytree=0.85,
    min_child_weight=3,
    reg_lambda=1.5,
    scale_pos_weight=scale_pos_weight,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42,
    n_jobs=-1
)

xgb.fit(
    X_train,
    y_train
)

xgb_prob = xgb.predict_proba(X_test)[:, 1]
xgb_pred = (xgb_prob >= 0.5).astype(int)


def evaluate(name, y_true, pred, prob):

    print("\n================================")
    print(name)
    print("================================")

    print("\nConfusion Matrix:")
    print(
        confusion_matrix(
            y_true,
            pred
        )
    )

    print("\nClassification Report:")
    print(
        classification_report(
            y_true,
            pred,
            digits=4,
            zero_division=0
        )
    )

    print(
        "Balanced Accuracy:",
        balanced_accuracy_score(
            y_true,
            pred
        )
    )

    print(
        "Precision:",
        precision_score(
            y_true,
            pred,
            zero_division=0
        )
    )

    print(
        "Recall:",
        recall_score(
            y_true,
            pred,
            zero_division=0
        )
    )

    print(
        "F1:",
        f1_score(
            y_true,
            pred,
            zero_division=0
        )
    )

    print(
        "ROC-AUC:",
        roc_auc_score(
            y_true,
            prob
        )
    )

    print(
        "PR-AUC:",
        average_precision_score(
            y_true,
            prob
        )
    )


evaluate(
    "RANDOM FOREST",
    y_test,
    rf_pred,
    rf_prob
)

evaluate(
    "XGBOOST",
    y_test,
    xgb_pred,
    xgb_prob
)


importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": xgb.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

print("\n================================")
print("XGBOOST FEATURE IMPORTANCE")
print("================================")

print(
    importance.to_string(
        index=False
    )
)


final_xgb = XGBClassifier(
    n_estimators=500,
    max_depth=5,
    learning_rate=0.04,
    subsample=0.85,
    colsample_bytree=0.85,
    min_child_weight=3,
    reg_lambda=1.5,
    scale_pos_weight=(y == 0).sum() / (y == 1).sum(),
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42,
    n_jobs=-1
)

final_xgb.fit(
    X,
    y
)

df["susceptibility_probability"] = (
    final_xgb.predict_proba(X)[:, 1]
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

zone_risk = zone_risk.sort_values(
    "zone_id"
)

joblib.dump(
    rf,
    RF_MODEL_FILE
)

final_xgb.save_model(
    XGB_MODEL_FILE
)

zone_risk.to_csv(
    ZONE_OUTPUT,
    index=False
)

importance.to_csv(
    "../data/processed/spatial_feature_importance.csv",
    index=False
)

print("\n================================")
print("ZONE SUSCEPTIBILITY")
print("================================")

print(
    zone_risk.to_string(
        index=False
    )
)

print("\nSaved:")
print(XGB_MODEL_FILE)
print(ZONE_OUTPUT)