import geopandas as gpd
import rasterio
import pandas as pd
import numpy as np
from pathlib import Path
from shapely.geometry import LineString, MultiLineString

ROOT = Path(__file__).resolve().parents[1]

ZONES_PATH = ROOT / "data" / "processed" / "melamchi_zones_ml.gpkg"

THALWEG_PATH = (
    ROOT
    / "data"
    / "raw"
    / "nepal_fres"
    / "extracted"
    / "b6da096000284d5882d13b085b7669ac"
    / "data"
    / "contents"
    / "Melamchi_Khola_River_Thalweg_Oct2021.kml"
)

DEM_PATH = ROOT / "data" / "processed" / "melamchi_dem_utm.tif"

OUTPUT_PATH = ROOT / "data" / "processed" / "eta_reach_parameters.csv"


def sample_line(line, spacing=30):
    if line.length == 0:
        return []

    distances = np.arange(0, line.length, spacing)

    if len(distances) == 0 or distances[-1] != line.length:
        distances = np.append(distances, line.length)

    return [line.interpolate(distance) for distance in distances]


zones = gpd.read_file(ZONES_PATH)

thalweg = gpd.read_file(
    THALWEG_PATH,
    driver="KML"
)

zones = zones.to_crs("EPSG:32645")
thalweg = thalweg.to_crs("EPSG:32645")

thalweg_geometry = thalweg.geometry.unary_union

results = []

with rasterio.open(DEM_PATH) as dem:

    for _, zone in zones.iterrows():

        zone_id = zone["zone_id"]

        river_segment = thalweg_geometry.intersection(
            zone.geometry
        )

        if river_segment.is_empty:
            print(f"{zone_id}: no river segment found")
            continue

        if isinstance(river_segment, MultiLineString):
            segments = list(river_segment.geoms)
        elif isinstance(river_segment, LineString):
            segments = [river_segment]
        else:
            segments = [
                geom
                for geom in getattr(
                    river_segment,
                    "geoms",
                    []
                )
                if isinstance(geom, LineString)
            ]

        reach_length = sum(
            segment.length
            for segment in segments
        )

        points = []

        for segment in segments:
            points.extend(
                sample_line(segment)
            )

        coordinates = [
            (point.x, point.y)
            for point in points
        ]

        elevation_values = []

        for value in dem.sample(coordinates):
            elevation = float(value[0])

            if (
                elevation != dem.nodata
                and np.isfinite(elevation)
            ):
                elevation_values.append(
                    elevation
                )

        if not elevation_values:
            print(f"{zone_id}: no DEM samples")
            continue

        max_elevation = max(elevation_values)
        min_elevation = min(elevation_values)

        elevation_drop = (
            max_elevation
            - min_elevation
        )

        slope = (
            elevation_drop / reach_length
            if reach_length > 0
            else 0
        )

        results.append(
            {
                "zone_id": zone_id,
                "reach_length_m": round(
                    reach_length,
                    2
                ),
                "elevation_high_m": round(
                    max_elevation,
                    2
                ),
                "elevation_low_m": round(
                    min_elevation,
                    2
                ),
                "elevation_drop_m": round(
                    elevation_drop,
                    2
                ),
                "reach_slope": round(
                    slope,
                    6
                )
            }
        )


df = pd.DataFrame(results)

df["zone_number"] = (
    df["zone_id"]
    .str.extract(r"(\d+)")
    .astype(int)
)

df = df.sort_values(
    "zone_number"
)

df = df.drop(
    columns=["zone_number"]
)

df.to_csv(
    OUTPUT_PATH,
    index=False
)

print()
print("=" * 70)
print("CASCADEGUARD ETA REACH PARAMETERS")
print("=" * 70)
print(df.to_string(index=False))
print()
print(
    f"Total river length: "
    f"{df['reach_length_m'].sum()/1000:.2f} km"
)
print()
print(
    f"Saved to: {OUTPUT_PATH}"
)