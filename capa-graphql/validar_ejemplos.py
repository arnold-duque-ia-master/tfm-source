"""Valida las tripletas pregunta→GraphQL→SoQL de un conjunto.

- La consulta GraphQL debe parsear y ser válida contra el SDL de referencia.
- La consulta SoQL debe ejecutarse en SODA3 (credenciales de ../spike-soda3/.env).
Escribe el resultado de cada SoQL en ejemplos-<id>.resultados.json.

Uso: python3 validar_ejemplos.py gcq5-hvdx
"""
import json, sys
from pathlib import Path
import graphql

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "spike-soda3"))
import soda3_probe as s  # noqa: E402

ds = sys.argv[1] if len(sys.argv) > 1 else "gcq5-hvdx"
schema = graphql.build_schema((HERE / f"esquema-{ds}.graphql").read_text(encoding="utf8"))
token = s.load_token()
ok = 0; out = []
for line in (HERE / f"ejemplos-{ds}.jsonl").read_text(encoding="utf8").splitlines():
    if not line.strip():
        continue
    e = json.loads(line)
    errs = [er.message for er in graphql.validate(schema, graphql.parse(e["graphql"]))]
    r = s.soql(ds, e["soql"], token, page=(1, 1000))
    good = not errs and r["status"] == 200
    ok += good
    out.append({"id": e["id"], "graphql_errores": errs, "soql_http": r["status"], "filas": r["n_rows"],
                "resultado": r["sample"] if r["status"] != 200 else (r["sample"] if r["n_rows"] <= 3 else r["sample"][:3])})
    print(f"{e['id']} {'OK ' if good else 'ERR'} gql={'ok' if not errs else errs} soql={r['status']} filas={r['n_rows']} {json.dumps(out[-1]['resultado'], ensure_ascii=False)[:150]}")
(HERE / f"ejemplos-{ds}.resultados.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf8")
print(f"{ok}/{len(out)} tripletas válidas")
