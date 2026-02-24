import streamlit as st
from data_loader import load_data
import pandas as pd

# ------------------------------------------------------------
# Page config + theme

st.set_page_config(layout="wide")

# ---------------------------------------------------------------------
#Title + Intro

st.title("🔍 Key Findings & Implications")
st.markdown(
    "This page summarises the main findings from the London Fire Brigade "
    "Incident & Response Time Analysis. All metrics update dynamically based on the selected filters."
)

# ---------------------------------------------------------------------
# Load Data

df = load_data()

# ---------------------------------------------------------------------
# Year and Month Filters

st.sidebar.header("Filters")

available_years = ["All"] + sorted(df["Year"].unique())
available_months = ["All"] + [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
incident_options = ["All"] + sorted(df["IncidentGroup"].dropna().unique())

selected_year     = st.sidebar.selectbox("Select Year",          options=available_years)
selected_month    = st.sidebar.selectbox("Select Month",         options=available_months)
selected_incident = st.sidebar.selectbox("Select Incident Type", options=incident_options, key="kf_incident")

# ---------------------------------------------------------------------
# Apply Filters

if selected_year == "All" and selected_month == "All":
    filtered_df = df.copy()
elif selected_year == "All":
    filtered_df = df[df["MonthName"] == selected_month]
elif selected_month == "All":
    filtered_df = df[df["Year"] == selected_year]
else:
    filtered_df = df[(df["Year"] == selected_year) & (df["MonthName"] == selected_month)]

if selected_incident != "All":
    filtered_df = filtered_df[filtered_df["IncidentGroup"] == selected_incident]

if filtered_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# Dynamic Period Label

min_year = df["Year"].min()
max_year = df["Year"].max()

if selected_year == "All" and selected_month == "All":
    period_label = f"{min_year}–{max_year}"
elif selected_year != "All" and selected_month == "All":
    period_label = str(selected_year)
elif selected_year == "All" and selected_month != "All":
    period_label = f"{selected_month} ({min_year}–{max_year})"
else:
    period_label = f"{selected_month} {selected_year}"

incident_label = "All Incident Types" if selected_incident == "All" else f"{selected_incident} Incidents"

st.caption(f"Data shown: {period_label}, {incident_label}")

# ---------------------------------------------------------------------
# Incident-level datasets

filtered_incidents = (
    filtered_df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

# Unfiltered incident-level (for composition + compliance by type)
all_incidents = (
    df
    .sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)

# ------------------------------------------------------------

# KPIs
total_incidents    = len(filtered_incidents)
median_response    = filtered_incidents["FirstPumpArriving_AttendanceTime"].median() / 60
p90_response       = filtered_incidents["FirstPumpArriving_AttendanceTime"].quantile(0.90) / 60
compliance_6min    = filtered_incidents["FirstPump_Within_6min"].mean() * 100
extreme_delay_rate = (filtered_incidents["FirstPumpArriving_AttendanceTime"] > 600).mean() * 100

# Incident composition, full dataset for context
incident_counts     = all_incidents["IncidentGroup"].value_counts(normalize=True) * 100
pct_false_alarm     = incident_counts.get("False Alarm", 0)
pct_special_service = incident_counts.get("Special Service", 0)
pct_fire            = incident_counts.get("Fire", 0)
pct_non_fire        = pct_false_alarm + pct_special_service

# Compliance by incident type, full dataset
compliance_by_type = (
    all_incidents
    .groupby("IncidentGroup")["FirstPump_Within_6min"]
    .mean() * 100
)
comp_fa = compliance_by_type.get("False Alarm", float("nan"))
comp_ss = compliance_by_type.get("Special Service", float("nan"))
comp_fi = compliance_by_type.get("Fire", float("nan"))

# Travel / Turnout decomposition (filtered) 
median_turnout  = filtered_incidents["TurnoutTimeSeconds"].median() / 60
median_travel   = filtered_incidents["TravelTimeSeconds"].median() / 60
total_component = median_turnout + median_travel
travel_share    = (median_travel / total_component * 100) if total_component > 0 else float("nan")

# Borough performance (filtered) 
# Auto-detect borough column name
borough_col = None
for col in ["IncGeo_BoroughName", "BoroughName", "Borough", "IncidentStationGround", "borough_name"]:
    if col in filtered_incidents.columns:
        borough_col = col
        break

if borough_col:
    borough_stats = (
        filtered_incidents
        .groupby(borough_col)
        .agg(
            median_rt  =("FirstPumpArriving_AttendanceTime", "median"),
            compliance =("FirstPump_Within_6min", "mean")
        )
        .dropna()
    )
    borough_stats["compliance"] = borough_stats["compliance"] * 100
else:
    borough_stats = pd.DataFrame()

borough_available = not borough_stats.empty
if borough_available:
    fastest_borough      = borough_stats["median_rt"].idxmin()
    fastest_time         = borough_stats["median_rt"].min() / 60
    slowest_borough      = borough_stats["median_rt"].idxmax()
    slowest_time         = borough_stats["median_rt"].max() / 60
    rt_spread            = slowest_time - fastest_time
    highest_comp_borough = borough_stats["compliance"].idxmax()
    highest_comp_val     = borough_stats["compliance"].max()
    lowest_comp_borough  = borough_stats["compliance"].idxmin()
    lowest_comp_val      = borough_stats["compliance"].min()
    compliance_spread    = highest_comp_val - lowest_comp_val

# Inner vs Outer London (filtered) 
inner_outer_available = False
if "InnerOuter" in filtered_incidents.columns:
    io_stats     = filtered_incidents.groupby("InnerOuter")["FirstPumpArriving_AttendanceTime"].median() / 60
    inner_median = io_stats.get("Inner London", None)
    outer_median = io_stats.get("Outer London", None)
    if inner_median is not None and outer_median is not None:
        io_gap_sec            = (outer_median - inner_median) * 60
        io_gap_pct            = (outer_median - inner_median) / inner_median * 100
        inner_outer_available = True

# Delay codes (filtered, exceedances only) 
exceedances       = filtered_incidents[filtered_incidents["FirstPumpArriving_AttendanceTime"] > 360]
total_exceedances = len(exceedances)
pct_exceedances   = (total_exceedances / total_incidents * 100) if total_incidents > 0 else 0

delay_available = False
delay_col       = None
for col in ["DelayCode_Description", "DelayCodeDescription", "DelayCode"]:
    if col in exceedances.columns:
        delay_col = col
        break

if delay_col and not exceedances.empty:
    delay_counts    = exceedances[delay_col].value_counts(normalize=True) * 100
    pct_not_held_up = delay_counts.get("Not held up", delay_counts.get("Not Held Up", 0))
    delay_available = True

# =====================================================================

st.markdown("---")


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Incidents",      f"{total_incidents:,}")
c2.metric("Median Response Time", f"{median_response:.2f} min")
c3.metric("6-min Compliance",     f"{compliance_6min:.1f}%")
c4.metric("90th Percentile",      f"{p90_response:.2f} min")
c5.metric(">10 min Delays",       f"{extreme_delay_rate:.1f}%")

st.markdown("---")

# ------------------------------------------------------------
# 1: 
st.header("1. Overall Performance: Stable but Uneven")

meets_target   = "broadly meets" if compliance_6min >= 65 else "shows strain against"
median_vs_6    = "sits below"    if median_response < 6  else "exceeds"
p90_vs_10      = "comfortably meets" if p90_response <= 10 else "exceeds"
delay_vs_ceil  = "well below"    if extreme_delay_rate < 5  else "above"

st.markdown(f"""
At the selected level of aggregation, the LFB **{meets_target}** its official benchmarks:

- The **median response time of {median_response:.2f} min** {median_vs_6} the 6-minute primary target.
- **{compliance_6min:.1f}% of incidents** are attended within 6 minutes, meaning roughly
  **{100 - compliance_6min:.1f}% exceed the target**.
- The **90th percentile of {p90_response:.2f} min** {p90_vs_10} the secondary 10-minute benchmark.
- Only **{extreme_delay_rate:.1f}% of incidents** exceed 10 minutes, {delay_vs_ceil} the 10% ceiling.

These aggregate figures can mask substantial variation at the borough level, pointing to
structural performance gaps not visible in city-wide summaries.
""")

st.markdown("---")

#  2: only shown when no incident type filter is active 
if selected_incident == "All":
    st.header("2. Incident Composition: Mostly Non-Fire")
    fire_ratio = round(100 / pct_fire) if pct_fire > 0 else "many"
    st.markdown(f"""
The LFB's workload is dominated by non-fire incidents (based on the full 2021–2025 dataset):

- **False Alarms: {pct_false_alarm:.1f}%** of all incidents: the single largest category.
- **Special Service: {pct_special_service:.1f}%**
- **Fire: {pct_fire:.1f}%**: less than 1 in {fire_ratio} deployments involves a fire.
- Nearly **{pct_non_fire:.1f}% of all deployments are non-fire-related**.

**Implication:** Performance benchmarks and resource planning should account for workload
composition. False Alarms drive high incident volumes but represent operationally
simpler deployments compared to fires or special services.
""")
    st.markdown("---")

# 3: only shown when no incident type filter is active 
if selected_incident == "All":
    st.header("3. Response Performance Differs Across Incident Types")
    st.markdown(f"""
Not all incident types are attended equally fast (based on the full 2021–2025 dataset):

- **False Alarms** record the highest 6-min compliance: **{comp_fa:.1f}%**, reflecting
  simpler operational conditions and more accessible locations.
- **Special Service** incidents consistently record the longest response times,
  with compliance at only **{comp_ss:.1f}%**.
- **Fire** incidents sit in between at **{comp_fi:.1f}%** compliance.

The relative ranking between incident types remains stable throughout the year.

**Implication:** Differences across incident types reflect operational complexity,
not performance failures. Evaluating compliance without controlling for incident type
can produce misleading conclusions.
""")
    st.markdown("---")

# 4:
if borough_available:
    st.header("4. Geography is the Primary Performance Driver")

    io_text = ""
    if inner_outer_available:
        io_text = (
            f"- **Outer London** has a median response time of **{outer_median:.2f} min** vs. "
            f"**{inner_median:.2f} min** for Inner London — a gap of "
            f"**{io_gap_sec:.0f} seconds ({io_gap_pct:.1f}%)**.\n"
        )

    st.markdown(f"""
Borough-level analysis reveals a strong structural pattern in the selected data:

{io_text}- **Fastest borough:** {fastest_borough}: **{fastest_time:.2f} min** ({highest_comp_val:.1f}% compliance).
- **Slowest borough:** {slowest_borough}: **{slowest_time:.2f} min** ({lowest_comp_val:.1f}% compliance).
- **Response time spread** across boroughs: **{rt_spread:.2f} minutes**.
- **Compliance spread:** **{compliance_spread:.1f} percentage points**.

Larger outer boroughs systematically struggle to meet the 6-minute target,
while smaller, denser inner boroughs consistently outperform.

**Implication:** Geographic scale rather than incident volume is the dominant constraint on
response times. Station placement and coverage area matter more than demand volume alone.
""")
    st.markdown("---")

# 5: 
if not pd.isna(median_turnout) and not pd.isna(median_travel):
    st.header("5. Travel Time, Not Turnout, Drives Performance")
    st.markdown(f"""
Decomposing response time into its two components reveals a decisive finding:

- **Median turnout time: {median_turnout:.2f} min**: consistent across all boroughs.
- **Median travel time: {median_travel:.2f} min**: the dominant and variable component.
- Travel time accounts for approximately **{travel_share:.0f}% of total median response time**.

Across the slowest boroughs, turnout times remain near-identical while travel times
diverge substantially. This pattern holds throughout the day: turnout is stable,
travel fluctuates with traffic and distance.

**Implication:** Station mobilisation is efficient and uniform: it is not the bottleneck.
Improving response performance requires addressing **travel distance and geographic coverage**,
not operational station processes.
""")
    st.markdown("---")

# 6: 
st.header("6. Most Target Exceedances Have No Recorded Delay Reason")

if total_exceedances > 0:
    st.markdown(f"""
Of the **{total_exceedances:,} incidents ({pct_exceedances:.1f}%)** that exceeded the 6-minute
target in the selected period:
""")
    if delay_available:
        st.markdown(f"""
- **{pct_not_held_up:.1f}%** were recorded as *"Not held up"*: no specific delay logged.
- The remaining exceedances involve traffic, roadworks, traffic calming, or address issues.

This indicates that the majority of exceedances occur under normal operating conditions
rather than exceptional operational disruptions.
""")
    else:
        st.markdown("- Delay code breakdown is not available for this filter selection.")
else:
    st.markdown("No incidents exceeded the 6-minute target in the selected period.")

st.markdown("""
**Implication:** Most exceedances are driven by **everyday structural and spatial constraints**,
principally travel distance in larger boroughs, rather than identifiable operational failures.
This reinforces the case for geographic solutions over operational ones.
""")

st.markdown("---")

# Overall Implications
st.header("7. Overall Implications")

travel_share_str = f"{travel_share:.0f}%" if not pd.isna(travel_share) else "the majority"

st.markdown(f"""
Taken together, the findings point to a consistent picture for **{period_label}, {incident_label}**:

**Geographic coverage is the most impactful factor.**
Travel time explains ~{travel_share_str} of response time and borough size strongly predicts
compliance. Optimising the **geographic placement of fire stations and coverage areas**
is more likely to improve performance than further refinements to already efficient
mobilisation processes.

**Aggregate KPIs are misleading without borough context.**
A city-wide median of {median_response:.2f} minutes can obscure the fact that some boroughs
fail to meet the 6-minute target in a significant share of incidents.
Borough-level reporting is essential for an accurate picture of operational performance.

**The 6-minute target is structurally harder to meet in outer London.**
Applying a uniform city-wide target across boroughs of very different geographic scales
may not fairly reflect structural constraints. Differentiated benchmarks could better
reflect operational realities.

**Turnout efficiency is a strength, not a problem.**
Station mobilisation processes are performing consistently well across the city.
Resources are better directed toward travel infrastructure and station distribution.
""")

st.markdown("---")
st.caption(
    "London Fire Brigade Incident & Response Time Analysis · February 2026"
)

