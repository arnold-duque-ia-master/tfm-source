"""Traductor GraphQL -> SoQL (paso 5) y conversión de la respuesta de SODA.

    from traductor import Traductor
    t = Traductor.desde_directorio("esquemas")
    tr = t.traducir('{ vacunacionAftosaVichadaAggregate { municipio count } }')
    tr.dataset, tr.soql, tr.page_size          # 'gcq5-hvdx', 'SELECT municipio, count(*) AS count GROUP BY municipio LIMIT 100', 100
    data = t.convertir(tr, filas_de_soda)      # lista de objetos con la forma de la consulta GraphQL

Reglas en CONVENCIONES.md (apartados 5, 6, 7 y 8). Sin red: la ejecución contra SODA está en el servidor.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import graphql
from graphql.execution.values import get_argument_values
from graphql.language import FieldNode, FragmentDefinitionNode, FragmentSpreadNode, InlineFragmentNode, OperationDefinitionNode

MAX_LIMIT = 1000
MAX_IN = 100
AGG_FUNCS = ("sum", "avg", "min", "max")
LOGICAL = ("_and", "_or", "_not")
OPS = {"eq": "=", "neq": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$")


class TranslationError(Exception):
    def __init__(self, code: str, message: str, details=None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details

    def to_graphql_error(self) -> dict:
        ext = {"code": self.code}
        if self.details:
            ext["details"] = self.details
        return {"message": self.message, "extensions": ext}


def rule(msg: str):
    raise TranslationError("QUERY_RULE_VIOLATION", msg)


@dataclass
class OutField:
    """Cómo convertir una clave de la fila de SODA en un campo de la respuesta GraphQL."""
    path: tuple            # ("municipio",) o ("sum", "totalAftosa")
    soda_key: str          # clave en la fila devuelta por SODA
    kind: str              # int | float | string | date | datetime | boolean | point | enum | count
    column: str | None = None


@dataclass
class Translation:
    dataset: str
    root: str
    mode: str              # rows | aggregate
    soql: str
    page_size: int
    out: list = field(default_factory=list)


# ---------------------------------------------------------------- literales SoQL

def q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def lit(v, kind: str) -> str:
    if kind in ("int", "float"):
        if isinstance(v, bool):
            rule("Se esperaba un número")
        return str(int(v)) if kind == "int" else repr(float(v))
    if kind == "boolean":
        return "true" if v else "false"
    if kind == "date":
        if not isinstance(v, str) or not DATE_RE.match(v):
            rule(f"Fecha no válida: {v!r}. Formato esperado AAAA-MM-DD")
        return q(v)
    if kind == "datetime":
        if not isinstance(v, str) or not DATETIME_RE.match(v):
            rule(f"Fecha y hora no válida: {v!r}. Formato esperado AAAA-MM-DDTHH:MM:SS")
        return q(v)
    return q(v)


# ---------------------------------------------------------------- traductor

class Traductor:
    def __init__(self, schema: graphql.GraphQLSchema, mappings: dict[str, dict]):
        self.schema = schema
        self.by_root = {}
        for m in mappings.values():
            self.by_root[m["alias"]] = (m, "rows")
            self.by_root[m["alias"] + "Aggregate"] = (m, "aggregate")

    @classmethod
    def desde_directorio(cls, d: str | Path = Path(__file__).resolve().parent / "esquemas"):
        d = Path(d)
        schema = graphql.build_schema((d / "schema.graphql").read_text(encoding="utf8"))
        maps = {}
        for f in sorted(d.glob("*.mapping.json")):
            m = json.loads(f.read_text(encoding="utf8"))
            maps[m["id"]] = m
        return cls(schema, maps)

    # -------------------------------------------------- entrada

    def traducir(self, query: str) -> Translation:
        try:
            doc = graphql.parse(query)
        except graphql.GraphQLError as e:
            raise TranslationError("GRAPHQL_VALIDATION_FAILED", e.message)
        errs = graphql.validate(self.schema, doc)
        if errs:
            raise TranslationError("GRAPHQL_VALIDATION_FAILED", errs[0].message, [e.message for e in errs])

        ops = [d for d in doc.definitions if isinstance(d, OperationDefinitionNode)]
        if any(isinstance(d, FragmentDefinitionNode) for d in doc.definitions):
            rule("No se admiten fragmentos")
        if len(ops) != 1 or ops[0].operation.value != "query":
            rule("Se admite una sola operación de tipo query")
        op = ops[0]
        if op.variable_definitions:
            rule("No se admiten variables: los valores deben ir escritos en la consulta")
        self._no_extras(op.selection_set)
        roots = op.selection_set.selections
        if len(roots) != 1:
            rule("La consulta debe tener un solo campo raíz")
        node: FieldNode = roots[0]
        if node.name.value not in self.by_root:
            rule(f"Campo raíz desconocido: {node.name.value}")
        m, mode = self.by_root[node.name.value]
        fdef = self.schema.query_type.fields[node.name.value]
        args = get_argument_values(fdef, node)

        limit, offset = args.get("limit", 100), args.get("offset", 0)
        if limit is None or not 1 <= limit <= MAX_LIMIT:
            rule(f"limit debe estar entre 1 y {MAX_LIMIT}")
        if offset is None or offset < 0:
            rule("offset no puede ser negativo")

        self.m, self.cols = m, m["columns"]
        out: list[OutField] = []
        select, group = [], []
        if mode == "rows":
            for f in node.selection_set.selections:
                name = f.name.value
                c = self.cols[name]
                if c["field"] not in select:
                    select.append(c["field"])
                    out.append(OutField((name,), c["field"], c["kind"], name))
        else:
            for f in node.selection_set.selections:
                name = f.name.value
                if name == "count":
                    self._add(select, out, "count(*) AS count", OutField(("count",), "count", "count"))
                elif name == "countDistinct" or name in AGG_FUNCS:
                    for sub in f.selection_set.selections:
                        col = sub.name.value
                        c = self.cols[col]
                        if name == "countDistinct":
                            key = f"count_distinct_{c['field']}"
                            expr = self._distinct(col)
                            kind = "count"
                        else:
                            key = f"{name}_{c['field']}"
                            expr = f"{name}({self._expr(col)})"
                            kind = "float" if name in ("sum", "avg") else c["kind"]
                        self._add(select, out, f"{expr} AS {key}", OutField((name, col), key, kind, col))
                else:
                    expr, key, kind, col = self._key(name)
                    if key not in group:
                        group.append(key)
                        sel = expr if expr == key else f"{expr} AS {key}"
                        self._add(select, out, sel, OutField((name,), key, kind, col))
        where = self._where_root(args.get("where"))
        order = self._order(args.get("orderBy"), mode, {o.path[0] for o in out if len(o.path) == 1})

        parts = ["SELECT " + ", ".join(select)]
        if where:
            parts.append("WHERE " + where)
        if group:
            parts.append("GROUP BY " + ", ".join(group))
        if order:
            parts.append("ORDER BY " + ", ".join(order))
        parts.append(f"LIMIT {limit}")
        if offset:
            parts.append(f"OFFSET {offset}")
        return Translation(m["id"], node.name.value, mode, " ".join(parts), limit, out)

    def _no_extras(self, sel_set):
        for s in sel_set.selections:
            if isinstance(s, (FragmentSpreadNode, InlineFragmentNode)):
                rule("No se admiten fragmentos")
            if s.alias:
                rule("No se admiten alias")
            if s.directives:
                rule("No se admiten directivas")
            if s.selection_set:
                self._no_extras(s.selection_set)

    @staticmethod
    def _add(select, out, sel, of):
        if sel not in select:
            select.append(sel)
            out.append(of)

    # -------------------------------------------------- columnas y expresiones

    def _col(self, name):
        if name.endswith(("Year", "Month")):
            base = name[:-4] if name.endswith("Year") else name[:-5]
            if base in self.cols and self.cols[base]["kind"] in ("date", "datetime"):
                return base, "year" if name.endswith("Year") else "month"
        return name, None

    def _expr(self, name) -> str:
        base, part = self._col(name)
        c = self.cols[base]
        f = c["field"]
        if part:
            return f"date_extract_{'y' if part == 'year' else 'm'}({f})"
        if c.get("cast"):
            nulls = c["cast"].get("nullTokens")
            if nulls:
                return f"case({f} IN ({', '.join(q(x) for x in nulls)}), NULL, true, {f}::number)"
            return f"{f}::number"
        return f

    def _kind(self, name):
        base, part = self._col(name)
        return "int" if part else self.cols[base]["kind"]

    def _enum_fusion(self, base) -> str | None:
        """Expresión que reduce cada grupo de variantes fusionadas de un enum a la primera (la canónica).

        Sin ella, GROUP BY y count(distinct) trabajan sobre los valores originales y devuelven una fila
        (o cuentan un valor) por variante: SABADO aparecería tres veces. None si el enum no fusiona nada."""
        c = self.cols[base]
        if c.get("kind") != "enum" or not c.get("enum"):
            return None
        grupos = [raws for raws in c["enum"].values() if len(raws) > 1]
        if not grupos:
            return None
        f = c["field"]
        ramas = ", ".join(f"{f} IN ({', '.join(q(x) for x in raws)}), {q(raws[0])}" for raws in grupos)
        return f"case({ramas}, true, {f})"

    def _distinct(self, col) -> str:
        return f"count(distinct {self._enum_fusion(col) or self.cols[col]['field']})"

    def _key(self, name):
        """Clave de agrupación: (expresión, alias SoQL, tipo, columna)."""
        base, part = self._col(name)
        c = self.cols[base]
        if part:
            return self._expr(name), f"{c['field']}_{part}", "int", base
        fusion = self._enum_fusion(base)
        if fusion:
            return fusion, c["field"] + "_canon", c["kind"], base
        if c.get("cast"):
            return self._expr(name), c["field"] + "_num", c["kind"], base
        return c["field"], c["field"], c["kind"], base

    # -------------------------------------------------- where

    def _where_root(self, w) -> str:
        conds = []
        base = self.m.get("baseWhere")
        if base:
            conds.append(f"({base})" if " OR " in base.upper() else base)
        if w:
            conds += self._where(w)
        return " AND ".join(conds)

    def _where(self, w: dict) -> list[str]:
        conds = []
        for name, flt in w.items():           # columnas primero (orden del esquema), lógicos al final
            if name in LOGICAL or flt is None:
                continue
            conds += self._filter(name, flt)
        if w.get("_and"):
            for sub in w["_and"]:
                conds.append(self._group(self._where(sub)))
        if w.get("_or"):
            subs = [self._group(self._where(sub)) for sub in w["_or"]]
            subs = [s for s in subs if s]
            if subs:
                conds.append("(" + " OR ".join(subs) + ")" if len(subs) > 1 else subs[0])
        if w.get("_not"):
            inner = " AND ".join(self._where(w["_not"]))
            if inner:
                conds.append(f"NOT ({inner})")
        return [c for c in conds if c]

    @staticmethod
    def _group(conds):
        if not conds:
            return ""
        return conds[0] if len(conds) == 1 else "(" + " AND ".join(conds) + ")"

    def _filter(self, name, flt: dict) -> list[str]:
        expr, kind = self._expr(name), self._kind(name)
        base, _ = self._col(name)
        enum = self.cols[base].get("enum") if kind == "enum" else None
        out = []
        for op, v in flt.items():
            if v is None:
                continue
            if op == "isNull":
                out.append(f"{expr} IS {'NULL' if v else 'NOT NULL'}")
            elif op in ("in", "nin"):
                if not v:
                    rule(f"La lista de {op} no puede estar vacía")
                if len(v) > MAX_IN:
                    rule(f"La lista de {op} admite como máximo {MAX_IN} valores")
                vals = [x for e in v for x in enum[e]] if enum else [lit(x, kind) for x in v]
                if enum:
                    vals = [q(x) for x in vals]
                out.append(f"{expr} {'IN' if op == 'in' else 'NOT IN'} ({', '.join(vals)})")
            elif op in ("eq", "neq") and enum:
                raw = enum[v]
                if len(raw) == 1:
                    out.append(f"{expr} {OPS[op]} {q(raw[0])}")
                else:
                    out.append(f"{expr} {'IN' if op == 'eq' else 'NOT IN'} ({', '.join(q(x) for x in raw)})")
            elif op in OPS:
                out.append(f"{expr} {OPS[op]} {lit(v, kind)}")
            elif op == "contains":
                out.append(f"upper({expr}) LIKE upper({q('%' + v + '%')})")
            elif op == "startsWith":
                out.append(f"starts_with(upper({expr}), upper({q(v)}))")
            else:
                rule(f"Operador no admitido: {op}")
        return out

    # -------------------------------------------------- orden

    def _order(self, ob, mode, selected_keys) -> list[str]:
        items = []
        for o in ob or []:
            flat = [(k, v) for k, v in o.items() if v is not None]
            if len(flat) != 1:
                rule("Cada elemento de orderBy debe tener exactamente una clave")
            k, v = flat[0]
            if isinstance(v, dict):
                inner = [(a, b) for a, b in v.items() if b is not None]
                if len(inner) != 1:
                    rule(f"orderBy.{k} debe tener exactamente una clave")
                col, d = inner[0]
                if k == "countDistinct":
                    items.append(f"{self._distinct(col)} {d}")
                else:
                    items.append(f"{k}({self._expr(col)}) {d}")
            elif k == "count":
                items.append(f"count(*) {v}")
            elif mode == "rows":
                items.append(f"{self._expr(k)} {v}")
            else:
                if k not in selected_keys:
                    rule(f"Solo se puede ordenar por {k} si se selecciona como clave de agrupación")
                items.append(f"{self._key(k)[1]} {v}")
        if mode == "rows":
            items.append(":id")
        return items

    # -------------------------------------------------- respuesta

    def convertir(self, tr: Translation, rows: list[dict]) -> list[dict]:
        cols = self.by_root[tr.root][0]["columns"]
        rev = {}
        for name, c in cols.items():
            if c.get("enum"):
                rev[name] = {raw: e for e, raws in c["enum"].items() for raw in raws}
        res = []
        for r in rows:
            obj = {}
            for of in tr.out:
                v = conv(r.get(of.soda_key), of.kind, cols.get(of.column) if of.column else None,
                         rev.get(of.column))
                tgt = obj
                for p in of.path[:-1]:
                    tgt = tgt.setdefault(p, {})
                tgt[of.path[-1]] = v
            res.append(obj)
        return res


def conv(v, kind, col=None, rev=None):
    if v is None:
        return 0 if kind == "count" else None
    if col and col.get("cast") and kind in ("int", "float") and v in (col["cast"].get("nullTokens") or []):
        return None
    try:
        if kind == "count":
            return int(v)
        if kind == "int":
            return int(float(v))
        if kind == "float":
            return float(v)
    except (TypeError, ValueError):
        return None
    if kind == "date":
        return str(v)[:10]
    if kind == "datetime":
        return str(v)[:19]
    if kind == "boolean":
        return v in (True, "true", "True", "1")
    if kind == "enum":
        return rev.get(v) if rev else None     # valor fuera del perfil congelado -> null
    if kind == "point":
        coords = (v or {}).get("coordinates") if isinstance(v, dict) else None
        return {"latitude": coords[1], "longitude": coords[0]} if coords else None
    return v
