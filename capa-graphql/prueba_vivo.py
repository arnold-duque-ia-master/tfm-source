"""Prueba de extremo a extremo contra SODA3: GraphQL -> SoQL -> SODA -> respuesta convertida.
Uso: python3 prueba_vivo.py   (credenciales en ../spike-soda3/.env)"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "spike-soda3"))
import soda3_probe as s  # noqa: E402
from traductor import Traductor, TranslationError  # noqa: E402

CONSULTAS = [
    '{ vacunacionAftosaVichadaAggregate(where: {municipio: {eq: CUMARIBO}, vigencia: {eq: 2024}}) { sum { totalAftosa } } }',
    '{ vacunacionAftosaVichada(orderBy: [{totalAftosa: DESC}], limit: 2) { municipio vereda tenencia fechaRuv totalAftosa latitud } }',
    '{ subsidiosViviendaAggregate(where: {anioDeAsignacion: {gte: 2020}}, orderBy: [{sum: {valorAsignado: DESC}}], limit: 3) { departamento sum { valorAsignado hogares } } }',
    '{ subsidiosViviendaAggregate(orderBy: [{count: DESC}], limit: 3) { programa count } }',
    '{ evaluacionesAgricolasAggregate(where: {cultivo: {eq: "Café"}, anio: {eq: 2024}}, orderBy: [{sum: {produccion: DESC}}], limit: 3) { departamento sum { produccion areaCosechada } } }',
    '{ evaluacionesAgricolasAggregate(where: {grupoCultivo: {eq: FRUTALES}}, limit: 3, orderBy: [{countDistinct: {cultivo: DESC}}]) { departamento countDistinct { cultivo } } }',
    '{ traficoPeajesAggregate(where: {desdeYear: {eq: 2025}}, orderBy: [{sum: {cantidadTrafico: DESC}}], limit: 3) { peaje sum { cantidadTrafico cantidadEvasores } } }',
    '{ traficoPeajes(where: {peaje: {contains: "alvarado"}, desde: {gte: "2026-01-01"}}, limit: 3, orderBy: [{desde: DESC}]) { peaje categoriaTarifa desde hasta valorTarifa cantidadTrafico } }',
    '{ energiaZonasNoInterconectadasAggregate(where: {diaDeDemandaMaxima: {eq: DOMINGO}}) { count } }',
    '{ energiaZonasNoInterconectadasAggregate(where: {departamento: {eq: ARCHIPIELAGO_DE_SAN_ANDRES_PROVIDENCIA_Y_SANTA_CATALINA}}, orderBy: [{anioServicio: ASC}]) { anioServicio count sum { energiaActiva } } }',
    '{ energiaZonasNoInterconectadas(where: {fechaDeDemandaMaxima: {gte: "2026-09-01T00:00:00"}}, orderBy: [{potenciaMaxima: DESC}], limit: 2) { localidad fechaDeDemandaMaxima diaDeDemandaMaxima potenciaMaxima } }',
    '{ indiceGobiernoDigitalAggregate(where: {indice: {eq: DECISIONES_BASADAS_EN_DATOS}}, orderBy: [{vigencia: ASC}]) { vigencia count avg { puntajeEntidad } } }',
    '{ indiceGobiernoDigitalAggregate(where: {sector: {eq: DEPORTE}}) { count } }',
    '{ calidadAireAggregate(where: {variable: {eq: PM2_5}, anio: {eq: 2024}}, orderBy: [{avg: {promedio: DESC}}], limit: 3) { nombreDelDepartamento avg { promedio } max { maximo } } }',
    '{ calidadAireAggregate(where: {representatividadTemporal: {gte: 75}}) { tipoDeEstacion count avg { representatividadTemporal } } }',
    '{ calidadAguaIrcaAggregate(where: {anio: {eq: 2023}}) { nivelDeRiesgo count } }',
    '{ calidadAguaIrca(where: {ircaUrbano: {gt: 80}, anio: {eq: 2023}}, limit: 3, orderBy: [{ircaUrbano: DESC}]) { departamento municipio ircaUrbano nivelDeRiesgoUrbano } }',
    '{ calidadAguaIrcaAggregate(where: {departamento: {eq: ANTIOQUIA}}, orderBy: [{anio: DESC}], limit: 2) { anio count } }',
    '{ preciosMinerales(where: {mineral: {contains: "oro"}, fechaDeInicio: {gte: "2026-01-01"}}, limit: 3) { mineral precio unidad fechaDeInicio fechaFin } }',
    '{ preciosMineralesAggregate(where: {fechaDeResolucionYear: {eq: 2025}}) { unidad count min { precio } max { precio } } }',
]


def main():
    t = Traductor.desde_directorio(HERE / "esquemas")
    tok = s.load_token()
    ok = 0
    for i, qs in enumerate(CONSULTAS, 1):
        try:
            tr = t.traducir(qs)
        except TranslationError as e:
            print(f"[{i:02}] ERROR DE TRADUCCIÓN {e.code}: {e.message}\n     {qs}")
            continue
        r = s.soql(tr.dataset, tr.soql, tok, page=(1, tr.page_size))
        if r["status"] != 200:
            print(f"[{i:02}] SODA {r['status']}: {json.dumps(r['sample'], ensure_ascii=False)[:300]}\n     {tr.soql}")
            continue
        data = t.convertir(tr, r["rows"])
        ok += 1
        print(f"[{i:02}] OK {r['ms']} ms {tr.dataset}\n     {tr.soql}\n     → {json.dumps(data[:3], ensure_ascii=False)[:330]}")
    print(f"\n{ok}/{len(CONSULTAS)} consultas correctas")


if __name__ == "__main__":
    main()
