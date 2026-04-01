#!/usr/bin/env python3
"""
Creación de Base de Datos Vectorial para Dispositivos Médicos
Usa FAISS para búsqueda eficiente de similitud semántica.
"""
import pickle
import numpy as np
import json
from pathlib import Path


def cargar_embeddings(archivo: str = '../data/vectorial/dispositivos_embeddings.pkl'):
    """Carga embeddings desde archivo pickle."""
    print(f"Cargando embeddings desde: {archivo}")
    
    with open(archivo, 'rb') as f:
        datos = pickle.load(f)
    
    print(f"✅ Cargados {len(datos)} registros con embeddings")
    return datos


def crear_base_faiss(datos, archivo_indice: str = '../data/vectorial/dispositivos_faiss.index'):
    """
    Crea índice FAISS para búsqueda vectorial eficiente.
    FAISS es la biblioteca de Facebook para búsqueda de similitud.
    """
    try:
        import faiss
    except ImportError:
        print("❌ FAISS no está instalado")
        print("Instalar con: pip install faiss-cpu")
        return None
    
    print(f"\n{'='*80}")
    print("CREANDO ÍNDICE FAISS")
    print("="*80)
    
    # Extraer embeddings como matriz numpy
    embeddings = np.array([d['embedding'] for d in datos]).astype('float32')
    dimension = embeddings.shape[1]
    n_vectores = embeddings.shape[0]
    
    print(f"\nDimensión de vectores: {dimension}")
    print(f"Número de vectores: {n_vectores}")
    
    # Crear índice FAISS
    # IndexFlatL2: búsqueda exacta usando distancia L2
    print("\nCreando índice FAISS (IndexFlatL2)...")
    indice = faiss.IndexFlatL2(dimension)
    
    # Agregar vectores al índice
    indice.add(embeddings)
    
    print(f"✅ Índice creado con {indice.ntotal} vectores")
    
    # Guardar índice
    faiss.write_index(indice, archivo_indice)
    print(f"✅ Índice guardado en: {archivo_indice}")
    
    return indice


def crear_metadata(datos, archivo_metadata: str = '../data/vectorial/dispositivos_metadata.json'):
    """
    Crea archivo de metadatos para mapear índices a información de dispositivos.
    """
    print(f"\n{'='*80}")
    print("CREANDO ARCHIVO DE METADATOS")
    print("="*80)
    
    metadata = []
    for i, d in enumerate(datos):
        metadata.append({
            'id': i,
            'auditoria_id': d['auditoria_id'],
            'nombre_original': d['nombre_original'],
            'nombre_normalizado': d['nombre_normalizado']
        })
    
    with open(archivo_metadata, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Metadatos guardados en: {archivo_metadata}")
    print(f"   Total de registros: {len(metadata)}")


def buscar_similares(indice, embeddings, metadata, query_idx: int, k: int = 5):
    """
    Busca los k dispositivos más similares a un dispositivo dado.
    
    Args:
        indice: Índice FAISS
        embeddings: Matriz de embeddings
        metadata: Lista de metadatos
        query_idx: Índice del dispositivo de consulta
        k: Número de resultados a retornar
    """
    try:
        import faiss
    except ImportError:
        return None
    
    # Obtener embedding del query
    query_vector = embeddings[query_idx:query_idx+1].astype('float32')
    
    # Buscar k vecinos más cercanos
    distancias, indices = indice.search(query_vector, k)
    
    return distancias[0], indices[0]


def demo_busqueda(indice, datos):
    """Demuestra búsqueda de similitud con ejemplos."""
    try:
        import faiss
    except ImportError:
        print("\n⚠️  FAISS no disponible, saltando demo de búsqueda")
        return
    
    print(f"\n{'='*80}")
    print("DEMO: BÚSQUEDA DE DISPOSITIVOS SIMILARES")
    print("="*80)
    
    # Extraer embeddings
    embeddings = np.array([d['embedding'] for d in datos])
    
    # Buscar similares para algunos dispositivos de ejemplo
    ejemplos = [0, 10, 50, 100]
    
    for idx in ejemplos:
        if idx >= len(datos):
            continue
        
        print(f"\n{'-'*80}")
        print(f"QUERY: {datos[idx]['nombre_original']}")
        print(f"       (Auditoría: {datos[idx]['auditoria_id']})")
        print(f"{'-'*80}")
        
        distancias, indices = buscar_similares(indice, embeddings, datos, idx, k=6)
        
        print("\nDispositivos más similares:")
        for i, (dist, sim_idx) in enumerate(zip(distancias, indices)):
            if i == 0:  # Saltar el mismo dispositivo
                continue
            
            similar = datos[sim_idx]
            print(f"\n{i}. Distancia: {dist:.4f}")
            print(f"   Nombre: {similar['nombre_original']}")
            print(f"   Auditoría: {similar['auditoria_id']}")


def crear_base_chromadb(datos, nombre_coleccion: str = 'dispositivos_medicos'):
    """
    Crea base de datos vectorial usando ChromaDB (alternativa a FAISS).
    ChromaDB es más fácil de usar y tiene persistencia automática.
    """
    try:
        import chromadb
    except ImportError:
        print("\n⚠️  ChromaDB no está instalado")
        print("Instalar con: pip install chromadb")
        return None
    
    print(f"\n{'='*80}")
    print("CREANDO BASE DE DATOS CHROMADB")
    print("="*80)
    
    # Crear cliente ChromaDB con persistencia
    cliente = chromadb.PersistentClient(path="./chroma_db")
    
    # Crear o obtener colección
    try:
        coleccion = cliente.get_collection(name=nombre_coleccion)
        print(f"⚠️  Colección '{nombre_coleccion}' ya existe, eliminando...")
        cliente.delete_collection(name=nombre_coleccion)
    except:
        pass
    
    coleccion = cliente.create_collection(
        name=nombre_coleccion,
        metadata={"description": "Dispositivos médicos de auditorías"}
    )
    
    print(f"✅ Colección '{nombre_coleccion}' creada")
    
    # Preparar datos para ChromaDB
    ids = [str(i) for i in range(len(datos))]
    embeddings = [d['embedding'].tolist() for d in datos]
    documentos = [d['nombre_normalizado'] for d in datos]
    metadatas = [
        {
            'auditoria_id': d['auditoria_id'],
            'nombre_original': d['nombre_original']
        }
        for d in datos
    ]
    
    # Agregar a ChromaDB en batches
    batch_size = 100
    print(f"\nAgregando {len(datos)} vectores en batches de {batch_size}...")
    
    for i in range(0, len(datos), batch_size):
        end_idx = min(i + batch_size, len(datos))
        coleccion.add(
            ids=ids[i:end_idx],
            embeddings=embeddings[i:end_idx],
            documents=documentos[i:end_idx],
            metadatas=metadatas[i:end_idx]
        )
        if (i // batch_size + 1) % 5 == 0:
            print(f"  Procesados {end_idx}/{len(datos)} vectores...")
    
    print(f"\n✅ Base de datos ChromaDB creada")
    print(f"   Ubicación: ./chroma_db")
    print(f"   Colección: {nombre_coleccion}")
    print(f"   Total de vectores: {coleccion.count()}")
    
    return coleccion


if __name__ == "__main__":
    print("="*80)
    print("CREACIÓN DE BASE DE DATOS VECTORIAL")
    print("="*80)
    print("\nOpciones: FAISS (Facebook) y ChromaDB\n")
    
    # 1. Cargar embeddings
    datos = cargar_embeddings()
    
    # 2. Crear índice FAISS
    indice_faiss = crear_base_faiss(datos)
    
    # 3. Crear archivo de metadatos
    crear_metadata(datos)
    
    # 4. Demo de búsqueda con FAISS
    if indice_faiss is not None:
        demo_busqueda(indice_faiss, datos)
    
    # 5. Crear base ChromaDB (alternativa)
    print("\n" + "="*80)
    coleccion_chroma = crear_base_chromadb(datos)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivos generados:")
    print("  - dispositivos_faiss.index (índice FAISS)")
    print("  - dispositivos_metadata.json (metadatos)")
    print("  - ./chroma_db/ (base de datos ChromaDB)")
    print("\nUso:")
    print("  - FAISS: Búsqueda vectorial ultra-rápida")
    print("  - ChromaDB: Base de datos vectorial con persistencia")
