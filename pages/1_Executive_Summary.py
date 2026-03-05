# page/1_Executive_Summary.py

import streamlit as st
from data_loader import load_data
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# ---------------------------------------------------------------------
# Theme
st.set_page_config(layout="wide")
sns.set_theme(style="white", context="notebook")

# ---------------------------------------------------------------------
# Plot constants
FIG_WIDTH      = 10
FIG_HEIGHT_SMALL  = 3.5
FIG_HEIGHT_MEDIUM = 4.5
FIG_HEIGHT_LARGE  = 6

def style_axes(ax):
    ax.title.set_fontsize(16)
    ax.title.set_weight("bold")
    ax.xaxis.label.set_size(13)
    ax.yaxis.label.set_size(13)
    ax.tick_params(axis="both", which="major", labelsize=11)

# ---------------------------------------------------------------------
# Title
st.title("Executive Summary")
st.markdown("London Fire Brigade Response Performance (2021–2025)")
st.markdown("""
*Note: In this dashboard, "Response Time" refers to First Pump Attendance Time (time from call
to arrival of the first pump).*
""")

# ---------------------------------------------------------------------
# Core Finding
st.markdown(
    """
    <div style="
        background-color: #f0f4ff;
        border-left: 5px solid #3b6fd4;
        padding: 16px 20px;
        border-radius: 6px;
        margin-bottom: 20px;
    ">
        <strong style="font-size: 1.05rem;">Core Finding</strong><br>
        <span style="font-size: 0.97rem; color: #1f2937;">
        <strong>Geography is the main driver of variation across London</strong>. 
        Borough area explains 59% of differences, with travel time accounting for 
        ~77% of total response time, while turnout is largely stable across stations.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Load Data
df = load_data()

# ---------------------------------------------------------------------
# Filters
st.sidebar.header("Filters")

available_years = ["All"] + sorted(df["Year"].unique())
available_months = ["All"] + [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

selected_year     = st.sidebar.selectbox("Select Year",  options=available_years)
selected_month    = st.sidebar.selectbox("Select Month", options=available_months)
incident_options  = ["All"] + sorted(df["IncidentGroup"].dropna().unique())
selected_incident = st.sidebar.selectbox(
    "Select Incident Type",
    options=incident_options,
    key="exec_incident"
)

# ---------------------------------------------------------------------
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

if selected_incident != "All":
    filtered_df = filtered_df[filtered_df["IncidentGroup"] == selected_incident]

if filtered_df.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# Dynamic labels
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

incident_label = "All Incident Types" if selected_incident == "All" else f"{selected_incident} Incidents"

# ---------------------------------------------------------------------
# Incident level (first pump only)
filtered_incidents = (
    filtered_df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

# ---------------------------------------------------------------------
# KPIs
total_incidents       = len(filtered_incidents)
median_response       = filtered_incidents["FirstPumpArriving_AttendanceTime"].median() / 60
response_within_6min  = (filtered_incidents["FirstPumpArriving_AttendanceTime"] <= 360).mean() * 100
p90_response          = filtered_incidents["FirstPumpArriving_AttendanceTime"].quantile(0.90) / 60
extreme_delay_rate    = (filtered_incidents["FirstPumpArriving_AttendanceTime"] > 600).mean() * 100

st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Incidents",                  f"{total_incidents:,}")
col2.metric("Median Response Time (min)",       f"{median_response:.2f} min")
col3.metric("90th Percentile (min)",            f"{p90_response:.2f} min")
col4.metric("Response within 6 min (%)",        f"{response_within_6min:.1f}%")
col5.metric(">10 min Delays (%)",               f"{extreme_delay_rate:.1f}%")
st.markdown("---")

# ---------------------------------------------------------------------
# 1. Distribution of Response Time
st.subheader("Distribution of Response Time")

st.markdown(
    f"""
    <div style='margin-top:-10px; margin-bottom:2px; color:#6b7280; font-size:0.85rem;'>
    Data shown: {period_label}, {incident_label}
    </div>
    <div style='margin-top:0px; margin-bottom:10px; color:#9ca3af; font-size:0.8rem;'>
    Note: X-axis capped at 15 minutes for readability. 0.5% of incidents exceed this threshold.
    </div>
    """,
    unsafe_allow_html=True,
)

response_minutes = filtered_incidents["FirstPumpArriving_AttendanceTime"] / 60
median = response_minutes.median()
mean   = response_minutes.mean()
p90    = response_minutes.quantile(0.90)

fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT_SMALL))
sns.histplot(response_minutes, bins=25, kde=False, stat="percent", ax=ax)
ax.axvline(6,      color="red",    linestyle="--", linewidth=2,   label=f"6-min target")
ax.axvline(median, color="black",  linewidth=2,                   label=f"Median ({median:.2f})")
ax.axvline(mean,   color="blue",   linestyle="--",                label=f"Mean ({mean:.2f})")
ax.axvline(p90,    color="purple", linestyle=":",                 label=f"P90 ({p90:.2f})")
ax.set_xlim(0, 15)
ax.set_xlabel("Attendance Time (minutes)")
ax.set_ylabel("Share of Incidents (%)")
style_axes(ax)
ax.legend(frameon=False, fontsize=11)
sns.despine()
fig.tight_layout()
st.pyplot(fig)

above_target    = 100 - response_within_6min
mean_median_gap = round(mean - median, 2)
st.markdown(f"""
- The 6-minute target is met in **{response_within_6min:.1f}%** of incidents, meaning **{above_target:.1f}%** exceed it.
- The mean ({mean:.2f} min) is **{mean_median_gap:.2f} min above the median ({median:.2f} min)**.
- Extreme delays above 10 minutes affect **{extreme_delay_rate:.1f}%** of incidents{", well within acceptable range." if extreme_delay_rate < 5 else ", exceeding the 5% warning threshold."}
""")

st.markdown("---")

# ---------------------------------------------------------------------
# 2. Compliance Trend by Year
# Always uses full unfiltered dataset so trend is always visible
st.subheader("Compliance Trend by Year (2021–2025)")
st.markdown(
    "<div style='color:#6b7280; font-size:0.85rem; margin-bottom:10px;'>"
    "Data shown: All years, " + incident_label + 
    " . Trend is shown unfiltered by year to preserve temporal context."
    "</div>",
    unsafe_allow_html=True,
)

# Build yearly trend from full dataset (filter incident type only)
trend_df = df.copy()
if selected_incident != "All":
    trend_df = trend_df[trend_df["IncidentGroup"] == selected_incident]

trend_incidents = (
    trend_df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

yearly_trend = (
    trend_incidents
    .groupby("Year")["FirstPumpArriving_AttendanceTime"]
    .apply(lambda x: (x <= 360).mean() * 100)
    .reset_index(name="ComplianceRate")
)
yearly_trend["MedianResponse"] = (
    trend_incidents
    .groupby("Year")["FirstPumpArriving_AttendanceTime"]
    .median()
    .values / 60
)

fig, ax1 = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT_SMALL))

color_compliance = "#3b6fd4"
color_median     = "#e05c2e"

# Compliance line (left axis)
ax1.plot(
    yearly_trend["Year"], yearly_trend["ComplianceRate"],
    marker="o", linewidth=2.5, color=color_compliance, label="Compliance (%)"
)
ax1.set_xlabel("Year")
ax1.set_ylabel("Response within 6 min (%)", color=color_compliance)
ax1.tick_params(axis="y", labelcolor=color_compliance)
ax1.set_ylim(
    max(0,  yearly_trend["ComplianceRate"].min() - 5),
    min(100, yearly_trend["ComplianceRate"].max() + 5)
)
# Annotate compliance values
for _, row in yearly_trend.iterrows():
    ax1.annotate(
        f"{row['ComplianceRate']:.1f}%",
        (row["Year"], row["ComplianceRate"]),
        textcoords="offset points", xytext=(0, 8), ha="center", fontsize=10, color=color_compliance
    )

# Median response line (right axis)
ax2 = ax1.twinx()
ax2.plot(
    yearly_trend["Year"], yearly_trend["MedianResponse"],
    marker="s", linewidth=2.5, linestyle="--", color=color_median, label="Median Response (min)"
)
ax2.set_ylabel("Median Response Time (min)", color=color_median)
ax2.tick_params(axis="y", labelcolor=color_median)
ax2.set_ylim(
    yearly_trend["MedianResponse"].min() - 0.3,
    yearly_trend["MedianResponse"].max() + 0.3
)
for _, row in yearly_trend.iterrows():
    ax2.annotate(
        f"{row['MedianResponse']:.2f}",
        (row["Year"], row["MedianResponse"]),
        textcoords="offset points", xytext=(0, -15), ha="center", fontsize=10, color=color_median
    )

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, frameon=False, fontsize=10, loc="lower left")

ax1.set_xticks(yearly_trend["Year"])
sns.despine(right=False)
fig.tight_layout()
st.pyplot(fig)

# Dynamic trend insight
best_year  = yearly_trend.loc[yearly_trend["ComplianceRate"].idxmax()]
worst_year = yearly_trend.loc[yearly_trend["ComplianceRate"].idxmin()]
trend_dir  = (
    "improving" if yearly_trend.iloc[-1]["ComplianceRate"] > yearly_trend.iloc[0]["ComplianceRate"]
    else "declining" if yearly_trend.iloc[-1]["ComplianceRate"] < yearly_trend.iloc[0]["ComplianceRate"]
    else "stable"
)
st.markdown(f"""
- Overall compliance trend is **{trend_dir}** over the observed period.
- Best year: **{int(best_year['Year'])}** with **{best_year['ComplianceRate']:.1f}%** compliance.
- Worst year: **{int(worst_year['Year'])}** with **{worst_year['ComplianceRate']:.1f}%** compliance.
""")

st.markdown("---")

# ---------------------------------------------------------------------
# 3. Borough Performance: Top 5 vs Bottom 5
st.subheader("Borough Performance: Best vs. Worst")
st.markdown(
    f"<div style='color:#6b7280; font-size:0.85rem; margin-bottom:10px;'>"
    f"Data shown: {period_label}, {incident_label}"
    f"</div>",
    unsafe_allow_html=True,
)

borough_compliance = (
    filtered_incidents
    .groupby("IncGeo_BoroughName")["FirstPumpArriving_AttendanceTime"]
    .apply(lambda x: (x <= 360).mean() * 100)
    .reset_index(name="ComplianceRate")
    .sort_values("ComplianceRate", ascending=False)
)

top5    = borough_compliance.head(5).copy().reset_index(drop=True)
bottom5 = borough_compliance.tail(5).sort_values("ComplianceRate", ascending=True).copy().reset_index(drop=True)

fig, (ax_top, ax_bot) = plt.subplots(1, 2, figsize=(FIG_WIDTH, 5.5))

# Top 5 — green
sns.barplot(
    data=top5,
    y="IncGeo_BoroughName",
    x="ComplianceRate",
    order=top5["IncGeo_BoroughName"],   # ← fixes phantom categories
    palette=["#2a9d8f"] * 5,
    ax=ax_top
)
ax_top.set_title("Top 5 Boroughs", fontweight="bold")
ax_top.set_xlabel("6-min Compliance (%)")
ax_top.set_ylabel("")
ax_top.set_xlim(0, 105)
for i, v in enumerate(top5["ComplianceRate"]):
    ax_top.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=10)
sns.despine(ax=ax_top)

# Bottom 5 — red
sns.barplot(
    data=bottom5,
    y="IncGeo_BoroughName",
    x="ComplianceRate",
    order=bottom5["IncGeo_BoroughName"],  # ← fixes phantom categories
    palette=["#e76f51"] * 5,
    ax=ax_bot
)
ax_bot.set_title("Bottom 5 Boroughs", fontweight="bold")
ax_bot.set_xlabel("6-min Compliance (%)")
ax_bot.set_ylabel("")
ax_bot.set_xlim(0, 105)
for i, v in enumerate(bottom5["ComplianceRate"]):
    ax_bot.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=10)
sns.despine(ax=ax_bot)

fig.tight_layout(pad=3.0)
st.pyplot(fig)

compliance_gap = top5.iloc[0]["ComplianceRate"] - bottom5.iloc[0]["ComplianceRate"]
st.markdown(f"""
- The best-performing borough (**{top5.iloc[0]['IncGeo_BoroughName'].title()}**, {top5.iloc[0]['ComplianceRate']:.1f}%) outperforms the worst (**{bottom5.iloc[0]['IncGeo_BoroughName'].title()}**, {bottom5.iloc[0]['ComplianceRate']:.1f}%) by **{compliance_gap:.1f} percentage points**.
- Geographic variation, not operational differences, is the primary driver — larger outer boroughs face longer travel distances.
""")

st.markdown("---")

# ---------------------------------------------------------------------
# 4. Compliance by Incident Type
st.subheader("6-Minute Compliance by Incident Type")
st.markdown(
    f"<div style='color:#6b7280; font-size:0.85rem; margin-bottom:10px;'>"
    f"Data shown: {period_label}, All Incident Types"
    f"</div>",
    unsafe_allow_html=True,
)

# Always show all incident types regardless of incident filter
incident_df = df.copy()
if selected_year != "All" and selected_month == "All":
    incident_df = incident_df[incident_df["Year"] == selected_year]
elif selected_year == "All" and selected_month != "All":
    incident_df = incident_df[incident_df["MonthName"] == selected_month]
elif selected_year != "All" and selected_month != "All":
    incident_df = incident_df[
        (incident_df["Year"] == selected_year) &
        (incident_df["MonthName"] == selected_month)
    ]

incident_level = (
    incident_df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

# Fix categorical order
incident_level["IncidentGroup"] = pd.Categorical(
    incident_level["IncidentGroup"],
    categories=["False Alarm", "Special Service", "Fire"],
    ordered=True
)

# Compliance per incident type (≤ 6 min only)
compliance_by_type = (
    incident_level
    .groupby("IncidentGroup", observed=True)["FirstPumpArriving_AttendanceTime"]
    .apply(lambda x: (x <= 360).mean() * 100)
    .reset_index(name="ComplianceRate")
)

# Overall average compliance for reference line
overall_avg = (incident_level["FirstPumpArriving_AttendanceTime"] <= 360).mean() * 100

# Plot — simple horizontal bar, green only, no grey remnants
fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT_SMALL))

bar_colors = [
    sns.color_palette("colorblind")[0],  # False Alarm
    sns.color_palette("colorblind")[2],  # Special Service
    sns.color_palette("colorblind")[1],  # Fire
]

bars = ax.barh(
    compliance_by_type["IncidentGroup"],
    compliance_by_type["ComplianceRate"],
    color=bar_colors
)

# Label inside bar
for bar, value in zip(bars, compliance_by_type["ComplianceRate"]):
    ax.text(
        bar.get_width() / 2,
        bar.get_y() + bar.get_height() / 2,
        f"{value:.1f}%",
        ha="center",
        va="center",
        color="white",
        fontsize=10,
        weight="bold"
    )

# Reference line
ax.axvline(
    overall_avg,
    color="black",
    linestyle="--",
    linewidth=1.5
)

# Label above the top bar (not overlapping)
ax.text(
    overall_avg + 0.8,
    2.45,                      # above top bar
    f"Avg: {overall_avg:.1f}%",
    fontsize=9,
    va="bottom",
    color="black"
)

ax.set_xlim(0, 100)
ax.set_xlabel("Percentage of Incidents within 6-Minute Response Target (%)")
ax.set_ylabel("")
ax.invert_yaxis()
style_axes(ax)
sns.despine()
fig.tight_layout()
st.pyplot(fig)

# Dynamic insights
best_type  = compliance_by_type.loc[compliance_by_type["ComplianceRate"].idxmax(), "IncidentGroup"]
worst_type = compliance_by_type.loc[compliance_by_type["ComplianceRate"].idxmin(), "IncidentGroup"]
best_val   = compliance_by_type.loc[compliance_by_type["ComplianceRate"].idxmax(), "ComplianceRate"]
worst_val  = compliance_by_type.loc[compliance_by_type["ComplianceRate"].idxmin(), "ComplianceRate"]
type_gap   = best_val - worst_val

st.markdown(f"""
- **{best_type}** incidents have the highest 6-minute compliance at **{best_val:.1f}%**.
- **{worst_type}** incidents have the lowest at **{worst_val:.1f}%** — a gap of **{type_gap:.1f} percentage points**.
- Incident type explains some variation, but geographic factors remain the dominant driver.
""")
