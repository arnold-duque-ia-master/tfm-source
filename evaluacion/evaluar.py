"""Evaluación técnica de un archivo de predicciones (OE4, capítulo 6).

Sirve para cualquier modelo que escriba el formato común de predicciones (ver README): la línea
base de recuperación y Qwen2.5-Coder y CodeLlama ajustados. Para cada par de la partición mide:

- `valida_sintaxis`: la consulta se puede analizar (`graphql.parse`);
- `valida_esquema`: no tiene errores de `graphql.validate` contra el esquema de la capa;
- `coincidencia_exacta`: su forma impresa por graphql-core es idéntica a la de la referencia;
- `coincidencia_estructural`: es idéntica salvo en los valores de los filtros (`where`); mide si se
  acierta la estructura de la consulta aunque no los valores;
- `exactitud_ejecucion` (métrica principal): la predicción y la referencia se ejecutan con la capa
  (traducción, SODA y conversión) y devuelven el mismo resultado. Las filas se comparan como
  multiconjunto, salvo que la referencia tenga `orderBy`, en cuyo caso importa el orden. Los números
  se comparan redondeados a 6 decimales;
- `ms`: latencia de inferencia, si la escribe el modelo.

La referencia se vuelve a ejecutar en el mismo momento que la predicción, de modo que ambas se
comparan sobre la misma instantánea del portal. Con la caché de la capa (o `--offline`) las
ejecuciones son repetibles.

Uso (desde esta carpeta, con las dependencias de `../capa-graphql/requirements.txt`):
    python3 evaluar.py predicciones/linea-base-recuperacion/test.jsonl
    python3 evaluar.py predicciones/qwen-qlora/test.jsonl --offline

Salida: `resultados/<modelo>/<particion>.jsonl` (un registro por par) y `<particion>.resumen.json`
(totales, por conjunto y por categoría). Credenciales: las de la capa (`../spike-soda3/.env`).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAIZ = HERE.parent
CAPA = RAIZ / "capa-graphql"
DATASET = RAIZ / "dataset"
METRICAS = ["valida_sintaxis", "valida_esquema", "coincidencia_exacta", "coincidencia_estructural",
            "exactitud_ejecucion"]


def leer(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf8").splitlines() if l.strip()]


def norm(v):
    if isinstance(v, float):
        return round(v, 6)
    if isinstance(v, dict):
        return tuple(sorted((k, norm(x)) for k, x in v.items()))
    if isinstance(v, list):
        return tuple(norm(x) for x in v)
    return v


def resultado(r: dict):
    """Filas de la respuesta de la capa, o None si hubo errores."""
    if r.get("errors") or not r.get("data"):
        return None
    return next(iter(r["data"].values()))


def iguales(pred_rows, ref_rows, ordenado: bool) -> bool:
    a = [norm(x) for x in pred_rows]
    b = [norm(x) for x in ref_rows]
    return a == b if ordenado else Counter(a) == Counter(b)


def estructura(doc) -> str:
    """Forma impresa de la consulta con los valores de los filtros (`where`) sustituidos por `$v`.

    Conserva todo lo demás (campos, agregados, orden, límite y operadores), así que dos consultas
    con la misma estructura solo difieren en los valores con los que se filtra. Un escalar o una
    lista de escalares (`in: [...]`) cuenta como un valor; las listas de objetos (`_or`) conservan
    su estructura."""
    import graphql
    from graphql.language import ast

    v = ast.VariableNode(name=ast.NameNode(value="v"))

    class Vaciar(graphql.Visitor):
        def __init__(self):
            super().__init__()
            self.en_where = 0

        def enter_argument(self, node, *_):
            if node.name.value == "where":
                self.en_where += 1

        def leave_argument(self, node, *_):
            if node.name.value == "where":
                self.en_where -= 1

        def enter_list_value(self, node, *_):
            if self.en_where and not all(isinstance(x, ast.ObjectValueNode) for x in node.values):
                return v

        def _escalar(self, node, *_):
            if self.en_where:
                return v

        enter_int_value = enter_float_value = enter_string_value = _escalar
        enter_boolean_value = enter_enum_value = enter_null_value = _escalar

    return graphql.print_ast(graphql.visit(doc, Vaciar()))


def tiene_orden(doc) -> bool:
    import graphql

    class V(graphql.Visitor):
        hay = False

        def enter_argument(self, node, *_):
            if node.name.value == "orderBy":
                V.hay = True

    graphql.visit(doc, V())
    return V.hay


def evaluar_par(svc, ref: dict, pred: dict, cache_ref: dict) -> dict:
    import graphql
    out = {"id": ref["id"], "dataset": ref["dataset"], "categoria": ref["categoria"],
           "graphql_ref": ref["graphql"], "graphql_pred": pred.get("graphql"), "ms": pred.get("ms"),
           **{m: False for m in METRICAS}, "error": None}
    q = pred.get("graphql")
    if not q:
        out["error"] = pred.get("error") or "sin predicción"
        return out
    try:
        doc = graphql.parse(q)
    except graphql.GraphQLError as e:
        out["error"] = "sintaxis: " + e.message
        return out
    out["valida_sintaxis"] = True
    errs = graphql.validate(svc.schema, doc)
    if errs:
        out["error"] = "esquema: " + errs[0].message
        return out
    out["valida_esquema"] = True
    doc_ref = graphql.parse(ref["graphql"])
    out["coincidencia_exacta"] = graphql.print_ast(doc) == graphql.print_ast(doc_ref)
    out["coincidencia_estructural"] = estructura(doc) == estructura(doc_ref)

    if ref["graphql"] not in cache_ref:
        cache_ref[ref["graphql"]] = svc.ejecutar(ref["graphql"])
    r_ref = cache_ref[ref["graphql"]]
    filas_ref = resultado(r_ref)
    if filas_ref is None:
        out["error"] = "referencia: " + r_ref["errors"][0]["message"][:160]
        out["referencia_fallida"] = True
        return out
    r_pred = r_ref if q == ref["graphql"] else svc.ejecutar(q)
    filas_pred = resultado(r_pred)
    if filas_pred is None:
        e = r_pred["errors"][0]
        out["error"] = "ejecución: " + e.get("extensions", {}).get("code", "") + " " + e["message"][:160]
        return out
    out["exactitud_ejecucion"] = iguales(filas_pred, filas_ref, tiene_orden(doc_ref))
    return out


def tasas(regs: list[dict]) -> dict:
    n = len(regs)
    d = {"n": n}
    for m in METRICAS:
        k = sum(r[m] for r in regs)
        d[m] = {"aciertos": k, "tasa": round(k / n, 4) if n else None}
    ms = [r["ms"] for r in regs if r.get("ms") is not None]
    if ms:
        d["ms_inferencia"] = {"mediana": statistics.median(ms), "media": round(statistics.mean(ms), 1),
                              "max": max(ms)}
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("predicciones", type=Path, help="archivo <particion>.jsonl con el formato común")
    ap.add_argument("--particion", help="test, val o reservado; por defecto, el nombre del archivo")
    ap.add_argument("--offline", action="store_true", help="responder solo desde la caché de la capa")
    ap.add_argument("--salida", type=Path, help="carpeta de salida; por defecto resultados/<modelo>")
    args = ap.parse_args()

    sys.path.insert(0, str(CAPA))
    from servicio import Servicio
    from soda_cliente import SodaCliente

    particion = args.particion or args.predicciones.stem
    refs = leer(DATASET / f"{particion}.jsonl")
    preds = {p["id"]: p for p in leer(args.predicciones)}
    faltan = [r["id"] for r in refs if r["id"] not in preds]
    if faltan:
        print(f"aviso: {len(faltan)} pares sin predicción (cuentan como fallos), p. ej. {faltan[:3]}")
    modelo = next(iter(preds.values()), {}).get("modelo") or args.predicciones.parent.name
    salida = args.salida or HERE / "resultados" / modelo
    salida.mkdir(parents=True, exist_ok=True)

    svc = Servicio(esquemas=CAPA / "esquemas", cliente=SodaCliente(offline=args.offline), log_path=None)
    cache_ref: dict = {}
    regs = []
    with open(salida / f"{particion}.jsonl", "w", encoding="utf8") as fh:
        for i, ref in enumerate(refs, 1):
            r = evaluar_par(svc, ref, preds.get(ref["id"], {}), cache_ref)
            regs.append(r)
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            if i % 25 == 0:
                print(f"{i}/{len(refs)}", flush=True)

    por = lambda clave: {k: tasas(v) for k, v in sorted(_agrupar(regs, clave).items())}  # noqa: E731
    resumen = {
        "modelo": modelo, "particion": particion, "predicciones": str(args.predicciones),
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), "offline": args.offline,
        "referencias_fallidas": sum(1 for r in regs if r.get("referencia_fallida")),
        "errores": dict(Counter(r["error"].split(":")[0] for r in regs if r["error"])),
        "total": tasas(regs), "por_conjunto": por("dataset"), "por_categoria": por("categoria"),
    }
    (salida / f"{particion}.resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n",
                                                     encoding="utf8")
    t = resumen["total"]
    print(f"{modelo} / {particion}: n={t['n']}  " + "  ".join(f"{m}={t[m]['tasa']:.1%}" for m in METRICAS))
    if resumen["referencias_fallidas"]:
        print(f"aviso: {resumen['referencias_fallidas']} referencias no se pudieron ejecutar")


def _agrupar(regs, clave):
    g = defaultdict(list)
    for r in regs:
        g[r[clave]].append(r)
    return g


if __name__ == "__main__":
    main()
