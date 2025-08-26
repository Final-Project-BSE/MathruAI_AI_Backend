import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split

class DataPreprocessor:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.risk_level_encoder = None
        self.health_advice_encoder = None
        
    def load_and_combine_data(self, file_paths):
        """Load and combine multiple CSV files"""
        dataframes = []
        for file_path in file_paths:
            print(f"Loading {file_path}...")
            df = pd.read_csv(file_path)
            print(f"Shape: {df.shape}")
            dataframes.append(df)
        
        combined_df = pd.concat(dataframes, ignore_index=True)
        print(f"Combined shape: {combined_df.shape}")
        return combined_df
        
    def preprocess_data(self, df, risk_level_column='RiskLevel', health_advice_column='HealthAdvice'):
        """Preprocess the data for training with multi-output"""
        print(f"Dataset columns: {list(df.columns)}")
        print(f"Risk level column: {risk_level_column}")
        print(f"Health advice column: {health_advice_column}")
        
        # Handle missing values
        print("Handling missing values...")
        # For numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        
        # For categorical columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else 'Unknown')
        
        # Verify target columns exist
        if risk_level_column not in df.columns:
            print(f"Available columns: {list(df.columns)}")
            raise ValueError(f"Risk level column '{risk_level_column}' not found in dataset")
        
        if health_advice_column not in df.columns:
            print(f"Available columns: {list(df.columns)}")
            raise ValueError(f"Health advice column '{health_advice_column}' not found in dataset")
        
        # Separate features and targets
        X = df.drop(columns=[risk_level_column, health_advice_column])
        y_risk = df[risk_level_column]
        y_advice = df[health_advice_column]
        
        print(f"Features shape: {X.shape}")
        print(f"Risk level distribution:\n{y_risk.value_counts()}")
        print(f"Health advice distribution:\n{y_advice.value_counts()}")
        
        # Store feature columns
        self.feature_columns = X.columns.tolist()
        
        # Handle categorical variables in features
        categorical_columns = X.select_dtypes(include=['object']).columns
        print(f"Categorical columns: {list(categorical_columns)}")
        
        for col in categorical_columns:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            self.label_encoders[col] = le
            print(f"Encoded {col}: {len(le.classes_)} unique values")
        
        # Scale numerical features
        numerical_columns = X.select_dtypes(include=[np.number]).columns
        print(f"Numerical columns to scale: {list(numerical_columns)}")
        
        if len(numerical_columns) > 0:
            X[numerical_columns] = self.scaler.fit_transform(X[numerical_columns])
        
        # Encode target variables
        print("Encoding risk level...")
        self.risk_level_encoder = LabelEncoder()
        y_risk_encoded = self.risk_level_encoder.fit_transform(y_risk.astype(str))
        print(f"Risk level classes: {self.risk_level_encoder.classes_}")
        
        print("Encoding health advice...")
        self.health_advice_encoder = LabelEncoder()
        y_advice_encoded = self.health_advice_encoder.fit_transform(y_advice.astype(str))
        print(f"Health advice classes: {len(self.health_advice_encoder.classes_)} unique advice types")
        
        # Combine targets for multi-output
        y_combined = np.column_stack((y_risk_encoded, y_advice_encoded))
        
        return X, y_combined
    
    def preprocess_single_input(self, input_data):
        """Preprocess single input for prediction"""
        df = pd.DataFrame([input_data])
        
        # Ensure all expected columns are present
        for col in self.feature_columns:
            if col not in df.columns:
                df[col] = 0  # Default value for missing columns
        
        # Reorder columns to match training data
        df = df[self.feature_columns]
        
        # Apply preprocessing
        categorical_columns = df.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            if col in self.label_encoders:
                try:
                    df[col] = self.label_encoders[col].transform(df[col].astype(str))
                except ValueError:
                    # Handle unseen categories
                    print(f"Warning: Unknown category in {col}, using default value")
                    df[col] = 0
        
        numerical_columns = df.select_dtypes(include=[np.number]).columns
        if len(numerical_columns) > 0:
            df[numerical_columns] = self.scaler.transform(df[numerical_columns])
        
        return df