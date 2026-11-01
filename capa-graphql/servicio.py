"""Ejecución de una consulta GraphQL completa (paso 6): validación, traducción, SODA y respuesta.

    svc = Servicio()
    svc.ejecutar('{ vacunacionAftosaVichadaAggregate { municipio count } }')
    # {"data": {"vacunacionAftosaVichadaAggregate": [...]}, "extensions": {"dataset": ..., "soql": ..., "ms": ..., "cache": ...}}

La respuesta final la produce graphql-core sobre los datos convertidos, de modo que tipos, nulos y
enums se serializan según el esquema. Las consultas de introspección (__schema, __type) se resuelven
directamente contra el esquema (RF-04).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import graphql

from soda_cliente import SodaCliente
from traductor import Traductor, TranslationError

HERE = Path(__file__).resolve().parent


def es_introspeccion(doc: graphql.DocumentNode) -> bool:
    for d in doc.definitions:
        sel = getattr(d, "selection_set", None)
        if sel and all(getattr(s, "name", None) and s.name.value.startswith("__") for s in sel.selections):
            continue
        return False
    return True


class Servicio:
    def __init__(self, esquemas: Path = HERE / "esquemas", cliente: SodaCliente | None = None,
                 log_path: Path | None = HERE / "logs" / "consultas.jsonl"):
        self.tr = Traductor.desde_directorio(esquemas)
        self.schema = self.tr.schema
        self.cliente = cliente or SodaCliente()
        self.log_path = log_path
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    def _log(self, **kw):
        if self.log_path:
            kw["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with open(self.log_path, "a", encoding="utf8") as f:
                f.write(json.dumps(kw, ensure_ascii=False) + "\n")

    def ejecutar(self, query: str) -> dict:
        t0 = time.perf_counter()
        try:
            doc = graphql.parse(query)
        except graphql.GraphQLError as e:
            return {"errors": [{"message": e.message, "extensions": {"code": "GRAPHQL_VALIDATION_FAILED"}}]}
        if es_introspeccion(doc):
            r = graphql.graphql_sync(self.schema, query)
            return r.formatted
        try:
            t = self.tr.traducir(query)
            res = self.cliente.consultar(t.dataset, t.soql, t.page_size)
            data = self.tr.convertir(t, res.rows)
        except TranslationError as e:
            self._log(query=query, status=e.code, ms=round((time.perf_counter() - t0) * 1000))
            return {"errors": [e.to_graphql_error()]}
        r = graphql.execute(self.schema, doc, root_value={t.root: data})
        out = r.formatted
        ms = round((time.perf_counter() - t0) * 1000)
        out["extensions"] = {"dataset": t.dataset, "soql": t.soql, "filas": len(data), "ms": ms, "cache": res.cache}
        self._log(query=query, dataset=t.dataset, soql=t.soql, status="OK" if not r.errors else "EXECUTION_ERROR",
                  filas=len(data), ms=ms, ms_soda=res.ms, cache=res.cache)
        return out

    def esquema_prompt(self, dataset_o_alias: str) -> str | None:
        d = HERE / "esquemas"
        for f in d.glob("*.mapping.json"):
            m = json.loads(f.read_text(encoding="utf8"))
            if dataset_o_alias in (m["id"], m["alias"]):
                return (d / f"{m['id']}.prompt.graphql").read_text(encoding="utf8")
        return None

    def conjuntos(self) -> list[dict]:
        import yaml
        reg = yaml.safe_load((HERE / "datasets.yaml").read_text(encoding="utf8"))
        return [{"id": e["id"], "alias": e["alias"], "descripcion": e["description"]} for e in reg]
