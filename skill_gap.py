# skill_gap.py
import os
import pandas as pd
from sqlalchemy import create_engine, text
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("NITAQAT_DB")

class SkillGapAnalyzer:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)

    def analyze(self, company_id):
        with self.engine.connect() as conn:
            employees = pd.read_sql(text("""
                SELECT 
                    employee_id,
                    name,
                    profession,
                    job_family,
                    skill_level,
                    is_saudi
                FROM employees
                WHERE company_id = :cid
                  AND is_active = TRUE
            """), conn, params={"cid": company_id})

            if employees.empty:
                return {"message": "No employees found.", "data": []}

            requirements = pd.read_sql("""
                SELECT profession, required_skills, min_skill_level
                FROM skill_requirements
            """, conn)

        merged = employees.merge(requirements, on='profession', how='left')
        merged['min_skill_level'] = merged['min_skill_level'].fillna(1)
        merged['required_skills'] = merged['required_skills'].fillna('{}')
        merged['has_gap'] = merged['skill_level'] < merged['min_skill_level']
        merged['gap_amount'] = (merged['min_skill_level'] - merged['skill_level']).clip(lower=0)

        summary = merged.groupby('profession').agg(
            total_employees=('employee_id', 'count'),
            avg_skill=('skill_level', 'mean'),
            min_required=('min_skill_level', 'first'),
            employees_with_gap=('has_gap', 'sum'),
            total_gap_amount=('gap_amount', 'sum')
        ).reset_index()

        summary['gap_percentage'] = (summary['employees_with_gap'] / summary['total_employees'] * 100).round(1)
        summary['status'] = summary['gap_percentage'].apply(
            lambda x: 'Critical' if x > 50 else ('Warning' if x > 20 else 'OK')
        )

        gap_employees = merged[merged['has_gap']].copy()
        gap_employees = gap_employees[[
            'employee_id', 'name', 'profession', 'skill_level',
            'min_skill_level', 'gap_amount'
        ]].sort_values('gap_amount', ascending=False)

        return {
            "company_id": company_id,
            "total_employees": len(merged),
            "employees_with_gaps": int(merged['has_gap'].sum()),
            "summary": summary.to_dict(orient="records"),
            "gap_employees": gap_employees.to_dict(orient="records")
        }