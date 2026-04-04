#!/usr/bin/env python3
"""
Extractor de Dispositivos Médicos de Auditorías
Genera CSV donde cada fila es un dispositivo médico individual.
Formato: auditoria_id, nombre_dispositivo
"""
import json
import csv
from pathlib import Path
from typing import List, Dict


def extraer_dispositivos_individuales(base_path: str = '../../ejercicios_auditoria') -> List[Dict]:
    """
    Extrae dispositivos médicos individuales de todas las auditorías.
    Cada dispositivo es un registro separado en el resultado.
    """
    base = Path(base_path)
    
    # Buscar todos los archivos clasificados
    archivos = list(base.glob('*/300 Identificacion de Conceptos/003 CONCEPTOS FACTURA CLASIFICADOS.json'))
    
    print(f"Encontrados {len(archivos)} archivos de auditorías\n")
    
    dispositivos_individuales = []
    auditorias_procesadas = 0
    
    for archivo in archivos:
        # Extraer ID de auditoría (ej: 000002_19307914)
        # El path es: ejercicios_auditoria/000002_19307914/300.../003...
        partes = archivo.parts
        auditoria_id = partes[partes.index('ejercicios_auditoria') + 1]
        
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            dispositivos_en_auditoria = 0
            
            for item in data.get('conceptos', []):
                componente = item.get('componente_medico', '')
                
                # Filtrar solo dispositivos médicos
                if componente.startswith('DispositivosMedicos'):
                    nombre = item.get('nombre', '').strip()
                    if nombre:
                        dispositivos_individuales.append({
                            'auditoria_id': auditoria_id,
                            'nombre_dispositivo': nombre
                        })
                        dispositivos_en_auditoria += 1
            
            auditorias_procesadas += 1
            
            if auditorias_procesadas % 10 == 0:
                print(f"Procesadas {auditorias_procesadas} auditorías, {len(dispositivos_individuales)} dispositivos extraídos...")
        
        except Exception as e:
            print(f"Error procesando {auditoria_id}: {e}")
    
    return dispositivos_individuales


def mostrar_estadisticas(dispositivos: List[Dict]):
    """Muestra estadísticas de los dispositivos extraídos."""
    print("\n" + "="*80)
    print("ESTADÍSTICAS DE DISPOSITIVOS MÉDICOS")
    print("="*80)
    
    # Contar auditorías únicas
    auditorias_unicas = set(d['auditoria_id'] for d in dispositivos)
    
    # Contar dispositivos por auditoría
    dispositivos_por_auditoria = {}
    for d in dispositivos:
        aid = d['auditoria_id']
        dispositivos_por_auditoria[aid] = dispositivos_por_auditoria.get(aid, 0) + 1
    
    print(f"\nTotal de registros (dispositivos): {len(dispositivos)}")
    print(f"Total de auditorías: {len(auditorias_unicas)}")
    print(f"Promedio de dispositivos por auditoría: {len(dispositivos) / len(auditorias_unicas):.2f}")
    
    # Top 10 auditorías con más dispositivos
    top_auditorias = sorted(dispositivos_por_auditoria.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print(f"\n{'='*80}")
    print("TOP 10 AUDITORÍAS CON MÁS DISPOSITIVOS")
    print("="*80)
    print(f"{'Auditoría':<25} {'N° Dispositivos':<15}")
    print("-"*40)
    
    for auditoria_id, count in top_auditorias:
        print(f"{auditoria_id:<25} {count:<15}")
    
    # Mostrar primeros 5 registros como ejemplo
    print(f"\n{'='*80}")
    print("PRIMEROS 5 REGISTROS (EJEMPLO)")
    print("="*80)
    print(f"{'Auditoría':<25} {'Dispositivo':<55}")
    print("-"*80)
    
    for d in dispositivos[:5]:
        nombre_corto = d['nombre_dispositivo'][:52] + "..." if len(d['nombre_dispositivo']) > 52 else d['nombre_dispositivo']
        print(f"{d['auditoria_id']:<25} {nombre_corto:<55}")


def exportar_csv(dispositivos: List[Dict], nombre_archivo: str = '../data/processed/dispositivos_medicos.csv'):
    """Exporta los dispositivos a CSV."""
    with open(nombre_archivo, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['auditoria_id', 'nombre_dispositivo'])
        
        for d in dispositivos:
            writer.writerow([d['auditoria_id'], d['nombre_dispositivo']])
    
    print(f"\n✅ Exportado a: {nombre_archivo}")
    print(f"   Total de filas: {len(dispositivos)}")


if __name__ == "__main__":
    print("="*80)
    print("EXTRACCIÓN DE DISPOSITIVOS MÉDICOS INDIVIDUALES")
    print("="*80)
    print("Cada fila del CSV = 1 dispositivo médico\n")
    
    # Extraer dispositivos individuales
    dispositivos = extraer_dispositivos_individuales()
    
    # Mostrar estadísticas
    mostrar_estadisticas(dispositivos)
    
    # Exportar a CSV
    exportar_csv(dispositivos)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
