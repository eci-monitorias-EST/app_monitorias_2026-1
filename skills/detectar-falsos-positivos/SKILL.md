---
name: detectar-falsos-positivos
description: >
  Evalúa si un hallazgo corresponde a un falso positivo, un error válido,
  un caso ambiguo o ruido no material. Trigger: cuando un pipeline produzca
  hallazgos con posible contradicción entre inputs, matching, threshold,
  clasificación o explicación.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Cuando un flujo de analítica o predicción marque un hallazgo sospechoso.
- Cuando haya dudas sobre la semántica de la clase positiva o el threshold.
- Cuando inputs, metadata y output del modelo no estén alineados.
- Cuando haya que distinguir señal real de ruido antes de decidir.

## Critical Patterns

- Nunca decidas antes de validar estructura y contexto.
- Nunca trates texto no vacío como evidencia suficiente.
- Nunca interpretes `predict_proba[:, 1]` sin mapear explícitamente la clase positiva.
- Separá validación, matching, materialidad y decisión final.
- La explicación no reemplaza validación; solo justifica una decisión ya validada.

## Inputs esperados

```yaml
hallazgo:
  id: string
  tipo: string
  origen: string
  ejercicio: string

contexto:
  participant_id: string
  exercise_id: string
  timestamp: string
  estado_previo: object | null

raw_inputs:
  comentarios:
    dataset_comment: string | null
    analytics_comment: string | null
    prediction_reflection: string | null
  prediction_inputs: object | null
  prediction_output: object | null

metadata:
  required_fields: string[]
  feature_schema:
    nombre: string
    tipo_esperado: string
  positive_class_definition: string | null
  threshold: number | null

evidencia_modelo:
  probability: number | null
  predicted_label: string | null
  positive_class: string | null
  explanation_items: array | null
```

## Outputs

```yaml
clasificacion_final:
  estado: valid_error | falso_positivo | ambiguo | ruido_no_material | invalido
  decision: string
  justificacion: string
  evidencia_usada: string[]
  evidencia_descartada: string[]
  alertas: string[]
```

## Internal Logic

1. **Validar contexto**
   - Confirmar que el hallazgo pertenece al ejercicio correcto.
   - Marcar como `invalido` si hay contradicción de contexto.

2. **Validar estructura**
   - Verificar required fields, tipos y comentarios mínimamente desarrollados.
   - Rechazar placeholders como `n/a`, `ok`, `ninguno`, `...`.

3. **Normalizar evidencia**
   - Canonicalizar nombres de variables.
   - Coaccionar tipos y separar texto crudo de texto interpretable.

4. **Verificar matching**
   - Confirmar que las features existen y coinciden con el esquema esperado.
   - Verificar consistencia entre metadata, clase positiva y etiqueta mostrada.

5. **Filtrar ruido**
   - Descartar texto genérico, defaults no intervenidos y explicaciones duplicadas.
   - Conservar solo evidencia material para decidir.

6. **Validar threshold e interpretación**
   - Si no hay threshold o clase positiva explícita, clasificar como `ambiguo`.
   - Si la semántica contradice la etiqueta final, clasificar como `falso_positivo`.

7. **Emitir clasificación final**
   - `valid_error`: hay evidencia consistente de error real.
   - `falso_positivo`: el hallazgo está mal interpretado o mal soportado.
   - `ambiguo`: falta evidencia crítica para decidir.
   - `ruido_no_material`: hay datos, pero no son relevantes.
   - `invalido`: el input no supera validación estructural.

## Edge Cases

- Contradicción entre `selected_exercise` y el ejercicio del hallazgo.
- Clase positiva invertida respecto de la etiqueta mostrada.
- Threshold duro sin justificación para un problema desbalanceado.
- Mismatch entre descriptor categórico y tratamiento numérico real.
- Explicaciones aparentemente múltiples que en realidad son duplicadas.
- Comentarios triviales usados como si fueran evidencia.

## Code Examples

```yaml
input:
  hallazgo:
    id: "H-001"
    tipo: "prediccion_credito"
    origen: "prediction_step"
    ejercicio: "credit_approval"
  metadata:
    positive_class_definition: "1=Good, 2=Bad"
    threshold: 0.5
  evidencia_modelo:
    probability: 0.89
    predicted_label: "Aprobado"
    positive_class: "Bad"

output:
  clasificacion_final:
    estado: falso_positivo
    decision: "La etiqueta final no es confiable"
    justificacion: "La probabilidad alta corresponde a la clase Bad, pero fue presentada como Aprobado"
    evidencia_usada:
      - "positive_class = Bad"
      - "predicted_label = Aprobado"
      - "threshold = 0.5"
    evidencia_descartada:
      - "explicacion_pedagogica"
    alertas:
      - "Inversion semantica de clase positiva"
```

## Commands

```bash
poetry run pytest tests/test_modeling.py tests/test_storage.py tests/test_submission_validation.py
poetry run streamlit run app/main.py
```

## Resources

- **Project flow**: `app/pages/sequential_flow.py`
- **Model semantics**: `app/services/modeling.py`
- **Per-exercise persistence**: `app/domain/models.py`, `app/services/storage.py`
- **Validation helper**: `app/services/submission_validation.py`
