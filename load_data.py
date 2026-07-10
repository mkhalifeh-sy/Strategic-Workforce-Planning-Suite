# load_data.py
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("NITAQAT_DB")
if not DATABASE_URL:
    raise ValueError("NITAQAT_DB environment variable is not set.")

engine = create_engine(DATABASE_URL)

# Load CSVs
try:
    companies_df = pd.read_csv("companies.csv")
    employees_df = pd.read_csv("employees.csv")
except FileNotFoundError as e:
    print(f"Error: {e}\nPlease run data_generator.py first to generate the CSV files.")
    exit(1)

# --- Fix date format ---
# Convert hire_date to datetime (auto-detects DD-MM-YYYY, YYYY-MM-DD, etc.)
# Then format as YYYY-MM-DD for PostgreSQL
employees_df['hire_date'] = pd.to_datetime(
    employees_df['hire_date'], errors='coerce'
).dt.strftime('%Y-%m-%d')

# Check for any NaT (failed conversions)
if employees_df['hire_date'].isna().any():
    print("⚠️ Warning: Some hire_date values could not be parsed. Check your CSV.")
    print(f"   Rows with invalid dates: {employees_df[employees_df['hire_date'].isna()].index.tolist()}")

# Truncate existing data (cascade will handle foreign keys)
with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE companies, employees RESTART IDENTITY CASCADE;"))
    conn.commit()
    print("✅ Truncated existing data.")

# Insert new data
companies_df.to_sql("companies", engine, if_exists="append", index=False)
employees_df.to_sql("employees", engine, if_exists="append", index=False)

print(f"✅ Loaded {len(companies_df)} companies and {len(employees_df)} employees.")
print("✅ All dates converted to YYYY-MM-DD (PostgreSQL standard).")