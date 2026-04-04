#!/usr/bin/env python3
"""
Análisis de vecindad local para un punto de consulta.

Añade capas visuales a la visualización 3D existente:
- Punto de consulta (rojo, grande)
- Vecinos dentro del radio (amarillo)
- Centroide del cluster más cercano (negro, estrella)
- Línea conectando punto de consulta con centroide

NO modifica los clusters existentes.
"""

import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from sklearn.metrics.pairwise import euclidean_distances
from umap import UMAP
import hdbscan


def cargar_datos_sapbert():
    """Carga los datos de clustering SapBERT."""
    base_dir = Path(__file__).parent.parent
    ruta_pkl = base_dir / 'data' / 'vectorial' / 'dispositivos_sapbert.pkl'
    
    print(f"📂 Cargando datos SapBERT desde: {ruta_pkl}")
    with open(ruta_pkl, 'rb') as f:
        data = pickle.load(f)
    
    datos = data['datos']
    stats = data['estadisticas']
    
    # Extraer embeddings y labels
    embeddings = np.array([d['embedding'] for d in datos])
    labels = np.array([d['cluster_id'] for d in datos])
    
    # Crear DataFrame
    df = pd.DataFrame([
        {
            'auditoria_id': d['auditoria_id'],
            'dispositivo_original': d['nombre_original'],
            'dispositivo_normalizado': d['nombre_normalizado'],
            'cluster_id': labels[i]
        }
        for i, d in enumerate(datos)
    ])
    
    print(f"✅ Datos cargados: {len(df)} dispositivos")
    print(f"   Clusters: {stats['n_clusters']}")
    print(f"   Outliers: {stats['n_noise']}")
    
    return embeddings, labels, df


def reducir_a_3d(embeddings):
    """Reduce embeddings a 3D usando UMAP."""
    print("\n🔄 Reduciendo a 3D con UMAP...")
    
    # Primero a 50D (como en el clustering original)
    umap_50d = UMAP(
        n_components=50,
        n_neighbors=30,
        min_dist=0.0,
        metric='cosine',
        random_state=42
    )
    embeddings_50d = umap_50d.fit_transform(embeddings)
    
    # Luego a 3D para visualización
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
    
    print(f"\n📊 Calculados {len(centroides)} centroides")
    
    return centroides


def encontrar_vecinos(query_point, coords_3d, radio=5.0):
    """
    Encuentra todos los puntos dentro del radio euclidiano.
    
    Args:
        query_point: coordenadas 3D del punto de consulta
        coords_3d: todas las coordenadas 3D
        radio: radio de búsqueda en unidades UMAP
    
    Returns:
        indices de los vecinos dentro del radio
    """
    distancias = euclidean_distances(
        query_point.reshape(1, -1),
        coords_3d
    ).flatten()
    
    vecinos_indices = np.where(distancias <= radio)[0]
    
    return vecinos_indices, distancias[vecinos_indices]


def encontrar_centroide_mas_cercano(query_point, centroides):
    """
    Encuentra el centroide más cercano al punto de consulta.
    
    Returns:
        (cluster_id, centroide, distancia)
    """
    min_distancia = float('inf')
    cluster_mas_cercano = None
    centroide_mas_cercano = None
    
    for cluster_id, centroide in centroides.items():
        distancia = np.linalg.norm(query_point - centroide)
        
        if distancia < min_distancia:
            min_distancia = distancia
            cluster_mas_cercano = cluster_id
            centroide_mas_cercano = centroide
    
    return cluster_mas_cercano, centroide_mas_cercano, min_distancia


def crear_visualizacion_con_vecindad(
    coords_3d,
    labels,
    df,
    query_idx,
    radio=5.0
):
    """
    Crea visualización 3D con análisis de vecindad local.
    
    Args:
        coords_3d: coordenadas 3D de todos los puntos
        labels: etiquetas de cluster
        df: DataFrame con información de dispositivos
        query_idx: índice del punto de consulta
        radio: radio de búsqueda
    """
    print("\n" + "=" * 80)
    print("ANÁLISIS DE VECINDAD LOCAL")
    print("=" * 80)
    
    query_point = coords_3d[query_idx]
    query_label = labels[query_idx]
    query_dispositivo = df.iloc[query_idx]['dispositivo_normalizado']
    
    print(f"\n🎯 Punto de consulta (índice {query_idx}):")
    print(f"   Dispositivo: {query_dispositivo}")
    print(f"   Cluster: {query_label}")
    print(f"   Coordenadas: ({query_point[0]:.2f}, {query_point[1]:.2f}, {query_point[2]:.2f})")
    
    # Calcular centroides
    centroides = calcular_centroides(coords_3d, labels)
    
    # Encontrar vecinos
    print(f"\n🔍 Buscando vecinos dentro de radio = {radio} unidades...")
    vecinos_indices, vecinos_distancias = encontrar_vecinos(query_point, coords_3d, radio)
    
    print(f"✅ Encontrados {len(vecinos_indices)} vecinos (incluyendo el punto mismo)")
    
    # Analizar clusters de los vecinos
    vecinos_labels = labels[vecinos_indices]
    clusters_vecinos = {}
    for label in vecinos_labels:
        if label not in clusters_vecinos:
            clusters_vecinos[label] = 0
        clusters_vecinos[label] += 1
    
    print(f"\n📊 Distribución de clusters en vecindad:")
    for cluster_id, count in sorted(clusters_vecinos.items(), key=lambda x: x[1], reverse=True):
        cluster_name = "Outlier" if cluster_id == -1 else f"Cluster {cluster_id}"
        print(f"   {cluster_name}: {count} puntos ({count/len(vecinos_indices)*100:.1f}%)")
    
    # Encontrar centroide más cercano
    cluster_cercano, centroide_cercano, dist_centroide = encontrar_centroide_mas_cercano(
        query_point,
        centroides
    )
    
    print(f"\n⭐ Centroide más cercano:")
    print(f"   Cluster: {cluster_cercano}")
    print(f"   Distancia: {dist_centroide:.2f} unidades")
    print(f"   Coordenadas: ({centroide_cercano[0]:.2f}, {centroide_cercano[1]:.2f}, {centroide_cercano[2]:.2f})")
    
    # Crear figura
    print("\n🎨 Generando visualización 3D...")
    fig = go.Figure()
    
    # CAPA 1: Todos los clusters (tenues, fondo)
    clusters_unicos = sorted([c for c in np.unique(labels) if c != -1])
    
    for cluster_id in clusters_unicos:
        mask = labels == cluster_id
        hover_text = [
            f"<b>{df.iloc[i]['dispositivo_normalizado'][:60]}</b><br>" +
            f"Cluster: {cluster_id}<br>" +
            f"Auditoría: {df.iloc[i]['auditoria_id']}"
            for i in np.where(mask)[0]
        ]
        
        fig.add_trace(
            go.Scatter3d(
                x=coords_3d[mask, 0],
                y=coords_3d[mask, 1],
                z=coords_3d[mask, 2],
                mode='markers',
                name=f'Cluster {cluster_id}',
                marker=dict(size=2, opacity=0.3),
                hovertext=hover_text,
                hoverinfo='text',
                showlegend=False
            )
        )
    
    # Outliers (muy tenues)
    outliers_mask = labels == -1
    if np.any(outliers_mask):
        fig.add_trace(
            go.Scatter3d(
                x=coords_3d[outliers_mask, 0],
                y=coords_3d[outliers_mask, 1],
                z=coords_3d[outliers_mask, 2],
                mode='markers',
                name='Outliers',
                marker=dict(size=2, color='gray', opacity=0.2),
                hoverinfo='skip',
                showlegend=False
            )
        )
    
    # CAPA 2: Vecinos (amarillo)
    # Excluir el punto de consulta de los vecinos para mostrarlo separado
    vecinos_sin_query = [i for i in vecinos_indices if i != query_idx]
    
    if len(vecinos_sin_query) > 0:
        hover_vecinos = [
            f"<b>VECINO</b><br>" +
            f"{df.iloc[i]['dispositivo_normalizado'][:60]}<br>" +
            f"Cluster: {labels[i]}<br>" +
            f"Distancia al query: {euclidean_distances(query_point.reshape(1, -1), coords_3d[i].reshape(1, -1))[0, 0]:.2f}"
            for i in vecinos_sin_query
        ]
        
        fig.add_trace(
            go.Scatter3d(
                x=coords_3d[vecinos_sin_query, 0],
                y=coords_3d[vecinos_sin_query, 1],
                z=coords_3d[vecinos_sin_query, 2],
                mode='markers',
                name=f'Vecinos (radio={radio})',
                marker=dict(
                    size=6,
                    color='yellow',
                    opacity=0.7,
                    line=dict(color='orange', width=1)
                ),
                hovertext=hover_vecinos,
                hoverinfo='text'
            )
        )
    
    # CAPA 3: Todos los centroides (pequeños, grises)
    centroides_coords = np.array([c for c in centroides.values()])
    centroides_ids = list(centroides.keys())
    
    hover_centroides = [
        f"<b>CENTROIDE</b><br>" +
        f"Cluster: {cluster_id}<br>" +
        f"Distancia al query: {np.linalg.norm(query_point - centroides[cluster_id]):.2f}"
        for cluster_id in centroides_ids
    ]
    
    fig.add_trace(
        go.Scatter3d(
            x=centroides_coords[:, 0],
            y=centroides_coords[:, 1],
            z=centroides_coords[:, 2],
            mode='markers',
            name='Centroides',
            marker=dict(
                size=4,
                color='lightgray',
                symbol='diamond',
                opacity=0.5
            ),
            hovertext=hover_centroides,
            hoverinfo='text',
            showlegend=False
        )
    )
    
    # CAPA 4: Centroide más cercano (negro, estrella grande)
    fig.add_trace(
        go.Scatter3d(
            x=[centroide_cercano[0]],
            y=[centroide_cercano[1]],
            z=[centroide_cercano[2]],
            mode='markers',
            name=f'Centroide más cercano (C{cluster_cercano})',
            marker=dict(
                size=12,
                color='black',
                symbol='diamond',
                line=dict(color='white', width=2)
            ),
            hovertext=[
                f"<b>⭐ CENTROIDE MÁS CERCANO</b><br>" +
                f"Cluster: {cluster_cercano}<br>" +
                f"Distancia al query: {dist_centroide:.2f}"
            ],
            hoverinfo='text'
        )
    )
    
    # CAPA 5: Línea entre query point y centroide más cercano
    fig.add_trace(
        go.Scatter3d(
            x=[query_point[0], centroide_cercano[0]],
            y=[query_point[1], centroide_cercano[1]],
            z=[query_point[2], centroide_cercano[2]],
            mode='lines',
            name='Conexión query-centroide',
            line=dict(color='purple', width=4, dash='dash'),
            hoverinfo='skip',
            showlegend=False
        )
    )
    
    # CAPA 6: Punto de consulta (rojo, grande, al final para que esté encima)
    fig.add_trace(
        go.Scatter3d(
            x=[query_point[0]],
            y=[query_point[1]],
            z=[query_point[2]],
            mode='markers',
            name='🎯 Punto de consulta',
            marker=dict(
                size=15,
                color='red',
                symbol='circle',
                line=dict(color='darkred', width=3)
            ),
            hovertext=[
                f"<b>🎯 PUNTO DE CONSULTA</b><br>" +
                f"{query_dispositivo}<br>" +
                f"Cluster original: {query_label}<br>" +
                f"Vecinos encontrados: {len(vecinos_indices)}<br>" +
                f"Centroide más cercano: Cluster {cluster_cercano} (dist={dist_centroide:.2f})"
            ],
            hoverinfo='text'
        )
    )
    
    # Layout
    fig.update_layout(
        title=dict(
            text=(
                f"<b>Análisis de Vecindad Local - SapBERT</b><br>" +
                f"<sub>Query: {query_dispositivo[:80]}<br>" +
                f"Radio: {radio} unidades | Vecinos: {len(vecinos_indices)} | " +
                f"Centroide más cercano: Cluster {cluster_cercano} (dist={dist_centroide:.2f})</sub>"
            ),
            x=0.5,
            xanchor='center'
        ),
        scene=dict(
            xaxis_title='UMAP 1',
            yaxis_title='UMAP 2',
            zaxis_title='UMAP 3',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        height=800,
        showlegend=True,
        legend=dict(x=1.02, y=0.5)
    )
    
    return fig


def main():
    print("=" * 80)
    print("ANÁLISIS DE VECINDAD LOCAL - SAPBERT")
    print("=" * 80)
    print()
    
    # Cargar datos
    embeddings, labels, df = cargar_datos_sapbert()
    
    # Reducir a 3D
    coords_3d = reducir_a_3d(embeddings)
    
    # Seleccionar punto de consulta
    # Opción 1: Seleccionar un outlier interesante
    outliers_indices = np.where(labels == -1)[0]
    
    if len(outliers_indices) > 0:
        query_idx = outliers_indices[0]  # Primer outlier
        print(f"\n📍 Seleccionado outlier como punto de consulta (índice {query_idx})")
    else:
        # Opción 2: Seleccionar un punto aleatorio
        query_idx = np.random.randint(0, len(labels))
        print(f"\n📍 Seleccionado punto aleatorio como consulta (índice {query_idx})")
    
    # Parámetros de análisis
    RADIO = 5.0  # unidades UMAP
    
    # Crear visualización
    fig = crear_visualizacion_con_vecindad(
        coords_3d,
        labels,
        df,
        query_idx,
        radio=RADIO
    )
    
    # Guardar
    base_dir = Path(__file__).parent.parent
    ruta_salida = base_dir / 'visualizaciones' / 'analisis_vecindad_local_sapbert.html'
    fig.write_html(str(ruta_salida))
    
    print(f"\n✅ Visualización guardada: {ruta_salida}")
    
    print("\n" + "=" * 80)
    print("ANÁLISIS COMPLETADO")
    print("=" * 80)
    print("\nLa visualización muestra:")
    print("  🔴 Punto de consulta (rojo, grande)")
    print("  🟡 Vecinos dentro del radio (amarillo)")
    print("  ⚫ Centroide más cercano (negro, diamante)")
    print("  🟣 Línea conectando query con centroide (púrpura)")
    print("  ⚪ Todos los demás centroides (gris claro)")
    print("  🌫️  Clusters existentes (fondo tenue)")


if __name__ == '__main__':
    main()
