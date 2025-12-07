# debug_model.py - Run this to diagnose the model loading issue

import os
import sys
import traceback

def debug_model_loading():
    """Debug the maternal risk model loading process"""
    print("=" * 60)
    print("DEBUGGING MATERNAL RISK MODEL LOADING")
    print("=" * 60)
    
    # 1. Check current directory and project structure
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    
    # 2. Check if risk_predition_model directory exists
    risk_model_dir = "risk_predition_model"
    if os.path.exists(risk_model_dir):
        print(f"✓ {risk_model_dir} directory exists")
        print(f"Contents: {os.listdir(risk_model_dir)}")
        
        # Check for __init__.py files
        init_files = [
            "risk_predition_model/__init__.py",
            "risk_predition_model/model/__init__.py", 
            "risk_predition_model/api/__init__.py",
            "risk_predition_model/utils/__init__.py"
        ]
        
        for init_file in init_files:
            if os.path.exists(init_file):
                print(f"✓ {init_file} exists")
            else:
                print(f"✗ {init_file} MISSING - Creating it...")
                os.makedirs(os.path.dirname(init_file), exist_ok=True)
                open(init_file, 'a').close()
                
    else:
        print(f"✗ {risk_model_dir} directory does NOT exist")
        return False
    
    # 3. Check for model file
    model_path = "risk_predition_model/model/maternal_risk_advice_model.pkl"
    if os.path.exists(model_path):
        print(f"✓ Model file exists at: {model_path}")
        print(f"Model file size: {os.path.getsize(model_path)} bytes")
    else:
        print(f"✗ Model file NOT found at: {model_path}")
        
        # Check if model directory exists
        model_dir = "risk_predition_model/model"
        if os.path.exists(model_dir):
            print(f"Model directory contents: {os.listdir(model_dir)}")
        else:
            print(f"✗ Model directory does not exist: {model_dir}")
        
        print("\nYou need to train the model first. Run:")
        print("python risk_predition_model/model/train_model.py")
        return False
    
    # 4. Test imports step by step
    print("\n" + "=" * 40)
    print("TESTING IMPORTS")
    print("=" * 40)
    
    try:
        print("Testing: from risk_predition_model.config import config")
        from risk_predition_model.config import config
        print("✓ Config import successful")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("Testing: from risk_predition_model.utils.data_preprocessing import DataPreprocessor")
        from risk_predition_model.utils.data_preprocessing import DataPreprocessor
        print("✓ DataPreprocessor import successful")
    except Exception as e:
        print(f"✗ DataPreprocessor import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("Testing: from risk_predition_model.model.predict import RiskAdvicePredictor")
        from risk_predition_model.model.predict import RiskAdvicePredictor
        print("✓ RiskAdvicePredictor import successful")
    except Exception as e:
        print(f"✗ RiskAdvicePredictor import failed: {e}")
        traceback.print_exc()
        return False
    
    # 5. Test model loading
    print("\n" + "=" * 40)
    print("TESTING MODEL LOADING")
    print("=" * 40)
    
    try:
        predictor = RiskAdvicePredictor(model_path)
        print("✓ Model loaded successfully")
        
        # Test model info
        model_info = predictor.get_model_info()
        print(f"✓ Model info: {len(model_info.get('features', []))} features")
        print(f"✓ Risk levels: {model_info.get('risk_levels', [])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        traceback.print_exc()
        return False

def create_missing_files():
    """Create any missing __init__.py files"""
    print("\nCreating missing __init__.py files...")
    
    init_files = [
        "risk_predition_model/__init__.py",
        "risk_predition_model/model/__init__.py",
        "risk_predition_model/api/__init__.py", 
        "risk_predition_model/utils/__init__.py"
    ]
    
    for init_file in init_files:
        if not os.path.exists(init_file):
            os.makedirs(os.path.dirname(init_file), exist_ok=True)
            with open(init_file, 'w') as f:
                f.write("# Auto-generated __init__.py\n")
            print(f"Created: {init_file}")
        else:
            print(f"Exists: {init_file}")

def check_data_files():
    """Check if training data exists"""
    print("\n" + "=" * 40)
    print("CHECKING TRAINING DATA")
    print("=" * 40)
    
    data_files = [
        "data/dataset_cleaned.csv",
        "data/dataset1_with_health_advice.csv"
    ]
    
    for data_file in data_files:
        if os.path.exists(data_file):
            print(f"✓ Data file exists: {data_file}")
        else:
            print(f"✗ Data file missing: {data_file}")
    
    if not os.path.exists("data"):
        print("✗ Data directory does not exist")
        print("You need to create the 'data' directory and add your CSV files")

if __name__ == "__main__":
    # Create missing __init__.py files first
    create_missing_files()
    
    # Check data files
    check_data_files()
    
    # Run debug process
    success = debug_model_loading()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ ALL CHECKS PASSED - Model should work now!")
        print("Try running: python main.py")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ ISSUES FOUND - See above for details")
        print("=" * 60)
        
        print("\nNext steps:")
        print("1. If model file is missing, train it first:")
        print("   python risk_predition_model/model/train_model.py")
        print("2. If data files are missing, add them to the 'data' directory")
        print("3. Run this debug script again: python debug_model.py")