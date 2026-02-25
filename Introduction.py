# pages/0_Introduction.py


import streamlit as st

from data_loader import load_data


st.set_page_config(
    page_title="London Fire Brigade – Operational Performance", layout="wide")

# ---------------------------------------------------------------------
# Title

st.title("London Fire Brigade Incident & Response Time Analysis Dashboard")

st.markdown("---")

# ---------------------------------------------------------------------
# Context

st.markdown("""
The **London Fire Brigade (LFB)** is the busiest fire and rescue service in the United Kingdom
and one of the largest firefighting organisations in the world. Responsible for a city of over
9 million people across 1,572 km², the LFB responds to fires, road traffic collisions,
flooding, and a wide range of special services.

This dashboard analyses **incident and mobilisation records from 2021 to 2025**, covering
approximately **586,000 incidents** across all 32 London boroughs and the City of London.
The goal is to evaluate operational response performance, identify structural patterns,
and understand what drives variation in response times across the city.
""")

st.markdown("---")

# ---------------------------------------------------------------------
# What this dashboard examines

st.subheader("What This Dashboard Examines")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
**Performance Against Targets**
The LFB operates against two official benchmarks:
- First pump arriving within **6 minutes**
- 90% of first pumps arriving within **10 minutes**

This dashboard evaluates how consistently these targets are met
across different time periods, incident types, and boroughs.
""")

    st.markdown("""
**Geographic Variation**
Response performance is not uniform across London.
This dashboard maps performance differences across all 33 boroughs,
comparing Inner and Outer London and identifying which areas
systematically exceed or fall short of the 6-minute target.
""")

with col2:
    st.markdown("""
**What Drives Response Time**
Response time consists of two components:
- **Turnout time:** from station alert to vehicle departure
- **Travel time:** from departure to arrival on scene

Understanding which component drives variation is key to
identifying where improvements can be made.
""")

    st.markdown("""
**Temporal Patterns**
Incident demand and response performance are not constant.
This dashboard explores how volumes and response times vary
by month, day of week, and hour of call — revealing
predictable patterns that can inform operational planning.
""")

st.markdown("---")

# ---------------------------------------------------------------------
# Data sources

st.subheader("Data Sources")

st.markdown("""
This analysis is based on two publicly available datasets from the London Fire Brigade,
accessed via the London Datastore:

- **LFB Incident Records** — date, location, incident type, and property category
  for each incident responded to between 2021 and 2025.
- **LFB Mobilisation Records** — pump-level response data including turnout time,
  travel time, and attendance time for each appliance deployed.

Both datasets are publicly available at:
[data.london.gov.uk](https://data.london.gov.uk/dataset/london-fire-brigade-incident-records)

Geographic boundary data (GIS borough boundaries) was sourced from the
[London Datastore Statistical GIS Boundary Files](https://data.london.gov.uk/dataset/statistical-gis-boundary-files-for-london).
""")

st.markdown("---")

# ---------------------------------------------------------------------
# Navigation guide

st.subheader("How to Navigate This Dashboard")

st.markdown("""
Use the **sidebar** to move between the analytical sections. Each page builds on the previous
one, following a structured analytical narrative:
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
**1. Executive Summary**
City-wide performance overview,
KPIs, and response time distribution.

**2. Incident Composition**
Workload breakdown by incident type,
seasonal trends, and hourly demand patterns.
""")

with col2:
    st.markdown("""
**3. Response Performance**
Compliance rates by incident type,
seasonal and hourly variation in response times.

**4. Geographic Performance**
Borough-level response time mapping,
Inner vs. Outer London comparison.
""")

with col3:
    st.markdown("""
**5. Drivers of Response Time**
Turnout vs. travel time decomposition,
delay code analysis, and structural drivers.

**6. Key Findings & Implications**
Summary of main findings and
their operational implications.
""")

st.markdown("---")


