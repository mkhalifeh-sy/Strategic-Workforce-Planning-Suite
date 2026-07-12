# 🇸🇦 Nitaqat Strategic Workforce Planning Suite

A production‑ready workforce planning platform that uses Linear Programming and Monte Carlo simulation to help Saudi companies achieve Nitaqat compliance at minimum cost. Built for integration with Jisr, SAP SuccessFactors, and Oracle HCM.

---

## Why This Project Matters

Saudization is mandatory for every company in Saudi Arabia. The rules are complex – 269 professions each have their own quota, and the government updates them frequently. Most companies treat compliance as a checkbox, reacting only when they fall into the Red band and face penalties. This project takes a different approach: it uses mathematical optimization to find the minimum‑cost path to compliance, and Monte Carlo simulation to forecast risk 36 months ahead. It turns a regulatory burden into a strategic advantage.

This is not a toy project. It is a complete, cloud‑deployed system built by someone with 20+ years of GCC enterprise experience, reinforced by a Master’s degree in Machine Learning. The code is production‑ready, the API is documented, and the dashboard is live. It demonstrates the ability to bridge compliance, data, and strategy – to build systems that solve real business problems, not just write code.

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

- **API:** [strategic-workforce-planning-suite-production-13c1.up.railway.app](strategic-workforce-planning-suite-production-13c1.up.railway.app)
- **API Documentation:** [strategic-workforce-planning-suite-production-13c1.up.railway.app/docs](strategic-workforce-planning-suite-production-13c1.up.railway.app)
- **Dashboard:** [https://strategic-workforce-planning-suite.streamlit.app/](https://strategic-workforce-planning-suite.streamlit.app/)

---

## Repository Structure
├── api.py                 # FastAPI backend – all endpoints
├── optimizer.py           # Linear Programming optimizer (PuLP)
├── risk_simulator.py      # Monte Carlo simulation engine
├── attrition_model.py     # Attrition prediction (Logistic Regression)
├── skill_gap.py           # Skill‑gap analysis
├── cost_of_turnover.py    # Turnover cost calculator
├── scenario_builder.py    # What‑if scenario runner
├── dashboard.py           # Streamlit frontend
├── utils.py               # Shared helpers (NumPy conversion)
├── data_generator.py      # Synthetic data generator
├── init_db.py             # Database initialization script
├── load_data.py           # Data loader
├── Dockerfile             # Container build
├── start.sh               # Startup script for Railway
├── requirements.txt       # Python dependencies
└── README.md              # This file