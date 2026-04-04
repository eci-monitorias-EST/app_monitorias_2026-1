#!/usr/bin/env python3
"""
Sistema de asignación conservadora de nuevos puntos a clusters existentes.

Estrategia de 3 filtros estrictos:
1. HDBSCAN approximate_predict con strength >= 0.90
2. kNN consensus: al menos 4/5 vecinos del mismo cluster
3. Margen entre clusters: d1/d2 <= 0.80

No modifica clusters existentes, solo asigna nuevos puntos si cumplen
criterios muy estrictos. Si no cumplen, quedan como UNASSIGNED.
"""

import pickle
import numpy as np
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_distances
import pandas as pd
import hdbscan

# Configuración de filtros estrictos
CONFIG = {
    'strength_threshold': 0.90,      # Umbral de confianza HDBSCAN
    'knn_k': 5,                       # Número de vecinos a consultar
    'knn_consensus': 0.80,            # Al menos 4/5 vecinos del mismo cluster
    'margin_ratio': 0.80,             # d1/d2 <= 0.80 (margen claro)
    'use_medoid_radius': True,        # Validar con radio del cluster
    'radius_percentile': 90           # Percentil para radio del cluster
}


def cargar_modelo_congelado(ruta_pkl):
    """Carga el modelo HDBSCAN entrenado y los datos."""
    print(f"📂 Cargando modelo desde: {ruta_pkl}")
    with open(ruta_pkl, 'rb') as f:
        data = pickle.load(f)
    
    print(f"✅ Modelo cargado:")
    print(f"   - Registros: {len(data['df'])}")
    print(f"   - Clusters: {data['n_clusters']}")
    print(f"   - Outliers: {data['n_outliers']} ({data['outlier_percentage']:.2f}%)")
    
    return data


def calcular_medoids_y_radios(embeddings, labels, percentile=90):
    """
    Calcula el medoid y radio de cada cluster.
    
    Medoid: punto real del cluster más cercano al centroide.
    Radio: percentil de distancias internas al medoid.
    """
    clusters_unicos = [c for c in np.unique(labels) if c != -1]
    medoids = {}
    radios = {}
    
    for cluster_id in clusters_unicos:
        mask = labels == cluster_id
        cluster_points = embeddings[mask]
        
        # Calcular centroide
        centroid = cluster_points.mean(axis=0)
        
        # Encontrar medoid (punto más cercano al centroide)
        distances_to_centroid = cosine_distances(
            cluster_points, 
            centroid.reshape(1, -1)
        ).flatten()
        medoid_idx = np.argmin(distances_to_centroid)
        medoid = cluster_points[medoid_idx]
        
        # Calcular radio (percentil de distancias al medoid)
        distances_to_medoid = cosine_distances(
            cluster_points,
            medoid.reshape(1, -1)
        ).flatten()
        radio = np.percentile(distances_to_medoid, percentile)
        
        medoids[cluster_id] = medoid
        radios[cluster_id] = radio
    
    return medoids, radios


def asignar_punto_conservador(
    embedding_nuevo,
    clusterer,
    embeddings_train,
    labels_train,
    medoids,
    radios,
    knn_model,
    config
):
    """
    Asigna un nuevo punto usando estrategia conservadora de 3 filtros.
    
    Returns:
        tuple: (cluster_asignado, detalles_decision)
        cluster_asignado: int o -1 (UNASSIGNED)
        detalles_decision: dict con información de la decisión
    """
    detalles = {
        'filtro_1_strength': None,
        'filtro_2_knn_consensus': None,
        'filtro_3_margin': None,
        'filtro_4_radius': None,
        'decision': 'UNASSIGNED',
        'razon': []
    }
    
    # FILTRO 1: HDBSCAN approximate_predict
    try:
        labels_pred, strengths = hdbscan.approximate_predict(
            clusterer, 
            embedding_nuevo.reshape(1, -1)
        )
        cluster_propuesto = labels_pred[0]
        strength = strengths[0]
        
        detalles['filtro_1_strength'] = strength
        detalles['cluster_propuesto'] = cluster_propuesto
        
        if cluster_propuesto == -1:
            detalles['razon'].append('HDBSCAN propuso outlier')
            return -1, detalles
        
        if strength < config['strength_threshold']:
            detalles['razon'].append(
                f'Strength {strength:.3f} < {config["strength_threshold"]}'
            )
            return -1, detalles
            
    except Exception as e:
        detalles['razon'].append(f'Error en approximate_predict: {str(e)}')
        return -1, detalles
    
    # FILTRO 2: kNN consensus
    distances, indices = knn_model.kneighbors(
        embedding_nuevo.reshape(1, -1),
        n_neighbors=config['knn_k']
    )
    vecinos_labels = labels_train[indices[0]]
    
    # Contar cuántos vecinos pertenecen al cluster propuesto
    vecinos_mismo_cluster = np.sum(vecinos_labels == cluster_propuesto)
    consensus = vecinos_mismo_cluster / config['knn_k']
    
    detalles['filtro_2_knn_consensus'] = consensus
    detalles['vecinos_labels'] = vecinos_labels.tolist()
    
    if consensus < config['knn_consensus']:
        detalles['razon'].append(
            f'Consensus {consensus:.2f} < {config["knn_consensus"]} '
            f'({vecinos_mismo_cluster}/{config["knn_k"]} vecinos)'
        )
        return -1, detalles
    
    # FILTRO 3: Margen entre clusters
    # Calcular distancia a todos los medoids
    distancias_medoids = {}
    for cluster_id, medoid in medoids.items():
        dist = cosine_distances(
            embedding_nuevo.reshape(1, -1),
            medoid.reshape(1, -1)
        )[0, 0]
        distancias_medoids[cluster_id] = dist
    
    # Ordenar por distancia
    clusters_ordenados = sorted(distancias_medoids.items(), key=lambda x: x[1])
    
    if len(clusters_ordenados) < 2:
        # Solo hay un cluster, no podemos calcular margen
        detalles['filtro_3_margin'] = 1.0
    else:
        d1 = clusters_ordenados[0][1]  # Distancia al más cercano
        d2 = clusters_ordenados[1][1]  # Distancia al segundo más cercano
        
        if d2 == 0:
            margin_ratio = 0.0
        else:
            margin_ratio = d1 / d2
        
        detalles['filtro_3_margin'] = margin_ratio
        detalles['d1'] = d1
        detalles['d2'] = d2
        
        if margin_ratio > config['margin_ratio']:
            detalles['razon'].append(
                f'Margen {margin_ratio:.3f} > {config["margin_ratio"]} '
                f'(d1={d1:.3f}, d2={d2:.3f})'
            )
            return -1, detalles
    
    # FILTRO 4: Radio del cluster (opcional)
    if config['use_medoid_radius']:
        dist_al_medoid = distancias_medoids[cluster_propuesto]
        radio_permitido = radios[cluster_propuesto]
        
        detalles['filtro_4_radius'] = dist_al_medoid / radio_permitido
        detalles['dist_medoid'] = dist_al_medoid
        detalles['radio_cluster'] = radio_permitido
        
        if dist_al_medoid > radio_permitido:
            detalles['razon'].append(
                f'Distancia al medoid {dist_al_medoid:.3f} > '
                f'radio {radio_permitido:.3f}'
            )
            return -1, detalles
    
    # ✅ Pasó todos los filtros
    detalles['decision'] = 'ASSIGNED'
    detalles['razon'].append('Pasó todos los filtros')
    
    return cluster_propuesto, detalles


def main():
    print("=" * 80)
    print("ASIGNACIÓN CONSERVADORA DE NUEVOS PUNTOS")
    print("=" * 80)
    print()
    
    # Rutas
    base_dir = Path(__file__).parent.parent
    ruta_modelo = base_dir / 'data' / 'vectorial' / 'dispositivos_hdbscan_optimal.pkl'
    
    # Cargar modelo congelado
    data = cargar_modelo_congelado(ruta_modelo)
    
    embeddings_train = data['embeddings_umap']
    labels_train = data['labels']
    df_train = data['df']
    clusterer = data['clusterer']
    
    # Verificar que el modelo tiene prediction_data
    if not hasattr(clusterer, 'prediction_data_') or clusterer.prediction_data_ is None:
        print("⚠️  El modelo no fue entrenado con prediction_data=True")
        print("   No se puede usar approximate_predict")
        print("   Reentrenar con: HDBSCAN(..., prediction_data=True)")
        return
    
    print("\n📊 Calculando medoids y radios de clusters...")
    medoids, radios = calcular_medoids_y_radios(
        embeddings_train,
        labels_train,
        percentile=CONFIG['radius_percentile']
    )
    print(f"✅ Calculados {len(medoids)} medoids")
    
    # Crear modelo kNN para búsqueda de vecinos
    print("\n🔍 Construyendo índice kNN...")
    knn_model = NearestNeighbors(
        n_neighbors=CONFIG['knn_k'],
        metric='cosine',
        algorithm='brute'
    )
    knn_model.fit(embeddings_train)
    print("✅ Índice kNN construido")
    
    print("\n" + "=" * 80)
    print("CONFIGURACIÓN DE FILTROS")
    print("=" * 80)
    for key, value in CONFIG.items():
        print(f"  {key}: {value}")
    
    # DEMO: Simular asignación de puntos nuevos
    # Usaremos algunos outliers del conjunto original como "nuevos puntos"
    print("\n" + "=" * 80)
    print("DEMO: Intentar asignar outliers existentes")
    print("=" * 80)
    
    outliers_mask = labels_train == -1
    outliers_indices = np.where(outliers_mask)[0]
    
    if len(outliers_indices) == 0:
        print("⚠️  No hay outliers para probar")
        return
    
    # Probar con los primeros 10 outliers
    n_pruebas = min(10, len(outliers_indices))
    print(f"\nProbando con {n_pruebas} outliers...")
    print()
    
    resultados = []
    
    for i, idx in enumerate(outliers_indices[:n_pruebas], 1):
        embedding_nuevo = embeddings_train[idx]
        dispositivo = df_train.iloc[idx]['dispositivo_normalizado']
        
        cluster_asignado, detalles = asignar_punto_conservador(
            embedding_nuevo,
            clusterer,
            embeddings_train,
            labels_train,
            medoids,
            radios,
            knn_model,
            CONFIG
        )
        
        resultados.append({
            'idx': idx,
            'dispositivo': dispositivo,
            'cluster_asignado': cluster_asignado,
            'decision': detalles['decision'],
            'strength': detalles.get('filtro_1_strength'),
            'consensus': detalles.get('filtro_2_knn_consensus'),
            'margin': detalles.get('filtro_3_margin'),
            'radius_ratio': detalles.get('filtro_4_radius'),
            'razon': '; '.join(detalles['razon'])
        })
        
        print(f"[{i}/{n_pruebas}] {dispositivo[:60]}")
        print(f"  Cluster: {cluster_asignado} | Decisión: {detalles['decision']}")
        if detalles.get('filtro_1_strength'):
            print(f"  Strength: {detalles['filtro_1_strength']:.3f}")
        if detalles.get('filtro_2_knn_consensus'):
            print(f"  Consensus: {detalles['filtro_2_knn_consensus']:.2f}")
        if detalles.get('filtro_3_margin'):
            print(f"  Margin: {detalles['filtro_3_margin']:.3f}")
        print(f"  Razón: {detalles['razon'][0]}")
        print()
    
    # Resumen
    df_resultados = pd.DataFrame(resultados)
    n_asignados = (df_resultados['decision'] == 'ASSIGNED').sum()
    n_rechazados = (df_resultados['decision'] == 'UNASSIGNED').sum()
    
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Puntos probados: {n_pruebas}")
    print(f"Asignados: {n_asignados} ({n_asignados/n_pruebas*100:.1f}%)")
    print(f"Rechazados: {n_rechazados} ({n_rechazados/n_pruebas*100:.1f}%)")
    print()
    
    if n_asignados > 0:
        print("Puntos asignados:")
        for _, row in df_resultados[df_resultados['decision'] == 'ASSIGNED'].iterrows():
            print(f"  • {row['dispositivo'][:60]} → Cluster {row['cluster_asignado']}")
    
    # Guardar resultados
    ruta_salida = base_dir / 'reportes' / 'asignacion_conservadora_demo.csv'
    df_resultados.to_csv(ruta_salida, index=False)
    print(f"\n💾 Resultados guardados: {ruta_salida}")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETADA")
    print("=" * 80)
    print("\nEste script demuestra la asignación conservadora.")
    print("Para usar en producción:")
    print("  1. Cargar embeddings de nuevos dispositivos")
    print("  2. Llamar a asignar_punto_conservador() para cada uno")
    print("  3. Solo se asignan si pasan TODOS los filtros")
    print("  4. Los clusters existentes NO se modifican")


if __name__ == '__main__':
    main()
