import pandas as pd

path = "../data/processed/zone_static_features.csv"

df = pd.read_csv(path)

print("\n============================")
print("ZONE STATIC FEATURES")
print("============================")

print("\nShape:")
print(df.shape)

print("\nColumns:")
for col in df.columns:
    print("-", col)

print("\nData:")
print(df.to_string(index=False))

print("\nMissing values:")
print(df.isnull().sum())

print("\nData types:")
print(df.dtypes)

print("\nNumeric summary:")
print(df.describe())