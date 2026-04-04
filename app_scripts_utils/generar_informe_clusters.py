#!/usr/bin/env python3
"""
Genera informe CSV completo con información detallada de clusters.

Incluye:
- Información por cluster (tamaño, ejemplos, estadísticas)
- Información por dispositivo (cluster, cluster más cercano, distancias)
- Resumen ejecutivo
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics.pairwise import euclidean_distances
from umap import UMAP


def cargar_datos_sapbert():
    """Carga los datos de clustering SapBERT."""
    base_dir = Path(__file__).parent.parent
    ruta_pkl = base_dir / 'data' / 'vectorial' / 'dispositivos_sapbert.pkl'
    
    print(f"📂 Cargando datos SapBERT desde: {ruta_pkl}")
    with open(ruta_pkl, 'rb') as f:
        data = pickle.load(f)
    
    datos = data['datos']
    stats = data['estadisticas']
    
    embeddings = np.array([d['embedding'] for d in datos])
    labels = np.array([d['cluster_id'] for d in datos])
    
    df = pd.DataFrame([
        {
            'auditoria_id': d['auditoria_id'],
            'dispositivo_original': d['nombre_original'],
            'dispositivo_normalizado': d['nombre_normalizado'],
            'cluster_id': labels[i],
            'es_outlier': labels[i] == -1
        }
        for i, d in enumerate(datos)
    ])
    
    print(f"✅ Datos cargados: {len(df)} dispositivos")
    print(f"   Clusters: {stats['n_clusters']}")
    print(f"   Outliers: {stats['n_noise']}")
    
    return embeddings, labels, df, stats


def reducir_a_3d(embeddings):
    """Reduce embeddings a 3D usando UMAP."""
    print("\n🔄 Reduciendo a 3D con UMAP...")
    
    umap_50d = UMAP(
        n_components=50,
        n_neighbors=30,
        min_dist=0.0,
        metric='cosine',
        random_state=42
    )
    embeddings_50d = umap_50d.fit_transform(embeddings)
    
    umap_3d = UMAP(
        n_components=3,
        n_neighbors=30,
        min_dist=0.1,
        metric='euclidean',
        random_state=42
    )
    coords_3d = umap_3d.fit_transform(embeddings_50d)
    
    print(f"✅ Reducción completada: {embeddings.shape} → {coords_3d.shape}")
    
    return coords_3d


def calcular_centroides(coords_3d, labels):
    """Calcula el centroide de cada cluster."""
    clusters_unicos = [c for c in np.unique(labels) if c != -1]
    centroides = {}
    
    for cluster_id in clusters_unicos:
        mask = labels == cluster_id
        cluster_points = coords_3d[mask]
        centroide = cluster_points.mean(axis=0)
        centroides[cluster_id] = centroide
    
    return centroides


def calcular_estadisticas_cluster(coords_3d, labels, cluster_id, centroide):
    """Calcula estadísticas de un cluster."""
    mask = labels == cluster_id
    cluster_points = coords_3d[mask]
    
    # Distancias al centroide
    distancias = euclidean_distances(
        cluster_points,
        centroide.reshape(1, -1)
    ).flatten()
    
    return {
        'tamaño': len(cluster_points),
        'dist_media': distancias.mean(),
        'dist_std': distancias.std(),
        'dist_min': distancias.min(),
        'dist_max': distancias.max(),
        'dist_p50': np.percentile(distancias, 50),
        'dist_p90': np.percentile(distancias, 90),
        'dist_p95': np.percentile(distancias, 95)
    }


def encontrar_cluster_mas_cercano(punto, centroides):
    """Encuentra el cluster más cercano al punto."""
    min_distancia = float('inf')
    cluster_mas_cercano = None
    
    for cluster_id, centroide in centroides.items():
        distancia = np.linalg.norm(punto - centroide)
        
        if distancia < min_distancia:
            min_distancia = distancia
            cluster_mas_cercano = cluster_id
    
    return cluster_mas_cercano, min_distancia


def generar_informe_por_cluster(coords_3d, labels, df, centroides):
    """Genera CSV con información por cluster."""
    print("\n📊 Generando informe por cluster...")
    
    clusters_unicos = sorted([c for c in np.unique(labels) if c != -1])
    
    informe_clusters = []
    
    for cluster_id in clusters_unicos:
        mask = labels == cluster_id
        dispositivos_cluster = df[mask]
        
        # Estadísticas del cluster
        centroide = centroides[cluster_id]
        stats = calcular_estadisticas_cluster(coords_3d, labels, cluster_id, centroide)
        
        # Ejemplos de dispositivos (top 5 más frecuentes)
        top_dispositivos = (
            dispositivos_cluster['dispositivo_normalizado']
            .value_counts()
            .head(5)
        )
        
        ejemplos = '; '.join([
            f"{disp} ({count})"
            for disp, count in top_dispositivos.items()
        ])
        
        # Auditorías únicas
        auditorias_unicas = dispositivos_cluster['auditoria_id'].nunique()
        
        informe_clusters.append({
            'cluster_id': cluster_id,
            'tamaño': stats['tamaño'],
            'auditorias_unicas': auditorias_unicas,
            'dist_media_centroide': round(stats['dist_media'], 3),
            'dist_std_centroide': round(stats['dist_std'], 3),
            'dist_min_centroide': round(stats['dist_min'], 3),
            'dist_max_centroide': round(stats['dist_max'], 3),
            'dist_p50_centroide': round(stats['dist_p50'], 3),
            'dist_p90_centroide': round(stats['dist_p90'], 3),
            'dist_p95_centroide': round(stats['dist_p95'], 3),
            'centroide_x': round(centroide[0], 3),
            'centroide_y': round(centroide[1], 3),
            'centroide_z': round(centroide[2], 3),
            'ejemplos_dispositivos': ejemplos
        })
    
    df_clusters = pd.DataFrame(informe_clusters)
    df_clusters = df_clusters.sort_values('tamaño', ascending=False)
    
    return df_clusters


def generar_informe_por_dispositivo(coords_3d, labels, df, centroides):
    """Genera CSV con información detallada por dispositivo."""
    print("\n📊 Generando informe por dispositivo...")
    
    informe_dispositivos = []
    
    for i in range(len(df)):
        punto = coords_3d[i]
        cluster_actual = labels[i]
        
        # Encontrar cluster más cercano
        cluster_cercano, dist_cercano = encontrar_cluster_mas_cercano(punto, centroides)
        
        # Distancia al centroide de su propio cluster (si no es outlier)
        if cluster_actual != -1:
            centroide_actual = centroides[cluster_actual]
            dist_propio_centroide = np.linalg.norm(punto - centroide_actual)
            esta_en_cluster_correcto = (cluster_actual == cluster_cercano)
        else:
            dist_propio_centroide = None
            esta_en_cluster_correcto = False
        
        # Clasificación
        if cluster_actual == -1:
            clasificacion = 'outlier'
        elif esta_en_cluster_correcto:
            clasificacion = 'bien_clasificado'
        else:
            clasificacion = 'posible_reclasificacion'
        
        informe_dispositivos.append({
            'auditoria_id': df.iloc[i]['auditoria_id'],
            'dispositivo_original': df.iloc[i]['dispositivo_original'],
            'dispositivo_normalizado': df.iloc[i]['dispositivo_normalizado'],
            'cluster_actual': cluster_actual,
            'es_outlier': cluster_actual == -1,
            'cluster_mas_cercano': cluster_cercano,
            'dist_cluster_cercano': round(dist_cercano, 3),
            'dist_propio_centroide': round(dist_propio_centroide, 3) if dist_propio_centroide else None,
            'clasificacion': clasificacion,
            'coord_x': round(punto[0], 3),
            'coord_y': round(punto[1], 3),
            'coord_z': round(punto[2], 3)
        })
    
    df_dispositivos = pd.DataFrame(informe_dispositivos)
    
    return df_dispositivos


def generar_resumen_ejecutivo(df_clusters, df_dispositivos, stats):
    """Genera CSV con resumen ejecutivo."""
    print("\n📊 Generando resumen ejecutivo...")
    
    # Estadísticas generales
    n_total = len(df_dispositivos)
    n_outliers = df_dispositivos['es_outlier'].sum()
    n_bien_clasificados = (df_dispositivos['clasificacion'] == 'bien_clasificado').sum()
    n_posible_reclasif = (df_dispositivos['clasificacion'] == 'posible_reclasificacion').sum()
    
    # Estadísticas de clusters
    cluster_mas_grande = df_clusters.iloc[0]
    cluster_mas_pequeño = df_clusters.iloc[-1]
    tamaño_promedio = df_clusters['tamaño'].mean()
    
    # Distancias promedio
    dist_media_global = df_clusters['dist_media_centroide'].mean()
    
    resumen = [
        {'metrica': 'total_dispositivos', 'valor': n_total},
        {'metrica': 'total_clusters', 'valor': stats['n_clusters']},
        {'metrica': 'total_outliers', 'valor': n_outliers},
        {'metrica': 'porcentaje_outliers', 'valor': round(stats['pct_noise'], 2)},
        {'metrica': 'dispositivos_bien_clasificados', 'valor': n_bien_clasificados},
        {'metrica': 'porcentaje_bien_clasificados', 'valor': round(n_bien_clasificados/n_total*100, 2)},
        {'metrica': 'dispositivos_posible_reclasificacion', 'valor': n_posible_reclasif},
        {'metrica': 'porcentaje_posible_reclasificacion', 'valor': round(n_posible_reclasif/n_total*100, 2)},
        {'metrica': 'cluster_mas_grande_id', 'valor': int(cluster_mas_grande['cluster_id'])},
        {'metrica': 'cluster_mas_grande_tamaño', 'valor': int(cluster_mas_grande['tamaño'])},
        {'metrica': 'cluster_mas_pequeño_id', 'valor': int(cluster_mas_pequeño['cluster_id'])},
        {'metrica': 'cluster_mas_pequeño_tamaño', 'valor': int(cluster_mas_pequeño['tamaño'])},
        {'metrica': 'tamaño_promedio_cluster', 'valor': round(tamaño_promedio, 2)},
        {'metrica': 'distancia_media_centroide_global', 'valor': round(dist_media_global, 3)},
        {'metrica': 'silhouette_score', 'valor': round(stats.get('silhouette', 0), 4)},
        {'metrica': 'davies_bouldin_score', 'valor': round(stats.get('davies_bouldin', 0), 4)}
    ]
    
    df_resumen = pd.DataFrame(resumen)
    
    return df_resumen


def main():
    print("=" * 80)
    print("GENERACIÓN DE INFORME CSV - CLUSTERING SAPBERT")
    print("=" * 80)
    print()
    
    base_dir = Path(__file__).parent.parent
    
    # Cargar datos
    embeddings, labels, df, stats = cargar_datos_sapbert()
    
    # Reducir a 3D
    coords_3d = reducir_a_3d(embeddings)
    
    # Calcular centroides
    print("\n📊 Calculando centroides...")
    centroides = calcular_centroides(coords_3d, labels)
    print(f"✅ Calculados {len(centroides)} centroides")
    
    # Generar informes
    df_clusters = generar_informe_por_cluster(coords_3d, labels, df, centroides)
    df_dispositivos = generar_informe_por_dispositivo(coords_3d, labels, df, centroides)
    df_resumen = generar_resumen_ejecutivo(df_clusters, df_dispositivos, stats)
    
    # Guardar CSVs
    print("\n💾 Guardando archivos CSV...")
    
    ruta_clusters = base_dir / 'reportes' / 'informe_clusters_sapbert.csv'
    df_clusters.to_csv(ruta_clusters, index=False, encoding='utf-8')
    print(f"✅ Guardado: {ruta_clusters}")
    
    ruta_dispositivos = base_dir / 'reportes' / 'informe_dispositivos_sapbert.csv'
    df_dispositivos.to_csv(ruta_dispositivos, index=False, encoding='utf-8')
    print(f"✅ Guardado: {ruta_dispositivos}")
    
    ruta_resumen = base_dir / 'reportes' / 'resumen_ejecutivo_sapbert.csv'
    df_resumen.to_csv(ruta_resumen, index=False, encoding='utf-8')
    print(f"✅ Guardado: {ruta_resumen}")
    
    # Mostrar resumen
    print("\n" + "=" * 80)
    print("RESUMEN EJECUTIVO")
    print("=" * 80)
    print(f"\n📊 Total dispositivos: {len(df_dispositivos)}")
    print(f"📊 Total clusters: {stats['n_clusters']}")
    print(f"📊 Outliers: {stats['n_noise']} ({stats['pct_noise']:.2f}%)")
    print(f"\n✅ Bien clasificados: {(df_dispositivos['clasificacion'] == 'bien_clasificado').sum()} "
          f"({(df_dispositivos['clasificacion'] == 'bien_clasificado').sum()/len(df_dispositivos)*100:.1f}%)")
    print(f"⚠️  Posible reclasificación: {(df_dispositivos['clasificacion'] == 'posible_reclasificacion').sum()} "
          f"({(df_dispositivos['clasificacion'] == 'posible_reclasificacion').sum()/len(df_dispositivos)*100:.1f}%)")
    
    print(f"\n📈 Cluster más grande: {df_clusters.iloc[0]['cluster_id']} "
          f"({df_clusters.iloc[0]['tamaño']} dispositivos)")
    print(f"📉 Cluster más pequeño: {df_clusters.iloc[-1]['cluster_id']} "
          f"({df_clusters.iloc[-1]['tamaño']} dispositivos)")
    print(f"📊 Tamaño promedio: {df_clusters['tamaño'].mean():.1f} dispositivos/cluster")
    
    print("\n" + "=" * 80)
    print("ARCHIVOS GENERADOS")
    print("=" * 80)
    print(f"\n1. {ruta_clusters.name}")
    print(f"   - {len(df_clusters)} clusters")
    print(f"   - Estadísticas por cluster (tamaño, distancias, ejemplos)")
    
    print(f"\n2. {ruta_dispositivos.name}")
    print(f"   - {len(df_dispositivos)} dispositivos")
    print(f"   - Cluster actual, cluster más cercano, clasificación")
    
    print(f"\n3. {ruta_resumen.name}")
    print(f"   - {len(df_resumen)} métricas")
    print(f"   - Resumen ejecutivo del clustering")


if __name__ == '__main__':
    main()
