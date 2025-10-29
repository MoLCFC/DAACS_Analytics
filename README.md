# DAACS Analytics (Fresh Setup)

This project provides a comprehensive analytics service for the Diagnostic Assessment and Achievement of College Skills (DAACS) dataset. It ingests the provided MongoDB export and exposes summary metrics and visualisations via a Flask API and a professional dashboard.

## Features

- System overview with traffic-light grading
- Score distribution histogram with key stats
- User growth timeline (bar chart)
- Assessment activity (started/completed) by date range
- Answer choice frequency (circular bar plot)
- Navigation flow explorer per user (ready for tangled tree integration)
- CAT/MC timing metrics for item groups and items
- User summary cards with assessment details
- Filterable list of top 200 users

## Prerequisites

- Python 3.10+
- MongoDB 4.4+ running locally or via connection string
- DAACS JSON dump in `analytic_database/` (ignored by Git)

## Installation

```bash
# optional but recommended
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python import_data.py --connection-string mongodb://localhost:27017/ --database daacs_analytics
python web_app.py --connection-string mongodb://localhost:27017/ --database daacs_analytics
```

## Dashboard Overview

- `http://127.0.0.1:5000/` – main dashboard
- `http://127.0.0.1:5000/api/system/dashboard` – system metrics JSON
- Additional APIs:
  - `/api/users?limit=100`
  - `/api/users/<id>/analytics`
  - `/api/users/<id>/navigation?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - `/api/users/created?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - `/api/assessments/activity?start=...&end=...`
  - `/api/assessments/answers?start=...&end=...`
  - `/api/assessments/timing`

## Project Structure

```
DAACS/
├── analytic_database/         # JSON dumps (ignored by Git)
├── analytics.py               # Analytics engine
├── database.py                # MongoDB repository
├── import_data.py             # Import script
├── models.py                  # Dataclasses
├── requirements.txt           # Dependencies
├── static/
│   ├── charts.js              # D3 helpers + custom components
│   └── dashboard.html         # Reimagined dashboard UI
└── web_app.py                 # Flask server with REST endpoints
```

## Troubleshooting

- **No data**: confirm MongoDB is running and import script succeeded.
- **API 500 errors**: check console output; tracebacks include details.
- **Large files warning**: data JSON is excluded from Git; regenerate via import script.

## Notes

- Navigation view currently shows placeholder text; plug in tangled-tree code or observable embed to complete the visualization.
- Date-range inputs default to the last 30 days when empty.
