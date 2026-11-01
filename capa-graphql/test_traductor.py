"""Pruebas del traductor (sin red). Uso: python3 test_traductor.py"""
import json
from pathlib import Path

from traductor import Traductor, TranslationError

HERE = Path(__file__).resolve().parent
T = Traductor.desde_directorio(HERE / "esquemas")


def soql(qs):
    return T.traducir(qs).soql


def err(qs):
    try:
        T.traducir(qs)
    except TranslationError as e:
        return e.code
    return None


def test_tripletas_gcq5():
    for line in (HERE / "ejemplos-gcq5-hvdx.jsonl").read_text(encoding="utf8").splitlines():
        e = json.loads(line)
        got = soql(e["graphql"])
        assert got == e["soql"], f"{e['id']}\n  esperado: {e['soql']}\n  obtenido: {got}"


def test_enum_fusionado():
    assert soql('{ energiaZonasNoInterconectadasAggregate(where: {diaDeDemandaMaxima: {eq: DOMINGO}}) { count } }') == \
        "SELECT count(*) AS count WHERE dia_demanda_maxima IN ('Domingo', 'domingo') LIMIT 100"
    assert soql('{ calidadAguaIrcaAggregate(where: {nivelDeRiesgo: {in: [ALTO_RIESGO, SIN_RIESGO]}}) { count } }') == \
        "SELECT count(*) AS count WHERE municipiocodigo != '#TODOS' AND nivel_de_riesgo IN ('Alto riesgo', 'Riesgo alto', 'Sin riesgo') LIMIT 100"


def test_cast_y_base_where():
    assert soql('{ calidadAguaIrcaAggregate(where: {ircaUrbano: {gt: 80}}) { anio max { ircaUrbano } } }') == (
        "SELECT a_o, max(case(ircaurbano IN ('ND'), NULL, true, ircaurbano::number)) AS max_ircaurbano "
        "WHERE municipiocodigo != '#TODOS' AND case(ircaurbano IN ('ND'), NULL, true, ircaurbano::number) > 80.0 "
        "GROUP BY a_o LIMIT 100")
    assert soql('{ energiaZonasNoInterconectadasAggregate(orderBy: [{anioServicio: ASC}]) { anioServicio sum { energiaActiva } } }') == (
        "SELECT anio::number AS anio_num, sum(energia_activa) AS sum_energia_activa GROUP BY anio_num ORDER BY anio_num ASC LIMIT 100")


def test_datetime():
    assert soql('{ energiaZonasNoInterconectadas(where: {fechaDeDemandaMaxima: {gte: "2026-01-01T00:00:00"}}, limit: 3) { localidad fechaDeDemandaMaxima } }') == \
        "SELECT localidad, fecha_demanda_maxima WHERE fecha_demanda_maxima >= '2026-01-01T00:00:00' ORDER BY :id LIMIT 3"
    assert err('{ energiaZonasNoInterconectadas(where: {fechaDeDemandaMaxima: {gte: "enero"}}) { localidad } }') == "QUERY_RULE_VIOLATION"


def test_reglas():
    assert err('{ vacunacionAftosaVichada(limit: 5000) { vereda } }') == "QUERY_RULE_VIOLATION"
    assert err('{ vacunacionAftosaVichada(offset: -1) { vereda } }') == "QUERY_RULE_VIOLATION"
    assert err('{ a: vacunacionAftosaVichada { vereda } }') == "QUERY_RULE_VIOLATION"
    assert err('query($m: VacunacionAftosaVichadaMunicipio) { vacunacionAftosaVichada(where: {municipio: {eq: $m}}) { vereda } }') == "QUERY_RULE_VIOLATION"
    assert err('{ vacunacionAftosaVichada { vereda } vacunacionAftosaVichadaAggregate { count } }') == "QUERY_RULE_VIOLATION"
    assert err('{ vacunacionAftosaVichada(orderBy: [{vereda: ASC, ruv: DESC}]) { vereda } }') == "QUERY_RULE_VIOLATION"
    assert err('{ vacunacionAftosaVichadaAggregate(orderBy: [{vereda: ASC}]) { municipio count } }') == "QUERY_RULE_VIOLATION"
    assert err('{ vacunacionAftosaVichadaAggregate(where: {tenencia: {in: []}}) { count } }') == "QUERY_RULE_VIOLATION"
    assert err('{ vacunacionAftosaVichada(where: {municipio: {eq: BOGOTA}}) { vereda } }') == "GRAPHQL_VALIDATION_FAILED"
    assert err('{ vacunacionAftosaVichada { predio } }') == "GRAPHQL_VALIDATION_FAILED"
    assert err('{ vacunacionAftosaVichada { vereda ') == "GRAPHQL_VALIDATION_FAILED"


def test_escape_y_logicos():
    assert soql('{ vacunacionAftosaVichadaAggregate(where: {vereda: {eq: "LA O\'HIGGINS"}, _and: [{equinos: {gt: 0}, ovinos: {gt: 0}}]}) { count } }') == \
        "SELECT count(*) AS count WHERE vereda = 'LA O''HIGGINS' AND (ovinos > 0 AND equinos > 0) LIMIT 100".replace("(ovinos > 0 AND equinos > 0)", "(equinos > 0 AND ovinos > 0)")


def test_convertir():
    tr = T.traducir('{ calidadAguaIrcaAggregate { nivelDeRiesgo count avg { ircaUrbano } } }')
    rows = [{"nivel_de_riesgo": "Riesgo alto", "count": "12", "avg_ircaurbano": "45.5"}, {"nivel_de_riesgo": "Desconocido", "count": "1"}]
    assert T.convertir(tr, rows) == [{"nivelDeRiesgo": "ALTO_RIESGO", "count": 12, "avg": {"ircaUrbano": 45.5}},
                                     {"nivelDeRiesgo": None, "count": 1, "avg": {"ircaUrbano": None}}]
    tr = T.traducir('{ calidadAguaIrca(limit: 1) { ircaUrbano anio } }')
    assert T.convertir(tr, [{"ircaurbano": "ND", "a_o": "2007"}]) == [{"ircaUrbano": None, "anio": 2007}]
    tr = T.traducir('{ vacunacionAftosaVichada(limit: 1) { fechaRuv totalAftosa } }')
    assert T.convertir(tr, [{"fecha_ruv": "2024-10-28T00:00:00.000", "total_aftosa": "148"}]) == [{"fechaRuv": "2024-10-28", "totalAftosa": 148}]


if __name__ == "__main__":
    ok = 0
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            try:
                f(); ok += 1; print("ok  ", n)
            except AssertionError as e:
                print("FALLA", n, e)
    print(f"{ok} pruebas correctas")
