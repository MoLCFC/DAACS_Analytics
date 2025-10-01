````markdown
# DAACS Analytics (Fresh Setup)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/flask-2.x-green)
![MongoDB](https://img.shields.io/badge/mongodb-4.4%2B-brightgreen)
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
````

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

* Health check: [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)
* System dashboard API: [http://127.0.0.1:5000/api/system/dashboard](http://127.0.0.1:5000/api/system/dashboard)
* User analytics: `http://127.0.0.1:5000/api/users/<user_id>/analytics`
* Dashboard UI: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

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

* **No data in dashboard**: ensure MongoDB is running and `import_data.py` succeeded.
* **API errors**: check the Flask console output; errors include tracebacks.
* **Wrong database**: pass `--connection-string` and `--database` explicitly when launching `web_app.py`.

---

## 🔮 Next Steps

The code is intentionally light.
Extend `AnalyticsEngine` with additional statistics, or connect the front-end to external charting libraries (e.g., Plotly, D3, Chart.js) as needed.

---

## 📜 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

````

---

# 📄 LICENSE (MIT)

```text
MIT License

Copyright (c) 2025 DAACS Analytics Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
````

---

👉 Drop `README.md` and `LICENSE` into the root of your repo.
Do you also want me to add a **`CONTRIBUTING.md`** with guidelines for setup, PRs, and code style, so others can collaborate smoothly?

