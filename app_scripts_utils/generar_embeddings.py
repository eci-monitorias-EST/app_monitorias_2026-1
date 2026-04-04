#!/usr/bin/env python3
"""
Generación de Embeddings para Dispositivos Médicos
Usa sentence-transformers (Facebook) para generar embeddings semánticos.
El modelo incluye su propio tokenizador.
"""
import csv
import numpy as np
import pickle
from pathlib import Path


def cargar_datos(archivo: str = '../data/processed/dispositivos_medicos_normalizado.csv'):
    """Carga datos normalizados desde CSV."""
    datos = []
    
    print(f"Cargando datos desde: {archivo}")
    
    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            datos.append({
                'auditoria_id': row['auditoria_id'],
                'nombre_original': row['nombre_original'],
                'nombre_normalizado': row['nombre_normalizado']
            })
    
    print(f"✅ Cargados {len(datos)} registros")
    return datos


def generar_embeddings(
    datos,
    modelo_nombre: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    batch_size: int = 32
):
    """
    Genera embeddings usando sentence-transformers de Facebook.
    El modelo incluye tokenizador automático.
    
    Args:
        datos: Lista de diccionarios con datos
        modelo_nombre: Nombre del modelo de sentence-transformers
        batch_size: Tamaño de batch para procesamiento
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("❌ Error: sentence-transformers no está instalado")
        print("Instalar con: pip install sentence-transformers")
        return None
    
    print(f"\n{'='*80}")
    print("GENERACIÓN DE EMBEDDINGS")
    print("="*80)
    print(f"Modelo: {modelo_nombre}")
    print(f"Batch size: {batch_size}")
    
    # Cargar modelo (incluye tokenizador automático)
    print("\nCargando modelo de sentence-transformers...")
    modelo = SentenceTransformer(modelo_nombre)
    
    print(f"✅ Modelo cargado")
    print(f"   Dimensión de embeddings: {modelo.get_sentence_embedding_dimension()}")
    
    # Extraer textos normalizados
    textos = [d['nombre_normalizado'] for d in datos]
    
    print(f"\nGenerando embeddings para {len(textos)} dispositivos...")
    print("(El modelo tokeniza automáticamente)")
    
    # Generar embeddings
    # El modelo maneja internamente:
    # 1. Tokenización
    # 2. Conversión a IDs
    # 3. Generación de embeddings
    embeddings = modelo.encode(
        textos,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    print(f"\n✅ Embeddings generados")
    print(f"   Shape: {embeddings.shape}")
    print(f"   Dtype: {embeddings.dtype}")
    
    return embeddings, modelo


def guardar_embeddings(datos, embeddings, archivo_salida: str = '../data/vectorial/dispositivos_embeddings.pkl'):
    """Guarda datos y embeddings en formato pickle."""
    
    # Preparar datos para guardar
    datos_con_embeddings = []
    for i, d in enumerate(datos):
        datos_con_embeddings.append({
            'auditoria_id': d['auditoria_id'],
            'nombre_original': d['nombre_original'],
            'nombre_normalizado': d['nombre_normalizado'],
            'embedding': embeddings[i]
        })
    
    # Guardar en pickle
    with open(archivo_salida, 'wb') as f:
        pickle.dump(datos_con_embeddings, f)
    
    print(f"\n✅ Embeddings guardados en: {archivo_salida}")
    print(f"   Tamaño del archivo: {Path(archivo_salida).stat().st_size / 1024 / 1024:.2f} MB")


def guardar_embeddings_csv(datos, embeddings, archivo_salida: str = '../data/vectorial/dispositivos_embeddings.csv'):
    """Guarda embeddings en formato CSV (para inspección)."""
    
    print(f"\nGuardando embeddings en CSV: {archivo_salida}")
    
    with open(archivo_salida, 'w', newline='', encoding='utf-8') as f:
        # Crear header con dimensiones de embedding
        n_dims = embeddings.shape[1]
        header = ['auditoria_id', 'nombre_original', 'nombre_normalizado']
        header.extend([f'emb_{i}' for i in range(n_dims)])
        
        writer = csv.writer(f)
        writer.writerow(header)
        
        for i, d in enumerate(datos):
            row = [
                d['auditoria_id'],
                d['nombre_original'],
                d['nombre_normalizado']
            ]
            row.extend(embeddings[i].tolist())
            writer.writerow(row)
    
    print(f"✅ CSV guardado: {archivo_salida}")


def analizar_embeddings(embeddings):
    """Analiza estadísticas de los embeddings generados."""
    print(f"\n{'='*80}")
    print("ANÁLISIS DE EMBEDDINGS")
    print("="*80)
    
    print(f"\nShape: {embeddings.shape}")
    print(f"  - Número de dispositivos: {embeddings.shape[0]}")
    print(f"  - Dimensión de embeddings: {embeddings.shape[1]}")
    
    print(f"\nEstadísticas:")
    print(f"  - Media: {embeddings.mean():.6f}")
    print(f"  - Desviación estándar: {embeddings.std():.6f}")
    print(f"  - Mínimo: {embeddings.min():.6f}")
    print(f"  - Máximo: {embeddings.max():.6f}")
    
    # Calcular normas L2
    normas = np.linalg.norm(embeddings, axis=1)
    print(f"\nNormas L2:")
    print(f"  - Media: {normas.mean():.6f}")
    print(f"  - Min: {normas.min():.6f}")
    print(f"  - Max: {normas.max():.6f}")


if __name__ == "__main__":
    print("="*80)
    print("GENERACIÓN DE EMBEDDINGS - DISPOSITIVOS MÉDICOS")
    print("="*80)
    print("\nUsando sentence-transformers de Facebook")
    print("(Incluye tokenizador automático)\n")
    
    # 1. Cargar datos normalizados
    datos = cargar_datos()
    
    # 2. Generar embeddings
    resultado = generar_embeddings(datos)
    
    if resultado is None:
        print("\n❌ No se pudieron generar embeddings")
        print("Instala sentence-transformers: pip install sentence-transformers")
        exit(1)
    
    embeddings, modelo = resultado
    
    # 3. Analizar embeddings
    analizar_embeddings(embeddings)
    
    # 4. Guardar embeddings
    guardar_embeddings(datos, embeddings)
    guardar_embeddings_csv(datos, embeddings)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivos generados:")
    print("  - dispositivos_embeddings.pkl (formato pickle, para clustering)")
    print("  - dispositivos_embeddings.csv (formato CSV, para inspección)")
