"""Prueba de la API SODA3 de datos.gov.co (paso 1 de la capa GraphQL).

Para cada conjunto de datos:
  1. Descarga los metadatos (/api/views/{id}.json) y los guarda en out/metadata/.
  2. Lanza consultas SoQL de prueba por POST (/api/v3/views/{id}/query.json):
     muestra, conteo, filtro, agregación, rango de fechas, paginación,
     error provocado y petición sin token.
  3. Escribe un informe en Markdown con tipos de columna, forma de la
     respuesta, tiempos y formato de errores.

Uso:
  export SOCRATA_APP_TOKEN=...      (o un archivo .env junto al script)
  python3 soda3_probe.py gcq5-hvdx [otro-id ...]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path

import requests

BASE = "https://www.datos.gov.co"
HERE = Path(__file__).resolve().parent
TIMEOUT = 60


def load_env() -> dict:
    """Lee SOCRATA_APP_TOKEN o, alternativamente, SOCRATA_KEY_ID y SOCRATA_KEY_SECRET (API key)."""
    vals = {}
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"\'')
    for k in ("SOCRATA_APP_TOKEN", "SOCRATA_KEY_ID", "SOCRATA_KEY_SECRET"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    return {k: v for k, v in vals.items() if v}


def load_token():
    """Devuelve (headers, auth) para las peticiones autenticadas, o None."""
    v = load_env()
    if v.get("SOCRATA_KEY_ID") and v.get("SOCRATA_KEY_SECRET"):
        return ({}, (v["SOCRATA_KEY_ID"], v["SOCRATA_KEY_SECRET"]))
    if v.get("SOCRATA_APP_TOKEN"):
        return ({"X-App-Token": v["SOCRATA_APP_TOKEN"]}, None)
    return None


def get_metadata(ds: str) -> dict:
    r = requests.get(f"{BASE}/api/views/{ds}.json", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def soql(ds: str, query: str, token, page=(1, 100)) -> dict:
    """Ejecuta una consulta SoQL y devuelve un registro con todo lo observado."""
    headers = {"Accept": "application/json"}
    auth = None
    if token:
        headers.update(token[0])
        auth = token[1]
    body = {
        "query": query,
        "page": {"pageNumber": page[0], "pageSize": page[1]},
        "includeSynthetic": False,
    }
    t0 = time.perf_counter()
    r = requests.post(f"{BASE}/api/v3/views/{ds}/query.json", json=body,
                      headers=headers, auth=auth, timeout=TIMEOUT)
    ms = round((time.perf_counter() - t0) * 1000)
    try:
        payload = r.json()
    except ValueError:
        payload = r.text[:2000]
    rows = payload if isinstance(payload, list) else None
    value_types = {}
    if rows:
        for k in rows[0]:
            value_types[k] = dict(Counter(type(x.get(k)).__name__ for x in rows))
    return {
        "query": query,
        "page": page,
        "status": r.status_code,
        "ms": ms,
        "response_type": type(payload).__name__,
        "n_rows": len(rows) if rows is not None else None,
        "value_types": value_types,
        "headers": {k: v for k, v in r.headers.items()
                    if k.lower().startswith(("x-soda", "x-socrata", "x-ratelimit", "content-type", "last-modified"))},
        "sample": rows[:3] if rows else payload,
        "rows": rows,
    }


def pick(cols, types, exclude=()):
    for c in cols:
        if c["dataTypeName"] in types and not c["fieldName"].startswith(exclude):
            return c["fieldName"]
    return None


def probe(ds: str, token, out: Path) -> None:
    meta = get_metadata(ds)
    (out / "metadata").mkdir(parents=True, exist_ok=True)
    (out / "metadata" / f"{ds}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf8")

    cols = [c for c in meta["columns"] if not c["fieldName"].startswith(":")]
    text_col = pick(cols, {"text"}, exclude=("departamento",)) or pick(cols, {"text"})
    num_col = pick(cols, {"number"}, exclude=("codigo", "cod_", "lat", "lon", "id", "ruv", "vigencia", "anio", "ano"))
    date_col = pick(cols, {"calendar_date", "floating_timestamp", "fixed_timestamp"})

    results = []
    if token:
        sample = soql(ds, "SELECT *", token, page=(1, 5))
        results.append(("Muestra (SELECT *)", sample))
        results.append(("Conteo total", soql(ds, "SELECT count(*) AS total", token)))
        if text_col and isinstance(sample["sample"], list) and sample["sample"]:
            val = str(sample["sample"][0].get(text_col, "")).replace("'", "''")
            results.append(("Filtro por texto",
                            soql(ds, f"SELECT * WHERE {text_col} = '{val}'", token, page=(1, 5))))
        if text_col and num_col:
            results.append(("Agregación con GROUP BY", soql(
                ds, f"SELECT {text_col}, sum({num_col}) AS suma, count(*) AS n "
                    f"GROUP BY {text_col} ORDER BY suma DESC", token, page=(1, 10))))
        if date_col:
            results.append(("Rango de fechas y orden", soql(
                ds, f"SELECT {date_col} WHERE {date_col} >= '2020-01-01T00:00:00' "
                    f"ORDER BY {date_col} DESC", token, page=(1, 5))))
            results.append(("Mínimo y máximo de fecha", soql(
                ds, f"SELECT min({date_col}) AS desde, max({date_col}) AS hasta", token)))
        p1 = soql(ds, "SELECT * ORDER BY :id", token, page=(1, 3))
        p2 = soql(ds, "SELECT * ORDER BY :id", token, page=(2, 3))
        results.append(("Paginación, página 1", p1))
        results.append(("Paginación, página 2", p2))
        results.append(("Error provocado (columna inexistente)",
                        soql(ds, "SELECT columna_que_no_existe", token)))
    results.append(("Sin token de aplicación", soql(ds, "SELECT *", None, page=(1, 1))))

    (out / f"resultados-{ds}.json").write_text(
        json.dumps([{"caso": n, **r} for n, r in results], ensure_ascii=False, indent=2, default=str),
        encoding="utf8")
    write_report(ds, meta, cols, results, token is not None, out)


def write_report(ds, meta, cols, results, with_token, out: Path) -> None:
    L = [f"# Prueba SODA3: `{ds}`", "",
         f"- **Nombre:** {meta.get('name')}",
         f"- **Publicador:** {meta.get('attribution')}",
         f"- **Licencia:** {(meta.get('license') or {}).get('name')}",
         f"- **Categoría:** {meta.get('category')}",
         f"- **Última actualización de filas (epoch):** {meta.get('rowsUpdatedAt')}",
         f"- **Consultas con token:** {'sí' if with_token else 'no (solo metadatos y prueba sin token)'}",
         "", "## Columnas", "", "| fieldName | dataTypeName | Etiqueta visible | Descripción |",
         "|---|---|---|---|"]
    for c in cols:
        desc = (c.get("description") or "").replace("\n", " ").replace("|", "/")[:80]
        L.append(f"| `{c['fieldName']}` | {c['dataTypeName']} | {c.get('name')} | {desc} |")
    L += ["", "## Consultas", "", "| Caso | HTTP | ms | Filas | Tipo de respuesta |", "|---|---|---|---|---|"]
    for name, r in results:
        L.append(f"| {name} | {r['status']} | {r['ms']} | {r['n_rows']} | {r['response_type']} |")
    for name, r in results:
        L += ["", f"### {name}", "", "```sql", r["query"], "```",
              f"Página {r['page']}. Tipos de los valores devueltos: `{r['value_types']}`", "",
              f"Cabeceras relevantes: `{r['headers']}`", "", "```json",
              json.dumps(r["sample"], ensure_ascii=False, indent=2, default=str)[:1500], "```"]
    (out / f"informe-{ds}.md").write_text("\n".join(L) + "\n", encoding="utf8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datasets", nargs="*", default=["gcq5-hvdx"])
    ap.add_argument("--out", default=str(HERE / "out"))
    a = ap.parse_args()
    token = load_token()
    if not token:
        print("AVISO: no hay SOCRATA_APP_TOKEN; solo se descargan metadatos y se prueba la petición sin token.")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for ds in a.datasets:
        print(f"→ {ds}")
        probe(ds, token, out)
        print(f"  informe: {out / f'informe-{ds}.md'}")


if __name__ == "__main__":
    main()
