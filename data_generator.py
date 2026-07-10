import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

fake = Faker('en_US')  # We'll customize names manually

# --- Configuration: The Real Saudi Market Rules (April 2026) ---

# Sector base Saudi percentages (before optimization interventions)
SECTOR_BASE_SAUDI_RATIO = {
    "engineering": 0.15,
    "retail": 0.10,
    "construction": 0.08,
    "healthcare": 0.25,
    "it_telecom": 0.20,
    "finance": 0.22,
    "hospitality": 0.12
}

# Profession-specific quotas (The 269 professions rule simplified)
# Target % for Saudization in each profession
PROFESSION_TARGETS = {
    "civil_engineer": 0.30,
    "mechanical_engineer": 0.30,
    "electrical_engineer": 0.28,
    "accountant": 0.40,
    "procurement_officer": 0.70,
    "hr_specialist": 0.45,
    "sales_executive": 0.35,
    "it_developer": 0.22,
    "network_admin": 0.25,
    "nurse": 0.55,
    "doctor": 0.45,
    "technician": 0.15,
    "administrative_assistant": 0.20,
    "marketing_specialist": 0.30,
    "logistics_coordinator": 0.30
}

# Salary bands (Monthly SAR)
SALARY_BANDS = {
    "entry": (3000, 6000),
    "mid": (7000, 12000),
    "senior": (13000, 25000),
    "executive": (26000, 50000)
}

# Map profession to typical salary level
PROFESSION_SALARY_LEVEL = {
    "civil_engineer": "mid",
    "mechanical_engineer": "mid",
    "electrical_engineer": "mid",
    "accountant": "mid",
    "procurement_officer": "mid",
    "hr_specialist": "mid",
    "sales_executive": "mid",
    "it_developer": "senior",
    "network_admin": "mid",
    "nurse": "mid",
    "doctor": "senior",
    "technician": "entry",
    "administrative_assistant": "entry",
    "marketing_specialist": "mid",
    "logistics_coordinator": "entry"
}

# Sector -> list of available professions
SECTOR_PROFESSIONS = {
    "engineering": ["civil_engineer", "mechanical_engineer", "electrical_engineer", "technician", "administrative_assistant"],
    "retail": ["sales_executive", "procurement_officer", "logistics_coordinator", "administrative_assistant"],
    "construction": ["civil_engineer", "technician", "procurement_officer", "administrative_assistant"],
    "healthcare": ["doctor", "nurse", "technician", "administrative_assistant"],
    "it_telecom": ["it_developer", "network_admin", "sales_executive", "administrative_assistant"],
    "finance": ["accountant", "hr_specialist", "sales_executive", "administrative_assistant"],
    "hospitality": ["sales_executive", "marketing_specialist", "administrative_assistant", "logistics_coordinator"]
}

def generate_saudi_name():
    """Generate a plausible Saudi name (First + Father + Grandfather + Family)"""
    first_names = ["Mohammed", "Ahmed", "Abdullah", "Khalid", "Saud", "Faisal", "Sultan", "Nasser", "Mansour", "Turki"]
    family_names = ["Al-Otaibi", "Al-Ghamdi", "Al-Dosari", "Al-Shammari", "Al-Harbi", "Al-Malki", "Al-Saud", "Al-Qahtani"]
    return f"{random.choice(first_names)} {random.choice(first_names)} {random.choice(family_names)}"

def generate_foreign_name():
    """Generate a plausible expat name"""
    return fake.name()

def generate_employee(company_id, sector, saudi_ratio, seed_offset=0):
    """Generate a single employee record"""
    random.seed(seed_offset + company_id * 1000)  # Deterministic but varied
    
    is_saudi = random.random() < saudi_ratio
    profession = random.choice(SECTOR_PROFESSIONS[sector])
    
    # Salary logic
    level = PROFESSION_SALARY_LEVEL[profession]
    min_sal, max_sal = SALARY_BANDS[level]
    # Apply some randomness within the band
    salary = random.randint(min_sal, max_sal)
    
    # Low-wage Saudis (<4000 SAR) count as 0.5x for Nitaqat
    is_low_wage = False
    if is_saudi and salary < 4000:
        is_low_wage = True
    
    # Seniority/Tenure (Hired between 2018 and 2026)
    years_back = random.randint(0, 8)
    hire_date = datetime.now() - timedelta(days=years_back * 365 + random.randint(0, 180))
    
    # Gender for diversity
    gender = random.choice(["Male", "Female"])
    
    # 1. Assign a job family (grouping for later analysis)
    job_families = ["Engineering", "Finance", "IT", "HR", "Sales", "Operations"]
    job_family = random.choice(job_families)
    
    # 2. Assign a skill level (1 = beginner, 5 = expert)
    # Higher salary/tenure usually means higher skill
    skill_level = min(5, max(1, int(years_back / 2) + random.randint(0, 1)))
    
    # 3. Did this employee leave the company? (Realistic probability)
    # Low salary + short tenure = high chance of leaving
    leave_prob = 0.3 if (years_back < 2 and salary < 6000) else 0.05
    left = random.random() < leave_prob
    # --- End of new logic ---

    return {
        "company_id": company_id,
        "employee_id": f"EMP-{company_id:03d}-{random.randint(1000, 9999)}",
        "name": generate_saudi_name() if is_saudi else generate_foreign_name(),
        "nationality": "Saudi" if is_saudi else random.choice(["Indian", "Pakistani", "Egyptian", "Filipino", "Bangladeshi", "Jordanian", "Syrian"]),
        "sector": sector,
        "profession": profession,
        "salary": salary,
        "is_low_wage": is_low_wage,
        "is_saudi": is_saudi,
        "gender": gender,
        "hire_date": hire_date.strftime("%Y-%m-%d"),
        "years_of_service": round(years_back + random.random(), 1),
        
        "job_family": job_family,
        "skill_level": skill_level,
        "left_job": left,
        "is_active": True
    }

def generate_dataset(num_companies=15, avg_size=150):
    """Generate the master dataset"""
    companies = []
    employees = []
    
    for i in range(1, num_companies + 1):
        # Randomly assign a sector
        sector = random.choice(list(SECTOR_BASE_SAUDI_RATIO.keys()))
        base_saudi_ratio = SECTOR_BASE_SAUDI_RATIO[sector]
        
        # Vary company size (+- 40%)
        size = int(avg_size * random.uniform(0.6, 1.4))
        
        # Some companies might be better/worse than the baseline
        company_saudi_ratio = base_saudi_ratio * random.uniform(0.7, 1.5)
        company_saudi_ratio = min(0.5, company_saudi_ratio)  # Cap at 50% for realism
        
        for j in range(size):
            emp = generate_employee(i, sector, company_saudi_ratio, seed_offset=j)
            employees.append(emp)
        
        companies.append({
            "company_id": i,
            "name": f"{fake.company()} {sector.title()}",
            "sector": sector,
            "total_employees": size,
            "saudi_ratio_target": round(company_saudi_ratio, 3)
        })
    
    return pd.DataFrame(companies), pd.DataFrame(employees)

if __name__ == "__main__":
    print("🚀 Generating Enterprise Nitaqat Dataset...")
    companies_df, employees_df = generate_dataset(num_companies=20, avg_size=120)
    
    # Save to CSV (Stage 1)
    companies_df.to_csv("companies.csv", index=False)
    employees_df.to_csv("employees.csv", index=False)
    
    print(f"✅ Generated {len(companies_df)} companies and {len(employees_df)} employees.")
    print("📁 Files saved: companies.csv, employees.csv")
    
    # Quick stats
    saudi_count = employees_df[employees_df['is_saudi'] == True].shape[0]
    print(f"👤 Total Saudis: {saudi_count} ({round(saudi_count/len(employees_df)*100,1)}%)")
    print(f"📊 Sectors: {employees_df['sector'].unique()}")