# Conjunto de datos Texto→GraphQL (OE3)

Pares de pregunta en español y consulta GraphQL sobre los 9 conjuntos de datos.gov.co que expone `capa-graphql`. Todas las consultas se validaron contra el esquema y se ejecutaron en el portal real. Versión del 01/11/2026.

## Archivos

| Archivo | Contenido |
|---|---|
| `train.jsonl`, `val.jsonl`, `test.jsonl` | Particiones de 8 conjuntos (70/15/15) |
| `reservado.jsonl` | `ni93-8mm5` completo, como prueba secundaria con un esquema no visto |
| `revision.csv` | Todas las preguntas, con columnas para la revisión humana |
| `lexico.py` | Vocabulario en español de cada conjunto: nombres de filas, campos, medidas y forma de filtrar |
| `construir.py` | Generación, validación y partición (ver "Reproducir") |
| `trabajo/valores.json` | Valores reales consultados en el portal: años, valores frecuentes, medias |
| `trabajo/candidatos.jsonl` | Todos los candidatos generados |
| `trabajo/validados.jsonl` | Resultado de validar cada candidato: SoQL, filas, primeras filas de la respuesta y motivo de rechazo |
| `trabajo/estadisticas.json` | Recuentos por conjunto, partición y categoría |

Cada línea de las particiones contiene:

```json
{"id": "train-0434", "dataset": "h2yr-zfb2", "categoria": "suma+filtro",
 "pregunta": "Total de hogares beneficiados en Nariño.",
 "graphql": "{ subsidiosViviendaAggregate(where: {departamento: {eq: NARINO}}) { sum { hogares } } }",
 "soql": "SELECT sum(hogares) AS sum_hogares WHERE departamento = 'NARIÑO' LIMIT 100",
 "filas": 1, "origen": "plantilla", "revision": "pendiente"}
```

## Cifras

| Conjunto | train | val | test | reservado | Total |
|---|---|---|---|---|---|
| `gcq5-hvdx` | 119 | 22 | 25 | — | 166 |
| `h2yr-zfb2` | 115 | 27 | 28 | — | 170 |
| `uejq-wxrr` | 118 | 28 | 30 | — | 176 |
| `8yi9-t44c` | 114 | 23 | 25 | — | 162 |
| `3ebi-d83g` | 117 | 28 | 29 | — | 174 |
| `rtai-k9uh` | 70 | 19 | 20 | — | 109 |
| `kekd-7v7h` | 106 | 24 | 26 | — | 156 |
| `nxt2-39c3` | 88 | 20 | 24 | — | 132 |
| `ni93-8mm5` | — | — | — | 116 | 116 |
| **Total** | **847** | **191** | **207** | **116** | **1.361** |

- 1.397 candidatos, de los que 1.361 son válidos (97,4 %). No hubo errores de esquema ni de SoQL. Los 36 rechazos devolvieron resultados vacíos: 28 sumas nulas o cero, 5 conteos 0 y 3 promedios nulos.
- 28 categorías de consulta, más 6 exclusivas de las 20 tripletas originales: conteos, sumas, promedios, mínimos y máximos, agrupaciones simples y dobles, top-N, filtros `in`, `neq`, `contains` y `startsWith`, rangos de años y fechas, `_or`, paginación, conteo distinto y evolución anual.
- 1.142 consultas de agregación y 219 de filas. Media de 13,4 palabras por pregunta.
- Incluye las 20 tripletas validadas de `gcq5-hvdx` (`origen: "ejemplo"`).

## Método

1. **Valores reales** (`explorar`). Para cada conjunto se consultan, a través de la capa:
   - los años disponibles;
   - los 30 valores más frecuentes de cada campo de filtro;
   - la media y el máximo de cada medida;
   - los meses con datos.

   Así las preguntas usan valores que existen en el portal.
2. **Plantillas** (`generar`):
   - 28 plantillas, cada una con varias redacciones en español, se instancian con el léxico de `lexico.py` y con esos valores (semilla fija 20261101).
   - La consulta se escribe directamente en la forma canónica de `CONVENCIONES.md` §9.
   - Cada consulta GraphQL aparece una sola vez en el conjunto.
3. **Validación** (`validar`):
   - `graphql.validate` contra el esquema de la capa;
   - ejecución completa en datos.gov.co (traducción, SODA3 y conversión);
   - se descartan las consultas cuya respuesta no aporta información (conteo 0, suma o promedio nulos, sin filas).
4. **Partición** (`particionar`):
   - estratificada por conjunto y categoría, 70/15/15;
   - como cada consulta es única, ninguna pregunta de prueba es una paráfrasis de una de entrenamiento;
   - `ni93-8mm5` queda fuera del entrenamiento.

## Reproducir

```bash
pip install -r ../capa-graphql/requirements.txt     # credenciales en ../spike-soda3/.env
python3 construir.py explorar
python3 construir.py generar
python3 construir.py validar       # reanudable; con la caché de la capa no vuelve a consultar el portal
python3 construir.py particionar
```

## Limitaciones y pendientes

- **Revisión humana pendiente.** Las redacciones de las plantillas se escribieron con ayuda de un LLM (Claude), y algunas preguntas suenan poco naturales ("¿cuánto suma bovinos vacunados…?", "promedio de concentración promedio"). Antes de entrenar, cada integrante revisa `revision.csv` (unas 680 filas cada uno) y corrige la pregunta cuando haga falta; la consulta GraphQL no se toca. Este uso de un LLM debe declararse en la memoria.
- **Una redacción por consulta.** No hay paráfrasis múltiples de la misma consulta. Si hace falta más variedad lingüística, se pueden añadir paráfrasis de las preguntas de entrenamiento, dejando val y test intactos.
- **Agrupación por enum fusionado (capa).** Al agrupar por una columna `enum` cuyas variantes se fusionaron (por ejemplo `diaDeDemandaMaxima`), la capa devuelve una fila por variante original (`SABADO` aparece tres veces). Afecta a 83 pares. Las consultas siguen siendo válidas y la comparación por ejecución es coherente, pero la respuesta al usuario es incorrecta. Hay que corregirlo en `traductor.py`, agrupando por una expresión `case(...)` que unifique las variantes, y volver a validar.
- **`rtai-k9uh`.** No se generan preguntas de evolución anual del puntaje, porque los puntajes de 2021 y 2025 no son comparables.
- **`gcq5-hvdx`.** Solo tiene la vigencia 2024, así que sus preguntas temporales son poco variadas.
- **Datos vivos.** Las respuestas corresponden al portal el 01/11/2026. La caché de la capa (`~/.cache/tfm-graphql/soda.sqlite`) conserva esa instantánea para la evaluación.
