"""Construcción del conjunto de datos Texto→GraphQL (OE3).

Fases (se ejecutan en orden; cada una guarda su salida en dataset/trabajo/):
  python3 construir.py explorar   consulta a la capa los valores reales de cada conjunto (años, valores frecuentes, medias)
  python3 construir.py generar    instancia las plantillas con el léxico y los valores → candidatos.jsonl
  python3 construir.py validar    valida cada candidato contra el esquema y lo ejecuta en datos.gov.co → validados.jsonl
  python3 construir.py particionar  70/15/15 por consulta en 8 conjuntos; ni93-8mm5 reservado → train/val/test/reservado.jsonl

Requisitos: los de capa-graphql/requirements.txt y credenciales en spike-soda3/.env.
La caché SQLite de la capa hace que repetir la validación no vuelva a consultar el portal.
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPA = HERE.parent / "capa-graphql"
sys.path.insert(0, str(CAPA))
sys.path.insert(0, str(HERE))

from lexico import LEXICO, MESES  # noqa: E402

TRABAJO = HERE / "trabajo"
TRABAJO.mkdir(exist_ok=True)
SEMILLA = 20261101

# ----------------------------------------------------------------------------- utilidades de la capa

def servicio():
    from servicio import Servicio
    return Servicio(esquemas=CAPA / "esquemas", log_path=None)


def mappings():
    out = {}
    for f in (CAPA / "esquemas").glob("*.mapping.json"):
        m = json.loads(f.read_text(encoding="utf8"))
        out[m["id"]] = m
    return out


def orden_where(schema, tipo):
    t = schema.type_map[f"{tipo}Where"]
    return list(t.fields.keys())


# ----------------------------------------------------------------------------- consultas canónicas

def lit(v):
    if isinstance(v, Enum):
        return v.name
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(lit(x) for x in v) + "]"
    return json.dumps(v, ensure_ascii=False)


class Enum:
    def __init__(self, name):
        self.name = name

    def __eq__(self, o):
        return isinstance(o, Enum) and o.name == self.name

    def __hash__(self):
        return hash(self.name)


OPS = ["eq", "neq", "in", "nin", "gt", "gte", "lt", "lte", "contains", "startsWith", "isNull"]


def fmt_where(w, order):
    parts = []
    cols = [k for k in w if not k.startswith("_")]
    cols.sort(key=lambda k: order.index(k))
    for k in cols:
        ops = w[k]
        inner = ", ".join(f"{op}: {lit(ops[op])}" for op in OPS if op in ops)
        parts.append(f"{k}: {{{inner}}}")
    for k in ("_and", "_or"):
        if k in w:
            parts.append(f"{k}: [" + ", ".join(fmt_where(x, order) for x in w[k]) + "]")
    if "_not" in w:
        parts.append("_not: " + fmt_where(w["_not"], order))
    return "{" + ", ".join(parts) + "}"


def fmt_order(ob):
    items = []
    for o in ob:
        (k, v), = o.items()
        if isinstance(v, dict):
            (k2, d), = v.items()
            items.append(f"{{{k}: {{{k2}: {d}}}}}")
        else:
            items.append(f"{{{k}: {v}}}")
    return "[" + ", ".join(items) + "]"


def consulta(alias, agg, sel, order, where=None, orderBy=None, limit=None, offset=None):
    args = []
    if where:
        args.append("where: " + fmt_where(where, order))
    if orderBy:
        args.append("orderBy: " + fmt_order(orderBy))
    if limit is not None:
        args.append(f"limit: {limit}")
    if offset:
        args.append(f"offset: {offset}")
    root = alias + ("Aggregate" if agg else "")
    a = f"({', '.join(args)})" if args else ""
    s = []
    for x in sel:
        if isinstance(x, tuple):
            s.append(f"{x[0]} {{ {' '.join(x[1])} }}")
        else:
            s.append(x)
    return f"{{ {root}{a} {{ {' '.join(s)} }} }}"


# ----------------------------------------------------------------------------- texto en español

MENORES = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "o", "a", "por", "con"}


def titulo(v):
    out = []
    for i, w in enumerate(v.lower().split(" ")):
        if i and w in MENORES:
            out.append(w)
        elif "." in w and len(w) <= 5:
            out.append(w.upper())
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def mostrar_valor(v, estilo):
    if estilo == "title":
        return titulo(v)
    if estilo == "lower":
        return v.lower()
    if estilo == "lowerfirst":
        return v if (len(v) > 1 and v[:2].isupper()) else v[:1].lower() + v[1:]
    return v


def num(x):
    """1234567.5 → '1.234.567,5' (formato español)."""
    if isinstance(x, float) and not x.is_integer():
        e, d = f"{x:.2f}".split(".")
        return f"{int(e):,}".replace(",", ".") + "," + d.rstrip("0")
    return f"{int(x):,}".replace(",", ".")


def redondo(x):
    if x <= 0:
        return 1
    import math
    p = 10 ** max(0, int(math.log10(x)) - 1)
    return int(round(x / p) * p) or 1


def C(s):
    i = 1 if s.startswith("¿") else 0
    return s[:i] + s[i:i + 1].upper() + s[i + 1:]


def cuantos(g):
    return "cuántas" if g == "f" else "cuántos"


def los(g):
    return "las" if g == "f" else "los"


# ----------------------------------------------------------------------------- exploración

def explorar():
    svc = servicio()
    maps = mappings()
    out = {}
    for ds, lx in LEXICO.items():
        a, m = lx["alias"], maps[ds]
        info = {"anios": [], "dims": {}, "medias": {}, "meses": []}
        def q(s):
            r = svc.ejecutar(s)
            if r.get("errors"):
                print("  ERROR", s, r["errors"][0]["message"][:200])
                return []
            return r["data"][a + "Aggregate"] if a + "Aggregate" in r["data"] else r["data"][a]
        t = lx["tiempo"]["campo"]
        info["anios"] = [x[t] for x in q(f"{{ {a}Aggregate(orderBy: [{{{t}: ASC}}]) {{ {t} count }} }}") if x[t] is not None]
        for d in lx["dims"]:
            rows = q(f"{{ {a}Aggregate(orderBy: [{{count: DESC}}], limit: 30) {{ {d} count }} }}")
            col = m["columns"][d]
            vals = []
            for r in rows:
                v = r[d]
                if v is None:
                    continue
                if col["kind"] == "enum":
                    vals.append({"enum": v, "texto": col["enum"][v][0], "n": r["count"]})
                else:
                    if not str(v).strip():
                        continue
                    vals.append({"texto": v, "n": r["count"]})
            info["dims"][d] = vals
        for md in lx["medidas"]:
            r = q(f"{{ {a}Aggregate {{ avg {{ {md} }} max {{ {md} }} }} }}")
            if r:
                info["medias"][md] = {"avg": r[0]["avg"][md], "max": r[0]["max"][md]}
        if lx["fecha"]:
            f = lx["fecha"]["campo"]
            rows = q(f"{{ {a}Aggregate(orderBy: [{{{f}Year: DESC}}, {{{f}Month: DESC}}], limit: 36) {{ {f}Year {f}Month count }} }}")
            info["meses"] = [(r[f + "Year"], r[f + "Month"]) for r in rows if r[f + "Year"]]
        out[ds] = info
        print(ds, "años:", info["anios"][:3], "…", "dims:", {k: len(v) for k, v in info["dims"].items()}, "meses:", len(info["meses"]))
    (TRABAJO / "valores.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")


# ----------------------------------------------------------------------------- plantillas

class Ctx:
    def __init__(self, ds, lx, info, m, order, rng):
        self.ds, self.lx, self.info, self.m, self.order, self.rng = ds, lx, info, m, order, rng
        self.a = lx["alias"]
        self.rng_txt = random.Random(rng.random())   # la redacción no altera la secuencia de consultas
        # los enum fusionados aparecen varias veces al agrupar por la columna original: se deduplican
        for d, vals in info["dims"].items():
            vistos, limpio = set(), []
            for v in vals:
                k = v.get("enum", v["texto"])
                if k in vistos:
                    continue
                vistos.add(k); limpio.append(v)
            info["dims"][d] = limpio

    # valores
    def dims(self, kinds=("enum", "string")):
        return [d for d in self.lx["dims"] if self.m["columns"][d]["kind"] in kinds and self.info["dims"].get(d)]

    def valor(self, d, top=12):
        vals = self.info["dims"][d][:top]
        v = self.rng.choice(vals)
        return self.fv(d, v)

    def fv(self, d, v):
        """(literal GraphQL, texto mostrado, frase de filtro)"""
        spec = self.lx["dims"][d]
        base = v["texto"]
        if "enum" in v:
            variantes = self.m["columns"][d]["enum"].get(v["enum"], [base])
            base = max(variantes, key=lambda x: (sum(ch in "áéíóúñÁÉÍÓÚÑ" for ch in x), x[:1].isupper()))
        txt = mostrar_valor(base, spec["estilo"])
        litv = Enum(v["enum"]) if "enum" in v else v["texto"]
        return litv, txt, spec["filtro"].format(v=txt)

    def fm(self, d, f):
        """Filtro detrás de una medida: los filtros relativos a la fila necesitan el sustantivo."""
        if self.lx["dims"][d].get("rel"):
            return f"en {los(self.g)} {self.lx['pl']} {f}"
        return f

    def anio(self):
        return self.rng.choice(self.info["anios"][-6:])

    def medidas(self, agg):
        return [k for k, v in self.lx["medidas"].items() if agg in v["agg"] and k in self.info["medias"]]

    def pick(self, xs):
        return self.rng.choice(xs)

    def q(self, agg, sel, **kw):
        return consulta(self.a, agg, sel, self.order, **kw)

    @property
    def g(self):
        return self.lx["g"]


def P(ctx, opciones, **kw):
    return C(ctx.rng_txt.choice(opciones).format(**kw))


def plantillas():
    T = {}

    def reg(nombre, n):
        def deco(f):
            T[nombre] = (f, n)
            return f
        return deco

    @reg("conteo", 1)
    def _(c):
        return P(c, ["¿{cu} {pl} hay en total?", "Número total de {pl}.", "¿{cu} {pl} contiene el conjunto de datos sobre {tema}?"],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], tema=c.lx["tema"]), c.q(True, ["count"])

    @reg("conteo+filtro", 8)
    def _(c):
        d = c.pick(c.dims()); v, t, f = c.valor(d)
        return P(c, ["¿{cu} {pl} hay {f}?", "Número de {pl} {f}.", "¿{cu} {pl} se registran {f}?"],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], f=f), c.q(True, ["count"], where={d: {"eq": v}})

    @reg("conteo+año", 4)
    def _(c):
        t = c.lx["tiempo"]; y = c.anio()
        return P(c, ["¿{cu} {pl} hay en {y}?", "Número de {pl} con {tn} {y}.", "¿{cu} {pl} corresponden a {y}?"],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], y=y, tn=t["np"]), c.q(True, ["count"], where={t["campo"]: {"eq": y}})

    @reg("suma+filtro", 8)
    def _(c):
        md = c.pick(c.medidas("sum")); d = c.pick(c.dims()); v, t, f = c.valor(d)
        n = c.lx["medidas"][md]["np"]; f = c.fm(d, f)
        return P(c, ["¿Cuál es el total de {n} {f}?", "Total de {n} {f}.", "Suma de {n} {f}."], n=n, f=f), \
            c.q(True, [("sum", [md])], where={d: {"eq": v}})

    @reg("suma+filtros", 6)
    def _(c):
        md = c.pick(c.medidas("sum")); d = c.pick(c.dims()); v, t, f = c.valor(d)
        y = c.anio(); tc = c.lx["tiempo"]["campo"]; n = c.lx["medidas"][md]["np"]; f = c.fm(d, f)
        return P(c, ["¿Cuál fue el total de {n} {f} en {y}?", "Total de {n} {f} durante {y}.", "En {y}, ¿cuánto suma {n} {f}?"],
                 n=n, f=f, y=y), c.q(True, [("sum", [md])], where={d: {"eq": v}, tc: {"eq": y}})

    @reg("promedio+filtro", 6)
    def _(c):
        md = c.pick(c.medidas("avg")); d = c.pick(c.dims()); v, t, f = c.valor(d)
        n = c.lx["medidas"][md]["np"]; f = c.fm(d, f)
        return P(c, ["¿Cuál es el promedio de {n} {f}?", "Promedio de {n} por registro {f}.", "¿Cuál es el valor medio de {n} {f}?"],
                 n=n, f=f), c.q(True, [("avg", [md])], where={d: {"eq": v}})

    @reg("agrupación+orden por agregado", 5)
    def _(c):
        md = c.pick(c.medidas("sum")); d = c.pick(c.dims(("enum",)) or c.dims()); spec = c.lx["dims"][d]
        n = c.lx["medidas"][md]["np"]
        if c.rng.random() < 0.5:
            y = c.anio(); tc = c.lx["tiempo"]["campo"]
            return P(c, ["Total de {n} por {g} en {y}, de mayor a menor.", "¿Cuánto suma {n} en cada {g} en {y}? Ordena de mayor a menor."],
                     n=n, g=spec["np"], y=y), c.q(True, [d, ("sum", [md])], where={tc: {"eq": y}}, orderBy=[{"sum": {md: "DESC"}}])
        return P(c, ["Total de {n} por {g}, de mayor a menor.", "¿Cuánto suma {n} en cada {g}? Ordena de mayor a menor."],
                 n=n, g=spec["np"]), c.q(True, [d, ("sum", [md])], orderBy=[{"sum": {md: "DESC"}}])

    @reg("top-N de grupos", 5)
    def _(c):
        md = c.pick(c.medidas("sum")); d = c.pick(c.dims()); spec = c.lx["dims"][d]
        k = c.pick([3, 5, 10]); n = c.lx["medidas"][md]["np"]
        return P(c, ["¿Cuáles son {los} {k} {gp} con más {n}?", "Los {k} {gp} con mayor total de {n}.", "Top {k} de {gp} según el total de {n}."],
                 los=los(spec["g"]), k=k, gp=spec["pl"], n=n), \
            c.q(True, [d, ("sum", [md])], orderBy=[{"sum": {md: "DESC"}}], limit=k)

    @reg("conteo por grupo", 4)
    def _(c):
        d = c.pick(c.dims()); spec = c.lx["dims"][d]
        return P(c, ["¿{cu} {pl} hay por {g}?", "Número de {pl} por {g}, de mayor a menor.", "Distribución de {pl} por {g}."],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], g=spec["np"]), c.q(True, [d, "count"], orderBy=[{"count": "DESC"}])

    @reg("filas+filtro", 6)
    def _(c):
        d = c.pick(c.dims()); v, t, f = c.valor(d); k = c.pick([5, 10, 20])
        campos = [x for x in c.lx["mostrar"] if x != d][:4]
        return P(c, ["Muestra {k} {pl} {f}.", "Lista {k} {pl} {f}.", "Dame {k} {pl} {f}."], k=k, pl=c.lx["pl"], f=f), \
            c.q(False, campos, where={d: {"eq": v}}, limit=k)

    @reg("filas+orden+límite", 5)
    def _(c):
        md = c.pick(list(c.lx["medidas"])); n = c.lx["medidas"][md]["np"]; k = c.pick([3, 5, 10])
        desc = c.rng.random() < 0.75
        campos = [x for x in c.lx["mostrar"] if x != md][:3] + [md]
        return P(c, ["Muestra {los} {k} {pl} con {mm} {n}.", "¿Cuáles son {los} {k} {pl} con {mm} {n}?"],
                 los=los(c.g), k=k, pl=c.lx["pl"], mm="mayor" if desc else "menor", n=n), \
            c.q(False, campos, orderBy=[{md: "DESC" if desc else "ASC"}], limit=k)

    @reg("mínimo y máximo", 4)
    def _(c):
        md = c.pick(c.medidas("minmax")); n = c.lx["medidas"][md]["np"]
        if c.rng.random() < 0.5:
            d = c.pick(c.dims()); v, t, f = c.valor(d); f = c.fm(d, f)
            return P(c, ["¿Cuáles son el mínimo y el máximo de {n} {f}?", "Valor mínimo y máximo de {n} {f}."], n=n, f=f), \
                c.q(True, [("min", [md]), ("max", [md])], where={d: {"eq": v}})
        return P(c, ["¿Cuáles son el mínimo y el máximo de {n}?", "Rango de {n}: mínimo y máximo."], n=n), \
            c.q(True, [("min", [md]), ("max", [md])])

    @reg("comparación numérica", 5)
    def _(c):
        md = c.pick(list(c.info["medias"])); n = c.lx["medidas"][md]["np"]
        avg = c.info["medias"][md]["avg"] or 1
        x = redondo(avg * c.pick([0.5, 1, 2, 5]))
        op, pal = c.pick([("gt", "mayor que"), ("gte", "mayor o igual que"), ("lt", "menor que")])
        return P(c, ["¿En {cu} {pl} el valor de «{n}» es {pal} {x}?", "Número de {pl} en los que «{n}» es {pal} {x}.", "¿{CU} {pl} tienen un valor de «{n}» {pal} {x}?"],
                 cu=cuantos(c.g), CU=C(cuantos(c.g)), pl=c.lx["pl"], pal=pal, x=num(x), n=n), c.q(True, ["count"], where={md: {op: x}})

    @reg("filtro in", 4)
    def _(c):
        d = c.pick(c.dims()); vals = c.info["dims"][d][:10]
        if len(vals) < 2:
            return None
        a, b = c.rng.sample(vals, 2); (va, ta, fa), (vb, tb, fb) = c.fv(d, a), c.fv(d, b)
        f = f"{fa} o {fb}"
        return P(c, ["¿{cu} {pl} hay {f}?", "Número de {pl} {f}."], cu=C(cuantos(c.g)), pl=c.lx["pl"], f=f), \
            c.q(True, ["count"], where={d: {"in": [va, vb]}})

    @reg("conteo distinto", 3)
    def _(c):
        ds = c.dims(("string",)) or c.dims()
        x = c.pick(ds); sx = c.lx["dims"][x]
        otros = [d for d in c.dims(("enum",)) if d != x]
        if otros and c.rng.random() < 0.6:
            d = c.pick(otros); sd = c.lx["dims"][d]
            return P(c, ["¿{cu} {xp} distint{oa}s hay en cada {g}?", "Número de {xp} diferentes por {g}."],
                     cu=C(cuantos(sx["g"])), xp=sx["pl"], oa="a" if sx["g"] == "f" else "o", g=sd["np"]), \
                c.q(True, [d, ("countDistinct", [x])])
        return P(c, ["¿{cu} {xp} distint{oa}s aparecen en los datos?", "Número de {xp} diferentes."],
                 cu=C(cuantos(sx["g"])), xp=sx["pl"], oa="a" if sx["g"] == "f" else "o"), c.q(True, [("countDistinct", [x])])

    @reg("evolución anual", 4)
    def _(c):
        if c.lx.get("sin_evolucion"):
            return None
        tc, tn = c.lx["tiempo"]["campo"], c.lx["tiempo"]["np"]
        aggs = c.medidas("sum") + c.medidas("avg")
        md = c.pick(aggs); ag = "sum" if md in c.medidas("sum") and c.rng.random() < 0.6 else "avg"
        if md not in c.medidas(ag):
            ag = "avg" if md in c.medidas("avg") else "sum"
        n = c.lx["medidas"][md]["np"]; pal = "total" if ag == "sum" else "promedio"
        where = None; f = ""
        if c.rng.random() < 0.5:
            d = c.pick(c.dims(("enum",)) or c.dims()); v, t, f = c.valor(d); where = {d: {"eq": v}}
            f = f" para {los(c.g)} {c.lx['pl']} {f}"
        return P(c, ["Evolución del {p} de {n} por {tn}{f}.", "{P2} de {n} por {tn}{f}, en orden cronológico."],
                 p=pal, P2=C(pal), n=n, tn=tn, f=f), \
            c.q(True, [tc, (ag, [md])], where=where, orderBy=[{tc: "ASC"}])

    @reg("texto contiene", 5)
    def _(c):
        tx = [d for d in c.lx["texto"] if c.info["dims"].get(d)]
        if not tx:
            return None
        d = c.pick(tx); v = c.rng.choice(c.info["dims"][d][:20])["texto"]
        palabras = [w for w in str(v).replace(",", " ").split() if len(w) >= 4]
        if not palabras:
            return None
        w = c.pick(palabras).lower(); spec = c.lx["dims"][d]
        if c.rng.random() < 0.5:
            return P(c, ["¿{cu} {pl} hay en {gp} cuyo nombre contiene «{w}»?", "Número de {pl} de {gp} que contienen «{w}» en el nombre."],
                     cu=C(cuantos(c.g)), pl=c.lx["pl"], gp=spec["pl"], w=w), c.q(True, ["count"], where={d: {"contains": w}})
        campos = [x for x in c.lx["mostrar"] if x != d][:3]
        return P(c, ["Lista los {pl} cuyo {g} contiene «{w}».", "Muestra los registros de {gp} que contienen «{w}»."],
                 pl=c.lx["pl"], g=spec["np"], gp=spec["pl"], w=w), c.q(False, [d] + campos, where={d: {"contains": w}}, limit=20)

    @reg("rango de años", 4)
    def _(c):
        an = c.info["anios"]
        if len(an) < 3:
            return None
        i = c.rng.randrange(0, len(an) - 2); j = c.rng.randrange(i + 1, len(an))
        a, b = an[i], an[j]; tc = c.lx["tiempo"]["campo"]
        if c.medidas("sum") and c.rng.random() < 0.5:
            md = c.pick(c.medidas("sum")); n = c.lx["medidas"][md]["np"]
            return P(c, ["Total de {n} entre {a} y {b}.", "¿Cuánto suma {n} desde {a} hasta {b}?"], n=n, a=a, b=b), \
                c.q(True, [("sum", [md])], where={tc: {"gte": a, "lte": b}})
        return P(c, ["¿{cu} {pl} hay entre {a} y {b}?", "Número de {pl} desde {a} hasta {b}."],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], a=a, b=b), c.q(True, ["count"], where={tc: {"gte": a, "lte": b}})

    @reg("varias medidas", 3)
    def _(c):
        ms = c.medidas("sum")
        if len(ms) < 2:
            ms = c.medidas("avg"); ag = "avg"
        else:
            ag = "sum"
        if len(ms) < 2:
            return None
        sel = c.rng.sample(ms, 2); sel.sort(key=list(c.lx["medidas"]).index)
        n = " y ".join(c.lx["medidas"][x]["np"] for x in sel); pal = "total" if ag == "sum" else "promedio"
        d = c.pick(c.dims()); v, t, f = c.valor(d); f = c.fm(d, f)
        return P(c, ["{P2} de {n} {f}.", "¿Cuál es el {p} de {n} {f}?"], P2=C(pal), p=pal, n=n, f=f), \
            c.q(True, [(ag, sel)], where={d: {"eq": v}})

    @reg("negación", 4)
    def _(c):
        d = c.pick(c.dims(("enum",)) or c.dims()); v, t, f = c.valor(d, top=5)
        return P(c, ["¿{cu} {pl} hay que no sean {f}?", "Número de {pl} excluyendo los {f}."], cu=C(cuantos(c.g)), pl=c.lx["pl"], f=f), \
            c.q(True, ["count"], where={d: {"neq": v}})

    @reg("rango de fechas", 4)
    def _(c):
        if not c.lx["fecha"] or not c.info["meses"]:
            return None
        y, mth = c.pick(c.info["meses"]); f = c.lx["fecha"]["campo"]
        ini = f"{y:04d}-{mth:02d}-01"; fin = f"{y + (mth == 12):04d}-{mth % 12 + 1:02d}-01"
        return P(c, ["¿{cu} {pl} tienen {fn} en {m} de {y}?", "Número de {pl} con {fn} en {m} de {y}."],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], fn=c.lx["fecha"]["np"], m=MESES[mth - 1], y=y), \
            c.q(True, ["count"], where={f: {"gte": ini, "lt": fin}})

    @reg("agrupación doble", 4)
    def _(c):
        es = c.dims(("enum",))
        if len(es) < 2:
            return None
        d1, d2 = c.rng.sample(es, 2); s1, s2 = c.lx["dims"][d1], c.lx["dims"][d2]
        y = c.anio(); tc = c.lx["tiempo"]["campo"]
        return P(c, ["¿{cu} {pl} hubo por {a} y {b} en {y}?", "Número de {pl} por {a} y {b} en {y}."],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], a=s1["np"], b=s2["np"], y=y), \
            c.q(True, [d1, d2, "count"], where={tc: {"eq": y}}, orderBy=[{d1: "ASC"}, {"count": "DESC"}])

    @reg("texto empieza por", 3)
    def _(c):
        tx = [d for d in c.lx["texto"] if c.info["dims"].get(d)]
        if not tx:
            return None
        d = c.pick(tx); v = str(c.rng.choice(c.info["dims"][d][:20])["texto"])
        w = v.split()[0]
        if len(w) < 3:
            return None
        w = titulo(w); spec = c.lx["dims"][d]
        return P(c, ["¿{cu} {pl} hay en {gp} cuyo nombre empieza por «{w}»?", "Número de {pl} de {gp} que empiezan por «{w}»."],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], gp=spec["pl"], w=w), c.q(True, ["count"], where={d: {"startsWith": w}})

    @reg("paginación", 2)
    def _(c):
        d = c.pick(c.dims()); v, t, f = c.valor(d, top=4); k = c.pick([10, 20])
        campos = [x for x in c.lx["mostrar"] if x != d][:3]
        return P(c, ["Muestra la segunda página de {k} {pl} {f}.", "Dame los {pl} {f} del {a} al {b}."],
                 k=k, pl=c.lx["pl"], f=f, a=k + 1, b=2 * k), c.q(False, campos, where={d: {"eq": v}}, limit=k, offset=k)

    @reg("lógica or/not", 3)
    def _(c):
        es = c.dims()
        if len(es) < 2 or not c.info["medias"]:
            return None
        d1 = c.pick(es); v1, t1, f1 = c.valor(d1, top=6)
        md = c.pick(list(c.info["medias"])); n = c.lx["medidas"][md]["np"]
        x = redondo((c.info["medias"][md]["avg"] or 1) * 2)
        return P(c, ["¿{cu} {pl} son {f1} o tienen un valor de «{n}» mayor que {x}?", "Número de {pl} {f1} o en los que «{n}» es mayor que {x}."],
                 cu=C(cuantos(c.g)), pl=c.lx["pl"], f1=f1, x=num(x), n=n), \
            c.q(True, ["count"], where={"_or": [{d1: {"eq": v1}}, {md: {"gt": x}}]})

    @reg("promedio por grupo", 4)
    def _(c):
        md = c.pick(c.medidas("avg")); d = c.pick(c.dims(("enum",)) or c.dims()); spec = c.lx["dims"][d]
        n = c.lx["medidas"][md]["np"]; k = c.pick([None, 5])
        if k:
            return P(c, ["¿Qué {k} {gp} tienen el mayor promedio de {n}?", "Los {k} {gp} con mayor promedio de {n}."],
                     k=k, gp=spec["pl"], n=n), c.q(True, [d, ("avg", [md])], orderBy=[{"avg": {md: "DESC"}}], limit=k)
        return P(c, ["Promedio de {n} por {g}, de mayor a menor.", "¿Cuál es el promedio de {n} en cada {g}?"],
                 n=n, g=spec["np"]), c.q(True, [d, ("avg", [md])], orderBy=[{"avg": {md: "DESC"}}])

    @reg("mínimo y máximo de fecha", 1)
    def _(c):
        if not c.lx["fecha"]:
            return None
        f = c.lx["fecha"]["campo"]
        return P(c, ["¿Cuál es la primera y la última {fn}?", "Fechas mínima y máxima de {fn}."], fn=c.lx["fecha"]["np"]), \
            c.q(True, [("min", [f]), ("max", [f])])

    @reg("año con el máximo", 3)
    def _(c):
        md = c.pick(c.medidas("sum") or c.medidas("avg")); ag = "sum" if md in c.medidas("sum") else "avg"
        tc, tn = c.lx["tiempo"]["campo"], c.lx["tiempo"]["np"]; n = c.lx["medidas"][md]["np"]
        if c.lx.get("sin_evolucion"):
            return None
        return P(c, ["¿En qué {tn} se registró el mayor {p} de {n}?", "{TN} con el mayor {p} de {n}."],
                 tn=tn, TN=C(tn), p="total" if ag == "sum" else "promedio", n=n), \
            c.q(True, [tc, (ag, [md])], orderBy=[{ag: {md: "DESC"}}], limit=1)

    return T


def generar(factor=1.6):
    maps = mappings()
    from traductor import Traductor
    schema = Traductor.desde_directorio(CAPA / "esquemas").schema
    info = json.loads((TRABAJO / "valores.json").read_text(encoding="utf8"))
    T = plantillas()
    rng = random.Random(SEMILLA)
    vistos = set()
    out = []
    # tripletas ya validadas (origen: ejemplo)
    for l in (CAPA / "ejemplos-gcq5-hvdx.jsonl").read_text(encoding="utf8").splitlines():
        if l.strip():
            e = json.loads(l)
            vistos.add(e["graphql"])
            out.append({"dataset": "gcq5-hvdx", "categoria": e["categoria"], "pregunta": e["pregunta"], "graphql": e["graphql"], "origen": "ejemplo"})
    for ds, lx in LEXICO.items():
        order = orden_where(schema, maps[ds]["type"])
        c = Ctx(ds, lx, info[ds], maps[ds], order, rng)
        n_ds = 0
        for nombre, (f, n) in T.items():
            objetivo = max(1, round(n * factor)); intentos = 0; hechos = 0
            while hechos < objetivo and intentos < objetivo * 6:
                intentos += 1
                try:
                    r = f(c)
                except (IndexError, ValueError, KeyError):
                    r = None
                if not r:
                    continue
                preg, gql = r
                if gql in vistos:
                    continue
                vistos.add(gql); hechos += 1
                out.append({"dataset": ds, "categoria": nombre, "pregunta": preg, "graphql": gql, "origen": "plantilla"})
            n_ds += hechos
        print(ds, n_ds, "candidatos")
    with open(TRABAJO / "candidatos.jsonl", "w", encoding="utf8") as fh:
        for e in out:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    print("total", len(out))


# ----------------------------------------------------------------------------- validación

def util(data, root):
    rows = data.get(root) or []
    if not rows:
        return False, "sin filas"
    if root.endswith("Aggregate") and len(rows) == 1:
        r = rows[0]
        if "count" in r and not r["count"]:
            return False, "conteo 0"
        for k, v in r.items():
            if isinstance(v, dict) and all(x is None for x in v.values()):
                return False, f"{k} vacío"
            if k in ("sum", "avg") and isinstance(v, dict) and all(x in (None, 0) for x in v.values()):
                return False, f"{k} vacío"
    return True, ""


def validar():
    import graphql
    svc = servicio()
    cand = [json.loads(l) for l in (TRABAJO / "candidatos.jsonl").read_text(encoding="utf8").splitlines() if l.strip()]
    hechos = {}
    vf = TRABAJO / "validados.jsonl"
    if vf.exists():   # reanudable
        for l in vf.read_text(encoding="utf8").splitlines():
            e = json.loads(l); hechos[e["graphql"]] = e
    motivos = Counter()
    with open(vf, "a", encoding="utf8") as fh:
        for i, e in enumerate(cand, 1):
            h = hechos.get(e["graphql"])
            if h is not None and not (h["estado"] == "rechazado" and h.get("motivo", "").startswith(("min vacío", "max vacío"))):
                continue
            errs = [x.message for x in graphql.validate(svc.schema, graphql.parse(e["graphql"]))]
            if errs:
                e.update(estado="rechazado", motivo="esquema: " + errs[0])
            else:
                r = svc.ejecutar(e["graphql"])
                if r.get("errors"):
                    e.update(estado="rechazado", motivo="ejecución: " + r["errors"][0].get("extensions", {}).get("code", "") + " " + r["errors"][0]["message"][:160])
                else:
                    root = next(iter(r["data"]))
                    ok, m = util(r["data"], root)
                    e.update(soql=r["extensions"]["soql"], filas=r["extensions"]["filas"],
                             respuesta=r["data"][root][:5], estado="valido" if ok else "rechazado", motivo=m)
            motivos[e["estado"] + (": " + e["motivo"].split(":")[0] if e["estado"] != "valido" else "")] += 1
            fh.write(json.dumps(e, ensure_ascii=False) + "\n"); fh.flush()
            if i % 50 == 0:
                print(i, "/", len(cand), dict(motivos), flush=True)
    print("fin", dict(motivos))


def revalidar():
    """Vuelve a validar los pares válidos cuya SoQL cambia con la versión actual de la capa.

    Se usa tras corregir el traductor sin cambiar el esquema (p. ej., la agrupación y el conteo distinto por
    enums fusionados, 06/11/2026): la consulta GraphQL y la pregunta no cambian, pero sí la SoQL y la respuesta.
    Añade las nuevas validaciones a validados.jsonl (la última de cada consulta prevalece); después hay que
    ejecutar `particionar`, que conserva las particiones mientras no cambie el conjunto de pares válidos."""
    svc = servicio()
    vf = TRABAJO / "validados.jsonl"
    ultimo = {}
    for l in vf.read_text(encoding="utf8").splitlines():
        if l.strip():
            e = json.loads(l); ultimo[e["graphql"]] = e
    resumen = Counter()
    with open(vf, "a", encoding="utf8") as fh:
        for g, e in ultimo.items():
            if e["estado"] != "valido":
                continue
            if svc.tr.traducir(g).soql == e.get("soql"):
                continue
            e = dict(e)
            r = svc.ejecutar(g)
            if r.get("errors"):
                e.update(estado="rechazado", motivo="ejecución: " + r["errors"][0].get("extensions", {}).get("code", "") + " " + r["errors"][0]["message"][:160])
            else:
                root = next(iter(r["data"]))
                ok, m = util(r["data"], root)
                e.update(soql=r["extensions"]["soql"], filas=r["extensions"]["filas"],
                         respuesta=r["data"][root][:5], estado="valido" if ok else "rechazado", motivo=m)
            resumen[e["estado"] + (": " + e["motivo"] if e["estado"] != "valido" else "")] += 1
            fh.write(json.dumps(e, ensure_ascii=False) + "\n"); fh.flush()
    print("revalidados", sum(resumen.values()), dict(resumen))


# ----------------------------------------------------------------------------- partición

RESERVADO = "ni93-8mm5"


def particionar():
    ultimo = {}
    for l in (TRABAJO / "validados.jsonl").read_text(encoding="utf8").splitlines():
        if l.strip():
            e = json.loads(l); ultimo[e["graphql"]] = e      # la última validación de cada consulta prevalece
    cand = [json.loads(l) for l in (TRABAJO / "candidatos.jsonl").read_text(encoding="utf8").splitlines() if l.strip()]
    vals = []
    for e in cand:
        v = ultimo.get(e["graphql"])
        if v and v["estado"] == "valido":
            v = dict(v); v.update(pregunta=e["pregunta"], categoria=e["categoria"], origen=e["origen"]); vals.append(v)
    rng = random.Random(SEMILLA)
    sal = defaultdict(list)
    por_ds = defaultdict(list)
    for e in vals:
        por_ds[e["dataset"]].append(e)
    for ds, es in sorted(por_ds.items()):
        if ds == RESERVADO:
            for e in es:
                e["particion"] = "reservado"
            sal["reservado"] += es
            continue
        # estratificado por categoría: cada consulta GraphQL es única, así que no hay paráfrasis compartidas entre particiones
        porcat = defaultdict(list)
        for e in es:
            porcat[e["categoria"]].append(e)
        for cat, xs in sorted(porcat.items()):
            rng.shuffle(xs)
            n = len(xs); nt = round(n * 0.15); nv = round(n * 0.15)
            if n >= 3:
                nt, nv = max(nt, 1), max(nv, 1) if n >= 5 else nv
            for k, e in enumerate(xs):
                e["particion"] = "test" if k < nt else ("val" if k < nt + nv else "train")
                sal[e["particion"]].append(e)
    n = 0
    for part in ("train", "val", "test", "reservado"):
        es = sal[part]
        with open(HERE / f"{part}.jsonl", "w", encoding="utf8") as fh:
            for k, e in enumerate(es, 1):
                n += 1
                fh.write(json.dumps({
                    "id": f"{part}-{k:04d}",
                    "dataset": e["dataset"], "categoria": e["categoria"], "pregunta": e["pregunta"],
                    "graphql": e["graphql"], "soql": e["soql"], "filas": e["filas"], "origen": e["origen"],
                    "revision": "pendiente"}, ensure_ascii=False) + "\n")
        print(part, len(es))
    print("total", n)


if __name__ == "__main__":
    {"explorar": explorar, "generar": generar, "validar": validar, "revalidar": revalidar,
     "particionar": particionar}[sys.argv[1]]()
