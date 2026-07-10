# dashboard.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
API_URL = os.getenv("API_URL")

st.set_page_config(page_title="Nitaqat Strategic Workforce Planning Suite", layout="wide")
st.title("🇸🇦 Nitaqat Strategic Workforce Planning Suite")
st.caption("Enterprise compliance optimization powered by Linear Programming, Machine Learning, and Monte Carlo simulation")

# --- Helper: Convert numpy types (just in case) ---
def safe_json(obj):
    """Convert to JSON‑serializable type."""
    return json.loads(json.dumps(obj, default=str))

# --- Sidebar: Company Selection ---
st.sidebar.header("Company Selection")

try:
    resp = requests.get(f"{API_URL}/companies")
    if resp.status_code == 200:
        companies = resp.json()["companies"]
        company_options = {c["company_id"]: f"{c['name']} (ID: {c['company_id']})" for c in companies}
    else:
        st.error("Could not fetch companies. Is the API running?")
        st.stop()
except Exception as e:
    st.error(f"Error connecting to API: {e}")
    st.stop()

selected_id = st.sidebar.selectbox(
    "Select Company",
    options=list(company_options.keys()),
    format_func=lambda x: company_options[x]
)

# --- Session state to cache results ---
if "results" not in st.session_state:
    st.session_state.results = {}

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", 
    "⚠️ Attrition Risk", 
    "📈 Skill Gap", 
    "💰 Turnover Cost", 
    "🔮 Scenario Builder"
])

# ============================================================
# TAB 1: OVERVIEW (Optimizer + Simulation)
# ============================================================
with tab1:
    st.header("Optimization & Compliance Forecast")
    
    if st.button("Run Optimizer & Simulation", type="primary"):
        with st.spinner("Running optimizer..."):
            opt_resp = requests.post(f"{API_URL}/optimize", json={"company_id": selected_id})
            if opt_resp.status_code != 200:
                st.error(f"Optimizer failed: {opt_resp.text}")
            else:
                opt_data = opt_resp.json()
                st.session_state.results["optimizer"] = opt_data
                st.success("Optimizer completed.")
        
        with st.spinner("Running Monte Carlo simulation..."):
            sim_resp = requests.post(
                f"{API_URL}/simulate",
                json={
                    "company_id": selected_id,
                    "months": 36,
                    "n_simulations": 500,
                    "adopt_optimization": True
                }
            )
            if sim_resp.status_code != 200:
                st.error(f"Simulation failed: {sim_resp.text}")
            else:
                sim_data = sim_resp.json()
                st.session_state.results["simulation"] = sim_data
                st.success("Simulation completed.")
    
    # Display results if available
    if "optimizer" in st.session_state.results and "simulation" in st.session_state.results:
        opt = st.session_state.results["optimizer"]
        sim = st.session_state.results["simulation"]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Saudization", f"{opt['current_overall_pct']:.1f}%")
        col2.metric("Red Probability (36 mo)", f"{sim['red_probability']*100:.1f}%")
        col3.metric("Total Cost (Optimizer)", f"SAR {opt['total_cost_sar']:,.0f}")
        
        st.subheader("Recommendations")
        if opt['recommendations']:
            rec_df = pd.DataFrame([
                {"Profession": p, "Hire": a['hire'], "Upskill": a['upskill']}
                for p, a in opt['recommendations'].items()
            ])
            st.dataframe(rec_df, use_container_width=True)
        else:
            st.info("✅ Already compliant. No changes needed.")
        
        st.subheader("Projected Compliance by Profession")
        proj_df = pd.DataFrame(opt['projection'])
        st.dataframe(proj_df[['profession', 'current_pct', 'target_pct', 'projected_pct', 'hires', 'upskills']], use_container_width=True)

# ============================================================
# TAB 2: ATTRITION RISK
# ============================================================
with tab2:
    st.header("Attrition Risk Prediction")
    if st.button("Predict Attrition Risk"):
        with st.spinner("Calculating risk scores..."):
            resp = requests.get(f"{API_URL}/attrition-risks/{selected_id}")
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.results["attrition"] = data
                st.success("Risk scores loaded.")
            else:
                st.error(f"Error: {resp.text}")
    
    if "attrition" in st.session_state.results:
        data = st.session_state.results["attrition"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Employees", data['total_employees'])
        col2.metric("High Risk", data['high_risk'], delta_color="inverse")
        col3.metric("Medium Risk", data['medium_risk'])
        
        if data['employees']:
            df = pd.DataFrame(data['employees'])
            st.dataframe(df, use_container_width=True)
            
            # Distribution chart
            fig = go.Figure(data=[go.Histogram(x=df['risk_score'], nbinsx=20, marker_color='coral')])
            fig.update_layout(title="Risk Score Distribution", xaxis_title="Risk Score", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 3: SKILL GAP
# ============================================================
with tab3:
    st.header("Skill Gap Analysis")
    if st.button("Analyze Skill Gaps"):
        with st.spinner("Analyzing..."):
            resp = requests.get(f"{API_URL}/skill-gap/{selected_id}")
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.results["skill_gap"] = data
                st.success("Analysis complete.")
            else:
                st.error(f"Error: {resp.text}")
    
    if "skill_gap" in st.session_state.results:
        data = st.session_state.results["skill_gap"]
        st.write(f"**Total employees:** {data['total_employees']}")
        st.write(f"**Employees with gaps:** {data['employees_with_gaps']}")
        
        if data['summary']:
            df_summary = pd.DataFrame(data['summary'])
            st.subheader("Summary by Profession")
            st.dataframe(df_summary, use_container_width=True)
            
            # Status distribution
            status_counts = df_summary['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig = go.Figure(data=[go.Bar(x=status_counts['Status'], y=status_counts['Count'], marker_color='lightblue')])
            fig.update_layout(title="Gap Status by Profession")
            st.plotly_chart(fig, use_container_width=True)
        
        if data['gap_employees']:
            df_gap = pd.DataFrame(data['gap_employees'])
            st.subheader("Employees with Skill Gaps")
            st.dataframe(df_gap, use_container_width=True)

# ============================================================
# TAB 4: TURNOVER COST
# ============================================================
with tab4:
    st.header("Turnover Cost Calculator")
    
    with st.form("turnover_form"):
        col1, col2 = st.columns(2)
        with col1:
            num_leavers = st.number_input("Number of Leavers", min_value=0, value=5)
            avg_salary = st.number_input("Average Monthly Salary (SAR)", min_value=1000, value=8000)
        with col2:
            recruitment_pct = st.slider("Recruitment Cost (% of annual salary)", 5, 50, 20, step=5) / 100.0
            training_pct = st.slider("Training Cost (% of annual salary)", 5, 30, 10, step=5) / 100.0
            productivity_pct = st.slider("Productivity Loss (% of annual salary)", 10, 50, 30, step=5) / 100.0
        
        submitted = st.form_submit_button("Calculate Turnover Cost")
    
    if submitted:
        payload = {
            "company_id": selected_id,
            "num_leavers": num_leavers,
            "avg_salary": avg_salary,
            "recruitment_cost_pct": recruitment_pct,
            "training_cost_pct": training_pct,
            "productivity_loss_pct": productivity_pct
        }
        with st.spinner("Calculating..."):
            resp = requests.post(f"{API_URL}/turnover-cost", json=payload)
            if resp.status_code == 200:
                result = resp.json()
                st.session_state.results["turnover"] = result
                st.success("Calculation complete.")
            else:
                st.error(f"Error: {resp.text}")
    
    if "turnover" in st.session_state.results:
        r = st.session_state.results["turnover"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Cost per Leaver", f"SAR {r['cost_per_leaver']:,.0f}")
        col2.metric("Total Cost", f"SAR {r['total_cost']:,.0f}")
        col3.metric("Total Employees", r['total_employees'])
        
        st.subheader("Breakdown per Leaver")
        bd = r['breakdown']
        df_bd = pd.DataFrame({
            "Component": ["Recruitment", "Training", "Productivity Loss"],
            "Cost (SAR)": [bd['recruitment_cost'], bd['training_cost'], bd['productivity_loss']]
        })
        fig = go.Figure(data=[go.Bar(x=df_bd['Component'], y=df_bd['Cost (SAR)'], marker_color='lightgreen')])
        fig.update_layout(title="Cost Breakdown per Leaver")
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 5: SCENARIO BUILDER
# ============================================================
with tab5:
    st.header("Scenario Builder – What‑if Analysis")
    st.caption("Adjust assumptions and see how they affect compliance, cost, and risk.")
    
    with st.form("scenario_form"):
        col1, col2 = st.columns(2)
        with col1:
            months = st.slider("Forecast Horizon (months)", 6, 60, 36)
            n_sims = st.slider("Number of Simulations", 100, 2000, 500, step=100)
            growth_rate = st.slider("Monthly Headcount Growth Rate", 0.0, 3.0, 0.5, step=0.1) / 100.0
        with col2:
            hire_multiplier = st.slider("Hiring Cost Multiplier", 0.5, 2.0, 1.0, step=0.1)
            upskill_multiplier = st.slider("Upskill Cost Multiplier", 0.5, 2.0, 1.0, step=0.1)
            adopt_opt = st.checkbox("Adopt Optimizer Recommendations", value=True)
        
        submitted = st.form_submit_button("Run Scenario")
    
    if submitted:
        payload = {
            "company_id": selected_id,
            "months": months,
            "n_simulations": n_sims,
            "hiring_cost_multiplier": hire_multiplier,
            "upskill_cost_multiplier": upskill_multiplier,
            "growth_rate": growth_rate,
            "adopt_optimization": adopt_opt
        }
        with st.spinner("Running scenario..."):
            resp = requests.post(f"{API_URL}/scenario", json=payload)
            if resp.status_code == 200:
                result = resp.json()
                st.session_state.results["scenario"] = result
                st.success("Scenario completed.")
            else:
                st.error(f"Error: {resp.text}")
    
    if "scenario" in st.session_state.results:
        s = st.session_state.results["scenario"]
        opt = s['optimizer']
        sim = s['simulation']
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Red Probability", f"{sim['red_probability']*100:.1f}%")
        col2.metric("Total Cost", f"SAR {opt['total_cost_sar']:,.0f}")
        col3.metric("Current Saudization", f"{opt['current_overall_pct']:.1f}%")
        
        st.subheader("Scenario Parameters")
        params = s['scenario_parameters']
        st.json(params)
        
        # Display forecast chart from scenario
        df_stats = pd.DataFrame(sim['monthly_stats'])
        fig = make_subplots()
        fig.add_trace(go.Scatter(
            x=df_stats['month'],
            y=df_stats['p95'],
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            name='p95'
        ))
        fig.add_trace(go.Scatter(
            x=df_stats['month'],
            y=df_stats['p5'],
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(0,100,200,0.2)',
            showlegend=False,
            name='80% CI'
        ))
        fig.add_trace(go.Scatter(
            x=df_stats['month'],
            y=df_stats['p50'],
            mode='lines',
            line=dict(color='blue', width=3),
            name='Median'
        ))
        fig.add_hline(y=10, line_dash="dot", line_color="red", annotation_text="Red Threshold (10%)")
        fig.add_hline(y=20, line_dash="dot", line_color="green", annotation_text="Green Threshold (20%)")
        fig.update_layout(
            xaxis_title="Months from now",
            yaxis_title="Saudization %",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)