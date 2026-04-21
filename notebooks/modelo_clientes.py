#Importación de librerías
import pandas as pd

ruta_archivo = "data/raw/Default_Clientes.csv"
datos = pd.read_csv(ruta_archivo, sep=";")
copia_datos = datos
copia_datos.head(10)
print(copia_datos['Default'].value_counts())

datos.info()

cols_categoricas = ["SEX", "EDUCATION", "MARRIAGE", "PAY_0", "PAY_2", "PAY_3", 
                    "PAY_4", "PAY_5", "PAY_6"]

for col in cols_categoricas:
    if col in copia_datos.columns:
        copia_datos[col] = copia_datos[col].astype('category')
    else:
        print(f"Advertencia: columna '{col}' no encontrada")

# Partición de los datos en conjunto de entrenamiento y de prueba
from sklearn.model_selection import train_test_split
# Se establece 80% de los datos para entrenamiento y 20% para prueba, con una semilla aleatoria de 123 para reproducibilidad.
X_train, X_test, y_train, y_test = train_test_split(copia_datos.drop('Default', axis=1), copia_datos['Default'], test_size=0.2, random_state=123)

# Dado que hay desbalance en la variable objetivo, se puede aplicar un muestreo para equilibrar las clases. 
# En este caso, se puede utilizar el método de sobremuestreo (oversampling) para aumentar la cantidad de muestras de la clase minoritaria (Default = 0).
from imblearn.over_sampling import RandomOverSampler


