"""Léxico en español de los 9 conjuntos (OE3).

Para cada conjunto:
  sg, pl, g      nombre de la unidad de fila (singular, plural) y su género (m/f)
  dims           campos de agrupación o filtro: frase del campo, plural, género, forma de filtrar y estilo del valor
  medidas        campos numéricos: frase y agregados con sentido (sum, avg, minmax)
  tiempo         campo de año (rol time o derivado <fecha>Year) y su frase
  fecha          campo de fecha para rangos de meses (opcional)
  mostrar        campos que se listan en las consultas de filas
  texto          campos String sobre los que tiene sentido 'contains'

Estilos de valor: title (Santa Rosalía), lower (arrendado), raw (PM2.5, «Bolsa Ordinaria»).
El filtro usa {v} para el valor mostrado.
"""

LEXICO = {
    "gcq5-hvdx": {
        "alias": "vacunacionAftosaVichada",
        "sg": "registro de vacunación", "pl": "registros de vacunación", "g": "m",
        "tema": "la vacunación contra la fiebre aftosa en el Vichada",
        "dims": {
            "municipio": {"np": "municipio", "pl": "municipios", "g": "m", "filtro": "en {v}", "estilo": "title"},
            "tenencia": {"np": "tipo de tenencia", "pl": "tipos de tenencia", "g": "m", "filtro": "con tenencia {v}", "rel": True, "estilo": "lower"},
            "vereda": {"np": "vereda", "pl": "veredas", "g": "f", "filtro": "en la vereda {v}", "estilo": "title"},
        },
        "medidas": {
            "totalAftosa": {"np": "bovinos vacunados", "agg": ["sum", "avg", "minmax"]},
            "equinos": {"np": "equinos", "agg": ["sum", "avg"]},
            "porcinos": {"np": "porcinos", "agg": ["sum", "avg"]},
            "ovinos": {"np": "ovinos", "agg": ["sum"]},
            "caprinos": {"np": "caprinos", "agg": ["sum"]},
        },
        "tiempo": {"campo": "vigencia", "np": "vigencia"},
        "fecha": {"campo": "fechaRuv", "np": "fecha de registro"},
        "mostrar": ["municipio", "vereda", "fechaRuv", "totalAftosa"],
        "texto": ["vereda"],
    },
    "h2yr-zfb2": {
        "alias": "subsidiosVivienda",
        "sg": "asignación de subsidios de vivienda", "pl": "asignaciones de subsidios de vivienda", "g": "f",
        "tema": "los subsidios de vivienda",
        "dims": {
            "departamento": {"np": "departamento", "pl": "departamentos", "g": "m", "filtro": "en {v}", "estilo": "title"},
            "programa": {"np": "programa", "pl": "programas", "g": "m", "filtro": "del programa «{v}»", "estilo": "raw"},
            "estadoDePostulacion": {"np": "estado de postulación", "pl": "estados de postulación", "g": "m", "filtro": "en estado «{v}»", "rel": True, "estilo": "raw"},
            "municipio": {"np": "municipio", "pl": "municipios", "g": "m", "filtro": "en el municipio de {v}", "estilo": "title"},
        },
        "medidas": {
            "hogares": {"np": "hogares beneficiados", "agg": ["sum", "avg", "minmax"]},
            "valorAsignado": {"np": "valor asignado en pesos", "agg": ["sum", "avg", "minmax"]},
        },
        "tiempo": {"campo": "anioDeAsignacion", "np": "año de asignación"},
        "fecha": None,
        "mostrar": ["departamento", "municipio", "programa", "anioDeAsignacion", "hogares", "valorAsignado"],
        "texto": ["municipio"],
    },
    "uejq-wxrr": {
        "alias": "evaluacionesAgricolas",
        "sg": "registro de la evaluación agropecuaria", "pl": "registros de la evaluación agropecuaria", "g": "m",
        "tema": "las evaluaciones agropecuarias municipales",
        "dims": {
            "departamento": {"np": "departamento", "pl": "departamentos", "g": "m", "filtro": "en {v}", "estilo": "title"},
            "grupoCultivo": {"np": "grupo de cultivo", "pl": "grupos de cultivo", "g": "m", "filtro": "del grupo «{v}»", "estilo": "raw"},
            "cultivo": {"np": "cultivo", "pl": "cultivos", "g": "m", "filtro": "de {v}", "estilo": "lowerfirst"},
            "cicloDelCultivo": {"np": "ciclo del cultivo", "pl": "ciclos de cultivo", "g": "m", "filtro": "de cultivos de ciclo {v}", "rel": True, "estilo": "lower"},
            "municipio": {"np": "municipio", "pl": "municipios", "g": "m", "filtro": "en el municipio de {v}", "estilo": "title"},
        },
        "medidas": {
            "areaSembrada": {"np": "área sembrada en hectáreas", "agg": ["sum", "avg"]},
            "areaCosechada": {"np": "área cosechada en hectáreas", "agg": ["sum", "avg"]},
            "produccion": {"np": "producción en toneladas", "agg": ["sum", "avg", "minmax"]},
            "rendimiento": {"np": "rendimiento en toneladas por hectárea", "agg": ["avg", "minmax"]},
        },
        "tiempo": {"campo": "anio", "np": "año"},
        "fecha": None,
        "mostrar": ["departamento", "municipio", "cultivo", "anio", "produccion"],
        "texto": ["cultivo", "municipio"],
    },
    "8yi9-t44c": {
        "alias": "traficoPeajes",
        "sg": "registro de tráfico mensual", "pl": "registros de tráfico mensual", "g": "m",
        "tema": "el tráfico en los peajes de la ANI",
        "dims": {
            "peaje": {"np": "peaje", "pl": "peajes", "g": "m", "filtro": "en el peaje {v}", "estilo": "title"},
            "categoriaTarifa": {"np": "categoría de tarifa", "pl": "categorías de tarifa", "g": "f", "filtro": "de la categoría {v}", "estilo": "raw"},
        },
        "medidas": {
            "cantidadTrafico": {"np": "vehículos que pasaron", "agg": ["sum", "avg", "minmax"]},
            "cantidadEvasores": {"np": "evasores", "agg": ["sum", "avg"]},
            "cantidadExentos787": {"np": "vehículos exentos", "agg": ["sum"]},
            "valorTarifa": {"np": "valor de la tarifa", "agg": ["avg", "minmax"]},
        },
        "tiempo": {"campo": "desdeYear", "np": "año"},
        "fecha": {"campo": "desde", "np": "fecha de inicio del periodo"},
        "mostrar": ["peaje", "categoriaTarifa", "desde", "cantidadTrafico"],
        "texto": ["peaje"],
    },
    "3ebi-d83g": {
        "alias": "energiaZonasNoInterconectadas",
        "sg": "registro mensual del servicio de energía", "pl": "registros mensuales del servicio de energía", "g": "m",
        "tema": "el servicio de energía en las Zonas No Interconectadas",
        "dims": {
            "departamento": {"np": "departamento", "pl": "departamentos", "g": "m", "filtro": "en {v}", "estilo": "title"},
            "municipio": {"np": "municipio", "pl": "municipios", "g": "m", "filtro": "en el municipio de {v}", "estilo": "title"},
            "localidad": {"np": "localidad", "pl": "localidades", "g": "f", "filtro": "en la localidad {v}", "estilo": "title"},
            "diaDeDemandaMaxima": {"np": "día de demanda máxima", "pl": "días de demanda máxima", "g": "m", "filtro": "cuyo día de demanda máxima fue el {v}", "rel": True, "estilo": "lower"},
        },
        "medidas": {
            "energiaActiva": {"np": "energía activa en kWh", "agg": ["sum", "avg", "minmax"]},
            "energiaReactiva": {"np": "energía reactiva", "agg": ["sum", "avg"]},
            "potenciaMaxima": {"np": "potencia máxima", "agg": ["avg", "minmax"]},
            "promedioDiarioEnHoras": {"np": "horas diarias de servicio", "agg": ["avg", "minmax"]},
        },
        "tiempo": {"campo": "anioServicio", "np": "año de servicio"},
        "fecha": None,
        "mostrar": ["departamento", "municipio", "localidad", "anioServicio", "mesServicio", "energiaActiva"],
        "texto": ["localidad", "municipio"],
    },
    "rtai-k9uh": {
        "alias": "indiceGobiernoDigital",
        "sg": "puntaje del Índice de Gobierno Digital", "pl": "puntajes del Índice de Gobierno Digital", "g": "m",
        "tema": "el Índice de Gobierno Digital",
        "dims": {
            "orden": {"np": "orden", "pl": "órdenes", "g": "m", "filtro": "de entidades del orden {v}", "rel": True, "estilo": "lower"},
            "sector": {"np": "sector", "pl": "sectores", "g": "m", "filtro": "del sector {v}", "estilo": "lower"},
            "indice": {"np": "índice", "pl": "índices", "g": "m", "filtro": "del índice «{v}»", "estilo": "raw"},
            "departamento": {"np": "departamento", "pl": "departamentos", "g": "m", "filtro": "de entidades de {v}", "rel": True, "estilo": "title"},
        },
        "medidas": {
            "puntajeEntidad": {"np": "puntaje de la entidad", "agg": ["avg", "minmax"]},
            "promedioGrupoPar": {"np": "promedio del grupo par", "agg": ["avg"]},
        },
        "tiempo": {"campo": "vigencia", "np": "vigencia"},
        "fecha": None,
        "mostrar": ["entidad", "indice", "vigencia", "puntajeEntidad"],
        "texto": ["entidad"],
        "sin_evolucion": True,   # los puntajes 2021 y 2025 no son comparables
    },
    "kekd-7v7h": {
        "alias": "calidadAire",
        "sg": "registro anual de calidad del aire", "pl": "registros anuales de calidad del aire", "g": "m",
        "tema": "la calidad del aire",
        "dims": {
            "variable": {"np": "variable", "pl": "variables", "g": "f", "filtro": "de la variable {v}", "estilo": "raw"},
            "nombreDelDepartamento": {"np": "departamento", "pl": "departamentos", "g": "m", "filtro": "en {v}", "estilo": "title"},
            "tipoDeEstacion": {"np": "tipo de estación", "pl": "tipos de estación", "g": "m", "filtro": "de estaciones de tipo {v}", "rel": True, "estilo": "lower"},
            "autoridadAmbiental": {"np": "autoridad ambiental", "pl": "autoridades ambientales", "g": "f", "filtro": "de la autoridad ambiental {v}", "estilo": "raw"},
            "nombreDelMunicipio": {"np": "municipio", "pl": "municipios", "g": "m", "filtro": "en el municipio de {v}", "estilo": "title"},
        },
        "medidas": {
            "promedio": {"np": "concentración promedio", "agg": ["avg", "minmax"]},
            "maximo": {"np": "valor máximo medido", "agg": ["minmax"]},
            "diasDeExcedencias": {"np": "días de excedencia", "agg": ["sum", "avg"]},
            "excedenciasLimiteActual": {"np": "excedencias del límite actual", "agg": ["sum"]},
            "noDeDatos": {"np": "número de datos", "agg": ["sum", "avg"]},
        },
        "tiempo": {"campo": "anio", "np": "año"},
        "fecha": None,
        "mostrar": ["estacion", "nombreDelMunicipio", "variable", "anio", "promedio"],
        "texto": ["estacion"],
    },
    "nxt2-39c3": {
        "alias": "calidadAguaIrca",
        "sg": "registro municipal del IRCA", "pl": "registros municipales del IRCA", "g": "m",
        "tema": "la calidad del agua para consumo humano",
        "dims": {
            "departamento": {"np": "departamento", "pl": "departamentos", "g": "m", "filtro": "en {v}", "estilo": "title"},
            "nivelDeRiesgo": {"np": "nivel de riesgo", "pl": "niveles de riesgo", "g": "m", "filtro": "clasificados como «{v}»", "rel": True, "estilo": "lowerfirst"},
            "municipio": {"np": "municipio", "pl": "municipios", "g": "m", "filtro": "en el municipio de {v}", "estilo": "title"},
        },
        "medidas": {
            "irca": {"np": "IRCA", "agg": ["avg", "minmax"]},
            "ircaUrbano": {"np": "IRCA urbano", "agg": ["avg", "minmax"]},
            "ircaRural": {"np": "IRCA rural", "agg": ["avg", "minmax"]},
        },
        "tiempo": {"campo": "anio", "np": "año"},
        "fecha": None,
        "mostrar": ["departamento", "municipio", "anio", "irca", "nivelDeRiesgo"],
        "texto": ["municipio"],
    },
    "ni93-8mm5": {
        "alias": "preciosMinerales",
        "sg": "precio base de mineral", "pl": "precios base de minerales", "g": "m",
        "tema": "los precios base de minerales para regalías",
        "dims": {
            "mineral": {"np": "mineral", "pl": "minerales", "g": "m", "filtro": "del mineral {v}", "estilo": "title"},
            "unidad": {"np": "unidad", "pl": "unidades", "g": "f", "filtro": "expresados en {v}", "rel": True, "estilo": "raw"},
        },
        "medidas": {
            "precio": {"np": "precio base", "agg": ["avg", "minmax"]},
        },
        "tiempo": {"campo": "fechaDeResolucionYear", "np": "año de la resolución"},
        "fecha": {"campo": "fechaDeInicio", "np": "fecha de inicio de vigencia"},
        "mostrar": ["mineral", "precio", "unidad", "fechaDeInicio", "fechaFin"],
        "texto": ["mineral"],
    },
}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
