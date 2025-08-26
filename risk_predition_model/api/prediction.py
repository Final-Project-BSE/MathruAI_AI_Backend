from flask import Blueprint, request, jsonify
import logging
from risk_predition_model.app import get_predictor

prediction_bp = Blueprint('prediction', __name__)
logger = logging.getLogger(__name__)

@prediction_bp.route('/predict', methods=['POST'])
def predict_risk_and_advice():
    """Predict both maternal risk level and health advice"""
    try:
        predictor = get_predictor()
        
        if predictor is None:
            return jsonify({
                'error': 'Model not loaded',
                'status': 'error'
            }), 500
        
        # Get input data
        input_data = request.get_json()
        
        if not input_data:
            return jsonify({
                'error': 'No input data provided',
                'status': 'error',
                'expected_format': {
                    'Age': 'number',
                    'SystolicBP': 'number',
                    'DiastolicBP': 'number', 
                    'BS': 'number (blood sugar)',
                    'BodyTemp': 'number',
                    'BMI': 'number',
                    'PreviousComplications': '0 or 1',
                    'PreexistingDiabetes': '0 or 1',
                    'GestationalDiabetes': '0 or 1',
                    'MentalHealth': '0 or 1',
                    'HeartRate': 'number'
                }
            }), 400
        
        # Validate required fields
        required_fields = ['Age', 'SystolicBP', 'DiastolicBP', 'BS', 'BodyTemp', 'BMI', 
                          'HeartRate']
        missing_fields = [field for field in required_fields if field not in input_data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {missing_fields}',
                'status': 'error',
                'provided_fields': list(input_data.keys())
            }), 400
        
        # Make prediction
        result = predictor.predict_risk_and_advice(input_data)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'status': 'error'
            }), 400
        
        return jsonify({
            'status': 'success',
            'data': {
                'risk_assessment': {
                    'risk_level': result['risk_level'],
                    'confidence': result['risk_confidence'],
                    'all_risk_probabilities': result['risk_probabilities']
                },
                'health_guidance': {
                    'primary_advice': result['health_advice'],
                    'advice_confidence': result['advice_confidence'],
                    'alternative_recommendations': result.get('alternative_advice', [])
                },
                'patient_profile': result.get('input_summary', {}),
                'technical_info': {
                    'features_analyzed': len(result['features_used']),
                    'model_version': '2.0'
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({
            'error': 'Internal server error during prediction',
            'status': 'error',
            'details': str(e)
        }), 500

@prediction_bp.route('/predict-risk-only', methods=['POST'])
def predict_risk_only():
    """Predict only risk level (backward compatibility)"""
    try:
        predictor = get_predictor()
        
        if predictor is None:
            return jsonify({
                'error': 'Model not loaded',
                'status': 'error'
            }), 500
        
        # Get input data
        input_data = request.get_json()
        
        if not input_data:
            return jsonify({
                'error': 'No input data provided',
                'status': 'error'
            }), 400
        
        # Make prediction using backward compatibility method
        result = predictor.predict_risk(input_data)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'status': 'error'
            }), 400
        
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Risk-only prediction error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500

@prediction_bp.route('/batch-predict', methods=['POST'])
def batch_predict():
    """Predict risk and advice for multiple patients"""
    try:
        predictor = get_predictor()
        
        if predictor is None:
            return jsonify({
                'error': 'Model not loaded',
                'status': 'error'
            }), 500
        
        input_data = request.get_json()
        
        if not input_data or 'patients' not in input_data:
            return jsonify({
                'error': 'Invalid input format. Expected {"patients": [patient_data]}',
                'status': 'error'
            }), 400
        
        patients = input_data['patients']
        results = []
        
        for i, patient_data in enumerate(patients):
            try:
                result = predictor.predict_risk_and_advice(patient_data)
                
                # Format result for batch response
                formatted_result = {
                    'patient_id': i,
                    'risk_level': result.get('risk_level', 'Error'),
                    'risk_confidence': result.get('risk_confidence', 0.0),
                    'health_advice': result.get('health_advice', 'No advice available'),
                    'advice_confidence': result.get('advice_confidence', 0.0),
                    'patient_summary': result.get('input_summary', {}),
                    'status': 'success' if 'error' not in result else 'error'
                }
                
                if 'error' in result:
                    formatted_result['error'] = result['error']
                    formatted_result['status'] = 'error'
                
                results.append(formatted_result)
                
            except Exception as e:
                results.append({
                    'patient_id': i,
                    'error': str(e),
                    'risk_level': 'Error',
                    'health_advice': 'Error processing patient data',
                    'risk_confidence': 0.0,
                    'advice_confidence': 0.0,
                    'status': 'error'
                })
        
        # Calculate summary statistics
        successful_predictions = [r for r in results if r['status'] == 'success']
        error_count = len(results) - len(successful_predictions)
        
        # Risk level distribution
        risk_distribution = {}
        for result in successful_predictions:
            risk = result['risk_level']
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
        
        return jsonify({
            'status': 'success',
            'data': {
                'predictions': results,
                'summary': {
                    'total_patients': len(patients),
                    'successful_predictions': len(successful_predictions),
                    'errors': error_count,
                    'success_rate': len(successful_predictions) / len(patients) if patients else 0,
                    'risk_distribution': risk_distribution
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Batch prediction error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500