# risk_simulator.py
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
import random
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmployeeAgent:
    def __init__(self, emp_data):
        self.employee_id = emp_data['employee_id']
        self.company_id = emp_data['company_id']
        self.profession = emp_data['profession']
        self.salary = emp_data['salary']
        self.is_saudi = emp_data['is_saudi']
        self.is_low_wage = emp_data['is_low_wage']
        self.tenure_months = emp_data.get('tenure_months', 0)
        self.active = True

    def apply_attrition(self, hazard_saudi, hazard_foreign):
        if not self.active:
            return False
        tenure_factor = max(0.5, 1.0 - 0.5 * min(1.0, self.tenure_months / 12.0))
        hazard = hazard_saudi * tenure_factor if self.is_saudi else hazard_foreign * tenure_factor
        if random.random() < hazard:
            self.active = False
            return True
        return False

    def apply_salary_progression(self, upskill_prob=0.01):
        if self.is_saudi and self.is_low_wage and self.active:
            if random.random() < upskill_prob:
                self.salary = random.randint(4000, 6000)
                self.is_low_wage = False
                return True
        return False

class NitaqatRiskSimulator:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.hazard_saudi = 0.02 / 12
        self.hazard_foreign = 0.06 / 12
        self.monthly_growth_rate = 0.005
        self.upskill_probability = 0.01

    def load_company_employees(self, company_id):
        with self.engine.connect() as conn:
            df = pd.read_sql(
                text("""
                    SELECT 
                        employee_id,
                        company_id,
                        profession,
                        salary,
                        is_saudi,
                        is_low_wage,
                        EXTRACT(YEAR FROM AGE(CURRENT_DATE, hire_date::date)) * 12 
                        + EXTRACT(MONTH FROM AGE(CURRENT_DATE, hire_date::date)) AS tenure_months
                    FROM employees
                    WHERE company_id = :cid
                """),
                conn, params={"cid": company_id}
            )
        if df.empty:
            raise ValueError(f"No active employees found for company {company_id}")
        return [EmployeeAgent(row) for row in df.to_dict('records')]

    def get_optimization_recommendations(self, company_id):
        from optimizer import NitaqatOptimizer
        opt = NitaqatOptimizer(str(self.engine.url))
        result = opt.optimize(company_id)
        if not result['feasible']:
            logger.warning(f"Optimizer not feasible for company {company_id}")
            return {}
        hire_plan = {}
        for prof, actions in result['recommendations'].items():
            if actions.get('hire', 0) > 0:
                hire_plan[prof] = actions['hire']
        return hire_plan

    def calculate_metrics(self, agents):
        total = len(agents)
        saudi_count = sum(1 for a in agents if a.is_saudi and a.active)
        low_wage = sum(1 for a in agents if a.is_saudi and a.is_low_wage and a.active)
        weighted = (saudi_count - low_wage) + 0.5 * low_wage
        # Ensure weighted is a number (not None)
        weighted = weighted if weighted is not None else 0
        pct = (weighted / total * 100) if total > 0 else 0
        band = "Green" if pct >= 20 else ("Yellow" if pct >= 10 else "Red")
        return {
            'total_employees': total,
            'saudi_count': saudi_count,
            'low_wage_saudis': low_wage,
            'weighted_saudis': weighted,
            'saudization_pct': pct,
            'band': band,
            'is_red': band == "Red"
        }

    def run_simulation(self, company_id, months=36, n_simulations=1000,
                       adopt_optimization=True, growth_rate=None):
        if growth_rate is None:
            growth_rate = self.monthly_growth_rate

        logger.info(f"Starting simulation for Company {company_id}, {n_simulations} sims, {months} months")

        hire_plan = {}
        if adopt_optimization:
            try:
                hire_plan = self.get_optimization_recommendations(company_id)
                logger.info(f"Optimizer recommendations: {hire_plan}")
            except Exception as e:
                logger.warning(f"Could not get optimizer recommendations: {e}")

        initial_agents = self.load_company_employees(company_id)
        initial_metrics = self.calculate_metrics(initial_agents)
        logger.info(f"Initial metrics: {initial_metrics}")

        all_red_flags = []
        monthly_pcts = []

        for sim in range(n_simulations):
            agents = []
            for agent in initial_agents:
                new_agent = EmployeeAgent({
                    'employee_id': agent.employee_id,
                    'company_id': agent.company_id,
                    'profession': agent.profession,
                    'salary': agent.salary,
                    'is_saudi': agent.is_saudi,
                    'is_low_wage': agent.is_low_wage,
                    'tenure_months': agent.tenure_months
                })
                agents.append(new_agent)

            red_month = None
            monthly_sim_pcts = []

            # Apply optimizer hires at month 0
            if adopt_optimization and hire_plan:
                with self.engine.connect() as conn:
                    for prof, num in hire_plan.items():
                        min_sal = 4000
                        result = conn.execute(
                            text("SELECT min_salary_requirement FROM profession_quotas WHERE profession = :prof"),
                            {"prof": prof}
                        ).fetchone()
                        if result:
                            min_sal = result[0] or 4000
                        for _ in range(num):
                            new_emp = EmployeeAgent({
                                'employee_id': f"SIM-{sim}-{prof}",
                                'company_id': company_id,
                                'profession': prof,
                                'salary': max(min_sal, random.randint(4000, 8000)),
                                'is_saudi': True,
                                'is_low_wage': False,
                                'tenure_months': 0
                            })
                            agents.append(new_emp)

            for month in range(1, months + 1):
                new_agents = []
                for agent in agents:
                    if not agent.active:
                        continue
                    if agent.apply_attrition(self.hazard_saudi, self.hazard_foreign):
                        continue
                    new_agents.append(agent)
                for agent in new_agents:
                    agent.apply_salary_progression(self.upskill_probability)

                current_total = len(new_agents)
                target_total = int(current_total * (1 + growth_rate))
                total_hire = target_total - current_total
                if total_hire > 0:
                    saudi_ratio = 0.7
                    saudi_hires = int(total_hire * saudi_ratio)
                    foreign_hires = total_hire - saudi_hires

                    prof_counts = {}
                    for agent in new_agents:
                        prof_counts[agent.profession] = prof_counts.get(agent.profession, 0) + 1
                    total_prof = sum(prof_counts.values())
                    prof_list = list(prof_counts.keys())
                    probs = [count/total_prof for count in prof_counts.values()] if total_prof > 0 else [1/len(prof_list)] * len(prof_list)

                    for _ in range(saudi_hires):
                        prof = np.random.choice(prof_list, p=probs) if prof_list else 'technician'
                        min_sal = 4000
                        with self.engine.connect() as conn:
                            result = conn.execute(
                                text("SELECT min_salary_requirement FROM profession_quotas WHERE profession = :prof"),
                                {"prof": prof}
                            ).fetchone()
                            if result:
                                min_sal = result[0] or 4000
                        salary = max(min_sal, random.randint(4000, 8000))
                        new_agent = EmployeeAgent({
                            'employee_id': f"SIM-{sim}-{prof}-{month}",
                            'company_id': company_id,
                            'profession': prof,
                            'salary': salary,
                            'is_saudi': True,
                            'is_low_wage': False,
                            'tenure_months': 0
                        })
                        new_agents.append(new_agent)
                    for _ in range(foreign_hires):
                        prof = np.random.choice(prof_list, p=probs) if prof_list else 'technician'
                        salary = random.randint(3000, 6000)
                        new_agent = EmployeeAgent({
                            'employee_id': f"SIM-{sim}-foreign-{month}",
                            'company_id': company_id,
                            'profession': prof,
                            'salary': salary,
                            'is_saudi': False,
                            'is_low_wage': False,
                            'tenure_months': 0
                        })
                        new_agents.append(new_agent)

                agents = new_agents
                metrics = self.calculate_metrics(agents)
                monthly_sim_pcts.append(metrics['saudization_pct'])
                if metrics['is_red'] and red_month is None:
                    red_month = month

            monthly_pcts.append(monthly_sim_pcts)
            all_red_flags.append(red_month)

        red_prob = sum(1 for r in all_red_flags if r is not None) / n_simulations
        red_times = [r for r in all_red_flags if r is not None]
        avg_time_to_red = np.mean(red_times) if red_times else None

        pct_array = np.array(monthly_pcts)
        monthly_stats = {
            'month': list(range(1, months+1)),
            'mean': np.mean(pct_array, axis=0),
            'p5': np.percentile(pct_array, 5, axis=0),
            'p25': np.percentile(pct_array, 25, axis=0),
            'p50': np.percentile(pct_array, 50, axis=0),
            'p75': np.percentile(pct_array, 75, axis=0),
            'p95': np.percentile(pct_array, 95, axis=0),
        }

        return {
            'red_probability': red_prob,
            'red_times': red_times,
            'avg_time_to_red': avg_time_to_red,
            'monthly_stats': pd.DataFrame(monthly_stats),
            'initial_metrics': initial_metrics,
            'n_simulations': n_simulations,
            'months': months,
            'adopt_optimization': adopt_optimization,
            'hire_plan_applied': hire_plan if adopt_optimization else {}
        }