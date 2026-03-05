# prepare_station_coverage.py
# Build station coverage layer for the LFB Streamlit dashboard
# Run once locally (or Colab) to generate Parquet outputs used in Streamlit.

import os
import re
import pandas as pd
import geopandas as gpd


# -----------------------------
# 1) CONFIG
# -----------------------------

# Inputs
PATH_STATIONS_ODI   = "Data/raw/lfb_stations_odI.csv"
PATH_BOROUGHS_SHP   = "Data/london_boroughs/London_Borough_Excluding_MHW.shp"
PATH_MASTER_PARQUET = "Data/lfb_streamlit.parquet"

# Outputs
OUT_STATIONS_PARQUET = "Data/processed/stations_london_cov.parquet"
OUT_FLOWS_PARQUET    = "Data/processed/station_borough_flows.parquet"

# Column names (master parquet)
COL_STATION_NAME   = "DeployedFromStation_Name"
COL_DEPLOYED_FROM  = "DeployedFromLocation"
COL_BOROUGH        = "IncGeo_BoroughName"
COL_TRAVEL_SECONDS = "TravelTimeSeconds"
COL_INCIDENT_ID    = "IncidentNumber"
COL_PUMP_ORDER     = "PumpOrder"

# Borough name column in shapefile
BOROUGH_NAME_COL = "NAME"

# Toggle flows export (station -> borough centroids)
EXPORT_FLOWS = True


# -----------------------------
# 2) HELPERS
# -----------------------------

def norm_station_name(x: str) -> str:
    """
    Normalize station names for joining:
    - lowercase
    - remove punctuation
    - remove common suffixes like "fire station"
    """
    if pd.isna(x):
        return ""
    x = str(x).strip().lower()

    # remove typical suffixes / phrases first
    x = re.sub(r"\bfire station\b", "", x)
    x = re.sub(r"\bfire brigade\b", "", x)
    x = re.sub(r"\bfire and rescue\b.*", "", x)

    # remove punctuation, collapse whitespace
    x = re.sub(r"[^a-z0-9\s]", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x


# -----------------------------
# 3) LOAD MASTER (INCIDENT-LEVEL)
# -----------------------------

print("Loading master dataset...")
df = pd.read_parquet(PATH_MASTER_PARQUET)

# Keep first pump only (incident-level), consistent with dashboard
df = (
    df.sort_values(COL_PUMP_ORDER)
      .drop_duplicates(COL_INCIDENT_ID)
      .copy()
)

print(f"First pump incidents loaded: {len(df):,}")

required_cols = [COL_STATION_NAME, COL_DEPLOYED_FROM, COL_TRAVEL_SECONDS, COL_INCIDENT_ID]
if EXPORT_FLOWS:
    required_cols.append(COL_BOROUGH)

missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in master parquet: {missing}")


# -----------------------------
# 4) LOAD BOROUGHS
# -----------------------------

print("Loading borough shapefile...")
boroughs = gpd.read_file(PATH_BOROUGHS_SHP)

if BOROUGH_NAME_COL not in boroughs.columns:
    raise ValueError(
        f"BOROUGH_NAME_COL='{BOROUGH_NAME_COL}' not found in borough shapefile. "
        f"Available columns: {list(boroughs.columns)}"
    )

# Ensure boroughs are in WGS84 for spatial join with lat/lon points
boroughs = boroughs.to_crs(epsg=4326)

# London boundary polygon
london_boundary = boroughs.dissolve()[["geometry"]].copy()


# -----------------------------
# 5) LOAD ODI STATIONS CSV -> POINTS
# -----------------------------

print("Loading ODI stations CSV...")
s = pd.read_csv(PATH_STATIONS_ODI)

expected_station_cols = {"name", "latitude", "longitude"}
missing_station_cols = expected_station_cols - set(s.columns)
if missing_station_cols:
    raise ValueError(
        f"Stations CSV missing columns: {sorted(missing_station_cols)}. "
        f"Available columns: {list(s.columns)}"
    )

# Clean borough field if it contains HTML breaks/entities (optional)
if "borough" in s.columns:
    s["borough"] = (
        s["borough"]
        .astype(str)
        .str.replace(r"<br\s*/?>", " ", regex=True)
        .str.replace(r"&nbsp;", " ", regex=False)
        .str.strip()
    )

# Build GeoDataFrame from lat/lon
stations = gpd.GeoDataFrame(
    s.copy(),
    geometry=gpd.points_from_xy(s["longitude"], s["latitude"]),
    crs="EPSG:4326"
)

# Filter to stations inside Greater London boundary
print("Filtering stations to London boundary (spatial join)...")
stations_london = gpd.sjoin(
    stations,
    london_boundary,
    predicate="intersects",
    how="inner"
).drop(columns=["index_right"])

print(f"Total stations in CSV: {len(stations):,}")
print(f"Stations within London boundary: {len(stations_london):,}")


# -----------------------------
# 6) NORMALIZE JOIN KEYS
# -----------------------------

print("Normalizing station names for joining...")
stations_london["station_name_raw"] = stations_london["name"].astype(str)
stations_london["station_key"] = stations_london["station_name_raw"].apply(norm_station_name)

df["station_key"] = df[COL_STATION_NAME].apply(norm_station_name)


# -----------------------------
# 7) BUILD STATION-LEVEL KPIS
# -----------------------------

station_stats = (
    df.groupby("station_key", dropna=False)
      .agg(
          mobilisations=(COL_INCIDENT_ID, "count"),
          median_travel_sec=(COL_TRAVEL_SECONDS, "median"),
          home_share=(COL_DEPLOYED_FROM, lambda s: (s == "Home Station").mean())
      )
      .reset_index()
)

station_stats["median_travel_min"] = (station_stats["median_travel_sec"] / 60).round(2)

# -----------------------------
# 8) JOIN KPIS ONTO STATION POINTS
# -----------------------------

print("Joining station KPIs onto station geometries...")
stations_cov_gdf = stations_london.merge(station_stats, on="station_key", how="left")

match_rate = stations_cov_gdf["mobilisations"].notna().mean()
print(f"Join match rate (stations with KPI match): {match_rate:.1%}")

# Helpful debugging: show unmatched
unmatched = (
    stations_cov_gdf.loc[stations_cov_gdf["mobilisations"].isna(), ["station_name_raw", "station_key"]]
    .drop_duplicates()
    .head(20)
)
if len(unmatched):
    print("\nUnmatched stations (first 20) — likely naming differences:")
    print(unmatched.to_string(index=False))
else:
    print("All London stations matched successfully.")


# Add explicit lat/lon columns (handy for Streamlit/Folium)
stations_cov_gdf["station_lat"] = stations_cov_gdf.geometry.y
stations_cov_gdf["station_lon"] = stations_cov_gdf.geometry.x

# Provide a clean 'station_name' column that Streamlit can rely on
stations_cov_gdf["station_name"] = stations_cov_gdf["station_name_raw"]


# -----------------------------
# 9) SAVE STATION COVERAGE PARQUET
# -----------------------------

os.makedirs("Data/processed", exist_ok=True)

print(f"Saving station coverage layer to: {OUT_STATIONS_PARQUET}")

# Save as non-geometry parquet (folium wants lat/lon anyway)
stations_cov_out = pd.DataFrame(
    stations_cov_gdf.drop(columns="geometry")
)

stations_cov_out.to_parquet(OUT_STATIONS_PARQUET, index=False)
print(f"Saved {len(stations_cov_out):,} station records.")


# -----------------------------
# 10) FLOWS (Station -> Borough)
# -----------------------------

def norm_borough(x: str) -> str:
    if pd.isna(x):
        return ""
    x = str(x).strip().lower()
    x = x.replace("&", "and")
    x = re.sub(r"\s+", " ", x)
    return x

if EXPORT_FLOWS:
    print("Building station → borough flow table...")

    # Centroids in projected CRS berechnen (vermeidet Warning + ist korrekt)
    boroughs_proj = boroughs.to_crs(epsg=27700).copy()
    boroughs_proj["centroid"] = boroughs_proj.geometry.centroid
    boroughs_cent = boroughs_proj.set_geometry("centroid").to_crs(epsg=4326)

    borough_centroids = (
        boroughs_cent[[BOROUGH_NAME_COL, "centroid"]]
        .rename(columns={BOROUGH_NAME_COL: "BoroughName"})
        .copy()
    )
    borough_centroids["borough_lat"] = borough_centroids["centroid"].y
    borough_centroids["borough_lon"] = borough_centroids["centroid"].x
    borough_centroids.drop(columns=["centroid"], inplace=True)

    # Normalize borough keys on both sides
    borough_centroids["borough_key"] = borough_centroids["BoroughName"].apply(norm_borough)

    df_flow = df.copy()
    df_flow["borough_key"] = df_flow[COL_BOROUGH].apply(norm_borough)

    # Aggregate mobilisations and median travel per station-borough pair
    flows = (
        df_flow.groupby(["station_key", "borough_key"])
          .agg(
              mobilisations=(COL_INCIDENT_ID, "count"),
              median_travel_sec=(COL_TRAVEL_SECONDS, "median"),
          )
          .reset_index()
    )
    flows["median_travel_min"] = (flows["median_travel_sec"] / 60).round(2)

    # Add station coordinates
    station_coords = (
        stations_cov_out[["station_key", "station_lat", "station_lon", "station_name_raw"]]
        .drop_duplicates()
        .copy()
    )

    flows = flows.merge(station_coords, on="station_key", how="left")
    flows = flows.merge(
        borough_centroids[["borough_key", "BoroughName", "borough_lat", "borough_lon"]],
        on="borough_key",
        how="left",
    )

    # Remove rows with missing coordinates
    flows = flows.dropna(subset=["station_lat", "station_lon", "borough_lat", "borough_lon"])

    print(f"Flow records: {len(flows):,}")
    print(f"Saving flows to: {OUT_FLOWS_PARQUET}")
    flows.to_parquet(OUT_FLOWS_PARQUET, index=False)


print("\nDone")
print(f"Station coverage: {OUT_STATIONS_PARQUET}")
if EXPORT_FLOWS:
    print(f"Station-borough flows: {OUT_FLOWS_PARQUET}")
