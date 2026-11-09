# Evaluación técnica (OE4)

Línea base, instrucción en español, métricas técnicas y prueba de McNemar del capítulo 6. Qwen2.5-Coder-7B y CodeLlama-7B se evalúan **solo ajustados con QLoRA**, entre sí y frente a **Granite-8B-Code-Instruct sin ajustar** con un ejemplo en contexto (decisión del 08/11/2026; `tfm-internal`, sección 4.3).

| Archivo o carpeta | Uso |
|---|---|
| `instruccion.py` | Plantilla de instrucción en español, común al ajuste QLoRA y a la línea base; extracción de la consulta de la respuesta |
| `linea_base_granite.py` | Línea base: Granite-8B-Code-Instruct sin entrenamiento, con un ejemplo en contexto |
| `evaluar.py` | Métricas técnicas de cualquier archivo de predicciones (línea base o modelos ajustados) |
| `mcnemar.py` | Prueba de McNemar exacta entre dos resultados de `evaluar.py` |
| `predicciones/<modelo>/<particion>.jsonl` | Predicciones, en el formato común |
| `resultados/<modelo>/<particion>.jsonl` y `.resumen.json` | Evaluación por par y resumen (total, por conjunto y por categoría) |
| `descartado/linea-base-embeddings/` | Experimento descartado: recuperación por vecino más cercano con Qwen3-Embedding-0.6B-GraphQL (ver su README) |

```bash
pip install -r requirements.txt
```

## Instrucción en español (`instruccion.py`)

El entrenamiento es completamente en español: la instrucción, las preguntas y los nombres de campos y valores del esquema están en español. La sintaxis de GraphQL y los operadores de la capa (`eq`, `in`, `count`, `sum`, `orderBy`, `where`, `ASC`/`DESC`…) conservan la forma de `CONVENCIONES.md`.

- **Sistema:** el texto de `SISTEMA` (traducir a GraphQL, responder solo con la consulta en una línea, usar solo el esquema, sin alias, variables ni fragmentos).
- **Usuario:** `Esquema:` + el esquema compacto del conjunto (`capa-graphql/esquemas/<id>.prompt.graphql`) + `Pregunta: …`. En la línea base, entre el esquema y la pregunta va el bloque `Ejemplo:` con una pregunta y su `Consulta:`; el esquema aparece una sola vez.
- **Ajuste QLoRA:** `ejemplo_entrenamiento(par)` devuelve la conversación de un par con la consulta como respuesta del asistente. Cada modelo la convierte en texto con su plantilla de chat (`tokenizer.apply_chat_template`), así que la misma instrucción sirve para Qwen2.5-Coder, CodeLlama y Granite.

## Línea base: Granite-8B-Code-Instruct

`ibm-granite/granite-8b-code-instruct-4k` (Mishra et al., 2024; Apache 2.0), sin ningún entrenamiento adicional. En el banco de pruebas de referencia obtuvo un 7,65 % sin ejemplos y un 23,9 % con un ejemplo (Kesarwani et al., 2024).

- **Ejemplo en contexto:** un par de `train.jsonl` del mismo conjunto de datos, elegido con la semilla `20261108` y común a todas sus preguntas (los identificadores quedan en `<particion>.meta.json`). Si la instrucción no cupiera en la ventana, se usaría el par más corto del conjunto.
- **Tipos comunes:** como el modelo no está ajustado, la instrucción incluye además los tipos compartidos (`StringFilter`, `IntFilter`, `OrderDirection`…) que el esquema compacto omite porque los modelos ajustados los aprenden en el entrenamiento. `--sin-comunes` los quita.
- **Generación:** decodificación voraz, hasta 256 tokens; la consulta se extrae con `extraer_consulta` (quita bloques de código y texto alrededor).
- **Alcance:** solo `test.jsonl` (o `val.jsonl`); `ni93-8mm5` no tiene pares de entrenamiento de los que tomar el ejemplo.

```bash
python3 linea_base_granite.py --tokens                 # mide las instrucciones (solo el tokenizador, sin GPU)
python3 linea_base_granite.py --limite 10              # prueba rápida en el desktop (CUDA, 4 bits)
python3 linea_base_granite.py                          # test completo → predicciones/granite-8b/test.jsonl
python3 linea_base_granite.py --cuantizacion ninguna --dispositivo mps   # MacBook (bf16, unos 16 GB)
python3 evaluar.py predicciones/granite-8b/test.jsonl
```

**Ventana de contexto (medido el 08/11/2026 con el tokenizador de Granite):** con los tipos comunes y el ejemplo, las 207 instrucciones de test caben en los 4.096 tokens dejando 256 para la respuesta. La más larga es de `uejq-wxrr` (3.051 tokens; mediana por conjunto entre 1.261 y 3.026). Las consultas de referencia tienen una mediana de 39 tokens y un máximo de 71.

La cadena completa (instrucción, generación, extracción, predicciones y metadatos) se probó con un modelo pequeño (`--modelo Qwen/Qwen2.5-0.5B-Instruct --cuantizacion ninguna --limite 3`); falta ejecutarla con Granite en el desktop.

## Formato común de predicciones

Una línea por par de la partición; los modelos ajustados deben escribir el mismo formato:

```json
{"id": "test-0001", "dataset": "3ebi-d83g", "graphql": "{ ... }", "ms": 812.4, "modelo": "granite-8b"}
```

- `graphql`: la consulta predicha (`null` si no hay);
- `ms`: latencia de inferencia (opcional);
- `modelo`: nombre de la carpeta de resultados (`granite-8b`, `qwen-qlora`, `codellama-qlora`).

Los campos adicionales se ignoran (Granite añade `respuesta`, `ejemplo_id`, `ejemplo_corto` y `tokens_instruccion`).

## Métricas

```bash
python3 evaluar.py predicciones/granite-8b/test.jsonl         # usa ../spike-soda3/.env
python3 evaluar.py predicciones/qwen-qlora/test.jsonl --offline   # solo desde la caché de la capa
```

| Métrica | Criterio |
|---|---|
| `valida_sintaxis` | `graphql.parse` no falla |
| `valida_esquema` | `graphql.validate` contra el esquema de la capa sin errores |
| `coincidencia_exacta` | Misma forma impresa por graphql-core que la referencia |
| `coincidencia_estructural` | Igual que la exacta, salvo los valores de `where` (diagnóstico: estructura acertada con otros valores) |
| `exactitud_ejecucion` | **Métrica principal.** Predicción y referencia se ejecutan con la capa y devuelven las mismas filas (multiconjunto; en orden si la referencia tiene `orderBy`; números a 6 decimales) |

La referencia se ejecuta en el mismo momento que la predicción, así que ambas se comparan sobre la misma instantánea del portal. Como en cualquier exactitud de ejecución, una consulta distinta que devuelva por casualidad el mismo resultado cuenta como acierto.

Comprobación: un archivo de predicciones igual a las referencias de `test.jsonl` da 100 % en todas las métricas.

## McNemar

```bash
python3 mcnemar.py resultados/qwen-qlora/test.jsonl resultados/granite-8b/test.jsonl
python3 mcnemar.py resultados/qwen-qlora/test.jsonl resultados/codellama-qlora/test.jsonl
```

Devuelve la tabla de contingencia (ambos, solo A, solo B, ninguno), el p-valor exacto (binomial bilateral sobre los discordantes) y el chi-cuadrado con corrección de continuidad.
