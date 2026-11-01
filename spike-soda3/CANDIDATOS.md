# Candidatos de conjuntos de datos (paso 2) — 01/11/2026

Fuente: Discovery API de Socrata (`api.us.socrata.com/api/catalog/v1`, dominio www.datos.gov.co), 3.000 conjuntos más vistos de 8.467. Script: `filtrar_catalogo.py` (filtro) y `perfilar.py` (filas, rango y muestra; resultados en `out/catalogo/`).

## Criterios del filtro

- Licencia CC BY o CC BY-SA 4.0 (se excluye NoDerivatives).
- Sin columnas con indicios de datos personales (nombre de persona, documento, dirección, teléfono, correo, edad, sexo de individuos, predio, víctima, etc.).
- Se excluyen las categorías Seguridad y Defensa, Justicia y Derecho, Resultados Electorales y Organismos de Control.
- Entre 6 y 35 columnas, con al menos 2 de texto, 2 numéricas y 1 temporal (fecha o año/periodo).
- Datos actualizados desde el 01/01/2025.
- Resultado: 150 candidatos; se perfilaron 22 de sectores distintos y se descartaron 2 (`kwqa-xugj`, nombres de columna crípticos; `akpq-tuqi`, 4,1 millones de filas y fecha como texto).

## Candidatos

| # | ID | Conjunto | Sector | Entidad | Filas | Rango temporal | Cols | Valoración | Observación |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [`h2yr-zfb2`](https://www.datos.gov.co/d/h2yr-zfb2) | Subsidios De Vivienda Asignados | Vivienda | Gobernación de Risaralda | 87.095 | a_o_de_asignaci_n: 2003 → 2026 | 9 | Recomendado | Limpio; 23 años de serie; programa y estado como categorías; valor monetario numérico. |
| 2 | [`uejq-wxrr`](https://www.datos.gov.co/d/uejq-wxrr) | Evaluaciones Agropecuarias Municipales – EVA. 2019 - 2025. Base Agríco | Agricultura | Unidad de Planificación de Tierras Rurales | 166.732 | a_o: 2019 → 2025 | 18 | Recomendado | Jerarquía grupo→subgrupo→cultivo; área, producción y rendimiento numéricos. Complementa a gcq5-hvdx. |
| 3 | [`8yi9-t44c`](https://www.datos.gov.co/d/8yi9-t44c) | Tráfico Vehicular ANI | Transporte | Agencia Nacional de Infraestructura - ANI | 149.944 | desde: 2014-01-01 → 2026-05-01 | 9 | Recomendado | Fechas reales (desde/hasta); peajes y categorías; tráfico, evasores y tarifa numéricos. |
| 4 | [`3ebi-d83g`](https://www.datos.gov.co/d/3ebi-d83g) | Estado de la prestación del servicio de energía en Zonas No Interconec | Minas y Energía | Instituto de Planificación y Promoción de Sol | 7.091 | fecha_demanda_maxima: 2020-01-02 → 2026-09-30 | 14 | Recomendado | Fecha real con hora; jerarquía dpto→mpio→localidad; energía y potencia numéricas. Año y mes como texto. |
| 5 | [`rtai-k9uh`](https://www.datos.gov.co/d/rtai-k9uh) | Índice de Gobierno Digital - Histórico | Gobierno digital | Ministerio de Tecnologías de la Información y | 108.956 | vigencia: 2018 → 2025 | 18 | Recomendado | Puntajes numéricos bien tipados; entidad, sector, orden e índice como categorías. |
| 6 | [`kekd-7v7h`](https://www.datos.gov.co/d/kekd-7v7h) | Calidad del Aire en Colombia (Promedio Anual) | Ambiente | Instituto de Hidrología | 30.665 | a_o: 2011 → 2025 | 28 | Recomendado | 28 columnas y tipo point; estaciones, variables y estadísticos. Algunas cifras como texto (representatividad, excedencias). |
| 7 | [`nxt2-39c3`](https://www.datos.gov.co/d/nxt2-39c3) | Calidad del Agua para Consumo Humano en Colombia | Salud | Instituto Nacional de Salud INS | 19.160 | a_o: 2007 → 2024 | 11 | Recomendado | IRCA por municipio 2007-2024, con nivel de riesgo categórico. IRCA urbano y rural llegan como texto. |
| 8 | [`5fct-ib9u`](https://www.datos.gov.co/d/5fct-ib9u) | Exportaciones agrícolas no tradicionales y tradicionales | Comercio exterior | Ministerio de Agricultura y Desarrollo Rural  | 544.914 | a_o: 2019 → 2025 | 9 | Posible | 545 mil filas; país, departamento y producto; mes como nombre en texto. |
| 9 | [`ni93-8mm5`](https://www.datos.gov.co/d/ni93-8mm5) | Precios base de minerales para la Liquidación de Regalías | Minería | Unidad de Planeación Minero Energética - UPME | 5.868 | fecha_de_resolucion: 1994-10-24 → 2026-06-30 | 7 | Posible | Pequeño; tres fechas reales (resolución, inicio, fin); bueno para preguntas de rango de fechas. |
| 10 | [`7atu-2b28`](https://www.datos.gov.co/d/7atu-2b28) | Tráfico de pasajeros y carga férreo en Colombia | Transporte | Superintendencia de Transporte - SUPERTRANSPO | 101.322 | fecha_operacion: 2018-01-01 → 2026-09-27 | 16 | Posible | Origen-destino con coordenadas; carga y pasajeros. Solapa sector con 8yi9-t44c. |
| 11 | [`96sh-4v8d`](https://www.datos.gov.co/d/96sh-4v8d) | Entradas de extranjeros a Colombia | Migración | Unidad Administrativa Especial Migración Colo | 181.186 | a_o: 2012 → 2026 | 9 | Posible | Nacionalidad, sexo y mes; año y mes como texto; punto guardado como texto. |
| 12 | [`ekup-y869`](https://www.datos.gov.co/d/ekup-y869) | Tarifas de gas natural para hogares - EPM | Servicios públicos | E.S.P. Empresas Públicas de Medellín - EPM | 664 | — | 7 | Posible | Solo 664 filas; estrato y cargos; útil para preguntas simples. |
| 13 | [`gim6-e69u`](https://www.datos.gov.co/d/gim6-e69u) | Población Sistema del Subsidio Familiar | Trabajo | Superintendencia del Subsidio Familiar - SUPE | 1.176 | a_o: 2024 → 2025 | 12 | Posible | 1.176 filas; afiliados por caja de compensación; año como texto. |
| 14 | [`26um-zdwn`](https://www.datos.gov.co/d/26um-zdwn) | PRIMERAS CAUSAS DE MORBILIDAD | Salud | E.S.E. Instituto de Salud de Bucaramanga | 3.442 | a_o: 2021 → 2026 | 7 | Posible | Datos agregados de morbilidad (Bucaramanga) con código CIE-10; ámbito local. |
| 15 | [`nsz2-kzcq`](https://www.datos.gov.co/d/nsz2-kzcq) | Normales Climatológicas de Colombia | Ambiente | Instituto de Hidrología | 16.761 | periodo: 1961-1990 → 1991-2020 | 24 | Posible | Formato ancho (una columna por mes): exige preguntas sobre columnas, no filas. Interesante como caso difícil. |
| 16 | [`xyy7-rn7p`](https://www.datos.gov.co/d/xyy7-rn7p) | Quejas interpuestas por los consumidores financieros en contra de las  | Finanzas | Superintendencia Financiera de Colombia - SUP | 1.400.425 | a_o_creacion: 2023 → 2026 | 10 | Con reservas | 1,4 millones de filas; tipo y código de entidad sin etiqueta legible. |
| 17 | [`daed-z4fw`](https://www.datos.gov.co/d/daed-z4fw) | FURAG | Función pública | Departamento Administrativo de la Función Púb | 1.011.662 | vigencia: 2022 → 2025 | 16 | Con reservas | 1 millón de filas; puntajes y códigos como texto ("47.66", "6,418"). |
| 18 | [`6cat-2gcs`](https://www.datos.gov.co/d/6cat-2gcs) | 10.000 Empresas mas Grandes del País | Empresas | Superintendencia de Sociedades SuperSociedade | 50.000 | a_o_de_corte: 2021.00 → 2025.00 | 14 | Con reservas | Cifras financieras como texto con símbolo ("$ 100.59"): no se pueden sumar ni ordenar. |
| 19 | [`y9ga-zwzy`](https://www.datos.gov.co/d/y9ga-zwzy) | MEN_ESTADISTICAS MATRICULA POR MUNICIPIOS_ES | Educación | Alcaldía de Sipí | 19.618 | a_o: 2005 → 2021 | 12 | Con reservas | Inconsistencias (nombre_del_departamento = "11"); publicado por una alcaldía; termina en 2021. |
| 20 | [`6hgx-q9pi`](https://www.datos.gov.co/d/6hgx-q9pi) | Proyectos de Investigación e Innovación evaluados y aprobados desde el | Ciencia y tecnología | Ministerio de Ciencia | 3.155 | fecha_registro: 2009-01-16 → 2021-10-19 | 31 | Con reservas | 31 columnas con muchos "No disponible"; termina en 2021. |

Referencia ya probada: `gcq5-hvdx` (vacunación fiebre aftosa, Vichada; 2.877 filas; solo 2024).

## Observación general

Muchos conjuntos guardan años, meses o cifras como texto. Además de convertir los valores devueltos (todos llegan como cadenas), la capa debe decidir si expone esas columnas con su tipo declarado (`String`) o con un tipo corregido. Lo segundo exige una tabla de correcciones por conjunto.
