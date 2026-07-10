# init_db.py
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("NITAQAT_DB")
if not DATABASE_URL:
    raise ValueError("NITAQAT_DB environment variable is not set.")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # --- Drop tables in correct order (CASCADE handles dependencies) ---
    conn.execute(text("DROP TABLE IF EXISTS compliance_snapshots CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS employees CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS companies CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS profession_quotas CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS skill_requirements CASCADE;"))
    conn.commit()
    print("✅ Dropped existing tables.")

    # --- 1. Companies ---
    conn.execute(text("""
        CREATE TABLE companies (
            company_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            sector VARCHAR(100) NOT NULL,
            total_employees INTEGER,
            saudi_ratio_target DECIMAL(5,3),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

    # --- 2. Employees (full schema matching data_generator.py) ---
    conn.execute(text("""
        CREATE TABLE employees (
            employee_id VARCHAR(50) PRIMARY KEY,
            company_id INTEGER REFERENCES companies(company_id),
            name VARCHAR(255),
            nationality VARCHAR(50),
            sector VARCHAR(100),
            profession VARCHAR(100),
            salary INTEGER,
            is_low_wage BOOLEAN DEFAULT FALSE,
            is_saudi BOOLEAN,
            gender VARCHAR(10),
            hire_date DATE,
            years_of_service DECIMAL(4,1),
            job_family VARCHAR(100),
            skill_level INTEGER,
            left_job BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE
        );
    """))

    # --- 3. Profession quotas ---
    conn.execute(text("""
        CREATE TABLE profession_quotas (
            profession VARCHAR(100) PRIMARY KEY,
            target_saudization_pct DECIMAL(5,2) NOT NULL,
            min_salary_requirement INTEGER,
            last_updated DATE DEFAULT CURRENT_DATE
        );
    """))

    conn.execute(text("""
        INSERT INTO profession_quotas (profession, target_saudization_pct, min_salary_requirement) VALUES
        ('civil_engineer', 30.0, 8000),
        ('mechanical_engineer', 30.0, 8000),
        ('electrical_engineer', 28.0, 8000),
        ('accountant', 40.0, 7000),
        ('procurement_officer', 70.0, 5000),
        ('hr_specialist', 45.0, 7000),
        ('sales_executive', 35.0, 5000),
        ('it_developer', 22.0, 10000),
        ('network_admin', 25.0, 8000),
        ('nurse', 55.0, 6000),
        ('doctor', 45.0, 12000),
        ('technician', 15.0, 4000),
        ('administrative_assistant', 20.0, 4000),
        ('marketing_specialist', 30.0, 6000),
        ('logistics_coordinator', 30.0, 5000)
        ON CONFLICT (profession) DO NOTHING;
    """))

    # --- 4. Skill requirements ---
    conn.execute(text("""
        CREATE TABLE skill_requirements (
            profession VARCHAR(100) PRIMARY KEY,
            required_skills TEXT[],
            min_skill_level INTEGER
        );
    """))

    conn.execute(text("""
        INSERT INTO skill_requirements (profession, required_skills, min_skill_level) VALUES
        ('civil_engineer', ARRAY['AutoCAD', 'Structural Analysis', 'Project Management'], 4),
        ('mechanical_engineer', ARRAY['AutoCAD', 'Thermodynamics', 'Project Management'], 4),
        ('electrical_engineer', ARRAY['AutoCAD', 'Circuit Design', 'Project Management'], 4),
        ('accountant', ARRAY['SAP FI', 'IFRS', 'Excel'], 4),
        ('procurement_officer', ARRAY['Supply Chain', 'Negotiation', 'Excel'], 3),
        ('hr_specialist', ARRAY['Labor Law', 'Recruitment', 'Excel'], 3),
        ('sales_executive', ARRAY['CRM', 'Negotiation', 'Presentation'], 3),
        ('it_developer', ARRAY['Python', 'SQL', 'Docker'], 4),
        ('network_admin', ARRAY['Cisco', 'Linux', 'Network Security'], 4),
        ('nurse', ARRAY['Patient Care', 'Medical Records', 'Emergency Response'], 4),
        ('doctor', ARRAY['Diagnosis', 'Treatment Planning', 'Medical Records'], 5),
        ('technician', ARRAY['Equipment Maintenance', 'Safety Protocols', 'Documentation'], 2),
        ('administrative_assistant', ARRAY['Microsoft Office', 'Communication', 'Scheduling'], 2),
        ('marketing_specialist', ARRAY['Digital Marketing', 'Content Creation', 'Analytics'], 3),
        ('logistics_coordinator', ARRAY['Supply Chain', 'Inventory Management', 'Excel'], 3)
        ON CONFLICT (profession) DO NOTHING;
    """))

    # --- 5. Compliance snapshots (reserved) ---
    conn.execute(text("""
        CREATE TABLE compliance_snapshots (
            snapshot_id SERIAL PRIMARY KEY,
            company_id INTEGER REFERENCES companies(company_id),
            snapshot_date DATE NOT NULL,
            total_employees INTEGER,
            saudi_employees INTEGER,
            effective_saudization_pct DECIMAL(5,2),
            nitaqat_band VARCHAR(20),
            profession_deficits JSONB
        );
    """))

    conn.commit()
    print("✅ All tables created successfully with all required columns!")