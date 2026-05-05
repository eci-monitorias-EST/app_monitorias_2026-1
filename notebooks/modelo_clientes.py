#Importación de librerías
import pandas as pd
import numpy as np

ruta_archivo = "data/raw/Default_Clientes.csv"
datos = pd.read_csv(ruta_archivo, sep=";")
copia_datos = datos
copia_datos.head(10)
print(copia_datos['Default'].value_counts())

datos.info()

# ------------------------- Limpieza -------------------------
# 1. Separar la variable objetivo de las predictoras para no imputar el target
target_col = 'Default'

cols_numericas = datos.select_dtypes(include=[np.number]).columns.tolist()
cols_numericas.remove(target_col) # No tocar el target
# Remover ID que no aporta información predictiva
if 'ID' in cols_numericas:
    cols_numericas.remove('ID')
    
cols_texto = datos.select_dtypes(include=['object']).columns.tolist()

# 2. Imputación: mediana para numéricas, moda para categóricas (texto)
datos[cols_numericas] = datos[cols_numericas].fillna(datos[cols_numericas].median())

if cols_texto:
    for col in cols_texto:
        datos[col] = datos[col].fillna(datos[col].mode()[0])

# 3. Convertir variables que conceptualmente son categóricas al tipo 'category'
# Ojo: Mantenemos 'Default' como int (0 y 1) para SMOTE y modelos
cols_categoricas = ["SEX", "EDUCATION", "MARRIAGE", "PAY_0", "PAY_2", "PAY_3", 
                    "PAY_4", "PAY_5", "PAY_6"]

for col in cols_categoricas:
    if col in datos.columns:
        # Primero llenamos nulos en estas columnas categóricas numéricas con la moda
        datos[col] = datos[col].fillna(datos[col].mode()[0])
        datos[col] = datos[col].astype('category')
    else:
        print(f"Advertencia: columna '{col}' no encontrada")

print("\nLimpieza e imputación completada.")
print(f"Columnas categóricas: {datos.select_dtypes(include=['category']).columns.tolist()}")

cols_categoricas = ["SEX", "EDUCATION", "MARRIAGE", "PAY_0", "PAY_2", "PAY_3", 
                    "PAY_4", "PAY_5", "PAY_6"]

for col in cols_categoricas:
    if col in copia_datos.columns:
        copia_datos[col] = copia_datos[col].astype('category')
    else:
        print(f"Advertencia: columna '{col}' no encontrada")

copia_datos_agregacion = copia_datos

# Dado que hay desbalance en la variable objetivo, se utilizará el parámetro class_weight='balanced' en los modelos de clasificación para ajustar 
# automáticamente los pesos de las clases minoritarias y mayoritarias durante el entrenamiento. Esto ayuda a mejorar el rendimiento 
# del modelo en la clase minoritaria (Default=1) sin necesidad de realizar técnicas adicionales de sobremuestreo o submuestreo.

# Análisis de multicolinealidad
from statsmodels.stats.outliers_influence import variance_inflation_factor

vif = pd.DataFrame()
vif['variable'] = copia_datos_agregacion.columns
vif['VIF'] = [variance_inflation_factor(copia_datos_agregacion.values, i) for i in range(copia_datos_agregacion.shape[1])]

variables_eliminar = ['ID', 'BILL_AMT2', 'BILL_AMT3', 'BILL_AMT4', 
                      'BILL_AMT5', 'BILL_AMT6', 'AGE']

copia_datos_agregacion = copia_datos_agregacion.drop(columns=variables_eliminar)

print(vif.sort_values(by='VIF', ascending=False))

vif_2 = pd.DataFrame()
vif_2['variable'] = copia_datos_agregacion.columns
vif_2['VIF'] = [variance_inflation_factor(copia_datos_agregacion.values, i) for i in range(copia_datos_agregacion.shape[1])]

print(vif_2.sort_values(by='VIF', ascending=False))

# Se generan variables agrupadas para evitar que un usuario ingrese una extensión muy grande de datos
for col in ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6']:
    copia_datos_agregacion[col] = copia_datos_agregacion[col].astype(int)

copia_datos_agregacion['PAY_max'] = copia_datos_agregacion[['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6']].max(axis=1)
copia_datos_agregacion['PAY_mean'] = copia_datos_agregacion[['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6']].mean(axis=1)
copia_datos_agregacion['PAY_n_atrasos'] = (copia_datos_agregacion[['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6']] > 0).sum(axis=1)
copia_datos_agregacion['PAY_AMT_total'] = copia_datos_agregacion[['PAY_AMT1','PAY_AMT2','PAY_AMT3','PAY_AMT4','PAY_AMT5','PAY_AMT6']].sum(axis=1)

print(copia_datos_agregacion.columns)

#Eliminación de variables originales de pagos y montos para evitar multicolinealidad
# Eliminar las originales
cols_eliminar_vif = ['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6',
                 'PAY_AMT1','PAY_AMT2','PAY_AMT3','PAY_AMT4','PAY_AMT5','PAY_AMT6']

copia_datos_agregacion = copia_datos_agregacion.drop(columns=cols_eliminar_vif)

# Cálculo de VIF con variables agregadas
vif_3 = pd.DataFrame()
vif_3['variable'] = copia_datos_agregacion.columns
vif_3['VIF'] = [variance_inflation_factor(copia_datos_agregacion.values, i) for i in range(copia_datos_agregacion.shape[1])]

print(vif_3.sort_values(by='VIF', ascending=False))

from sklearn.model_selection import train_test_split

#Identificación de desbalance en la variable objetivo
print(copia_datos_agregacion['Default'].value_counts()/len(copia_datos_agregacion)*100)

# Se establece 80% de los datos para entrenamiento y 20% para prueba, con una semilla aleatoria de 123 para reproducibilidad.
X_train, X_test, y_train, y_test = train_test_split(copia_datos_agregacion.drop('Default', axis=1), copia_datos_agregacion['Default'], test_size=0.2, random_state=123)

from sklearn.preprocessing import StandardScaler
numericas = [f for f in X_train.columns if X_train[f].dtype in ['int64', 'float64']]

scaler = StandardScaler()

X_train[numericas] = scaler.fit_transform(X_train[numericas])
X_test[numericas] = scaler.transform(X_test[numericas])

for col in X_train.select_dtypes(include=['category']).columns:
    print(f"Columna: {col}")
    print(X_train[col].unique())

# Se aplica dumminización a la variable 'MARRIAGE', eliminando la primera categoría para evitar multicolinealidad. 
# Esto crea nuevas columnas binarias para cada categoría de 'MARRIAGE' excepto la primera, que se usará como referencia.
X_train = pd.get_dummies(X_train, columns=['MARRIAGE'], drop_first=True)
X_test = pd.get_dummies(X_test, columns=['MARRIAGE'], drop_first=True)

from sklearn.linear_model import LogisticRegression
model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=123)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

from sklearn.metrics import classification_report, confusion_matrix
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred)) 

from sklearn.metrics import roc_auc_score, roc_curve, auc, precision_recall_curve, precision_score, recall_score, f1_score, accuracy_score
# Porcentaje de aciertos totales
print(accuracy_score(y_test, y_pred))

# Precisión (calidad de positivos) y Recall (cantidad de positivos capturados)
print(precision_score(y_test, y_pred))
print(recall_score(y_test, y_pred))

# F1-Score (equilibrio entre precisión y recall)
print(f1_score(y_test, y_pred))

# Matriz de confusión (ver dónde se equivoca el modelo)
print(confusion_matrix(y_test, y_pred))

from sklearn.metrics import roc_curve, roc_auc_score
import matplotlib.pyplot as plt
import numpy as np

# Probabilidades
y_prob = model.predict_proba(X_test)[:, 1]

# Curva ROC
fpr, tpr, thresholds = roc_curve(y_test, y_prob)
auc = roc_auc_score(y_test, y_prob)

# Índice de Youden
youden = tpr - fpr
umbral_optimo = thresholds[np.argmax(youden)]
print(f'Umbral óptimo (Youden): {umbral_optimo:.4f}')
print(f'AUC-ROC: {auc:.4f}')

# Curva ROC
plt.figure(figsize=(8,6))
plt.plot(fpr, tpr, label=f'AUC = {auc:.4f}')
plt.plot([0,1],[0,1], 'k--', label='Aleatorio')
plt.axvline(fpr[np.argmax(youden)], color='red', linestyle='--', alpha=0.5)
plt.axhline(tpr[np.argmax(youden)], color='red', linestyle='--', alpha=0.5, label=f'Umbral Youden = {umbral_optimo:.4f}')
plt.xlabel('FPR (1 - Especificidad)')
plt.ylabel('TPR (Sensibilidad / Recall)')
plt.title('Curva ROC - Regresión Logística')
plt.legend()
plt.tight_layout()
plt.show()

## Métricas con umbral óptimo
# Aplicar umbral óptimo
y_pred_youden = (y_prob >= umbral_optimo).astype(int)

print(f'Umbral aplicado: {umbral_optimo:.4f}')
print(f'Accuracy:  {accuracy_score(y_test, y_pred_youden):.4f}')
print(f'Precision: {precision_score(y_test, y_pred_youden):.4f}')
print(f'Recall:    {recall_score(y_test, y_pred_youden):.4f}')
print(f'F1:        {f1_score(y_test, y_pred_youden):.4f}')
print()
print(confusion_matrix(y_test, y_pred_youden))

## Modelo con random forest
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(class_weight='balanced', random_state=123, n_estimators=100)
rf.fit(X_train, y_train)

y_pred_rf = rf.predict(X_test)
y_prob_rf = rf.predict_proba(X_test)[:, 1]

fpr_rf, tpr_rf, thresholds_rf = roc_curve(y_test, y_prob_rf)
youden_rf = tpr_rf - fpr_rf
umbral_rf = thresholds_rf[np.argmax(youden_rf)]
print(f'Umbral óptimo RF: {umbral_rf:.4f}')

y_pred_rf_youden = (y_prob_rf >= umbral_rf).astype(int)
print(f'Recall:    {recall_score(y_test, y_pred_rf_youden):.4f}')
print(f'Precision: {precision_score(y_test, y_pred_rf_youden):.4f}')
print(f'F1:        {f1_score(y_test, y_pred_rf_youden):.4f}')
print(confusion_matrix(y_test, y_pred_rf_youden))