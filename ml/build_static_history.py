import geopandas as gpd
import pandas as pd

BASE = "../data/raw/nepal_fres/extracted/b6da096000284d5882d13b085b7669ac/data/contents"

ZONES = "../data/processed/melamchi_zones_ml.gpkg"

OLD_1 = f"{BASE}/Landslide_before_Nov2014.kml"
OLD_2 = f"{BASE}/Landslide_and_Fluvial_Erosion_Nov2014-Nov2020.kml"

STATIC_CSV = "../data/processed/zone_static_features.csv"
OUTPUT = "../data/processed/zone_static_features_clean.csv"

print("Loading zones...")
zones = gpd.read_file(ZONES)

zones = zones[["zone_id", "geometry"]].copy()
zones = zones.to_crs("EPSG:32645")

print("Loading historical landslides...")
ls1 = gpd.read_file(OLD_1).to_crs(zones.crs)
ls2 = gpd.read_file(OLD_2).to_crs(zones.crs)

# Repair geometry if required
ls1.geometry = ls1.geometry.make_valid()
ls2.geometry = ls2.geometry.make_valid()

historical = gpd.GeoDataFrame(
    pd.concat(
        [
            ls1[["geometry"]],
            ls2[["geometry"]]
        ],
        ignore_index=True
    ),
    crs=zones.crs
)

# Merge overlapping historical polygons so area isn't double counted
historical["group"] = 1
historical = historical.dissolve(by="group").reset_index()

print("Intersecting with zones...")

intersections = gpd.overlay(
    zones,
    historical[["geometry"]],
    how="intersection"
)

intersections["pre2021_ls_area"] = intersections.geometry.area

stats = (
    intersections
    .groupby("zone_id")["pre2021_ls_area"]
    .sum()
    .reset_index()
)

zones["zone_area_check"] = zones.geometry.area

stats = zones[
    ["zone_id", "zone_area_check"]
].merge(
    stats,
    on="zone_id",
    how="left"
)

stats["pre2021_ls_area"] = stats["pre2021_ls_area"].fillna(0)

stats["pre2021_landslide_pct"] = (
    100 *
    stats["pre2021_ls_area"] /
    stats["zone_area_check"]
)

static = pd.read_csv(STATIC_CSV)

static = static.merge(
    stats[
        [
            "zone_id",
            "pre2021_landslide_pct"
        ]
    ],
    on="zone_id",
    how="left"
)

# landslide_pct includes the 2021 event, so don't use it as predictor
if "landslide_pct" in static.columns:
    static = static.drop(columns=["landslide_pct"])

static.to_csv(OUTPUT, index=False)

print("\n==========================")
print("STATIC FEATURES READY")
print("==========================")

print(
    static[
        [
            "zone_id",
            "elev_mean",
            "slope_mean",
            "pre2021_landslide_pct"
        ]
    ].to_string(index=False)
)

print("\nSaved:", OUTPUT)