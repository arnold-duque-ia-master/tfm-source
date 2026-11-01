"""Pruebas del generador (sin red). Uso: python3 -m pytest -q test_generador.py  o  python3 test_generador.py"""
import json
from pathlib import Path

import graphql

import generador as g

HERE = Path(__file__).resolve().parent


def schema_for(ds):
    entry, meta, prof = g.load(ds)
    sdl = g.generate(entry, g.build_columns(entry, meta, prof))
    return graphql.build_schema(g.COMUNES + "type Query\n" + sdl)


def shape(schema):
    """Estructura comparable: tipo -> {campo: tipo (con argumentos)} sin descripciones ni orden."""
    out = {}
    for name, t in schema.type_map.items():
        if name.startswith("__") or name in ("String", "Int", "Float", "Boolean", "ID"):
            continue
        if hasattr(t, "fields"):
            out[name] = {f: str(v.type) + str(sorted((a, str(x.type)) for a, x in getattr(v, "args", {}).items()))
                         for f, v in t.fields.items()}
        elif hasattr(t, "values"):
            out[name] = set(t.values)
    return out


def test_ejemplos_validos_contra_esquema_generado():
    s = schema_for("gcq5-hvdx")
    for line in (HERE / "ejemplos-gcq5-hvdx.jsonl").read_text(encoding="utf8").splitlines():
        e = json.loads(line)
        errs = graphql.validate(s, graphql.parse(e["graphql"]))
        assert not errs, (e["id"], [x.message for x in errs])


def test_todos_los_conjuntos_generan_esquema_valido():
    import yaml
    for e in yaml.safe_load((HERE / "datasets.yaml").read_text(encoding="utf8")):
        schema_for(e["id"])


def test_nombres():
    assert g.camel("Código Divipola Departamento") == "codigoDivipolaDepartamento"
    assert g.camel("CategoriaTarifa") == "categoriaTarifa"
    assert g.camel("Tiempo de exposición (horas)") == "tiempoDeExposicionHoras"
    assert g.camel("CÓDIGO_SIGEP") == "codigoSigep"
    assert g.camel("Año de Asignación") == "anioDeAsignacion"
    assert g.enum_value_name("SANTA ROSALÍA") == "SANTA_ROSALIA"
    assert g.enum_value_name("2025A") == "_2025A"


def test_fusion_de_variantes():
    entry, meta, prof = g.load("3ebi-d83g")
    cols = {c.name: c for c in g.build_columns(entry, meta, prof)}
    assert sorted(cols["diaDeDemandaMaxima"].enum_values["DOMINGO"]) == ["Domingo", "domingo"]


def test_sinonimos():
    entry, meta, prof = g.load("nxt2-39c3")
    cols = {c.field: c for c in g.build_columns(entry, meta, prof)}
    assert cols["nivel_de_riesgo"].enum_values["ALTO_RIESGO"] == ["Alto riesgo", "Riesgo alto"]
    entry, meta, prof = g.load("rtai-k9uh")
    cols = {c.field: c for c in g.build_columns(entry, meta, prof)}
    assert "Toma de decisiones basadas en datos" in cols["ndice"].enum_values["DECISIONES_BASADAS_EN_DATOS"]
    assert "GOBIERNO_DIGITAL" not in cols["ndice"].enum_values
    entry, meta, prof = g.load("3ebi-d83g")
    cols = {c.field: c for c in g.build_columns(entry, meta, prof)}
    assert len(cols["dpto"].enum_values["ARCHIPIELAGO_DE_SAN_ANDRES_PROVIDENCIA_Y_SANTA_CATALINA"]) == 5
    assert g.group_values(["PM10", "PM2.5", "NO", "NO2"]) == [["PM10"], ["PM2.5"], ["NO"], ["NO2"]]


def test_exclusiones_y_casts():
    entry, meta, prof = g.load("gcq5-hvdx")
    names = {c.field for c in g.build_columns(entry, meta, prof)}
    assert "predio" not in names
    entry, meta, prof = g.load("nxt2-39c3")
    cols = {c.field: c for c in g.build_columns(entry, meta, prof)}
    assert cols["ircaurbano"].kind == "float" and cols["ircaurbano"].cast["nullTokens"] == ["ND"]


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
    ref = shape(graphql.build_schema((HERE / "esquema-gcq5-hvdx.graphql").read_text(encoding="utf8")))
    gen = shape(schema_for("gcq5-hvdx"))
    print("\nDiferencias con el esquema escrito a mano (gcq5-hvdx):")
    for t in sorted(set(ref) | set(gen)):
        a, b = ref.get(t), gen.get(t)
        if a == b:
            continue
        if a is None or b is None:
            print(f"  {t}: {'solo en generado' if a is None else 'solo en referencia'}"); continue
        ka, kb = set(a), set(b)
        diff = {"+": sorted(kb - ka), "-": sorted(ka - kb), "~": sorted(k for k in ka & kb if a[k] != b[k])} if isinstance(a, dict) else {"+": sorted(b - a), "-": sorted(a - b)}
        print(f"  {t}: " + "; ".join(f"{k} {v}" for k, v in diff.items() if v))
