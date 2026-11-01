# Hallazgos de la prueba SODA3 (paso 1) — 01/11/2026

Conjunto probado: `gcq5-hvdx` (vacunación contra fiebre aftosa, Vichada). Informe completo en `out/informe-gcq5-hvdx.md`.

## Acceso

- Metadatos (`GET /api/views/{id}.json`): públicos, sin autenticación.
- Consultas (`POST /api/v3/views/{id}/query.json`): exigen autenticación.
  - Sin credenciales: `403 authentication_required`.
  - App Token inválido en `X-App-Token`: `403 permission_denied` ("Invalid app_token specified").
  - Funciona con API Key (Key ID + Key Secret) por autenticación básica HTTP.
- Cuerpo: `{"query": "<SoQL>", "page": {"pageNumber": n, "pageSize": m}, "includeSynthetic": false}`.
- Latencia observada: 490–1.540 ms por consulta (mediana ≈ 600 ms). Justifica una caché de respuestas.

## Forma de la respuesta

- Lista JSON de objetos, uno por fila; las claves son los `fieldName`.
- **Todos los valores llegan como cadenas**, incluidos números y conteos (`"total": "2877"`). El resolver debe convertirlos según el tipo declarado.
- `calendar_date` en metadatos aparece como `floating_timestamp` en la consulta, con formato `2024-10-28T00:00:00.000` (sin zona horaria).
- Las cabeceras `X-SODA2-Fields` y `X-SODA2-Types` dan nombres y tipos de las columnas devueltas, pero están marcadas como obsoletas: no depender de ellas.

## Paginación

- `pageNumber` empieza en 1. Con `ORDER BY :id`, las páginas 1 y 2 no se solapan.
- `pageSize` de 5.000 devolvió las 2.877 filas en 778 ms.
- Sin `ORDER BY` el orden no está garantizado: la capa debe añadir `ORDER BY :id` cuando pagine.

## Errores

- Error de SoQL: HTTP 400 con `code` (p. ej. `soql.analyzer.typechecker.no-such-column`), `message`, `data` y `source.position` (fila y columna). Sirve para traducirlo a un error GraphQL comprensible (RF-06).

## Datos de `gcq5-hvdx`

- 2.877 filas, 4 municipios, 100 veredas, 1.117 predios distintos.
- **Una sola vigencia y un solo ciclo**: 2024, "Ciclo II - 2024" (fechas 28/10/2024–16/12/2024).
  - La Figura 2 del borrador pregunta por Cumaribo **en 2025**: esa consulta devolvería 0. Cambiar el ejemplo a 2024.
  - Para el dataset de preguntas, este conjunto ofrece poca variedad temporal.
- Valores de texto en mayúsculas y **con tildes** ("SANTA ROSALÍA"). `upper(municipio) = 'SANTA ROSALIA'` devuelve 0; `like '%ROSAL%'` devuelve 495.
  - Decisión pendiente: normalizar mayúsculas y tildes en la capa, o enseñar al modelo los valores exactos (p. ej. incluyendo valores de ejemplo en el esquema o en la instrucción).
- `tenencia` tiene categorías cerradas (PROPIO, ARRENDADO, POSEEDOR, OTRO): candidata a `enum` GraphQL.

## Decisiones

- **Excluir la columna `predio`** del esquema GraphQL (nombre de la finca; junto con las coordenadas puede identificar a particulares). Acordado el 01/11/2026.
- Credenciales en `spike-soda3/.env` (ignorado por Git), con API Key.
