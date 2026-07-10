# optimizer.py
import pulp
import pandas as pd
import logging
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NitaqatOptimizer:
    """
    Enterprise-grade optimizer for Nitaqat compliance.
    Uses Linear Programming to minimize cost while meeting profession-specific quotas.
    """
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.hiring_cost_per_hire = 22000
        self.upskill_cost = 8000
        self.annual_salary_multiplier = 12

        self.sector_thresholds = {
            "retail": 0.35,
            "engineering": 0.12,
            "construction": 0.10,
            "healthcare": 0.25,
            "it_telecom": 0.20,
            "finance": 0.22,
            "hospitality": 0.15
        }

    def get_company_data(self, company_id):
        with self.engine.connect() as conn:
            company_info = pd.read_sql(
                text("SELECT sector FROM companies WHERE company_id = :cid"),
                conn, params={"cid": company_id}
            )
            if company_info.empty:
                raise ValueError(f"Company {company_id} not found.")
            sector = company_info.iloc[0]['sector']

            query = text("""
                SELECT 
                    e.profession,
                    COUNT(*) AS total_employees,
                    SUM(CASE WHEN e.is_saudi THEN 1 ELSE 0 END) AS saudi_count,
                    SUM(CASE WHEN e.is_saudi AND e.is_low_wage THEN 1 ELSE 0 END) AS low_wage_saudi_count,
                    AVG(e.salary) AS avg_salary
                FROM employees e
                WHERE e.company_id = :cid
                GROUP BY e.profession
            """)
            df = pd.read_sql(query, conn, params={"cid": company_id})

            quotas = pd.read_sql(
                text("SELECT profession, target_saudization_pct, min_salary_requirement FROM profession_quotas"),
                conn
            )
        return sector, df, quotas

    def optimize(self, company_id, target_band="Green (Low)", hiring_cost_multiplier=1.0, upskill_cost_multiplier=1.0):
        logger.info(f"🚀 Starting optimization for Company {company_id}")
        sector, agg_df, quotas_df = self.get_company_data(company_id)
        logger.info(f"📊 Sector: {sector}, Professions found: {len(agg_df)}")

        df = agg_df.merge(quotas_df, on="profession", how="left")

        # --- FIX: ensure numeric columns are not None ---
        df['total_employees'] = df['total_employees'].fillna(0).astype(int)
        df['saudi_count'] = df['saudi_count'].fillna(0).astype(int)
        df['low_wage_saudi_count'] = df['low_wage_saudi_count'].fillna(0).astype(int)

        df['target_pct'] = df['target_saudization_pct'] / 100.0
        df['target_pct'] = df['target_pct'].fillna(0.20)
        df['min_salary'] = df['min_salary_requirement'].fillna(4000)

        # --- FIX: weighted saudis with safe conversion ---
        df['current_weighted_saudis'] = (
            (df['saudi_count'] - df['low_wage_saudi_count']) * 1.0 +
            df['low_wage_saudi_count'] * 0.5
        )

        # --- FIX: avoid division by zero and None ---
        df['current_effective_pct'] = df.apply(
            lambda row: row['current_weighted_saudis'] / row['total_employees']
            if row['total_employees'] > 0 else 0.0,
            axis=1
        )

        prob = pulp.LpProblem(f"Nitaqat_Optimization_Company_{company_id}", pulp.LpMinimize)
        professions = df['profession'].tolist()

        hires = pulp.LpVariable.dicts("Hire", professions, lowBound=0, cat='Integer')
        upskills = pulp.LpVariable.dicts("Upskill", professions, lowBound=0, cat='Integer')

        total_cost = pulp.lpSum([
            (self.hiring_cost_per_hire * hiring_cost_multiplier +
             df.loc[i, 'min_salary'] * self.annual_salary_multiplier) * hires[prof]
            for i, prof in enumerate(professions)
        ]) + pulp.lpSum([
            self.upskill_cost * upskill_cost_multiplier * upskills[prof]
            for prof in professions
        ])
        prob += total_cost

        for i, row in df.iterrows():
            prof = row['profession']
            total_emp = row['total_employees']
            current_weighted = row['current_weighted_saudis']
            target_pct = row['target_pct']
            prob += (
                current_weighted + hires[prof] + 0.5 * upskills[prof]
                >= target_pct * (total_emp + hires[prof])
            ), f"Prof_Constraint_{prof}"

        for i, row in df.iterrows():
            prof = row['profession']
            prob += upskills[prof] <= row['low_wage_saudi_count'], f"Upskill_Limit_{prof}"

        overall_target = self.sector_thresholds.get(sector, 0.20)
        total_weighted_current = df['current_weighted_saudis'].sum()
        total_employees_current = df['total_employees'].sum()

        prob += (
            total_weighted_current
            + pulp.lpSum(hires[prof] for prof in professions)
            + 0.5 * pulp.lpSum(upskills[prof] for prof in professions)
            >= overall_target * (
                total_employees_current
                + pulp.lpSum(hires[prof] for prof in professions)
            )
        ), "Overall_Nitaqat_Threshold"

        max_hire_multiplier = 0.30
        for i, row in df.iterrows():
            prof = row['profession']
            prob += hires[prof] <= row['total_employees'] * max_hire_multiplier, f"Max_Hire_{prof}"

        logger.info("🧮 Solving LP problem...")
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        status = pulp.LpStatus[prob.status]
        logger.info(f"✅ Solver status: {status}")
        feasibility = (status == "Optimal")

        recommendations = {}
        for prof in professions:
            h_val = int(pulp.value(hires[prof]) or 0)
            u_val = int(pulp.value(upskills[prof]) or 0)
            if h_val > 0 or u_val > 0:
                recommendations[prof] = {"hire": h_val, "upskill": u_val}

        total_cost_value = pulp.value(prob.objective)

        projection = []
        for i, row in df.iterrows():
            prof = row['profession']
            h = recommendations.get(prof, {}).get("hire", 0)
            u = recommendations.get(prof, {}).get("upskill", 0)
            new_total = row['total_employees'] + h
            new_weighted = row['current_weighted_saudis'] + h + 0.5 * u
            new_pct = (new_weighted / new_total * 100) if new_total > 0 else 0
            target_pct = row['target_pct'] * 100
            projection.append({
                "profession": prof,
                "current_pct": row['current_effective_pct'] * 100,
                "target_pct": target_pct,
                "projected_pct": new_pct,
                "hires": h,
                "upskills": u,
                "new_total": new_total,
                "new_weighted_saudis": new_weighted
            })

        return {
            "company_id": company_id,
            "sector": sector,
            "status": status,
            "feasible": feasibility,
            "total_cost_sar": total_cost_value,
            "recommendations": recommendations,
            "projection": projection,
            "current_overall_pct": (total_weighted_current / total_employees_current * 100) if total_employees_current > 0 else 0,
            "target_overall_pct": overall_target * 100,
            "message": self._generate_message(feasibility, recommendations)
        }

    def _generate_message(self, feasible, recommendations):
        if not feasible:
            return "⚠️ No feasible solution found with current constraints. Consider relaxing hiring limits or targeting a lower band."
        if not recommendations:
            return "✅ Company is already compliant! No changes needed."
        hire_sum = sum(v['hire'] for v in recommendations.values())
        upskill_sum = sum(v['upskill'] for v in recommendations.values())
        msg = f"✅ Optimal strategy: Hire {hire_sum} Saudis across {len(recommendations)} professions"
        if upskill_sum > 0:
            msg += f", and upskill {upskill_sum} low-wage Saudi employees"
        return msg + "."

if __name__ == "__main__":
    import sys
    DB_URL = os.getenv("NITAQAT_DB")
    if not DB_URL:
        print("NITAQAT_DB environment variable not set.")
        sys.exit(1)
    if len(sys.argv) < 2:
        print("Usage: python optimizer.py <company_id>")
        sys.exit(1)
    company_id = int(sys.argv[1])
    optimizer = NitaqatOptimizer(DB_URL)
    result = optimizer.optimize(company_id)
    print(result)