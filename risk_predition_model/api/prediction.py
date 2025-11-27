"""
Secured Pregnancy Risk Prediction API Routes with JWT Authentication
"""
from flask import Blueprint, request, jsonify
import logging
import traceback
from auth.JWTauth import token_required

logger = logging.getLogger(__name__)
prediction_bp = Blueprint('prediction', __name__)


def validate_input_data(data):
    """Validate input data"""
    required_fields = ['Age', 'SystolicBP', 'DiastolicBP', 'BS', 'BodyTemp', 'BMI', 'HeartRate']
    missing_fields = []
    invalid_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif data[field] == '' or data[field] is None:
            invalid_fields.append(f"{field} is empty")
        else:
            try:
                float(data[field])
            except (ValueError, TypeError):
                invalid_fields.append(f"{field} is not a valid number")
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    if invalid_fields:
        return False, f"Invalid field values: {'; '.join(invalid_fields)}"
    
    return True, None


@prediction_bp.route('/store', methods=['POST'])
@token_required
def store_prediction():
    """
    Store new prediction - PROTECTED ROUTE
    Automatically uses authenticated user's email from JWT token
    
    Request Headers:
    Authorization: Bearer <jwt_token>
    
    Request body:
    {
        "Age": 25,
        "SystolicBP": 120,
        "DiastolicBP": 80,
        "BS": 100,
        "BodyTemp": 98.6,
        "BMI": 22.5,
        "HeartRate": 75,
        "PreviousComplications": 0,
        "PreexistingDiabetes": 0,
        "GestationalDiabetes": 0,
        "MentalHealth": 0
    }
    """
    try:
        data = request.get_json(force=True)
        
        if not data:
            return jsonify({
                "status": "error",
                "error": "No JSON data provided"
            }), 400
        
        # Get email from JWT token (set by @token_required decorator)
        email = request.user_email
        
        # Validate input
        is_valid, error_msg = validate_input_data(data)
        if not is_valid:
            return jsonify({"status": "error", "error": error_msg}), 400
        
        # Prepare input data
        input_data = {
            'Age': float(data['Age']),
            'SystolicBP': float(data['SystolicBP']),
            'DiastolicBP': float(data['DiastolicBP']),
            'BS': float(data['BS']),
            'BodyTemp': float(data['BodyTemp']),
            'BMI': float(data['BMI']),
            'HeartRate': float(data['HeartRate']),
            'PreviousComplications': int(data.get('PreviousComplications', 0)),
            'PreexistingDiabetes': int(data.get('PreexistingDiabetes', 0)),
            'GestationalDiabetes': int(data.get('GestationalDiabetes', 0)),
            'MentalHealth': int(data.get('MentalHealth', 0))
        }
        
        logger.info(f"Processing prediction for authenticated user: {email}")
        
        # Get database manager
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        # Create or get user
        user_id = db_manager.create_user(email)
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to create user"
            }), 500
        
        # Get predictor
        try:
            from model.predict import RiskAdvicePredictor
            predictor = RiskAdvicePredictor()
        except:
            return jsonify({
                "status": "error",
                "error": "Prediction model not available"
            }), 503
        
        # Make prediction
        prediction_result = predictor.predict_risk_and_advice(input_data)
        
        if 'error' in prediction_result:
            return jsonify({
                "status": "error",
                "error": prediction_result['error']
            }), 500
        
        # Store in database
        prediction_id = db_manager.store_prediction(user_id, input_data, prediction_result)
        
        if not prediction_id:
            logger.error("Failed to store prediction")
            return jsonify({
                "status": "error",
                "error": "Failed to store prediction"
            }), 500
        
        response_data = {
            "status": "success",
            "message": "Prediction stored successfully",
            "data": {
                "prediction_id": prediction_id,
                "user_id": user_id,
                "email": email,
                "risk_assessment": {
                    "risk_level": prediction_result.get('risk_level'),
                    "confidence": prediction_result.get('risk_confidence'),
                    "all_risk_probabilities": prediction_result.get('risk_probabilities', {})
                },
                "health_guidance": {
                    "primary_advice": prediction_result.get('health_advice'),
                    "advice_confidence": prediction_result.get('advice_confidence'),
                    "alternative_recommendations": prediction_result.get('alternative_advice', [])
                },
                "patient_profile": prediction_result.get('input_summary', {}),
                "vitals": input_data
            }
        }
        
        logger.info(f"Successfully processed prediction {prediction_id}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Error in store_prediction: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/update/<int:prediction_id>', methods=['PUT'])
@token_required
def update_prediction(prediction_id):
    """
    Update existing prediction - PROTECTED ROUTE
    Only the owner can update their prediction
    """
    try:
        data = request.get_json(force=True)
        
        if not data:
            return jsonify({
                "status": "error",
                "error": "No JSON data provided"
            }), 400
        
        # Get email from JWT token
        email = request.user_email
        
        # Validate input
        is_valid, error_msg = validate_input_data(data)
        if not is_valid:
            return jsonify({"status": "error", "error": error_msg}), 400
        
        # Prepare input data
        input_data = {
            'Age': float(data['Age']),
            'SystolicBP': float(data['SystolicBP']),
            'DiastolicBP': float(data['DiastolicBP']),
            'BS': float(data['BS']),
            'BodyTemp': float(data['BodyTemp']),
            'BMI': float(data['BMI']),
            'HeartRate': float(data['HeartRate']),
            'PreviousComplications': int(data.get('PreviousComplications', 0)),
            'PreexistingDiabetes': int(data.get('PreexistingDiabetes', 0)),
            'GestationalDiabetes': int(data.get('GestationalDiabetes', 0)),
            'MentalHealth': int(data.get('MentalHealth', 0))
        }
        
        logger.info(f"Updating prediction {prediction_id} for user: {email}")
        
        # Get database manager
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        # Get user
        user_id = db_manager.create_user(email)
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        # Check if prediction exists and belongs to user
        existing = db_manager.get_prediction(prediction_id, user_id)
        if not existing:
            return jsonify({
                "status": "error",
                "error": f"Prediction {prediction_id} not found or you don't have permission"
            }), 404
        
        # Get predictor
        try:
            from model.predict import RiskAdvicePredictor
            predictor = RiskAdvicePredictor()
        except:
            return jsonify({
                "status": "error",
                "error": "Prediction model not available"
            }), 503
        
        # Make prediction
        prediction_result = predictor.predict_risk_and_advice(input_data)
        
        if 'error' in prediction_result:
            return jsonify({
                "status": "error",
                "error": prediction_result['error']
            }), 500
        
        # Update in database
        success = db_manager.update_prediction(user_id, prediction_id, input_data, prediction_result)
        
        if not success:
            return jsonify({
                "status": "error",
                "error": "Failed to update prediction"
            }), 500
        
        response_data = {
            "status": "success",
            "message": "Prediction updated successfully",
            "data": {
                "prediction_id": prediction_id,
                "user_id": user_id,
                "email": email,
                "risk_assessment": {
                    "risk_level": prediction_result.get('risk_level'),
                    "confidence": prediction_result.get('risk_confidence'),
                    "all_risk_probabilities": prediction_result.get('risk_probabilities', {})
                },
                "health_guidance": {
                    "primary_advice": prediction_result.get('health_advice'),
                    "advice_confidence": prediction_result.get('advice_confidence'),
                    "alternative_recommendations": prediction_result.get('alternative_advice', [])
                },
                "patient_profile": prediction_result.get('input_summary', {}),
                "vitals": input_data
            }
        }
        
        logger.info(f"Successfully updated prediction {prediction_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in update_prediction: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/get/<int:prediction_id>', methods=['GET'])
@token_required
def get_prediction(prediction_id):
    """Get a specific prediction - PROTECTED ROUTE"""
    try:
        email = request.user_email
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        user_id = db_manager.create_user(email)
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        prediction = db_manager.get_prediction(prediction_id, user_id)
        
        if not prediction:
            return jsonify({
                "status": "error",
                "error": f"Prediction {prediction_id} not found or you don't have permission"
            }), 404
        
        return jsonify({
            "status": "success",
            "data": prediction
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_prediction: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/latest', methods=['GET'])
@token_required
def get_latest():
    """Get latest prediction for authenticated user - PROTECTED ROUTE"""
    try:
        email = request.user_email
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        user_id = db_manager.create_user(email)
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        prediction = db_manager.get_latest_prediction(user_id)
        
        if not prediction:
            return jsonify({
                "status": "error",
                "error": "No predictions found"
            }), 404
        
        return jsonify({
            "status": "success",
            "data": prediction
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_latest: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/history', methods=['GET'])
@token_required
def get_history():
    """Get prediction history for authenticated user - PROTECTED ROUTE"""
    try:
        email = request.user_email
        limit = request.args.get('limit', 10, type=int)
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        user_id = db_manager.create_user(email)
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        predictions = db_manager.get_user_predictions(user_id, limit)
        
        return jsonify({
            "status": "success",
            "count": len(predictions),
            "data": predictions
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_history: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

@prediction_bp.route('/delete/<int:prediction_id>', methods=['DELETE'])
@token_required
def delete_prediction(prediction_id):
    """Delete a prediction - PROTECTED ROUTE"""
    try:
        email = request.user_email
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        user_id = db_manager.create_user(email)
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        success = db_manager.delete_prediction(prediction_id, user_id)
        
        if not success:
            return jsonify({
                "status": "error",
                "error": "Prediction not found or you don't have permission"
            }), 404
        
        return jsonify({
            "status": "success",
            "message": f"Prediction {prediction_id} deleted"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in delete_prediction: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/user/<int:user_id>/predictions', methods=['GET'])
@token_required
def get_predictions_by_user_id(user_id):
    """
    Get all predictions for a specific user ID - PROTECTED ROUTE
    Users can only access their own data
    
    Query Parameters:
    - limit: Maximum number of predictions to return (default: 10)
    """
    try:
        email = request.user_email
        limit = request.args.get('limit', 10, type=int)
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        # Get the authenticated user's ID
        auth_user_id = db_manager.create_user(email)
        if not auth_user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        # Check if the requested user_id matches the authenticated user
        if auth_user_id != user_id:
            return jsonify({
                "status": "error",
                "error": "You can only access your own predictions"
            }), 403
        
        predictions = db_manager.get_user_predictions(user_id, limit)
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "count": len(predictions),
            "data": predictions
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_predictions_by_user_id: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/user/<int:user_id>/latest', methods=['GET'])
@token_required
def get_latest_by_user_id(user_id):
    """
    Get latest prediction for a specific user ID - PROTECTED ROUTE
    Users can only access their own data
    """
    try:
        email = request.user_email
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        # Get the authenticated user's ID
        auth_user_id = db_manager.create_user(email)
        if not auth_user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        # Check if the requested user_id matches the authenticated user
        if auth_user_id != user_id:
            return jsonify({
                "status": "error",
                "error": "You can only access your own predictions"
            }), 403
        
        prediction = db_manager.get_latest_prediction(user_id)
        
        if not prediction:
            return jsonify({
                "status": "error",
                "error": "No predictions found"
            }), 404
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "data": prediction
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_latest_by_user_id: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/user/<int:user_id>/prediction/<int:prediction_id>', methods=['GET'])
@token_required
def get_prediction_by_user_id(user_id, prediction_id):
    """
    Get a specific prediction for a user ID - PROTECTED ROUTE
    Users can only access their own data
    """
    try:
        email = request.user_email
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        # Get the authenticated user's ID
        auth_user_id = db_manager.create_user(email)
        if not auth_user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        # Check if the requested user_id matches the authenticated user
        if auth_user_id != user_id:
            return jsonify({
                "status": "error",
                "error": "You can only access your own predictions"
            }), 403
        
        prediction = db_manager.get_prediction(prediction_id, user_id)
        
        if not prediction:
            return jsonify({
                "status": "error",
                "error": f"Prediction {prediction_id} not found"
            }), 404
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "data": prediction
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_prediction_by_user_id: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500


@prediction_bp.route('/user/<int:user_id>/prediction/<int:prediction_id>', methods=['PUT'])
@token_required
def update_prediction_by_user_id(user_id, prediction_id):
    """
    Update a prediction using user ID and prediction ID - PROTECTED ROUTE
    Users can only update their own data
    """
    try:
        data = request.get_json(force=True)
        
        if not data:
            return jsonify({
                "status": "error",
                "error": "No JSON data provided"
            }), 400
        
        email = request.user_email
        
        # Validate input
        is_valid, error_msg = validate_input_data(data)
        if not is_valid:
            return jsonify({"status": "error", "error": error_msg}), 400
        
        # Prepare input data
        input_data = {
            'Age': float(data['Age']),
            'SystolicBP': float(data['SystolicBP']),
            'DiastolicBP': float(data['DiastolicBP']),
            'BS': float(data['BS']),
            'BodyTemp': float(data['BodyTemp']),
            'BMI': float(data['BMI']),
            'HeartRate': float(data['HeartRate']),
            'PreviousComplications': int(data.get('PreviousComplications', 0)),
            'PreexistingDiabetes': int(data.get('PreexistingDiabetes', 0)),
            'GestationalDiabetes': int(data.get('GestationalDiabetes', 0)),
            'MentalHealth': int(data.get('MentalHealth', 0))
        }
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        # Get the authenticated user's ID
        auth_user_id = db_manager.create_user(email)
        if not auth_user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        # Check if the requested user_id matches the authenticated user
        if auth_user_id != user_id:
            return jsonify({
                "status": "error",
                "error": "You can only update your own predictions"
            }), 403
        
        # Check if prediction exists and belongs to user
        existing = db_manager.get_prediction(prediction_id, user_id)
        if not existing:
            return jsonify({
                "status": "error",
                "error": f"Prediction {prediction_id} not found"
            }), 404
        
        # Get predictor
        try:
            from model.predict import RiskAdvicePredictor
            predictor = RiskAdvicePredictor()
        except:
            return jsonify({
                "status": "error",
                "error": "Prediction model not available"
            }), 503
        
        # Make prediction
        prediction_result = predictor.predict_risk_and_advice(input_data)
        
        if 'error' in prediction_result:
            return jsonify({
                "status": "error",
                "error": prediction_result['error']
            }), 500
        
        # Update in database
        success = db_manager.update_prediction(user_id, prediction_id, input_data, prediction_result)
        
        if not success:
            return jsonify({
                "status": "error",
                "error": "Failed to update prediction"
            }), 500
        
        response_data = {
            "status": "success",
            "message": "Prediction updated successfully",
            "data": {
                "prediction_id": prediction_id,
                "user_id": user_id,
                "email": email,
                "risk_assessment": {
                    "risk_level": prediction_result.get('risk_level'),
                    "confidence": prediction_result.get('risk_confidence'),
                    "all_risk_probabilities": prediction_result.get('risk_probabilities', {})
                },
                "health_guidance": {
                    "primary_advice": prediction_result.get('health_advice'),
                    "advice_confidence": prediction_result.get('advice_confidence'),
                    "alternative_recommendations": prediction_result.get('alternative_advice', [])
                },
                "patient_profile": prediction_result.get('input_summary', {}),
                "vitals": input_data
            }
        }
        
        logger.info(f"Successfully updated prediction {prediction_id} for user {user_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in update_prediction_by_user_id: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500

@prediction_bp.route('/delete/<int:prediction_id>', methods=['DELETE'])
@token_required
def delete_prediction(prediction_id):
    """Delete a prediction - PROTECTED ROUTE"""
    try:
        email = request.user_email
        
        from model.database import get_db_manager
        db_manager = get_db_manager()
        
        user_id = db_manager.create_user(email)
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Failed to get user"
            }), 500
        
        success = db_manager.delete_prediction(prediction_id, user_id)
        
        if not success:
            return jsonify({
                "status": "error",
                "error": "Prediction not found or you don't have permission"
            }), 404
        
        return jsonify({
            "status": "success",
            "message": f"Prediction {prediction_id} deleted"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in delete_prediction: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), 500