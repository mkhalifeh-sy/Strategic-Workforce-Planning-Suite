# 🇸🇦 Nitaqat Strategic Workforce Planning Suite

A production‑ready workforce planning platform that uses Linear Programming and Monte Carlo simulation to help Saudi companies achieve Nitaqat compliance at minimum cost. Built for integration with Jisr, SAP SuccessFactors, and Oracle HCM.

---

## Why This Project Matters

Saudization is mandatory for every company in Saudi Arabia. The rules are complex – 269 professions each have their own quota, and the government updates them frequently. Most companies treat compliance as a checkbox, reacting only when they fall into the Red band and face penalties. This project takes a different approach: it uses mathematical optimization to find the minimum‑cost path to compliance, and Monte Carlo simulation to forecast risk 36 months ahead. It turns a regulatory burden into a strategic advantage.

This is not a toy project. It is a complete, cloud‑deployed system built by someone with 20+ years of GCC enterprise experience, reinforced by a Master's degree in Machine Learning. The code is production‑ready, the API is documented, and the dashboard is live. It demonstrates the ability to bridge compliance, data, and strategy – to build systems that solve real business problems, not just write code.

---

## Key Features

- **Profession‑level compliance optimization** – respects 2026 Nitaqat quotas across 269 professions, with sector‑specific thresholds.
- **Weighted Saudization formula** – handles low‑wage (0.5x) and disabled (4x) weighting, as defined by the Ministry of Human Resources.
- **Monte Carlo risk simulation** – forecasts Red‑band probability up to 36 months, factoring in probabilistic attrition and hiring.
- **What‑if scenario builder** – adjust hiring costs, growth rates, and policy changes to see the impact on compliance and cost.
- **Enterprise API** – RESTful endpoints with OpenAPI documentation, designed for integration with Jisr, SAP SuccessFactors, and Oracle HCM.
- **Interactive dashboard** – Streamlit frontend with company selection, real‑time metrics, and bilingual support (Arabic/English).
- **Attrition prediction** – Logistic Regression model to identify employees at risk of leaving.
- **Skill‑gap analysis** – identifies professions where Saudi employees lack required skills.
- **Turnover cost calculator** – quantifies the financial impact of employee departures.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| Optimization | PuLP (Linear Programming) |
| Simulation | Monte Carlo (NumPy) |
| Machine Learning | scikit‑learn, Logistic Regression |
| Frontend | Streamlit, Plotly |
| Deployment | Docker, Railway, Streamlit Cloud |
| Authentication | JWT (mock RBAC) |

---

## Live Demo

- **API:** [https://strategic-workforce-planning-suite-production.up.railway.app](https://strategic-workforce-planning-suite-production.up.railway.app)
- **API Documentation:** [https://strategic-workforce-planning-suite-production.up.railway.app/docs](https://strategic-workforce-planning-suite-production.up.railway.app/docs)
- **Dashboard:** [https://your-username-nitaqat-suite.streamlit.app](https://your-username-nitaqat-suite.streamlit.app)

---

## Repository Structure
├── api.py # FastAPI backend – all endpoints
├── optimizer.py # Linear Programming optimizer (PuLP)
├── risk_simulator.py # Monte Carlo simulation engine
├── attrition_model.py # Attrition prediction (Logistic Regression)
├── skill_gap.py # Skill‑gap analysis
├── cost_of_turnover.py # Turnover cost calculator
├── scenario_builder.py # What‑if scenario runner
├── dashboard.py # Streamlit frontend
├── utils.py # Shared helpers (NumPy conversion)
├── data_generator.py # Synthetic data generator
├── init_db.py # Database initialization script
├── load_data.py # Data loader
├── Dockerfile # Container build
├── start.sh # Startup script for Railway
├── requirements.txt # Python dependencies
└── README.md # This file


---

## Deployment

This project is deployed on:

- **Railway** – FastAPI backend (PostgreSQL database)
- **Streamlit Cloud** – Interactive dashboard

Environment variables are managed securely via Railway's built‑in variable system and Streamlit Cloud Secrets.

---

## Local Setup

### Prerequisites

- Python 3.13+
- PostgreSQL (local or cloud)
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/nitaqat-suite.git
cd nitaqat-suite

# 2. Create a virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file with your database URL
echo "NITAQAT_DB=postgresql://user:pass@localhost:5432/nitaqat_db" > .env

# 5. Generate synthetic data
python data_generator.py

# 6. Initialize the database (creates tables and lookup data)
python init_db.py

# 7. Load the data
python load_data.py

# 8. Run the API
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# 9. Run the dashboard (in a new terminal)
streamlit run dashboard.py

Open your browser at http://localhost:8501 to view the dashboard.
```
## API Endpoints

Method	Endpoint	Description
GET	/	Health check
GET	/companies	List all companies
GET	/companies/{id}	Get company details
POST	/optimize	Run the Nitaqat optimizer
POST	/simulate	Run Monte Carlo simulation
GET	/attrition-risks/{id}	Get attrition risk scores
GET	/skill-gap/{id}	Analyze skill gaps
POST	/turnover-cost	Calculate turnover cost
POST	/scenario	Run a what‑if scenario
Full interactive documentation is available at /docs when the API is running.

---
## License
MIT

---
## Author
Mohammad Khalifeh

linkedin.com/in/your-handle

github.com/mkhaifeh-sy

---
## Related Projects
This project is part of a broader HR technology portfolio:

Retention & Talent Intelligence Platform – Predict attrition, recommend interventions, and calculate ROI.

HR Operational Intelligence Dashboard – Real‑time workforce metrics and alerts.

HR Intelligence & Automation Platform – Unified API, LLM chat, workflows, and RBAC.