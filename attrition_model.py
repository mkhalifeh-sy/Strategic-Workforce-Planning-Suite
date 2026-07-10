# attrition_model.py
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score
import joblib
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("NITAQAT_DB")
MODEL_PATH = "attrition_model.pkl"
ENCODER_PATH = "encoders.pkl"
SCALER_PATH = "scaler.pkl"

class AttritionPredictor:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.model = None
        self.encoders = {}
        self.scaler = None

    def train(self, force_retrain=False):
        if not force_retrain and os.path.exists(MODEL_PATH):
            logger.info("Loading existing model...")
            self.model = joblib.load(MODEL_PATH)
            self.encoders = joblib.load(ENCODER_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            return

        logger.info("Training new attrition model...")
        with self.engine.connect() as conn:
            df = pd.read_sql("""
                SELECT 
                    (years_of_service * 12) AS tenure_months,
                    salary,
                    CASE WHEN is_saudi THEN 1 ELSE 0 END AS is_saudi,
                    CASE WHEN is_low_wage THEN 1 ELSE 0 END AS is_low_wage,
                    profession,
                    job_family,
                    skill_level,
                    left_job
                FROM employees
                WHERE left_job IS NOT NULL
            """, conn)

        if df.empty:
            raise ValueError("No labeled data found. Run data_generator.py with left_job column.")

        logger.info(f"Loaded {len(df)} records for training.")
        X = df.drop('left_job', axis=1)
        y = df['left_job'].astype(int)

        cat_cols = ['profession', 'job_family']
        for col in cat_cols:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            self.encoders[col] = le

        num_cols = ['tenure_months', 'salary', 'is_saudi', 'is_low_wage', 'skill_level']
        self.scaler = StandardScaler()
        X[num_cols] = self.scaler.fit_transform(X[num_cols])

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        self.model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        logger.info(f"✅ Accuracy: {acc:.2%}, AUC: {auc:.2%}")

        joblib.dump(self.model, MODEL_PATH)
        joblib.dump(self.encoders, ENCODER_PATH)
        joblib.dump(self.scaler, SCALER_PATH)
        logger.info("Model saved.")

    def predict_risk(self, company_id):
        if self.model is None:
            self.train()

        with self.engine.connect() as conn:
            df = pd.read_sql(text("""
                SELECT 
                    employee_id,
                    (years_of_service * 12) AS tenure_months,
                    salary,
                    CASE WHEN is_saudi THEN 1 ELSE 0 END AS is_saudi,
                    CASE WHEN is_low_wage THEN 1 ELSE 0 END AS is_low_wage,
                    profession,
                    job_family,
                    skill_level
                FROM employees
                WHERE company_id = :cid
                  AND is_active = TRUE
                  AND (left_job IS NOT TRUE OR left_job IS NULL)
            """), conn, params={"cid": company_id})

        if df.empty:
            return pd.DataFrame()

        employee_ids = df['employee_id'].copy()
        X = df.drop('employee_id', axis=1)

        for col in ['profession', 'job_family']:
            le = self.encoders.get(col)
            if le:
                X[col] = X[col].apply(lambda x: x if x in le.classes_ else 'unknown')
                X[col] = le.transform(X[col])
            else:
                X[col] = 0

        num_cols = ['tenure_months', 'salary', 'is_saudi', 'is_low_wage', 'skill_level']
        X[num_cols] = self.scaler.transform(X[num_cols])

        risk_scores = self.model.predict_proba(X)[:, 1]
        result = pd.DataFrame({
            'employee_id': employee_ids,
            'risk_score': risk_scores
        })
        result['risk_category'] = result['risk_score'].apply(
            lambda x: 'High' if x > 0.7 else ('Medium' if x > 0.4 else 'Low')
        )
        return result.sort_values('risk_score', ascending=False)