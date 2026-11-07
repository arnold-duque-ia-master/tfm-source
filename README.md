# tfm-source

Código del Trabajo Fin de Máster *Asistente Texto-a-GraphQL para datos.gov.co: comparativa de Qwen2.5-Coder y CodeLlama ajustados con QLoRA* (UNIR, Máster Universitario en Inteligencia Artificial), de Andrea Paola Castiblanco Carreño y Arnold Humberto Duque Velásquez.

El asistente traduce preguntas en español a consultas GraphQL sobre 9 conjuntos de datos del portal datos.gov.co, que actúa como caso de estudio. Este repositorio contiene la capa GraphQL de solo lectura sobre la API SODA3 del portal, el conjunto de pares pregunta → GraphQL para ajustar los modelos y las mediciones de la capa.

## Módulos

| Carpeta | Contenido | Documentación |
|---|---|---|
| [`spike-soda3/`](spike-soda3/) | Prueba inicial de la API SODA3, selección de los 9 conjuntos y metadatos del catálogo | [`HALLAZGOS.md`](spike-soda3/HALLAZGOS.md), [`CANDIDATOS.md`](spike-soda3/CANDIDATOS.md) |
| [`capa-graphql/`](capa-graphql/) | Capa GraphQL: perfilado de columnas, generación de esquemas, traducción a SoQL, caché, servidor HTTP con GraphiQL y pruebas | [`README.md`](capa-graphql/README.md), [`CONVENCIONES.md`](capa-graphql/CONVENCIONES.md) |
| [`dataset/`](dataset/) | Conjunto de 1.361 pares pregunta → GraphQL validados por esquema y ejecución, con particiones train/val/test y un conjunto reservado | [`README.md`](dataset/README.md) |
| [`medicion-latencia/`](medicion-latencia/) | Medición reproducible de la latencia de la capa con y sin caché | [`README.md`](medicion-latencia/README.md) |

## Puesta en marcha

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r capa-graphql/requirements.txt
cp spike-soda3/.env.example spike-soda3/.env      # completar SOCRATA_KEY_ID y SOCRATA_KEY_SECRET
cd capa-graphql && python3 servidor.py             # http://127.0.0.1:8000/graphql
```

Las credenciales de la API de datos.gov.co se leen de `spike-soda3/.env` o de variables de entorno y nunca se versionan.

## Pruebas

```bash
cd capa-graphql
python3 test_generador.py      # generación de los 9 esquemas (sin red)
python3 test_traductor.py      # traducción GraphQL → SoQL; las 20 tripletas de referencia coinciden carácter a carácter (sin red)
python3 test_servidor.py       # servicio, rutas HTTP, caché y modo sin conexión
python3 prueba_vivo.py         # 20 consultas de extremo a extremo sobre los 9 conjuntos (requiere credenciales)
```

## Datos

Los conjuntos de datos proceden de datos.gov.co: `gcq5-hvdx` se publica con licencia CC BY 4.0 y los otros 8, con CC BY-SA 4.0. Ninguno contiene datos personales; la columna `predio` de `gcq5-hvdx` se excluye del esquema por precaución.
