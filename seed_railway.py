# seed_railway.py
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("NITAQAT_DB_CLOWDE")
if not DATABASE_URL:
    raise ValueError("NITAQAT_DB environment variable is not set.")

engine = create_engine(DATABASE_URL)

# Load CSVs
try:
    companies = pd.read_csv("companies.csv")
    employees = pd.read_csv("employees.csv")
except FileNotFoundError as e:
    print(f"Error: {e}\nPlease run data_generator.py first.")
    exit(1)

# --- Fix date format: specify DD-MM-YYYY explicitly ---
# This eliminates the warning and ensures correct parsing
employees['hire_date'] = pd.to_datetime(
    employees['hire_date'], 
    format='%d-%m-%Y',  # Explicitly tell pandas the date format[reference:2][reference:3]
    errors='coerce'
).dt.strftime('%Y-%m-%d')

# Check for invalid dates
if employees['hire_date'].isna().any():
    print("⚠️ Warning: Some hire_date values could not be parsed. Check your CSV.")
    print(f"   Rows with invalid dates: {employees[employees['hire_date'].isna()].index.tolist()}")

# --- Truncate existing data (clean slate, preserves table structure) ---
# Tables must exist before TRUNCATE can run[reference:4]
with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE companies, employees RESTART IDENTITY CASCADE;"))
    conn.commit()
    print("✅ Truncated existing data.")

# --- Insert new data ---
companies.to_sql("companies", engine, if_exists="append", index=False)
employees.to_sql("employees", engine, if_exists="append", index=False)

print(f"✅ Seeded {len(companies)} companies and {len(employees)} employees!")
print("✅ All dates converted to YYYY-MM-DD (PostgreSQL standard).")