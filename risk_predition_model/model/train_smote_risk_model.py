import sys
from pathlib import Path

import joblib
import pandas as pd

from imblearn.over_sampling import SMOTE

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from risk_predition_model.utils.data_preprocessing import DataPreprocessor


DATASET_PATH = PROJECT_ROOT / "risk_predition_model" / "data" / "dataset_cleaned.csv"
MODEL_PATH = PROJECT_ROOT / "risk_predition_model" / "model" / "maternal_separate_smote_model.pkl"


def print_overfitting_check(model, X_train_original, y_train, X_test, y_test, title):
    print(f"\n================ {title} OVERFITTING / UNDERFITTING CHECK ================")

    y_train_pred = model.predict(X_train_original)
    y_test_pred = model.predict(X_test)

    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    train_f1 = f1_score(y_train, y_train_pred, average="weighted", zero_division=0)
    test_f1 = f1_score(y_test, y_test_pred, average="weighted", zero_division=0)

    print(f"Train Accuracy: {train_acc:.4f}")
    print(f"Test Accuracy : {test_acc:.4f}")
    print(f"Train F1-score: {train_f1:.4f}")
    print(f"Test F1-score : {test_f1:.4f}")

    gap = train_acc - test_acc
    print(f"Accuracy Gap  : {gap:.4f}")

    if train_acc > 0.95 and gap > 0.10:
        print("Interpretation: Possible OVERFITTING.")
    elif train_acc < 0.75 and test_acc < 0.75:
        print("Interpretation: Possible UNDERFITTING.")
    else:
        print("Interpretation: No major overfitting/underfitting signal.")


def train_models():
    print("=" * 70)
    print("TRAINING SEPARATE RISK + HEALTH ADVICE MODELS WITH SMOTE")
    print("=" * 70)

    df = pd.read_csv(DATASET_PATH)

    print("\nDataset shape:", df.shape)
    print("\nRiskLevel distribution:")
    print(df["RiskLevel"].value_counts())
    print("\nHealthAdvice classes:", df["HealthAdvice"].nunique())

    preprocessor = DataPreprocessor()
    X, y = preprocessor.preprocess_data(df, "RiskLevel", "HealthAdvice")

    y_risk = y[:, 0]
    y_advice = y[:, 1]

    X_train, X_test, y_risk_train, y_risk_test, y_advice_train, y_advice_test = train_test_split(
        X,
        y_risk,
        y_advice,
        test_size=0.2,
        random_state=42,
        stratify=y_risk,
    )

    print("\nBefore SMOTE risk distribution:")
    print(pd.Series(y_risk_train).value_counts().sort_index())

    smote = SMOTE(random_state=42)
    X_risk_train_smote, y_risk_train_smote = smote.fit_resample(
        X_train,
        y_risk_train,
    )

    print("\nAfter SMOTE risk distribution:")
    print(pd.Series(y_risk_train_smote).value_counts().sort_index())

    risk_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    advice_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=25,
        min_samples_split=3,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    print("\nTraining RiskLevel model with SMOTE...")
    risk_model.fit(X_risk_train_smote, y_risk_train_smote)

    print("\nTraining HealthAdvice model separately...")
    advice_model.fit(X_train, y_advice_train)

    print("\n================ RISK MODEL TEST RESULTS ================")
    y_risk_pred = risk_model.predict(X_test)

    print("Risk Accuracy:", round(accuracy_score(y_risk_test, y_risk_pred), 4))
    print("\nRisk Confusion Matrix:")
    print(confusion_matrix(y_risk_test, y_risk_pred))

    print("\nRisk Classification Report:")
    print(
        classification_report(
            y_risk_test,
            y_risk_pred,
            target_names=preprocessor.risk_level_encoder.classes_,
            zero_division=0,
        )
    )

    print_overfitting_check(
        risk_model,
        X_train,
        y_risk_train,
        X_test,
        y_risk_test,
        "RISK MODEL",
    )

    print("\n================ ADVICE MODEL TEST RESULTS ================")
    y_advice_pred = advice_model.predict(X_test)

    print("Advice Accuracy:", round(accuracy_score(y_advice_test, y_advice_pred), 4))

    print("\nAdvice Classification Report:")
    print(
        classification_report(
            y_advice_test,
            y_advice_pred,
            zero_division=0,
        )
    )

    print_overfitting_check(
        advice_model,
        X_train,
        y_advice_train,
        X_test,
        y_advice_test,
        "ADVICE MODEL",
    )

    print("\n================ RISK MODEL 5-FOLD CROSS VALIDATION ================")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    cv_results = cross_validate(
        risk_model,
        X,
        y_risk,
        cv=cv,
        scoring=["accuracy", "precision_weighted", "recall_weighted", "f1_weighted"],
        return_train_score=True,
    )

    cv_table = pd.DataFrame(
        {
            "Fold": range(1, 6),
            "Train Accuracy": cv_results["train_accuracy"],
            "Test Accuracy": cv_results["test_accuracy"],
            "Train F1": cv_results["train_f1_weighted"],
            "Test F1": cv_results["test_f1_weighted"],
        }
    )

    print(cv_table.round(4))

    print("\nCross-validation averages:")
    print(cv_table.mean(numeric_only=True).round(4))

    avg_gap = (
        cv_table["Train Accuracy"].mean()
        - cv_table["Test Accuracy"].mean()
    )

    print(f"\nAverage CV accuracy gap: {avg_gap:.4f}")

    if avg_gap > 0.10:
        print("CV Interpretation: Possible overfitting.")
    else:
        print("CV Interpretation: Generalization looks acceptable.")

    model_data = {
        "model_type": "separate_risk_advice_models",
        "risk_model": risk_model,
        "advice_model": advice_model,
        "preprocessor": preprocessor,
        "risk_levels": preprocessor.risk_level_encoder.classes_.tolist(),
        "health_advice_options": preprocessor.health_advice_encoder.classes_.tolist(),
        "feature_columns": list(X.columns),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_data, MODEL_PATH)

    print("\nSaved model to:")
    print(MODEL_PATH)

    print("\nTraining completed successfully.")


if __name__ == "__main__":
    train_models()