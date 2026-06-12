# risk_predictor.py

import os
import numpy as np
from sklearn.tree import DecisionTreeClassifier

class RiskPredictor:
    def __init__(self, performance_file='perfomance.py'):
        self.performance_file = performance_file
        self.model = DecisionTreeClassifier(random_state=42)
        self.is_trained = False
        self.train()

    def train(self):
        if not os.path.exists(self.performance_file):
            print(f"Error: {self.performance_file} not found.")
            return False
        
        try:
            features = []
            labels = []
            with open(self.performance_file, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                # Skip header line
                if parts[0] == 'Attendance' or 'result' in [p.lower() for p in parts]:
                    continue
                if len(parts) == 4:
                    try:
                        att = float(parts[0])
                        internal = float(parts[1])
                        assign = float(parts[2])
                        result = parts[3]  # Pass or Fail
                        features.append([att, internal, assign])
                        labels.append(1 if result.lower() == 'pass' else 0)
                    except ValueError:
                        continue
            
            if len(features) > 0:
                self.model.fit(np.array(features), np.array(labels))
                self.is_trained = True
                return True
            else:
                print("No data parsed from performance file.")
                return False
        except Exception as e:
            print(f"Error training model: {e}")
            return False

    def predict(self, attendance, internal, assignment):
        if not self.is_trained:
            # Fallback logic if training failed or file wasn't found
            return "Pass" if attendance >= 75 else "Fail"
        
        prediction = self.model.predict([[attendance, internal, assignment]])[0]
        return "Pass" if prediction == 1 else "Fail"

if __name__ == "__main__":
    predictor = RiskPredictor()
    print("Testing Risk Predictor:")
    print("Attendance=95, Internal=85, Assignment=80 -> Prediction:", predictor.predict(95, 85, 80))
    print("Attendance=50, Internal=40, Assignment=35 -> Prediction:", predictor.predict(50, 40, 35))
    print("Attendance=70, Internal=60, Assignment=55 -> Prediction:", predictor.predict(70, 60, 55))
