# attendancerisk.py

from risk_predictor import RiskPredictor

predictor = RiskPredictor()

# Predict for attendance=68, internal=60, assignment=55
result = predictor.predict(68, 60, 55)
print(f"Prediction for input [68, 60, 55]: {result}")