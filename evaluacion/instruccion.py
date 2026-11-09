"""Plantilla de instrucción en español, común al ajuste QLoRA y a la línea base.

El entrenamiento es completamente en español (decisión del 08/11/2026): la instrucción, las preguntas
y los nombres de campos y valores del esquema están en español. La sintaxis de GraphQL y los
operadores de la capa (`eq`, `in`, `count`, `sum`, `orderBy`, `where`, `ASC`/`DESC`…) conservan su
forma, definida en `capa-graphql/CONVENCIONES.md`.

La instrucción contiene el esquema compacto del conjunto que elige el usuario
(`capa-graphql/esquemas/<id>.prompt.graphql`) y la pregunta, y, en la línea base, un ejemplo en
contexto entre ambos. Se expresa como una conversación (sistema y usuario), y cada modelo la convierte
en texto con su propia plantilla de chat (`tokenizer.apply_chat_template`).

Uso:
    from instruccion import mensajes
    msgs = mensajes("Total de hogares beneficiados en Nariño.", "h2yr-zfb2")
    msgs = mensajes(pregunta, dataset, ejemplo={"pregunta": ..., "graphql": ...}, con_comunes=True)
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ESQUEMAS = Path(__file__).resolve().parent.parent / "capa-graphql" / "esquemas"

SISTEMA = (
    "Eres un asistente que traduce preguntas en español a consultas GraphQL sobre conjuntos de datos "
    "abiertos de datos.gov.co. Recibes el esquema GraphQL del conjunto de datos y una pregunta. "
    "Responde únicamente con la consulta GraphQL, en una sola línea, sin explicaciones ni bloques de código. "
    "Usa solo los campos, filtros y valores que aparecen en el esquema. Las consultas son de solo lectura y "
    "no llevan alias, variables ni fragmentos."
)


@lru_cache(maxsize=None)
def esquema(dataset: str) -> str:
    """Esquema compacto del conjunto (el mismo que recibe el modelo ajustado)."""
    return (ESQUEMAS / f"{dataset}.prompt.graphql").read_text(encoding="utf8").strip()


@lru_cache(maxsize=None)
def comunes() -> str:
    """Tipos compartidos (filtros, orden, escalares) sin descripciones, en el formato compacto.

    El esquema compacto no los incluye porque el modelo ajustado los aprende en el entrenamiento
    (`CONVENCIONES.md` §10). Un modelo sin ajustar no puede aprenderlos, así que la línea base los recibe."""
    sdl = (ESQUEMAS / "comunes.graphql").read_text(encoding="utf8")
    sdl = re.sub(r'"""[\s\S]*?"""', "", sdl)          # descripciones
    bloques = re.findall(r"((?:scalar|enum|input|type)\b[^{\n]*(?:\{[^}]*\})?)", sdl)
    return "\n".join(re.sub(r"\s+", " ", b).strip() for b in bloques)


def usuario(pregunta: str, dataset: str, ejemplo: dict | None = None, con_comunes: bool = False) -> str:
    """Mensaje del usuario: el esquema una sola vez, el ejemplo en contexto (si lo hay) y la pregunta."""
    partes = ["Esquema:"]
    if con_comunes:
        partes.append(comunes())
    partes.append(esquema(dataset))
    if ejemplo is not None:
        partes += ["", "Ejemplo:", f"Pregunta: {ejemplo['pregunta'].strip()}", f"Consulta: {ejemplo['graphql'].strip()}"]
    partes += ["", f"Pregunta: {pregunta.strip()}"]
    return "\n".join(partes)


def mensajes(pregunta: str, dataset: str, ejemplo: dict | None = None, con_comunes: bool = False) -> list[dict]:
    """Conversación para `apply_chat_template`. Sin la respuesta: el modelo la genera.

    El ejemplo en contexto va dentro del mismo mensaje, para no repetir el esquema. Para el ajuste, se
    añade al final `{"role": "assistant", "content": graphql}` (ver `ejemplo_entrenamiento`)."""
    return [{"role": "system", "content": SISTEMA},
            {"role": "user", "content": usuario(pregunta, dataset, ejemplo, con_comunes)}]


def ejemplo_entrenamiento(par: dict) -> list[dict]:
    """Conversación completa de un par del conjunto de datos, para el ajuste QLoRA (sin ejemplo en contexto)."""
    return mensajes(par["pregunta"], par["dataset"]) + [{"role": "assistant", "content": par["graphql"]}]


def extraer_consulta(texto: str) -> str | None:
    """Extrae la consulta GraphQL de la respuesta del modelo.

    Quita los bloques de código y el texto que la rodee, y devuelve desde la primera llave (o la palabra
    `query`) hasta la llave que la cierra. Si las llaves no se cierran, devuelve el texto desde la
    primera llave, para que el error se registre como de sintaxis y no como respuesta vacía."""
    t = re.sub(r"```[a-zA-Z]*", "", texto).replace("```", "").strip()
    m = re.search(r"\bquery\b[^{]*\{|\{", t)
    if not m:
        return None
    inicio = m.start()
    nivel = 0
    for i in range(t.index("{", inicio), len(t)):
        if t[i] == "{":
            nivel += 1
        elif t[i] == "}":
            nivel -= 1
            if nivel == 0:
                return re.sub(r"\s+", " ", t[inicio:i + 1]).strip()
    return re.sub(r"\s+", " ", t[inicio:]).strip()
