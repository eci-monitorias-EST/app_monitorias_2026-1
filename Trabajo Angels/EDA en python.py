import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ==============================================================================
# 1. CARGA DE DATOS
# ==============================================================================
ruta_archivo = "C:/Users/norba/OneDrive/NUESTRO HOGAR/1. ANGEL SANTIAGO/Proyecto Banco/default of credit card clients.csv"
df = pd.read_csv(ruta_archivo, sep=";", skiprows=1)

print("\n--- Estructura inicial del Dataset ---")
print(df.info())
print("\n", df.describe())

# ==============================================================================
# 2. LIMPIEZA E IMPUTACIÓN
# ==============================================================================
cols_numericas = df.select_dtypes(include=[np.number]).columns
cols_texto = df.select_dtypes(include=['object']).columns

# Imputación: mediana para numéricas, moda para categóricas
df[cols_numericas] = df[cols_numericas].fillna(df[cols_numericas].median())

if not cols_texto.empty:
    for col in cols_texto:
        df[col] = df[col].fillna(df[col].mode()[0])

# Renombrar la variable objetivo
df.rename(columns={'default payment next month': 'DEFAULT'}, inplace=True)

# Convertir variables que conceptualmente son categóricas al tipo 'category'
cols_categoricas = ["SEX", "EDUCATION", "MARRIAGE", "PAY_0", "PAY_2", "PAY_3", 
                    "PAY_4", "PAY_5", "PAY_6", "DEFAULT"]

for col in cols_categoricas:
    df[col] = df[col].astype('category')

# ==============================================================================
# 3. ESTADÍSTICAS DESCRIPTIVAS POST-LIMPIEZA
# ==============================================================================
print("\n--- Resumen de Datos Limpios ---")
print(df.describe(include='all'))

# ==============================================================================
# 4. VISUALIZACIÓN DE DATOS
# ==============================================================================
sns.set_theme(style="whitegrid")

# a) Distribución de la variable objetivo (Default)
plt.figure(figsize=(6, 4))
sns.countplot(data=df, x='DEFAULT', palette='Set2', edgecolor='black')
plt.title('Distribución de Clientes en Default\n(0 = No, 1 = Sí)')
plt.ylabel('Cantidad de Clientes')
plt.show()

# b) Histograma del límite de crédito (LIMIT_BAL)
plt.figure(figsize=(8, 5))
sns.histplot(df['LIMIT_BAL'], bins=30, color='steelblue', kde=False)
plt.title('Distribución del Límite de Crédito')
plt.xlabel('Límite de Crédito (NT$)')
plt.ylabel('Frecuencia')
plt.show()

# c) Boxplot de Límite de crédito vs Default
plt.figure(figsize=(8, 5))
sns.boxplot(data=df, x='DEFAULT', y='LIMIT_BAL', palette='Set2')
plt.title('Límite de Crédito según Estado de Default')
plt.show()

# d) Relación entre Edad e Impagos (Proporción)
plt.figure(figsize=(10, 5))
sns.histplot(data=df, x='AGE', hue='DEFAULT', multiple='fill', bins=20, palette='Set2')
plt.title('Proporción de Default por Edad')
plt.ylabel('Proporción')
plt.show()

# ==============================================================================
# 5. PRUEBAS DE NORMALIDAD Y CORRELACIÓN (SIN SCIPY)
# ==============================================================================
df_numerico = df.select_dtypes(include=[np.number]).drop(columns=['ID'], errors='ignore')

print("\n--- Evaluación de Normalidad (Asimetría y Curtosis) ---")
# Una asimetría entre -2 y 2, y una curtosis entre -2 y 2 suelen ser aceptables 
# para asumir cierta normalidad en muestras grandes.
for col in df_numerico.columns:
    asimetria = df_numerico[col].skew()
    curtosis = df_numerico[col].kurtosis()
    
    es_aceptable = (abs(asimetria) < 2) and (abs(curtosis) < 2)
    print(f"Variable: {col} - ¿Aceptable? {'Sí' if es_aceptable else 'No'} (Asimetría: {asimetria:.2f}, Curtosis: {curtosis:.2f})")

print("\n--- Generando Matriz de Correlación ---")
# Correlación de Spearman calculada directamente con Pandas
matriz_cor = df_numerico.corr(method='spearman')

plt.figure(figsize=(14, 10))
sns.heatmap(matriz_cor, annot=True, fmt=".2f", cmap='coolwarm', 
            square=True, linewidths=.5, cbar_kws={"shrink": .75},
            annot_kws={"size": 8})
plt.title('Matriz de Correlación (Spearman)')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()