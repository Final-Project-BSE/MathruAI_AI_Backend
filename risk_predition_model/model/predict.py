import numpy as np
import joblib
from typing import Dict, Any
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class RiskAdvicePredictor:
    def __init__(self, model_path='model/maternal_risk_advice_model.pkl'):
        """Initialize the predictor with the trained model"""
        self.model_data = joblib.load(model_path)
        self.model = self.model_data['model']
        self.preprocessor = self.model_data['preprocessor']
        self.risk_levels = self.model_data['risk_levels']
        self.health_advice_options = self.model_data['health_advice_options']
        
    def predict_risk_and_advice(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict both maternal risk level and health advice"""
        try:
            # Preprocess input data
            processed_data = self.preprocessor.preprocess_single_input(input_data)
            
            # Make predictions (multi-output)
            predictions = self.model.predict(processed_data)
            risk_prediction = predictions[0][0]  # First output: risk level
            advice_prediction = predictions[0][1]  # Second output: health advice
            
            # Get prediction probabilities for both outputs
            prediction_probas = self.model.predict_proba(processed_data)
            risk_probabilities = prediction_probas[0][0]  # Risk level probabilities
            advice_probabilities = prediction_probas[1][0]  # Advice probabilities
            
            # Convert predictions back to original labels
            risk_level = self.preprocessor.risk_level_encoder.inverse_transform([risk_prediction])[0]
            health_advice = self.preprocessor.health_advice_encoder.inverse_transform([advice_prediction])[0]
            
            # Get confidence scores for risk levels
            risk_confidence_scores = {}
            for i, level in enumerate(self.risk_levels):
                if i < len(risk_probabilities):
                    risk_confidence_scores[level] = float(risk_probabilities[i])
            
            # Get confidence for the predicted advice
            advice_confidence = float(advice_probabilities[advice_prediction]) if advice_prediction < len(advice_probabilities) else 0.0
            
            # Get top 3 most likely advice options
            top_advice_indices = np.argsort(advice_probabilities)[-3:][::-1]  # Top 3 in descending order
            top_advice_options = []
            for idx in top_advice_indices:
                if idx < len(self.health_advice_options):
                    advice_text = self.preprocessor.health_advice_encoder.inverse_transform([idx])[0]
                    confidence = float(advice_probabilities[idx])
                    top_advice_options.append({
                        'advice': advice_text,
                        'confidence': confidence
                    })
            
            return {
                'risk_level': risk_level,
                'risk_confidence': float(max(risk_probabilities)),
                'risk_probabilities': risk_confidence_scores,
                'health_advice': health_advice,
                'advice_confidence': advice_confidence,
                'alternative_advice': top_advice_options,
                'features_used': list(processed_data.columns),
                'input_summary': self._generate_input_summary(input_data)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'risk_level': 'Error',
                'health_advice': 'Unable to generate advice due to error',
                'risk_confidence': 0.0,
                'advice_confidence': 0.0
            }
    
    def _generate_input_summary(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the input data for better interpretation"""
        summary = {}
        
        # Age assessment
        age = input_data.get('Age', 0)
        if age < 18:
            summary['age_category'] = 'Very young maternal age'
        elif age <= 25:
            summary['age_category'] = 'Young maternal age'
        elif age <= 35:
            summary['age_category'] = 'Optimal maternal age'
        else:
            summary['age_category'] = 'Advanced maternal age'
        
        # Blood pressure assessment
        systolic = input_data.get('SystolicBP', 120)
        diastolic = input_data.get('DiastolicBP', 80)
        if systolic >= 140 or diastolic >= 90:
            summary['bp_status'] = 'Hypertensive'
        elif systolic >= 130 or diastolic >= 80:
            summary['bp_status'] = 'Stage 1 Hypertension'
        elif systolic >= 120:
            summary['bp_status'] = 'Elevated'
        else:
            summary['bp_status'] = 'Normal'
        
        # BMI assessment
        bmi = input_data.get('BMI', 25)
        if bmi < 18.5:
            summary['bmi_category'] = 'Underweight'
        elif bmi < 25:
            summary['bmi_category'] = 'Normal weight'
        elif bmi < 30:
            summary['bmi_category'] = 'Overweight'
        else:
            summary['bmi_category'] = 'Obese'
        
        # Blood sugar assessment
        bs = input_data.get('BS', 100)
        if bs >= 126:
            summary['glucose_status'] = 'Diabetic range'
        elif bs >= 100:
            summary['glucose_status'] = 'Prediabetic range'
        else:
            summary['glucose_status'] = 'Normal glucose'
        
        # Risk factors summary
        risk_factors = []
        if input_data.get('PreviousComplications', 0) == 1:
            risk_factors.append('Previous complications')
        if input_data.get('PreexistingDiabetes', 0) == 1:
            risk_factors.append('Preexisting diabetes')
        if input_data.get('GestationalDiabetes', 0) == 1:
            risk_factors.append('Gestational diabetes')
        if input_data.get('MentalHealth', 0) == 1:
            risk_factors.append('Mental health concerns')
        
        summary['risk_factors'] = risk_factors if risk_factors else ['None identified']
        
        return summary
    
    def get_feature_importance(self) -> Dict[str, Dict[str, float]]:
        """Get feature importance from both models"""
        if hasattr(self.model, 'estimators_'):
            features = self.preprocessor.feature_columns
            risk_importance = self.model.estimators_[0].feature_importances_
            advice_importance = self.model.estimators_[1].feature_importances_
            
            return {
                'risk_prediction': dict(zip(features, risk_importance.tolist())),
                'advice_prediction': dict(zip(features, advice_importance.tolist()))
            }
        return {'risk_prediction': {}, 'advice_prediction': {}}
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information"""
        return {
            'risk_levels': self.risk_levels,
            'total_advice_options': len(self.health_advice_options),
            'feature_count': len(self.preprocessor.feature_columns),
            'features': self.preprocessor.feature_columns,
            'sample_advice_options': self.health_advice_options[:10]  # Show first 10 advice options
        }

# Compatibility class for existing code
class RiskPredictor(RiskAdvicePredictor):
    """Backward compatibility wrapper"""
    def __init__(self, model_path='model/maternal_risk_advice_model.pkl'):
        super().__init__(model_path)
    
    def predict_risk(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict risk (backward compatibility method)"""
        result = self.predict_risk_and_advice(input_data)
        
        # Return format compatible with old API
        return {
            'risk_level': result.get('risk_level'),
            'confidence': result.get('risk_confidence', 0.0),
            'all_probabilities': result.get('risk_probabilities', {}),
            'features_used': result.get('features_used', []),
            'health_advice': result.get('health_advice'),  # Added advice
            'advice_confidence': result.get('advice_confidence', 0.0),  # Added advice confidence
            'input_summary': result.get('input_summary', {})  # Added input summary
        }