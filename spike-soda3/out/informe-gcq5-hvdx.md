# Prueba SODA3: `gcq5-hvdx`

- **Nombre:** Registros de Vacunación contra Fiebre Aftosa y Especies Asociadas en el Departamento del Vichada
- **Publicador:** Secretaria de agricultura y desarrollo rural del Vichada
- **Licencia:** Creative Commons Attribution 4.0 International
- **Categoría:** Agricultura y Desarrollo Rural
- **Última actualización de filas (epoch):** 1789138669
- **Consultas con token:** sí

## Columnas

| fieldName | dataTypeName | Etiqueta visible | Descripción |
|---|---|---|---|
| `codigo_dane_departamento` | number | CODIGO_DANE_DEPARTAMENTO | Código numérico de dos dígitos asignado por el DANE en la codificación DIVIPOLA  |
| `departamento` | text | DEPARTAMENTO | Nombre oficial del departamento de Colombia donde se localiza el predio pecuario |
| `codigo_dane_municipio` | number | CODIGO_DANE_MUNICIPIO | Código numérico oficial de cinco dígitos DIVIPOLA asignado por el DANE a la enti |
| `municipio` | text | MUNICIPIO | Nombre del municipio del departamento del Vichada donde se ejecutó la jornada de |
| `vereda` | text | VEREDA | División territorial rural o sector veredal en el que se encuentra ubicado el pr |
| `predio` | text | PREDIO | Denominación o nombre comercial/catastral con el cual se identifica la finca, ha |
| `tenencia` | text | TENENCIA | Condición jurídica de ocupación o explotación del predio (Propio, Arrendado, Pos |
| `ruv` | number | RUV | Número del Registro Único de Vacunación emitido oficialmente como soporte de la  |
| `fecha_ruv` | calendar_date | FECHA_RUV | Fecha de expedición del RUV y aplicación del biológico en el predio, en formato  |
| `vigencia` | number | VIGENCIA | Año fiscal y calendario al que corresponde la ejecución de las jornadas de vacun |
| `ciclo_vacunacion` | text | CICLO_VACUNACION | Etapa o ciclo oficial del calendario sanitario animal fijado por el Instituto Co |
| `longitud` | number | LONGITUD | Coordenada geográfica decimal de longitud en el sistema de referencia WGS84 para |
| `latitud` | number | LATITUD | Coordenada geográfica decimal de latitud en el sistema de referencia WGS84 para  |
| `total_aftosa` | number | TOTAL_AFTOSA | Cantidad total de cabezas de ganado bovino y bufalino efectivamente vacunadas co |
| `equinos` | number | EQUINOS | Censo de animales de la especie équida (caballos, yeguas, mulares y asnales) reg |
| `porcinos` | number | PORCINOS | Censo total de ganado porcino registrado en las instalaciones del predio durante |
| `ovinos` | number | OVINOS | Censo de animales de la especie ovina registrados en el predio pecuario. |
| `caprinos` | number | CAPRINOS | Censo total de ganado caprino registrado en el predio pecuario durante la visita |

## Consultas

| Caso | HTTP | ms | Filas | Tipo de respuesta |
|---|---|---|---|---|
| Muestra (SELECT *) | 200 | 773 | 5 | list |
| Conteo total | 200 | 583 | 1 | list |
| Filtro por texto | 200 | 612 | 5 | list |
| Agregación con GROUP BY | 200 | 643 | 4 | list |
| Rango de fechas y orden | 200 | 718 | 5 | list |
| Mínimo y máximo de fecha | 200 | 587 | 1 | list |
| Paginación, página 1 | 200 | 652 | 3 | list |
| Paginación, página 2 | 200 | 609 | 3 | list |
| Error provocado (columna inexistente) | 400 | 605 | None | dict |
| Sin token de aplicación | 403 | 409 | None | dict |

### Muestra (SELECT *)

```sql
SELECT *
```
Página (1, 5). Tipos de los valores devueltos: `{'codigo_dane_departamento': {'str': 5}, 'departamento': {'str': 5}, 'codigo_dane_municipio': {'str': 5}, 'municipio': {'str': 5}, 'vereda': {'str': 5}, 'predio': {'str': 5}, 'tenencia': {'str': 5}, 'ruv': {'str': 5}, 'fecha_ruv': {'str': 5}, 'vigencia': {'str': 5}, 'ciclo_vacunacion': {'str': 5}, 'longitud': {'str': 5}, 'latitud': {'str': 5}, 'total_aftosa': {'str': 5}, 'equinos': {'str': 5}, 'porcinos': {'str': 5}, 'ovinos': {'str': 5}, 'caprinos': {'str': 5}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:01 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["codigo_dane_departamento","departamento","codigo_dane_municipio","municipio","vereda","predio","tenencia","ruv","fecha_ruv","vigencia","ciclo_vacunacion","longitud","latitud","total_aftosa","equinos","porcinos","ovinos","caprinos"]', 'X-SODA2-Types': '["number","text","number","text","text","text","text","number","floating_timestamp","number","text","number","number","number","number","number","number","number"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': 'b2dc15ba86675fdd625e944eb5ce3b33'}`

```json
[
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "PUERTO ORIENTE",
    "predio": "TABATINGA",
    "tenencia": "PROPIO",
    "ruv": "10266907",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-71.03091134",
    "latitud": "4.22127451",
    "total_aftosa": "148",
    "equinos": "0",
    "porcinos": "0",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "EL TRIUNFO",
    "predio": "CATALINA",
    "tenencia": "PROPIO",
    "ruv": "10257502",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-68.521105",
    "latitud": "5.10694667",
    "total_aftosa": "105",
    "equinos": "0",
    "porcinos": "0",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "PUERTO ORIENTE",
    "predio": "EL ORIENTE",
    "tenencia": "PROPIO",
    "ruv": "10331828",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-71.0355165",
    "latitud": "4.2665283",
    "total_aftosa": "2
```

### Conteo total

```sql
SELECT count(*) AS total
```
Página (1, 100). Tipos de los valores devueltos: `{'total': {'str': 1}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:02 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["total"]', 'X-SODA2-Types': '["number"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': '4f7b198d6d15dfea74a1644275c64e45'}`

```json
[
  {
    "total": "2877"
  }
]
```

### Filtro por texto

```sql
SELECT * WHERE municipio = 'CUMARIBO'
```
Página (1, 5). Tipos de los valores devueltos: `{'codigo_dane_departamento': {'str': 5}, 'departamento': {'str': 5}, 'codigo_dane_municipio': {'str': 5}, 'municipio': {'str': 5}, 'vereda': {'str': 5}, 'predio': {'str': 5}, 'tenencia': {'str': 5}, 'ruv': {'str': 5}, 'fecha_ruv': {'str': 5}, 'vigencia': {'str': 5}, 'ciclo_vacunacion': {'str': 5}, 'longitud': {'str': 5}, 'latitud': {'str': 5}, 'total_aftosa': {'str': 5}, 'equinos': {'str': 5}, 'porcinos': {'str': 5}, 'ovinos': {'str': 5}, 'caprinos': {'str': 5}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:02 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["codigo_dane_departamento","departamento","codigo_dane_municipio","municipio","vereda","predio","tenencia","ruv","fecha_ruv","vigencia","ciclo_vacunacion","longitud","latitud","total_aftosa","equinos","porcinos","ovinos","caprinos"]', 'X-SODA2-Types': '["number","text","number","text","text","text","text","number","floating_timestamp","number","text","number","number","number","number","number","number","number"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': '4abe81026687b5845b698d2ea807b551'}`

```json
[
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "PUERTO ORIENTE",
    "predio": "TABATINGA",
    "tenencia": "PROPIO",
    "ruv": "10266907",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-71.03091134",
    "latitud": "4.22127451",
    "total_aftosa": "148",
    "equinos": "0",
    "porcinos": "0",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "EL TRIUNFO",
    "predio": "CATALINA",
    "tenencia": "PROPIO",
    "ruv": "10257502",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-68.521105",
    "latitud": "5.10694667",
    "total_aftosa": "105",
    "equinos": "0",
    "porcinos": "0",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "PUERTO ORIENTE",
    "predio": "EL ORIENTE",
    "tenencia": "PROPIO",
    "ruv": "10331828",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-71.0355165",
    "latitud": "4.2665283",
    "total_aftosa": "2
```

### Agregación con GROUP BY

```sql
SELECT municipio, sum(vigencia) AS suma, count(*) AS n GROUP BY municipio ORDER BY suma DESC
```
Página (1, 10). Tipos de los valores devueltos: `{'municipio': {'str': 4}, 'suma': {'str': 4}, 'n': {'str': 4}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:03 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["municipio","suma","n"]', 'X-SODA2-Types': '["text","number","number"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': '97463130f5d3ba31e9fdf79dce485f37'}`

```json
[
  {
    "municipio": "LA PRIMAVERA",
    "suma": "2706088",
    "n": "1337"
  },
  {
    "municipio": "CUMARIBO",
    "suma": "1548360",
    "n": "765"
  },
  {
    "municipio": "SANTA ROSALÍA",
    "suma": "1001880",
    "n": "495"
  }
]
```

### Rango de fechas y orden

```sql
SELECT fecha_ruv WHERE fecha_ruv >= '2020-01-01T00:00:00' ORDER BY fecha_ruv DESC
```
Página (1, 5). Tipos de los valores devueltos: `{'fecha_ruv': {'str': 5}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:04 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["fecha_ruv"]', 'X-SODA2-Types': '["floating_timestamp"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': 'a1c83a9585a950e1148be1f0e6c57268'}`

```json
[
  {
    "fecha_ruv": "2024-12-16T00:00:00.000"
  },
  {
    "fecha_ruv": "2024-12-16T00:00:00.000"
  },
  {
    "fecha_ruv": "2024-12-16T00:00:00.000"
  }
]
```

### Mínimo y máximo de fecha

```sql
SELECT min(fecha_ruv) AS desde, max(fecha_ruv) AS hasta
```
Página (1, 100). Tipos de los valores devueltos: `{'desde': {'str': 1}, 'hasta': {'str': 1}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:04 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["desde","hasta"]', 'X-SODA2-Types': '["floating_timestamp","floating_timestamp"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': '985c69e9cd83e33ea4edc6ba7198f602'}`

```json
[
  {
    "desde": "2024-10-28T00:00:00.000",
    "hasta": "2024-12-16T00:00:00.000"
  }
]
```

### Paginación, página 1

```sql
SELECT * ORDER BY :id
```
Página (1, 3). Tipos de los valores devueltos: `{'codigo_dane_departamento': {'str': 3}, 'departamento': {'str': 3}, 'codigo_dane_municipio': {'str': 3}, 'municipio': {'str': 3}, 'vereda': {'str': 3}, 'predio': {'str': 3}, 'tenencia': {'str': 3}, 'ruv': {'str': 3}, 'fecha_ruv': {'str': 3}, 'vigencia': {'str': 3}, 'ciclo_vacunacion': {'str': 3}, 'longitud': {'str': 3}, 'latitud': {'str': 3}, 'total_aftosa': {'str': 3}, 'equinos': {'str': 3}, 'porcinos': {'str': 3}, 'ovinos': {'str': 3}, 'caprinos': {'str': 3}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:05 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["codigo_dane_departamento","departamento","codigo_dane_municipio","municipio","vereda","predio","tenencia","ruv","fecha_ruv","vigencia","ciclo_vacunacion","longitud","latitud","total_aftosa","equinos","porcinos","ovinos","caprinos"]', 'X-SODA2-Types': '["number","text","number","text","text","text","text","number","floating_timestamp","number","text","number","number","number","number","number","number","number"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': 'dc59e74f45dd26a690c539a88ef74617'}`

```json
[
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "PUERTO ORIENTE",
    "predio": "TABATINGA",
    "tenencia": "PROPIO",
    "ruv": "10266907",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-71.03091134",
    "latitud": "4.22127451",
    "total_aftosa": "148",
    "equinos": "0",
    "porcinos": "0",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "EL TRIUNFO",
    "predio": "CATALINA",
    "tenencia": "PROPIO",
    "ruv": "10257502",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-68.521105",
    "latitud": "5.10694667",
    "total_aftosa": "105",
    "equinos": "0",
    "porcinos": "0",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "PUERTO ORIENTE",
    "predio": "EL ORIENTE",
    "tenencia": "PROPIO",
    "ruv": "10331828",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-71.0355165",
    "latitud": "4.2665283",
    "total_aftosa": "2
```

### Paginación, página 2

```sql
SELECT * ORDER BY :id
```
Página (2, 3). Tipos de los valores devueltos: `{'codigo_dane_departamento': {'str': 3}, 'departamento': {'str': 3}, 'codigo_dane_municipio': {'str': 3}, 'municipio': {'str': 3}, 'vereda': {'str': 3}, 'predio': {'str': 3}, 'tenencia': {'str': 3}, 'ruv': {'str': 3}, 'fecha_ruv': {'str': 3}, 'vigencia': {'str': 3}, 'ciclo_vacunacion': {'str': 3}, 'longitud': {'str': 3}, 'latitud': {'str': 3}, 'total_aftosa': {'str': 3}, 'equinos': {'str': 3}, 'porcinos': {'str': 3}, 'ovinos': {'str': 3}, 'caprinos': {'str': 3}}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'Last-Modified': 'Sun, 01 Nov 2026 18:24:06 GMT', 'x-soda2-secondary': 'pg.pg3-a-fedramp-prod', 'x-soda2-cached': 'false', 'x-soda2-data-out-of-date': '[]', 'X-SODA2-Warning': 'X-SODA2-Fields, X-SODA2-Types, and X-SODA2-Legacy-Types are deprecated', 'X-SODA2-Fields': '["codigo_dane_departamento","departamento","codigo_dane_municipio","municipio","vereda","predio","tenencia","ruv","fecha_ruv","vigencia","ciclo_vacunacion","longitud","latitud","total_aftosa","equinos","porcinos","ovinos","caprinos"]', 'X-SODA2-Types': '["number","text","number","text","text","text","text","number","floating_timestamp","number","text","number","number","number","number","number","number","number"]', 'X-Socrata-Region': 'aws-us-east-1-fedramp-prod', 'X-Socrata-RequestId': '6335b580a563832341c6597d53b3a88a'}`

```json
[
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "CHAPARRAL BAJO",
    "predio": "EL AFRICA",
    "tenencia": "PROPIO",
    "ruv": "10317298",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-68.82366667",
    "latitud": "4.77173833",
    "total_aftosa": "130",
    "equinos": "0",
    "porcinos": "0",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "UVA ALTO",
    "predio": "LA GRANJA",
    "tenencia": "PROPIO",
    "ruv": "10351021",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-70.42385833",
    "latitud": "3.54071167",
    "total_aftosa": "121",
    "equinos": "10",
    "porcinos": "15",
    "ovinos": "0",
    "caprinos": "0"
  },
  {
    "codigo_dane_departamento": "99",
    "departamento": "VICHADA",
    "codigo_dane_municipio": "99773",
    "municipio": "CUMARIBO",
    "vereda": "EL TRIUNFO",
    "predio": "LA CAÑERA",
    "tenencia": "PROPIO",
    "ruv": "10257503",
    "fecha_ruv": "2024-10-28T00:00:00.000",
    "vigencia": "2024",
    "ciclo_vacunacion": "Ciclo II - 2024",
    "longitud": "-68.66655167",
    "latitud": "5.02505333",
    "total_aftosa": "1
```

### Error provocado (columna inexistente)

```sql
SELECT columna_que_no_existe
```
Página (1, 100). Tipos de los valores devueltos: `{}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'X-Socrata-RequestId': 'd07965b245a040d345c5c33b89d16239'}`

```json
{
  "code": "soql.analyzer.typechecker.no-such-column",
  "error": true,
  "message": "No such column `columna_que_no_existe'",
  "status": 400,
  "data": {
    "name": "columna_que_no_existe"
  },
  "source": {
    "position": {
      "column": 8,
      "row": 1,
      "text": "SELECT columna_que_no_existe"
    },
    "type": "anonymous"
  }
}
```

### Sin token de aplicación

```sql
SELECT *
```
Página (1, 1). Tipos de los valores devueltos: `{}`

Cabeceras relevantes: `{'Content-Type': 'application/json; charset=utf-8', 'X-Socrata-RequestId': 'b8c3782ccc8544698ce601589a7ec8c5'}`

```json
{
  "code": "authentication_required",
  "error": true,
  "message": "This request must be authenticated or have an application token"
}
```
