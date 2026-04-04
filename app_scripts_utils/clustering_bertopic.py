#!/usr/bin/env python3
"""
Clustering con BERTopic - Etiquetado Automático
Genera etiquetas descriptivas para cada cluster usando BERTopic.
Usa la configuración óptima de HDBSCAN encontrada por grid search.
"""
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
import hdbscan


def cargar_datos_hdbscan(archivo: str = '../data/vectorial/dispositivos_hdbscan_optimal.pkl'):
    """Carga datos con clusters HDBSCAN óptimos asignados."""
    print(f"Cargando datos desde: {archivo}")
    
    with open(archivo, 'rb') as f:
        resultado = pickle.load(f)
    
    datos = resultado['datos']
    estadisticas = resultado['estadisticas']
    
    print(f"✅ Cargados {len(datos)} registros")
    print(f"   Clusters: {estadisticas['n_clusters']}")
    print(f"   Outliers: {estadisticas['n_noise']} ({estadisticas['pct_noise']:.2f}%)")
    print(f"   Silhouette: {estadisticas.get('silhouette_score', 'N/A')}")
    print(f"   Score compuesto: {estadisticas.get('score_compuesto', 'N/A')}")
    
    return datos, estadisticas


def preparar_documentos(datos: List[Dict]):
    """Prepara documentos y embeddings para BERTopic."""
    print("\nPreparando documentos...")
    
    # Usar nombres normalizados como documentos
    documentos = [d['nombre_normalizado'] for d in datos]
    embeddings = np.array([d['embedding'] for d in datos])
    clusters = [d['cluster_id'] for d in datos]
    
    print(f"✅ {len(documentos)} documentos preparados")
    
    return documentos, embeddings, clusters


def crear_bertopic_model():
    """Crea modelo BERTopic con componentes personalizados."""
    print("\nCreando modelo BERTopic...")
    
    # Usar el mismo modelo de embeddings que ya tenemos
    embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    # UMAP para reducción dimensional
    umap_model = UMAP(
        n_components=5,
        n_neighbors=15,
        min_dist=0.0,
        metric='cosine',
        random_state=42
    )
    
    # HDBSCAN para clustering (usar configuración óptima)
    hdbscan_model = hdbscan.HDBSCAN(
        min_cluster_size=7,
        min_samples=5,
        metric='euclidean',
        cluster_selection_method='eom',
        prediction_data=True
    )
    
    # CountVectorizer para extraer palabras clave en español
    vectorizer_model = CountVectorizer(
        ngram_range=(1, 2),
        stop_words=None,  # No usar stop words para mantener términos médicos
        min_df=1
    )
    
    # Crear modelo BERTopic
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        language='multilingual',
        calculate_probabilities=True,
        verbose=True,
        nr_topics='auto'
    )
    
    print("✅ Modelo BERTopic creado")
    
    return topic_model


def generar_etiquetas_clusters(datos: List[Dict], documentos: List[str], embeddings: np.ndarray):
    """Genera etiquetas descriptivas para cada cluster usando BERTopic."""
    print(f"\n{'='*80}")
    print("GENERACIÓN DE ETIQUETAS CON BERTOPIC")
    print("="*80)
    
    # Crear modelo
    topic_model = crear_bertopic_model()
    
    # Entrenar modelo
    print("\nEntrenando BERTopic...")
    topics, probs = topic_model.fit_transform(documentos, embeddings)
    
    # Obtener información de topics
    topic_info = topic_model.get_topic_info()
    
    print(f"\n✅ BERTopic entrenado")
    print(f"   Topics detectados: {len(topic_info) - 1}")  # -1 porque incluye outliers
    
    # Generar etiquetas personalizadas
    print("\nGenerando etiquetas descriptivas...")
    
    etiquetas_clusters = {}
    
    for topic_id in topic_info['Topic']:
        if topic_id == -1:
            etiquetas_clusters[topic_id] = "Outliers / Dispositivos Únicos"
            continue
        
        # Obtener palabras clave del topic
        palabras = topic_model.get_topic(topic_id)
        
        if palabras:
            # Tomar las 3 palabras más importantes
            top_words = [word for word, score in palabras[:3]]
            etiqueta = " + ".join(top_words)
            etiquetas_clusters[topic_id] = etiqueta
            
            # Contar documentos en este topic
            count = len([t for t in topics if t == topic_id])
            
            print(f"  Topic {topic_id}: {etiqueta} ({count} dispositivos)")
    
    return topic_model, topics, etiquetas_clusters


def asignar_etiquetas_a_datos(datos: List[Dict], topics: List[int], etiquetas_clusters: Dict):
    """Asigna etiquetas generadas a los datos originales."""
    print(f"\n{'='*80}")
    print("ASIGNACIÓN DE ETIQUETAS A CLUSTERS")
    print("="*80)
    
    datos_con_etiquetas = []
    for i, d in enumerate(datos):
        topic_id = topics[i]
        etiqueta = etiquetas_clusters.get(topic_id, "Sin etiqueta")
        
        datos_con_etiquetas.append({
            'auditoria_id': d['auditoria_id'],
            'nombre_original': d['nombre_original'],
            'nombre_normalizado': d['nombre_normalizado'],
            'cluster_id': d['cluster_id'],
            'topic_id': topic_id,
            'etiqueta_cluster': etiqueta,
            'es_ruido': d['es_ruido']
        })
    
    print(f"✅ Etiquetas asignadas a {len(datos_con_etiquetas)} dispositivos")
    
    return datos_con_etiquetas


def analizar_clusters_etiquetados(datos_con_etiquetas: List[Dict]):
    """Analiza y muestra clusters con sus etiquetas."""
    print(f"\n{'='*80}")
    print("ANÁLISIS DE CLUSTERS ETIQUETADOS")
    print("="*80)
    
    # Agrupar por etiqueta
    clusters_por_etiqueta = {}
    for d in datos_con_etiquetas:
        etiqueta = d['etiqueta_cluster']
        if etiqueta not in clusters_por_etiqueta:
            clusters_por_etiqueta[etiqueta] = []
        clusters_por_etiqueta[etiqueta].append(d)
    
    # Ordenar por tamaño
    clusters_ordenados = sorted(clusters_por_etiqueta.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"\nTotal de etiquetas únicas: {len(clusters_ordenados)}")
    print(f"\n{'='*80}")
    print("TOP 20 CATEGORÍAS DE DISPOSITIVOS")
    print("="*80)
    
    for i, (etiqueta, dispositivos) in enumerate(clusters_ordenados[:20], 1):
        print(f"\n{i}. {etiqueta.upper()}")
        print(f"   Cantidad: {len(dispositivos)} dispositivos")
        print(f"   Ejemplos:")
        for d in dispositivos[:3]:
            print(f"     - {d['nombre_original'][:70]}")


def guardar_resultados(
    datos_con_etiquetas: List[Dict],
    topic_model: BERTopic,
    archivo_csv: str = '../reportes/dispositivos_bertopic_etiquetados.csv',
    archivo_pkl: str = '../data/vectorial/dispositivos_bertopic.pkl',
    archivo_modelo: str = '../data/vectorial/bertopic_model'
):
    """Guarda resultados con etiquetas."""
    print(f"\n{'='*80}")
    print("GUARDANDO RESULTADOS")
    print("="*80)
    
    # Guardar CSV
    df = pd.DataFrame(datos_con_etiquetas)
    df.to_csv(archivo_csv, index=False, encoding='utf-8')
    print(f"✅ CSV guardado: {archivo_csv}")
    
    # Guardar pickle
    with open(archivo_pkl, 'wb') as f:
        pickle.dump(datos_con_etiquetas, f)
    print(f"✅ Pickle guardado: {archivo_pkl}")
    
    # Guardar modelo BERTopic
    try:
        topic_model.save(archivo_modelo, serialization="safetensors", save_ctfidf=True, save_embedding_model=embedding_model)
        print(f"✅ Modelo BERTopic guardado: {archivo_modelo}")
    except Exception as e:
        print(f"⚠️  No se pudo guardar el modelo completo: {e}")
        print(f"   Los resultados CSV y pickle están disponibles")


def generar_clasificador_html(datos_con_etiquetas: List[Dict]):
    """Genera HTML interactivo con clasificador de dispositivos."""
    print("\nGenerando clasificador HTML...")
    
    # Agrupar por etiqueta
    clusters_por_etiqueta = {}
    for d in datos_con_etiquetas:
        etiqueta = d['etiqueta_cluster']
        if etiqueta not in clusters_por_etiqueta:
            clusters_por_etiqueta[etiqueta] = []
        clusters_por_etiqueta[etiqueta].append(d)
    
    # Ordenar por tamaño
    clusters_ordenados = sorted(clusters_por_etiqueta.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Contar outliers
    n_outliers = sum(1 for d in datos_con_etiquetas if d['es_ruido'])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Clasificador Automático de Dispositivos Médicos</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
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
                margin-bottom: 10px;
            }}
            .subtitle {{
                text-align: center;
                color: #7f8c8d;
                font-size: 18px;
                margin-bottom: 40px;
            }}
            .search-box {{
                margin: 30px 0;
                text-align: center;
            }}
            .search-box input {{
                width: 60%;
                padding: 15px;
                font-size: 16px;
                border: 2px solid #667eea;
                border-radius: 25px;
                outline: none;
            }}
            .category {{
                margin: 20px 0;
                padding: 20px;
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-left: 5px solid #667eea;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s;
            }}
            .category:hover {{
                transform: translateX(10px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            .category-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .category-title {{
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .category-count {{
                background-color: #667eea;
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
            }}
            .devices {{
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #dee2e6;
                display: none;
            }}
            .device-item {{
                padding: 8px;
                margin: 5px 0;
                background-color: white;
                border-radius: 5px;
                font-size: 14px;
                color: #495057;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 10px;
                text-align: center;
            }}
            .stat-number {{
                font-size: 36px;
                font-weight: bold;
            }}
            .stat-label {{
                font-size: 14px;
                margin-top: 5px;
            }}
            .badge {{
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
                margin-left: 10px;
            }}
            .badge-optimal {{
                background-color: #28a745;
                color: white;
            }}
        </style>
        <script>
            function toggleDevices(id) {{
                var element = document.getElementById('devices-' + id);
                if (element.style.display === 'none' || element.style.display === '') {{
                    element.style.display = 'block';
                }} else {{
                    element.style.display = 'none';
                }}
            }}
            
            function searchCategories() {{
                var input = document.getElementById('searchInput');
                var filter = input.value.toUpperCase();
                var categories = document.getElementsByClassName('category');
                
                for (var i = 0; i < categories.length; i++) {{
                    var title = categories[i].getElementsByClassName('category-title')[0];
                    var txtValue = title.textContent || title.innerText;
                    if (txtValue.toUpperCase().indexOf(filter) > -1) {{
                        categories[i].style.display = '';
                    }} else {{
                        categories[i].style.display = 'none';
                    }}
                }}
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🏥 Clasificador Automático de Dispositivos Médicos</h1>
            <p class="subtitle">
                Powered by BERTopic + HDBSCAN Óptimo 
                <span class="badge badge-optimal">Configuración Óptima</span>
            </p>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{len(datos_con_etiquetas)}</div>
                    <div class="stat-label">Total Dispositivos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(clusters_ordenados)}</div>
                    <div class="stat-label">Categorías Detectadas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{n_outliers}</div>
                    <div class="stat-label">Outliers (7.84%)</div>
                </div>
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" onkeyup="searchCategories()" 
                       placeholder="Buscar categoría... (ej: jeringa, cateter, equipo, tornillo)">
            </div>
            
            <h2 style="color: #2c3e50; margin-top: 40px;">📋 Categorías de Dispositivos</h2>
    """
    
    for i, (etiqueta, dispositivos) in enumerate(clusters_ordenados):
        html += f"""
            <div class="category" onclick="toggleDevices({i})">
                <div class="category-header">
                    <div class="category-title">{etiqueta.upper()}</div>
                    <div class="category-count">{len(dispositivos)} dispositivos</div>
                </div>
                <div class="devices" id="devices-{i}">
        """
        
        for d in dispositivos[:30]:  # Mostrar máximo 30 ejemplos
            html += f"""
                    <div class="device-item">
                        • {d['nombre_original']} <span style="color: #6c757d;">(Auditoría: {d['auditoria_id']})</span>
                    </div>
            """
        
        if len(dispositivos) > 30:
            html += f"""
                    <div class="device-item" style="font-style: italic; color: #6c757d;">
                        ... y {len(dispositivos) - 30} dispositivos más
                    </div>
            """
        
        html += """
                </div>
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    archivo = '../visualizaciones/clasificador_dispositivos_medicos.html'
    with open(archivo, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Clasificador HTML guardado: {archivo}")


if __name__ == "__main__":
    print("="*80)
    print("CLUSTERING CON BERTOPIC - ETIQUETADO AUTOMÁTICO")
    print("="*80)
    print("\nUsando configuración óptima de HDBSCAN:")
    print("  ✓ min_cluster_size: 7")
    print("  ✓ min_samples: 5")
    print("  ✓ 77 clusters detectados")
    print("  ✓ 7.84% outliers")
    print("  ✓ Silhouette: 0.8007")
    print()
    
    # 1. Cargar datos con clusters óptimos
    datos, estadisticas = cargar_datos_hdbscan()
    
    # 2. Preparar documentos
    documentos, embeddings, clusters = preparar_documentos(datos)
    
    # 3. Generar etiquetas con BERTopic
    topic_model, topics, etiquetas_clusters = generar_etiquetas_clusters(datos, documentos, embeddings)
    
    # 4. Asignar etiquetas a datos
    datos_con_etiquetas = asignar_etiquetas_a_datos(datos, topics, etiquetas_clusters)
    
    # 5. Analizar clusters etiquetados
    analizar_clusters_etiquetados(datos_con_etiquetas)
    
    # 6. Guardar resultados
    guardar_resultados(datos_con_etiquetas, topic_model)
    
    # 7. Generar clasificador HTML
    generar_clasificador_html(datos_con_etiquetas)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivos generados:")
    print("  - ../reportes/dispositivos_bertopic_etiquetados.csv")
    print("  - ../data/vectorial/dispositivos_bertopic.pkl")
    print("  - ../visualizaciones/clasificador_dispositivos_medicos.html")
    print("\n💡 Ahora tienes un clasificador automático de dispositivos médicos")
    print("   basado en la configuración óptima de HDBSCAN!")
    print("   Abre el archivo HTML para explorar las categorías detectadas.")
