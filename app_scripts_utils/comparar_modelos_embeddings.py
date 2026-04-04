#!/usr/bin/env python3
"""
Comparación de Modelos de Embeddings
Prueba diferentes modelos de sentence-transformers y compara resultados de clustering.
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


# Modelos a comparar
MODELOS = {
    'MiniLM-L12 (actual)': 'paraphrase-multilingual-MiniLM-L12-v2',
    'E5-base (multilingüe)': 'intfloat/multilingual-e5-base',
    'E5-large (multilingüe)': 'intfloat/multilingual-e5-large',
    'SapBERT (biomédico)': 'cambridgeltl/SapBERT-from-PubMedBERT-fulltext',
    'MPNet-base': 'all-mpnet-base-v2',
}


def cargar_datos_normalizados(archivo: str = '../reportes/dispositivos_hdbscan_optimal.csv'):
    """Carga datos limpios desde CSV de reportes."""
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


def generar_embeddings_modelo(textos: List[str], modelo_nombre: str) -> Tuple[np.ndarray, float, int]:
    """Genera embeddings con un modelo específico."""
    print(f"\n  Cargando modelo: {modelo_nombre}")
    start_time = time.time()
    
    try:
        modelo = SentenceTransformer(modelo_nombre)
        load_time = time.time() - start_time
        
        print(f"  ✅ Modelo cargado en {load_time:.2f}s")
        print(f"     Dimensiones: {modelo.get_sentence_embedding_dimension()}")
        
        # Generar embeddings
        print(f"  Generando embeddings...")
        start_embed = time.time()
        embeddings = modelo.encode(textos, show_progress_bar=True, batch_size=32)
        embed_time = time.time() - start_embed
        
        print(f"  ✅ Embeddings generados en {embed_time:.2f}s")
        
        return embeddings, embed_time, modelo.get_sentence_embedding_dimension()
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None, 0, 0


def clustering_hdbscan_rapido(embeddings: np.ndarray) -> Tuple[np.ndarray, Dict]:
    """Ejecuta HDBSCAN con configuración óptima."""
    # Reducir dimensionalidad con UMAP
    reducer = UMAP(
        n_components=50,
        n_neighbors=30,
        min_dist=0.0,
        metric='cosine',
        random_state=42
    )
    embeddings_reducidos = reducer.fit_transform(embeddings)
    
    # HDBSCAN con configuración óptima
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=7,
        min_samples=5,
        metric='euclidean',
        cluster_selection_method='eom'
    )
    
    labels = clusterer.fit_predict(embeddings_reducidos)
    
    # Calcular estadísticas
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    pct_noise = (n_noise / len(labels) * 100)
    
    # Calcular tamaño del cluster más grande
    cluster_sizes = {}
    for label in labels:
        if label != -1:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
    max_cluster_size = max(cluster_sizes.values()) if cluster_sizes else 0
    
    # Métricas de calidad
    silhouette = None
    davies_bouldin = None
    
    if n_clusters > 1:
        mask = labels != -1
        if mask.sum() > n_clusters:
            try:
                silhouette = silhouette_score(embeddings_reducidos[mask], labels[mask])
                davies_bouldin = davies_bouldin_score(embeddings_reducidos[mask], labels[mask])
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


def comparar_modelos(datos: List[Dict]):
    """Compara diferentes modelos de embeddings."""
    print(f"\n{'='*80}")
    print("COMPARACIÓN DE MODELOS DE EMBEDDINGS")
    print("="*80)
    print(f"\nProbando {len(MODELOS)} modelos diferentes...")
    
    textos = [d['nombre_normalizado'] for d in datos]
    resultados = []
    
    for nombre_modelo, modelo_id in MODELOS.items():
        print(f"\n{'='*80}")
        print(f"MODELO: {nombre_modelo}")
        print("="*80)
        
        # Generar embeddings
        embeddings, embed_time, dims = generar_embeddings_modelo(textos, modelo_id)
        
        if embeddings is None:
            print(f"  ⚠️  Saltando modelo por error")
            continue
        
        # Clustering
        print(f"\n  Ejecutando clustering...")
        start_cluster = time.time()
        labels, stats = clustering_hdbscan_rapido(embeddings)
        cluster_time = time.time() - start_cluster
        
        print(f"  ✅ Clustering completado en {cluster_time:.2f}s")
        print(f"\n  Resultados:")
        print(f"    Clusters: {stats['n_clusters']}")
        print(f"    Outliers: {stats['n_noise']} ({stats['pct_noise']:.2f}%)")
        print(f"    Cluster más grande: {stats['max_cluster_size']}")
        if stats['silhouette']:
            print(f"    Silhouette: {stats['silhouette']:.4f}")
            print(f"    Davies-Bouldin: {stats['davies_bouldin']:.4f}")
        
        # Guardar resultados
        resultados.append({
            'modelo': nombre_modelo,
            'modelo_id': modelo_id,
            'dimensiones': dims,
            'tiempo_embeddings': embed_time,
            'tiempo_clustering': cluster_time,
            'tiempo_total': embed_time + cluster_time,
            **stats
        })
    
    return resultados


def generar_tabla_comparativa(resultados: List[Dict]):
    """Genera tabla comparativa de resultados."""
    print(f"\n{'='*80}")
    print("TABLA COMPARATIVA DE MODELOS")
    print("="*80)
    
    df = pd.DataFrame(resultados)
    
    # Ordenar por silhouette (descendente)
    df = df.sort_values('silhouette', ascending=False)
    
    print("\n")
    print(df.to_string(index=False))
    
    # Guardar CSV
    archivo_csv = '../reportes/comparacion_modelos_embeddings.csv'
    df.to_csv(archivo_csv, index=False, encoding='utf-8')
    print(f"\n✅ Tabla guardada: {archivo_csv}")
    
    return df


def generar_reporte_html(resultados: List[Dict]):
    """Genera reporte HTML con comparación visual."""
    print("\nGenerando reporte HTML...")
    
    df = pd.DataFrame(resultados)
    df = df.sort_values('silhouette', ascending=False)
    
    # Encontrar mejor modelo
    mejor_modelo = df.iloc[0]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Comparación de Modelos de Embeddings</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
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
            .badge-current {{
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
            <h1>🔬 Comparación de Modelos de Embeddings</h1>
            <p style="text-align: center; color: #7f8c8d; font-size: 18px;">
                Clustering de Dispositivos Médicos con HDBSCAN
            </p>
            
            <div class="highlight">
                <h3>🏆 Mejor Modelo Encontrado</h3>
                <p style="font-size: 18px;">
                    <strong>{mejor_modelo['modelo']}</strong>
                    <span class="badge badge-best">GANADOR</span>
                </p>
                <ul style="font-size: 16px;">
                    <li>Silhouette Score: <strong>{mejor_modelo['silhouette']:.4f}</strong></li>
                    <li>Davies-Bouldin Score: <strong>{mejor_modelo['davies_bouldin']:.4f}</strong></li>
                    <li>Clusters: <strong>{mejor_modelo['n_clusters']}</strong></li>
                    <li>Outliers: <strong>{mejor_modelo['pct_noise']:.2f}%</strong></li>
                    <li>Dimensiones: <strong>{mejor_modelo['dimensiones']}</strong></li>
                </ul>
            </div>
            
            <h2>📊 Comparación Detallada</h2>
            <table>
                <tr>
                    <th>Modelo</th>
                    <th>Dims</th>
                    <th>Clusters</th>
                    <th>Outliers</th>
                    <th>Max Size</th>
                    <th>Silhouette</th>
                    <th>Davies-B</th>
                    <th>Tiempo (s)</th>
                </tr>
    """
    
    for _, row in df.iterrows():
        clase = "winner" if row['modelo'] == mejor_modelo['modelo'] else ""
        badge = '<span class="badge badge-best">MEJOR</span>' if row['modelo'] == mejor_modelo['modelo'] else ""
        if 'actual' in row['modelo'].lower():
            badge = '<span class="badge badge-current">ACTUAL</span>'
        
        html += f"""
                <tr class="{clase}">
                    <td>{row['modelo']} {badge}</td>
                    <td>{row['dimensiones']}</td>
                    <td>{row['n_clusters']}</td>
                    <td>{row['pct_noise']:.2f}%</td>
                    <td>{row['max_cluster_size']}</td>
                    <td>{row['silhouette']:.4f}</td>
                    <td>{row['davies_bouldin']:.4f}</td>
                    <td>{row['tiempo_total']:.1f}</td>
                </tr>
        """
    
    html += """
            </table>
            
            <h2>💡 Recomendaciones</h2>
            <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                <ul style="font-size: 16px; line-height: 1.8;">
                    <li><strong>Mejor calidad:</strong> Modelo con mayor Silhouette Score</li>
                    <li><strong>Mejor velocidad:</strong> Modelo con menor tiempo total</li>
                    <li><strong>Balance:</strong> Considera calidad vs tiempo de procesamiento</li>
                    <li><strong>Producción:</strong> MPNet o E5-base son buenas opciones balanceadas</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    archivo = '../visualizaciones/comparacion_modelos_embeddings.html'
    with open(archivo, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Reporte HTML guardado: {archivo}")


if __name__ == "__main__":
    print("="*80)
    print("COMPARACIÓN DE MODELOS DE EMBEDDINGS")
    print("="*80)
    print("\nModelos a comparar:")
    for i, (nombre, modelo_id) in enumerate(MODELOS.items(), 1):
        print(f"  {i}. {nombre}")
        print(f"     {modelo_id}")
    print()
    
    # Cargar datos
    datos = cargar_datos_normalizados()
    
    # Comparar modelos
    resultados = comparar_modelos(datos)
    
    if resultados:
        # Generar tabla comparativa
        df = generar_tabla_comparativa(resultados)
        
        # Generar reporte HTML
        generar_reporte_html(resultados)
        
        print("\n" + "="*80)
        print("COMPARACIÓN COMPLETADA")
        print("="*80)
        print("\nArchivos generados:")
        print("  - ../reportes/comparacion_modelos_embeddings.csv")
        print("  - ../visualizaciones/comparacion_modelos_embeddings.html")
        print("\n💡 Revisa el reporte HTML para ver la comparación visual completa")
    else:
        print("\n⚠️  No se pudieron comparar modelos")
