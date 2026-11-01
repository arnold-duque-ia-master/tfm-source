"""Generador de esquema GraphQL a partir de metadatos SODA (paso 4).

Entradas, sin red:
  datasets.yaml           registro de conjuntos (alias, exclusiones, roles, casts...)
  metadata/<id>.json      metadatos de /api/views/<id>.json
  perfiles/<id>.json      perfil de columnas (perfilar_columnas.py)

Salidas en esquemas/:
  comunes.graphql         tipos compartidos (escalares, filtros, OrderDirection)
  <id>.graphql            tipos y campos raíz del conjunto, con descripciones
  <id>.prompt.graphql     versión compacta para la instrucción del modelo
  <id>.mapping.json       correspondencias que necesita el traductor GraphQL -> SoQL
  schema.graphql          esquema completo (comunes + todos los conjuntos)

Uso: python3 generador.py [id ...]     (sin argumentos: todos los del registro)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import graphql
import yaml

HERE = Path(__file__).resolve().parent
ENUM_MAX = 40
STOPWORDS = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "con", "por", "para"}
INT32 = 2**31 - 1
RESERVED = {"_and", "_or", "_not", "count", "countDistinct", "sum", "avg", "min", "max", "where", "orderBy", "limit", "offset"}

COMUNES = '''"""Fecha ISO 8601 sin hora (AAAA-MM-DD)."""
scalar Date

"""Fecha y hora ISO 8601 sin zona horaria (AAAA-MM-DDTHH:MM:SS)."""
scalar DateTime

enum OrderDirection {
  ASC
  DESC
}

type Point {
  latitude: Float
  longitude: Float
}

input StringFilter {
  eq: String
  neq: String
  in: [String!]
  nin: [String!]
  contains: String
  startsWith: String
  isNull: Boolean
}

input IntFilter {
  eq: Int
  neq: Int
  gt: Int
  gte: Int
  lt: Int
  lte: Int
  in: [Int!]
  nin: [Int!]
  isNull: Boolean
}

input FloatFilter {
  eq: Float
  neq: Float
  gt: Float
  gte: Float
  lt: Float
  lte: Float
  in: [Float!]
  nin: [Float!]
  isNull: Boolean
}

input DateFilter {
  eq: Date
  neq: Date
  gt: Date
  gte: Date
  lt: Date
  lte: Date
  isNull: Boolean
}

input DateTimeFilter {
  eq: DateTime
  neq: DateTime
  gt: DateTime
  gte: DateTime
  lt: DateTime
  lte: DateTime
  isNull: Boolean
}

input BooleanFilter {
  eq: Boolean
  isNull: Boolean
}
'''
SHARED_NAMES = {"Date", "DateTime", "OrderDirection", "Point", "StringFilter", "IntFilter", "FloatFilter",
                "DateFilter", "DateTimeFilter", "BooleanFilter"}


# ---------------------------------------------------------------- nombres

def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def camel(label: str) -> str:
    s = strip_accents(label.replace("ñ", "ni").replace("Ñ", "NI"))   # "Año" -> "anio", no "ano"
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)        # CategoriaTarifa -> Categoria Tarifa
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)      # HTMLParser -> HTML Parser
    words = re.findall(r"[A-Za-z0-9]+", s)
    if not words:
        return "campo"
    out = words[0].lower() + "".join(w[:1].upper() + w[1:].lower() for w in words[1:])
    return "c" + out if out[0].isdigit() else out


def pascal(name: str) -> str:
    return name[:1].upper() + name[1:]


def enum_value_name(v: str) -> str:
    s = re.sub(r"[^A-Z0-9]+", "_", strip_accents(v).upper()).strip("_") or "VACIO"
    return "_" + s if s[0].isdigit() else s


def _norm_words(v: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", strip_accents(v).lower())


def value_keys(v: str) -> list[str]:
    """Claves deterministas: dos valores con alguna clave igual se consideran el mismo valor.

    1. Sin tildes, mayúsculas ni puntuación ............ "BOLÍVAR" = "Bolivar"
    2. Mismas palabras en otro orden, sin artículos ..... "Alto riesgo" = "Riesgo alto"
    3. Solo letras y dígitos, sin separadores ........... "N/A" = "NA"
    """
    w = _norm_words(v)
    return ["n:" + " ".join(w),
            "b:" + " ".join(sorted(x for x in w if x not in STOPWORDS)),
            "c:" + "".join(w)]


def group_values(values: list[str], aliases: list[list[str]] | None = None) -> list[list[str]]:
    """Agrupa variantes de un mismo valor (unión-búsqueda sobre value_keys y valueAliases del registro)."""
    parent = {v: v for v in values}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    seen = {}
    for v in values:
        for k in value_keys(v):
            if k in seen:
                union(v, seen[k])
            else:
                seen[k] = v
    for grp in aliases or []:
        present = [v for v in grp if v in parent]
        for v in present[1:]:
            union(present[0], v)
    groups: dict[str, list[str]] = {}
    for v in values:
        groups.setdefault(find(v), []).append(v)
    return list(groups.values())


def similar_pairs(groups: list[list[str]], threshold: float = 0.88) -> list[tuple[str, str, float]]:
    """Pares de grupos parecidos que NO se fusionan automáticamente (para revisión humana).

    Se señalan si (a) la similitud de caracteres es >= threshold, o (b) todas las palabras con
    contenido del más corto (al menos 2) aparecen en el más largo. Se ignoran los valores que son
    códigos (contienen dígitos) porque suelen diferir en un solo carácter a propósito (2019A/2019B, PM10/PM2.5).
    """
    import difflib
    reps = [" ".join(_norm_words(g[0])) for g in groups]
    content = [set(r.split()) - STOPWORDS for r in reps]
    out = []
    for i in range(len(reps)):
        for j in range(i + 1, len(reps)):
            a, b = reps[i], reps[j]
            if re.search(r"\d", a + b):
                continue
            r = difflib.SequenceMatcher(None, a, b).ratio()
            short, long_ = sorted((content[i], content[j]), key=len)
            sub = len(short) >= 2 and short <= long_
            if r >= threshold or sub:
                out.append((groups[i][0], groups[j][0], round(r, 2)))
    return out


def short_desc(text: str | None, limit: int = 110) -> str | None:
    if not text:
        return None
    t = re.sub(r"\s+", " ", text).strip()
    t = re.split(r"(?<=[.;])\s", t)[0]
    if len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0] + "…"
    return t.replace('"', "'").replace("\\", "/")


# ---------------------------------------------------------------- modelo

@dataclass
class Col:
    field: str                 # fieldName en SODA
    name: str                  # nombre GraphQL
    soda_type: str
    gql: str                   # Int | Float | String | Date | DateTime | Boolean | Point | <Enum>
    kind: str                  # int | float | string | date | datetime | boolean | point | enum
    role: str | None = None    # id | time | geo | None (medida si es numérica)
    desc: str | None = None
    cast: dict | None = None
    enum_values: dict = field(default_factory=dict)   # nombre GraphQL -> [valores originales]
    similar: list = field(default_factory=list)       # pares parecidos no fusionados (revisión)

    @property
    def numeric(self):
        return self.kind in ("int", "float")

    @property
    def measure(self):
        return self.numeric and self.role is None

    @property
    def temporal(self):
        return self.kind in ("date", "datetime")


def build_columns(entry: dict, meta: dict, prof: dict, enum_max: int = ENUM_MAX) -> list[Col]:
    roles = {f: r for r, fs in (entry.get("roles") or {}).items() for f in fs}
    exclude = set(entry.get("exclude") or [])
    rename = entry.get("rename") or {}
    casts = entry.get("casts") or {}
    cols, used = [], set()
    for c in meta["columns"]:
        f, t = c["fieldName"], c["dataTypeName"]
        if f.startswith(":") or f in exclude:
            continue
        p = prof["columnas"].get(f, {})
        role = roles.get(f)
        if f in casts:
            kind = casts[f]["type"].lower()
        elif t == "text":
            vals = p.get("valores")
            complete = vals is not None and len(vals) >= p.get("distintos", 0)   # el perfil guarda hasta 60 valores
            groups = group_values(vals, (entry.get("valueAliases") or {}).get(f)) if complete else []
            kind = "enum" if (role is None and complete and vals and len(groups) <= enum_max) else "string"
        elif t in ("number", "money", "percent"):
            big = any(abs(float(p[k])) > INT32 for k in ("min", "max") if p.get(k) not in (None, ""))
            kind = "int" if p.get("entero") and not big else "float"
        elif t in ("calendar_date", "floating_timestamp", "fixed_timestamp"):
            kind = "datetime" if p.get("con_hora") else "date"
        elif t == "checkbox":
            kind = "boolean"
        elif t == "point":
            kind = "point"
        elif t == "url":
            kind = "string"
        else:
            print(f"  AVISO {entry['id']}: columna {f} de tipo {t} omitida", file=sys.stderr)
            continue
        name = rename.get(f) or camel(c.get("name") or f)
        if name in RESERVED:
            name += "Col"
        base, i = name, 2
        while name in used:
            name, i = f"{base}{i}", i + 1
        used.add(name)
        col = Col(field=f, name=name, soda_type=t, kind=kind, gql="", role=role,
                  desc=short_desc(c.get("description")), cast=casts.get(f))
        if kind == "enum":
            named = {}
            canon = [a[0] for a in (entry.get("valueAliases") or {}).get(f, [])]
            for grp in groups:
                pref = [v for v in canon if v in grp]
                name = enum_value_name(pref[0]) if pref else sorted(enum_value_name(v) for v in grp)[0]
                named[name] = sorted(grp)
            col.enum_values = dict(sorted(named.items()))
            col.similar = similar_pairs([named[k] for k in col.enum_values])
        col.gql = {"int": "Int", "float": "Float", "string": "String", "date": "Date", "datetime": "DateTime",
                   "boolean": "Boolean", "point": "Point"}.get(kind) or ""
        cols.append(col)
    tp = pascal(entry["alias"])
    for col in cols:
        if col.kind == "enum":
            col.gql = tp + pascal(col.name)
    return cols


# ---------------------------------------------------------------- SDL

def _d(text, indent=""):
    return f'{indent}"{text}"\n' if text else ""


def filter_type(col: Col) -> str:
    return {"int": "IntFilter", "float": "FloatFilter", "string": "StringFilter", "date": "DateFilter",
            "datetime": "DateTimeFilter", "boolean": "BooleanFilter"}.get(col.kind, col.gql + "Filter")


def generate(entry: dict, cols: list[Col]) -> str:
    A = entry["alias"]
    T = pascal(A)
    out = [f"# ---------- {entry['id']} ----------\n"]

    for c in cols:
        if c.kind != "enum":
            continue
        out.append(f"enum {c.gql} {{\n" + "".join(f"  {v}\n" for v in c.enum_values) + "}\n")
        out.append(f"input {c.gql}Filter {{\n  eq: {c.gql}\n  neq: {c.gql}\n  in: [{c.gql}!]\n  nin: [{c.gql}!]\n  isNull: Boolean\n}}\n")

    out.append(f'"""{entry["description"]} ({entry["id"]})"""\ntype {T} {{\n' +
               "".join(_d(c.desc, "  ") + f"  {c.name}: {c.gql}\n" for c in cols) + "}\n")

    filt = [c for c in cols if c.kind != "point"]
    derived = [(c, suf) for c in cols if c.temporal for suf in ("Year", "Month")]
    w = [f"  _and: [{T}Where!]\n", f"  _or: [{T}Where!]\n", f"  _not: {T}Where\n"]
    for c in filt:
        w.append(f"  {c.name}: {filter_type(c)}\n")
        if c.temporal:
            w += [f"  {c.name}Year: IntFilter\n", f"  {c.name}Month: IntFilter\n"]
    out.append(f"input {T}Where {{\n" + "".join(w) + "}\n")
    out.append(f"input {T}OrderBy {{\n" + "".join(f"  {c.name}: OrderDirection\n" for c in filt) + "}\n")

    measures = [c for c in cols if c.measure]
    minmax = [c for c in cols if (c.numeric and c.role != "id") or c.temporal]
    cdist = [c for c in cols if c.kind in ("string", "enum", "date", "datetime", "boolean") or (c.numeric and c.role in ("id", "time"))]
    keys = [c for c in cols if not c.measure and c.role != "geo" and c.kind != "point"]

    if measures:
        out.append(f"type {T}Sum {{\n" + "".join(f"  {c.name}: Float\n" for c in measures) + "}\n")
        out.append(f"input {T}SumOrderBy {{\n" + "".join(f"  {c.name}: OrderDirection\n" for c in measures) + "}\n")
    if minmax:
        out.append(f"type {T}MinMax {{\n" + "".join(f"  {c.name}: {c.gql}\n" for c in minmax) + "}\n")
        out.append(f"input {T}MinMaxOrderBy {{\n" + "".join(f"  {c.name}: OrderDirection\n" for c in minmax) + "}\n")
    if cdist:
        out.append(f"type {T}CountDistinct {{\n" + "".join(f"  {c.name}: Int\n" for c in cdist) + "}\n")
        out.append(f"input {T}CountDistinctOrderBy {{\n" + "".join(f"  {c.name}: OrderDirection\n" for c in cdist) + "}\n")

    g = []
    for c in keys:
        g.append(f"  {c.name}: {c.gql}\n")
        if c.temporal:
            g += [f'  "Año de {c.name}."\n  {c.name}Year: Int\n', f'  "Mes (1-12) de {c.name}."\n  {c.name}Month: Int\n']
    g.append('  "Número de filas del grupo."\n  count: Int!\n')
    if cdist:
        g.append(f"  countDistinct: {T}CountDistinct\n")
    if measures:
        g += [f"  sum: {T}Sum\n", f"  avg: {T}Sum\n"]
    if minmax:
        g += [f"  min: {T}MinMax\n", f"  max: {T}MinMax\n"]
    out.append(f'"""Fila de un resultado agregado de {A}. Los campos escalares seleccionados son las claves de agrupación."""\n'
               f"type {T}Group {{\n" + "".join(g) + "}\n")

    go = []
    for c in keys:
        go.append(f"  {c.name}: OrderDirection\n")
        if c.temporal:
            go += [f"  {c.name}Year: OrderDirection\n", f"  {c.name}Month: OrderDirection\n"]
    go.append("  count: OrderDirection\n")
    if cdist:
        go.append(f"  countDistinct: {T}CountDistinctOrderBy\n")
    if measures:
        go += [f"  sum: {T}SumOrderBy\n", f"  avg: {T}SumOrderBy\n"]
    if minmax:
        go += [f"  min: {T}MinMaxOrderBy\n", f"  max: {T}MinMaxOrderBy\n"]
    out.append(f"input {T}GroupOrderBy {{\n" + "".join(go) + "}\n")

    out.append("extend type Query {\n"
               f'  "Filas de {entry["id"]}. Sin orderBy se ordenan por el identificador interno de fila."\n'
               f"  {A}(where: {T}Where, orderBy: [{T}OrderBy!], limit: Int = 100, offset: Int = 0): [{T}!]!\n"
               f'  "Agregados de {entry["id"]} agrupados por los campos escalares seleccionados."\n'
               f"  {A}Aggregate(where: {T}Where, orderBy: [{T}GroupOrderBy!], limit: Int = 100, offset: Int = 0): [{T}Group!]!\n"
               "}\n")
    return "\n".join(out)


def mapping(entry: dict, cols: list[Col]) -> dict:
    return {
        "id": entry["id"], "alias": entry["alias"], "type": pascal(entry["alias"]),
        "baseWhere": entry.get("baseWhere"),
        "columns": {c.name: {"field": c.field, "kind": c.kind, "gql": c.gql, "role": c.role, "cast": c.cast,
                             "enum": c.enum_values or None} for c in cols},
    }


def compact(sdl: str) -> str:
    """SDL para la instrucción del modelo: sin descripciones, comentarios ni tipos compartidos, en una línea por tipo."""
    doc = graphql.parse(sdl)
    defs = []
    for d in doc.definitions:
        name = getattr(getattr(d, "name", None), "value", None)
        if name in SHARED_NAMES:
            continue
        defs.append(d)
    txt = graphql.print_ast(graphql.language.DocumentNode(definitions=tuple(defs)))
    txt = re.sub(r'"""[\s\S]*?"""\s*', "", txt)
    txt = re.sub(r'^\s*"[^"\n]*"\s*$\n', "", txt, flags=re.M)
    blocks = [re.sub(r"\s+", " ", b).strip() for b in txt.split("\n\n") if b.strip()]
    return "\n".join(blocks) + "\n"


# ---------------------------------------------------------------- CLI

def load(ds_id: str):
    reg = {e["id"]: e for e in yaml.safe_load((HERE / "datasets.yaml").read_text(encoding="utf8"))}
    entry = reg[ds_id]
    meta = json.loads((HERE / "metadata" / f"{ds_id}.json").read_text(encoding="utf8"))
    prof = json.loads((HERE / "perfiles" / f"{ds_id}.json").read_text(encoding="utf8"))
    return entry, meta, prof


def main(ids: list[str]) -> None:
    reg = yaml.safe_load((HERE / "datasets.yaml").read_text(encoding="utf8"))
    ids = ids or [e["id"] for e in reg]
    od = HERE / "esquemas"
    od.mkdir(exist_ok=True)
    (od / "comunes.graphql").write_text(COMUNES, encoding="utf8")
    parts = [COMUNES, "type Query\n"]
    for ds in ids:
        entry, meta, prof = load(ds)
        cols = build_columns(entry, meta, prof)
        sdl = generate(entry, cols)
        graphql.build_schema(COMUNES + "type Query\n" + sdl)          # valida el conjunto por separado
        (od / f"{ds}.graphql").write_text(sdl, encoding="utf8")
        pr = compact(sdl)
        (od / f"{ds}.prompt.graphql").write_text(pr, encoding="utf8")
        (od / f"{ds}.mapping.json").write_text(json.dumps(mapping(entry, cols), ensure_ascii=False, indent=1), encoding="utf8")
        parts.append(sdl)
        n_enum = sum(1 for c in cols if c.kind == "enum")
        merged = sum(1 for c in cols for v in c.enum_values.values() if len(v) > 1)
        print(f"{ds:10} {entry['alias']:32} cols={len(cols):2} enums={n_enum:2} fusionados={merged:2} "
              f"SDL={len(sdl):6} prompt={len(pr):6} car.")
    rev = ["# Revisión de valores de enum (generado por generador.py)", "",
           "Valores fusionados automáticamente y pares parecidos que **no** se fusionaron.",
           "Para fusionar un par, añadirlo en `valueAliases` de `datasets.yaml`: `campo: [[valor1, valor2]]`.", ""]
    for ds in ids:
        entry, meta, prof = load(ds)
        for c in build_columns(entry, meta, prof):
            if c.kind != "enum":
                continue
            merged = {k: v for k, v in c.enum_values.items() if len(v) > 1}
            if not merged and not c.similar:
                continue
            rev.append(f"## {ds} · `{c.name}` ({c.field}), {len(c.enum_values)} valores")
            rev.append("")
            for k, v in merged.items():
                rev.append(f"- Fusionado `{k}` ← " + " · ".join(f"\"{x}\"" for x in v))
            for a, b, r in c.similar:
                rev.append(f"- **Revisar:** \"{a}\" ~ \"{b}\" (similitud {r})")
            rev.append("")
    (od / "revision-enums.md").write_text("\n".join(rev) + "\n", encoding="utf8")
    full = "\n".join(parts)
    graphql.build_schema(full)
    (od / "schema.graphql").write_text(full, encoding="utf8")
    print(f"schema.graphql válido ({len(full)} car.)")


if __name__ == "__main__":
    main(sys.argv[1:])
