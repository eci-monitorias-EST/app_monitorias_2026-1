#!/usr/bin/env python3
"""
Genera tabla de conteos y estadísticas de clusters
"""
import pickle
import pandas as pd
from collections import Counter


def cargar_datos_clustered(archivo: str = '../data/vectorial/dispositivos_clustered.pkl'):
    """Carga datos con clusters asignados."""
    print(f"Cargando datos desde: {archivo}")
    
    with open(archivo, 'rb') as f:
        datos = pickle.load(f)
    
    print(f"✅ Cargados {len(datos)} registros con clusters")
    return datos


def generar_tabla_conteos_clusters(datos):
    """Genera tabla de conteos por cluster."""
    print("\nGenerando tabla de conteos por cluster...")
    
    # Agrupar por cluster
    clusters_dict = {}
    for d in datos:
        cid = d['cluster_id']
        if cid not in clusters_dict:
            clusters_dict[cid] = []
        clusters_dict[cid].append(d)
    
    # Crear lista de registros para el DataFrame
    registros = []
    for cluster_id, dispositivos in clusters_dict.items():
        # Obtener auditorías únicas en este cluster
        auditorias_unicas = set(d['auditoria_id'] for d in dispositivos)
        
        # Obtener ejemplo de nombre
        ejemplo_nombre = dispositivos[0]['nombre_original']
        
        registros.append({
            'cluster_id': cluster_id,
            'cantidad_dispositivos': len(dispositivos),
            'cantidad_auditorias': len(auditorias_unicas),
            'ejemplo_dispositivo': ejemplo_nombre
        })
    
    # Crear DataFrame
    df = pd.DataFrame(registros)
    
    # Ordenar por cantidad de dispositivos (descendente)
    df = df.sort_values('cantidad_dispositivos', ascending=False).reset_index(drop=True)
    
    print(f"✅ Tabla generada con {len(df)} clusters")
    
    return df


def generar_tabla_conteos_auditorias(datos):
    """Genera tabla de conteos por auditoría."""
    print("\nGenerando tabla de conteos por auditoría...")
    
    # Agrupar por auditoría
    auditorias_dict = {}
    for d in datos:
        aid = d['auditoria_id']
        if aid not in auditorias_dict:
            auditorias_dict[aid] = []
        auditorias_dict[aid].append(d)
    
    # Crear lista de registros para el DataFrame
    registros = []
    for auditoria_id, dispositivos in auditorias_dict.items():
        # Obtener clusters únicos en esta auditoría
        clusters_unicos = set(d['cluster_id'] for d in dispositivos)
        
        registros.append({
            'auditoria_id': auditoria_id,
            'cantidad_dispositivos': len(dispositivos),
            'cantidad_clusters': len(clusters_unicos)
        })
    
    # Crear DataFrame
    df = pd.DataFrame(registros)
    
    # Ordenar por cantidad de dispositivos (descendente)
    df = df.sort_values('cantidad_dispositivos', ascending=False).reset_index(drop=True)
    
    print(f"✅ Tabla generada con {len(df)} auditorías")
    
    return df


def generar_tabla_resumen_general(datos):
    """Genera tabla resumen general."""
    print("\nGenerando tabla resumen general...")
    
    # Calcular estadísticas
    total_dispositivos = len(datos)
    total_clusters = len(set(d['cluster_id'] for d in datos))
    total_auditorias = len(set(d['auditoria_id'] for d in datos))
    
    # Conteo de dispositivos por cluster
    cluster_counts = Counter(d['cluster_id'] for d in datos)
    promedio_dispositivos_por_cluster = sum(cluster_counts.values()) / len(cluster_counts)
    max_dispositivos_cluster = max(cluster_counts.values())
    min_dispositivos_cluster = min(cluster_counts.values())
    
    # Conteo de dispositivos por auditoría
    auditoria_counts = Counter(d['auditoria_id'] for d in datos)
    promedio_dispositivos_por_auditoria = sum(auditoria_counts.values()) / len(auditoria_counts)
    
    # Crear DataFrame resumen
    resumen = {
        'metrica': [
            'Total Dispositivos',
            'Total Clusters',
            'Total Auditorías',
            'Promedio Dispositivos por Cluster',
            'Máximo Dispositivos en un Cluster',
            'Mínimo Dispositivos en un Cluster',
            'Promedio Dispositivos por Auditoría'
        ],
        'valor': [
            total_dispositivos,
            total_clusters,
            total_auditorias,
            round(promedio_dispositivos_por_cluster, 2),
            max_dispositivos_cluster,
            min_dispositivos_cluster,
            round(promedio_dispositivos_por_auditoria, 2)
        ]
    }
    
    df = pd.DataFrame(resumen)
    
    print(f"✅ Tabla resumen generada")
    
    return df


def generar_tabla_cluster_detallado(datos):
    """Genera tabla detallada con todos los dispositivos por cluster."""
    print("\nGenerando tabla detallada de dispositivos...")
    
    registros = []
    for d in datos:
        registros.append({
            'cluster_id': d['cluster_id'],
            'auditoria_id': d['auditoria_id'],
            'nombre_original': d['nombre_original'],
            'nombre_normalizado': d['nombre_normalizado']
        })
    
    df = pd.DataFrame(registros)
    
    # Ordenar por cluster y auditoría
    df = df.sort_values(['cluster_id', 'auditoria_id']).reset_index(drop=True)
    
    print(f"✅ Tabla detallada generada con {len(df)} registros")
    
    return df


if __name__ == "__main__":
    print("="*80)
    print("GENERACIÓN DE TABLAS DE CONTEOS Y ESTADÍSTICAS")
    print("="*80)
    print()
    
    # Cargar datos
    datos = cargar_datos_clustered()
    
    # 1. Tabla de conteos por cluster
    df_clusters = generar_tabla_conteos_clusters(datos)
    archivo_clusters = '../reportes/conteos_por_cluster.csv'
    df_clusters.to_csv(archivo_clusters, index=False, encoding='utf-8')
    print(f"✅ Guardado: {archivo_clusters}")
    print(f"\nPrimeras 10 filas:")
    print(df_clusters.head(10))
    
    # 2. Tabla de conteos por auditoría
    df_auditorias = generar_tabla_conteos_auditorias(datos)
    archivo_auditorias = '../reportes/conteos_por_auditoria.csv'
    df_auditorias.to_csv(archivo_auditorias, index=False, encoding='utf-8')
    print(f"\n✅ Guardado: {archivo_auditorias}")
    print(f"\nPrimeras 10 filas:")
    print(df_auditorias.head(10))
    
    # 3. Tabla resumen general
    df_resumen = generar_tabla_resumen_general(datos)
    archivo_resumen = '../reportes/resumen_general.csv'
    df_resumen.to_csv(archivo_resumen, index=False, encoding='utf-8')
    print(f"\n✅ Guardado: {archivo_resumen}")
    print(f"\nResumen:")
    print(df_resumen)
    
    # 4. Tabla detallada completa
    df_detallado = generar_tabla_cluster_detallado(datos)
    archivo_detallado = '../reportes/dispositivos_detallado.csv'
    df_detallado.to_csv(archivo_detallado, index=False, encoding='utf-8')
    print(f"\n✅ Guardado: {archivo_detallado}")
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivos CSV generados:")
    print(f"  1. {archivo_clusters} - Conteos por cluster")
    print(f"  2. {archivo_auditorias} - Conteos por auditoría")
    print(f"  3. {archivo_resumen} - Resumen general de estadísticas")
    print(f"  4. {archivo_detallado} - Listado completo de dispositivos")
