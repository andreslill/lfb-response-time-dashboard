import streamlit as st
from data_loader import load_data
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


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

st.title("Summary")
st.markdown("")

# ---------------------------------------------------------------------
# Load Data

df = load_data()

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

# Dynamic Incident Label
if selected_incident == "All":
    incident_label = "All Incident Types"
else:
    incident_label = f"{selected_incident} Incidents"
    

st.caption(f"Data shown: {period_label}, {incident_label} ")

# ---------------------------------------------------------------------
# Mobilisation-only subset 

df_operational = filtered_df[filtered_df["DeployedFromLocation"].notna()].copy()

df_operational = filtered_df[
    filtered_df["DeployedFromLocation"].notna()
].copy()

if df_operational.empty:
    st.warning("No mobilisation data available for selected filters.")
    st.stop()

# ---------------------------------------------------------------------
# Define CrossGround

df_operational["CrossGround"] = (
    df_operational["IncidentStationGround"].astype(str) !=
    df_operational["DeployedFromStation_Name"].astype(str)
)

# Define incident_level
incident_level = (
    df_operational
    .groupby("IncidentNumber")["CrossGround"]
    .max()
)


# ---------------------------------------------------------------------
# 1️⃣ Cross-Ground Dispatch Rate

st.markdown("## 1. Cross-Ground Dispatch Rate")

cross_rate = df_operational["CrossGround"].mean() * 100

st.caption("how many times incident station ground and incident location isn't the same?")
 
st.metric(
    "Cross-Ground Dispatch Rate",
    f"{cross_rate:.1f}%"
)


st.write("CrossGround counts:")
st.write(df_operational["CrossGround"].value_counts())

st.write("CrossGround percentage:")
st.write(df_operational["CrossGround"].value_counts(normalize=True) * 100)


st.write("Total incidents (filtered):", len(filtered_df))
st.write("Incidents with mobilisation data:", len(df_operational))

st.write(
    df_operational[[
        "IncidentStationGround",
        "DeployedFromStation_Name",
        "CrossGround"
    ]].head(20)
)

st.write(
    df_operational.groupby(
        ["IncidentStationGround", "DeployedFromStation_Name"]
    ).size().sort_values(ascending=False).head(20)
)









# ---------------------------------------------------------------------
# 2️⃣ Performance Impact (Same vs Cross-Ground)

st.markdown("## 2. Performance Impact: Same vs Cross-Ground")

comparison = (
    df_operational
    .groupby("CrossGround")
    .agg(
        MedianResponseMinutes=(
            "FirstPumpArriving_AttendanceTime",
            lambda x: x.median() / 60
        ),
        ComplianceRate=(
            "FirstPump_Within_6min",
            "mean"
        )
    )
    .reset_index()
)

comparison["ComplianceRate"] *= 100

# Rename boolean values for readability
comparison["DispatchType"] = comparison["CrossGround"].map({
    False: "Same Ground",
    True: "Cross Ground"
})

st.dataframe(
    comparison[["DispatchType", "MedianResponseMinutes", "ComplianceRate"]],
    use_container_width=True
)

# ---------------------------------------------------------------------
# 3️⃣ “Not held up” Distribution

st.markdown("## 3. Distribution of 'Not held up' Delay Code")

not_held = df_operational[
    df_operational["DelayCode_Description"] == "Not held up"
]

not_held_counts = (
    not_held
    .groupby("IncidentStationGround")
    .size()
    .reset_index(name="Count")
    .sort_values("Count", ascending=False)
)

st.subheader("Top 10 Station Grounds – 'Not held up'")

st.dataframe(
    not_held_counts.head(10),
    use_container_width=True
)


st.metric(
    "Cross-Ground Rate (Mobilisations)",
    f"{(df_operational['CrossGround'].mean()*100):.1f}%"
)

st.metric(
    "Cross-Ground Rate (Incident-level)",
    f"{(incident_level.mean()*100):.1f}%"
)

# ---------------------------------------------------------------------
# Optional Insight Summary

st.markdown("""
### Key Operational Insights

- Cross-ground dispatch reflects operational reallocation across station grounds.
- Performance comparison indicates whether cross-ground mobilisation is associated 
  with slower attendance or lower compliance.
- A high proportion of "Not held up" codes suggests that many 6-minute exceedances 
  occur without a recorded operational delay.
""")


st.write(df_operational[[
    "IncidentStationGround",
    "DeployedFromLocation"
]].head(20))

st.write(df_operational["DeployedFromStation_Name"].unique()[:10])








st.write(df["PumpOrder"].value_counts())











# ---------------------------------------------------------------------









