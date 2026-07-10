# scenario_builder.py
import os
from dotenv import load_dotenv
from optimizer import NitaqatOptimizer
from risk_simulator import NitaqatRiskSimulator
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("NITAQAT_DB")

class ScenarioBuilder:
    def __init__(self):
        self.optimizer = NitaqatOptimizer(DATABASE_URL)
        self.simulator = NitaqatRiskSimulator(DATABASE_URL)

    def run_scenario(self, company_id, months=36, n_simulations=500,
                     hiring_cost_multiplier=1.0, upskill_cost_multiplier=1.0,
                     growth_rate=0.005, adopt_optimization=True):
        logger.info(f"Running scenario for company {company_id}")
        logger.info(f"  Hiring cost multiplier: {hiring_cost_multiplier}")
        logger.info(f"  Upskill cost multiplier: {upskill_cost_multiplier}")
        logger.info(f"  Growth rate: {growth_rate}")

        opt_result = self.optimizer.optimize(
            company_id,
            hiring_cost_multiplier=hiring_cost_multiplier,
            upskill_cost_multiplier=upskill_cost_multiplier
        )

        sim_result = self.simulator.run_simulation(
            company_id,
            months=months,
            n_simulations=n_simulations,
            adopt_optimization=adopt_optimization,
            growth_rate=growth_rate
        )

        return {
            "scenario_parameters": {
                "company_id": company_id,
                "months": months,
                "n_simulations": n_simulations,
                "hiring_cost_multiplier": hiring_cost_multiplier,
                "upskill_cost_multiplier": upskill_cost_multiplier,
                "growth_rate": growth_rate,
                "adopt_optimization": adopt_optimization
            },
            "optimizer": opt_result,
            "simulation": {
                "red_probability": sim_result["red_probability"],
                "avg_time_to_red": sim_result["avg_time_to_red"],
                "monthly_stats": sim_result["monthly_stats"].to_dict(orient="records"),
                "initial_metrics": sim_result["initial_metrics"]
            }
        }