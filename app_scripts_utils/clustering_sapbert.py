#!/usr/bin/env python3
"""
Clustering con SapBERT (modelo biomédico)
Genera embeddings con SapBERT y ejecuta clustering HDBSCAN óptimo.
"""
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import hdbscan
from sklearn.metrics import silhouette_score, davies_bouldin_score
from umap import UMAP
import time


def cargar_datos(archivo: str = '../reportes/dispositivos_hdbscan_optimal.csv'):
    """Carga datos limpios."""
    print(f"Cargando datos desde: {archivo}")
    
    datos = []
    with open(archivo, 'r', encoding='utf-8') as f:
        import csv
        reader = csv.DictReader(f)
        for row in reader:
            datos.append({
                'auditoria_id': row['auditoria_id'],
                'nombre_original': row['nombre_original'],
                'nombre_normalizado': row['nombre_normalizado']
            })
    
    print(f"✅ Cargados {len(datos)} registros")
    return datos


def generar_embeddings_sapbert(textos: List[str]) -> np.ndarray:
    """Genera embeddings con SapBERT."""
    print(f"\n{'='*80}")
    print("GENERACIÓN DE EMBEDDINGS CON SAPBERT")
    print("="*80)
    print("Modelo: cambridgeltl/SapBERT-from-PubMedBERT-fulltext")
    print("Especializado en: Terminología biomédica y conceptos médicos")
    
    print("\nCargando modelo SapBERT...")
    start_time = time.time()
    
    modelo = SentenceTransformer('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')
    load_time = time.time() - start_time
    
    print(f"✅ Modelo cargado en {load_time:.2f}s")
    print(f"   Dimensiones: {modelo.get_sentence_embedding_dimension()}")
    
    print(f"\nGenerando embeddings para {len(textos)} dispositivos...")
    start_embed = time.time()
    embeddings = modelo.encode(textos, show_progress_bar=True, batch_size=32)
    embed_time = time.time() - start_embed
    
    print(f"✅ Embeddings generados en {embed_time:.2f}s")
    print(f"   Shape: {embeddings.shape}")
    
    return embeddings


def reducir_con_umap(embeddings: np.ndarray, n_components: int = 50) -> np.ndarray:
    """Reduce dimensionalidad con UMAP."""
    print(f"\n{'='*80}")
    print("REDUCCIÓN DIMENSIONAL CON UMAP")
    print("="*80)
    print(f"Reduciendo de {embeddings.shape[1]} a {n_components} dimensiones...")
    
    reducer = UMAP(
        n_components=n_components,
        n_neighbors=30,
        min_dist=0.0,
        metric='cosine',
        random_state=42
    )
    
    embeddings_reducidos = reducer.fit_transform(embeddings)
    
    print(f"✅ Reducción completada")
    print(f"   Nueva shape: {embeddings_reducidos.shape}")
    
    return embeddings_reducidos


def clustering_hdbscan(embeddings: np.ndarray) -> Tuple[np.ndarray, Dict]:
    """Ejecuta HDBSCAN con configuración óptima."""
    print(f"\n{'='*80}")
    print("CLUSTERING HDBSCAN")
    print("="*80)
    print("Configuración óptima:")
    print("  min_cluster_size: 7")
    print("  min_samples: 5")
    print("  metric: euclidean")
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=7,
        min_samples=5,
        metric='euclidean',
        cluster_selection_method='eom'
    )
    
    labels = clusterer.fit_predict(embeddings)
    
    # Calcular estadísticas
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    pct_noise = (n_noise / len(labels) * 100)
    
    cluster_sizes = {}
    for label in labels:
        if label != -1:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
    max_cluster_size = max(cluster_sizes.values()) if cluster_sizes else 0
    
    print(f"\n✅ Clustering completado")
    print(f"   Clusters: {n_clusters}")
    print(f"   Outliers: {n_noise} ({pct_noise:.2f}%)")
    print(f"   Cluster más grande: {max_cluster_size}")
    
    # Métricas de calidad
    silhouette = None
    davies_bouldin = None
    
    if n_clusters > 1:
        mask = labels != -1
        if mask.sum() > n_clusters:
            try:
                silhouette = silhouette_score(embeddings[mask], labels[mask])
                davies_bouldin = davies_bouldin_score(embeddings[mask], labels[mask])
                
                print(f"\nMétricas de calidad:")
                print(f"   Silhouette: {silhouette:.4f}")
                print(f"   Davies-Bouldin: {davies_bouldin:.4f}")
            except:
                pass
    
    estadisticas = {
        'n_clusters': n_clusters,
        'n_noise': n_noise,
        'pct_noise': pct_noise,
        'max_cluster_size': max_cluster_size,
        'silhouette': silhouette,
        'davies_bouldin': davies_bouldin
    }
    
    return labels, estadisticas


def analizar_clusters(labels: np.ndarray, datos: List[Dict]):
    """Analiza y muestra clusters."""
    print(f"\n{'='*80}")
    print("ANÁLISIS DE CLUSTERS")
    print("="*80)
    
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
    
    cluster_counts = {}
    for label in labels:
        if label != -1:
            cluster_counts[label] = cluster_counts.get(label, 0) + 1
    
    if cluster_counts:
        counts = list(cluster_counts.values())
        
        print(f"\nTotal de clusters: {n_clusters}")
        print(f"Tamaño promedio: {np.mean(counts):.2f}")
        print(f"Tamaño mediano: {np.median(counts):.0f}")
        print(f"Cluster más pequeño: {min(counts)}")
        print(f"Cluster más grande: {max(counts)}")
        
        print(f"\nDistribución de tamaños:")
        print(f"  1-5 elementos: {sum(1 for c in counts if c <= 5)}")
        print(f"  6-10 elementos: {sum(1 for c in counts if 6 <= c <= 10)}")
        print(f"  11-20 elementos: {sum(1 for c in counts if 11 <= c <= 20)}")
        print(f"  21-50 elementos: {sum(1 for c in counts if 21 <= c <= 50)}")
        print(f"  >50 elementos: {sum(1 for c in counts if c > 50)}")
        
        # Top 10 clusters
        print(f"\n{'='*80}")
        print("TOP 10 CLUSTERS MÁS GRANDES")
        print("="*80)
        
        sorted_clusters = sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)
        
        for i, (cluster_id, size) in enumerate(sorted_clusters[:10], 1):
            indices = [j for j, label in enumerate(labels) if label == cluster_id]
            ejemplos = [datos[j]['nombre_original'] for j in indices[:3]]
            
            print(f"\nCluster {cluster_id}: {size} dispositivos")
            print(f"  Ejemplos:")
            for ej in ejemplos:
                print(f"    - {ej[:70]}")


def guardar_resultados(
    datos: List[Dict],
    embeddings: np.ndarray,
    labels: np.ndarray,
    estadisticas: Dict,
    archivo_csv: str = '../reportes/dispositivos_sapbert.csv',
    archivo_pkl: str = '../data/vectorial/dispositivos_sapbert.pkl'
):
    """Guarda resultados."""
    print(f"\n{'='*80}")
    print("GUARDANDO RESULTADOS")
    print("="*80)
    
    datos_con_cluster = []
    for i, d in enumerate(datos):
        datos_con_cluster.append({
            'auditoria_id': d['auditoria_id'],
            'nombre_original': d['nombre_original'],
            'nombre_normalizado': d['nombre_normalizado'],
            'cluster_id': int(labels[i]),
            'es_ruido': labels[i] == -1,
            'embedding': embeddings[i]
        })
    
    # Guardar CSV
    df = pd.DataFrame([
        {
            'auditoria_id': d['auditoria_id'],
            'nombre_original': d['nombre_original'],
            'nombre_normalizado': d['nombre_normalizado'],
            'cluster_id': d['cluster_id'],
            'es_ruido': d['es_ruido']
        }
        for d in datos_con_cluster
    ])
    df.to_csv(archivo_csv, index=False, encoding='utf-8')
    print(f"✅ CSV guardado: {archivo_csv}")
    
    # Guardar pickle
    resultado = {
        'datos': datos_con_cluster,
        'estadisticas': estadisticas
    }
    
    with open(archivo_pkl, 'wb') as f:
        pickle.dump(resultado, f)
    
    print(f"✅ Pickle guardado: {archivo_pkl}")


if __name__ == "__main__":
    print("="*80)
    print("CLUSTERING CON SAPBERT (MODELO BIOMÉDICO)")
    print("="*80)
    print("\nSapBERT está entrenado específicamente para:")
    print("  ✓ Terminología biomédica (UMLS)")
    print("  ✓ Nombres de conceptos médicos")
    print("  ✓ Normalización de entidades clínicas")
    print()
    
    # 1. Cargar datos
    datos = cargar_datos()
    
    # 2. Generar embeddings con SapBERT
    textos = [d['nombre_normalizado'] for d in datos]
    embeddings = generar_embeddings_sapbert(textos)
    
    # 3. Reducir dimensionalidad
    embeddings_reducidos = reducir_con_umap(embeddings, n_components=50)
    
    # 4. Clustering
    labels, estadisticas = clustering_hdbscan(embeddings_reducidos)
    
    # 5. Analizar clusters
    analizar_clusters(labels, datos)
    
    # 6. Guardar resultados
    guardar_resultados(datos, embeddings, labels, estadisticas)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivos generados:")
    print("  - ../reportes/dispositivos_sapbert.csv")
    print("  - ../data/vectorial/dispositivos_sapbert.pkl")
    print("\nPróximos pasos:")
    print("  1. Visualizar en 3D:")
    print("     python visualizar_sapbert_3d.py")
