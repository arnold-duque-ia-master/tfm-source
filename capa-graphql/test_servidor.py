"""Pruebas del servicio y del servidor. Uso: python3 test_servidor.py [--vivo]"""
import sys
import tempfile
from pathlib import Path

from starlette.testclient import TestClient

from servicio import Servicio
from servidor import crear_app
from soda_cliente import Resultado, SodaCliente
from traductor import TranslationError

HERE = Path(__file__).resolve().parent


class FakeSoda:
    offline = False

    def __init__(self, rows=None, error=None):
        self.rows, self.error, self.llamadas = rows or [], error, []

    def consultar(self, dataset, soql, page_size):
        self.llamadas.append((dataset, soql, page_size))
        if self.error:
            raise self.error
        return Resultado(self.rows, 5, False)


def svc(**kw):
    return Servicio(cliente=FakeSoda(**kw), log_path=None)


def test_respuesta_tipada():
    s = svc(rows=[{"municipio": "SANTA ROSALÍA", "sum_total_aftosa": "40103"}, {"municipio": "CUMARIBO"}])
    r = s.ejecutar('{ vacunacionAftosaVichadaAggregate { municipio count sum { totalAftosa } } }')
    assert "errors" not in r, r
    assert r["data"]["vacunacionAftosaVichadaAggregate"] == [
        {"municipio": "SANTA_ROSALIA", "count": 0, "sum": {"totalAftosa": 40103.0}},
        {"municipio": "CUMARIBO", "count": 0, "sum": {"totalAftosa": None}}]
    assert r["extensions"]["soql"].startswith("SELECT municipio, count(*)")


def test_errores():
    r = svc().ejecutar('{ vacunacionAftosaVichada(limit: 5000) { vereda } }')
    assert r["errors"][0]["extensions"]["code"] == "QUERY_RULE_VIOLATION"
    r = svc().ejecutar('{ vacunacionAftosaVichada { noExiste } }')
    assert r["errors"][0]["extensions"]["code"] == "GRAPHQL_VALIDATION_FAILED"
    r = svc(error=TranslationError("SOQL_ERROR", "x", {"soqlCode": "c"})).ejecutar('{ vacunacionAftosaVichada { vereda } }')
    assert r["errors"][0]["extensions"]["code"] == "SOQL_ERROR"


def test_introspeccion():
    s = svc()
    r = s.ejecutar('{ __type(name: "VacunacionAftosaVichadaMunicipio") { enumValues { name } } }')
    assert [v["name"] for v in r["data"]["__type"]["enumValues"]] == ["CUMARIBO", "LA_PRIMAVERA", "PUERTO_CARRENO", "SANTA_ROSALIA"]
    r = s.ejecutar('{ __schema { queryType { fields { name } } } }')
    assert len(r["data"]["__schema"]["queryType"]["fields"]) == 18
    assert not s.cliente.llamadas


def test_rutas_http():
    c = TestClient(crear_app(svc(rows=[{"count": "7"}])))
    r = c.post("/graphql", json={"query": "{ calidadAguaIrcaAggregate { count } }"})
    assert r.status_code == 200 and r.json()["data"]["calidadAguaIrcaAggregate"] == [{"count": 7}]
    assert c.post("/graphql", json={}).status_code == 400
    assert "GraphiQL" in c.get("/graphql").text
    assert len(c.get("/conjuntos").json()) == 9
    assert c.get("/esquema/calidadAguaIrca").text.startswith("enum ")
    assert c.get("/esquema/nada").status_code == 404


def test_cache_y_offline():
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "c.sqlite"
        cli = SodaCliente(cache_path=db, credenciales={})
        cli._put_cache(cli._key("gcq5-hvdx", "SELECT count(*) AS count LIMIT 100", 100), "gcq5-hvdx",
                       "SELECT count(*) AS count LIMIT 100", 100, [{"count": "2877"}])
        off = SodaCliente(cache_path=db, offline=True, credenciales={})
        s = Servicio(cliente=off, log_path=None)
        r = s.ejecutar("{ vacunacionAftosaVichadaAggregate { count } }")
        assert r["data"]["vacunacionAftosaVichadaAggregate"] == [{"count": 2877}] and r["extensions"]["cache"]
        r = s.ejecutar("{ vacunacionAftosaVichadaAggregate { municipio count } }")
        assert r["errors"][0]["extensions"]["code"] == "UPSTREAM_UNAVAILABLE"


def vivo():
    with tempfile.TemporaryDirectory() as d:
        s = Servicio(cliente=SodaCliente(cache_path=Path(d) / "c.sqlite"), log_path=Path(d) / "log.jsonl")
        q = '{ vacunacionAftosaVichadaAggregate(orderBy: [{sum: {totalAftosa: DESC}}]) { municipio sum { totalAftosa } } }'
        r1, r2 = s.ejecutar(q), s.ejecutar(q)
        print("  1.ª vez:", r1["extensions"]["ms"], "ms, caché", r1["extensions"]["cache"])
        print("  2.ª vez:", r2["extensions"]["ms"], "ms, caché", r2["extensions"]["cache"])
        print("  datos:", r1["data"])
        r = s.ejecutar('{ calidadAguaIrcaAggregate(where: {ircaUrbano: {gt: 80}, anio: {eq: 2023}}) { departamento count } }')
        print("  IRCA urbano > 80 en 2023:", r.get("data") or r.get("errors"))
        bad = SodaCliente(cache_path=None, credenciales={"SOCRATA_APP_TOKEN": "x" * 25})
        r = Servicio(cliente=bad, log_path=None).ejecutar("{ vacunacionAftosaVichadaAggregate { count } }")
        print("  credencial inválida:", r["errors"][0]["extensions"])
        print("  log:", (Path(d) / "log.jsonl").read_text().count("\n"), "líneas")


if __name__ == "__main__":
    ok = 0
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            try:
                f(); ok += 1; print("ok  ", n)
            except Exception as e:
                import traceback; traceback.print_exc(); print("FALLA", n)
    print(f"{ok} pruebas correctas")
    if "--vivo" in sys.argv:
        print("\nPrueba en vivo:")
        vivo()
