#!/usr/bin/env python3
"""
Genera visualización HTML interactiva sin dependencias externas.
Usa D3.js (cargado desde CDN) para visualización.
"""
import pickle
import numpy as np
import json


def cargar_datos_clustered(archivo: str = 'dispositivos_clustered.pkl'):
    """Carga datos con clusters asignados."""
    print(f"Cargando datos desde: {archivo}")
    
    with open(archivo, 'rb') as f:
        datos = pickle.load(f)
    
    print(f"✅ Cargados {len(datos)} registros con clusters")
    return datos


def reduccion_pca_simple(embeddings: np.ndarray, n_components: int = 2):
    """
    Reducción de dimensionalidad simple usando PCA manual.
    Alternativa a UMAP cuando no está disponible.
    """
    print(f"\nReduciendo dimensionalidad con PCA...")
    print(f"  De {embeddings.shape[1]}D a {n_components}D")
    
    # Centrar datos
    mean = np.mean(embeddings, axis=0)
    centered = embeddings - mean
    
    # Calcular covarianza
    cov = np.cov(centered.T)
    
    # Eigenvalores y eigenvectores
    eigenvalues, eigenvectors = np.linalg.eig(cov)
    
    # Ordenar por eigenvalores
    idx = eigenvalues.argsort()[::-1]
    eigenvectors = eigenvectors[:, idx]
    
    # Proyectar a n_components dimensiones
    projection = centered @ eigenvectors[:, :n_components]
    
    print(f"✅ Reducción completada")
    
    return projection.real


def generar_html_interactivo(datos, coords_2d, archivo_html: str = 'visualizacion_clusters.html'):
    """Genera archivo HTML con visualización interactiva usando D3.js."""
    
    print(f"\nGenerando visualización HTML...")
    
    # Preparar datos para JavaScript
    datos_json = []
    for i, d in enumerate(datos):
        datos_json.append({
            'x': float(coords_2d[i, 0]),
            'y': float(coords_2d[i, 1]),
            'cluster': int(d['cluster_id']),
            'nombre': d['nombre_original'],
            'auditoria': d['auditoria_id'],
            'normalizado': d['nombre_normalizado']
        })
    
    # Calcular estadísticas para escala de colores
    n_clusters = len(set(d['cluster'] for d in datos_json))
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visualización de Clusters - Dispositivos Médicos</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }}
        
        #chart {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin: 0 auto;
        }}
        
        .tooltip {{
            position: absolute;
            padding: 12px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            border-radius: 6px;
            pointer-events: none;
            font-size: 13px;
            max-width: 400px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        
        .tooltip-title {{
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 14px;
            border-bottom: 1px solid rgba(255,255,255,0.3);
            padding-bottom: 6px;
        }}
        
        .tooltip-info {{
            margin: 4px 0;
            font-size: 12px;
        }}
        
        .controls {{
            text-align: center;
            margin: 20px 0;
        }}
        
        button {{
            padding: 10px 20px;
            margin: 0 5px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        button:hover {{
            background-color: #45a049;
        }}
        
        .legend {{
            text-align: center;
            margin-top: 20px;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>Visualización de Clusters de Dispositivos Médicos</h1>
    <div class="subtitle">
        Total: {len(datos_json)} dispositivos | {n_clusters} clusters | 
        Umbral de similitud: 0.98 | Reducción: PCA
    </div>
    
    <div class="controls">
        <button onclick="resetZoom()">Resetear Zoom</button>
        <button onclick="toggleLabels()">Mostrar/Ocultar Etiquetas</button>
    </div>
    
    <div id="chart"></div>
    
    <div class="legend">
        💡 Pasa el mouse sobre los puntos para ver detalles | Usa la rueda del mouse para zoom | Arrastra para mover
    </div>
    
    <script>
        // Datos
        const data = {json.dumps(datos_json, ensure_ascii=False)};
        
        // Configuración
        const width = 1200;
        const height = 800;
        const margin = {{top: 20, right: 20, bottom: 40, left: 60}};
        
        // Crear SVG
        const svg = d3.select("#chart")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        // Grupo principal con zoom
        const g = svg.append("g");
        
        // Escalas
        const xExtent = d3.extent(data, d => d.x);
        const yExtent = d3.extent(data, d => d.y);
        
        const xScale = d3.scaleLinear()
            .domain([xExtent[0] - 1, xExtent[1] + 1])
            .range([margin.left, width - margin.right]);
        
        const yScale = d3.scaleLinear()
            .domain([yExtent[0] - 1, yExtent[1] + 1])
            .range([height - margin.bottom, margin.top]);
        
        // Escala de colores
        const colorScale = d3.scaleSequential(d3.interpolateViridis)
            .domain([0, {n_clusters}]);
        
        // Ejes
        const xAxis = g.append("g")
            .attr("transform", `translate(0,${{height - margin.bottom}})`)
            .call(d3.axisBottom(xScale));
        
        const yAxis = g.append("g")
            .attr("transform", `translate(${{margin.left}},0)`)
            .call(d3.axisLeft(yScale));
        
        // Tooltip
        const tooltip = d3.select("body")
            .append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);
        
        // Puntos
        const circles = g.selectAll("circle")
            .data(data)
            .enter()
            .append("circle")
            .attr("cx", d => xScale(d.x))
            .attr("cy", d => yScale(d.y))
            .attr("r", 5)
            .attr("fill", d => colorScale(d.cluster))
            .attr("opacity", 0.7)
            .attr("stroke", "white")
            .attr("stroke-width", 1)
            .on("mouseover", function(event, d) {{
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("r", 8)
                    .attr("opacity", 1);
                
                tooltip.transition()
                    .duration(200)
                    .style("opacity", 1);
                
                tooltip.html(`
                    <div class="tooltip-title">${{d.nombre}}</div>
                    <div class="tooltip-info"><strong>Cluster:</strong> ${{d.cluster}}</div>
                    <div class="tooltip-info"><strong>Auditoría:</strong> ${{d.auditoria}}</div>
                    <div class="tooltip-info"><strong>Normalizado:</strong> ${{d.normalizado}}</div>
                `)
                    .style("left", (event.pageX + 15) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", function(d) {{
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("r", 5)
                    .attr("opacity", 0.7);
                
                tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            }});
        
        // Zoom
        const zoom = d3.zoom()
            .scaleExtent([0.5, 10])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});
        
        svg.call(zoom);
        
        // Funciones de control
        window.resetZoom = function() {{
            svg.transition()
                .duration(750)
                .call(zoom.transform, d3.zoomIdentity);
        }};
        
        let labelsVisible = false;
        window.toggleLabels = function() {{
            labelsVisible = !labelsVisible;
            // Implementar si se desea
            alert("Función de etiquetas en desarrollo");
        }};
        
        console.log("Visualización cargada:", data.length, "puntos");
    </script>
</body>
</html>"""
    
    # Guardar HTML
    with open(archivo_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Visualización HTML generada: {archivo_html}")
    print(f"   Abre el archivo en tu navegador web")
    
    return archivo_html


if __name__ == "__main__":
    print("="*80)
    print("GENERACIÓN DE VISUALIZACIÓN HTML INTERACTIVA")
    print("="*80)
    print()
    
    # 1. Cargar datos
    datos = cargar_datos_clustered()
    
    # 2. Extraer embeddings
    embeddings = np.array([d['embedding'] for d in datos])
    
    # 3. Reducir dimensionalidad con PCA
    coords_2d = reduccion_pca_simple(embeddings, n_components=2)
    
    # 4. Generar HTML
    archivo_html = generar_html_interactivo(datos, coords_2d)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print(f"\n📊 Abre el archivo en tu navegador:")
    print(f"   {archivo_html}")
    print("\n💡 Características:")
    print("   - Pasa el mouse sobre los puntos para ver el nombre del dispositivo")
    print("   - Usa la rueda del mouse para hacer zoom")
    print("   - Arrastra para mover la visualización")
