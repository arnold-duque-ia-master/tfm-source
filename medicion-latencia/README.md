# Medición de la latencia de la capa GraphQL

Mide el tiempo que tarda la capa GraphQL (`../capa-graphql`) en responder cada consulta, con y sin caché. Es la medición del apartado 5.6 de la memoria (Tabla 13) y la evidencia del requisito RNF-06.

## Qué mide

Ejecuta las 20 consultas de extremo a extremo de `capa-graphql/prueba_vivo.py`, que cubren los 9 conjuntos, a través del servicio completo: validación, traducción a SoQL, consulta a datos.gov.co y conversión de la respuesta.

| Escenario | Cómo se consigue |
|---|---|
| Sin caché | Cada ronda en frío usa una caché nueva y vacía, así que todas las consultas van al portal |
| Con caché | Las rondas en caliente reutilizan la caché de la última ronda en frío, así que ninguna va al portal |

- El tiempo es el que devuelve el servicio en `extensions.ms`: desde que recibe la consulta hasta que devuelve la respuesta convertida.
- El percentil 90 se calcula por rango más cercano inferior: `ordenados[int(0.9 * (n - 1))]`.
- No toca la caché ni el registro de la capa (`~/.cache/tfm-graphql/` y `capa-graphql/logs/`): las cachés y los registros de cada ronda se escriben en la carpeta de salida.

## Uso

```bash
pip install -r ../capa-graphql/requirements.txt   # credenciales en ../spike-soda3/.env
python3 medir_latencia.py                         # 3 rondas en frío y 3 en caliente → resultados/AAAA-MM-DD/
python3 medir_latencia.py --rondas 5 --salida resultados/prueba
```

Al terminar imprime una tabla en Markdown con la mediana, la media, el percentil 90, el mínimo y el máximo de cada escenario.

## Archivos de salida

| Archivo | Contenido |
|---|---|
| `resumen.json` | Fecha de inicio (UTC), rondas, ejecuciones correctas y estadísticas de cada escenario |
| `ejecuciones.json` | Una entrada por ejecución: ronda, consulta, si fue correcta, milisegundos, uso de la caché, filas y conjunto |
| `log_<ronda>.jsonl` | Registro del servicio en cada ronda: consulta, SoQL, filas, tiempo total, tiempo de SODA y caché |
| `cache_frio<k>.sqlite` | Cachés de cada ronda en frío; no se versionan (`*.sqlite` en `.gitignore`) |

## Resultados

| Fecha | Ejecuciones | Sin caché: mediana / media / p90 / máx. (ms) | Con caché: mediana / máx. (ms) | Uso |
|---|---|---|---|---|
| 06/11/2026 (`resultados/2026-11-06/`) | 120/120 correctas | 279 / 524 / 703 / 4.591 | 1 / 10 | Tabla 13 del Borrador 2 |

La medición del 06/11/2026 se hizo con una versión previa de este script, con la misma lógica (mismas consultas, rondas, cachés y estadísticas); sus resultados se pasaron al formato actual. El portal es muy variable: en una prueba posterior de una ronda, el máximo sin caché llegó a 7,2 s. Para la memoria conviene citar siempre la mediana, el percentil 90 y la fecha de la medición.
