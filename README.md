# London Fire Brigade — Incident & Response Time Analysis (2021–2025)

A multi-page interactive dashboard analysing operational performance data from the London Fire Brigade (LFB) between 2021 and 2025. The project explores response time patterns, evaluates compliance with official performance targets, and identifies structural performance drivers across all 33 London boroughs.

🔗 **[Live Dashboard →](https://lfb-response-time-dashboard-cqk7jfyroyw9dfkfbcj9w5.streamlit.app/)**

---

## Project Overview

The London Fire Brigade operates against two official performance benchmarks for the first appliance:
- First pump arriving within **6 minutes**
- 90% of first pumps arriving within **10 minutes**

A separate 8-minute target exists for the second appliance. However, with the second pump deployed in only 36% of incidents, reflected in a 64% missing value rate for SecondPumpArriving_AttendanceTime,  it does not provide a consistent basis for cross-incident comparison and was therefore excluded from this analysis.

This analysis evaluates how consistently the first appliance targets are met — across time periods, incident types, and geographies — and identifies the structural factors that drive variation in response performance.

**Core finding:** Geography is the dominant driver of performance variation. Borough size alone explains 59% of the variation in median response time and 62% of the variation in 6-minute compliance. Travel time accounts for approximately 77% of total response time, while turnout time remains remarkably stable across all boroughs (IQR: just 4 seconds).

---

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Introduction** | Project context, research questions, and dashboard structure |
| **Executive Summary** | City-wide KPIs, response time distribution, and performance overview |
| **Incident Composition** | Breakdown by incident type, seasonal patterns, and hourly demand heatmap |
| **Response Performance** | Compliance rates by incident type, month, and hour of day |
| **Geographic Performance** | Borough-level choropleth maps for response time, compliance, and incident volume |
| **Drivers of Response Time** | Turnout vs. travel time decomposition, hourly variation, and delay code analysis |
| **Key Findings & Implications** | Summary of findings, operational implications, study limitations, and further outlook |

All pages update dynamically based on sidebar filters (Year, Month, Incident Type).

---

## Key Findings

- **Median response time: 5.02 min** — below the 6-minute target at the aggregate level
- **6-minute compliance: 69.5%** — roughly 1 in 3 incidents exceeds the primary target
- **Borough range:** 4.22 min (Kensington & Chelsea) to 6.02 min (Hillingdon) — a gap of 1.80 minutes
- **Travel time** accounts for ~77% of total response time; turnout time is highly consistent (IQR: 4 s)
- **Borough size** explains 59% of response time variation and 62% of compliance variation (r = −0.79)
- **61.6% of all target exceedances** are recorded as "Not held up" — no specific operational cause

---

## Tech Stack

- **Python** — data processing and analysis
- **Pandas / NumPy** — data manipulation and statistical calculations
- **Streamlit** — multi-page interactive dashboard
- **Matplotlib / Seaborn** — static visualisations
- **Plotly** — interactive choropleth maps
- **GeoPandas / Folium** — geographic boundary data and mapping
- **SciPy** — statistical testing (ANOVA, correlation)

Data is stored in compressed **Parquet (Snappy)** format for performance optimisation.

---

## Project Structure

```
lfb-streamlit-app/
│
├── Introduction.py                         # Entry point
├── data_loader.py                          # Cached data loading and preprocessing
├── pages/
│   ├── 1_Executive_Summary.py
│   ├── 2_Incident_Composition.py
│   ├── 3_Response_Performance.py
│   ├── 4_Geographic_Performance.py
│   ├── 5_Drivers_of_Response_Time.py
│   └── 6_Key_Findings_&_Implications.py
├── Data/
│   ├── lfb_streamlit.parquet
│   ├── london_boroughs/                    # GeoJSON boundary files
│   └── london_population_borough.csv
├── analysis/
│   └── London_Fire_Brigade_Analysis.ipynb  # EDA and preprocessing notebook
├── .streamlit/
│   └── config.toml                         # Theme configuration
├── requirements.txt
└── README.md
```

---

## Running the App Locally

```bash
pip install -r requirements.txt
streamlit run Introduction.py
```

---

## Data Source

This analysis is based on two publicly available datasets from the London Fire Brigade, accessed via the London Datastore:

- **LFB Incident Records** — [data.london.gov.uk](https://data.london.gov.uk/dataset/london-fire-brigade-incident-records)
- **LFB Mobilisation Records** — [data.london.gov.uk](https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records)

Geographic boundary data (GIS borough boundaries) was sourced from the [London Datastore Statistical GIS Boundary Files](https://data.london.gov.uk/dataset/statistical-gis-boundary-files-for-london-20od9/).

The full data preprocessing and exploratory analysis pipeline is documented in [`analysis/London_Fire_Brigade_Analysis.ipynb`](analysis/London_Fire_Brigade_Analysis.ipynb).

## Analysis Notebook

The [`analysis/`](analysis/) folder contains the full EDA and preprocessing pipeline, including:
- Data loading and inspection
- Missing value handling and imputation strategy
- Feature engineering
- Exploratory visualisations
- Export to Parquet for the Streamlit dashboard
