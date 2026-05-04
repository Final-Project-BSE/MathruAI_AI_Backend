import joblib
import numpy as np
from typing import Dict, Any

from risk_predition_model.config import get_config


class RiskAdvicePredictor:
    def __init__(self, model_path=None):
        config = get_config()
        self.model_path = model_path or config.MODEL_PATH

        self.model_data = joblib.load(self.model_path)
        self.model_type = self.model_data.get("model_type", "multi_output")

        self.preprocessor = self.model_data["preprocessor"]
        self.risk_levels = self.model_data["risk_levels"]
        self.health_advice_options = self.model_data["health_advice_options"]

        if self.model_type == "separate_risk_advice_models":
            self.risk_model = self.model_data["risk_model"]
            self.advice_model = self.model_data["advice_model"]
            self.model = None
        else:
            self.model = self.model_data["model"]
            self.risk_model = None
            self.advice_model = None

    def predict_risk_and_advice(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            processed_data = self.preprocessor.preprocess_single_input(input_data)

            if self.model_type == "separate_risk_advice_models":
                return self._predict_separate_models(input_data, processed_data)

            return self._predict_multi_output(input_data, processed_data)

        except Exception as e:
            return {
                "error": str(e),
                "risk_level": "Error",
                "health_advice": "Unable to generate advice due to error",
                "risk_confidence": 0.0,
                "advice_confidence": 0.0,
            }

    def _predict_separate_models(self, input_data, processed_data):
        risk_prediction = self.risk_model.predict(processed_data)[0]
        advice_prediction = self.advice_model.predict(processed_data)[0]

        risk_probabilities = self.risk_model.predict_proba(processed_data)[0]
        advice_probabilities = self.advice_model.predict_proba(processed_data)[0]

        risk_level = self.preprocessor.risk_level_encoder.inverse_transform(
            [risk_prediction]
        )[0]

        health_advice = self.preprocessor.health_advice_encoder.inverse_transform(
            [advice_prediction]
        )[0]

        risk_confidence_scores = {}
        for i, level in enumerate(self.risk_levels):
            if i < len(risk_probabilities):
                risk_confidence_scores[level] = float(risk_probabilities[i])

        advice_confidence = float(max(advice_probabilities))

        top_advice_indices = np.argsort(advice_probabilities)[-3:][::-1]
        alternative_advice = []

        for idx in top_advice_indices:
            if idx < len(self.health_advice_options):
                advice_text = self.preprocessor.health_advice_encoder.inverse_transform(
                    [idx]
                )[0]
                alternative_advice.append({
                    "advice": advice_text,
                    "confidence": float(advice_probabilities[idx]),
                })

        return {
            "risk_level": risk_level,
            "risk_confidence": float(max(risk_probabilities)),
            "risk_probabilities": risk_confidence_scores,
            "health_advice": health_advice,
            "advice_confidence": advice_confidence,
            "alternative_advice": alternative_advice,
            "features_used": list(processed_data.columns),
            "input_summary": self._generate_input_summary(input_data),
        }

    def _predict_multi_output(self, input_data, processed_data):
        predictions = self.model.predict(processed_data)

        risk_prediction = predictions[0][0]
        advice_prediction = predictions[0][1]

        prediction_probas = self.model.predict_proba(processed_data)
        risk_probabilities = prediction_probas[0][0]
        advice_probabilities = prediction_probas[1][0]

        risk_level = self.preprocessor.risk_level_encoder.inverse_transform(
            [risk_prediction]
        )[0]

        health_advice = self.preprocessor.health_advice_encoder.inverse_transform(
            [advice_prediction]
        )[0]

        risk_confidence_scores = {}
        for i, level in enumerate(self.risk_levels):
            if i < len(risk_probabilities):
                risk_confidence_scores[level] = float(risk_probabilities[i])

        advice_confidence = (
            float(advice_probabilities[advice_prediction])
            if advice_prediction < len(advice_probabilities)
            else 0.0
        )

        top_advice_indices = np.argsort(advice_probabilities)[-3:][::-1]
        top_advice_options = []

        for idx in top_advice_indices:
            if idx < len(self.health_advice_options):
                advice_text = self.preprocessor.health_advice_encoder.inverse_transform(
                    [idx]
                )[0]
                top_advice_options.append({
                    "advice": advice_text,
                    "confidence": float(advice_probabilities[idx]),
                })

        return {
            "risk_level": risk_level,
            "risk_confidence": float(max(risk_probabilities)),
            "risk_probabilities": risk_confidence_scores,
            "health_advice": health_advice,
            "advice_confidence": advice_confidence,
            "alternative_advice": top_advice_options,
            "features_used": list(processed_data.columns),
            "input_summary": self._generate_input_summary(input_data),
        }

    def _generate_input_summary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        summary = {}

        age = input_data.get("Age", 0)
        if age < 18:
            summary["age_category"] = "Very young maternal age"
        elif age <= 25:
            summary["age_category"] = "Young maternal age"
        elif age <= 35:
            summary["age_category"] = "Optimal maternal age"
        else:
            summary["age_category"] = "Advanced maternal age"

        systolic = input_data.get("SystolicBP", 120)
        diastolic = input_data.get("DiastolicBP", 80)

        if systolic >= 140 or diastolic >= 90:
            summary["bp_status"] = "Hypertensive"
        elif systolic >= 130 or diastolic >= 80:
            summary["bp_status"] = "Stage 1 Hypertension"
        elif systolic >= 120:
            summary["bp_status"] = "Elevated"
        else:
            summary["bp_status"] = "Normal"

        bmi = input_data.get("BMI", 25)

        if bmi < 18.5:
            summary["bmi_category"] = "Underweight"
        elif bmi < 25:
            summary["bmi_category"] = "Normal weight"
        elif bmi < 30:
            summary["bmi_category"] = "Overweight"
        else:
            summary["bmi_category"] = "Obese"

        bs = input_data.get("BS", 100)

        if bs >= 126:
            summary["glucose_status"] = "Diabetic range"
        elif bs >= 100:
            summary["glucose_status"] = "Prediabetic range"
        else:
            summary["glucose_status"] = "Normal glucose"

        risk_factors = []

        if input_data.get("PreviousComplications", 0) == 1:
            risk_factors.append("Previous complications")

        if input_data.get("PreexistingDiabetes", 0) == 1:
            risk_factors.append("Preexisting diabetes")

        if input_data.get("GestationalDiabetes", 0) == 1:
            risk_factors.append("Gestational diabetes")

        if input_data.get("MentalHealth", 0) == 1:
            risk_factors.append("Mental health concerns")

        summary["risk_factors"] = risk_factors if risk_factors else ["None identified"]

        return summary

    def get_feature_importance(self) -> Dict[str, Dict[str, float]]:
        if self.model_type == "separate_risk_advice_models":
            features = self.preprocessor.feature_columns

            risk_importance = (
                self.risk_model.feature_importances_
                if hasattr(self.risk_model, "feature_importances_")
                else []
            )

            advice_importance = (
                self.advice_model.feature_importances_
                if hasattr(self.advice_model, "feature_importances_")
                else []
            )

            return {
                "risk_prediction": dict(zip(features, risk_importance.tolist())),
                "advice_prediction": dict(zip(features, advice_importance.tolist())),
            }

        if hasattr(self.model, "estimators_"):
            features = self.preprocessor.feature_columns
            risk_importance = self.model.estimators_[0].feature_importances_
            advice_importance = self.model.estimators_[1].feature_importances_

            return {
                "risk_prediction": dict(zip(features, risk_importance.tolist())),
                "advice_prediction": dict(zip(features, advice_importance.tolist())),
            }

        return {
            "risk_prediction": {},
            "advice_prediction": {},
        }

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_type,
            "risk_levels": self.risk_levels,
            "health_advice_options_count": len(self.health_advice_options),
            "model_path": self.model_path,
        }