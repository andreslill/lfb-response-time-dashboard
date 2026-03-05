# pages/7_Scenario_Explorer.py
import streamlit as st
from data_loader import load_data
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

st.set_page_config(layout="wide")
sns.set_theme(style="white", context="notebook")

FIG_WIDTH = 10

# ---------------------------------------------------------------------
# Header
st.title("Scenario Explorer")
st.markdown(
    "**How much would 6-min Compliance Rate improve under uniform time reductions?**  \n"
    "Select a borough and apply a uniform reduction (seconds) to incident response times — "
    "recalculated from the actual incident-level data (2021–2025)."
)
st.markdown("---")

# ---------------------------------------------------------------------
# Load data
df = load_data()

has_travel = "TravelTimeSeconds" in df.columns
has_turnout = "TurnoutTimeSeconds" in df.columns

# First pump only, full dataset (no year/month filter — maximum sample)
incidents = (
    df.sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

# Helpful derived fields (if present)
if has_travel:
    incidents["TravelMinutes"] = incidents["TravelTimeSeconds"] / 60
if has_turnout:
    incidents["TurnoutMinutes"] = incidents["TurnoutTimeSeconds"] / 60

# City-wide baseline (used for comparison)
city_within_6 = (incidents["FirstPumpArriving_AttendanceTime"] <= 360).mean() * 100
city_median = incidents["FirstPumpArriving_AttendanceTime"].median() / 60

# ---------------------------------------------------------------------
# Borough selector
boroughs_list = sorted(incidents["IncGeo_BoroughName"].dropna().unique())
selected_borough = st.selectbox("Select a Borough", boroughs_list)

borough_df = incidents[incidents["IncGeo_BoroughName"] == selected_borough].copy()

# Current borough stats
current_within_6 = (borough_df["FirstPumpArriving_AttendanceTime"] <= 360).mean() * 100
current_median = borough_df["FirstPumpArriving_AttendanceTime"].median() / 60
n_incidents = len(borough_df)
n_over_target = (borough_df["FirstPumpArriving_AttendanceTime"] > 360).sum()

# Travel/turnout context (where available)
attendance_median_sec = float(borough_df["FirstPumpArriving_AttendanceTime"].median())

if has_travel:
    median_travel_sec = float(borough_df["TravelTimeSeconds"].median())
    median_turnout_sec = float(borough_df["TurnoutTimeSeconds"].median()) if has_turnout else None
    travel_share = (median_travel_sec / attendance_median_sec * 100) if attendance_median_sec > 0 else np.nan
else:
    # Fallback: 77% travel / 23% turnout heuristic (only used if travel isn't present)
    median_travel_sec = attendance_median_sec * 0.77
    median_turnout_sec = attendance_median_sec * 0.23
    travel_share = 77.0

st.caption(f"{n_over_target:,} incidents exceeded 6 minutes in 2021–2025 for this borough.")

# ---------------------------------------------------------------------
# KPIs
st.subheader(f"Current Performance: {selected_borough.title()}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Incidents analysed", f"{n_incidents:,}")
c2.metric(
    "Response within 6 min",
    f"{current_within_6:.1f}%",
    delta=f"{current_within_6 - city_within_6:+.1f} pp vs London avg",
)
c3.metric("Median response time", f"{current_median:.2f} min")
c4.metric(
    "Median travel time",
    f"{median_travel_sec/60:.2f} min",
    delta=f"{travel_share:.0f}% of total response" if np.isfinite(travel_share) else "—",
)

st.markdown("---")

# ---------------------------------------------------------------------
# Simulator controls
st.subheader("Scenario: Uniform time reduction")
st.markdown(
    "Move the slider to apply a uniform reduction (seconds) to every incident response time in this borough. "
    "The page recalculates  6-min compliance rate and median response time from the underlying incident data."
)

col_slider, col_note = st.columns([3, 1])
with col_slider:
    time_reduction_sec = st.slider(
        "Uniform time reduction (seconds)",
        min_value=0,
        max_value=300,
        value=0,
        step=5,
        help="Example: 30s could represent faster routing, small coverage improvements, or reduced delays in travel-related components.",
    )

with col_note:
    denom = median_travel_sec if (median_travel_sec and median_travel_sec > 0) else None
    reduction_pct_of_median_travel = (time_reduction_sec / denom * 100) if denom else 0.0

    st.markdown(
        f"""
        <div style="background:#f8f9fa; border-radius:8px; padding:12px; margin-top:28px; font-size:0.85rem; color:#374151;">
        Median travel time:<br><strong>{median_travel_sec/60:.2f} min ({median_travel_sec:.0f}s)</strong><br><br>
        Reduction = <strong>{reduction_pct_of_median_travel:.1f}%</strong> of median travel
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# Calculate simulated outcome
# NOTE: This is a uniform reduction applied to recorded attendance times (not a route/station model).
borough_df["SimulatedTime"] = (
    borough_df["FirstPumpArriving_AttendanceTime"] - time_reduction_sec
).clip(lower=0)

new_within_6 = (borough_df["SimulatedTime"] <= 360).mean() * 100
new_median = borough_df["SimulatedTime"].median() / 60

within_gain_pp = new_within_6 - current_within_6
median_gain_sec = (current_median - new_median) * 60  # positive means improvement

additional_within_total = int(round(within_gain_pp / 100 * n_incidents))

# "Per year" estimate (since borough_df spans 2021–2025)
if "Year" in borough_df.columns:
    n_years = int(borough_df["Year"].nunique())
else:
    n_years = 5  

additional_within_per_year = int(round(additional_within_total / n_years)) if n_years > 0 else additional_within_total

# ---------------------------------------------------------------------
# Results
st.markdown("---")
st.subheader("Simulated outcome")

r1, r2, r3, r4 = st.columns(4)
r1.metric("% Current response within 6 min (%)", f"{current_within_6:.1f}%")
r2.metric(
    "Simulated response within 6 minutes (%)",
    f"{new_within_6:.1f}%",
    delta=f"{within_gain_pp:+.1f} pp" if within_gain_pp != 0 else "No change",
)
r3.metric("Median response (current)", f"{current_median:.2f} min")
r4.metric(
    "Median response (simulated)",
    f"{new_median:.2f} min",
    delta=f"−{median_gain_sec:.0f}s" if median_gain_sec > 0 else ("No change" if median_gain_sec == 0 else f"+{abs(median_gain_sec):.0f}s"),
)

# Highlight card
if time_reduction_sec > 0:
    st.markdown(
        f"""
        <div style="
            background-color: #f0fdf4;
            border-left: 5px solid #16a34a;
            padding: 14px 20px;
            border-radius: 6px;
            margin: 16px 0;
        ">
            <strong>Impact:</strong>
            A uniform <strong>{time_reduction_sec}s</strong> reduction would bring an additional
            <strong>~{additional_within_per_year:,} incidents</strong> within the 6-minute target
            <strong>per year</strong> in <strong>{selected_borough.title()}</strong> —
            increasing <strong>% within 6 minutes</strong> from <strong>{current_within_6:.1f}%</strong>
            to <strong>{new_within_6:.1f}%</strong>
            ({within_gain_pp:+.1f} percentage points).
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# Before / After Histogram
st.subheader("Response time distribution: before vs after")

response_before = borough_df["FirstPumpArriving_AttendanceTime"] / 60
response_after = borough_df["SimulatedTime"] / 60

fig, ax = plt.subplots(figsize=(FIG_WIDTH, 4))
bins = np.linspace(0, 15, 40)

ax.hist(response_before, bins=bins, alpha=0.5, color="#6b7280", label="Current", density=True)
ax.hist(
    response_after,
    bins=bins,
    alpha=0.7,
    color="#3b6fd4",
    label=f"Simulated (−{time_reduction_sec}s)",
    density=True,
)

ax.axvline(6, color="red", linestyle="--", linewidth=2, label="6-minute target")
ax.axvline(current_median, color="#6b7280", linestyle=":", linewidth=1.5, label=f"Current median ({current_median:.2f} min)")
if time_reduction_sec > 0:
    ax.axvline(new_median, color="#3b6fd4", linestyle=":", linewidth=1.5, label=f"Simulated median ({new_median:.2f} min)")

ax.set_xlim(0, 15)
ax.set_xlabel("Attendance time (minutes)")
ax.set_ylabel("Density")
ax.legend(frameon=False, fontsize=10)
ax.set_title(f"{selected_borough.title()} — Response time distribution", fontweight="bold", fontsize=14)
sns.despine()
fig.tight_layout()
st.pyplot(fig)

st.markdown("---")

# ---------------------------------------------------------------------
# Breakeven Analysis: what reduction is needed to hit 70%, 75%, 80%, 85%?
st.subheader("Breakeven analysis")
st.markdown("At what uniform time reduction would this borough reach common thresholds for **% within 6 minutes**?")

targets = [70.0, 75.0, 80.0, 85.0]
results = []

for target in targets:
    if current_within_6 >= target:
        results.append({"Target": f"{target:.0f}%", "Reduction needed": "Already achieved", "Incidents gained": "—"})
        continue

    found = False
    for r in range(0, 301, 5):
        sim = (borough_df["FirstPumpArriving_AttendanceTime"] - r).clip(lower=0)
        within = (sim <= 360).mean() * 100
        if within >= target:
            gained_total = int(round((within - current_within_6) / 100 * n_incidents))
            gained_per_year = int(round(gained_total / n_years)) if n_years > 0 else gained_total

            results.append(
                {
                    "Target": f"{target:.0f}%",
                    "Reduction needed": f"{r}s ({r/60:.1f} min)",
                    "Incidents gained (per year)": f"~{gained_per_year:,}",
                }
            )
            found = True
            break

    if not found:
        results.append({"Target": f"{target:.0f}%", "Reduction needed": "Not achievable within 5 min reduction", "Incidents gained (per year)": "—"})

breakeven_df = pd.DataFrame(results)
st.table(breakeven_df.set_index("Target"))

st.markdown("---")

# ---------------------------------------------------------------------
# Borough comparison: where does the selected borough rank?
st.subheader("Context: how does this borough compare?")
st.markdown(
    "<div style='color:#6b7280; font-size:0.85rem; margin-bottom:10px;'>"
    "All boroughs ranked by <strong>% within 6 minutes</strong> · Full dataset 2021–2025"
    "</div>",
    unsafe_allow_html=True,
)

all_borough_within = (
    incidents.groupby("IncGeo_BoroughName")["FirstPumpArriving_AttendanceTime"]
    .apply(lambda x: (x <= 360).mean() * 100)
    .reset_index(name="Within6Rate")
    .sort_values("Within6Rate", ascending=True)  # slowest first
)

bar_colors = [
    "#3b6fd4" if borough_name == selected_borough else ("#2a9d8f" if value >= city_within_6 else "#e5e7eb")
    for borough_name, value in zip(all_borough_within["IncGeo_BoroughName"], all_borough_within["Within6Rate"])
]

fig2, ax2 = plt.subplots(figsize=(FIG_WIDTH, max(5, len(all_borough_within) * 0.38)))

ax2.barh(all_borough_within["IncGeo_BoroughName"], all_borough_within["Within6Rate"], color=bar_colors)
ax2.axvline(city_within_6, color="black", linestyle="--", linewidth=1.5, label=f"London average ({city_within_6:.1f}%)")

# Label only the selected borough
sel_val = float(all_borough_within.loc[all_borough_within["IncGeo_BoroughName"] == selected_borough, "Within6Rate"].values[0])
sel_idx = list(all_borough_within["IncGeo_BoroughName"]).index(selected_borough)
ax2.text(sel_val + 0.5, sel_idx, f"{sel_val:.1f}%", va="center", fontsize=9, color="#3b6fd4", fontweight="bold")

legend_patches = [
    mpatches.Patch(color="#3b6fd4", label=f"Selected: {selected_borough.title()}"),
    mpatches.Patch(color="#2a9d8f", label="Above London average"),
    mpatches.Patch(color="#e5e7eb", label="Below London average"),
]
ax2.legend(handles=legend_patches, frameon=False, fontsize=9, loc="lower right")

ax2.set_xlabel("% within 6 minutes")
ax2.set_ylabel("")
ax2.set_xlim(0, 105)
sns.despine()
fig2.tight_layout()
st.pyplot(fig2)

# Rank (1 = slowest), because we sorted ascending
rank_slowest = sel_idx + 1
total_boroughs = len(all_borough_within)

st.markdown(
    f"**{selected_borough.title()}** ranks **{rank_slowest} of {total_boroughs}** boroughs "
    f"(1 = slowest). London average: **{city_within_6:.1f}%**."
)

st.markdown("---")
st.markdown(
    """
    <div style="padding-left:12px; border-left:3px solid #e5e7eb; color:#6b7280; font-size:0.85rem;">
    <strong>Methodology note:</strong> This scenario applies a uniform time reduction (seconds) to each incident’s recorded
    attendance time and recalculates <strong>% within 6 minutes</strong> and medians. It does <em>not</em> model routing,
    station location, or incident geography directly. Real-world improvements would vary by incident.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")
st.caption("London Fire Brigade Response Time Analysis (2021–2025) · Andrés Lill · February 2026")
