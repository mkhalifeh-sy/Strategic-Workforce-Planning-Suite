# cost_of_turnover.py
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("NITAQAT_DB")

class TurnoverCostCalculator:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)

    def calculate(self, company_id, num_leavers=None, avg_salary=None,
                  recruitment_cost_pct=0.20, training_cost_pct=0.10,
                  productivity_loss_pct=0.30):
        with self.engine.connect() as conn:
            employees = pd.read_sql(text("""
                SELECT salary, left_job
                FROM employees
                WHERE company_id = :cid AND is_active = TRUE
            """), conn, params={"cid": company_id})

            if employees.empty:
                return {"error": "No active employees found for this company."}

            if num_leavers is None:
                leavers = pd.read_sql(text("""
                    SELECT COUNT(*) AS count
                    FROM employees
                    WHERE company_id = :cid AND left_job = TRUE
                """), conn, params={"cid": company_id})
                num_leavers = leavers.iloc[0]['count'] or 0

            if avg_salary is None:
                avg_salary = employees['salary'].mean()

        annual_salary = avg_salary * 12
        recruitment_cost = annual_salary * recruitment_cost_pct
        training_cost = annual_salary * training_cost_pct
        productivity_loss = annual_salary * productivity_loss_pct
        cost_per_leaver = recruitment_cost + training_cost + productivity_loss
        total_cost = cost_per_leaver * num_leavers

        return {
            "company_id": company_id,
            "total_employees": len(employees),
            "num_leavers": num_leavers,
            "avg_salary": round(avg_salary, 2),
            "annual_salary": round(annual_salary, 2),
            "breakdown": {
                "recruitment_cost": round(recruitment_cost, 2),
                "training_cost": round(training_cost, 2),
                "productivity_loss": round(productivity_loss, 2)
            },
            "cost_per_leaver": round(cost_per_leaver, 2),
            "total_cost": round(total_cost, 2),
            "assumptions": {
                "recruitment_cost_pct": recruitment_cost_pct,
                "training_cost_pct": training_cost_pct,
                "productivity_loss_pct": productivity_loss_pct
            }
        }