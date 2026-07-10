# seed_railway.py
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# Use your Railway PostgreSQL connection string
# Replace with the actual string from Railway
DATABASE_URL = "postgresql://postgres:adEpRFEAZcWVnErSZnrXTULKpYjmZgwp@hayabusa.proxy.rlwy.net:54203/railway"

engine = create_engine(DATABASE_URL)

# Load your CSV files
companies = pd.read_csv("companies.csv")
employees = pd.read_csv("employees.csv")

# Create tables and insert data
companies.to_sql("companies", engine, if_exists="replace", index=False)
employees.to_sql("employees", engine, if_exists="replace", index=False)

print(f"✅ Seeded {len(companies)} companies and {len(employees)} employees!")