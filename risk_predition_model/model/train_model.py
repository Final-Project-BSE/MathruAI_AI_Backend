import pandas as pd
import numpy as np
import os
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.multioutput import MultiOutputClassifier
import joblib

# Import the preprocessor from the model directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from risk_predition_model.utils.data_preprocessing import DataPreprocessor

class MaternalRiskAdviceModel:
    def __init__(self):
        self.model = None
        self.preprocessor = DataPreprocessor()
        self.risk_levels = None
        self.health_advice_options = None
        
    def train_model(self, data_files, risk_level_column='RiskLevel', health_advice_column='HealthAdvice'):
        """Train the Multi-Output Random Forest model"""
        print("="*60)
        print("TRAINING MATERNAL RISK & ADVICE PREDICTION MODEL")
        print("="*60)
        
        # Load data
        df = self.preprocessor.load_and_combine_data(data_files)
        
        # Show basic info about the dataset
        print(f"\nDataset Info:")
        print(f"Total records: {len(df)}")
        print(f"Total features: {len(df.columns)}")
        print("\nFirst few rows:")
        print(df.head())
        
        # Check for target columns
        possible_risk_names = [risk_level_column, 'risk_level', 'Risk Level', 'RISK_LEVEL', 
                              'RiskLevel', 'Risk', 'risk']
        possible_advice_names = [health_advice_column, 'health_advice', 'Health Advice', 
                                'HEALTH_ADVICE', 'HealthAdvice', 'Advice', 'advice']
        
        actual_risk_target = None
        actual_advice_target = None
        
        for col_name in possible_risk_names:
            if col_name in df.columns:
                actual_risk_target = col_name
                break
                
        for col_name in possible_advice_names:
            if col_name in df.columns:
                actual_advice_target = col_name
                break
        
        if actual_risk_target is None:
            print(f"\nAvailable columns: {list(df.columns)}")
            print(f"Please specify the correct risk level column name.")
            return None, 0, 0
            
        if actual_advice_target is None:
            print(f"\nAvailable columns: {list(df.columns)}")
            print(f"Please specify the correct health advice column name.")
            return None, 0, 0
        
        print(f"Using risk level column: {actual_risk_target}")
        print(f"Using health advice column: {actual_advice_target}")
        
        # Preprocess data
        X, y = self.preprocessor.preprocess_data(df, actual_risk_target, actual_advice_target)
        
        # Set risk levels and advice options
        self.risk_levels = self.preprocessor.risk_level_encoder.classes_.tolist()
        self.health_advice_options = self.preprocessor.health_advice_encoder.classes_.tolist()
        
        print(f"Risk levels: {self.risk_levels}")
        print(f"Number of health advice options: {len(self.health_advice_options)}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        print(f"\nTraining set size: {len(X_train)}")
        print(f"Test set size: {len(X_test)}")
        
        print("\nTraining Multi-Output Random Forest model...")
        
        # Create Random Forest classifier for multi-output
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        # Use MultiOutputClassifier to handle both outputs
        self.model = MultiOutputClassifier(rf, n_jobs=-1)
        
        # Train the model
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        print("\nEvaluating model...")
        y_pred = self.model.predict(X_test)
        
        # Calculate accuracy for each output
        risk_accuracy = accuracy_score(y_test[:, 0], y_pred[:, 0])
        advice_accuracy = accuracy_score(y_test[:, 1], y_pred[:, 1])
        
        print(f"\nRisk Level Prediction Accuracy: {risk_accuracy:.4f}")
        print(f"Health Advice Prediction Accuracy: {advice_accuracy:.4f}")
        
        # Detailed classification reports
        print("\nRisk Level Classification Report:")
        print(classification_report(y_test[:, 0], y_pred[:, 0], 
                                  target_names=self.risk_levels))
        
        print("\nHealth Advice Classification Report:")
        advice_sample = self.health_advice_options[:min(10, len(self.health_advice_options))]
        print(f"(Showing first {len(advice_sample)} advice categories)")
        
        # Feature importance (from the first estimator for risk level)
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'risk_importance': self.model.estimators_[0].feature_importances_,
            'advice_importance': self.model.estimators_[1].feature_importances_
        }).sort_values('risk_importance', ascending=False)
        
        print(f"\nTop 10 Most Important Features for Risk Prediction:")
        print(feature_importance[['feature', 'risk_importance']].head(10))
        
        print(f"\nTop 10 Most Important Features for Advice Prediction:")
        print(feature_importance[['feature', 'advice_importance']].head(10))
        
        return self.model, risk_accuracy, advice_accuracy
    
    def save_model(self, model_path='model/maternal_risk_advice_model.pkl'):
        """Save the trained model and preprocessor"""
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'preprocessor': self.preprocessor,
            'risk_levels': self.risk_levels,
            'health_advice_options': self.health_advice_options
        }
        
        joblib.dump(model_data, model_path)
        print(f"\nModel saved to {model_path}")
        
        # Save feature importance as CSV for reference
        if hasattr(self.model, 'estimators_'):
            feature_importance = pd.DataFrame({
                'feature': self.preprocessor.feature_columns,
                'risk_importance': self.model.estimators_[0].feature_importances_,
                'advice_importance': self.model.estimators_[1].feature_importances_
            }).sort_values('risk_importance', ascending=False)
            
            importance_path = model_path.replace('.pkl', '_feature_importance.csv')
            feature_importance.to_csv(importance_path, index=False)
            print(f"Feature importance saved to {importance_path}")

def main():
    """Main training function"""
    # Initialize model
    maternal_model = MaternalRiskAdviceModel()
    
    # Check if data files exist
    data_files = ['data/dataset_cleaned.csv']
    
    missing_files = [f for f in data_files if not os.path.exists(f)]
    if missing_files:
        print(f"Missing data files: {missing_files}")
        print("Please ensure your CSV files are in the 'data' directory")
        return
    
    # Modify these column names to match your dataset
    risk_level_column = 'RiskLevel'
    health_advice_column = 'HealthAdvice'
    
    try:
        # Train model
        model, risk_accuracy, advice_accuracy = maternal_model.train_model(
            data_files, risk_level_column, health_advice_column
        )
        
        if model is None:
            print("Training failed. Please check your column names.")
            return
        
        # Save model
        maternal_model.save_model()
        
        print("\n" + "="*60)
        print("MULTI-OUTPUT MODEL TRAINING COMPLETED SUCCESSFULLY!")
        print(f"Risk Level Prediction Accuracy: {risk_accuracy:.4f}")
        print(f"Health Advice Prediction Accuracy: {advice_accuracy:.4f}")
        print("You can now run the Flask app to make predictions.")
        print("="*60)
        
    except Exception as e:
        print(f"Error during training: {str(e)}")
        print("Please check your data files and column names.")

if __name__ == "__main__":
    main()