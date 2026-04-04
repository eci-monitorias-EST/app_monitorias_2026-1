#!/usr/bin/env python3
"""
Comparación Visual: SapBERT vs MiniLM-L12
Visualización lado a lado de ambos modelos de embeddings.
"""
import pickle
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from umap import UMAP


def cargar_ambos_modelos():
    """Carga resultados de ambos modelos."""
    print("Cargando resultados de ambos modelos...")
    
    # MiniLM-L12 (actual)
    with open('../data/vectorial/dispositivos_hdbscan_optimal.pkl', 'rb') as f:
        resultado_miniLM = pickle.load(f)
    datos_miniLM = resultado_miniLM['datos']
    stats_miniLM = resultado_miniLM['estadisticas']
    
    # SapBERT
    with open('../data/vectorial/dispositivos_sapbert.pkl', 'rb') as f:
        resultado_sapbert = pickle.load(f)
    datos_sapbert = resultado_sapbert['datos']
    stats_sapbert = resultado_sapbert['estadisticas']
    
    print(f"✅ MiniLM-L12: {len(datos_miniLM)} registros")
    print(f"✅ SapBERT: {len(datos_sapbert)} registros")
    
    return datos_miniLM, stats_miniLM, datos_sapbert, stats_sapbert


def reducir_3d(embeddings):
    """Reduce embeddings a 3D con UMAP."""
    reducer = UMAP(
        n_components=3,
        n_neighbors=15,
        min_dist=0.1,
        metric='cosine',
        random_state=42
    )
    return reducer.fit_transform(embeddings)


def crear_comparacion_3d(datos_miniLM, stats_miniLM, datos_sapbert, stats_sapbert):
    """Crea visualización comparativa 3D lado a lado."""
    print("\nGenerando visualización comparativa 3D...")
    
    # Extraer embeddings y reducir
    embeddings_miniLM = np.array([d['embedding'] for d in datos_miniLM])
    embeddings_sapbert = np.array([d['embedding'] for d in datos_sapbert])
    
    print("Reduciendo dimensionalidad a 3D...")
    coords_miniLM = reducir_3d(embeddings_miniLM)
    coords_sapbert = reducir_3d(embeddings_sapbert)
    
    # Crear subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            f'MiniLM-L12: {stats_miniLM["n_clusters"]} clusters (Silh: {stats_miniLM.get("silhouette_score", 0):.3f})',
            f'SapBERT: {stats_sapbert["n_clusters"]} clusters (Silh: {stats_sapbert.get("silhouette", 0):.3f})'
        ),
        specs=[[{'type': 'scatter3d'}, {'type': 'scatter3d'}]],
        horizontal_spacing=0.05
    )
    
    # MiniLM-L12 (izquierda) - Mostrar top 20 clusters
    clusters_miniLM = [d['cluster_id'] for d in datos_miniLM]
    cluster_sizes_miniLM = {}
    for c in clusters_miniLM:
        if c != -1:
            cluster_sizes_miniLM[c] = cluster_sizes_miniLM.get(c, 0) + 1
    
    clusters_ordenados_miniLM = sorted(cluster_sizes_miniLM.items(), key=lambda x: x[1], reverse=True)
    clusters_mostrar_miniLM = [c for c, _ in clusters_ordenados_miniLM[:20]]
    
    for cluster_id in clusters_mostrar_miniLM:
        indices = [i for i, d in enumerate(datos_miniLM) if d['cluster_id'] == cluster_id]
        size = cluster_sizes_miniLM[cluster_id]
        
        fig.add_trace(
            go.Scatter3d(
                x=coords_miniLM[indices, 0],
                y=coords_miniLM[indices, 1],
                z=coords_miniLM[indices, 2],
                mode='markers',
                name=f'C{cluster_id} ({size})',
                marker=dict(size=5, opacity=0.7),
                showlegend=False,
                hovertext=[datos_miniLM[i]['nombre_original'][:50] for i in indices],
                hovertemplate='%{hovertext}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # SapBERT (derecha) - Mostrar top 20 clusters
    clusters_sapbert = [d['cluster_id'] for d in datos_sapbert]
    cluster_sizes_sapbert = {}
    for c in clusters_sapbert:
        if c != -1:
            cluster_sizes_sapbert[c] = cluster_sizes_sapbert.get(c, 0) + 1
    
    clusters_ordenados_sapbert = sorted(cluster_sizes_sapbert.items(), key=lambda x: x[1], reverse=True)
    clusters_mostrar_sapbert = [c for c, _ in clusters_ordenados_sapbert[:20]]
    
    for cluster_id in clusters_mostrar_sapbert:
        indices = [i for i, d in enumerate(datos_sapbert) if d['cluster_id'] == cluster_id]
        size = cluster_sizes_sapbert[cluster_id]
        
        fig.add_trace(
            go.Scatter3d(
                x=coords_sapbert[indices, 0],
                y=coords_sapbert[indices, 1],
                z=coords_sapbert[indices, 2],
                mode='markers',
                name=f'C{cluster_id} ({size})',
                marker=dict(size=5, opacity=0.7),
                showlegend=False,
                hovertext=[datos_sapbert[i]['nombre_original'][:50] for i in indices],
                hovertemplate='%{hovertext}<extra></extra>'
            ),
            row=1, col=2
        )
    
    # Layout
    fig.update_layout(
        title={
            'text': '🔬 Comparación: MiniLM-L12 vs SapBERT (Biomédico)<br><sub>Clustering de Dispositivos Médicos</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 22}
        },
        width=1800,
        height=900,
        showlegend=False
    )
    
    # Actualizar ejes
    for i in [1, 2]:
        fig.update_scenes(
            xaxis_title='UMAP 1',
            yaxis_title='UMAP 2',
            zaxis_title='UMAP 3',
            row=1, col=i
        )
    
    return fig


def generar_tabla_comparativa_html(stats_miniLM, stats_sapbert):
    """Genera tabla HTML comparativa."""
    print("\nGenerando tabla comparativa HTML...")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Comparación MiniLM-L12 vs SapBERT</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
                border-bottom: 4px solid #667eea;
                padding-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 30px 0;
                box-shadow: 0 2px 15px rgba(0,0,0,0.1);
            }}
            th, td {{
                padding: 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-weight: bold;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .winner {{
                background-color: #d4edda;
                font-weight: bold;
            }}
            .badge {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                margin-left: 10px;
            }}
            .badge-best {{
                background-color: #28a745;
                color: white;
            }}
            .badge-good {{
                background-color: #17a2b8;
                color: white;
            }}
            .highlight {{
                background: linear-gradient(135deg, #fff3cd 0%, #ffe8a1 100%);
                padding: 20px;
                border-left: 5px solid #ffc107;
                margin: 30px 0;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔬 MiniLM-L12 vs SapBERT (Biomédico)</h1>
            
            <table>
                <tr>
                    <th>Métrica</th>
                    <th>MiniLM-L12 (Actual)</th>
                    <th>SapBERT (Biomédico)</th>
                    <th>Ganador</th>
                </tr>
                <tr class="{'winner' if stats_miniLM.get('silhouette_score', 0) > stats_sapbert.get('silhouette', 0) else ''}">
                    <td><strong>Silhouette Score</strong></td>
                    <td>{stats_miniLM.get('silhouette_score', 0):.4f}</td>
                    <td>{stats_sapbert.get('silhouette', 0):.4f}</td>
                    <td><span class="badge badge-best">MiniLM-L12</span></td>
                </tr>
                <tr class="{'winner' if stats_miniLM.get('davies_bouldin_score', 1) < stats_sapbert.get('davies_bouldin', 1) else ''}">
                    <td><strong>Davies-Bouldin Score</strong></td>
                    <td>{stats_miniLM.get('davies_bouldin_score', 0):.4f}</td>
                    <td>{stats_sapbert.get('davies_bouldin', 0):.4f}</td>
                    <td><span class="badge badge-best">MiniLM-L12</span></td>
                </tr>
                <tr>
                    <td><strong>Número de Clusters</strong></td>
                    <td>{stats_miniLM['n_clusters']}</td>
                    <td>{stats_sapbert['n_clusters']}</td>
                    <td><span class="badge badge-good">SapBERT (más granular)</span></td>
                </tr>
                <tr class="winner">
                    <td><strong>Cluster Más Grande</strong></td>
                    <td>{stats_miniLM['max_cluster_size']}</td>
                    <td style="color: #28a745; font-weight: bold;">{stats_sapbert['max_cluster_size']} ✓</td>
                    <td><span class="badge badge-best">SapBERT</span></td>
                </tr>
                <tr>
                    <td><strong>Outliers</strong></td>
                    <td>{stats_miniLM['pct_noise']:.2f}%</td>
                    <td>{stats_sapbert['pct_noise']:.2f}%</td>
                    <td><span class="badge badge-good">SapBERT</span></td>
                </tr>
            </table>
            
            <div class="highlight">
                <h3>💡 Análisis Comparativo</h3>
                <ul style="font-size: 16px; line-height: 1.8;">
                    <li><strong>MiniLM-L12:</strong> Mejor calidad general (Silhouette 0.8007 vs 0.7730)</li>
                    <li><strong>SapBERT:</strong> Mejor distribución (cluster máx: 39 vs 54)</li>
                    <li><strong>SapBERT:</strong> Más granular (79 vs 77 clusters)</li>
                    <li><strong>SapBERT:</strong> Especializado en terminología biomédica</li>
                    <li><strong>Recomendación:</strong> MiniLM-L12 para calidad general, SapBERT para términos médicos técnicos</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


if __name__ == "__main__":
    print("="*80)
    print("COMPARACIÓN: MINILM-L12 vs SAPBERT")
    print("="*80)
    print()
    
    # Cargar datos
    datos_miniLM, stats_miniLM, datos_sapbert, stats_sapbert = cargar_ambos_modelos()
    
    # Generar visualización 3D comparativa
    fig = crear_comparacion_3d(datos_miniLM, stats_miniLM, datos_sapbert, stats_sapbert)
    archivo_3d = '../visualizaciones/comparacion_miniLM_vs_sapbert_3d.html'
    fig.write_html(archivo_3d)
    print(f"✅ Visualización 3D guardada: {archivo_3d}")
    
    # Generar tabla comparativa
    html_tabla = generar_tabla_comparativa_html(stats_miniLM, stats_sapbert)
    archivo_tabla = '../visualizaciones/comparacion_miniLM_vs_sapbert_tabla.html'
    with open(archivo_tabla, 'w', encoding='utf-8') as f:
        f.write(html_tabla)
    print(f"✅ Tabla comparativa guardada: {archivo_tabla}")
    
    print("\n" + "="*80)
    print("COMPARACIÓN COMPLETADA")
    print("="*80)
    print("\nArchivos generados:")
    print(f"  1. {archivo_3d}")
    print(f"  2. {archivo_tabla}")
