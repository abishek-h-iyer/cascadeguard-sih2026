import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio

from shapely.geometry import box


# =====================================================
# PATHS
# =====================================================

BASE = "../data/raw/nepal_fres/extracted/b6da096000284d5882d13b085b7669ac/data/contents"

CATCHMENT = f"{BASE}/Melamchi_Khola_Catchment.kml"

THALWEG = f"{BASE}/Melamchi_Khola_River_Thalweg_Oct2021.kml"

PRE2014 = f"{BASE}/Landslide_before_Nov2014.kml"

LS_2014_2020 = (
    f"{BASE}/Landslide_and_Fluvial_Erosion_Nov2014-Nov2020.kml"
)

EVENT_IMPACT = (
    f"{BASE}/Landslide_and_Fluvial_Erosion_Nov2020-Oct2021.kml"
)

ZONES = "../data/processed/melamchi_zones_ml.gpkg"

DEM = "../data/processed/melamchi_dem.tif"
SLOPE = "../data/processed/melamchi_slope.tif"

OUTPUT = "../data/processed/spatial_training_data.csv"


CRS = "EPSG:32645"

# 250 m x 250 m grid
GRID_SIZE = 250


# =====================================================
# LOAD GIS DATA
# =====================================================

print("Loading GIS layers...")

catchment = gpd.read_file(CATCHMENT).to_crs(CRS)
zones = gpd.read_file(ZONES).to_crs(CRS)

thalweg = gpd.read_file(THALWEG).to_crs(CRS)

old1 = gpd.read_file(PRE2014).to_crs(CRS)
old2 = gpd.read_file(LS_2014_2020).to_crs(CRS)

impact = gpd.read_file(EVENT_IMPACT).to_crs(CRS)


# Repair geometry
old1.geometry = old1.geometry.make_valid()
old2.geometry = old2.geometry.make_valid()
impact.geometry = impact.geometry.make_valid()
catchment.geometry = catchment.geometry.make_valid()


# =====================================================
# CREATE 250m GRID
# =====================================================

print("Creating spatial grid...")

minx, miny, maxx, maxy = catchment.total_bounds

cells = []
cell_id = 0

for x in np.arange(minx, maxx, GRID_SIZE):
    for y in np.arange(miny, maxy, GRID_SIZE):

        cells.append({
            "cell_id": cell_id,
            "geometry": box(
                x,
                y,
                x + GRID_SIZE,
                y + GRID_SIZE
            )
        })

        cell_id += 1


grid = gpd.GeoDataFrame(
    cells,
    crs=CRS
)


# Clip grid to catchment
grid = gpd.overlay(
    grid,
    catchment[["geometry"]],
    how="intersection"
)

grid["cell_area_m2"] = grid.geometry.area

# Remove tiny edge fragments
grid = grid[
    grid["cell_area_m2"] > 10000
].copy()

print("Grid cells:", len(grid))


# =====================================================
# ASSIGN EACH CELL TO OUR MEL_Zxx ZONE
# =====================================================

print("Assigning zones...")

points = grid[
    ["cell_id", "geometry"]
].copy()

points["geometry"] = (
    points.geometry.representative_point()
)

zone_lookup = gpd.sjoin(
    points,
    zones[["zone_id", "geometry"]],
    how="left",
    predicate="within"
)

grid = grid.merge(
    zone_lookup[
        ["cell_id", "zone_id"]
    ],
    on="cell_id",
    how="left"
)


# =====================================================
# CREATE UNION GEOMETRIES
# =====================================================

print("Preparing historical geometry...")

historical = gpd.GeoDataFrame(
    pd.concat(
        [
            old1[["geometry"]],
            old2[["geometry"]]
        ],
        ignore_index=True
    ),
    crs=CRS
)

historical_union = historical.geometry.union_all()

impact_union = impact.geometry.union_all()

river_union = thalweg.geometry.union_all()


# =====================================================
# CENTROIDS / REPRESENTATIVE POINTS
# =====================================================

grid_points = grid.geometry.representative_point()


# =====================================================
# DISTANCE TO RIVER
# =====================================================

print("Calculating river distance...")

grid["distance_to_river_m"] = (
    grid_points.distance(river_union)
)


# =====================================================
# HISTORICAL LANDSLIDE EXPOSURE
# =====================================================

print("Calculating pre-2021 landslide exposure...")

historical_intersection = (
    grid.geometry.intersection(
        historical_union
    )
)

grid["pre2021_landslide_pct"] = (
    historical_intersection.area
    /
    grid["cell_area_m2"]
    * 100
)


# =====================================================
# DISTANCE TO PREVIOUS LANDSLIDE
# =====================================================

grid["distance_to_old_landslide_m"] = (
    grid_points.distance(
        historical_union
    )
)


# =====================================================
# REAL 2021 IMPACT TARGET
# =====================================================

print("Creating real event-impact labels...")

impact_intersection = (
    grid.geometry.intersection(
        impact_union
    )
)

grid["event_impact_pct"] = (
    impact_intersection.area
    /
    grid["cell_area_m2"]
    * 100
)

# Cell counts as impacted if >= 1% of cell
# was mapped as landslide/fluvial erosion
grid["impacted_2021"] = (
    grid["event_impact_pct"] >= 1.0
).astype(int)


# =====================================================
# SAMPLE DEM + SLOPE
# =====================================================

coordinates = [
    (point.x, point.y)
    for point in grid_points
]


print("Sampling elevation...")

with rasterio.open(DEM) as src:

    values = [
        value[0]
        for value in src.sample(coordinates)
    ]

    grid["elevation"] = values

    dem_nodata = src.nodata


print("Sampling slope...")

with rasterio.open(SLOPE) as src:

    values = [
        value[0]
        for value in src.sample(coordinates)
    ]

    grid["slope"] = values

    slope_nodata = src.nodata


# =====================================================
# CLEAN
# =====================================================

if dem_nodata is not None:
    grid.loc[
        grid["elevation"] == dem_nodata,
        "elevation"
    ] = np.nan

if slope_nodata is not None:
    grid.loc[
        grid["slope"] == slope_nodata,
        "slope"
    ] = np.nan


grid = grid.dropna(
    subset=[
        "zone_id",
        "elevation",
        "slope"
    ]
).copy()


# =====================================================
# EXPORT ML TABLE
# =====================================================

columns = [
    "cell_id",
    "zone_id",

    "elevation",
    "slope",

    "distance_to_river_m",

    "pre2021_landslide_pct",
    "distance_to_old_landslide_m",

    "event_impact_pct",
    "impacted_2021"
]

dataset = grid[columns].copy()

dataset.to_csv(
    OUTPUT,
    index=False
)


print("\n================================")
print("SPATIAL ML DATASET READY")
print("================================")

print("Samples:", len(dataset))
print("Zones:", dataset["zone_id"].nunique())

print("\nTarget:")
print(
    dataset["impacted_2021"]
    .value_counts()
)

print("\nTarget percentage:")
print(
    dataset["impacted_2021"]
    .value_counts(normalize=True)
    * 100
)

print("\nFeatures summary:")
print(
    dataset[
        [
            "elevation",
            "slope",
            "distance_to_river_m",
            "pre2021_landslide_pct"
        ]
    ].describe()
)

print("\nSaved:")
print(OUTPUT)