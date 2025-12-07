# import sys
# import os
# import pandas as pd
# import numpy as np

# # Add the current directory to Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# try:
#     from model.predict import RiskPredictor
# except ImportError:
#     # Try alternative import
#     try:
#         from predict import RiskPredictor
#     except ImportError:
#         print("Could not import RiskPredictor. Make sure the model is trained and saved.")
#         sys.exit(1)

# def test_prediction_pipeline():
#     """Test the complete prediction pipeline"""
#     print("="*60)
#     print("TESTING MATERNAL RISK PREDICTION PIPELINE")
#     print("="*60)
    
#     try:
#         # Initialize predictor
#         print("Loading model...")
#         predictor = RiskPredictor()
        
#         # Get model info
#         print("\nModel Information:")
#         model_info = predictor.get_model_info()
#         print(f"Risk levels: {model_info['risk_levels']}")
#         print(f"Expected features: {model_info['feature_columns']}")
#         print(f"Number of features: {model_info['n_features']}")
        
#         # Test cases based on your actual dataset columns
#         test_cases = [
#             {
#                 "name": "Low Risk Case",
#                 "data": {
#                     "Age": 25,
#                     "SystolicBP": 110,
#                     "DiastolicBP": 70,
#                     "BS": 6.5,
#                     "BodyTemp": 98,
#                     "BMI": 22.0,
#                     "PreviousComplications": 0,
#                     "PreexistingDiabetes": 0,
#                     "GestationalDiabetes": 0,
#                     "MentalHealth": 0,
#                     "HeartRate": 75
#                 }
#             },
#             {
#                 "name": "High Risk Case",
#                 "data": {
#                     "Age": 35,
#                     "SystolicBP": 150,
#                     "DiastolicBP": 95,
#                     "BS": 12.0,
#                     "BodyTemp": 99,
#                     "BMI": 30.0,
#                     "PreviousComplications": 1,
#                     "PreexistingDiabetes": 1,
#                     "GestationalDiabetes": 1,
#                     "MentalHealth": 1,
#                     "HeartRate": 85
#                 }
#             },
#             {
#                 "name": "Medium Risk Case",
#                 "data": {
#                     "Age": 28,
#                     "SystolicBP": 125,
#                     "DiastolicBP": 80,
#                     "BS": 8.0,
#                     "BodyTemp": 98,
#                     "BMI": 25.0,
#                     "PreviousComplications": 0,
#                     "PreexistingDiabetes": 0,
#                     "GestationalDiabetes": 1,
#                     "MentalHealth": 0,
#                     "HeartRate": 78
#                 }
#             }
#         ]
        
#         print("\n" + "="*40)
#         print("RUNNING TEST CASES")
#         print("="*40)
        
#         for i, test_case in enumerate(test_cases, 1):
#             print(f"\nTest Case {i}: {test_case['name']}")
#             print("-" * 30)
            
#             # Validate input
#             validation = predictor.validate_input_data(test_case['data'])
#             print(f"Input validation: {'✓ PASS' if validation['valid'] else '✗ FAIL'}")
            
#             if validation['warnings']:
#                 print("Warnings:")
#                 for warning in validation['warnings']:
#                     print(f"  - {warning}")
            
#             if validation['errors']:
#                 print("Errors:")
#                 for error in validation['errors']:
#                     print(f"  - {error}")
            
#             # Make prediction
#             print("Making prediction...")
#             result = predictor.predict_risk(test_case['data'])
            
#             if 'error' in result:
#                 print(f"❌ PREDICTION FAILED: {result['error']}")
#             else:
#                 print(f"✅ PREDICTION SUCCESS")
#                 print(f"   Risk Level: {result['risk_level']}")
#                 print(f"   Confidence: {result['confidence']:.3f}")
#                 print(f"   All Probabilities:")
#                 for level, prob in result['all_probabilities'].items():
#                     print(f"     {level}: {prob:.3f}")
        
#         # Test with original column names (if user sends data with spaces)
#         print("\n" + "="*40)
#         print("TESTING WITH ORIGINAL COLUMN NAMES")
#         print("="*40)
        
#         original_format_data = {
#             "Age": 30,
#             "Systolic BP": 130,  # Note: space in name
#             "Diastolic": 85,
#             "BS": 9.0,
#             "Body Temp": 98,
#             "BMI": 27.0,
#             "Previous Complications": 1,
#             "Preexisting Diabetes": 0,
#             "Gestational Diabetes": 0,
#             "Mental Health": 1,
#             "Heart Rate": 80
#         }
        
#         print("Testing with original column format...")
#         print(f"Input: {original_format_data}")
        
#         # This might fail, which would indicate a column name mismatch issue
#         try:
#             result = predictor.predict_risk(original_format_data)
#             if 'error' in result:
#                 print(f"❌ Failed with original names: {result['error']}")
#                 print("This indicates you need to clean your input data format")
#             else:
#                 print(f"✅ Success with original names: {result['risk_level']}")
#         except Exception as e:
#             print(f"❌ Exception with original names: {e}")
        
#         print("\n" + "="*60)
#         print("TEST SUMMARY")
#         print("="*60)
#         print("If all tests passed, your model is working correctly!")
#         print("If tests failed, check:")
#         print("1. Column names match exactly between training and prediction")
#         print("2. Data types are correct (numbers as numbers)")
#         print("3. Value ranges are reasonable")
#         print("4. No missing required features")
        
#     except Exception as e:
#         print(f"❌ CRITICAL ERROR: {e}")
#         import traceback
#         traceback.print_exc()
#         print("\nThis suggests:")
#         print("1. Model file might be corrupted or missing")
#         print("2. Model was trained with different feature names")
#         print("3. There's a version mismatch in dependencies")

# def test_with_real_data():
#     """Test with actual data from CSV if available"""
#     try:
#         # Try to load some real data for testing
#         data_file = "data/dataset1_cleaned.csv"
#         if os.path.exists(data_file):
#             print(f"\nTesting with real data from {data_file}")
#             df = pd.read_csv(data_file)
            
#             # Test with first few rows
#             predictor = RiskPredictor()
            
#             for i in range(min(3, len(df))):
#                 row = df.iloc[i]
#                 actual_risk = row['RiskLevel'] if 'RiskLevel' in row else 'Unknown'
                
#                 # Remove target column for prediction
#                 input_data = row.drop('RiskLevel', errors='ignore').to_dict()
                
#                 print(f"\nReal data test {i+1}:")
#                 print(f"Actual risk: {actual_risk}")
                
#                 result = predictor.predict_risk(input_data)
#                 if 'error' not in result:
#                     predicted_risk = result['risk_level']
#                     confidence = result['confidence']
#                     print(f"Predicted risk: {predicted_risk}")
#                     print(f"Confidence: {confidence:.3f}")
#                     print(f"Match: {'✓' if str(actual_risk).lower() == str(predicted_risk).lower() else '✗'}")
#                 else:
#                     print(f"Error: {result['error']}")
                    
#     except Exception as e:
#         print(f"Could not test with real data: {e}")

# if __name__ == "__main__":
#     test_prediction_pipeline()
#     test_with_real_data()