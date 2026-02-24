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

if selected_year == "All":
    year_text = "All Years"
else:
    year_text = selected_year

if selected_month == "All":
    month_text = "All Months"
else:
    month_text = selected_month

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

st.caption(f"Data shown: {period_label}")

# ------------------------------------------------------------
# Convert filtered_df(mobilisation level) to incident level (first pump only)

filtered_incidents = (
    filtered_df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

#st.write("Filtered DF rows:", len(filtered_df))
#st.write("Unique IncidentNumber in filtered_df:", filtered_df["IncidentNumber"].nunique())
#st.write("Filtered incidents rows:", len(filtered_incidents))
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

# Borough-level medians
borough_decomp = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")
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
**Key Insights**

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
    .groupby("IncGeo_BoroughName")["TurnoutMinutes"]
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
        .groupby("IncGeo_BoroughName")
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
st.header("2. How does Hour of Day influence Response Time")

st.markdown("""Hourly response time patterns are analysed to assess whether
            turnout or travel time drives performance fluctuations throughout the day.
            """)

st.subheader("Turnout vs Travel Time by Hour of Day")

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

st.markdown(f"""

**Key Insights**

- Travel time drives hourly performance variation, fluctuating by approximately **{travel_range:.2f} minutes** across the day
  and peaking around **{peak_hour}:00**.
- Turnout time remains comparatively stable, with a variation of **{turnout_range:.2f} minutes**.
- This pattern conirms that performance differences are linked to travel constraints rather than station mobilisation.


""")



# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------


st.header("3. Why Do Incidents Exceed the 6-Minute Target?")

st.markdown("""Delay codes for incidents exceeding the 6-minute response target are analysed
to distinguish routine travel constraints from exceptional delays.
""")
# ---------------------------------------------------------------------

st.subheader("3.1 Breakdown of Recorded Delay Factors")

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
    .groupby("DelayCode_Description")
    .size()
    .reset_index(name="IncidentCount")
    .sort_values("IncidentCount", ascending=False)
)

delay_counts["DelayCode_Description"] = delay_counts["DelayCode_Description"].replace(
    {"No delay": "No recorded delay code"}
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

**Key Insights**

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
st.markdown("---")
# ---------------------------------------------------------------------

# ------------------------------------------------------------
st.subheader("3.2 Geographic Distribution of “Not held up” Exceedances?")

st.markdown(
    "To examine whether delay reasons vary by location, the map below shows "
    "the distribution of exceedances classified as “Not held up” across boroughs."
    )

# Exceedances with recorded delay

exceed_df = filtered_incidents[
    (filtered_incidents["FirstPumpArriving_AttendanceTime"] > 360) &
    (filtered_incidents["DelayCode_Description"].notna())
].copy()

#  Not held up exeedances
exceed_df["IsNotHeldUp"] = (
    exceed_df["DelayCode_Description"] == "Not held up"
)

# Borough-level aggregation
borough_notheld = (
    exceed_df
    .groupby("IncGeo_BoroughName", as_index=False)
    .agg(
        Exceedances=("IncidentNumber", "size"),
        NotHeldUp_Count=("IsNotHeldUp", "sum"),
        NotHeldUp_Rate=("IsNotHeldUp", "mean")
    )
)

borough_notheld["NotHeldUp_Rate"] *= 100


# create NAME_clean for merge 
borough_notheld["NAME_clean"] = (
    borough_notheld["IncGeo_BoroughName"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# Clean borough names for merging
boroughs["NAME_clean"] = (
    boroughs["NAME"]
    .str.strip()
    .str.upper()
)

# Merge into GeoDataframe

# Remove previous merge columns (in case of reruns)
boroughs = boroughs.drop(
    columns=["Exceedances", "NotHeldUp_Count", "NotHeldUp_Rate"],
    errors="ignore"
)

boroughs = boroughs.merge(
    borough_notheld[
        ["NAME_clean", "Exceedances", "NotHeldUp_Count", "NotHeldUp_Rate"]
    ],
    on="NAME_clean",
    how="left"
)

# Clean missing values
boroughs["Exceedances"] = boroughs["Exceedances"].fillna(0).astype(int)
boroughs["NotHeldUp_Count"] = boroughs["NotHeldUp_Count"].fillna(0).astype(int)
boroughs["NotHeldUp_Rate"] = boroughs["NotHeldUp_Rate"].fillna(0).round(1)

# Tooltip display
boroughs["NotHeldUp_Rate_display"] = (
    boroughs["NotHeldUp_Rate"].astype(str) + "%"
)

# Map

metric = st.radio(
    "Map metric",
    ["Not held up count", "Not held up rate (%)"],
    horizontal=True
)

m = folium.Map(
    location=[51.5074, -0.1278],
    zoom_start=10,
    min_zoom=10,
    max_zoom=10,
    zoom_control=False,
    scrollWheelZoom=False,
    dragging=False,
    doubleClickZoom=False,
    touchZoom=False
)

if metric == "Not held up count":
    value_col = "NotHeldUp_Count"
    legend_name = "Not held up (count)"
    fill_color = "Blues"
    tooltip_fields = ["NAME", "NotHeldUp_Count", "Exceedances"]
    tooltip_aliases = ["Borough:", "Not held up:", "Total exceedances:"]

else:
    value_col = "NotHeldUp_Rate"
    legend_name = "Not held up (% of exceedances)"
    fill_color = "YlOrRd"
    tooltip_fields = ["NAME", "NotHeldUp_Rate_display", "Exceedances"]
    tooltip_aliases = ["Borough:", "Not held up rate:", "Total exceedances:"]

folium.Choropleth(
    geo_data=boroughs,
    data=boroughs,
    columns=["NAME", value_col],
    key_on="feature.properties.NAME",
    fill_color=fill_color,
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name=legend_name
).add_to(m)

folium.GeoJson(
    boroughs,
    style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 0.5},
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        localize=True
    )
).add_to(m)

st_folium(m, use_container_width=True, height=600)

# Map insight

if metric == "Not held up count":

    top_row = borough_notheld.sort_values(
        "NotHeldUp_Count", ascending=False
    ).head(1)

    if not top_row.empty:
        st.markdown(f"""
            **Map Insight**
            - The highest number of “Not held up” exceedances is in 
             **{top_row.iloc[0]['IncGeo_BoroughName']}** 
             ({int(top_row.iloc[0]['NotHeldUp_Count']):,} incidents).
            - This concentration in larger outer boroughs confirms that borogh size
             is a major factor contributing to 6-minute target exceedances.
        """)

else:  # Not held up rate (%)

    top_row = borough_notheld.sort_values(
        "NotHeldUp_Rate", ascending=False
    ).head(1)

    if not top_row.empty:
        st.markdown(f"""
            -**Map Insight:** The highest percentage of exceedances recorded as “Not held up” 
            is in **{top_row.iloc[0]['IncGeo_BoroughName']}** 
            ({top_row.iloc[0]['NotHeldUp_Rate']:.1f}% of exceedances).
            -Higher proportions in several larger outer boroughs align with the relationship between
            borough size, travel distance, and response performance identified earlier.
        """)

# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------
### Key Takeaways:


st.markdown(f"""
### Key Takeaways

- Travel time accounts for **{travel_share_pct:.0f}%** of median response time,
  confirming it as the primary driver of geographic and hourly variation.
- Turnout time remains stable across boroughs (IQR: {turnout_iqr_sec:.0f} s),
  while travel time varies considerably (IQR: {travel_iqr_sec:.0f} s).
- **{not_held_up_percent:.1f}%** of 6-minute exceedances have no recorded delay reason,
  suggesting structural rather than operational causes.
""")




# Current calculation (sum of medians)
#overall_turnout = filtered_incidents["TurnoutMinutes"].median()
#overall_travel = filtered_incidents["TravelMinutes"].median()
#total_component = overall_turnout + overall_travel
#travel_share_pct_current = (overall_travel / total_component) * 100

# Alternative calculation (median of sum)
#total_attendance = filtered_incidents["TravelMinutes"].add(
#    filtered_incidents["TurnoutMinutes"]
#).median()
#travel_share_pct_alternative = (overall_travel / total_attendance) * 100

# Display
#col1, col2, col3, col4 = st.columns(4)
#col1.metric("Median Turnout", f"{overall_turnout:.2f} min")
#col2.metric("Median Travel", f"{overall_travel:.2f} min")
#col3.metric("Travel Share (sum of medians)", f"{travel_share_pct_current:.1f}%")
#col4.metric("Travel Share (median of sum)", f"{travel_share_pct_alternative:.1f}%")

#st.write(f"**Sum of medians:** {total_component:.3f} min")
#st.write(f"**Median of sum:** {total_attendance:.3f} min")
#st.write(f"**Difference:** {abs(total_component - total_attendance):.3f} min")


#st.write(f"**Median turnout:** {overall_turnout:.3f} min")
#st.write(f"**Median travel:**  {overall_travel:.3f} min")

