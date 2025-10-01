# DAACS Analytics (Fresh Setup)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)  
![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)  
![MongoDB](https://img.shields.io/badge/MongoDB-4.4%2B-brightgreen.svg)  
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)  

This project provides a minimal analytics service for the **Diagnostic Assessment and Achievement of College Skills (DAACS)** dataset.  
It ingests the provided MongoDB export and exposes summary metrics and visualisations via a Flask API and a single-page dashboard.

---

## 🚀 Prerequisites

- Python 3.10+
- MongoDB 4.4+ running locally or accessible via URI
- The DAACS JSON dump in the `analytic_database/` folder:
  - `users.json`
  - `user_assessments.json`
  - `event_containers.json`

---

## ⚙️ Installation

1. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Import the dataset into MongoDB**:
   ```bash
   python import_data.py --connection-string mongodb://localhost:27017/ --database daacs_analytics
   ```

4. **Run the analytics server**:
   ```bash
   python web_app.py --connection-string mongodb://localhost:27017/ --database daacs_analytics
   ```

---

## 📊 Usage

- Health check: [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)  
- System dashboard API: [http://127.0.0.1:5000/api/system/dashboard](http://127.0.0.1:5000/api/system/dashboard)  
- User analytics: `http://127.0.0.1:5000/api/users/<user_id>/analytics`  
- Dashboard UI: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)  

---

## 📂 Project Structure

```
DAACS/
├── analytic_database/
│   ├── users.json
│   ├── user_assessments.json
│   └── event_containers.json
├── analytics.py          # Analytics engine (system metrics, user summaries)
├── database.py           # MongoDB repository helpers
├── import_data.py        # JSON import script
├── models.py             # Core dataclasses
├── requirements.txt      # Dependencies
├── static/
│   ├── charts.js         # D3 utilities
│   └── dashboard.html    # Minimal dashboard page
└── web_app.py            # Flask application
```

---

## 🛠 Troubleshooting

- **No data in dashboard**: ensure MongoDB is running and `import_data.py` succeeded.  
- **API errors**: check the Flask console output; errors include tracebacks.  
- **Wrong database**: pass `--connection-string` and `--database` explicitly when launching `web_app.py`.  

---

## 🔮 Next Steps

The code is intentionally light.  
Extend `AnalyticsEngine` with additional statistics, or connect the front-end to external charting libraries (e.g., Plotly, D3, Chart.js) as needed.  

---

## 📜 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.  
