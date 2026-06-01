# =============================================================================
# MODELO DE PREDICCIÓN DE DEFAULT - VERSIÓN ENRIQUECIDA
# Incluye: Optuna, GridSearch, CV Estratificada 5-fold, Puntos Influyentes,
#          SHAP, Betas + Interpretabilidad (RL), Árbol Graficado
# =============================================================================

# ----------------------------- Librerías -------------------------------------
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import (train_test_split, StratifiedKFold,
                                     cross_val_score, cross_validate)
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, plot_tree, export_text
from sklearn.metrics import (classification_report, confusion_matrix,
                             roc_auc_score, roc_curve, accuracy_score,
                             precision_score, recall_score, f1_score)
from sklearn.model_selection import GridSearchCV

import statsmodels.api as sm

import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

import shap

from xgboost import XGBClassifier

from pathlib import Path

output_dir = Path('notebooks/outputs_mora')

def out(fname):
    return str(output_dir / fname)

# ========================= 1. CARGA Y LIMPIEZA ================================
print("=" * 70)
print("1. CARGA Y PREPROCESAMIENTO")
print("=" * 70)

ruta_archivo = "data/raw/Default_Clientes.csv"
datos = pd.read_csv(ruta_archivo, sep=";")
copia_datos = datos.copy()

print(copia_datos['Default'].value_counts())
datos.info()

# Separar target
target_col = 'Default'

cols_numericas = datos.select_dtypes(include=[np.number]).columns.tolist()
cols_numericas.remove(target_col)
if 'ID' in cols_numericas:
    cols_numericas.remove('ID')

cols_texto = datos.select_dtypes(include=['object']).columns.tolist()

# Imputación
datos[cols_numericas] = datos[cols_numericas].fillna(datos[cols_numericas].median())
if cols_texto:
    for col in cols_texto:
        datos[col] = datos[col].fillna(datos[col].mode()[0])

cols_categoricas = ["SEX", "EDUCATION", "MARRIAGE", "PAY_0", "PAY_2", "PAY_3",
                    "PAY_4", "PAY_5", "PAY_6"]

for col in cols_categoricas:
    if col in datos.columns:
        datos[col] = datos[col].fillna(datos[col].mode()[0])
        datos[col] = datos[col].astype('category')

# Copia para análisis
copia_datos_agregacion = datos.copy()
for col in cols_categoricas:
    if col in copia_datos.columns:
        copia_datos[col] = copia_datos[col].astype('category')

# ========================= 2. INGENIERÍA DE VARIABLES =========================
print("\n" + "=" * 70)
print("2. INGENIERÍA DE VARIABLES Y REDUCCIÓN MULTICOLINEALIDAD")
print("=" * 70)

from statsmodels.stats.outliers_influence import variance_inflation_factor

variables_eliminar = ['ID', 'BILL_AMT2', 'BILL_AMT3', 'BILL_AMT4',
                      'BILL_AMT5', 'BILL_AMT6', 'AGE']
copia_datos_agregacion = copia_datos_agregacion.drop(columns=variables_eliminar)

for col in ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6']:
    copia_datos_agregacion[col] = copia_datos_agregacion[col].astype(int)

copia_datos_agregacion['PAY_max']      = copia_datos_agregacion[['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6']].max(axis=1)
copia_datos_agregacion['PAY_mean']     = copia_datos_agregacion[['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6']].mean(axis=1)
copia_datos_agregacion['PAY_n_atrasos']= (copia_datos_agregacion[['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6']] > 0).sum(axis=1)
copia_datos_agregacion['PAY_AMT_total']= copia_datos_agregacion[['PAY_AMT1','PAY_AMT2','PAY_AMT3','PAY_AMT4','PAY_AMT5','PAY_AMT6']].sum(axis=1)

cols_eliminar_vif = ['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6',
                     'PAY_AMT1','PAY_AMT2','PAY_AMT3','PAY_AMT4','PAY_AMT5','PAY_AMT6']
copia_datos_agregacion = copia_datos_agregacion.drop(columns=cols_eliminar_vif)

# VIF final
vif_final = pd.DataFrame()
vif_final['variable'] = copia_datos_agregacion.columns
vif_final['VIF'] = [variance_inflation_factor(copia_datos_agregacion.values, i)
                    for i in range(copia_datos_agregacion.shape[1])]
print("\nVIF Final (variables agregadas):")
print(vif_final.sort_values(by='VIF', ascending=False).to_string(index=False))

# ========================= 3. SPLIT Y ESCALADO ================================
print("\n" + "=" * 70)
print("3. DIVISIÓN Y ESCALADO")
print("=" * 70)

print("\nDistribución del target:")
print(copia_datos_agregacion['Default'].value_counts(normalize=True).mul(100).round(2))

X = copia_datos_agregacion.drop('Default', axis=1)
y = copia_datos_agregacion['Default']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=123, stratify=y)

# Escalado
numericas_scale = [f for f in X_train.columns if X_train[f].dtype in ['int64', 'float64']]
scaler = StandardScaler()
X_train = X_train.copy()
X_test  = X_test.copy()
X_train[numericas_scale] = scaler.fit_transform(X_train[numericas_scale])
X_test[numericas_scale]  = scaler.transform(X_test[numericas_scale])

# Dummies para MARRIAGE
X_train = pd.get_dummies(X_train, columns=['MARRIAGE'], drop_first=True)
X_test  = pd.get_dummies(X_test,  columns=['MARRIAGE'], drop_first=True)

# Convertir categóricas a int para XGB
X_train = X_train.astype({col: 'int' for col in X_train.select_dtypes('category').columns})
X_test  = X_test.astype({col: 'int'  for col in X_test.select_dtypes('category').columns})

# Convertir bools
bool_cols = X_train.select_dtypes(include='bool').columns
X_train[bool_cols] = X_train[bool_cols].astype(int)
X_test[bool_cols]  = X_test[bool_cols].astype(int)

# CV estratificada
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=123)

# ========================= 4. ANÁLISIS DE PUNTOS INFLUYENTES =================
# (basado en metodología del segundo .py con statsmodels)
print("\n" + "=" * 70)
print("4. ANÁLISIS DE PUNTOS INFLUYENTES (Regresión Logística con statsmodels)")
print("=" * 70)

X_sm = sm.add_constant(X_train.astype(float))
model_sm = sm.Logit(y_train, X_sm).fit(disp=False)

influence    = model_sm.get_influence()
leverage     = influence.hat_matrix_diag
cooks_d      = influence.cooks_distance[0]
std_residuals= influence.resid_studentized

n = X_sm.shape[0]
p = X_sm.shape[1]

cook_threshold     = 4 / n
leverage_threshold = 2 * p / n
residual_threshold = 2

print(f"Umbral Cook's Distance : {cook_threshold:.4f}")
print(f"Umbral Leverage        : {leverage_threshold:.4f}")
print(f"Umbral residuos estud. : ±{residual_threshold}")

influence_df = pd.DataFrame({
    'fila_original'     : X_train.index,
    'leverage'          : leverage,
    'cooks_distance'    : cooks_d,
    'standard_residuals': std_residuals
})

influence_df['alto_cook']    = influence_df['cooks_distance']    > cook_threshold
influence_df['alto_leverage']= influence_df['leverage']          > leverage_threshold
influence_df['alto_residuo'] = abs(influence_df['standard_residuals']) > residual_threshold
influence_df['punto_influyente'] = (
    influence_df['alto_cook'] |
    influence_df['alto_leverage'] |
    influence_df['alto_residuo']
)
influence_df['severo'] = (
    (influence_df['cooks_distance'] > 1) |
    (abs(influence_df['standard_residuals']) > 3) |
    (influence_df['leverage'] > 0.5)
)

puntos_influyentes = influence_df[influence_df['punto_influyente']]
puntos_severos     = influence_df[influence_df['severo']]

print(f"\nPuntos influyentes detectados (≥1 criterio) : {len(puntos_influyentes)}")
print(f"Puntos severamente influyentes               : {len(puntos_severos)}")

print("\nTop 10 por Cook's Distance:")
print(
    puntos_influyentes[['fila_original','cooks_distance','leverage',
                         'standard_residuals','alto_cook','alto_leverage','alto_residuo']]
    .sort_values('cooks_distance', ascending=False)
    .head(10)
    .to_string(index=False)
)

if len(puntos_severos) > 0:
    print("\nPuntos severamente influyentes:")
    print(
        puntos_severos[['fila_original','cooks_distance','leverage','standard_residuals']]
        .sort_values('cooks_distance', ascending=False)
        .to_string(index=False)
    )
else:
    print("\nNo se detectaron puntos severamente influyentes (Cook's>1, |residuo|>3, leverage>0.5).")
    print("El modelo no muestra inestabilidad severa por observaciones individuales.")

# Gráfico puntos influyentes
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
axes[0].scatter(influence_df.index, influence_df['cooks_distance'], alpha=0.5, s=10)
axes[0].axhline(cook_threshold, color='red', linestyle='--', label=f'Umbral={cook_threshold:.4f}')
axes[0].set_title("Cook's Distance")
axes[0].set_xlabel("Observación")
axes[0].legend()

axes[1].scatter(influence_df.index, influence_df['leverage'], alpha=0.5, s=10)
axes[1].axhline(leverage_threshold, color='red', linestyle='--', label=f'Umbral={leverage_threshold:.4f}')
axes[1].set_title("Leverage (Hat Values)")
axes[1].set_xlabel("Observación")
axes[1].legend()

axes[2].scatter(influence_df.index, influence_df['standard_residuals'], alpha=0.5, s=10)
axes[2].axhline( residual_threshold, color='red', linestyle='--', label=f'Umbral=±{residual_threshold}')
axes[2].axhline(-residual_threshold, color='red', linestyle='--')
axes[2].set_title("Residuos Estudentizados")
axes[2].set_xlabel("Observación")
axes[2].legend()

plt.suptitle("Análisis de Puntos Influyentes", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(out('puntos_influyentes.png'), dpi=150)
plt.close()
print("\n→ Gráfico guardado: puntos_influyentes.png")

# ===========================================================================
# FUNCIÓN AUXILIAR DE MÉTRICAS
# ===========================================================================
def evaluar_modelo(nombre, y_true, y_prob, umbral=0.5):
    y_pred = (y_prob >= umbral).astype(int)
    fpr, tpr, ths = roc_curve(y_true, y_prob)
    youden = tpr - fpr
    idx_opt = np.argmax(youden)
    umbral_opt = ths[idx_opt]
    y_pred_opt = (y_prob >= umbral_opt).astype(int)
    auc = roc_auc_score(y_true, y_prob)

    print(f"\n{'─'*50}")
    print(f"  {nombre}")
    print(f"{'─'*50}")
    print(f"  Umbral 0.5   → Acc={accuracy_score(y_true, y_pred):.4f} | "
          f"Prec={precision_score(y_true, y_pred):.4f} | "
          f"Rec={recall_score(y_true, y_pred):.4f} | "
          f"F1={f1_score(y_true, y_pred):.4f} | AUC={auc:.4f}")
    print(f"  Umbral Youden ({umbral_opt:.4f}) → Acc={accuracy_score(y_true, y_pred_opt):.4f} | "
          f"Prec={precision_score(y_true, y_pred_opt):.4f} | "
          f"Rec={recall_score(y_true, y_pred_opt):.4f} | "
          f"F1={f1_score(y_true, y_pred_opt):.4f}")
    print(f"\n  Matriz confusión (Youden):\n{confusion_matrix(y_true, y_pred_opt)}")
    return fpr, tpr, auc, umbral_opt


# ===========================================================================
# FUNCIÓN AUXILIAR CV ESTRATIFICADA
# ===========================================================================
def cv_estratificada(nombre, modelo, X, y, cv):
    scores = cross_validate(modelo, X, y, cv=cv,
                            scoring=['roc_auc','f1','recall','precision'],
                            return_train_score=False)
    print(f"\n  CV 5-Fold Estratificada — {nombre}")
    print(f"    AUC     : {scores['test_roc_auc'].mean():.4f} ± {scores['test_roc_auc'].std():.4f}")
    print(f"    F1      : {scores['test_f1'].mean():.4f} ± {scores['test_f1'].std():.4f}")
    print(f"    Recall  : {scores['test_recall'].mean():.4f} ± {scores['test_recall'].std():.4f}")
    print(f"    Precision: {scores['test_precision'].mean():.4f} ± {scores['test_precision'].std():.4f}")
    return scores


# ===========================================================================
#                   5. REGRESIÓN LOGÍSTICA
# ===========================================================================
print("\n" + "=" * 70)
print("5. REGRESIÓN LOGÍSTICA")
print("=" * 70)

# ---- 5a. GridSearch ----
print("\n[5a] GridSearch RL")
param_grid_rl = {
    'C'       : [0.01, 0.1, 1, 10],
    'penalty' : ['l1', 'l2'],
    'solver'  : ['liblinear']
}
gs_rl = GridSearchCV(
    LogisticRegression(class_weight='balanced', max_iter=1000, random_state=123),
    param_grid_rl, cv=skf, scoring='roc_auc', n_jobs=-1
)
gs_rl.fit(X_train, y_train)
print(f"  Mejores parámetros: {gs_rl.best_params_}  |  AUC CV: {gs_rl.best_score_:.4f}")

# ---- 5b. Optuna ----
print("\n[5b] Optuna RL")
def objective_rl(trial):
    C       = trial.suggest_float('C', 1e-3, 100, log=True)
    penalty = trial.suggest_categorical('penalty', ['l1', 'l2'])
    m = LogisticRegression(C=C, penalty=penalty, solver='liblinear',
                           class_weight='balanced', max_iter=1000, random_state=123)
    return cross_val_score(m, X_train, y_train, cv=skf, scoring='roc_auc').mean()

study_rl = optuna.create_study(direction='maximize')
study_rl.optimize(objective_rl, n_trials=40, show_progress_bar=False)
print(f"  Mejores params Optuna: {study_rl.best_params}  |  AUC: {study_rl.best_value:.4f}")

# ---- 5c. Modelo final RL ----
best_rl_params = study_rl.best_params
model_rl = LogisticRegression(
    C=best_rl_params['C'],
    penalty=best_rl_params['penalty'],
    solver='liblinear',
    class_weight='balanced',
    max_iter=1000, random_state=123
)
model_rl.fit(X_train, y_train)
y_prob_rl = model_rl.predict_proba(X_test)[:, 1]

# ---- 5d. CV estratificada ----
cv_estratificada("Regresión Logística", model_rl, X_train, y_train, skf)

# ---- 5e. Evaluación ----
fpr_rl, tpr_rl, auc_rl, umbral_rl = evaluar_modelo(
    "Regresión Logística", y_test, y_prob_rl)

# ---- 5f. BETAS E INTERPRETABILIDAD ----
print("\n[5f] Coeficientes (Betas) e Interpretabilidad — Regresión Logística")
coefs = pd.DataFrame({
    'Variable'  : X_train.columns,
    'Beta'      : model_rl.coef_[0],
    'Odds_Ratio': np.exp(model_rl.coef_[0])
}).sort_values('Beta', key=abs, ascending=False)

print("\n  Top 15 variables por magnitud del coeficiente:")
print(coefs.head(15).to_string(index=False))

print("""
  Interpretación de coeficientes (Odds Ratios):
  ─────────────────────────────────────────────
  • OR > 1: La variable aumenta el riesgo de Default.
            Ejemplo: OR=2.0 → la probabilidad de default es 2x mayor
            al incrementar 1 unidad (o pasar de 0 a 1 en dummies).
  • OR < 1: La variable reduce el riesgo de Default.
            Ejemplo: OR=0.5 → la probabilidad se reduce a la mitad.
  • OR = 1: La variable no tiene efecto sobre el Default.
  
  Como las variables numéricas están escaladas (StandardScaler),
  los betas representan el cambio en log-odds por cada desviación
  estándar, permitiendo comparar magnitudes entre variables.
""")

# Gráfico de betas
fig, ax = plt.subplots(figsize=(10, 8))
top_coefs = coefs.head(15).sort_values('Beta')
colores = ['#d73027' if v > 0 else '#4575b4' for v in top_coefs['Beta']]
ax.barh(top_coefs['Variable'], top_coefs['Beta'], color=colores)
ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlabel('Coeficiente Beta (escala log-odds)')
ax.set_title('Top 15 Coeficientes — Regresión Logística\n(Rojo=aumenta riesgo | Azul=reduce riesgo)')
plt.tight_layout()
plt.savefig(out('rl_betas.png'), dpi=150)
plt.close()

# Gráfico odds ratios con intervalo
print("\n  Intervalos de confianza 95% para Odds Ratios (via statsmodels):")
X_sm2 = sm.add_constant(X_train.astype(float))
model_sm2 = sm.Logit(y_train, X_sm2).fit(disp=False)
conf = model_sm2.conf_int()
conf.columns = ['lower', 'upper']
odds_ci = pd.DataFrame({
    'Variable'  : X_sm2.columns[1:],
    'OR'        : np.exp(model_sm2.params[1:]),
    'OR_lower'  : np.exp(conf['lower'][1:]),
    'OR_upper'  : np.exp(conf['upper'][1:]),
    'p_value'   : model_sm2.pvalues[1:]
}).sort_values('OR', ascending=False)
print(odds_ci.head(15).to_string(index=False))

fig, ax = plt.subplots(figsize=(10, 8))
top_or = odds_ci.head(15).sort_values('OR')
ax.barh(top_or['Variable'], top_or['OR'], color='steelblue', alpha=0.7)
ax.errorbar(top_or['OR'], range(len(top_or)),
            xerr=[top_or['OR'] - top_or['OR_lower'],
                  top_or['OR_upper'] - top_or['OR']],
            fmt='none', color='black', capsize=3)
ax.axvline(1, color='red', linestyle='--', label='OR=1 (sin efecto)')
ax.set_xlabel('Odds Ratio (IC 95%)')
ax.set_title('Odds Ratios con Intervalos de Confianza 95%\nRegresión Logística')
ax.legend()
plt.tight_layout()
plt.savefig(out('rl_odds_ratios.png'), dpi=150)
plt.close()
print("→ Gráficos guardados: rl_betas.png, rl_odds_ratios.png")

# ---- 5g. SHAP RL ----
print("\n[5g] SHAP — Regresión Logística")
explainer_rl = shap.LinearExplainer(model_rl, X_train, feature_perturbation="interventional")
shap_values_rl = explainer_rl.shap_values(X_test)

fig, ax = plt.subplots(figsize=(10, 7))
shap.summary_plot(shap_values_rl, X_test, show=False, plot_size=None)
plt.title("SHAP Summary — Regresión Logística")
plt.tight_layout()
plt.savefig(out('shap_rl.png'), dpi=150, bbox_inches='tight')
plt.close()
print("→ Gráfico guardado: shap_rl.png")


# ===========================================================================
#                   6. RANDOM FOREST
# ===========================================================================
print("\n" + "=" * 70)
print("6. RANDOM FOREST")
print("=" * 70)

# ---- 6a. GridSearch ----
print("\n[6a] GridSearch RF")
param_grid_rf = {
    'n_estimators': [100, 200],
    'max_depth'   : [5, 10, None],
    'min_samples_leaf': [5, 10]
}
gs_rf = GridSearchCV(
    RandomForestClassifier(class_weight='balanced', random_state=123),
    param_grid_rf, cv=skf, scoring='roc_auc', n_jobs=-1
)
gs_rf.fit(X_train, y_train)
print(f"  Mejores parámetros: {gs_rf.best_params_}  |  AUC CV: {gs_rf.best_score_:.4f}")

# ---- 6b. Optuna ----
print("\n[6b] Optuna RF")
def objective_rf(trial):
    params = {
        'n_estimators'    : trial.suggest_int('n_estimators', 50, 300),
        'max_depth'       : trial.suggest_int('max_depth', 3, 15),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 20),
        'max_features'    : trial.suggest_categorical('max_features', ['sqrt', 'log2'])
    }
    m = RandomForestClassifier(**params, class_weight='balanced', random_state=123)
    return cross_val_score(m, X_train, y_train, cv=skf, scoring='roc_auc').mean()

study_rf = optuna.create_study(direction='maximize')
study_rf.optimize(objective_rf, n_trials=30, show_progress_bar=False)
print(f"  Mejores params Optuna: {study_rf.best_params}  |  AUC: {study_rf.best_value:.4f}")

# ---- 6c. Modelo final RF ----
rf = RandomForestClassifier(
    **study_rf.best_params,
    class_weight='balanced', random_state=123
)
rf.fit(X_train, y_train)
y_prob_rf = rf.predict_proba(X_test)[:, 1]

# ---- 6d. CV estratificada ----
cv_estratificada("Random Forest", rf, X_train, y_train, skf)

# ---- 6e. Evaluación ----
fpr_rf, tpr_rf, auc_rf, umbral_rf_opt = evaluar_modelo(
    "Random Forest", y_test, y_prob_rf)

# ---- 6f. SHAP RF ----
print("\n[6f] SHAP — Random Forest")
explainer_rf = shap.TreeExplainer(rf)
shap_values_rf = explainer_rf.shap_values(X_test)

# Para clasificación binaria, SHAP entrega lista [clase0, clase1]
sv = shap_values_rf[1] if isinstance(shap_values_rf, list) else shap_values_rf

fig, ax = plt.subplots(figsize=(10, 7))
shap.summary_plot(sv, X_test, show=False, plot_size=None)
plt.title("SHAP Summary — Random Forest")
plt.tight_layout()
plt.savefig(out('shap_rf.png'), dpi=150, bbox_inches='tight')
plt.close()

# Importancia SHAP bar plot
fig, ax = plt.subplots(figsize=(10, 7))
shap.summary_plot(sv, X_test, plot_type='bar', show=False, plot_size=None)
plt.title("SHAP Importancia Media — Random Forest")
plt.tight_layout()
plt.savefig(out('shap_rf_bar.png'), dpi=150, bbox_inches='tight')
plt.close()
print("→ Gráficos guardados: shap_rf.png, shap_rf_bar.png")


# ===========================================================================
#                   7. ÁRBOL DE DECISIÓN
# ===========================================================================
print("\n" + "=" * 70)
print("7. ÁRBOL DE DECISIÓN")
print("=" * 70)

# ---- 7a. GridSearch ----
print("\n[7a] GridSearch DT")
param_grid_dt = {
    'max_depth'       : [3, 5, 7, 10],
    'min_samples_leaf': [5, 10, 20],
    'criterion'       : ['gini', 'entropy']
}
gs_dt = GridSearchCV(
    DecisionTreeClassifier(class_weight='balanced', random_state=123),
    param_grid_dt, cv=skf, scoring='roc_auc', n_jobs=-1
)
gs_dt.fit(X_train, y_train)
print(f"  Mejores parámetros: {gs_dt.best_params_}  |  AUC CV: {gs_dt.best_score_:.4f}")

# ---- 7b. Optuna ----
print("\n[7b] Optuna DT")
def objective_dt(trial):
    params = {
        'max_depth'       : trial.suggest_int('max_depth', 2, 12),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 30),
        'criterion'       : trial.suggest_categorical('criterion', ['gini', 'entropy']),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20)
    }
    m = DecisionTreeClassifier(**params, class_weight='balanced', random_state=123)
    return cross_val_score(m, X_train, y_train, cv=skf, scoring='roc_auc').mean()

study_dt = optuna.create_study(direction='maximize')
study_dt.optimize(objective_dt, n_trials=40, show_progress_bar=False)
print(f"  Mejores params Optuna: {study_dt.best_params}  |  AUC: {study_dt.best_value:.4f}")

# ---- 7c. Modelo final DT ----
dt = DecisionTreeClassifier(
    **study_dt.best_params,
    class_weight='balanced', random_state=123
)
dt.fit(X_train, y_train)
y_prob_dt = dt.predict_proba(X_test)[:, 1]

# ---- 7d. CV estratificada ----
cv_estratificada("Árbol de Decisión", dt, X_train, y_train, skf)

# ---- 7e. Evaluación ----
fpr_dt, tpr_dt, auc_dt, umbral_dt_opt = evaluar_modelo(
    "Árbol de Decisión", y_test, y_prob_dt)

# ---- 7f. GRÁFICO DEL ÁRBOL ----
print("\n[7f] Gráfico del Árbol de Decisión")

# Árbol para visualización: limitar profundidad a 4 para legibilidad
dt_viz = DecisionTreeClassifier(
    max_depth=min(4, study_dt.best_params.get('max_depth', 4)),
    class_weight='balanced', random_state=123,
    criterion=study_dt.best_params.get('criterion', 'gini')
)
dt_viz.fit(X_train, y_train)

fig, ax = plt.subplots(figsize=(28, 12))
plot_tree(
    dt_viz,
    feature_names=X_train.columns.tolist(),
    class_names=['No Default', 'Default'],
    filled=True, rounded=True,
    fontsize=8, ax=ax,
    impurity=True, proportion=False
)
plt.title("Árbol de Decisión (profundidad ≤ 4) — Default Clientes",
          fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(out('arbol_decision.png'), dpi=120, bbox_inches='tight')
plt.close()
print("→ Gráfico guardado: arbol_decision.png")

# Representación en texto del árbol
print("\n  Reglas del árbol (texto):")
print(export_text(dt_viz, feature_names=X_train.columns.tolist(), max_depth=3))

# ---- 7g. SHAP DT ----
print("\n[7g] SHAP — Árbol de Decisión")
explainer_dt = shap.TreeExplainer(dt)
shap_values_dt = explainer_dt.shap_values(X_test)
sv_dt = shap_values_dt[1] if isinstance(shap_values_dt, list) else shap_values_dt

fig, ax = plt.subplots(figsize=(10, 7))
shap.summary_plot(sv_dt, X_test, show=False, plot_size=None)
plt.title("SHAP Summary — Árbol de Decisión")
plt.tight_layout()
plt.savefig(out('shap_dt.png'), dpi=150, bbox_inches='tight')
plt.close()
print("→ Gráfico guardado: shap_dt.png")


# ===========================================================================
#                   8. XGBOOST
# ===========================================================================
print("\n" + "=" * 70)
print("8. XGBOOST")
print("=" * 70)

scale_pos = (y_train == 0).sum() / (y_train == 1).sum()

# ---- 8a. GridSearch ----
print("\n[8a] GridSearch XGB")
param_grid_xgb = {
    'n_estimators': [100, 200],
    'max_depth'   : [3, 5, 7],
    'learning_rate': [0.05, 0.1, 0.2]
}
gs_xgb = GridSearchCV(
    XGBClassifier(scale_pos_weight=scale_pos, random_state=123,
                  eval_metric='logloss', use_label_encoder=False),
    param_grid_xgb, cv=skf, scoring='roc_auc', n_jobs=-1
)
gs_xgb.fit(X_train, y_train)
print(f"  Mejores parámetros: {gs_xgb.best_params_}  |  AUC CV: {gs_xgb.best_score_:.4f}")

# ---- 8b. Optuna ----
print("\n[8b] Optuna XGB")
def objective_xgb(trial):
    params = {
        'n_estimators'  : trial.suggest_int('n_estimators', 50, 300),
        'max_depth'     : trial.suggest_int('max_depth', 2, 10),
        'learning_rate' : trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample'     : trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'reg_alpha'     : trial.suggest_float('reg_alpha', 1e-4, 10, log=True),
        'reg_lambda'    : trial.suggest_float('reg_lambda', 1e-4, 10, log=True)
    }
    m = XGBClassifier(
        **params,
        scale_pos_weight=scale_pos,
        random_state=123, eval_metric='logloss',
        use_label_encoder=False, verbosity=0
    )
    return cross_val_score(m, X_train, y_train, cv=skf, scoring='roc_auc').mean()

study_xgb = optuna.create_study(direction='maximize')
study_xgb.optimize(objective_xgb, n_trials=40, show_progress_bar=False)
print(f"  Mejores params Optuna: {study_xgb.best_params}  |  AUC: {study_xgb.best_value:.4f}")

# ---- 8c. Modelo final XGB ----
xgb = XGBClassifier(
    **study_xgb.best_params,
    scale_pos_weight=scale_pos,
    random_state=123, eval_metric='logloss',
    use_label_encoder=False, verbosity=0
)
xgb.fit(X_train, y_train)
y_prob_xgb = xgb.predict_proba(X_test)[:, 1]

# ---- 8d. CV estratificada ----
cv_estratificada("XGBoost", xgb, X_train, y_train, skf)

# ---- 8e. Evaluación ----
fpr_xgb, tpr_xgb, auc_xgb, umbral_xgb_opt = evaluar_modelo(
    "XGBoost", y_test, y_prob_xgb)

# ---- 8f. SHAP XGB ----
print("\n[8f] SHAP — XGBoost")
explainer_xgb = shap.TreeExplainer(xgb)
shap_values_xgb = explainer_xgb.shap_values(X_test)

fig, ax = plt.subplots(figsize=(10, 7))
shap.summary_plot(shap_values_xgb, X_test, show=False, plot_size=None)
plt.title("SHAP Summary — XGBoost")
plt.tight_layout()
plt.savefig(out('shap_xgb.png'), dpi=150, bbox_inches='tight')
plt.close()

fig, ax = plt.subplots(figsize=(10, 7))
shap.summary_plot(shap_values_xgb, X_test, plot_type='bar', show=False, plot_size=None)
plt.title("SHAP Importancia Media — XGBoost")
plt.tight_layout()
plt.savefig(out('shap_xgb_bar.png'), dpi=150, bbox_inches='tight')
plt.close()
print("→ Gráficos guardados: shap_xgb.png, shap_xgb_bar.png")


# ===========================================================================
#                   9. CURVAS ROC COMPARATIVAS
# ===========================================================================
print("\n" + "=" * 70)
print("9. COMPARACIÓN FINAL DE MODELOS")
print("=" * 70)

fig, ax = plt.subplots(figsize=(9, 7))
ax.plot(fpr_rl,  tpr_rl,  label=f'Regresión Logística (AUC={auc_rl:.4f})')
ax.plot(fpr_rf,  tpr_rf,  label=f'Random Forest       (AUC={auc_rf:.4f})')
ax.plot(fpr_dt,  tpr_dt,  label=f'Árbol de Decisión   (AUC={auc_dt:.4f})')
ax.plot(fpr_xgb, tpr_xgb, label=f'XGBoost             (AUC={auc_xgb:.4f})')
ax.plot([0, 1], [0, 1], 'k--', label='Aleatorio')
ax.set_xlabel('FPR (1 - Especificidad)')
ax.set_ylabel('TPR (Sensibilidad / Recall)')
ax.set_title('Curvas ROC — Comparación de Modelos')
ax.legend(loc='lower right')
plt.tight_layout()
plt.savefig(out('roc_comparacion.png'), dpi=150)
plt.close()
print("→ Gráfico guardado: roc_comparacion.png")

# Tabla resumen
resumen = pd.DataFrame([
    {'Modelo': 'Regresión Logística', 'AUC': auc_rl,  'Umbral_Youden': umbral_rl},
    {'Modelo': 'Random Forest',       'AUC': auc_rf,  'Umbral_Youden': umbral_rf_opt},
    {'Modelo': 'Árbol de Decisión',   'AUC': auc_dt,  'Umbral_Youden': umbral_dt_opt},
    {'Modelo': 'XGBoost',             'AUC': auc_xgb, 'Umbral_Youden': umbral_xgb_opt},
])
print("\n  Resumen comparativo (AUC en test):")
print(resumen.sort_values('AUC', ascending=False).to_string(index=False))

# ===========================================================================
#         9. MATRICES DE CONFUSIÓN COMPARATIVAS (2x2 grid, ambos umbrales)
# ===========================================================================
print("\n" + "=" * 70)
print("9. MATRICES DE CONFUSIÓN COMPARATIVAS")
print("=" * 70)
 
modelos_cm = {
    'Reg. Logística': (y_prob_rl,  umbral_rl),
    'Random Forest' : (y_prob_rf,  umbral_rf_opt),
    'Árbol Decisión': (y_prob_dt,  umbral_dt_opt),
    'XGBoost'       : (y_prob_xgb, umbral_xgb_opt),
}
 
for usar_youden, titulo_bloque, fname in [
    (False, 'Matrices de Confusión — Umbral 0.5',    'cm_umbral05.png'),
    (True,  'Matrices de Confusión — Umbral Youden', 'cm_youden.png'),
]:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(titulo_bloque, fontsize=15, fontweight='bold', y=1.01)
 
    for ax, (nombre, (y_prob, umbral_youden)) in zip(axes.flat, modelos_cm.items()):
        umbral = umbral_youden if usar_youden else 0.5
        y_pred = (y_prob >= umbral).astype(int)
        cm_mat = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm_mat.ravel()
 
        cm_norm = cm_mat.astype(float) / cm_mat.sum(axis=1, keepdims=True)
 
        ax.imshow(cm_norm, cmap='Blues', vmin=0, vmax=1)
 
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Pred: No Default', 'Pred: Default'], fontsize=10)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['Real: No Default', 'Real: Default'], fontsize=10)
 
        celdas         = [[tn, fp], [fn, tp]]
        etiquetas_tipo = [['TN', 'FP'], ['FN', 'TP']]
        for i in range(2):
            for j in range(2):
                pct      = cm_norm[i, j]
                cnt      = celdas[i][j]
                tipo     = etiquetas_tipo[i][j]
                color_txt = 'white' if pct > 0.55 else 'black'
                ax.text(j, i,
                        f"{tipo}\n{cnt:,}\n({pct:.1%})",
                        ha='center', va='center',
                        fontsize=11, fontweight='bold', color=color_txt)
 
        rec = recall_score(y_test, y_pred, zero_division=0)
        prec= precision_score(y_test, y_pred, zero_division=0)
        f1  = f1_score(y_test, y_pred, zero_division=0)
        acc = accuracy_score(y_test, y_pred)
        umbral_str = f"{umbral:.3f}" if usar_youden else "0.500"
        ax.set_title(
            f"{nombre}  (umbral={umbral_str})\n"
            f"Acc={acc:.3f} | Prec={prec:.3f} | Rec={rec:.3f} | F1={f1:.3f}",
            fontsize=10, pad=8
        )
 
    plt.tight_layout()
    plt.savefig(out(fname), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"→ Gráfico guardado: {fname}")


# ===========================================================================
# TABLA COMPARATIVA COMPLETA DE MÉTRICAS
# ===========================================================================
 
def metricas_completas(nombre, y_true, y_prob, umbral_05=0.5, umbral_youden=None):
    """Calcula todas las métricas para umbral 0.5 y umbral Youden."""
    filas = []
    for etiqueta, umbral in [('Umbral 0.5', umbral_05), (f'Youden ({umbral_youden:.3f})', umbral_youden)]:
        y_pred = (y_prob >= umbral).astype(int)
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()
        filas.append({
            'Modelo'        : nombre,
            'Umbral'        : etiqueta,
            'Accuracy'      : accuracy_score(y_true, y_pred),
            'Precision'     : precision_score(y_true, y_pred, zero_division=0),
            'Recall'        : recall_score(y_true, y_pred, zero_division=0),
            'F1-Score'      : f1_score(y_true, y_pred, zero_division=0),
            'Specificity'   : tn / (tn + fp) if (tn + fp) > 0 else 0,
            'AUC-ROC'       : roc_auc_score(y_true, y_prob),
            'TP'            : int(tp),
            'FP'            : int(fp),
            'TN'            : int(tn),
            'FN'            : int(fn),
        })
    return filas
 
rows = []
rows += metricas_completas('Reg. Logística', y_test, y_prob_rl,  umbral_youden=umbral_rl)
rows += metricas_completas('Random Forest',  y_test, y_prob_rf,  umbral_youden=umbral_rf_opt)
rows += metricas_completas('Árbol Decisión', y_test, y_prob_dt,  umbral_youden=umbral_dt_opt)
rows += metricas_completas('XGBoost',        y_test, y_prob_xgb, umbral_youden=umbral_xgb_opt)
 
df_resumen = pd.DataFrame(rows)
 
# Formatear decimales para impresión
metricas_num = ['Accuracy','Precision','Recall','F1-Score','Specificity','AUC-ROC']
df_print = df_resumen.copy()
df_print[metricas_num] = df_print[metricas_num].applymap(lambda x: f"{x:.4f}")
 
print("\n  ── TABLA COMPARATIVA COMPLETA DE MÉTRICAS (Test Set) ──")
print(df_print.to_string(index=False))
 
# Guardar como CSV
df_resumen.to_csv(out('tabla_comparativa_modelos.csv'), index=False, float_format='%.4f')
print("\n→ CSV guardado: tabla_comparativa_modelos.csv")
 
# ------------------------------------------------------------------
# Heatmap de métricas (solo umbral Youden para comparación limpia)
# ------------------------------------------------------------------
df_youden = df_resumen[df_resumen['Umbral'].str.startswith('Youden')].copy()
df_youden = df_youden.set_index('Modelo')[metricas_num]
 
import matplotlib.colors as mcolors
 
fig, ax = plt.subplots(figsize=(11, 4))
im = ax.imshow(df_youden.values.astype(float), cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
 
# Ejes
ax.set_xticks(range(len(metricas_num)))
ax.set_xticklabels(metricas_num, fontsize=11, fontweight='bold')
ax.set_yticks(range(len(df_youden)))
ax.set_yticklabels(df_youden.index, fontsize=11)
 
# Valores en celdas
for i in range(len(df_youden)):
    for j in range(len(metricas_num)):
        val = df_youden.values[i, j]
        color = 'black' if 0.35 < val < 0.75 else 'white'
        ax.text(j, i, f"{val:.4f}", ha='center', va='center',
                fontsize=10, color=color, fontweight='bold')
 
plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
ax.set_title("Comparación de Modelos — Umbral Youden (Test Set)\n"
             "Verde = mejor rendimiento | Rojo = menor rendimiento",
             fontsize=12, fontweight='bold', pad=12)
plt.tight_layout()
plt.savefig(out('heatmap_comparacion_modelos.png'), dpi=150, bbox_inches='tight')
plt.close()
print("→ Gráfico guardado: heatmap_comparacion_modelos.png")
 
# ------------------------------------------------------------------
# Gráfico de barras agrupadas por métrica
# ------------------------------------------------------------------
modelos   = df_youden.index.tolist()
x         = np.arange(len(metricas_num))
ancho     = 0.18
colores   = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
 
fig, ax = plt.subplots(figsize=(13, 6))
for i, (modelo, color) in enumerate(zip(modelos, colores)):
    valores = df_youden.loc[modelo].values.astype(float)
    bars = ax.bar(x + i * ancho, valores, ancho, label=modelo,
                  color=color, alpha=0.85, edgecolor='white')
    for bar, val in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005, f"{val:.3f}",
                ha='center', va='bottom', fontsize=7, rotation=45)
 
ax.set_xticks(x + ancho * 1.5)
ax.set_xticklabels(metricas_num, fontsize=11)
ax.set_ylim(0, 1.12)
ax.set_ylabel('Valor', fontsize=11)
ax.set_title('Comparación de Métricas por Modelo — Umbral Youden (Test Set)',
             fontsize=12, fontweight='bold')
ax.legend(loc='lower right', fontsize=10)
ax.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(out('barras_comparacion_modelos.png'), dpi=150, bbox_inches='tight')
plt.close()
print("→ Gráfico guardado: barras_comparacion_modelos.png")


print("\n" + "=" * 70)
print("PROCESO COMPLETADO — Todos los gráficos guardados en outputs/")
print("=" * 70)