# api.py
import os
import logging
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from optimizer import NitaqatOptimizer
from risk_simulator import NitaqatRiskSimulator
from attrition_model import AttritionPredictor
from skill_gap import SkillGapAnalyzer
from cost_of_turnover import TurnoverCostCalculator
from scenario_builder import ScenarioBuilder
from utils import convert_numpy

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("NITAQAT_DB")
if not DATABASE_URL:
    raise ValueError("NITAQAT_DB environment variable is not set.")

# Initialize all components
optimizer = NitaqatOptimizer(DATABASE_URL)
risk_sim = NitaqatRiskSimulator(DATABASE_URL)
attrition_predictor = AttritionPredictor()
skill_gap_analyzer = SkillGapAnalyzer()
turnover_calculator = TurnoverCostCalculator()
scenario_builder = ScenarioBuilder()

app = FastAPI(
    title="Nitaqat Strategic Workforce Planning Suite",
    description="Enterprise API for Saudization compliance optimization.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins; for production, replace with your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic models ----------
class CompanyInfo(BaseModel):
    company_id: int
    name: str
    sector: str
    total_employees: int
    saudi_ratio_target: float

class CompanyListResponse(BaseModel):
    companies: List[CompanyInfo]

class OptimizeRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    target_band: Optional[str] = "Green (Low)"

class OptimizeResponse(BaseModel):
    company_id: int
    sector: str
    status: str
    feasible: bool
    total_cost_sar: float
    current_overall_pct: float
    target_overall_pct: float
    recommendations: Dict[str, Dict[str, int]]
    message: str
    projection: List[Dict]

class SimulationRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    months: Optional[int] = Field(36, ge=1, le=120)
    n_simulations: Optional[int] = Field(1000, ge=10, le=5000)
    adopt_optimization: Optional[bool] = True

class TurnoverCostRequest(BaseModel):
    company_id: int
    num_leavers: Optional[int] = None
    avg_salary: Optional[float] = None
    recruitment_cost_pct: float = 0.20
    training_cost_pct: float = 0.10
    productivity_loss_pct: float = 0.30

class ScenarioRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    months: Optional[int] = Field(36, ge=1, le=120)
    n_simulations: Optional[int] = Field(500, ge=10, le=5000)
    hiring_cost_multiplier: float = Field(1.0, ge=0.5, le=2.0)
    upskill_cost_multiplier: float = Field(1.0, ge=0.5, le=2.0)
    growth_rate: float = Field(0.005, ge=0.0, le=0.03)
    adopt_optimization: bool = True

# ---------- Health ----------
@app.get("/")
def root():
    return {
        "service": "Nitaqat Strategic Workforce Planning Suite",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs"
    }

# ---------- Companies ----------
@app.get("/companies", response_model=CompanyListResponse)
def list_companies():
    try:
        with optimizer.engine.connect() as conn:
            df = pd.read_sql("""
                SELECT company_id, name, sector, total_employees, saudi_ratio_target
                FROM companies ORDER BY company_id
            """, conn)
        companies = [
            CompanyInfo(
                company_id=row['company_id'],
                name=row['name'],
                sector=row['sector'],
                total_employees=row['total_employees'],
                saudi_ratio_target=float(row['saudi_ratio_target']) if row['saudi_ratio_target'] else 0.0
            )
            for _, row in df.iterrows()
        ]
        return CompanyListResponse(companies=companies)
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies/{company_id}")
def get_company(company_id: int):
    try:
        with optimizer.engine.connect() as conn:
            company = pd.read_sql(
                text("SELECT * FROM companies WHERE company_id = :cid"),
                conn, params={"cid": company_id}
            )
            if company.empty:
                raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
            workforce = pd.read_sql(
                text("""
                    SELECT 
                        profession,
                        COUNT(*) AS total,
                        SUM(CASE WHEN is_saudi THEN 1 ELSE 0 END) AS saudi_count,
                        SUM(CASE WHEN is_saudi AND is_low_wage THEN 1 ELSE 0 END) AS low_wage_saudis,
                        ROUND(AVG(salary), 0) AS avg_salary
                    FROM employees
                    WHERE company_id = :cid
                    GROUP BY profession
                    ORDER BY profession
                """),
                conn, params={"cid": company_id}
            )
        return {
            "company": company.iloc[0].to_dict(),
            "workforce": workforce.to_dict(orient="records")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/companies")
def create_company(name: str, sector: str, total_employees: int):
    try:
        with optimizer.engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO companies (name, sector, total_employees, saudi_ratio_target)
                    VALUES (:name, :sector, :total_employees, 0.20)
                    RETURNING company_id
                """),
                {"name": name, "sector": sector, "total_employees": total_employees}
            )
            conn.commit()
            new_id = result.fetchone()[0]
        return {"message": "Company created", "company_id": new_id}
    except Exception as e:
        logger.error(f"Error creating company: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Optimization ----------
@app.post("/optimize", response_model=OptimizeResponse)
def optimize(request: OptimizeRequest):
    try:
        result = optimizer.optimize(request.company_id, request.target_band)
        return OptimizeResponse(
            company_id=result['company_id'],
            sector=result['sector'],
            status=result['status'],
            feasible=result['feasible'],
            total_cost_sar=result['total_cost_sar'] or 0.0,
            current_overall_pct=result['current_overall_pct'],
            target_overall_pct=result['target_overall_pct'],
            recommendations=result['recommendations'],
            message=result['message'],
            projection=result['projection']
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error optimizing company {request.company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Simulation ----------
@app.post("/simulate")
def run_simulation(request: SimulationRequest):
    try:
        result = risk_sim.run_simulation(
            company_id=request.company_id,
            months=request.months,
            n_simulations=request.n_simulations,
            adopt_optimization=request.adopt_optimization
        )
        return convert_numpy({
            "company_id": request.company_id,
            "months": result["months"],
            "n_simulations": result["n_simulations"],
            "red_probability": float(result["red_probability"]),
            "avg_time_to_red": float(result["avg_time_to_red"]) if result["avg_time_to_red"] is not None else None,
            "initial_metrics": result["initial_metrics"],
            "monthly_stats": result["monthly_stats"].to_dict(orient="records")
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in simulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Attrition ----------
@app.get("/attrition-risks/{company_id}")
def get_attrition_risks(company_id: int):
    try:
        df = attrition_predictor.predict_risk(company_id)
        if df.empty:
            return {"message": "No employees found for this company.", "data": []}
        result = {
            "company_id": company_id,
            "total_employees": len(df),
            "high_risk": len(df[df['risk_category'] == 'High']),
            "medium_risk": len(df[df['risk_category'] == 'Medium']),
            "low_risk": len(df[df['risk_category'] == 'Low']),
            "employees": df.to_dict(orient="records")
        }
        return convert_numpy(result)
    except Exception as e:
        logger.error(f"Error predicting attrition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Skill Gap ----------
@app.get("/skill-gap/{company_id}")
def get_skill_gap(company_id: int):
    try:
        result = skill_gap_analyzer.analyze(company_id)
        return convert_numpy(result)
    except Exception as e:
        logger.error(f"Error in skill gap analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Turnover Cost ----------
@app.post("/turnover-cost")
def calculate_turnover_cost(request: TurnoverCostRequest):
    try:
        result = turnover_calculator.calculate(
            company_id=request.company_id,
            num_leavers=request.num_leavers,
            avg_salary=request.avg_salary,
            recruitment_cost_pct=request.recruitment_cost_pct,
            training_cost_pct=request.training_cost_pct,
            productivity_loss_pct=request.productivity_loss_pct
        )
        return convert_numpy(result)
    except Exception as e:
        logger.error(f"Error calculating turnover cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Scenario ----------
@app.post("/scenario")
def run_scenario(request: ScenarioRequest):
    try:
        result = scenario_builder.run_scenario(
            company_id=request.company_id,
            months=request.months,
            n_simulations=request.n_simulations,
            hiring_cost_multiplier=request.hiring_cost_multiplier,
            upskill_cost_multiplier=request.upskill_cost_multiplier,
            growth_rate=request.growth_rate,
            adopt_optimization=request.adopt_optimization
        )
        return convert_numpy(result)
    except Exception as e:
        logger.error(f"Error in scenario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Run (for local dev) ----------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)