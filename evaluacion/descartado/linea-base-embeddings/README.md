# Experimento descartado: línea base de recuperación con embeddings

**Estado:** descartado el 08/11/2026. La línea base del TFM es Granite-8B-Code-Instruct sin ajustar con un ejemplo en contexto (`../../linea_base_granite.py`). Esta carpeta se conserva para que el resultado sea reproducible y pueda citarse como decisión de diseño.

## Qué se probó

`xthor/Qwen3-Embedding-0.6B-GraphQL` (Koritzius, 2026), un ajuste de Qwen3-Embedding-0.6B (Zhang et al., 2025) para relacionar preguntas con campos de esquemas GraphQL, usado sin entrenamiento adicional. Como no genera texto, se usó como recuperador por vecino más cercano: para cada pregunta de prueba se devolvía la consulta de la pregunta de `train.jsonl` más parecida (similitud de coseno) del mismo conjunto de datos.

## Resultado (test, 207 pares; revisión del modelo `728ac823`)

| Métrica | Tasa |
|---|---|
| Validez sintáctica y contra el esquema | 100 % |
| Coincidencia exacta | 0 % |
| Coincidencia estructural | 21,7 % |
| **Exactitud de ejecución** | **0,5 % (1/207, acierto casual)** |

El vecino era de la misma categoría de consulta en el 47,8 % de los casos, pero como cada consulta del conjunto es única casi nunca coincidía en los valores de los filtros.

## Por qué se descartó

- No genera consultas: solo reutiliza las del entrenamiento, así que no puede adaptar los valores de los filtros.
- Con un 0,5 %, superarla con McNemar era casi seguro y aportaba poca información.
- No es comparable con el banco de pruebas de referencia (Kesarwani et al., 2024), mientras que Granite-8B-Code-Instruct sí tiene resultado publicado (23,9 % con un ejemplo).

## Reproducir

```bash
pip install "sentence-transformers>=3" numpy
python3 linea_base_recuperacion.py --revision 728ac823c1c7736c00f0aff95fca2a421dacf6a9   # → predicciones/test.jsonl
python3 ../../evaluar.py predicciones/test.jsonl --salida resultados                   # → resultados/
```

## Archivos

| Archivo | Contenido |
|---|---|
| `linea_base_recuperacion.py` | Script de la línea base |
| `predicciones/test.jsonl`, `test.meta.json` | Predicciones (con el vecino y su similitud) y metadatos |
| `resultados/test.jsonl`, `test.resumen.json` | Evaluación por par y resumen |
