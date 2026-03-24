import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, ConfusionMatrixDisplay, roc_auc_score, roc_curve
)
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from risk_predition_model.utils.data_preprocessing import DataPreprocessor

df = pd.read_csv("risk_predition_model/data/dataset_cleaned.csv")

print("\n================ DATA QUALITY SUMMARY ================\n")
print(f"Total samples: {len(df)}")
print(f"Total columns: {len(df.columns)}")

print("\nMissing values summary:")
print(df.isnull().sum())

print("\nClass distribution (%):")
print((df["RiskLevel"].value_counts(normalize=True) * 100).round(2))

preprocessor = DataPreprocessor()
X, y = preprocessor.preprocess_data(df, "RiskLevel", "HealthAdvice")

y_risk = y[:, 0]

risk_classes = list(preprocessor.risk_level_encoder.classes_)
print("\nRisk classes:", risk_classes)

positive_label_name = "high risk" if "high risk" in [c.lower() for c in risk_classes] else risk_classes[-1]

for c in risk_classes:
    if c.lower() == positive_label_name.lower():
        positive_class = c
        break
else:
    positive_class = risk_classes[-1]

positive_index = list(risk_classes).index(positive_class)
y_binary = (y_risk == positive_index).astype(int)


X_train, X_test, y_train, y_test = train_test_split(
    X, y_binary, test_size=0.2, random_state=42, stratify=y_binary
)

print("\n================ SPLIT SUMMARY ================\n")
print(f"Train size: {len(X_train)} ({len(X_train)/len(X)*100:.1f}%)")
print(f"Test size : {len(X_test)} ({len(X_test)/len(X)*100:.1f}%)")


models = {
    "Baseline (majority)": DummyClassifier(strategy="most_frequent"),
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
}

results = []

print("\n================ MODEL COMPARISON ================\n")

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
    else:
        y_prob = None
        auc = np.nan

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    results.append([name, acc, prec, rec, f1, auc])

comparison_df = pd.DataFrame(
    results,
    columns=["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]
)

print(comparison_df.round(4))


rf = models["Random Forest"]
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

cv_results = cross_validate(
    rf, X, y_binary, cv=cv,
    scoring=["accuracy", "f1", "roc_auc"],
    return_train_score=False
)

cv_table = pd.DataFrame({
    "Fold": range(1, 6),
    "Accuracy": cv_results["test_accuracy"],
    "F1": cv_results["test_f1"],
    "ROC-AUC": cv_results["test_roc_auc"]
})

print("\n================ 5-FOLD CROSS-VALIDATION ================\n")
print(cv_table.round(4))
print("\nAverage:")
print(cv_table[["Accuracy", "F1", "ROC-AUC"]].mean().round(4))


rf.fit(X_train, y_train)

y_train_pred = rf.predict(X_train)
y_test_pred = rf.predict(X_test)

train_acc = accuracy_score(y_train, y_train_pred)
test_acc = accuracy_score(y_test, y_test_pred)
train_f1 = f1_score(y_train, y_train_pred, zero_division=0)
test_f1 = f1_score(y_test, y_test_pred, zero_division=0)

print("\n================ OVERFITTING CHECK ================\n")
print(pd.DataFrame({
    "Dataset": ["Train", "Test"],
    "Accuracy": [train_acc, test_acc],
    "F1": [train_f1, test_f1]
}).round(4))

print("\nInterpretation:")
print("Small train-test gap = better generalization.")
print("Large gap = overfitting risk.")


cm = confusion_matrix(y_test, y_test_pred)
print("\n================ CONFUSION MATRIX ================\n")
print(cm)

print("\n================ FINAL METRICS (RANDOM FOREST) ================\n")
print(f"Accuracy : {accuracy_score(y_test, y_test_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_test_pred, zero_division=0):.4f}")
print(f"Recall   : {recall_score(y_test, y_test_pred, zero_division=0):.4f}")
print(f"F1-score : {f1_score(y_test, y_test_pred, zero_division=0):.4f}")

disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Non-Risk", "Risk"])
disp.plot()
plt.title("Confusion Matrix - Random Forest")
plt.show()


y_test_prob = rf.predict_proba(X_test)[:, 1]
fpr, tpr, thresholds = roc_curve(y_test, y_test_prob)
auc = roc_auc_score(y_test, y_test_prob)

plt.figure()
plt.plot(fpr, tpr, label=f"Random Forest (AUC = {auc:.3f})")
plt.plot([0, 1], [0, 1], linestyle="--")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve")
plt.legend()
plt.show()


feature_importance = pd.DataFrame({
    "Feature": X.columns,
    "Importance": rf.feature_importances_
}).sort_values("Importance", ascending=False)

print("\n================ TOP FEATURE IMPORTANCE ================\n")
print(feature_importance.head(10).round(4))

plt.figure()
top10 = feature_importance.head(10).sort_values("Importance")
plt.barh(top10["Feature"], top10["Importance"])
plt.title("Top 10 Feature Importances")
plt.xlabel("Importance")
plt.show()