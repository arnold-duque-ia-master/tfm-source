# Convenciones del esquema GraphQL sobre datos.gov.co

| Campo | Valor |
|---|---|
| Versión | 0.3 (umbral de enum 40 y fusión de sinónimos, 01/11/2026; ajustes del paso 4 en el apartado 12) |
| Fecha | 01/11/2026 |
| Esquema de referencia | `esquema-gcq5-hvdx.graphql`, generado por `generador.py`; esquemas de los 9 conjuntos en `esquemas/` |
| Ejemplos | `ejemplos-gcq5-hvdx.jsonl`: 20 tripletas pregunta → GraphQL → SoQL; 20/20 validadas (`validar_ejemplos.py`) |

Estas convenciones son el contrato entre la capa GraphQL, el dataset Texto→GraphQL y los dos modelos. **Cualquier cambio después de construir el dataset obliga a regenerarlo y a reentrenar.** Las decisiones marcadas **[CONFIRMADO]** se aprobaron entre ambos integrantes el 01/11/2026.

---

## 1. Alcance

- Solo lectura: operaciones `query`. Sin mutaciones ni suscripciones.
- Un conjunto de datos por consulta y un solo campo raíz por consulta. Sin uniones entre conjuntos.
- **[CONFIRMADO]** Entrada del modelo: la pregunta en español más el SDL del conjunto destino. El usuario elige el conjunto en la interfaz; la selección automática del conjunto (*routing*) queda fuera de alcance y pasa a trabajo futuro.
- Fuera de alcance de la v0.1: funciones geográficas, búsqueda de texto completo, `HAVING` (se cubre con `orderBy` + `limit`) y agrupación por expresiones arbitrarias.

## 2. Registro de conjuntos

Cada conjunto se declara en `datasets.yaml` (se crea en el paso 4). El generador lee los metadatos guardados y aplica el registro; nunca consulta el portal para generar el esquema.

```yaml
- id: gcq5-hvdx
  alias: vacunacionAftosaVichada      # nombre del campo raíz (camelCase, elegido a mano)
  exclude: [predio]                   # columnas que no se exponen
  int: [codigo_dane_departamento, codigo_dane_municipio, ruv, vigencia,
        total_aftosa, equinos, porcinos, ovinos, caprinos]
  roles:                              # controla qué agregados se ofrecen
    id: [codigo_dane_departamento, codigo_dane_municipio, ruv]
    year: [vigencia]
    geo: [latitud, longitud]
- id: nxt2-39c3
  alias: calidadAguaIrca
  casts:                              # columnas numéricas guardadas como texto
    ircaurbano: {type: Float, nullTokens: [ND]}
    ircarural:  {type: Float, nullTokens: [ND]}
```

## 3. Nombres

| Elemento | Regla | Ejemplo |
|---|---|---|
| Campo raíz de filas | `alias` del registro | `vacunacionAftosaVichada` |
| Campo raíz de agregados | `alias` + `Aggregate` | `vacunacionAftosaVichadaAggregate` |
| Tipos del conjunto | `alias` en PascalCase + sufijo | `VacunacionAftosaVichada`, `…Where`, `…OrderBy`, `…Group` |
| Campo de columna | Etiqueta visible (`name`) sin tildes ni signos, en camelCase | `FECHA_RUV` → `fechaRuv`; `AÑO DE ASIGNACIÓN` → `anoDeAsignacion` |
| Colisiones | Sufijo numérico en el orden de las columnas | `municipio`, `municipio2` |
| Nombre que empieza por dígito | Prefijo `c` | `2020` → `c2020` |
| Valor de enum | Valor original en mayúsculas, sin tildes, con `_` | `SANTA ROSALÍA` → `SANTA_ROSALIA`; `Ciclo II - 2024` → `CICLO_II_2024` |
| Campos derivados de fecha | Campo + `Year` / `Month` | `fechaRuvYear`, `fechaRuvMonth` |

Se usa la etiqueta visible y no el `fieldName`, porque Socrata destroza las tildes en este (`a_o_de_asignaci_n`). El resolver guarda la correspondencia campo → `fieldName`.

Nombres reservados que ninguna columna puede usar: `_and`, `_or`, `_not`, `count`, `countDistinct`, `sum`, `avg`, `min`, `max`. Si coinciden, se añade el sufijo `Col`.

## 4. Tipos

| Tipo SODA | Tipo GraphQL | Observación |
|---|---|---|
| `text` con ≤ 40 valores distintos, contados después de fusionar variantes **[CONFIRMADO]** | `enum` propio del conjunto | Los valores válidos quedan en el esquema; el modelo los aprende y la validación rechaza los inventados. Resuelve tildes y mayúsculas |
| `text` con más de 40 valores | `String` | |
| `number` | `Float`; `Int` si la columna figura en `int` del registro | El generador puede proponer `int` comprobando `count(*) WHERE col != floor(col)` = 0 |
| `calendar_date` | escalar `Date` (`AAAA-MM-DD`) | Se descarta la hora; SODA la devuelve como `floating_timestamp` |
| `checkbox` | `Boolean` | |
| `point` | tipo `Point { latitude: Float, longitude: Float }` | Sin filtros geográficos en la v0.1 |
| `url` | `String` | |
| texto que contiene números | El tipo indicado en `casts` | SoQL: `case(col IN ('ND'), NULL, true, col::number)`. Sin `nullTokens`, `::number` falla con HTTP 400 |

- Todos los campos de columna son anulables.
- El umbral de 40 valores (01/11/2026; antes 30) incluye los departamentos (32-34 valores) y mantiene el SDL acotado. Los valores se calculan al generar el esquema con `SELECT col, count(*) GROUP BY col` y quedan fijos.

## 5. Forma de las consultas

### 5.1 Filas

```graphql
{ vacunacionAftosaVichada(where: {...}, orderBy: [{campo: ASC|DESC}], limit: 100, offset: 0) { campo1 campo2 } }
```

- `limit` vale 100 por defecto, con un máximo de 1.000. `offset` vale 0 por defecto.
- Sin `orderBy` se ordena por `:id`, el identificador interno de fila de Socrata, para que la paginación sea estable. Con `orderBy`, se añade `:id` como desempate.

### 5.2 Agregados

```graphql
{ vacunacionAftosaVichadaAggregate(where: {...}, orderBy: [...], limit: 100) {
    municipio                 # claves de agrupación = campos escalares seleccionados
    count
    countDistinct { vereda }
    sum { totalAftosa }  avg { totalAftosa }
    min { fechaRuv }     max { fechaRuv }
} }
```

- **[CONFIRMADO]** No existe un argumento `groupBy`: los campos escalares seleccionados son las claves, en el orden de selección. Así el modelo escribe menos y no puede contradecir `groupBy` con la selección.
- `sum` y `avg` solo se ofrecen para columnas numéricas sin rol `id`, `year` ni `geo`, y devuelven `Float`. `min` y `max` también admiten fechas y años.
- Los campos derivados `<fecha>Year` y `<fecha>Month` permiten agrupar y filtrar por año o mes.

### 5.3 Filtros (`where`)

| Tipo | Operadores |
|---|---|
| `String` | `eq`, `neq`, `in`, `nin`, `contains`, `startsWith`, `isNull` |
| `Int`, `Float` | `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `nin`, `isNull` |
| `Date` | `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `isNull` |
| `enum` | `eq`, `neq`, `in`, `nin`, `isNull` |
| Lógicos | `_and: [Where!]`, `_or: [Where!]`, `_not: Where` |

- Los campos de un mismo objeto se combinan con AND.
- `contains` y `startsWith` no distinguen mayúsculas, pero **sí distinguen tildes**. SoQL no tiene una función para quitarlas. **[PENDIENTE]** Para columnas `String` de cardinalidad media (veredas, municipios a nivel nacional) se podría precalcular un índice de valores normalizados y traducir `eq` a `IN` con las variantes exactas. Se deja para la v0.2.

### 5.4 Orden en agregados

`orderBy` admite claves de agrupación, `count` y los agregados anidados: `[{sum: {totalAftosa: DESC}}]`. Cada objeto de la lista lleva una sola clave.

## 6. Traducción a SoQL

| GraphQL | SoQL |
|---|---|
| campo seleccionado (filas) | `SELECT field_name, …` |
| clave de agrupación | `SELECT field_name … GROUP BY field_name` |
| `count` | `count(*) AS count` |
| `countDistinct { x }` | `count(distinct x) AS count_distinct_x` |
| `sum { x }` / `avg` / `min` / `max` | `sum(x) AS sum_x` … |
| `xYear` / `xMonth` | `date_extract_y(x) AS x_year` / `date_extract_m(x) AS x_month` |
| `eq` / `neq` | `=` / `!=` |
| `gt` `gte` `lt` `lte` | `>` `>=` `<` `<=` |
| `in` / `nin` | `IN (…)` / `NOT IN (…)` |
| `isNull: true` / `false` | `IS NULL` / `IS NOT NULL` |
| `contains: "v"` | `upper(x) LIKE upper('%v%')` |
| `startsWith: "v"` | `starts_with(upper(x), upper('v'))` |
| `_or` / `_not` | `(a OR b)` / `NOT (a)` |
| valor de enum | valor original entre comillas (`SANTA_ROSALIA` → `'SANTA ROSALÍA'`) |
| `orderBy` sobre un agregado | se repite la expresión: `ORDER BY sum(total_aftosa) DESC` |
| `limit` / `offset` | `LIMIT n` / `OFFSET m` (se omite `OFFSET 0`) |

- Orden de las cláusulas: `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `LIMIT`, `OFFSET`.
- Implementación: `traductor.py` (paso 5), con pruebas en `test_traductor.py` (las 20 tripletas coinciden carácter a carácter) y `prueba_vivo.py` (20 consultas de extremo a extremo sobre los 9 conjuntos).
- Columnas con `cast` usadas como clave de agrupación: `anio::number AS anio_num … GROUP BY anio_num`.
- En `where`, las condiciones de columna van en el orden del esquema y las lógicas (`_and`, `_or`, `_not`) al final; `baseWhere` va siempre primero.
- Un valor de enum fusionado se traduce a `IN`/`NOT IN` con todas sus variantes, también en `eq`/`neq`.
- Las cadenas se escapan duplicando la comilla simple.
- La petición a SODA3 usa `page = {pageNumber: 1, pageSize: limit}`.
- La SoQL generada es determinista: la misma consulta GraphQL produce siempre la misma cadena. Esto permite comparar resultados en la exactitud de ejecución.

## 7. Respuesta

- SODA devuelve todos los valores como cadenas. El resolver los convierte al tipo GraphQL declarado:
  - `Int` y `Float`, con número.
  - `Date`, con los 10 primeros caracteres.
  - `enum`, con la correspondencia inversa al nombre del valor.
- Un campo ausente en la fila de SODA se devuelve como `null`.

## 8. Validación y errores

1. **Sintaxis y esquema:** se usa `graphql.validate()` antes de ejecutar (RF-06).
2. **Reglas propias:**
   - `limit` ≤ 1.000 y `offset` ≥ 0.
   - Cada objeto de `orderBy` lleva una sola clave.
   - En un agregado solo se ordena por claves seleccionadas o por agregados.
   - Las listas `in`/`nin` no pueden estar vacías y tienen como máximo 100 elementos.
   - La consulta tiene un solo campo raíz y no usa variables ni fragmentos.
3. **Errores de SODA:** se traducen a errores GraphQL con `extensions.code`.

| `extensions.code` | Causa |
|---|---|
| `GRAPHQL_VALIDATION_FAILED` | Sintaxis o esquema |
| `QUERY_RULE_VIOLATION` | Reglas propias del punto 2 |
| `SOQL_ERROR` | HTTP 400 de SODA; incluye `soqlCode` y `message` |
| `UPSTREAM_AUTH` | HTTP 401/403 de SODA |
| `UPSTREAM_UNAVAILABLE` | Tiempo de espera agotado o HTTP 5xx |

## 9. Forma canónica (para el dataset)

Para que la coincidencia exacta tenga sentido y el modelo aprenda una sola forma de escribir:

- Sin alias, variables ni fragmentos; operación anónima `{ … }`.
- Argumentos en este orden: `where`, `orderBy`, `limit`, `offset`. Se omiten los que tienen su valor por defecto.
- Campos de `where` en el orden del esquema; los lógicos al final.
- Formato: una línea, normalizada con `graphql.print_ast` y compactada.
- **[CONFIRMADO]** La métrica principal sigue siendo la exactitud de ejecución, porque dos consultas distintas pueden ser equivalentes (Roberson et al., 2024).

## 10. Tamaño del esquema en la instrucción

El SDL de `gcq5-hvdx` ocupa unos 7.500 caracteres; sin comentarios ni descripciones, unos 6.100; y sin los tipos compartidos, unos 5.600. Eso equivale aproximadamente a 1.800-2.200 *tokens*. Con 8 GB de VRAM y QLoRA hay que mantener secuencias moderadas, así que:

- **[CONFIRMADO]** En la instrucción se incluye el SDL compacto del conjunto, sin descripciones y sin los tipos compartidos, que el modelo aprende en el entrenamiento.
- **[PENDIENTE]** Medir los *tokens* con el tokenizador real de Qwen2.5-Coder y de CodeLlama para cada conjunto seleccionado, y fijar `max_seq_length`.
- Si algún conjunto supera el presupuesto, se pueden eliminar los tipos `…OrderBy` repetidos o reducir el umbral de enum.

## 11. Decisiones pendientes

- [x] Confirmar las propuestas de los apartados 1, 4, 5.2, 9 y 10 (01/11/2026).
- [ ] Normalización de tildes para columnas `String` (5.3).
- [x] Selección de conjuntos: los 7 recomendados de `spike-soda3/CANDIDATOS.md`, más `gcq5-hvdx` y `ni93-8mm5` (N = 9).
- [ ] Actualizar la Figura 2 del borrador a esta forma, con 2024 en lugar de 2025:
  `{ vacunacionAftosaVichadaAggregate(where: {municipio: {eq: CUMARIBO}, vigencia: {eq: 2024}}) { sum { totalAftosa } } }` → 54.910 bovinos.
- [x] Umbral de enum subido a 40 (01/11/2026).
- [x] Fusión de sinónimos (01/11/2026): reglas automáticas y `valueAliases` (apartado 12).

## 12. Ajustes introducidos en el paso 4 (v0.2)

Al generar los 9 esquemas aparecieron casos que la v0.1 no cubría:

| Ajuste | Motivo |
|---|---|
| Roles `id`, `time` y `geo` (antes `year`) | `time` agrupa año, mes y periodo: no se suman ni se promedian, pero sí se agrupan y admiten `min`/`max` |
| Escalar `DateTime` | `3ebi-d83g` tiene fechas con hora (`fecha_demanda_maxima`); el perfil detecta `con_hora` |
| Fusión de variantes en los enum | Un grupo de variantes forma un único valor GraphQL que se traduce a `IN` con todas ellas. Se fusionan automáticamente los valores que coinciden (1) sin tildes, mayúsculas ni puntuación (`DOMINGO` → `IN ('domingo', 'Domingo')`), (2) con las mismas palabras en otro orden, sin artículos (`ALTO_RIESGO` → `IN ('Alto riesgo', 'Riesgo alto')`), o (3) solo con letras y dígitos (`N/A` = `NA`). No se usa similitud aproximada para fusionar: separaría mal códigos como `PM10`/`PM2.5` o `NO`/`NO2` |
| `valueAliases` en el registro | Fusiones manuales decididas por el equipo; el primer valor de cada grupo da el nombre canónico. `generador.py` escribe `esquemas/revision-enums.md` con las fusiones hechas y los pares parecidos sin fusionar, para revisarlos. Casos aplicados: 5 grafías de San Andrés (`3ebi-d83g`); 7 índices y 1 sector renombrados en el cambio de metodología 2021→2025 (`rtai-k9uh`). Los puntajes de ambas metodologías no son estrictamente comparables |
| `baseWhere` en el registro | `nxt2-39c3` mezcla filas de totales departamentales (`municipiocodigo = '#TODOS'`, 569 filas) con las municipales; se excluyen siempre |
| `rename` en el registro | Etiquetas con errores o acrónimos mal separados (`ID DEPATAMENTO`, `IRCAurbano`) |
| `Int` solo si cabe en 32 bits | GraphQL `Int` es de 32 bits; `valor_asignado` de `h2yr-zfb2` llega a 6,6·10¹⁰ y pasa a `Float` |
| `ñ` → `ni` en nombres de campo | Evita `ano` para "año" (`anio`, `anioDeAsignacion`); los valores de enum mantienen `N` (`PUERTO_CARRENO`) |
| Claves de agrupación | Todas las columnas que no son medidas ni `geo` (incluye las de rol `id`, como `ruv`) |
| `countDistinct` | Columnas de texto, enum, fecha y booleanas, más las numéricas de rol `id` o `time` |
| Columnas con identificador | Las columnas de texto con rol `id` nunca son enum (conservan los ceros a la izquierda: `"05001"`) |
| `point` | Tipo compartido `Point`; se excluye `ubicacion` de `kekd-7v7h` porque duplica latitud y longitud |

