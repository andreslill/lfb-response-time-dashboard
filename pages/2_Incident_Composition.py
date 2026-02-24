import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from data_loader import load_data

# ---------------------------------------------------------------------
# theme

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

st.title("Incident Composition")

st.markdown("""
This section analyses the structural composition of incidents, 
including workload distribution and temporal patterns.
""")

df = load_data()

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
selected_year = st.sidebar.selectbox(
    "Select Year",
    options=available_years
)

# Month filter
selected_month = st.sidebar.selectbox(
    "Select Month",
    options=available_months
)

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

# ---------------------------------------------------------------------
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
# Total incidents

total_incidents = len(filtered_incidents)

st.markdown(
    f"<span style='font-size:16px;'><b>{total_incidents:,}</b> incidents analysed in the selected period.</span>",
    unsafe_allow_html=True
)
# ---------------------------------------------------------------------
# Barplot 


st.subheader("Incident Mix Distribution (%)")

st.markdown("<br>", unsafe_allow_html=True) # space

incident_mix = (
    filtered_incidents["IncidentGroup"]
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
    .reset_index()
)

incident_mix.columns = ["IncidentGroup", "Percentage"]

# Sort incident types
order = ["Fire", "Special Service", "False Alarm"]

incident_mix["IncidentGroup"] = pd.Categorical(
    incident_mix["IncidentGroup"],
    categories=order,
    ordered=True
)

incident_mix = incident_mix.sort_values("IncidentGroup")

fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT_SMALL))

colors = [
    sns.color_palette("colorblind")[1],  # Fire
    sns.color_palette("colorblind")[2],  # Special Service
    sns.color_palette("colorblind")[0],  # False Alarm
]

bars = ax.barh(
    incident_mix["IncidentGroup"],
    incident_mix["Percentage"],
    color=colors
)

# Value labels
for bar in bars:
    width = bar.get_width()
    ax.text(
        width + 0.5,
        bar.get_y() + bar.get_height() / 2,
        f"{width:.1f}%",
        va="center"
    )

ax.set_xlabel("Percentage of Total Incidents")
ax.set_ylabel("")
ax.set_xlim(0, 100)

style_axes(ax)
sns.despine(ax=ax)
fig.tight_layout()

st.pyplot(fig)


# Dynamic Markdown

# Calculate shares
incident_share = (
    filtered_incidents["IncidentGroup"]
    .value_counts(normalize=True)
    .mul(100)
    .round(1)
)

false_alarm_share = incident_share.get("False Alarm", 0)
special_service_share = incident_share.get("Special Service", 0)
fire_share = incident_share.get("Fire", 0)

st.markdown(f"""
    **Key Insights**

- Nearly **{100 - fire_share}%** of deployments are non-fire related.
- False Alarms dominate the workload and shape overall demand patterns.
- The imbalance between fire and non-fire incidents highlights
  the importance of understanding workload composition when evaluating
  response performance.
""")


# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------
# Lineplot

st.subheader("Monthly Incident Trends by Incident Type")

st.markdown("<br>", unsafe_allow_html=True) # space

# legend
spacer, col1, col2, col3, col4 = st.columns([0.4, 1, 1, 1, 1])

col1.markdown("<span style='color:black;'>●</span> All Incidents", unsafe_allow_html=True)
col2.markdown("<span style='color:#1f77b4;'>●</span> False Alarm", unsafe_allow_html=True)
col3.markdown("<span style='color:#2ca02c;'>●</span> Special Service", unsafe_allow_html=True)
col4.markdown("<span style='color:#ff7f0e;'>●</span> Fire", unsafe_allow_html=True)

# Monthly incident counts by incident type
monthly_incidents_by_type = (
    filtered_incidents
    .groupby(["Month", "IncidentGroup"])["IncidentNumber"]
    .size()
    .reset_index(name="IncidentCount")
)

# Monthly incident counts across all incident types
monthly_incidents_total = (
    filtered_incidents
    .groupby("Month")["IncidentNumber"]
    .size()
    .reset_index(name="IncidentCount")
)

# Label totals so they can be plotted together with incident types
monthly_incidents_total["IncidentGroup"] = "All Incidents"

# Combine into long format
monthly_incident_counts_long = pd.concat(
    [monthly_incidents_by_type, monthly_incidents_total],
    ignore_index=True
)

palette = {
    "All Incidents": "black",
    "False Alarm": sns.color_palette("colorblind")[0],
    "Fire": sns.color_palette("colorblind")[1],
    "Special Service": sns.color_palette("colorblind")[2],
}

sns.set_theme(style="white") # removes grid automatically

fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT_MEDIUM))

hue_order = [
    "All Incidents",
    "False Alarm",
    "Special Service",
    "Fire"
]

# Plot all incident types EXCEPT totals
sns.lineplot(
    data=monthly_incident_counts_long[monthly_incident_counts_long["IncidentGroup"] != "All Incidents"],
    x="Month",
    y="IncidentCount",
    hue="IncidentGroup",
    hue_order=hue_order[1:],  # exclude All Incidents
    palette=palette,
    linewidth=2.5,
    marker="o",
    alpha=0.7,
    ax=ax,
    legend=False,
)

# Plot ALL INCIDENTS separately with thicker line
sns.lineplot(
    data=monthly_incident_counts_long[monthly_incident_counts_long["IncidentGroup"] == "All Incidents"],
    x="Month",
    y="IncidentCount",
    color="black",
    linewidth=4,
    alpha=1,
    ax=ax,
    legend=False
)

ax.set_xlabel("Month")
ax.set_ylabel("Number of Incidents")

ax.set_xticks(range(1, 13))
ax.set_xticklabels(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])

style_axes(ax)
sns.despine(ax=ax)
fig.tight_layout()

st.pyplot(fig, use_container_width=True)

# Dynamic Markdown

# month order
month_order = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

#  Monthly totals (All Incidents) 
monthly_totals = (
    filtered_incidents
    .groupby("MonthName")
    .size()
    .reindex(month_order)
    .dropna()
)

peak_month = monthly_totals.idxmax()
low_month = monthly_totals.idxmin()

peak_value = int(monthly_totals.max())
low_value = int(monthly_totals.min())

if low_value > 0:
    seasonal_range_pct = round(((peak_value - low_value) / low_value) * 100, 1)
else:
    seasonal_range_pct = 0

# Fire 
monthly_fire = (
    filtered_incidents[filtered_incidents["IncidentGroup"] == "Fire"]
    .groupby("MonthName")
    .size()
    .reindex(month_order)
    .dropna()
)

fire_peak_month = monthly_fire.idxmax()
fire_peak_value = int(monthly_fire.max())

# Month with highest Fire share relative to total incidents
monthly_fire_share = (
    filtered_incidents[filtered_incidents["IncidentGroup"] == "Fire"]
    .groupby("MonthName")
    .size()
    .reindex(month_order)
    .dropna()
    .div(
        filtered_incidents.groupby("MonthName").size().reindex(month_order).dropna()
    )
    .mul(100)
    .round(1)
)

fire_share_peak_month = monthly_fire_share.idxmax()
fire_share_peak_val   = monthly_fire_share.max()
fire_share_low_month  = monthly_fire_share.idxmin()
fire_share_low_val    = monthly_fire_share.min()

# False Alarm 
monthly_false = (
    filtered_incidents[filtered_incidents["IncidentGroup"] == "False Alarm"]
    .groupby("MonthName")
    .size()
    .reindex(month_order)
    .dropna()
)

false_peak_month = monthly_false.idxmax()
false_peak_value = int(monthly_false.max())


# Special Service 
monthly_special = (
    filtered_incidents[filtered_incidents["IncidentGroup"] == "Special Service"]
    .groupby("MonthName")
    .size()
    .reindex(month_order)
    .dropna()
)

special_peak_month = monthly_special.idxmax()
special_peak_value = int(monthly_special.max())


st.markdown(f"""
 **Seasonal Insights**

- Overall incident demand peaks in **{peak_month} ({peak_value:,})** and reaches its lowest level in **{low_month} ({low_value:,})**,
  representing a seasonal variation of approximately **{seasonal_range_pct}%**.
- False alarms follow a similar demand curve, with the highest number of incidents observed in **{false_peak_month} ({false_peak_value:,})**.
- Special Services also display slight seasonal variation, with a peak in **{special_peak_month} ({special_peak_value:,})**.
- Fire-related incidents show a pronounced concentration in summer, peaking in **{fire_peak_month} ({fire_peak_value:,})**,
  suggesting potential seasonal drivers.
- Fire incidents represent their **largest share of the monthly workload in {fire_share_peak_month}**
  ({fire_share_peak_val:.1f}% of all incidents that month), compared to only **{fire_share_low_val:.1f}%
  in {fire_share_low_month}**, a {round(fire_share_peak_val - fire_share_low_val, 1)} percentage point
  seasonal shift in fire risk.
""")




# ---------------------------------------------------------------------
st.markdown("---")
# ---------------------------------------------------------------------
# Heatmap

st.subheader("Daily and Hourly Incident Heatmap")

incident_options = [
    "All",
    "False Alarm",
    "Special Service",
    "Fire"
]

selected_incident_type = st.radio(
    "Incident Type",
    options=incident_options,
    horizontal=True
)

# Filter
if selected_incident_type == "All":
    heatmap_df = filtered_incidents.copy()
else:
    heatmap_df = filtered_incidents[
        filtered_incidents["IncidentGroup"] == selected_incident_type
    ]

# Pivot table (Hour x Weekday)
daily_hourly_incidents = heatmap_df.pivot_table(
    index="HourOfCall",
    columns="Weekday",
    values="IncidentNumber",
    aggfunc="nunique"
)

weekday_order = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]

daily_hourly_incidents = (
    daily_hourly_incidents
    .reindex(index=range(24))          # ensure 0–23
    .reindex(columns=weekday_order)    # Monday → Sunday
    .fillna(0)
    .T                                 # 🔁 swap axes
)

# -------------------------
# Plot
# -------------------------

fig, ax = plt.subplots(figsize=(FIG_WIDTH, 10))

sns.heatmap(
    daily_hourly_incidents,
    cmap="coolwarm",
    square=True,
    linewidths=0.3,
    linecolor="white",
    cbar_kws={"label": "Number of Incidents",
              "shrink": 0.2},
    ax=ax
)

ax.set_xlabel("Hour of Call")
ax.set_ylabel("Day of Week")

ax.title.set_fontsize(10)
ax.title.set_weight("bold")

ax.xaxis.label.set_size(13)
ax.yaxis.label.set_size(13)

ax.tick_params(axis="both", labelsize=10)

cbar = ax.collections[0].colorbar
cbar.ax.tick_params(labelsize=10)
cbar.set_label("Number of Incidents", fontsize=13)

fig.tight_layout()

st.pyplot(fig)

# ---------------------------------------------------------------------
# Dynamic Markdown – Heatmap

# Peak hour and day for selected incident type
heatmap_long = heatmap_df.groupby(["Weekday", "HourOfCall"]).size().reset_index(name="Count")

# Peak hour overall
hourly_totals = heatmap_df.groupby("HourOfCall").size()
peak_hour     = int(hourly_totals.idxmax())
peak_hour_val = int(hourly_totals.max())
low_hour      = int(hourly_totals.idxmin())
low_hour_val  = int(hourly_totals.min())

# Peak day overall
daily_totals  = heatmap_df.groupby("Weekday").size().reindex(weekday_order).dropna()
peak_day      = daily_totals.idxmax()
peak_day_val  = int(daily_totals.max())
low_day       = daily_totals.idxmin()
low_day_val   = int(daily_totals.min())

# Peak hour-day combination
peak_combo    = heatmap_long.loc[heatmap_long["Count"].idxmax()]
peak_combo_day  = peak_combo["Weekday"]
peak_combo_hour = int(peak_combo["HourOfCall"])
peak_combo_val  = int(peak_combo["Count"])

# Night hours (0–6) vs daytime (7–22)
night_avg = hourly_totals[hourly_totals.index <= 6].mean()
day_avg   = hourly_totals[(hourly_totals.index >= 7) & (hourly_totals.index <= 22)].mean()
day_night_ratio = round(day_avg / night_avg, 1) if night_avg > 0 else 0

# Weekend vs weekday
weekdays_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
weekend_list  = ["Saturday", "Sunday"]

weekday_avg = daily_totals[daily_totals.index.isin(weekdays_list)].mean()
weekend_avg = daily_totals[daily_totals.index.isin(weekend_list)].mean()
weekend_diff_pct = round(((weekend_avg - weekday_avg) / weekday_avg) * 100, 1) if weekday_avg > 0 else 0
weekend_pattern  = "higher" if weekend_diff_pct > 0 else "lower"

# Incident type label for text
type_label = selected_incident_type if selected_incident_type != "All" else "overall"

st.markdown(f"""
**Key Insights**

- **{type_label.capitalize()} incidents** peak at **{peak_hour:02d}:00**
  ({peak_hour_val:,} incidents) and are lowest at **{low_hour:02d}:00** ({low_hour_val:,} incidents).
- The busiest single hour-day combination is **{peak_combo_day} at {peak_combo_hour:02d}:00**
  ({peak_combo_val:,} incidents).
- Daytime demand (**07:00–22:00**) averages **{day_night_ratio}x** more incidents per hour
  than the night period (00:00–06:00).
- **{peak_day}** is the busiest day of the week ({peak_day_val:,} incidents),
  while **{low_day}** records the lowest volume ({low_day_val:,} incidents).
- Weekend incident volumes are **{abs(weekend_diff_pct):.1f}% {weekend_pattern}**
  than the weekday average, suggesting {"higher leisure and social activity driving demand"
  if weekend_diff_pct > 0 else "reduced commercial and occupational activity at weekends"}.
""")




