#!/usr/bin/env python3
"""
Visualización 3D de Clusters con UMAP
Genera múltiples perspectivas de los datos en 3 dimensiones.
"""
import pickle
import numpy as np
import plotly.graph_objects as go
from umap import UMAP


def cargar_datos_clustered(archivo: str = '../data/vectorial/dispositivos_clustered.pkl'):
    """Carga datos con clusters asignados."""
    print(f"Cargando datos desde: {archivo}")
    
    with open(archivo, 'rb') as f:
        datos = pickle.load(f)
    
    print(f"✅ Cargados {len(datos)} registros con clusters")
    return datos


def reducir_dimensionalidad_3d(embeddings, n_neighbors=15, min_dist=0.1):
    """Reduce dimensionalidad usando UMAP a 3 dimensiones."""
    print(f"\nAplicando UMAP para reducir de {embeddings.shape[1]} a 3 dimensiones...")
    print(f"  n_neighbors: {n_neighbors}")
    print(f"  min_dist: {min_dist}")
    
    reducer = UMAP(
        n_components=3,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric='cosine',
        random_state=42
    )
    
    embeddings_reducidos = reducer.fit_transform(embeddings)
    print(f"✅ Reducción completada")
    
    return embeddings_reducidos


def visualizar_clusters_3d(datos, embeddings_3d, titulo="Visualización 3D"):
    """Crea visualización 3D interactiva con Plotly."""
    print("\nGenerando visualización 3D interactiva...")
    
    # Preparar datos
    x = embeddings_3d[:, 0]
    y = embeddings_3d[:, 1]
    z = embeddings_3d[:, 2]
    clusters = [d['cluster_id'] for d in datos]
    
    # Crear texto hover personalizado
    hover_texts = []
    for i, d in enumerate(datos):
        hover_text = (
            f"<b>{d['nombre_original']}</b><br>"
            f"Auditoría: {d['auditoria_id']}<br>"
            f"Cluster: {d['cluster_id']}<br>"
            f"Normalizado: {d['nombre_normalizado']}"
        )
        hover_texts.append(hover_text)
    
    # Crear figura
    fig = go.Figure()
    
    # Obtener clusters únicos
    clusters_unicos = sorted(set(clusters))
    
    print(f"Total de clusters únicos: {len(clusters_unicos)}")
    
    # Crear una traza por cluster
    for cluster_id in clusters_unicos:
        # Filtrar puntos de este cluster
        indices = [i for i, c in enumerate(clusters) if c == cluster_id]
        
        fig.add_trace(go.Scatter3d(
            x=[x[i] for i in indices],
            y=[y[i] for i in indices],
            z=[z[i] for i in indices],
            mode='markers',
            name=f'Cluster {cluster_id}',
            text=[hover_texts[i] for i in indices],
            hovertemplate='%{text}<extra></extra>',
            marker=dict(
                size=4,
                opacity=0.7,
                line=dict(width=0.5, color='white')
            )
        ))
    
    # Configurar layout
    fig.update_layout(
        title={
            'text': f'{titulo} ({len(datos)} dispositivos)',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        scene=dict(
            xaxis_title='UMAP Dimensión 1',
            yaxis_title='UMAP Dimensión 2',
            zaxis_title='UMAP Dimensión 3',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        width=1400,
        height=900,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        hovermode='closest'
    )
    
    return fig


def generar_multiples_perspectivas(datos, embeddings):
    """Genera visualizaciones con diferentes parámetros de UMAP."""
    print("\n" + "="*80)
    print("GENERANDO MÚLTIPLES PERSPECTIVAS")
    print("="*80)
    
    configuraciones = [
        {"n_neighbors": 15, "min_dist": 0.1, "nombre": "default"},
        {"n_neighbors": 5, "min_dist": 0.1, "nombre": "local"},
        {"n_neighbors": 30, "min_dist": 0.1, "nombre": "global"},
        {"n_neighbors": 15, "min_dist": 0.0, "nombre": "compacto"},
        {"n_neighbors": 15, "min_dist": 0.5, "nombre": "disperso"}
    ]
    
    archivos_generados = []
    
    for config in configuraciones:
        print(f"\n{'='*80}")
        print(f"Configuración: {config['nombre']}")
        print(f"  n_neighbors={config['n_neighbors']}, min_dist={config['min_dist']}")
        print("="*80)
        
        # Reducir dimensionalidad con esta configuración
        embeddings_3d = reducir_dimensionalidad_3d(
            embeddings, 
            n_neighbors=config['n_neighbors'],
            min_dist=config['min_dist']
        )
        
        # Crear visualización
        titulo = f"Visualización 3D - {config['nombre'].capitalize()}"
        fig = visualizar_clusters_3d(datos, embeddings_3d, titulo)
        
        # Guardar HTML
        html_file = f"../visualizaciones/visualizacion_3d_{config['nombre']}.html"
        fig.write_html(html_file)
        print(f"✅ Guardado: {html_file}")
        
        archivos_generados.append(html_file)
    
    return archivos_generados


if __name__ == "__main__":
    print("="*80)
    print("VISUALIZACIÓN 3D CON MÚLTIPLES PERSPECTIVAS")
    print("="*80)
    print()
    
    # Cargar datos
    datos = cargar_datos_clustered()
    
    # Extraer embeddings
    embeddings = np.array([d['embedding'] for d in datos])
    print(f"\nEmbeddings shape: {embeddings.shape}")
    
    # Generar múltiples perspectivas
    archivos = generar_multiples_perspectivas(datos, embeddings)
    
    # Abrir la visualización default en el navegador
    print("\n" + "="*80)
    print("ABRIENDO VISUALIZACIÓN DEFAULT")
    print("="*80)
    
    import plotly.graph_objects as go
    embeddings_3d_default = reducir_dimensionalidad_3d(embeddings, n_neighbors=15, min_dist=0.1)
    fig_default = visualizar_clusters_3d(datos, embeddings_3d_default, "Visualización 3D - Default")
    fig_default.show()
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivos HTML generados:")
    for archivo in archivos:
        print(f"  - {archivo}")
    print("\nCada archivo muestra una perspectiva diferente de los datos:")
    print("  - default: Configuración estándar balanceada")
    print("  - local: Enfatiza estructura local (n_neighbors=5)")
    print("  - global: Enfatiza estructura global (n_neighbors=30)")
    print("  - compacto: Clusters más densos (min_dist=0.0)")
    print("  - disperso: Clusters más separados (min_dist=0.5)")
    print("\nPuedes rotar, hacer zoom y explorar cada visualización en 3D.")
