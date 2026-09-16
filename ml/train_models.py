import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score
)

from xgboost import XGBClassifier


DATA_FILE = "../data/processed/training_data.csv"

RF_MODEL_FILE = "../models/random_forest.joblib"
XGB_MODEL_FILE = "../models/xgboost_model.json"


FEATURES = [
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

TARGET = "event_window"


print("Loading dataset...")

df = pd.read_csv(DATA_FILE)

train = df[df["dataset_split"] == "train"].copy()
test = df[df["dataset_split"] == "test"].copy()

X_train = train[FEATURES]
y_train = train[TARGET]

X_test = test[FEATURES]
y_test = test[TARGET]


print("\nTRAIN:")
print(X_train.shape)

print("\nTEST:")
print(X_test.shape)


# ---------------------------------------------------
# CLASS IMBALANCE
# ---------------------------------------------------

negative = (y_train == 0).sum()
positive = (y_train == 1).sum()

scale_pos_weight = negative / positive

print("\nPositive samples:", positive)
print("Negative samples:", negative)
print("scale_pos_weight:", scale_pos_weight)


# ===================================================
# RANDOM FOREST
# ===================================================

print("\n================================")
print("TRAINING RANDOM FOREST")
print("================================")

rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_leaf=3,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

rf.fit(X_train, y_train)

rf_prob = rf.predict_proba(X_test)[:, 1]
rf_pred = (rf_prob >= 0.5).astype(int)


# ===================================================
# XGBOOST
# ===================================================

print("\n================================")
print("TRAINING XGBOOST")
print("================================")

xgb = XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,

    subsample=0.8,
    colsample_bytree=0.8,

    scale_pos_weight=scale_pos_weight,

    objective="binary:logistic",
    eval_metric="logloss",

    random_state=42,
    n_jobs=-1
)

xgb.fit(X_train, y_train)

xgb_prob = xgb.predict_proba(X_test)[:, 1]
xgb_pred = (xgb_prob >= 0.5).astype(int)


# ===================================================
# EVALUATION FUNCTION
# ===================================================

def evaluate_model(name, y_true, prediction, probability):

    print("\n================================")
    print(name)
    print("================================")

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_true, prediction))

    print("\nClassification Report:")
    print(
        classification_report(
            y_true,
            prediction,
            digits=4
        )
    )

    print("Balanced accuracy:",
          balanced_accuracy_score(y_true, prediction))

    print("Precision:",
          precision_score(y_true, prediction, zero_division=0))

    print("Recall:",
          recall_score(y_true, prediction, zero_division=0))

    print("F1:",
          f1_score(y_true, prediction, zero_division=0))

    print("ROC-AUC:",
          roc_auc_score(y_true, probability))

    print("PR-AUC:",
          average_precision_score(y_true, probability))


evaluate_model(
    "RANDOM FOREST",
    y_test,
    rf_pred,
    rf_prob
)

evaluate_model(
    "XGBOOST",
    y_test,
    xgb_pred,
    xgb_prob
)


# ===================================================
# FEATURE IMPORTANCE
# ===================================================

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

print(importance.to_string(index=False))

importance.to_csv(
    "../data/processed/xgb_feature_importance.csv",
    index=False
)


# ===================================================
# SAVE MODELS
# ===================================================

joblib.dump(
    rf,
    RF_MODEL_FILE
)

xgb.save_model(
    XGB_MODEL_FILE
)

print("\nModels saved:")
print(RF_MODEL_FILE)
print(XGB_MODEL_FILE)