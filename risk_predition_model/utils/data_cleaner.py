import pandas as pd
import numpy as np

def clean_maternal_risk_data(input_file, output_file):
    """Clean the maternal risk dataset"""
    print("Loading data...")
    df = pd.read_csv(input_file)
    
    print(f"Original dataset shape: {df.shape}")
    print(f"Original columns: {list(df.columns)}")
    
    # Show missing values
    print(f"\nMissing values before cleaning:")
    print(df.isnull().sum())
    
    # Show basic statistics
    print(f"\nData description:")
    print(df.describe())
    
    # Check for outliers in Age (325 seems like an error)
    print(f"\nAge statistics:")
    print(f"Min Age: {df['Age'].min()}")
    print(f"Max Age: {df['Age'].max()}")
    print(f"Ages > 100: {(df['Age'] > 100).sum()}")
    
    if df['Age'].max() > 100:
        print("WARNING: Found unrealistic age values!")
        # Cap age at 50 (reasonable maximum for pregnancy)
        df['Age'] = df['Age'].clip(upper=50)
        print("Capped ages at 50")
    
    # Check BMI values
    print(f"\nBMI statistics:")
    print(f"Min BMI: {df['BMI'].min()}")
    print(f"Max BMI: {df['BMI'].max()}")
    print(f"BMI = 0: {(df['BMI'] == 0).sum()}")
    
    # Replace BMI = 0 with median
    if (df['BMI'] == 0).sum() > 0:
        median_bmi = df[df['BMI'] > 0]['BMI'].median()
        df['BMI'] = df['BMI'].replace(0, median_bmi)
        print(f"Replaced BMI = 0 with median: {median_bmi}")
    
    # Clean target column - remove rows with missing risk levels
    original_shape = df.shape[0]
    df = df.dropna(subset=['Risk Level'])
    print(f"Removed {original_shape - df.shape[0]} rows with missing Risk Level")
    
    # Fill other missing values
    print("\nFilling missing values...")
    
    # Numeric columns - fill with median
    numeric_cols = ['Systolic BP', 'Diastolic', 'BS', 'BMI', 'Previous Complications', 
                   'Preexisting Diabetes', 'Heart Rate']
    
    for col in numeric_cols:
        if col in df.columns and df[col].isnull().sum() > 0:
            median_val = df[col].median()
            missing_count = df[col].isnull().sum()
            df[col] = df[col].fillna(median_val)
            print(f"Filled {missing_count} missing values in {col} with median: {median_val}")
    
    # Remove duplicate rows
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        df = df.drop_duplicates()
        print(f"Removed {duplicate_count} duplicate rows")
    
    # Standardize column names (remove spaces, make consistent)
    column_mapping = {
        'Systolic BP': 'SystolicBP',
        'Diastolic': 'DiastolicBP',
        'Body Temp': 'BodyTemp',
        'Previous Complications': 'PreviousComplications',
        'Preexisting Diabetes': 'PreexistingDiabetes',
        'Gestational Diabetes': 'GestationalDiabetes',
        'Mental Health': 'MentalHealth',
        'Heart Rate': 'HeartRate',
        'Risk Level': 'RiskLevel'
    }
    
    df = df.rename(columns=column_mapping)
    
    print(f"\nCleaned dataset shape: {df.shape}")
    print(f"Cleaned columns: {list(df.columns)}")
    
    # Show final missing values
    print(f"\nMissing values after cleaning:")
    print(df.isnull().sum())
    
    # Show target distribution
    print(f"\nTarget distribution:")
    print(df['RiskLevel'].value_counts())
    print(f"\nTarget distribution percentages:")
    print(df['RiskLevel'].value_counts(normalize=True) * 100)
    
    # Show basic statistics after cleaning
    print(f"\nCleaned data description:")
    print(df.describe())
    
    # Save cleaned data
    df.to_csv(output_file, index=False)
    print(f"\nCleaned data saved to: {output_file}")
    
    return df

def validate_cleaned_data(file_path):
    """Validate the cleaned dataset"""
    df = pd.read_csv(file_path)
    
    print("=== DATA VALIDATION ===")
    print(f"Dataset shape: {df.shape}")
    
    # Check for any remaining issues
    issues = []
    
    # Missing values
    missing = df.isnull().sum().sum()
    if missing > 0:
        issues.append(f"Still has {missing} missing values")
    
    # Target column
    if 'RiskLevel' not in df.columns:
        issues.append("Missing RiskLevel column")
    else:
        unique_targets = df['RiskLevel'].unique()
        print(f"Unique risk levels: {unique_targets}")
        if len(unique_targets) < 2:
            issues.append("Less than 2 unique target classes")
    
    # Age range
    if 'Age' in df.columns:
        age_range = (df['Age'].min(), df['Age'].max())
        print(f"Age range: {age_range}")
        if age_range[0] < 10 or age_range[1] > 60:
            issues.append(f"Unrealistic age range: {age_range}")
    
    # BMI range
    if 'BMI' in df.columns:
        bmi_range = (df['BMI'].min(), df['BMI'].max())
        print(f"BMI range: {bmi_range}")
        if bmi_range[0] <= 0 or bmi_range[1] > 50:
            issues.append(f"Unrealistic BMI range: {bmi_range}")
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("✓ Data validation passed!")
    
    return len(issues) == 0

if __name__ == "__main__":
    # Clean the data
    input_file = "data/dataset1_with_health_advice.csv"
    output_file = "data/dataset_cleaned.csv"
    
    try:
        cleaned_df = clean_maternal_risk_data(input_file, output_file)
        
        # Validate cleaned data
        if validate_cleaned_data(output_file):
            print("\n" + "="*50)
            print("DATA CLEANING COMPLETED SUCCESSFULLY!")
            print(f"Use '{output_file}' for training your model")
            print("="*50)
        else:
            print("\n" + "="*50)
            print("DATA CLEANING COMPLETED WITH ISSUES!")
            print("Please review the issues above")
            print("="*50)
            
    except Exception as e:
        print(f"Error during data cleaning: {e}")
        import traceback
        traceback.print_exc()