"""
Secured Health Monitoring API Routes with JWT Authentication
Compatible with midwife/patient health-monitoring frontend contract
"""

import logging
import traceback
from flask import Blueprint, request, jsonify

from risk_predition_model.auth.JWTauth import token_required
from risk_predition_model.app import get_predictor
from risk_predition_model.model.database import get_db_manager

logger = logging.getLogger(__name__)
health_monitoring_bp = Blueprint(
    "health_monitoring", __name__, url_prefix="/health-monitoring"
)

REQUIRED_FIELDS = [
    "age",
    "systolicBP",
    "diastolicBP",
    "bs",
    "bodyTemp",
    "bmi",
    "heartRate",
]

OPTIONAL_INT_FIELDS = [
    "previousComplications",
    "preexistingDiabetes",
    "gestationalDiabetes",
    "mentalHealth",
]


def validate_input_data(data):
    """Validate request payload for health monitoring routes."""
    missing_fields = []
    invalid_fields = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            missing_fields.append(field)
        elif data[field] == "" or data[field] is None:
            invalid_fields.append(f"{field} is empty")
        else:
            try:
                float(data[field])
            except (ValueError, TypeError):
                invalid_fields.append(f"{field} is not a valid number")

    for field in OPTIONAL_INT_FIELDS:
        if field in data and data[field] not in ("", None):
            try:
                int(data[field])
            except (ValueError, TypeError):
                invalid_fields.append(f"{field} is not a valid integer")

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    if invalid_fields:
        return False, f"Invalid field values: {'; '.join(invalid_fields)}"

    return True, None


def build_model_input_data(data):
    return {
        "Age": float(data["age"]),
        "SystolicBP": float(data["systolicBP"]),
        "DiastolicBP": float(data["diastolicBP"]),
        "BS": float(data["bs"]),
        "BodyTemp": float(data["bodyTemp"]),
        "BMI": float(data["bmi"]),
        "HeartRate": float(data["heartRate"]),
        "PreviousComplications": int(data.get("previousComplications", 0)),
        "PreexistingDiabetes": int(data.get("preexistingDiabetes", 0)),
        "GestationalDiabetes": int(data.get("gestationalDiabetes", 0)),
        "MentalHealth": int(data.get("mentalHealth", 0)),
    }


def normalize_prediction_row(prediction):
    if not prediction:
        return None

    vitals = prediction.get("vitals", {}) or {}
    risk_assessment = prediction.get("risk_assessment", {}) or {}
    health_guidance = prediction.get("health_guidance", {}) or {}

    updated_by_midwife_id = (
        prediction.get("updated_by_midwife_id")
        or prediction.get("updatedByMidwifeId")
        or None
    )

    return {
        "id": str(prediction.get("prediction_id") or prediction.get("id") or ""),
        "userId": str(prediction.get("user_id") or prediction.get("userId") or ""),
        "updatedByMidwifeId": updated_by_midwife_id,
        "age": int(vitals.get("Age", 0)),
        "systolicBP": int(vitals.get("SystolicBP", 0)),
        "diastolicBP": int(vitals.get("DiastolicBP", 0)),
        "bs": int(vitals.get("BS", 0)),
        "bodyTemp": float(vitals.get("BodyTemp", 0)),
        "bmi": float(vitals.get("BMI", 0)),
        "heartRate": int(vitals.get("HeartRate", 0)),
        "previousComplications": int(vitals.get("PreviousComplications", 0)),
        "preexistingDiabetes": int(vitals.get("PreexistingDiabetes", 0)),
        "gestationalDiabetes": int(vitals.get("GestationalDiabetes", 0)),
        "mentalHealth": int(vitals.get("MentalHealth", 0)),
        "riskLevel": risk_assessment.get("risk_level", ""),
        "riskConfidence": float(risk_assessment.get("confidence", 0)),
        "healthAdvice": health_guidance.get("primary_advice", ""),
        "adviceConfidence": float(health_guidance.get("advice_confidence", 0)),
        "riskProbabilities": risk_assessment.get("all_risk_probabilities", {}) or {},
        "alternativeAdvice": [
            {
                "advice": item if isinstance(item, str) else item.get("advice", ""),
                "confidence": 0
                if isinstance(item, str)
                else float(item.get("confidence", 0)),
            }
            for item in (health_guidance.get("alternative_recommendations", []) or [])
        ],
        "patientProfile": prediction.get("patient_profile", {}) or {},
        "createdAt": prediction.get("created_at") or prediction.get("createdAt"),
        "updatedAt": prediction.get("updated_at") or prediction.get("updatedAt"),
    }


def get_authenticated_user_id():
    email = request.user_email
    db_manager = get_db_manager()
    user_id = db_manager.create_user(email)
    return db_manager, email, user_id


def ensure_midwife_access(auth_user_id, midwife_id):
    try:
        return int(auth_user_id) == int(midwife_id)
    except Exception:
        return False


def predict_from_input(input_data):
    predictor = get_predictor()
    prediction_result = predictor.predict_risk_and_advice(input_data)

    if "error" in prediction_result:
        return None, prediction_result["error"]

    return prediction_result, None


@health_monitoring_bp.route(
    "/midwife/<int:midwife_id>/patient/<int:patient_id>/latest", methods=["GET"]
)
@token_required
def get_latest_health_monitoring(midwife_id, patient_id):
    try:
        db_manager, _, auth_user_id = get_authenticated_user_id()

        if not auth_user_id:
            return jsonify({"status": "error", "error": "Failed to get authenticated user"}), 500

        if not ensure_midwife_access(auth_user_id, midwife_id):
            return jsonify({
                "status": "error",
                "error": "You do not have permission to access this patient's records"
            }), 403

        prediction = db_manager.get_latest_prediction(patient_id)
        if not prediction:
            return jsonify({"status": "error", "error": "No health monitoring records found"}), 404

        return jsonify({
            "status": "success",
            "data": prediction
        }), 200

    except Exception as e:
        logger.error(f"Error in get_latest_health_monitoring: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500


@health_monitoring_bp.route(
    "/midwife/<int:midwife_id>/patient/<int:patient_id>", methods=["POST"]
)
@token_required
def create_health_monitoring(midwife_id, patient_id):
    try:
        data = request.get_json(force=True)

        if not data:
            return jsonify({"status": "error", "error": "No JSON data provided"}), 400

        is_valid, error_msg = validate_input_data(data)
        if not is_valid:
            return jsonify({"status": "error", "error": error_msg}), 400

        db_manager, _, auth_user_id = get_authenticated_user_id()

        if not auth_user_id:
            return jsonify({"status": "error", "error": "Failed to get authenticated user"}), 500

        if not ensure_midwife_access(auth_user_id, midwife_id):
            return jsonify({
                "status": "error",
                "error": "You do not have permission to create this patient's records"
            }), 403

        input_data = build_model_input_data(data)
        prediction_result, prediction_error = predict_from_input(input_data)

        if prediction_error:
            return jsonify({"status": "error", "error": prediction_error}), 500

        prediction_id = db_manager.store_prediction(
            patient_id,
            input_data,
            prediction_result
        )

        if not prediction_id:
            return jsonify({
                "status": "error",
                "error": "Failed to create health monitoring record"
            }), 500

        try:
            db_manager.update_prediction(
                patient_id,
                prediction_id,
                input_data,
                prediction_result,
                updated_by_midwife_id=midwife_id,
            )
        except Exception:
            logger.warning(
                "Could not stamp updated_by_midwife_id for prediction %s",
                prediction_id
            )

        created_prediction = db_manager.get_prediction(prediction_id, patient_id)
        normalized = normalize_prediction_row(created_prediction)

        logger.info(
            f"Successfully created health monitoring record {prediction_id} "
            f"for patient {patient_id} by midwife {midwife_id}"
        )

        return jsonify({
            "status": "success",
            "message": "Health monitoring record created successfully",
            "data": normalized,
        }), 201

    except Exception as e:
        logger.error(f"Error in create_health_monitoring: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500


@health_monitoring_bp.route(
    "/midwife/<int:midwife_id>/patient/<int:patient_id>/prediction/<int:prediction_id>",
    methods=["PUT"],
)
@token_required
def update_health_monitoring(midwife_id, patient_id, prediction_id):
    try:
        data = request.get_json(force=True)

        if not data:
            return jsonify({"status": "error", "error": "No JSON data provided"}), 400

        is_valid, error_msg = validate_input_data(data)
        if not is_valid:
            return jsonify({"status": "error", "error": error_msg}), 400

        db_manager, _, auth_user_id = get_authenticated_user_id()

        if not auth_user_id:
            return jsonify({"status": "error", "error": "Failed to get authenticated user"}), 500

        if not ensure_midwife_access(auth_user_id, midwife_id):
            return jsonify({
                "status": "error",
                "error": "You do not have permission to update this patient's records"
            }), 403

        existing = db_manager.get_prediction(prediction_id, patient_id)
        if not existing:
            return jsonify({
                "status": "error",
                "error": f"Prediction {prediction_id} not found for patient {patient_id}"
            }), 404

        input_data = build_model_input_data(data)
        prediction_result, prediction_error = predict_from_input(input_data)

        if prediction_error:
            return jsonify({"status": "error", "error": prediction_error}), 500

        success = db_manager.update_prediction(
            patient_id,
            prediction_id,
            input_data,
            prediction_result,
            updated_by_midwife_id=midwife_id,
        )
        if not success:
            return jsonify({"status": "error", "error": "Failed to update health monitoring record"}), 500

        updated_prediction = db_manager.get_prediction(prediction_id, patient_id)
        normalized = normalize_prediction_row(updated_prediction)

        logger.info(
            f"Successfully updated health monitoring record {prediction_id} "
            f"for patient {patient_id} by midwife {midwife_id}"
        )
        return jsonify({
            "status": "success",
            "message": "Health monitoring record updated successfully",
            "data": normalized,
        }), 200

    except Exception as e:
        logger.error(f"Error in update_health_monitoring: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500


@health_monitoring_bp.route(
    "/midwife/<int:midwife_id>/patient/<int:patient_id>/prediction/<int:prediction_id>",
    methods=["DELETE"],
)
@token_required
def delete_health_monitoring(midwife_id, patient_id, prediction_id):
    try:
        db_manager, _, auth_user_id = get_authenticated_user_id()

        if not auth_user_id:
            return jsonify({"status": "error", "error": "Failed to get authenticated user"}), 500

        if not ensure_midwife_access(auth_user_id, midwife_id):
            return jsonify({
                "status": "error",
                "error": "You do not have permission to delete this patient's records"
            }), 403

        existing = db_manager.get_prediction(prediction_id, patient_id)
        if not existing:
            return jsonify({
                "status": "error",
                "error": f"Prediction {prediction_id} not found for patient {patient_id}"
            }), 404

        success = db_manager.delete_prediction(prediction_id, patient_id)
        if not success:
            return jsonify({
                "status": "error",
                "error": "Failed to delete health monitoring record"
            }), 500

        logger.info(
            f"Successfully deleted health monitoring record {prediction_id} "
            f"for patient {patient_id} by midwife {midwife_id}"
        )

        return jsonify({
            "status": "success",
            "message": f"Health monitoring record {prediction_id} deleted successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error in delete_health_monitoring: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500