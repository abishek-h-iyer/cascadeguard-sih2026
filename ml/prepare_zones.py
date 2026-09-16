import geopandas as gpd
import pandas as pd

# Our polygon layer with geometry
GPKG_PATH = "../data/processed/melamchi_zones_ml.gpkg"

gdf = gpd.read_file(GPKG_PATH)

print("Original CRS:", gdf.crs)
print("Zones:", len(gdf))

# Make sure the zones are ordered nicely
gdf = gdf.sort_values("zone_id").reset_index(drop=True)

# Calculate centroid while still in projected CRS (metres)
centroids = gdf.geometry.centroid

centroid_gdf = gpd.GeoDataFrame(
    gdf[["zone_id"]].copy(),
    geometry=centroids,
    crs=gdf.crs
)

# Convert coordinates to latitude / longitude
centroid_gdf = centroid_gdf.to_crs("EPSG:4326")

centroid_gdf["longitude"] = centroid_gdf.geometry.x
centroid_gdf["latitude"] = centroid_gdf.geometry.y

output = centroid_gdf[
    ["zone_id", "latitude", "longitude"]
]

print("\nZONE COORDINATES")
print(output.to_string(index=False))

output.to_csv(
    "../data/processed/zone_coordinates.csv",
    index=False
)

print("\nSaved: data/processed/zone_coordinates.csv")