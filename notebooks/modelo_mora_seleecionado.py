# ============================================================
# MODELO: ÁRBOL DE DECISIÓN - PREDICCIÓN DE DEFAULT
# Dataset: Default_Clientes.csv
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_curve, roc_auc_score, f1_score,
    accuracy_score, precision_score, recall_score
)

# ============================================================
# 1. CARGA DE DATOS
# ============================================================

df = pd.read_csv("Default_Clientes.csv")

# ============================================================
# 2. PREPROCESAMIENTO
# ============================================================

# 2.1 Imputación de valores faltantes
for col in df.select_dtypes(include=np.number).columns:
    df[col] = df[col].fillna(df[col].median())

for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].fillna(df[col].mode()[0])

# 2.2 Eliminación de variables con alta multicolinealidad (VIF)
cols_eliminar = ['BILL_AMT2', 'BILL_AMT3', 'BILL_AMT4', 'BILL_AMT5', 'BILL_AMT6', 'AGE', 'ID']
df = df.drop(columns=[c for c in cols_eliminar if c in df.columns])

# 2.3 Ingeniería de variables a partir de las columnas PAY_*
pay_cols = ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6']
pay_amt_cols = ['PAY_AMT1', 'PAY_AMT2', 'PAY_AMT3', 'PAY_AMT4', 'PAY_AMT5', 'PAY_AMT6']

df['PAY_max'] = df[pay_cols].max(axis=1)
df['PAY_mean'] = df[pay_cols].mean(axis=1)
df['PAY_n_atrasos'] = (df[pay_cols] > 0).sum(axis=1)
df['PAY_AMT_total'] = df[pay_amt_cols].sum(axis=1)

df = df.drop(columns=pay_cols + pay_amt_cols)

# 2.4 Variable objetivo
y = df['Default']
X = df.drop(columns=['Default'])

# 2.5 Dummies para MARRIAGE
X = pd.get_dummies(X, columns=['MARRIAGE'], drop_first=True)

# 2.6 División entrenamiento / prueba (80/20 estratificada)
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

# 2.7 Escalado de variables numéricas
numericas = ['LIMIT_BAL', 'BILL_AMT1', 'PAY_max', 'PAY_mean', 'PAY_n_atrasos', 'PAY_AMT_total']
numericas = [c for c in numericas if c in X_train.columns]

scaler = StandardScaler()
X_train[numericas] = scaler.fit_transform(X_train[numericas])
X_test[numericas] = scaler.transform(X_test[numericas])

# ============================================================
# 3. MODELO: ÁRBOL DE DECISIÓN
# Hiperparámetros óptimos encontrados por Optuna
# ============================================================

modelo_arbol = DecisionTreeClassifier(
    max_depth=6,
    min_samples_leaf=27,
    min_samples_split=13,
    criterion='entropy',
    class_weight='balanced',
    random_state=42
)

modelo_arbol.fit(X_train, y_train)

# ============================================================
# 4. VALIDACIÓN CRUZADA ESTRATIFICADA (5-FOLD)
# ============================================================

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

auc_scores = cross_val_score(modelo_arbol, X_train, y_train, cv=skf, scoring='roc_auc')
recall_scores = cross_val_score(modelo_arbol, X_train, y_train, cv=skf, scoring='recall')
f1_scores = cross_val_score(modelo_arbol, X_train, y_train, cv=skf, scoring='f1')

print("Validación Cruzada Estratificada (5-Fold)")
print(f"AUC:    {auc_scores.mean():.4f} ± {auc_scores.std():.4f}")
print(f"Recall: {recall_scores.mean():.4f} ± {recall_scores.std():.4f}")
print(f"F1:     {f1_scores.mean():.4f} ± {f1_scores.std():.4f}")

# ============================================================
# 5. PREDICCIÓN Y EVALUACIÓN (UMBRAL 0.5)
# ============================================================

y_pred = modelo_arbol.predict(X_test)
y_prob = modelo_arbol.predict_proba(X_test)[:, 1]

cm = confusion_matrix(y_test, y_pred)
print("\nMatriz de Confusión (umbral 0.5):")
print(cm)

print("\nReporte de Clasificación (umbral 0.5):")
print(classification_report(y_test, y_pred))

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
print("\nMétricas del modelo de Probabilidad de mora (umbral 0.5):")
print(f"Accuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print("Matriz de confusión [[TN, FP], [FN, TP]]:")
print(cm)

auc = roc_auc_score(y_test, y_prob)
print(f"\nAUC-ROC: {auc:.4f}")

# ============================================================
# 6. CURVA ROC Y UMBRAL DE YOUDEN
# ============================================================

fpr, tpr, thresholds = roc_curve(y_test, y_prob)
youden_index = tpr - fpr
optimal_idx = youden_index.argmax()
optimal_threshold = thresholds[optimal_idx]

print(f"\nThreshold óptimo (Índice de Youden): {optimal_threshold:.4f}")

y_pred_youden = (y_prob >= optimal_threshold).astype(int)

print("\nMatriz de Confusión (umbral Youden):")
print(confusion_matrix(y_test, y_pred_youden))

print("\nReporte de Clasificación (umbral Youden):")
print(classification_report(y_test, y_pred_youden))

# Gráfico curva ROC
plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, label=f"AUC = {auc:.4f}")
plt.plot([0, 1], [0, 1], linestyle='--', color='gray')
plt.scatter(fpr[optimal_idx], tpr[optimal_idx], color='red',
            label=f"Umbral óptimo = {optimal_threshold:.3f}")
plt.xlabel("Tasa de Falsos Positivos (FPR)")
plt.ylabel("Tasa de Verdaderos Positivos (TPR / Recall)")
plt.title("Curva ROC - Árbol de Decisión")
plt.legend()
plt.tight_layout()
plt.savefig("roc_arbol_decision.png", dpi=150)
plt.show()

# ============================================================
# 7. VISUALIZACIÓN DEL ÁRBOL (HASTA PROFUNDIDAD 3)
# Útil para explicar las reglas IF-THEN a estudiantes
# ============================================================

plt.figure(figsize=(20, 10))
plot_tree(
    modelo_arbol,
    feature_names=X_train.columns,
    class_names=['No Default', 'Default'],
    filled=True,
    rounded=True,
    max_depth=3,
    fontsize=9
)
plt.title("Árbol de Decisión - Reglas de Predicción de Default (hasta profundidad 3)")
plt.tight_layout()
plt.savefig("arbol_decision_reglas.png", dpi=150)
plt.show()

# ============================================================
# 8. IMPORTANCIA DE VARIABLES (SHAP)
# ============================================================

explainer = shap.TreeExplainer(modelo_arbol)
shap_values = explainer.shap_values(X_test)

# Para clasificación binaria, shap_values puede ser una lista [clase0, clase1]
# o un array 3D (muestras, variables, clases), según la versión de shap instalada
if isinstance(shap_values, list):
    shap_vals_default = shap_values[1] if len(shap_values) > 1 else shap_values[0]
elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
    shap_vals_default = shap_values[:, :, 1] if shap_values.shape[2] > 1 else shap_values[:, :, 0]
else:
    shap_vals_default = shap_values

shap_importance = (
    pd.DataFrame({"variable": X_test.columns, "shap_importance": np.abs(shap_vals_default).mean(axis=0)})
    .sort_values(by="shap_importance", ascending=False)
)
print("\nImportancia de variables según SHAP (promedio del valor absoluto):")
print(shap_importance.to_string(index=False))

plt.figure()
shap.summary_plot(shap_vals_default, X_test, show=False)
plt.title("Importancia de Variables (SHAP) - Árbol de Decisión")
plt.tight_layout()
plt.savefig("shap_arbol_decision.png", dpi=150, bbox_inches='tight')
plt.show()

# ============================================================
# 9. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 60)
print("RESUMEN - MODELO ÁRBOL DE DECISIÓN")
print("=" * 60)
print(f"Hiperparámetros: max_depth=6, min_samples_leaf=27, "
      f"min_samples_split=13, criterion='entropy'")
print(f"AUC-ROC (test):  {auc:.4f}")
print(f"Umbral 0.5    -> F1: {f1_score(y_test, y_pred):.4f}")
print(f"Umbral Youden -> F1: {f1_score(y_test, y_pred_youden):.4f} "
      f"(umbral = {optimal_threshold:.3f})")
print("\nInterpretación principal:")
print("- PAY_max <= ~0.78 (sin retrasos severos): mayoría clasificada como No Default")
print("- PAY_max > ~0.78 (al menos un mes con retraso): mayoría clasificada como Default")