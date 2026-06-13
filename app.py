import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, render_template, request

try:
    import mlflow
except ImportError:  # pragma: no cover - optional for local development
    mlflow = None

app = Flask(__name__)

MODEL_PATH = Path(__file__).resolve().parent / 'model' / 'model.pkl'
MONITORING_DIR = Path(__file__).resolve().parent / 'monitoring'
LOCAL_PREDICTIONS_LOG = MONITORING_DIR / 'predictions.jsonl'
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI')
MLFLOW_EXPERIMENT_NAME = os.getenv('MLFLOW_EXPERIMENT_NAME', 'ds-credishield-monitoring')


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f'Model file not found: {MODEL_PATH}')
    return joblib.load(MODEL_PATH)


model = load_model()
MODEL_FEATURES = list(getattr(model, 'feature_names_in_', []))


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_feature_frame(form_data):
    row = {feature_name: 0.0 for feature_name in MODEL_FEATURES}

    # Core numeric fields that exist in the model feature set.
    row['annual_income'] = _to_float(form_data.get('pendapatan'))
    row['loan_amount'] = _to_float(form_data.get('pinjaman'))
    row['debt_to_income'] = _to_float(form_data.get('dti'))
    row['interest_rate'] = _to_float(form_data.get('interest_rate'))
    row['emp_length'] = _to_float(form_data.get('emp_length'))
    row['term'] = _to_float(form_data.get('tenor'))

    # Optional alias if the model was trained with joint-income style features.
    row['annual_income_joint'] = _to_float(form_data.get('annual_income_joint'), 0.0)
    row['debt_to_income_joint'] = _to_float(form_data.get('debt_to_income_joint'), 0.0)

    # One-hot fields from the form.
    grade = (form_data.get('grade') or '').strip().upper()
    if grade in {'B', 'C', 'D', 'E', 'F', 'G'}:
        row[f'grade_{grade}'] = 1.0

    purpose = (form_data.get('loan_purpose') or '').strip().lower()
    purpose_map = {
        'credit_card': 'loan_purpose_credit_card',
        'debt_consolidation': 'loan_purpose_debt_consolidation',
        'home_improvement': 'loan_purpose_home_improvement',
        'major_purchase': 'loan_purpose_major_purchase',
        'small_business': 'loan_purpose_small_business',
        'other': 'loan_purpose_other',
        'house': 'loan_purpose_house',
        'medical': 'loan_purpose_medical',
        'moving': 'loan_purpose_moving',
        'renewable_energy': 'loan_purpose_renewable_energy',
        'vacation': 'loan_purpose_vacation',
    }
    purpose_column = purpose_map.get(purpose)
    if purpose_column in row:
        row[purpose_column] = 1.0

    return pd.DataFrame([[row[column] for column in MODEL_FEATURES]], columns=MODEL_FEATURES)


def _log_prediction(inputs, prediction_result):
    payload = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'inputs': inputs,
        'prediction': prediction_result,
    }

    if mlflow is not None and MLFLOW_TRACKING_URI:
        try:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
            with mlflow.start_run(run_name='web-prediction'):
                mlflow.set_tag('source', 'flask-web')
                mlflow.log_metric('prediction_score', float(prediction_result['score']))
                mlflow.log_metric('prediction_is_aman', 1.0 if prediction_result['label'] == 'AMAN' else 0.0)
                mlflow.log_dict(payload, 'prediction.json')
            return
        except Exception as exc:  # pragma: no cover - monitoring must not break predictions
            app.logger.warning('MLflow logging failed: %s', exc)

    try:
        MONITORING_DIR.mkdir(parents=True, exist_ok=True)
        with LOCAL_PREDICTIONS_LOG.open('a', encoding='utf-8') as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=True) + '\n')
    except Exception as exc:  # pragma: no cover - logging should never block the request
        app.logger.warning('Local monitoring log failed: %s', exc)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/health')
def health():
    return {'status': 'ok'}, 200


@app.route('/dashboard')
def dashboard():
    stats = {'visits': 128, 'predictions': 42}
    return render_template('dashboard.html', stats=stats)


@app.route('/prediksi', methods=['GET', 'POST'])
def predict_page():
    hasil = None
    if request.method == 'POST':
        fitur = build_feature_frame(request.form)

        prediction = model.predict(fitur)[0]
        proba = model.predict_proba(fitur)[0][1] if hasattr(model, 'predict_proba') else 0.0

        hasil = {
            'label': 'AMAN' if int(prediction) == 1 else 'MACET',
            'score': round(float(proba), 4),
        }

        _log_prediction(
            {
                'pendapatan': request.form.get('pendapatan'),
                'pinjaman': request.form.get('pinjaman'),
                'dti': request.form.get('dti'),
                'interest_rate': request.form.get('interest_rate'),
                'emp_length': request.form.get('emp_length'),
                'loan_purpose': request.form.get('loan_purpose'),
                'grade': request.form.get('grade'),
                'tenor': request.form.get('tenor'),
            },
            hasil,
        )

    return render_template('prediksi.html', hasil=hasil)


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host='0.0.0.0', port=port)
