# pages/4_Geographic_Performance.py

import streamlit as st
from data_loader import load_data
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import seaborn as sns
from scipy.stats import linregress
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import statsmodels.api as sm

# ---------------------------------------------------------------------
# Theme

st.set_page_config(layout="wide")
sns.set_theme(style="white", context="notebook")

# ---------------------------------------------------------------------
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
# Title

st.title("Geographic Performance")


st.markdown("""
This section analyses geographic variation in response performance
across London boroughs, identifying spatial patterns and structural differences
in operational response
""")

# ---------------------------------------------------------------------
# Load Data

df = load_data()

# Load London borough shapefile
boroughs = gpd.read_file("Data/london_boroughs/London_Borough_Excluding_MHW.shp")

# London Population
pop = pd.read_csv("Data/london_population_borough.csv")
boroughs["Area_km2"] = boroughs["HECTARES"] / 100

# ---------------------------------------------------------------------
# Filters

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

# Incident type Filter
incident_options = ["All"] + sorted(df["IncidentGroup"].dropna().unique())

selected_incident = st.sidebar.selectbox(
    "Select Incident Type",
    options=incident_options,
    key="geo_incident"
)

# ---------------------------------------------------------------------
# Apply Filters

# Year + Month
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

# Incident Type
if selected_incident != "All":
    filtered_df = filtered_df[
        filtered_df["IncidentGroup"] == selected_incident
    ]

# Empty check
if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# Dynamic Period Label
min_year = df["Year"].min()
max_year = df["Year"].max()

if selected_year == "All" and selected_month == "All":
    period_label = f"{min_year}–{max_year}"

elif selected_year != "All" and selected_month == "All":
    period_label = f"{selected_year}, January–December"

elif selected_year == "All" and selected_month != "All":
    period_label = f"{selected_month} months between {min_year} and {max_year}"

else:
    period_label = f"{selected_month} {selected_year}"

# Dynamic Incident Label
if selected_incident == "All":
    incident_label = "All Incident Types"
else:
    incident_label = f"{selected_incident} Incidents"
    

st.caption(f"Data shown: {period_label}, {incident_label} ")

# ---------------------------------------------------------------------
# Convert filtered_df(mobilisation level) to incident level (first pump only)

filtered_incidents = (
    filtered_df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)
# ---------------------------------------------------------------------

st.header("1. Do Response Times Differ Between Inner and Outer London?")

st.markdown("""Median response times in Inner versus Outer London were
compared to assess whether a structural performance gap exists..""")

# ---------------------------------------------------------------------
# Prepare dataset for analysis

# Normalize borough names for merging response time (uppercase + trim)
boroughs["NAME_clean"] = (
    boroughs["NAME"]
    .str.strip()
    .str.upper()
)

# Create borough-level Median Response Time (base dataframe for multiple plots)
# based on filtered_incidents
borough_spatial_extent = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")
    .agg(
        MedianResponseMinutes=(
            "FirstPumpArriving_AttendanceTime",
            lambda x: x.median() / 60
        )
    )
    .reset_index()
)

# Standardise borough names for merging with geo dataset
borough_spatial_extent["NAME_clean"] = (
    borough_spatial_extent["IncGeo_BoroughName"]
    .str.strip()
    .str.upper()
)

# Merge area size
borough_spatial_extent = borough_spatial_extent.merge(
    boroughs[["NAME_clean", "Area_km2"]],
    on="NAME_clean",
    how="left"
)

# Definition:
# "Response within 6 min (%)" shown in the dashboard
# corresponds to the internal variable "ComplianceRate"
# (share of incidents with first pump attendance ≤ 6 minutes).

# Add compliance rate per borough
borough_compliance = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")["FirstPumpArriving_AttendanceTime"]
    .apply(lambda x: (x <= 360).mean() * 100)
    .reset_index(name="ComplianceRate")
)

borough_spatial_extent = borough_spatial_extent.merge(
    borough_compliance,
    on="IncGeo_BoroughName"
)

# Add incident volume per borough (bubble size)
borough_volume = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")
    .size()
    .reset_index(name="IncidentCount")
)

borough_spatial_extent = borough_spatial_extent.merge(
    borough_volume,
    on="IncGeo_BoroughName"
)

# Prepare borough-level dataset for inner-outer London comparison
borough_df = borough_spatial_extent.copy()


# Merge official Inner / Outer London classification (ONS)
borough_df = borough_df.merge(
    boroughs[["NAME_clean", "ONS_INNER"]],
    on="NAME_clean",
    how="left"
)

# Map ONS indicator to Inner and Outer London 
borough_df["AreaType"] = borough_df["ONS_INNER"].map({
    "T": "Inner London",
    "F": "Outer London"
})


# Split dataset by Inner and Outer London 
inner_df = borough_df[borough_df["AreaType"] == "Inner London"]
outer_df = borough_df[borough_df["AreaType"] == "Outer London"]


# ---------------------------------------------------------------------
# Barplot
st.subheader("Median Response Time: Inner vs. Outer London")


# Prepare Inner vs Outer dataframe
inner_outer_df = (
    borough_spatial_extent
    .merge(
        boroughs[["NAME_clean", "ONS_INNER"]],
        on="NAME_clean",
        how="left"
    )
)

# Map readable labels
inner_outer_df["AreaType"] = inner_outer_df["ONS_INNER"].map({
    "T": "Inner London",
    "F": "Outer London"
})


# Aggregate
inner_outer_summary = (
    inner_outer_df
    .groupby("AreaType")["MedianResponseMinutes"]
    .mean()
    .reset_index()
)


# Set categorical order
inner_outer_summary["AreaType"] = pd.Categorical(
    inner_outer_summary["AreaType"],
    categories=["Inner London", "Outer London"],
    ordered=True
)

# Optional defensive sorting (not required but clean)
inner_outer_summary = inner_outer_summary.sort_values("AreaType")


# Plot 
fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT_SMALL))

# Colorblind-safe palette (2 colors)
palette = sns.color_palette("colorblind", 2)

ax = sns.barplot(
    data=inner_outer_summary,
    y="AreaType",
    x="MedianResponseMinutes",
    palette=palette
)

plt.title(
    "Median Response Time: Inner vs Outer London",
    weight="bold"
)

plt.xlabel("Median Response Time (minutes)")
plt.ylabel("")

# Value labels
for i, v in enumerate(inner_outer_summary["MedianResponseMinutes"]):
    ax.text(v + 0.03, i, f"{v:.2f} min", va="center")

sns.despine(left=True, bottom=True)

plt.tight_layout()
st.pyplot(fig)


# Dynamic Markdown Inner vs Outer London

inner_value = inner_outer_summary.loc[
    inner_outer_summary["AreaType"] == "Inner London",
    "MedianResponseMinutes"
].values[0]

outer_value = inner_outer_summary.loc[
    inner_outer_summary["AreaType"] == "Outer London",
    "MedianResponseMinutes"
].values[0]

difference_minutes = outer_value - inner_value
difference_seconds = difference_minutes * 60
percent_difference = (difference_minutes / inner_value) * 100

# Format gap text intelligently
if abs(difference_minutes) >= 1:
    gap_text = f"{difference_minutes:.2f} minutes"
else:
    gap_text = f"{difference_seconds:.0f} seconds"

st.markdown(f"""

**Key Insights**

- Outer London has a higher median response time **({outer_value:.2f} min)** 
  than Inner London **({inner_value:.2f} min)**.
- The gap of **{gap_text} ({percent_difference:.1f}% difference)**  highlights how borough density and travel distance directly affect response performance.
""")

with st.expander("Show Inner vs Outer Borough Classification"):


    st.subheader("Classification: Inner vs Outer London")

    st.markdown("""
    London’s Inner and Outer boroughs, according to official ONS classification.
    """)

    # Map T/F to readable labels
    boroughs["AreaType"] = boroughs["ONS_INNER"].map({
        "T": "Inner London",
        "F": "Outer London"
    })

    # Create base map
    m = folium.Map(
    location=[51.5074, -0.1278],
    zoom_start=10,
    min_zoom=10,
    max_zoom=10,
    zoom_control=False,      # removes zoom buttons
    scrollWheelZoom=False,   # disables mouse wheel zoom
    dragging=False,          # disables map dragging
    doubleClickZoom=False,   # disables double-click zoom
    touchZoom=False          # disables touch zoom (mobile)
)

    # Color mapping
    color_dict = {
        "Inner London": "#1f77b4",  # blue
        "Outer London": "#2ca02c"   # green
    }

    def style_function(feature):
        area = feature["properties"]["AreaType"]
        return {
            "fillColor": color_dict.get(area, "gray"),
            "color": "black",
            "weight": 0.8,
            "fillOpacity": 0.7
        }

    # Add GeoJSON layer
    folium.GeoJson(
        boroughs,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME", "AreaType"],
            aliases=["Borough:", "Classification:"]
        )
    ).add_to(m)

    # Add custom legend
    legend_html = """
    <div style="
    position: fixed; 
    bottom: 50px; left: 50px; 
    width: 180px; 
    background-color: white; 
    border:2px solid grey; 
    z-index:9999; 
    font-size:14px;
    padding: 10px;
    ">
    <b>London Classification</b><br>
    <i style="background:#1f77b4;width:12px;height:12px;display:inline-block;"></i> Inner London<br>
    <i style="background:#2ca02c;width:12px;height:12px;display:inline-block;"></i> Outer London
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    # Render
    st.components.v1.html(m._repr_html_(), height=600)
    
# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------


st.header("2. How Are Demand and Response Performance Distributed Across Boroughs?")

st.markdown("""The map below explores geographic patterns across boroughs by examining
incident demand, median response time, and compliance with the 6-minute target.""")

# INTERACTIVE GEOGRAPHIC PERFORMANCE MAP


# Calculate median response time per borough
median_response_by_borough = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")["FirstPumpArriving_AttendanceTime"]
    .median()
    .div(60)
    .reset_index(name="MedianResponseMinutes")
)


# Calculate incident volume per borough
incident_volume_by_borough = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")
    .size()
    .reset_index(name="IncidentCount")
)


median_response_by_borough["IncGeo_BoroughName_clean"] = (
    median_response_by_borough["IncGeo_BoroughName"]
    .str.strip()
    .str.upper()
)

# Merge Median Response Times with Geodataframe
boroughs = boroughs.merge(
    median_response_by_borough,
    left_on="NAME_clean",
    right_on="IncGeo_BoroughName_clean",
    how="left"
)

#Normalize (clean) Borough Names for Merging compliance rate (uppercase + trim)
borough_compliance["NAME_clean"] = (
    borough_compliance["IncGeo_BoroughName"]
    .str.strip()
    .str.upper()
)

# Remove old column if rerun (avoid _x/_y)
boroughs = boroughs.drop(
    columns=["ComplianceRate"],
    errors="ignore"
)

# Merge Compliance Rate with Geodataframe
boroughs = boroughs.merge(
    borough_compliance[["NAME_clean", "ComplianceRate"]],
    on="NAME_clean",
    how="left"
)

# Round Values for Tooltip Display
boroughs["ComplianceRate"] = boroughs["ComplianceRate"].round(1)

# Delete redundant and empty Columns
boroughs = boroughs.drop(columns=[
    "IncGeo_BoroughName_clean",
    "SUB_2009",
    "SUB_2006",
    ], errors="ignore")

# Clean names in incident volume df
incident_volume_by_borough["NAME_clean"] = (
    incident_volume_by_borough["IncGeo_BoroughName"]
    .str.strip()
    .str.upper()
)

# Remove old column if rerun (avoid _x/_y)
boroughs = boroughs.drop(
    columns=["IncidentCount"],
    errors="ignore"
)

# Merge Incident Volume with Geodataframe
boroughs = boroughs.merge(
    incident_volume_by_borough[["NAME_clean", "IncidentCount"]],
    on="NAME_clean",
    how="left"
)

# Metric Toggle
metric_choice = st.radio(
    "Select Geographic Metric",
    ["Median Response Time", "Response within 6 min (%)", "Incident Volume"],
    horizontal=True,
    key="geo_metric_toggle"
)

# # Non-interactive (fixed London view) dashboard map 
m = folium.Map(
    location=[51.5074, -0.1278],
    zoom_start=10,
    min_zoom=10,
    max_zoom=10,
    zoom_control=False,      # removes zoom buttons
    scrollWheelZoom=False,   # disables mouse wheel zoom
    dragging=False,          # disables map dragging
    doubleClickZoom=False,   # disables double-click zoom
    touchZoom=False          # disables touch zoom (mobile
)

# Select Metric
if metric_choice == "Median Response Time":
    value_column = "MedianResponseMinutes"
    legend_name = "Median Response Time (minutes)"
    fill_color = "YlOrRd"

    boroughs["MedianResponse_display"] = (
        boroughs["MedianResponseMinutes"]
        .round(2)
        .astype(str) + " min"
    )

    tooltip_fields = ["NAME", "MedianResponse_display"]
    tooltip_aliases = ["Borough:", "Median Response Time:"]

elif metric_choice == "Response within 6 min (%)":
    value_column = "ComplianceRate"
    legend_name = "Response within 6 min (%)"
    fill_color = "YlGn"

    boroughs["ComplianceRate_display"] = (
        boroughs["ComplianceRate"]
        .round(1)
        .astype(str) + "%"
    )
    
    tooltip_fields = ["NAME", "ComplianceRate_display"]
    tooltip_aliases = ["Borough:", "Compliance Rate:"]

else:  # Incident Volume

    value_column = "IncidentCount"
    legend_name = "Incident Volume"
    fill_color = "Blues"

    boroughs["IncidentVolume_display"] = (
        boroughs["IncidentCount"]
        .astype(int)
        .astype(str)
    )

    tooltip_fields = ["NAME", "IncidentVolume_display"]
    tooltip_aliases = ["Borough:", "Number of Incidents:"]

# Map

# Choropleth Layer
folium.Choropleth(
    geo_data=boroughs,
    data=boroughs,
    columns=["NAME", value_column],
    key_on="feature.properties.NAME",
    fill_color=fill_color,
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name=legend_name
).add_to(m)


# Tooltip Layer 
folium.GeoJson(
    boroughs,
    style_function=lambda x: {
        "fillOpacity": 0,
        "color": "black",
        "weight": 0.5
    },
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        style=(
            "background-color: white;"
            "color: black;"
            "font-family: Arial;"
            "font-size: 12px;"
            "padding: 6px;"
        ),
        localize=True
    )
).add_to(m)


st_folium(m, use_container_width=True, height=600)

# ---------------------------------------------------

# computing values needed for all dynamic map insights 

# Incident Volume
incident_volume_ranked = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")
    .size()
    .reset_index(name="IncidentCount")
    .sort_values("IncidentCount", ascending=False)
)

highest_volume_borough = incident_volume_ranked.iloc[0]["IncGeo_BoroughName"]
highest_volume_val     = incident_volume_ranked.iloc[0]["IncidentCount"]
lowest_volume_borough  = incident_volume_ranked.iloc[-1]["IncGeo_BoroughName"]
lowest_volume_val      = incident_volume_ranked.iloc[-1]["IncidentCount"]

# Median Response Time
rt_ranked = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")["FirstPumpArriving_AttendanceTime"]
    .median()
    .div(60)
    .reset_index(name="MedianResponseMinutes")
    .sort_values("MedianResponseMinutes")
)

fastest_map_borough  = rt_ranked.iloc[0]["IncGeo_BoroughName"]
fastest_map_val      = rt_ranked.iloc[0]["MedianResponseMinutes"]
slowest_map_borough  = rt_ranked.iloc[-1]["IncGeo_BoroughName"]
slowest_map_val      = rt_ranked.iloc[-1]["MedianResponseMinutes"]
rt_map_spread        = slowest_map_val - fastest_map_val

# Compliance Rate
comp_ranked = (
    borough_compliance
    .sort_values("ComplianceRate", ascending=False)
)

highest_comp_map_borough = comp_ranked.iloc[0]["IncGeo_BoroughName"]
highest_comp_map_val     = comp_ranked.iloc[0]["ComplianceRate"]
lowest_comp_map_borough  = comp_ranked.iloc[-1]["IncGeo_BoroughName"]
lowest_comp_map_val      = comp_ranked.iloc[-1]["ComplianceRate"]
comp_map_spread          = highest_comp_map_val - lowest_comp_map_val

# Check whether slowest boroughs are outer London
# (used to make the narrative smarter)
outer_boroughs = borough_df[borough_df["AreaType"] == "Outer London"]["IncGeo_BoroughName"].tolist()
slowest_is_outer = slowest_map_borough in outer_boroughs
lowest_comp_is_outer = lowest_comp_map_borough in outer_boroughs

# ---------------------------------------------------
# Dynamic Map Insights
# Correct insight based on selected metric

if metric_choice == "Incident Volume":
    st.markdown(f"""
**Map Insight**

- Incident demand is most concentrated in **{highest_volume_borough}**
  ({highest_volume_val:,} incidents), reflecting high population density,
  commercial activity, and tourism in central London.
- **{lowest_volume_borough}** records the lowest incident volume
  ({lowest_volume_val:,} incidents).

Despite this central concentration of incidents, slower response performance
is not primarily observed in high-volume boroughs. This suggests that the
number of incidents alone does not explain geographic differences in response times.
""")

elif metric_choice == "Median Response Time":
    outer_note = (
        "confirming that larger outer boroughs face the greatest structural constraints."
        if slowest_is_outer
        else "suggesting a complex interaction between geography and other operational factors."
    )
    st.markdown(f"""
**Map Insight**

- Median response times vary across boroughs, ranging from
  **{fastest_map_val:.2f} min ({fastest_map_borough})**
  to **{slowest_map_val:.2f} min ({slowest_map_borough})**
  ,a spread of **{rt_map_spread:.2f} minutes**.
- Longer response times are clustered in larger outer boroughs,
  while central areas generally demonstrate faster attendance.
- **{slowest_map_borough}** is {'an outer London borough' if slowest_is_outer else 'notable as a non-outer borough'},
  {outer_note}

The geographic pattern of slower performance in outer boroughs contrasts with
the central concentration of high incident numbers, indicating that borough size
and travel distance play a stronger role than incident volume.
""")

elif metric_choice == "Response within 6 min (%)":
    outer_note = (
        "consistent with the structural disadvantage faced by larger outer boroughs."
        if lowest_comp_is_outer
        else "suggesting additional factors beyond geographic size may be at play."
    )
    st.markdown(f"""
**Map Insight**

- 6-minute compliance rates range from
  **{highest_comp_map_val:.1f}% ({highest_comp_map_borough})**
  to **{lowest_comp_map_val:.1f}% ({lowest_comp_map_borough})**
  ,a gap of **{comp_map_spread:.1f} percentage points** across boroughs.
- Higher compliance rates cluster in central boroughs,
  while several outer boroughs show significantly lower target achievement.
- The lowest-performing borough, **{lowest_comp_map_borough}**,
  is {'an outer London borough' if lowest_comp_is_outer else 'notable as a non-outer borough'},
  {outer_note}

This pattern mirrors the distribution of median response times and reinforces
the structural relationship between borough size and response performance.
""")

# ---------------------------------------------------------------------

# Expandable Response Time Ranking

with st.expander("Show Response Time by Borough Ranking"):

    st.subheader("Borough Ranking: Median Response Time")

    # Median berechnen und sauber sortieren
    median_response_by_borough = (
        filtered_incidents
        .groupby("IncGeo_BoroughName")["FirstPumpArriving_AttendanceTime"]
        .median()
        .div(60)
        .reset_index(name="MedianResponseMinutes")
        .sort_values("MedianResponseMinutes", ascending=True)
    )

    sns.set_theme(style="white")

    fig, ax = plt.subplots(figsize=(10, 12))

    # Green (fast) → Red (slow)
    palette = sns.color_palette(
        "RdYlGn_r",   
        n_colors=len(median_response_by_borough)
    )

    sns.barplot(
        data=median_response_by_borough,
        y="IncGeo_BoroughName",
        x="MedianResponseMinutes",
        order=median_response_by_borough["IncGeo_BoroughName"],  
        palette=palette,
        ax=ax
    )

    # 6 Minuten-Reference Line
    ax.axvline(
        6,
        color="black",
        linestyle="--",
        linewidth=1.5,
        alpha=0.7
    )

    # Put Text next to the Reference line (left)
    ax.text(
        5.95,                                 
        -0.8,                                  
        "6 minute target",
        fontsize=10,
        ha="right"
    )

    ax.set_xlabel("Median Response Time (minutes)")
    ax.set_ylabel("")

    sns.despine()
    fig.tight_layout()

    st.pyplot(fig)

    # Dynamic Ranking Insight
    ranking_df = median_response_by_borough.copy()

    top_fast = ranking_df.iloc[0]
    top_slow = ranking_df.iloc[-1]

    spread = (
        top_slow["MedianResponseMinutes"]
        - top_fast["MedianResponseMinutes"]
    )

    st.markdown(f"""
    **Ranking Insight**

    - Fastest borough: **{top_fast['IncGeo_BoroughName']}**
      ({top_fast['MedianResponseMinutes']:.2f} min)

    - Slowest borough: **{top_slow['IncGeo_BoroughName']}**
      ({top_slow['MedianResponseMinutes']:.2f} min)

    - Overall performance spread: **{spread:.2f} minutes**

    Slower response times are common in larger outer boroughs,
    suggesting that geography, not just high demand, is the main
    constraint on response time.
    """)

# ---------------------------------------------------------------------
# Expandable Compliance Rate Ranking

with st.expander("Show Response within 6 min Rate by Borough Ranking"):

    st.subheader("Borough Ranking: Response within 6 min (%)")

    ranking_df = borough_compliance.sort_values(
        "ComplianceRate",
        ascending=False
    )

    fig, ax = plt.subplots(figsize=(10, 12))

    palette = sns.color_palette("RdYlGn_r", len(ranking_df))

    sns.barplot(
        data=ranking_df,
        y="IncGeo_BoroughName",
        x="ComplianceRate",
        order=ranking_df["IncGeo_BoroughName"],
        palette=palette,
        ax=ax
    )

    ax.set_xlabel("Response within 6 min (%)")
    ax.set_ylabel("")

    sns.despine()
    fig.tight_layout()

    st.pyplot(fig)

    # Dynamic Ranking Insight
    top_high = ranking_df.iloc[0]
    top_low  = ranking_df.iloc[-1]
    gap = top_high["ComplianceRate"] - top_low["ComplianceRate"]

    st.markdown(f"""
    **Ranking Insight**

    - Highest compliance: **{top_high['IncGeo_BoroughName']}** ({top_high['ComplianceRate']:.1f}%)
    - Lowest compliance: **{top_low['IncGeo_BoroughName']}** ({top_low['ComplianceRate']:.1f}%)
    - Compliance differs by up to **{gap:.1f} percentage points** across boroughs.

    Compliance rates vary considerably across boroughs. The fact that lower performance is concentrated
    in larger outer boroughs highlights the impact of geographic scale on response times.
    """)
# ---------------------------------------------------------------------
# Expandable Incident Volume Ranking

with st.expander("Incident Volume by Borough Ranking"):

    st.subheader("Borough Ranking: Incident Volume")

    incident_volume_by_borough = (
        filtered_incidents
        .groupby("IncGeo_BoroughName")
        .size()
        .reset_index(name="IncidentCount")
        .sort_values("IncidentCount", ascending=False)  
    )

    fig, ax = plt.subplots(figsize=(10, 12))

    sns.barplot(
        data=incident_volume_by_borough,
        y="IncGeo_BoroughName",
        x="IncidentCount",
        order=incident_volume_by_borough["IncGeo_BoroughName"],
        palette="Blues_r",   
        ax=ax
    )

    ax.set_xlabel("Number of Incidents")
    ax.set_ylabel("")

    sns.despine()

    st.pyplot(fig)


    # Dynamic Ranking Insight

    highest_borough = incident_volume_by_borough.iloc[0]
    lowest_borough = incident_volume_by_borough.iloc[-1]

    spread = (
        highest_borough["IncidentCount"]
        - lowest_borough["IncidentCount"]
    )

    st.markdown(f"""
    **Ranking Insight**

    - Highest incident volume: **{highest_borough['IncGeo_BoroughName']}** ({highest_borough['IncidentCount']:,})
    - Lowest incident volume: **{lowest_borough['IncGeo_BoroughName']}** ({lowest_borough['IncidentCount']:,})
    - Volume spread: **{spread:,} incidents**

    While incident demand is concentrated in central boroughs due to high population density, commerce, and tourism,
    incident volume doesn’t necessarily lead to slower response times.
    """)


# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------


st.header("3. What Drives Geographic Differences in Response Time?")

st.markdown("""The relationship between borough size and response performance
is analysed to assess whether geographic size acts as a driver of performance differences.""")

# ---------------------------------------------------------------------
# Borough Size vs. Median Response Time by Area Type
# Investigates structural relationship between geographic size and performance

st.subheader("3.1 Borough Size vs. Median Response Time by Area Type")


# Linear Regression (Borough Area vs Median Response Time
slope, intercept, r_value, p_value, std_err = linregress(
    borough_df["Area_km2"],
    borough_df["MedianResponseMinutes"]
)

# Statistical calculations
r = r_value
p = p_value
r_squared = r_value ** 2
r_squared_percent = r_squared * 100

x_range = np.linspace(
    borough_df["Area_km2"].min(),
    borough_df["Area_km2"].max(),
    100
)

y_range = slope * x_range + intercept



# Within-group regression (Inner vs Outer London)
_, _, r_inner_val, p_inner, _ = linregress(
    inner_df["Area_km2"],
    inner_df["MedianResponseMinutes"]
)

_, _, r_outer_val, p_outer, _ = linregress(
    outer_df["Area_km2"],
    outer_df["MedianResponseMinutes"]
)



# Colorblind-friendly palette
inner_color = sns.color_palette("colorblind")[1]
outer_color = sns.color_palette("colorblind")[2]



# Create scatter plot
fig = go.Figure()



# Inner London scatter
fig.add_trace(go.Scatter(
    x=inner_df["Area_km2"],
    y=inner_df["MedianResponseMinutes"],
    mode="markers",
    marker=dict(
        size=12,
        color="#1f77b4",
        line=dict(width=1.2, color="black"),
        opacity=0.85
    ),
    name="Inner London",
    customdata=np.stack(
        (
            inner_df["NAME_clean"],
            inner_df["Area_km2"],
            inner_df["MedianResponseMinutes"],
            inner_df["AreaType"]
        ),
        axis=-1
    ),
    hovertemplate=
    "<b>%{customdata[0]}</b><br><br>" +
    "Median Response Time: %{customdata[2]:.1f} min<br>" +
    "Area: %{customdata[1]:.1f} km²<br>" +
    "Area Type: %{customdata[3]}" +
    "<extra></extra>"
))



# Outer London scatter
fig.add_trace(go.Scatter(
    x=outer_df["Area_km2"],
    y=outer_df["MedianResponseMinutes"],
    mode="markers",
    marker=dict(
        size=12,
        color="#ff7f0e",
        line=dict(width=1.2, color="black"),
        opacity=0.85
    ),
    name="Outer London",
    customdata=np.stack(
        (
            outer_df["NAME_clean"],
            outer_df["Area_km2"],
            outer_df["MedianResponseMinutes"],
            outer_df["AreaType"]
        ),
        axis=-1
    ),
    hovertemplate=
       "<b>%{customdata[0]}</b><br><br>" +
       "Median Response Time: %{customdata[2]:.1f} min<br>" +
       "Area: %{customdata[1]:.1f} km²<br>" +
       "Area Type: %{customdata[3]}" +
       "<extra></extra>"
))

# Regression line
fig.add_trace(go.Scatter(
    x=x_range,
    y=y_range,
    mode="lines",
    line=dict(color="black", width=2),
    showlegend=False   
))

# Layout
fig.update_layout(
    height=650,
    xaxis_title="Borough Area (km²)",
    yaxis_title="Median Response Time (minutes)",
    template="simple_white",
    legend_title_text="Area Type"
)

fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False)

st.plotly_chart(fig, use_container_width=True)


# Regression Summary Table 
def format_p(p):
    return "< 0.001" if p < 0.001 else f"{p:.4f}"


def interpret_strength(r):
    abs_r = abs(r)
    if abs_r >= 0.7:
        return "Strong"
    elif abs_r >= 0.4:
        return "Moderate"
    elif abs_r >= 0.2:
        return "Weak"
    else:
        return "Very weak"


def significance_label(p):
    return "Yes" if p < 0.05 else "No"

def interpret_direction(r):
    return "Negative" if r < 0 else "Positive"


summary_table = pd.DataFrame({
    "Group": [
        "All Boroughs",
        "Inner London",
        "Outer London"
    ],
    "Correlation (r)": [
        round(r, 2),
        round(r_inner_val, 2),
        round(r_outer_val, 2)
    ],
    "R²": [
        round(r_squared, 2),
        round(r_inner_val**2, 2),
        round(r_outer_val**2, 2)
    ],
    "p-value": [
        format_p(p),
        format_p(p_inner),
        format_p(p_outer)
    ],
    "Statistically Significant (α = 0.05)": [
        significance_label(p),
        significance_label(p_inner),
        significance_label(p_outer)
    ],
    "Effect Strength": [
        interpret_strength(r),
        interpret_strength(r_inner_val),
        interpret_strength(r_outer_val)
    ]
})

with st.expander("Show Regression Summary (Statistical Details)"):

    col1, col2, col3 = st.columns(3)


    # All Boroughs
    with col1:
        st.markdown("### All Boroughs")
        st.metric("Correlation (r)", f"{r:.2f}")
        st.metric("R²", f"{r_squared:.2f}")
        st.metric("p-value", format_p(p))
        st.metric("Statistically Significant", significance_label(p))
        st.metric("Effect Strength", interpret_strength(r))
        st.metric("Effect Direction", interpret_direction(r))


    # Inner London
    with col2:
        st.markdown("### Inner London")
        st.metric("Correlation (r)", f"{r_inner_val:.2f}")
        st.metric("R²", f"{r_inner_val**2:.2f}")
        st.metric("p-value", format_p(p_inner))
        st.metric("Statistically Significant", significance_label(p_inner))
        st.metric("Effect Strength", interpret_strength(r_inner_val))
        st.metric("Effect Direction", interpret_direction(r_inner_val))


    # Outer London
    with col3:
        st.markdown("### Outer London")
        st.metric("Correlation (r)", f"{r_outer_val:.2f}")
        st.metric("R²", f"{r_outer_val**2:.2f}")
        st.metric("p-value", format_p(p_outer))
        st.metric("Statistically Significant", significance_label(p_outer))
        st.metric("Effect Strength", interpret_strength(r_outer_val))
        st.metric("Effect Direction", interpret_direction(r_outer_val))

# ---------------------------------------------------------------------
# Dynamic Markdown

significance_text = (
    "statistically significant"
    if p < 0.05
    else "not statistically significant"
)

significance_inner = (
    "statistically significant"
    if p_inner < 0.05
    else "not statistically significant"
)

significance_outer = (
    "statistically significant"
    if p_outer < 0.05
    else "not statistically significant"
)


st.markdown(f"""
**Key Insights**

- Borough size is {interpret_strength(r).lower()} and {interpret_direction(r).lower()} with median response time 
  **(r = {r:.2f}, R² = {r_squared:.2f})**, explaining approximately 
  **{r_squared_percent:.0f}%** of the observed variation 
  **(p {format_p(p)}; {significance_text})**.
- The positive relationship remains observable within both groups,
  Inner London **(r = {r_inner_val:.2f}; {significance_inner})** and 
  Outer London **(r = {r_outer_val:.2f}; {significance_outer})**.
- This suggests that borough size contributes to response performance 
  regardless of structural classification.
""")

# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------
st.subheader("3.2 Borough Size vs. Response within 6 Minute (%)")

df_comp = borough_df

# Regression
slope_c, intercept_c, r_c, p_c, std_err_c = linregress(
    df_comp["Area_km2"],
    df_comp["ComplianceRate"]
)

r2_c = r_c ** 2

# Interpretation helpers for expander
strength_c = (
    "very strong" if abs(r_c) >= 0.7 else
    "strong" if abs(r_c) >= 0.5 else
    "moderate" if abs(r_c) >= 0.3 else
    "weak"
)

direction_c = "Negative" if r_c < 0 else "Positive"

significance_c = (
    "statistically significant"
    if p_c < 0.05
    else "not statistically significant"
)

x_range_c = np.linspace(
    df_comp["Area_km2"].min(),
    df_comp["Area_km2"].max(),
    100
)

y_range_c = slope_c * x_range_c + intercept_c

fig_comp = go.Figure()

# Scatter
fig_comp.add_trace(go.Scatter(
    x=df_comp["Area_km2"],
    y=df_comp["ComplianceRate"],
    mode="markers",
    marker=dict(
        size=12,
        color=df_comp["ComplianceRate"],
        colorscale="YlGn",
        line=dict(width=1, color="black"),
        opacity=0.8,
        colorbar=dict(title="Response within 6 min (%)")
    ),
    text=df_comp["IncGeo_BoroughName"],
    hovertemplate=
        "<b>%{text}</b><br><br>" +
        "Response within 6 min: %{y:.1f}%<br>" +
        "Area: %{x:.1f} km²<br>" +
        "<extra></extra>",
    showlegend=False
))

# Regression line
fig_comp.add_trace(go.Scatter(
    x=x_range_c,
    y=y_range_c,
    mode="lines",
    line=dict(color="black", width=2),
    showlegend=False
))

fig_comp.update_layout(
    height=600,
    xaxis_title="Borough Area (km²)",
    yaxis_title="Response within 6-min Rate (%)",
    template="simple_white"
)

st.plotly_chart(fig_comp)


# Regression Summary Expander (Statistical Details)
with st.expander("Show Regression Summary (Statistical Details)"):

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Correlation (r)", f"{r_c:.2f}")
        st.metric("R²", f"{r2_c:.2f}")
        st.metric("p-value", f"{format_p(p_c)}")
        
    with col2:
        st.metric("Statistically Significant", "Yes" if p_c < 0.05 else "No" )
        st.metric("Effect Strength", strength_c.capitalize())
        st.metric("Effect Direction", direction_c)

# ----------------------------------------------------------
# Dynamic Markdown Size vs Compliance

strength_c = (
    "very strong" if abs(r_c) >= 0.7 else
    "strong" if abs(r_c) >= 0.5 else
    "moderate" if abs(r_c) >= 0.3 else
    "weak"
)

significance_c = (
    "statistically significant"
    if p_c < 0.05
    else "not statistically significant"
)

st.markdown(f"""

**Key Insights**

- The relationship between borough size and 6 minute compliance is **{strength_c} and {direction_c}**
(r = {r_c:.2f}, R² = {r2_c:.2f}).
- This indicates that the impact of borough size is not limited to response time but is also associated with lower target compliance.
- The effect is **{significance_c}** (p {format_p(p_c)}), indicating that larger boroughs are less likely to meet the 6 minute response target.
""")

# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------

st.markdown(f"""
### Key Takeaway

- Borough size is the primary driver of geographic variation in response performance,
  strongly associated with both longer response times (r = {r:.2f}) 
  and lower 6-minute compliance (r = {r_c:.2f}).
""")


st.markdown("---")
st.caption(
    "London Fire Brigade Response Time & Operational Performance Analysis (2021-2025) · Andrés Lill · February 2026"
)
