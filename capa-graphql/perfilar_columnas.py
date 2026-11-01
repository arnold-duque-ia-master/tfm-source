"""Perfila las columnas de un conjunto para el generador de esquema.

Para cada columna calcula lo que el generador necesita y que no está en los metadatos:
  - text:   valores distintos (lista completa si son <= ENUM_MAX) y si parece numérica.
  - number: si todos los valores son enteros, mínimo y máximo.
  - fechas: mínimo y máximo.
Guarda perfiles/<id>.json. El resultado queda congelado: el generador no consulta el portal.

Uso: python3 perfilar_columnas.py gcq5-hvdx [...]
"""
import json, re, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "spike-soda3"))
import soda3_probe as s  # noqa: E402

ENUM_MAX = 60  # se guardan hasta 60 valores; el umbral de enum lo aplica el generador
NUM_RE = re.compile(r"^-?\d+([.,]\d+)?$")


def q(ds, sql, tok):
    r = s.soql(ds, sql, tok, page=(1, 1000))
    if r["status"] != 200:
        raise RuntimeError(f"{ds}: {sql} -> {r['status']} {r['sample']}")
    return r["rows"]


def perfilar(ds, tok):
    meta = json.loads((HERE / "metadata" / f"{ds}.json").read_text(encoding="utf8"))
    cols = [c for c in meta["columns"] if not c["fieldName"].startswith(":")]
    total = int(q(ds, "SELECT count(*) AS n", tok)[0]["n"])
    out = {"id": ds, "perfilado": datetime.date.today().isoformat(), "filas": total, "columnas": {}}
    for c in cols:
        f, t = c["fieldName"], c["dataTypeName"]
        p = {"tipo": t}
        if t == "text":
            r = q(ds, f"SELECT count(distinct {f}) AS d, count({f}) AS nn", tok)[0]
            p["distintos"], p["no_nulos"] = int(r["d"]), int(r["nn"])
            if p["distintos"] <= ENUM_MAX:
                p["valores"] = [x.get(f) for x in q(ds, f"SELECT {f}, count(*) AS n GROUP BY {f} ORDER BY {f}", tok) if x.get(f) is not None]
            top = q(ds, f"SELECT {f}, count(*) AS n GROUP BY {f} ORDER BY n DESC LIMIT 50", tok)
            vals = [x.get(f) for x in top if x.get(f) is not None]
            num = [v for v in vals if NUM_RE.match(v.strip())]
            p["frac_numerica_top50"] = round(len(num) / len(vals), 2) if vals else 0
            if 0 < len(num) < len(vals):
                p["no_numericos_top50"] = [v for v in vals if not NUM_RE.match(v.strip())][:10]
            p["ceros_a_la_izquierda"] = any(v.startswith("0") and len(v) > 1 and v.isdigit() for v in num)
        elif t in ("number", "money", "percent"):
            r = q(ds, f"SELECT min({f}) AS a, max({f}) AS b, count({f}) AS nn", tok)[0]
            p["min"], p["max"], p["no_nulos"] = r.get("a"), r.get("b"), int(r["nn"])
            p["entero"] = int(q(ds, f"SELECT count(*) AS n WHERE {f} != floor({f})", tok)[0]["n"]) == 0
        elif t in ("calendar_date", "floating_timestamp"):
            r = q(ds, f"SELECT min({f}) AS a, max({f}) AS b, count({f}) AS nn", tok)[0]
            p["min"], p["max"], p["no_nulos"] = r.get("a"), r.get("b"), int(r["nn"])
            p["con_hora"] = int(q(ds, f"SELECT count(*) AS n WHERE date_trunc_ymd({f}) != {f}", tok)[0]["n"]) > 0
        out["columnas"][f] = p
    (HERE / "perfiles" / f"{ds}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
    return out


if __name__ == "__main__":
    tok = s.load_token()
    for ds in sys.argv[1:]:
        o = perfilar(ds, tok)
        print(ds, o["filas"], "filas")
        for f, p in o["columnas"].items():
            extra = {k: v for k, v in p.items() if k not in ("tipo",) and not (k == "valores" and len(v) > 8)}
            if "valores" in p and len(p["valores"]) > 8: extra["valores"] = p["valores"][:8] + ["…"]
            print("  ", f, p["tipo"], json.dumps(extra, ensure_ascii=False)[:230])
