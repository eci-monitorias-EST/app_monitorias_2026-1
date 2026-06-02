# imprtacion de librerias 
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.metrics import roc_curve, roc_auc_score


# carga de datos 
## categorico
german_data_path = r"C:\Users\mipip\Downloads\app_monitorias_2026-1\app_monitorias_2026-1\data\german_credit\statlog+german+credit+data\german.data"
df_german = pd.read_csv(german_data_path, sep=' ', header=None)

## numerico

german_numeric_path = r"C:\Users\mipip\Downloads\app_monitorias_2026-1\app_monitorias_2026-1\data\german_credit\statlog+german+credit+data\german.data-numeric"
df_german_numeric = pd.read_csv(german_numeric_path, sep=r'\s+', header=None)


# Definir nombres de columnas según documentación
column_names = [
    'status_checking_account', 'duration_months', 'credit_history',
    'purpose', 'credit_amount', 'savings_account', 'employment_since',
    'installment_rate', 'personal_status_sex', 'other_debtors',
    'present_residence', 'property', 'age_years', 'other_installment_plans',
    'housing', 'existing_credits', 'job', 'liable_people', 'telephone',
    'foreign_worker', 'target'
]

# Asignar nombres a las columnas
df_german.columns = column_names[:len(df_german.columns)]

# Para el dataset numérico (24 columnas)
numeric_names = column_names.copy()
extra_columns = [f'binarized_{i}' for i in range(1, 5)]
df_german_numeric.columns = numeric_names[:20] + extra_columns + ['target']



#3 tornar variable objetivo como 0y1
df_german['target'] = df_german['target'].map({1: 0, 2: 1})
df_german_numeric['target'] = df_german_numeric['target'].map({1: 0, 2: 1})

# reduccion de clases de la variable credit history
# como se reaaliza esta agrupacion en el dataset numerico se tiene que el cambio 
# reqalizadfo por la funcion significa lo siguiente para las categorias de la variable:
# A30,A31,A32/"PAGADO","PAGADO BANCOS", "AL DIA"/ 1,2,3 => "good"/ 0
# A33/"RETRASOS"/4 => "BAD"/ 1
# A34/"CUENTA CRITICA"/5 => "CRITICO"/ 2

def agrupar_credit_history(x):
    if x in [1, 2, 3]:
        return 0
    elif x == 4:
        return 1
    elif x == 5:
        return 2
    else:
        return 'unknown'
    
df_german_numeric['credit_history_grouped'] = df_german_numeric['credit_history'].apply(agrupar_credit_history)


# reduccion de clases para la variable employment_since
# como se realiza sobre el dataset numerico, esto es el cambio que realiza la funcion para las categorias
# A71 / "DESEMPLEADO"/ 1 => 
# A72 ,A73 / <1 AÑO, 1-4 AÑOS / 2,3 =>
# A74 ,A75 / 4-7 AÑOS, >7 AÑOS / 4,5 =>

def agrupar_empleo(x):
    if x == 1:
        return 0   
    elif x in [2, 3]:
        return 1   
    else:
        return 2  
    
df_german_numeric['employment_agroup'] = df_german_numeric['employment_since'].apply(agrupar_empleo)
##=================================================================
##seleccion de variables 
##=================================================================

numericas = [
    'duration_months',
    'credit_amount',
    'installment_rate',
    'existing_credits'
]

categoricas = [
    'status_checking_account',
    'credit_history_grouped',
    'savings_account',
    'other_debtors',
    'property',
    'other_installment_plans',
    'housing',
    'job'
]

Ordinales = [
    'employment_agroup'
] 

features = numericas + categoricas + Ordinales

X = df_german_numeric[features]
y = df_german_numeric['target']

# generacion de dummies para las variables categoricas del modelo
X = pd.get_dummies(X, columns=categoricas, drop_first=True)

##=================================================================
## division en entrenamiento y test
##=================================================================
# proporcion actual de datasets de entrenamiento y prueba es de 80%-20%
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

X_train = X_train.copy()
X_test = X_test.copy()

bool_cols = X_train.select_dtypes(include='bool').columns

X_train[bool_cols] = X_train[bool_cols].astype(int)
X_test[bool_cols] = X_test[bool_cols].astype(int)
##=================================================================
## balanceo de clases por pesos
##=================================================================

peso_cl_buenos = 1
peso_cl_malos = sum(y_train == 0) / sum(y_train == 1)


##==================================================================
## modelo logiastico 
##==================================================================

model = LogisticRegression(
    class_weight={0: peso_cl_buenos, 1: peso_cl_malos},
    max_iter=1000
)

model.fit(X_train, y_train)


##===================================================================
## verificacion de supuestos 
##===================================================================

##=====#####=====#####=====###
## multicolinealidad
##=====#####=====#####=====###

X_vif = X_train.copy()
X_vif = X_vif.astype(float)

#vif
vif_data = pd.DataFrame()
vif_data["variable"] = X_vif.columns
vif_data["VIF"] = [variance_inflation_factor(X_vif.values, i) for i in range(X_vif.shape[1])]

vif_data = vif_data.sort_values(by="VIF", ascending=False)
print(vif_data.head(20))


##=====#####=====#####=====###
## puntos influyentes
##=====#####=====#####=====###

X_sm = sm.add_constant(X_train)

model_sm = sm.Logit(y_train, X_sm).fit()

# medidas de influencia
influence = model_sm.get_influence()

# leverage
leverage = influence.hat_matrix_diag

# distancia de cook
cooks_d = influence.cooks_distance[0]

# residuos estudentizados
standard_residuals = influence.resid_studentized

# dataframe resumen
influence_df = pd.DataFrame({
    'fila_original': X_train.index,
    'leverage': leverage,
    'cooks_distance': cooks_d,
    'standard_residuals': standard_residuals
})

# cantidad de datos y variables
n = X_sm.shape[0]
p = X_sm.shape[1]

# umbrales
cook_threshold = 4 / n
leverage_threshold = 2 * p / n
residual_threshold = 2

print(f"Umbral Cook's Distance: {cook_threshold:.4f}")
print(f"Umbral Leverage: {leverage_threshold:.4f}")
print(f"Umbral residuos estudentizados: ±{residual_threshold}")

# identificar criterios
influence_df['alto_cook'] = influence_df['cooks_distance'] > cook_threshold
influence_df['alto_leverage'] = influence_df['leverage'] > leverage_threshold
influence_df['alto_residuo'] = abs(influence_df['standard_residuals']) > residual_threshold

# observacion influyente si cumple al menos un criterio
influence_df['punto_influyente'] = (
    influence_df['alto_cook'] |
    influence_df['alto_leverage'] |
    influence_df['alto_residuo']
)

# filtrar puntos influyentes
puntos_influyentes = influence_df[influence_df['punto_influyente']]

# mostrar cantidad
print(f"\nCantidad de puntos influyentes detectados: {len(puntos_influyentes)}")

# mostrar filas
print("\nFilas potencialmente influyentes:")
print(
    puntos_influyentes[
        [
            'fila_original',
            'cooks_distance',
            'leverage',
            'standard_residuals',
            'alto_cook',
            'alto_leverage',
            'alto_residuo'
        ]
    ].sort_values(by='cooks_distance', ascending=False)
)

# clasificacion de severidad
influence_df['severo'] = (
    (influence_df['cooks_distance'] > 1) |
    (abs(influence_df['standard_residuals']) > 3) |
    (influence_df['leverage'] > 0.5)
)

# puntos severos
puntos_severos = influence_df[influence_df['severo']]

print(f"\nCantidad de puntos severamente influyentes: {len(puntos_severos)}")

print(
    puntos_severos[
        [
            'fila_original',
            'cooks_distance',
            'leverage',
            'standard_residuals'
        ]
    ].sort_values(by='cooks_distance', ascending=False)
)

# e encontro la cantidad final de 26 puntos influyentes lo cual nos indica que puede existir un sobre ajuste en torno 
# a estos puntos 

#se tienen los casos criticos a tener encuenta
filas_problematicas = [163, 536, 846]
print(X.loc[filas_problematicas])

#omprobacion de separacion perfecta, prediccion perfecta
print(y.loc[[163,536,846]])

print(model.predict_proba(X.loc[[163,536,846]]))

# no se evidencia una interpretabilidad o separacion perfecta en las observaciones, por lo cual procederemos con los
# puntos influyentes y el modelo ademas del resto de sus medidas permanece estable por lo cual no se evidencian fallos
# en el modleo por sus supuestos

##===================================================================
## prediccion
##===================================================================

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:,1]

##=====####=====####=====##
# matriz de confusion 
##=====####=====####=====##
print(confusion_matrix(y_test, y_pred))


print(classification_report(y_test, y_pred))
##=====####=====####=====##
# curva de rocc y auc
##=====####=====####=====##
fpr, tpr, thresholds = roc_curve(y_test, y_prob)
auc = roc_auc_score(y_test, y_prob)

print(f"AUC: {auc:.4f}")

plt.figure(figsize=(8,6))
plt.plot(fpr, tpr, label=f"AUC = {auc:.4f}")
plt.plot([0,1], [0,1], linestyle='--')
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("Curva ROC")
plt.legend()
plt.show()

# por lo visto en la matriz de confusion se tiene un buen modelo que estima bien aon un auc aceptable de 0.71, pero se 
# pretende reducir el riesgo de deteccion de los falsosnegativos(clientes malos detectados como buenos), por lo cual se quiere 
# hallar el umnral optimo para aumnetar el el recall y asi disminuir los falsos negativos

# Se empleara el  indice de youden para esta labor

# especificidad + sensibilidad - 1, donde sensibilidad = recall, especificidad = tnr

# calcular indice de youden
youden_index = tpr - fpr

# posicion del mejor threshold
optimal_idx = youden_index.argmax()

# threshold optimo
optimal_threshold = thresholds[optimal_idx]

print(f"\nThreshold óptimo: {optimal_threshold:.4f}")

# predicciones con threshold optimo
y_pred_optimal = (y_prob >= optimal_threshold).astype(int)

# nueva matriz de confusion
print("\nMatriz de confusión con threshold óptimo:")
print(confusion_matrix(y_test, y_pred_optimal))

# nuevo reporte
print("\nReporte de clasificación:")
print(classification_report(y_test, y_pred_optimal))

# se tiene que al emplear el indice de youden se redujeron los falsos negativos, pero a su vez parece ser que se 
# vio afectada la capacidad predictoria en los verdaderos positivos

"""
###==================================================================
## deteccion de variables significativas
##==================================================================

X_sm = sm.add_constant(X_train)

model_sm = sm.Logit(y_train, X_sm).fit()

print(model_sm.summary()) # equivalente asummary en r
"""


#####========================#####========================#####========================
##seccion de pruebas
#####========================#####========================#####========================