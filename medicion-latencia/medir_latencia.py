"""Medición de la latencia de la capa GraphQL con y sin caché.

Ejecuta las 20 consultas de extremo a extremo de `capa-graphql/prueba_vivo.py` a través del
servicio completo (validación, traducción a SoQL, consulta a datos.gov.co y conversión):

- rondas en frío: cada ronda usa una caché nueva y vacía, así que todas las consultas van al portal;
- rondas en caliente: reutilizan la caché de la última ronda en frío, así que ninguna va al portal.

El tiempo medido es el que devuelve el servicio en `extensions.ms`: desde que recibe la consulta
hasta que devuelve la respuesta convertida. No usa la caché ni el registro de la capa
(`~/.cache/tfm-graphql/` y `capa-graphql/logs/`): todo se escribe en la carpeta de salida.

Uso (desde esta carpeta, con las dependencias de `capa-graphql/requirements.txt`):
    python3 medir_latencia.py                       # 3 rondas en frío y 3 en caliente
    python3 medir_latencia.py --rondas 5 --salida resultados/prueba

Credenciales: las mismas que la capa (`../spike-soda3/.env` o variables de entorno
SOCRATA_KEY_ID y SOCRATA_KEY_SECRET, o SOCRATA_APP_TOKEN).
"""
import argparse
import json
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def percentil(ordenados, p):
    """Percentil por rango más cercano inferior (el mismo método usado en la memoria)."""
    return ordenados[int(p * (len(ordenados) - 1))]


def resumen(valores):
    xs = sorted(valores)
    return {"ejecuciones": len(xs), "min": xs[0], "mediana": statistics.median(xs),
            "media": round(statistics.mean(xs)), "p90": percentil(xs, 0.9), "max": xs[-1]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rondas", type=int, default=3, help="rondas por escenario (por defecto 3)")
    ap.add_argument("--salida", type=Path, default=HERE / "resultados" / date.today().isoformat(),
                    help="carpeta de resultados (por defecto resultados/AAAA-MM-DD)")
    ap.add_argument("--capa", type=Path, default=HERE.parent / "capa-graphql",
                    help="carpeta de la capa GraphQL (por defecto ../capa-graphql)")
    args = ap.parse_args()

    capa = args.capa.resolve()
    sys.path.insert(0, str(capa))
    sys.path.insert(0, str(capa.parent / "spike-soda3"))
    from servicio import Servicio          # noqa: E402
    from soda_cliente import SodaCliente   # noqa: E402
    from prueba_vivo import CONSULTAS      # noqa: E402

    salida = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)
    for f in list(salida.glob("cache_*.sqlite")) + list(salida.glob("log_*.jsonl")):
        f.unlink()   # cada medición empieza con cachés vacías

    filas = []

    def ronda(nombre, cache):
        sv = Servicio(cliente=SodaCliente(cache_path=cache), log_path=salida / f"log_{nombre}.jsonl")
        for i, q in enumerate(CONSULTAS, 1):
            r = sv.ejecutar(q)
            e = r.get("extensions") or {}
            filas.append({"ronda": nombre, "consulta": i, "ok": "errors" not in r, "ms": e.get("ms"),
                          "cache": e.get("cache"), "filas": e.get("filas"), "dataset": e.get("dataset")})
            print(f"{nombre:<10} [{i:02}] {'OK ' if 'errors' not in r else 'ERR'} {e.get('ms')} ms", flush=True)

    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for k in range(1, args.rondas + 1):
        ronda(f"frio{k}", salida / f"cache_frio{k}.sqlite")
    for k in range(1, args.rondas + 1):
        ronda(f"caliente{k}", salida / f"cache_frio{args.rondas}.sqlite")

    frio = [f["ms"] for f in filas if f["ronda"].startswith("frio") and f["ok"]]
    caliente = [f["ms"] for f in filas if f["ronda"].startswith("caliente") and f["ok"]]
    res = {"inicio_utc": inicio, "rondas_por_escenario": args.rondas, "consultas": len(CONSULTAS),
           "correctas": sum(f["ok"] for f in filas), "total": len(filas),
           "cache_en_frio": sorted({str(f["cache"]) for f in filas if f["ronda"].startswith("frio")}),
           "cache_en_caliente": sorted({str(f["cache"]) for f in filas if f["ronda"].startswith("caliente")}),
           "sin_cache": resumen(frio) if frio else None, "con_cache": resumen(caliente) if caliente else None}
    (salida / "ejecuciones.json").write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf8")
    (salida / "resumen.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf8")

    print(f"\n{res['correctas']}/{res['total']} ejecuciones correctas. Resultados en {salida}\n")
    print("| Escenario | Ejecuciones | Mediana (ms) | Media (ms) | P90 (ms) | Mín. (ms) | Máx. (ms) |")
    print("|---|---|---|---|---|---|---|")
    for nombre, s in (("Sin caché", res["sin_cache"]), ("Con caché", res["con_cache"])):
        if s:
            print(f"| {nombre} | {s['ejecuciones']} | {s['mediana']} | {s['media']} | {s['p90']} | {s['min']} | {s['max']} |")


if __name__ == "__main__":
    main()
