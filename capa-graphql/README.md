# Capa GraphQL sobre datos.gov.co

Capa de solo lectura que expone 9 conjuntos de datos.gov.co con un esquema GraphQL tipado y traduce cada consulta a SoQL (API SODA3). Las convenciones están en [`CONVENCIONES.md`](CONVENCIONES.md).

## Puesta en marcha

```bash
pip install -r requirements.txt
# Credenciales en ../spike-soda3/.env (SOCRATA_KEY_ID y SOCRATA_KEY_SECRET, o SOCRATA_APP_TOKEN)
python3 servidor.py                 # http://127.0.0.1:8000/graphql (GraphiQL en el navegador)
python3 servidor.py --offline       # solo responde desde la caché (respaldo para la demostración)
```

| Ruta | Uso |
|---|---|
| `POST /graphql` | `{"query": "..."}`; la respuesta incluye en `extensions` el conjunto, la SoQL, las filas, el tiempo y si vino de la caché |
| `GET /graphql` | GraphiQL para explorar el esquema y probar consultas |
| `GET /conjuntos` | Conjuntos disponibles |
| `GET /esquema/{id o alias}` | SDL compacto del conjunto (la entrada del modelo) |
| `GET /salud` | Estado del servidor |

La caché se guarda en `~/.cache/tfm-graphql/soda.sqlite`, fuera de la carpeta sincronizada; se puede cambiar con `SODA_CACHE`. Las consultas se registran en `logs/consultas.jsonl` (sirve para medir la latencia).

## Piezas

| Paso | Archivo | Función |
|---|---|---|
| 2 | `perfilar_columnas.py` | Perfila las columnas (valores distintos, enteros, fechas con hora) → `perfiles/` |
| 4 | `datasets.yaml`, `generador.py` | Registro de conjuntos y generación de esquemas → `esquemas/` |
| 5 | `traductor.py` | GraphQL → SoQL y conversión de la respuesta |
| 6 | `soda_cliente.py`, `servicio.py`, `servidor.py` | Cliente SODA3 con caché, ejecución completa y servidor HTTP |

Para regenerar los esquemas tras cambiar el registro: `python3 generador.py`.

## Pruebas

```bash
python3 test_generador.py           # generador (sin red)
python3 test_traductor.py           # traductor; las 20 tripletas coinciden carácter a carácter (sin red)
python3 test_servidor.py [--vivo]   # servicio, rutas HTTP, caché y modo offline
python3 prueba_vivo.py              # 20 consultas de extremo a extremo sobre los 9 conjuntos
python3 validar_ejemplos.py gcq5-hvdx
```
