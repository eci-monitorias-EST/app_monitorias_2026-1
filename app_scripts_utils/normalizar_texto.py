#!/usr/bin/env python3
"""
Normalización y Limpieza de Texto para Dispositivos Médicos
Preprocesa los nombres de dispositivos para clustering semántico.
"""
import csv
import re
import unicodedata
from typing import List, Dict


def normalizar_texto(texto: str) -> str:
    """
    Normaliza y limpia texto de dispositivos médicos.
    
    Pasos:
    1. Convertir a minúsculas
    2. Remover acentos y diacríticos
    3. Normalizar espacios múltiples
    4. Remover caracteres especiales (mantener letras, números, espacios)
    5. Remover stopwords médicas comunes
    6. Normalizar unidades de medida
    """
    if not texto:
        return ""
    
    # 1. Convertir a minúsculas
    texto = texto.lower()
    
    # 2. Remover acentos y diacríticos
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    
    # 3. Normalizar unidades de medida comunes
    # ml, cc, mg, g, etc.
    texto = re.sub(r'\bml\b', 'mililitros', texto)
    texto = re.sub(r'\bc\.?c\.?\b', 'centimetros cubicos', texto)
    texto = re.sub(r'\bmg\b', 'miligramos', texto)
    texto = re.sub(r'\b(\d+)\s*x\s*(\d+)', r'\1 por \2', texto)  # 10 x 5 -> 10 por 5
    
    # 4. Remover caracteres especiales (mantener letras, números, espacios)
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    
    # 5. Normalizar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto)
    
    # 6. Remover stopwords médicas comunes (opcional)
    stopwords = {'de', 'del', 'la', 'el', 'los', 'las', 'para', 'con', 'sin', 'por'}
    palabras = texto.split()
    palabras_filtradas = [p for p in palabras if p not in stopwords or len(palabras) <= 3]
    texto = ' '.join(palabras_filtradas)
    
    # 7. Trim
    texto = texto.strip()
    
    return texto


def procesar_csv(
    archivo_entrada: str = '../data/processed/dispositivos_medicos.csv',
    archivo_salida: str = '../data/processed/dispositivos_medicos_normalizado.csv'
) -> List[Dict]:
    """
    Procesa el CSV de dispositivos y genera versión normalizada.
    
    Returns:
        Lista de diccionarios con datos procesados
    """
    datos_procesados = []
    
    print(f"Leyendo archivo: {archivo_entrada}")
    
    with open(archivo_entrada, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            auditoria_id = row['auditoria_id']
            nombre_original = row['nombre_dispositivo']
            nombre_normalizado = normalizar_texto(nombre_original)
            
            datos_procesados.append({
                'auditoria_id': auditoria_id,
                'nombre_original': nombre_original,
                'nombre_normalizado': nombre_normalizado
            })
    
    print(f"Total de registros procesados: {len(datos_procesados)}")
    
    # Guardar CSV normalizado
    with open(archivo_salida, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['auditoria_id', 'nombre_original', 'nombre_normalizado'])
        
        for d in datos_procesados:
            writer.writerow([
                d['auditoria_id'],
                d['nombre_original'],
                d['nombre_normalizado']
            ])
    
    print(f"✅ Archivo normalizado guardado: {archivo_salida}")
    
    return datos_procesados


def mostrar_ejemplos(datos: List[Dict], n: int = 10):
    """Muestra ejemplos de normalización."""
    print("\n" + "="*100)
    print("EJEMPLOS DE NORMALIZACIÓN")
    print("="*100)
    print(f"{'Original':<50} {'Normalizado':<50}")
    print("-"*100)
    
    for d in datos[:n]:
        original = d['nombre_original'][:47] + "..." if len(d['nombre_original']) > 47 else d['nombre_original']
        normalizado = d['nombre_normalizado'][:47] + "..." if len(d['nombre_normalizado']) > 47 else d['nombre_normalizado']
        print(f"{original:<50} {normalizado:<50}")


def analizar_normalizacion(datos: List[Dict]):
    """Analiza estadísticas de la normalización."""
    print("\n" + "="*80)
    print("ESTADÍSTICAS DE NORMALIZACIÓN")
    print("="*80)
    
    # Longitud promedio antes y después
    long_original = sum(len(d['nombre_original']) for d in datos) / len(datos)
    long_normalizado = sum(len(d['nombre_normalizado']) for d in datos) / len(datos)
    
    print(f"\nLongitud promedio original: {long_original:.2f} caracteres")
    print(f"Longitud promedio normalizado: {long_normalizado:.2f} caracteres")
    print(f"Reducción: {((long_original - long_normalizado) / long_original * 100):.2f}%")
    
    # Contar textos vacíos después de normalización
    vacios = sum(1 for d in datos if not d['nombre_normalizado'])
    print(f"\nTextos vacíos después de normalización: {vacios}")
    
    # Contar dispositivos únicos
    originales_unicos = len(set(d['nombre_original'] for d in datos))
    normalizados_unicos = len(set(d['nombre_normalizado'] for d in datos if d['nombre_normalizado']))
    
    print(f"\nDispositivos únicos (original): {originales_unicos}")
    print(f"Dispositivos únicos (normalizado): {normalizados_unicos}")
    print(f"Reducción de variantes: {originales_unicos - normalizados_unicos}")


if __name__ == "__main__":
    print("="*80)
    print("NORMALIZACIÓN DE TEXTO - DISPOSITIVOS MÉDICOS")
    print("="*80)
    print()
    
    # Procesar CSV
    datos = procesar_csv()
    
    # Mostrar ejemplos
    mostrar_ejemplos(datos, n=15)
    
    # Analizar normalización
    analizar_normalizacion(datos)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print("\nArchivo generado: dispositivos_medicos_normalizado.csv")
    print("Columnas: auditoria_id, nombre_original, nombre_normalizado")
