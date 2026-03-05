# page/0_Introduction.py

import streamlit as st
from data_loader import load_data

st.set_page_config(
    page_title="London Fire Brigade Response Time Analysis (2021–2025)",
    layout="wide"
)

# ---------------------------------------------------------------------
# Load data for live KPIs
df = load_data()
incidents = (
    df.sort_values("PumpOrder")
    .drop_duplicates("IncidentNumber")
    .copy()
)
total_incidents      = len(incidents)
compliance_rate      = (incidents["FirstPumpArriving_AttendanceTime"] <= 360).mean() * 100
median_response      = incidents["FirstPumpArriving_AttendanceTime"].median() / 60
n_boroughs           = incidents["IncGeo_BoroughName"].nunique()
years_covered        = f"{df['Year'].min()}–{df['Year'].max()}"

# ---------------------------------------------------------------------
# Hero
st.title("London Fire Brigade Response Time Analysis")
st.markdown(
    f"##### Analysing operational response performance across London · {years_covered}"
)
st.markdown("")

# ---------------------------------------------------------------------
# Live KPIs — the numbers do the talking
col1, col2, col3, col4 = st.columns(4)
col1.metric("Incidents Analysed",       f"{total_incidents:,}")
col2.metric("6-min Compliance Rate",    f"{compliance_rate:.1f}%")
col3.metric("Median Response Time",     f"{median_response:.2f} min")
col4.metric("London Boroughs Covered",  f"{n_boroughs}")

st.markdown("---")

# ---------------------------------------------------------------------
# Key Questions — scannable, no paragraphs
st.subheader("What This Dashboard Investigates")

q1, q2 = st.columns(2)
with q1:
    st.markdown(
        """
        <div style="background:#f8f9fa; border-radius:8px; padding:14px 18px; margin-bottom:12px;">
        <strong>Geography</strong><br>
        Do response times differ systematically between Inner and Outer London boroughs?
        </div>
        <div style="background:#f8f9fa; border-radius:8px; padding:14px 18px;">
        <strong>Time of Day</strong><br>
        How do incident demand and response performance vary by hour, day, and season?
        </div>
        """,
        unsafe_allow_html=True,
    )
with q2:
    st.markdown(
        """
        <div style="background:#f8f9fa; border-radius:8px; padding:14px 18px; margin-bottom:12px;">
        <strong>Turnout vs. Travel</strong><br>
        Is response time variation driven by station mobilisation or by travel distance?
        </div>
        <div style="background:#f8f9fa; border-radius:8px; padding:14px 18px;">
        <strong>Target Compliance</strong><br>
        Which incident types and boroughs consistently miss the 6-minute benchmark?
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ---------------------------------------------------------------------
# Navigation cards
st.subheader("Dashboard Pages")

nav1, nav2, nav3 = st.columns(3)

with nav1:
    st.markdown(
        """
        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:16px; margin-bottom:12px;">
        <strong>Executive Summary</strong><br>
        <span style="color:#6b7280; font-size:0.9rem;">City-wide KPIs, compliance trend (2021–2025), best & worst boroughs, incident type breakdown.</span>
        </div>
        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:16px;">
        <strong>Incident Composition</strong><br>
        <span style="color:#6b7280; font-size:0.9rem;">Workload by incident type, seasonal patterns, and hourly demand heatmap.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with nav2:
    st.markdown(
        """
        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:16px; margin-bottom:12px;">
        <strong>Response Performance</strong><br>
        <span style="color:#6b7280; font-size:0.9rem;">Compliance rates by incident type, month, and hour of day.</span>
        </div>
        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:16px;">
        <strong>Geographic Performance</strong><br>
        <span style="color:#6b7280; font-size:0.9rem;">Borough-level choropleth maps for response time, compliance, and incident volume.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with nav3:
    st.markdown(
        """
        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:16px; margin-bottom:12px;">
        <strong>Drivers of Response Time</strong><br>
        <span style="color:#6b7280; font-size:0.9rem;">Turnout vs. travel time decomposition, hourly variation, delay code analysis.</span>
        </div>
        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:16px;">
        <strong>Key Findings & Implications</strong><br>
        <span style="color:#6b7280; font-size:0.9rem;">Summary of findings, operational implications, and study limitations.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ---------------------------------------------------------------------
# Data Sources — collapsed by default, out of the way
with st.expander("Data Sources & Methodology"):
    st.markdown("""
    **Datasets** — two publicly available sources from the [London Datastore](https://data.london.gov.uk):
    - **LFB Incident Records (2021–2025):** date, location, incident type, and property category.
    - **LFB Mobilisation Records (2021–2025):** pump-level turnout time, travel time, and attendance time.

    **Data Pipeline:**
    1. Raw datasets downloaded and joined at incident level using `IncidentNumber`.
    2. Filtered to first-pump arrivals only (`PumpOrder == 1`) for consistent response time measurement.
    3. Borough boundaries joined via GeoJSON (ONS Statistical GIS Boundary Files).
    4. Processed data exported to compressed Parquet (Snappy) for fast dashboard loading.

    The second appliance (8-minute target) was excluded due to a 64% missing value rate,
    making cross-incident comparison unreliable.
    """)

st.caption(
    "London Fire Brigade Response Time Analysis (2021–2025) · Andrés Lill · February 2026"
)
