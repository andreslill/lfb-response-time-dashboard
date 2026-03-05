# pages/5__Drivers_of_Response_Time_.py

import streamlit as st
from data_loader import load_data
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from branca.colormap import linear
import re as _re

# ------------------------------------------------------------
# Page config + theme


st.set_page_config(layout="wide")
sns.set_theme(style="white", context="notebook")

# Plot constants

FIG_WIDTH = 10
FIG_HEIGHT_SMALL = 3.5
FIG_HEIGHT_MEDIUM = 4.5
FIG_HEIGHT_LARGE = 6

def style_axes(ax):
    ax.title.set_fontsize(16)
    ax.title.set_weight("bold")

    ax.xaxis.label.set_size(13)
    ax.yaxis.label.set_size(13)

    ax.tick_params(axis="both", which="major", labelsize=11)

# ---------------------------------------------------------------------
#Title + Intro

st.title("Operational and Structural Drivers of Response Time")

st.markdown("""

This section decomposes response time into turnout and travel components to evaluate whether performance variation is primarily driven by
mobilisation processes or travel constraints.



**Response Time = Turnout Time (Station alerted → First vehicle leaves) + Travel Time (First vehicle leaves → Arrival at scene)**

""")


# ---------------------------------------------------------------------
# Load Data
df = load_data()

# Load London borough shapefile
boroughs = gpd.read_file("Data/london_boroughs/London_Borough_Excluding_MHW.shp")

# ---------------------------------------------------------------------
# Year and Month Filters

st.sidebar.header("Filters")

# Available years
available_years = ["All"] + sorted(df["Year"].unique())

# Available months (mit All Option)
available_months = ["All"] + [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

# Year filter
selected_year = st.sidebar.selectbox("Select Year",options=available_years)

# Month filter
selected_month = st.sidebar.selectbox("Select Month",options=available_months)

# Apply Filters
if selected_year == "All" and selected_month == "All":
    filtered_df = df.copy()

elif selected_year == "All":
    filtered_df = df[df["MonthName"] == selected_month]

elif selected_month == "All":
    filtered_df = df[df["Year"] == selected_year]
else:
    filtered_df = df[
        (df["Year"] == selected_year) &
        (df["MonthName"] == selected_month)
    ]

if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# Dynamic Period Label

min_year = df["Year"].min()
max_year = df["Year"].max()

if selected_year == "All" and selected_month == "All":
    period_label = f"{min_year}–{max_year}"

elif selected_year != "All" and selected_month == "All":
    period_label = f"{selected_year}"

elif selected_year == "All" and selected_month != "All":
    period_label = f"{selected_month} months between {min_year} and {max_year}"

else:
    period_label = f"{selected_month} {selected_year}"

# ------------------------------------------------------------
# Convert filtered_df(mobilisation level) to incident level (first pump only)

filtered_incidents = (
    filtered_df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

# ---------------------------------------------------------------------
# Feature engineering for this page

# Minutes versions (clean + consistent)
filtered_incidents = filtered_incidents.copy()

# Attendance in minutes
filtered_incidents["AttendanceMinutes"] = filtered_incidents["FirstPumpArriving_AttendanceTime"] / 60

# Turnout + Travel 
has_turnout = "TurnoutTimeSeconds" in filtered_incidents.columns
has_travel  = "TravelTimeSeconds" in filtered_incidents.columns

if has_turnout:
    filtered_incidents["TurnoutMinutes"] = filtered_incidents["TurnoutTimeSeconds"] / 60
if has_travel:
    filtered_incidents["TravelMinutes"] = filtered_incidents["TravelTimeSeconds"] / 60

filtered_incidents["Over6"] = filtered_incidents["FirstPumpArriving_AttendanceTime"] > 360

# ------------------------------------------------------------
# KPIs

st.markdown("---")

overall_turnout = filtered_incidents["TurnoutMinutes"].median()
overall_travel = filtered_incidents["TravelMinutes"].median()

total_component = overall_turnout + overall_travel
travel_share_pct = (overall_travel / total_component) * 100

col1, col2, col3 = st.columns(3)

col1.metric(
    "Median Turnout Time",
    f"{overall_turnout:.2f} min"
)

col2.metric(
    "Median Travel Time",
    f"{overall_travel:.2f} min"
)

col3.metric(
    "Travel Share of Response",
    f"{travel_share_pct:.0f}%"
)

# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------

# ------------------------------------------------------------
st.header("1. Is it Turnout or Travel? What Drives Borough Differences")  
# ------------------------------------------------------------
# Borough-level decomposition (Top 10 slowest boroughs)
st.subheader("Top 10 Slowest Boroughs: Response Time Decomposition")

st.markdown("""The ten slowest boroughs are analysed to understand which
            response component accounts for their extended median response times.
            """)
st.markdown(
    f"<div style='margin-top:-10px; margin-bottom:8px; color:#6b7280; font-size:0.85rem;'>"
    f"Data shown: {period_label}"
    f"</div>",
    unsafe_allow_html=True
)

# Borough-level medians
borough_decomp = (
    filtered_incidents
    .groupby("IncGeo_BoroughName", observed=True)
    .agg(
        TurnoutMedian=("TurnoutMinutes", "median"),
        TravelMedian=("TravelMinutes", "median"),
    )
    .reset_index()
)


# Exact total = turnout + travel
borough_decomp["TotalMedian"] = (
    borough_decomp["TurnoutMedian"] +
    borough_decomp["TravelMedian"]
)


# Sort by total descending
borough_decomp = borough_decomp.sort_values(
    "TotalMedian",
    ascending=False
)

# Optional: show only slowest 10
borough_decomp = borough_decomp.head(10)


# Plot
fig, ax = plt.subplots(figsize=(8, 5))


ax.barh(
    borough_decomp["IncGeo_BoroughName"],
    borough_decomp["TurnoutMedian"],
    label="Turnout (median)"
)

ax.barh(
    borough_decomp["IncGeo_BoroughName"],
    borough_decomp["TravelMedian"],
    left=borough_decomp["TurnoutMedian"],
    label="Travel (median)"
)


ax.set_xlabel("Minutes (median)")
ax.set_ylabel("")

# 6-minute reference line
ax.axvline(
    6,
    color="black",
    linestyle="--",
    linewidth=1.5,
    alpha=0.7
)

# Label for reference line
ax.text(
    5.95,
    -0.61,
    "6 minute target",
    fontsize=10,
    ha="right"
)

# Reverse y-axis so slowest on top
ax.invert_yaxis()

# ️Legend 
ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, 1.08),
    ncol=2,
    frameon=False
)

sns.despine()
fig.tight_layout()

st.pyplot(fig)


# Dynamic insight for the shown borough subset
borough_decomp["TravelShare"] = (
    borough_decomp["TravelMedian"] /
    borough_decomp["TotalMedian"]
)

avg_travel_share = borough_decomp["TravelShare"].mean() * 100

slowest_turnout_median = borough_decomp["TurnoutMedian"].median()
slowest_travel_median = borough_decomp["TravelMedian"].median()

st.markdown(f"""
- Travel accounts for **{travel_share_pct:.0f}%** of the median response time.
- Among the slowest boroughs, median turnout time is **{slowest_turnout_median:.2f} minutes**,
  while travel time reaches **{slowest_travel_median:.2f} minutes**.
- Turnout times vary only slightly across boroughs.
- These results suggest that differences in response performance are primarily driven by travel
  rather than station mobilisation.
""")


# ------------------------------------------------------------
# Turnout Time Stability Check 

# Overall turnout median (minutes)
overall_turnout_median = filtered_incidents["TurnoutMinutes"].median()

turnout_stats = (
    filtered_incidents
    .groupby("IncGeo_BoroughName", observed=True)["TurnoutMinutes"]
    .agg(["median", "std"])
    .reset_index()
)

avg_borough_std = turnout_stats["std"].mean()
max_borough_std = turnout_stats["std"].max()

# Convert to seconds
overall_turnout_sec = overall_turnout_median * 60
avg_borough_std_sec = avg_borough_std * 60
max_borough_std_sec = max_borough_std * 60

with st.expander("Validation: Turnout time is stable across boroughs"):

    # Borough-level medians
    borough_medians = (
        filtered_incidents
        .groupby("IncGeo_BoroughName", observed=True)
        .agg(
            TurnoutMedian=("TurnoutMinutes", "median"),
            TravelMedian=("TravelMinutes", "median")
        )
        .dropna()
    )

    # Turnout stability metrics (in seconds)
    turnout_overall_sec = filtered_incidents["TurnoutMinutes"].median() * 60
    turnout_min_med_sec = borough_medians["TurnoutMedian"].min() * 60
    turnout_max_med_sec = borough_medians["TurnoutMedian"].max() * 60
    turnout_iqr_sec = (borough_medians["TurnoutMedian"].quantile(0.75) - borough_medians["TurnoutMedian"].quantile(0.25)) * 60

    # Travel variability metrics (in minutes)
    travel_overall_min = filtered_incidents["TravelMinutes"].median()
    travel_min_med = borough_medians["TravelMedian"].min()
    travel_max_med = borough_medians["TravelMedian"].max()
    travel_iqr_min = borough_medians["TravelMedian"].quantile(0.75) - borough_medians["TravelMedian"].quantile(0.25)
    travel_iqr_sec = travel_iqr_min * 60

    st.markdown(f"""
- Overall median turnout: **{turnout_overall_sec/60:.2f} min**
- Borough median turnout range: **{turnout_min_med_sec/60:.2f}–{turnout_max_med_sec/60:.2f} min**
- Borough median turnout IQR: **{turnout_iqr_sec:.0f} s**

In contrast:
- Overall median travel: **{travel_overall_min:.2f} min**
- Borough median travel range: **{travel_min_med:.2f}–{travel_max_med:.2f} min**
- Borough median travel IQR: **{travel_iqr_sec:.0f} s**

**Conclusion:** Turnout medians vary only slightly across boroughs,
while travel medians variation is high, suggesting travel time as
the main geographic driver of response performance.
""")



# ------------------------------------------------------------
#Methodological Note


with st.expander("Methodological Note"):
    st.markdown("""
    Median turnout and median travel time are calculated independently.
    As medians are not additive, Median(A) + Median(B) does not necessarily equal 
    Median(A + B). Therefore, their sum may differ slightly from the median attendance time.
    """)

# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------

# ------------------------------------------------------------
# Station Coverage and Cross-Borough Deployment


STATIONS_PARQUET = "Data/processed/stations_london_cov.parquet"

@st.cache_data
def load_station_coords(path: str) -> pd.DataFrame:
    """Load pre-computed station coordinates from prepare_station_coverage.py output."""
    return pd.read_parquet(path)

def norm_station_name(x: str) -> str:
    """Normalise station names for joining — keep consistent with prepare script."""
    if pd.isna(x):
        return ""
    x = str(x).strip().lower()
    x = x.replace("&", "and")
    x = _re.sub(r"[^a-z0-9\s]", " ", x)
    x = _re.sub(r"\s+", " ", x).strip()
    return x

def norm_borough(x: str) -> str:
    """Normalise borough names for joining."""
    if pd.isna(x):
        return ""
    x = str(x).strip().lower()
    x = x.replace("&", "and")
    x = _re.sub(r"\s+", " ", x)
    return x

def make_colormap(series: pd.Series, palette: str = "YlOrRd"):
    """Build a branca linear colormap scaled to the data range.
    branca palette names use _09 suffix: YlOrRd_09, PuBuGn_09, YlGnBu_09, PuRd_09
    """
    s = series.dropna()
    if s.empty:
        return None
    vmin, vmax = float(s.min()), float(s.max())
    if vmin == vmax:
        vmax = vmin + 1e-9
    # branca appends _09 to colorbrewer palette names
    palette_key = palette if hasattr(linear, palette) else f"{palette}_09"
    return getattr(linear, palette_key).scale(vmin, vmax)
st.header("2. Station Coverage and Cross-Borough Deployment")

# -----------------------------
# Build station KPIs first (needed for KPI bar above the map)

station_df = filtered_incidents.copy()

need_cols = {"DeployedFromStation_Name", "TravelMinutes", "DeployedFromLocation"}
missing_cols = need_cols - set(station_df.columns)
if missing_cols:
    st.warning(f"Missing columns needed for station KPIs: {sorted(missing_cols)}")
    st.stop()

station_kpis = (
    station_df
    .groupby("DeployedFromStation_Name", observed=True)
    .agg(
        incidents=("IncidentNumber", "count"),
        median_travel_min=("TravelMinutes", "median"),
        home_share=("DeployedFromLocation", lambda s: (s == "Home Station").mean()),
    )
    .reset_index()
)
station_kpis["station_key"] = station_kpis["DeployedFromStation_Name"].apply(norm_station_name)

coords = load_station_coords(STATIONS_PARQUET).copy()
coords = coords.dropna(subset=["station_lat", "station_lon"])
coords = coords.drop(columns=["mobilisations", "median_travel_sec", "median_travel_min", "home_share"], errors="ignore")

if "station_key" not in coords.columns:
    base_name = "station_name" if "station_name" in coords.columns else "station_name_raw"
    coords["station_key"] = coords[base_name].apply(norm_station_name)

stations_map = coords.merge(
    station_kpis[["station_key", "incidents", "median_travel_min", "home_share"]],
    on="station_key",
    how="left",
)
stations_map["kpi_matched"] = stations_map["incidents"].notna()
stations_map = stations_map[stations_map["kpi_matched"]].copy()

if stations_map.empty:
    st.warning("No station points available for the current filters.")
    st.stop()

# -----------------------------
# KPI Bar 

med_travel_home_kpi = filtered_incidents[
    filtered_incidents["DeployedFromLocation"] == "Home Station"
]["TravelMinutes"].median()
med_travel_away_kpi = filtered_incidents[
    filtered_incidents["DeployedFromLocation"] != "Home Station"
]["TravelMinutes"].median()
avg_home_share_kpi  = stations_map["home_share"].mean() * 100

k1, k2, k3, k4 = st.columns(4)
k1.metric("Stations shown", f"{len(stations_map)}")
k2.metric("Avg home share", f"{avg_home_share_kpi:.1f}%")
k3.metric("Median travel time (home)", f"{med_travel_home_kpi:.2f} min")
k4.metric("Median travel time (away)", f"{med_travel_away_kpi:.2f} min")

# -----------------------------
# Context + research question

st.markdown(
    "All 102 London Fire Brigade stations are mapped to examine how geographic coverage "
    "and cross-borough deployment influence travel time."
    "Cross-borough deployments refer to responses where a station attends an incident outside its home ground. "
    "[london-fire.gov.uk](https://www.london-fire.gov.uk/community/your-borough/)"
)
st.markdown(
    "**Are longer travel times driven by geographic coverage gaps and cross-borough deployment, "
    "or by exceptional operational delays?**"
)

# -----------------------------
# Filters + toggles

c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    deployment_scope = st.selectbox(
        "Deployments",
        ["All (home + away)", "Home station only", "Away / out-of-area only"],
        index=0,
    )

with c2:
    metric_color = st.selectbox(
        "Colour stations by",
        ["Median travel time (min)", "Incidents (count)", "Home share (%)", "No colour (uniform)"],
        index=0,
    )

with c3:
    show_flows = st.toggle("Show station → borough flows", value=False)

# Apply Home/Away scope to stations_map
if deployment_scope == "Home station only":
    station_df_scoped = station_df[station_df["DeployedFromLocation"] == "Home Station"]
elif deployment_scope == "Away / out-of-area only":
    station_df_scoped = station_df[station_df["DeployedFromLocation"] != "Home Station"]
else:
    station_df_scoped = station_df

# Recompute KPIs for scoped view
station_kpis_scoped = (
    station_df_scoped
    .groupby("DeployedFromStation_Name", observed=True)
    .agg(
        incidents=("IncidentNumber", "count"),
        median_travel_min=("TravelMinutes", "median"),
        home_share=("DeployedFromLocation", lambda s: (s == "Home Station").mean()),
    )
    .reset_index()
)
station_kpis_scoped["station_key"] = station_kpis_scoped["DeployedFromStation_Name"].apply(norm_station_name)

stations_map = coords.merge(
    station_kpis_scoped[["station_key", "incidents", "median_travel_min", "home_share"]],
    on="station_key",
    how="left",
)
stations_map["kpi_matched"] = stations_map["incidents"].notna()
stations_map = stations_map[stations_map["kpi_matched"]].copy()

if stations_map.empty:
    st.warning("No station points available for the current filters.")
    st.stop()

# -----------------------------
# Build colormap for selected metric

cmap = None
color_col = None
legend_name_station = None

if metric_color == "Median travel time (min)":
    color_col = "median_travel_min"
    legend_name_station = "Median travel time (min)"
    cmap = make_colormap(stations_map[color_col], palette="YlOrRd")

elif metric_color == "Incidents (count)":
    color_col = "incidents"
    legend_name_station = "Incidents"
    cmap = make_colormap(stations_map[color_col], palette="PuBuGn")

elif metric_color == "Home share (%)":
    stations_map["home_share_pct"] = (stations_map["home_share"] * 100).round(1)
    color_col = "home_share_pct"
    legend_name_station = "Home share (%)"
    cmap = make_colormap(stations_map[color_col], palette="YlGnBu")

def radius_from_incidents(x) -> float:
    """Scale marker radius by incident count — min 3, max 10."""
    if pd.isna(x):
        return 3
    r = 3 + (float(x) ** 0.5) / 18
    return max(3, min(r, 10))

# -----------------------------
# Build Folium map 

m_stations = folium.Map(
    location=[51.5074, -0.1278],
    zoom_start=10,
    min_zoom=10,
    max_zoom=10,
    zoom_control=False,
    scrollWheelZoom=False,
    dragging=False,
    doubleClickZoom=False,
    touchZoom=False,
    tiles="CartoDB positron",
)

# Borough boundaries (inner lines)
folium.GeoJson(
    boroughs,
    name="Borough boundaries",
    style_function=lambda x: {
        "fillOpacity": 0,
        "color": "#6b7280",
        "weight": 0.8,
    },
).add_to(m_stations)

# London outer boundary (bold outline)
london_outline = boroughs.dissolve()
folium.GeoJson(
    london_outline,
    name="London boundary",
    style_function=lambda x: {
        "fillOpacity": 0,
        "color": "#1f2937",
        "weight": 2.5,
    },
).add_to(m_stations)

marker_parent = m_stations

for _, row in stations_map.iterrows():
    name    = row.get("station_name", row.get("station_name_raw", "Unknown"))
    lat     = float(row["station_lat"])
    lon     = float(row["station_lon"])
    inc     = row.get("incidents", None)
    med_tr  = row.get("median_travel_min", None)
    hs      = row.get("home_share", None)
    matched = bool(row.get("kpi_matched", False))

    if matched and cmap is not None and color_col is not None and pd.notna(row.get(color_col)):
        col = cmap(row[color_col])
    elif not matched:
        col = "#6b7280"
    else:
        col = "#2b6cb0"

    tooltip_lines = [f"<b>{name}</b>"]
    if matched:
        if pd.notna(inc):
            tooltip_lines.append(f"Incidents: {int(inc):,}")
        if pd.notna(med_tr):
            tooltip_lines.append(f"Median travel: {float(med_tr):.2f} min")
        if pd.notna(hs):
            tooltip_lines.append(f"Home share: {float(hs)*100:.1f}%")
    else:
        tooltip_lines.append("No KPI match for current filters.")

    folium.CircleMarker(
        location=[lat, lon],
        radius=radius_from_incidents(inc) if matched else 4,
        color=col,
        fill=True,
        fill_color=col,
        fill_opacity=0.85,
        weight=1,
        tooltip=folium.Tooltip("<br>".join(tooltip_lines), sticky=True),
    ).add_to(marker_parent)

if cmap is not None and legend_name_station is not None:
    cmap.caption = legend_name_station
    cmap.add_to(m_stations)

# Optional flows
if show_flows:
    boroughs_proj = boroughs.to_crs(epsg=27700).copy()
    boroughs_proj["centroid"] = boroughs_proj.geometry.centroid
    boroughs_cent = boroughs_proj.set_geometry("centroid").to_crs(epsg=4326)

    borough_centroids_flow = boroughs_cent[["NAME", "centroid"]].copy()
    borough_centroids_flow["borough_lat"] = borough_centroids_flow["centroid"].y
    borough_centroids_flow["borough_lon"] = borough_centroids_flow["centroid"].x
    borough_centroids_flow["borough_key"] = borough_centroids_flow["NAME"].apply(norm_borough)

    flow_df = station_df_scoped.copy()
    flow_df["station_key"] = flow_df["DeployedFromStation_Name"].apply(norm_station_name)
    flow_df["borough_key"] = flow_df["IncGeo_BoroughName"].apply(norm_borough)

    flows = (
        flow_df
        .groupby(["station_key", "borough_key"], observed=True)
        .agg(
            incidents=("IncidentNumber", "count"),
            median_travel_min=("TravelMinutes", "median"),
        )
        .reset_index()
    )

    station_coords_flow = coords[["station_key", "station_lat", "station_lon"]].drop_duplicates()
    flows = flows.merge(station_coords_flow, on="station_key", how="left")
    flows = flows.merge(
        borough_centroids_flow[["borough_key", "borough_lat", "borough_lon"]],
        on="borough_key", how="left"
    )
    flows = flows.dropna(subset=["station_lat", "station_lon", "borough_lat", "borough_lon"])

    if len(flows):
        fc1, fc2, fc3 = st.columns([1, 1, 1])
        with fc1:
            max_lines = int(st.slider("Max flow lines", 100, 5000, 1200, 100))
        with fc2:
            min_flow_inc = int(st.slider(
                "Min incidents per flow", 1, int(flows["incidents"].max()), 50, 10
            ))
        with fc3:
            flow_colour = st.selectbox(
                "Colour flows by",
                ["Incidents", "Median travel time (min)", "Uniform"],
                index=0
            )

        f = flows.loc[flows["incidents"] >= min_flow_inc].copy()
        f = f.sort_values("incidents", ascending=False).head(max_lines)

        flow_layer = folium.FeatureGroup(name="Station → Borough flows", show=True)
        flow_layer.add_to(m_stations)

        flow_cmap = None
        if flow_colour == "Incidents":
            flow_cmap = make_colormap(f["incidents"], palette="PuRd")
        elif flow_colour == "Median travel time (min)":
            flow_cmap = make_colormap(f["median_travel_min"], palette="YlOrRd")

        for _, r in f.iterrows():
            inc_flow    = float(r["incidents"])
            med_tr_flow = float(r["median_travel_min"]) if pd.notna(r.get("median_travel_min")) else None
            w = 1 + min(6, (inc_flow ** 0.5) / 10)

            if flow_colour == "Uniform":
                c = "#111827"
            elif flow_cmap is not None:
                val = inc_flow if flow_colour == "Incidents" else (med_tr_flow or 0)
                c = flow_cmap(val)
            else:
                c = "#111827"

            tip = f"Incidents: {int(inc_flow):,}"
            if med_tr_flow is not None:
                tip += f"<br>Median travel: {med_tr_flow:.2f} min"

            folium.PolyLine(
                locations=[
                    [float(r["station_lat"]), float(r["station_lon"])],
                    [float(r["borough_lat"]), float(r["borough_lon"])]
                ],
                color=c, weight=w, opacity=0.35,
                tooltip=folium.Tooltip(tip, sticky=True),
            ).add_to(flow_layer)

        folium.LayerControl(collapsed=True).add_to(m_stations)
    else:
        st.info("No flow lines available for the current filters.")

# Render map
st_folium(m_stations, use_container_width=True, height=650)

# -----------------------------

st.markdown(
    f"<div style='margin-top:-10px; margin-bottom:8px; color:#6b7280; font-size:0.85rem;'>"
    f"Data shown: {period_label}"
    f"</div>",
    unsafe_allow_html=True
)

# -----------------------------
# Map explanation expander
# -----------------------------
with st.expander("How to read the map"):
    st.markdown("""
Each circle represents one fire station. Circle size reflects the number of incidents responded to,
while colour indicates the selected metric.

Hover over a station to view its name, incident count, median travel time and home share.

**Home share** represents the proportion of incidents a station attended within its own ground.
Lower values indicate frequent cross-borough deployment, which typically results in longer travel times.

Enable **station → borough flows** to visualise deployment patterns. Lines connect stations to the
boroughs they serve, with line width scaled by incident volume.
""")

# -----------------------------
# Dynamic map insight
# -----------------------------
if not stations_map.empty:
    busiest    = stations_map.loc[stations_map["incidents"].idxmax()]
    slowest    = stations_map.loc[stations_map["median_travel_min"].idxmax()]
    lowest_home = stations_map.loc[stations_map["home_share"].idxmin()]

    avg_home_share = stations_map["home_share"].mean() * 100
    avg_travel     = stations_map["median_travel_min"].mean()

    travel_diff_pct = (
        (med_travel_away_kpi - med_travel_home_kpi) / med_travel_home_kpi * 100
        if med_travel_home_kpi > 0 else 0
    )

    st.markdown(f"""
**Map Insight ({period_label})**

- The busiest station is **{busiest['station_name']}** with **{int(busiest['incidents']):,} incidents**.
- The station with the longest median travel time is **{slowest['station_name']}** 
  at **{slowest['median_travel_min']:.2f} minutes**.
- **{lowest_home['station_name']}** has the lowest home share at 
  **{lowest_home['home_share']*100:.1f}%**, indicating frequent cross-borough deployment.
- Median travel time increases from **{med_travel_home_kpi:.2f} min** for home deployments to 
  **{med_travel_away_kpi:.2f} min** for cross-borough responses, a **{travel_diff_pct:+.0f}%** 
  difference, indicating longer distances when stations respond outside their home ground.
""")

# ------------------------------------------------------------
st.header("3. How does Hour of Day influence Response Time?")

st.markdown("""Hourly response time patterns are analysed to assess whether
            turnout or travel time drives performance fluctuations throughout the day.
            """)

st.subheader("Turnout vs Travel Time by Hour of Day")

st.markdown(
    f"<div style='margin-top:-10px; margin-bottom:8px; color:#6b7280; font-size:0.85rem;'>"
    f"Data shown: {period_label}"
    f"</div>",
    unsafe_allow_html=True
)

hourly_components = (
    filtered_incidents
    .groupby("HourOfCall")
    .agg(
        TurnoutMedian=("TurnoutMinutes", "median"),
        TravelMedian=("TravelMinutes", "median")
    )
    .reset_index()
)

# Add total response time
hourly_components["TotalMedian"] = (
    hourly_components["TurnoutMedian"] +
    hourly_components["TravelMedian"]
)

fig, ax = plt.subplots(figsize=(10, 5))

cb = sns.color_palette("colorblind")
turnout_color = cb[2]
travel_color = cb[0]

ax.plot(
    hourly_components["HourOfCall"],
    hourly_components["TurnoutMedian"],
    label="Turnout (median)",
    linewidth=2.5,
    marker="o"
)

ax.plot(
    hourly_components["HourOfCall"],
    hourly_components["TravelMedian"],
    label="Travel (median)",
    linewidth=2.5,
    marker="o"
)

ax.plot(
    hourly_components["HourOfCall"],
    hourly_components["TotalMedian"],
    label="Total Response (median)",
    linewidth=2.8,
    linestyle="--",
    color="black",
    alpha=0.8
)

handles, labels = ax.get_legend_handles_labels()

# Desired order:
# Total, Travel, Turnout
order = [2, 1, 0]

ax.legend(
    [handles[i] for i in order],
    [labels[i] for i in order],
    loc="upper center",
    bbox_to_anchor=(0.5, 1.15),
    ncol=3,
    frameon=False
)

ax.set_xlabel("Hour of Call")
ax.set_ylabel("Minutes (median)")
ax.set_xticks(range(0, 24))


sns.despine()
fig.tight_layout()

st.pyplot(fig)


# Peak travel hour
peak_hour = hourly_components.loc[
    hourly_components["TravelMedian"].idxmax(),
    "HourOfCall"
]

travel_range = (
    hourly_components["TravelMedian"].max() -
    hourly_components["TravelMedian"].min()
)

turnout_range = (
    hourly_components["TurnoutMedian"].max() -
    hourly_components["TurnoutMedian"].min()
)

if travel_range > turnout_range:
    dominant = "Travel"
    other = "Turnout"
    dominant_range = travel_range
    other_range = turnout_range
else:
    dominant = "Turnout"
    other = "Travel"
    dominant_range = turnout_range
    other_range = travel_range

range_ratio = round(dominant_range / other_range, 1) if other_range > 0 else 0

st.markdown(f"""
**Key Insights ({period_label})**

- **{dominant} time** shows greater hourly variation, fluctuating by 
  **{dominant_range:.2f} minutes** across the day and peaking around **{peak_hour}:00**.
- **{other} time** varies by **{other_range:.2f} minutes**,
  {"approximately the same magnitude, suggesting hourly conditions affect both components similarly."
  if abs(travel_range - turnout_range) < 0.15
  else f"{range_ratio}x less, confirming that {'station mobilisation' if dominant == 'Travel' else 'travel conditions'} is more consistent throughout the day."}
""")



# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------

st.header("4. Why Do Incidents Exceed the 6-Minute Target?")

st.markdown("""Delay codes for incidents exceeding the 6-minute response target are analysed
to distinguish routine travel constraints from exceptional delays.
""")
# ---------------------------------------------------------------------

st.subheader("Breakdown of Recorded Delay Factors")

st.markdown(
    f"<div style='margin-top:-10px; margin-bottom:8px; color:#6b7280; font-size:0.85rem;'>"
    f"Data shown: {period_label}"
    f"</div>",
    unsafe_allow_html=True
)

# Filter incidents exceeding 6-minute target
delayed_df = filtered_incidents[
    filtered_incidents["FirstPumpArriving_AttendanceTime"] > 360
].copy()

# Remove missing delay codes
delayed_df = delayed_df[
    delayed_df["DelayCode_Description"].notna()
]

# Count delay codes
delay_counts = (
    delayed_df
    .groupby("DelayCode_Description", observed=True)
    .size()
    .reset_index(name="IncidentCount")
    .sort_values("IncidentCount", ascending=False)
)

# Rename category to avoid CategoricalDtype replace warning
if "No delay" in delay_counts["DelayCode_Description"].values:
    delay_counts["DelayCode_Description"] = (
        delay_counts["DelayCode_Description"]
        .astype(str)
        .replace({"No delay": "No recorded delay code"})
    )


total_exceedances = delay_counts["IncidentCount"].sum()

# Define top categories to show in main chart
top_n = 4

top_delay = delay_counts.head(top_n).copy()
others_delay = delay_counts.iloc[top_n:].copy()

# Ensure "Arrived but held up - Other reaso." is included in Others
mask_arrived = delay_counts["DelayCode_Description"].str.contains(
    "Arrived but held up", na=False
)

arrived_rows = delay_counts[mask_arrived]

# Append it to others explicitly
others_delay = pd.concat([others_delay, arrived_rows], ignore_index=True)

# Remove duplicates
others_delay = others_delay.drop_duplicates(subset="DelayCode_Description")

# Calculate percentages
top_delay["Percent"] = (
    top_delay["IncidentCount"] / total_exceedances * 100
)

others_percent = (
    others_delay["IncidentCount"].sum() / total_exceedances * 100
)

# Add Others row
others_row = pd.DataFrame({
    "DelayCode_Description": ["Other Delay Codes"],
    "IncidentCount": [others_delay["IncidentCount"].sum()],
    "Percent": [others_percent]
})

final_delay = pd.concat([top_delay, others_row], ignore_index=True)

# Sort ascending for horizontal bar plot
final_delay = final_delay.sort_values("Percent", ascending=True)

# Context
exceedances = f"{len(delayed_df):,}".replace(",", ".")

st.caption(
    f"{exceedances} incidents exceeded the 6-minute target "
    f"({len(delayed_df)/len(filtered_incidents)*100:.1f}% of total incidents) in {period_label}."
)

# Plot
fig, ax = plt.subplots(figsize=(10, 6))

cb = sns.color_palette("colorblind")
main_color = cb[0]  # consistent dashboard color

bars = ax.barh(
    final_delay["DelayCode_Description"],
    final_delay["Percent"],
    color=main_color
)

# Add labels
for i, val in enumerate(final_delay["Percent"]):
    ax.text(
        val - 0.5,
        i,
        f"{val:.1f}%",
        va="center",
        ha="right",
        fontsize=10,
        weight="bold",
        color="white"
    )

ax.set_xlabel("Share of Incidents Exceeding 6-Minute Response Time Target (%)")

sns.despine()
plt.tight_layout()
st.pyplot(fig)

# Calculate Share of "Not held up" for the Insights

not_held_up_row = delay_counts[
    delay_counts["DelayCode_Description"] == "Not held up"
]

if not not_held_up_row.empty:
    not_held_up_percent = (
        not_held_up_row["IncidentCount"].values[0] /
        total_exceedances * 100
    )
else:
    not_held_up_percent = 0

# Insights

top_driver = top_delay.iloc[0]

st.markdown(f"""
- A substantial share of exceedances (**{not_held_up_percent:.1f}%**) are recorded without
  a specific delay factor ("Not held up"), indicating that most exceedances occur under normal
  operating conditions rather than being driven by exceptional operational delays.
- The remaining delay factors collectively account for approximately **{others_percent:.1f}%**,
  indicating a moderate long-tail distribution of operational causes.
"""
)

# ---------------------------------------------------------------------
# Expandable explaining "Others" Category

with st.expander("Show delay codes included in 'Other Delay Codes'"):

    if not others_delay.empty:

        others_delay["Percent"] = (
            others_delay["IncidentCount"] / total_exceedances * 100
        )

        others_delay = others_delay.sort_values("Percent", ascending=False)

        for _, row in others_delay.iterrows():
            st.markdown(
                f"- {row['DelayCode_Description']} "
                f"– {row['Percent']:.1f}%"
            )

# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------

st.markdown(
  "<div style='margin-top:12px; padding-left:12px; border-left:3px solid #e5e7eb; "
  "color:#4b5563; font-size:0.95rem;'>"
  "<strong>In summary:</strong> Variation in response performance is primarily explained by travel dynamics: Travel time accounts for "
  "most of median attendance time and increases for cross-borough deployments. While most 6-minute exceedances carry no specific delay code, "
  "suggesting routine operational conditions rather than exceptional disruptions."
  "</div>",
  unsafe_allow_html=True
)

# ---------------------------------------------------------------------
st.markdown("---")
st.caption(
    "London Fire Brigade Response Time Analysis (2021–2025) · Andrés Lill · February 2026"
)
