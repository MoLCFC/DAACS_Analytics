# DAACS Analytics

Interactive analytics for the Diagnostic Assessment and Achievement of College Skills (DAACS). The app ingests a MongoDB export and serves a clean dashboard backed by a Flask API and D3 visualizations.

## What’s in the dashboard

- System Overview cards: total users, active users, total assessments
- Performance Distribution: score histogram with quick stats
- User Growth: users created per day (date-range)
- Assessments Activity: started vs. completed per day (date-range)
- User Analytics: searchable user details with traffic‑light indicator at the user level
- Navigation Flow: year-scoped path visualization for students with navigation events only
- Login Heatmap (Year): Month × Weekday intensity for selected year
- Daily Logins (Dot Chart): day-level counts for chosen year + month with trend line
- CAT/MC Timing — Item Groups: 20 slowest groups by average seconds
- CAT/MC Timing — Items: 20 slowest items by average seconds
- Top Students: 100 best average scores, displayed as 3‑dot traffic lights

Notes:
- The “Answer Selection Frequency” and “Answer Choice Ridgeline” panels are currently removed per requirements (kept server-side pieces where helpful for future work).

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

## Dashboard & API

- `http://127.0.0.1:5000/` – main dashboard

Key API routes:
- Health: `/api/health`
- System metrics: `/api/system/dashboard`
- Users:
  - List/search: `/api/users?q=<term>&limit=<n>`
  - Top students: `/api/users/top?limit=100`
  - With navigation (by range): `/api/users/with_navigation?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - Created per day (by range): `/api/users/created?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - Analytics (one user): `/api/users/<user_id>/analytics`
  - Navigation events (one user, by year/range): `/api/users/<user_id>/navigation?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Assessments:
  - Activity (started/completed): `/api/assessments/activity?start=YYYY-MM-DD&end=YYYY-MM-DD`
  - Timing metrics (groups/items): `/api/assessments/timing`
  - Search assessments: `/api/assessments/list?q=<term>&limit=<n>&category=<label>`

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

- No data on the dashboard: ensure MongoDB is running and `import_data.py` completed successfully.
- Navigation list empty: use a date range/year where events exist; the user chooser hides students without navigation activity in the selected window.
- API 500 errors: check the Flask console logs; stack traces include the failing query.
- Large files/Git: the `analytic_database/` directory is ignored; re-run the import script to regenerate.

## Notes

- Navigation flow uses a compact, readable sequence layout with gradient links; year filter defaults to the current year.
- Date-range inputs default to the last 30 days when empty.
