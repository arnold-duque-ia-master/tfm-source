"""Línea base de recuperación por vecino más cercano con Qwen3-Embedding-0.6B-GraphQL.

EXPERIMENTO DESCARTADO el 08/11/2026 (ver README.md de esta carpeta): la línea base del TFM es
Granite-8B-Code-Instruct (`../../linea_base_granite.py`). Se conserva para que el resultado sea reproducible.

El modelo de *embeddings* se usa tal como se publica, sin ningún entrenamiento adicional. Como no
genera texto, la línea base no escribe consultas: para cada pregunta de la partición evaluada busca,
por similitud de coseno, la pregunta más parecida de `train.jsonl` **del mismo conjunto de datos**
(la misma información que recibe el modelo ajustado: la pregunta y el conjunto que elige el usuario)
y devuelve su consulta GraphQL sin modificar. Las predicciones se evalúan después con `../../evaluar.py`,
igual que las de Qwen2.5-Coder y CodeLlama ajustados.

El conjunto reservado (`ni93-8mm5`) no tiene pares de entrenamiento de su esquema, así que la línea
base no se aplica a `reservado.jsonl`.

Uso (desde esta carpeta, con las dependencias de `../../requirements.txt`):
    python3 linea_base_recuperacion.py                      # partición test
    python3 linea_base_recuperacion.py --particion val
    python3 linea_base_recuperacion.py --revision <sha>     # fija la versión del modelo en Hugging Face

Salida: `predicciones/<particion>.jsonl` (formato común de predicciones,
ver README) y `<particion>.meta.json` con el modelo, su versión y los parámetros usados.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET = HERE.parents[2] / "dataset"
MODELO = "xthor/Qwen3-Embedding-0.6B-GraphQL"
NOMBRE = "linea-base-recuperacion"


def leer(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf8").splitlines() if l.strip()]


def resolver_revision(revision: str | None) -> str | None:
    """Devuelve el *commit* del modelo en Hugging Face (RNF-02); None si no hay conexión."""
    if revision:
        return revision
    try:
        from huggingface_hub import model_info
        return model_info(MODELO).sha
    except Exception as e:  # sin red: se usa la copia local y se avisa
        print(f"aviso: no se pudo resolver la revisión de {MODELO} ({e}); se usa la copia local")
        return None


def dispositivo(pedido: str) -> str:
    if pedido != "auto":
        return pedido
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--particion", default="test", choices=["test", "val"],
                    help="partición evaluada (reservado no tiene pares de entrenamiento de su esquema)")
    ap.add_argument("--revision", help="commit del modelo en Hugging Face; por defecto, el último")
    ap.add_argument("--prompt", default="query", choices=["query", "document"],
                    help="prompt de Qwen3-Embedding con el que se codifican las preguntas de entrenamiento; "
                         "las de prueba usan siempre 'query' (comparación simétrica pregunta-pregunta)")
    ap.add_argument("--dispositivo", default="auto", help="auto, cpu, cuda o mps")
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--salida", type=Path, default=HERE / "predicciones")
    args = ap.parse_args()

    import numpy as np
    import sentence_transformers
    from sentence_transformers import SentenceTransformer

    train = leer(DATASET / "train.jsonl")
    evaluar = leer(DATASET / f"{args.particion}.jsonl")
    revision = resolver_revision(args.revision)
    dev = dispositivo(args.dispositivo)

    t0 = time.perf_counter()
    modelo = SentenceTransformer(MODELO, revision=revision, device=dev)
    ms_carga = round((time.perf_counter() - t0) * 1000)

    # Índice por conjunto de datos: solo se recupera dentro del conjunto que eligió el usuario.
    por_conjunto: dict[str, list[dict]] = defaultdict(list)
    for e in train:
        por_conjunto[e["dataset"]].append(e)
    t0 = time.perf_counter()
    indice = {}
    for ds, pares in por_conjunto.items():
        emb = modelo.encode([p["pregunta"] for p in pares], prompt_name=args.prompt, batch_size=args.lote,
                            normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        indice[ds] = (pares, emb)
    ms_indice = round((time.perf_counter() - t0) * 1000)

    args.salida.mkdir(parents=True, exist_ok=True)
    out = args.salida / f"{args.particion}.jsonl"
    sin_indice = 0
    with open(out, "w", encoding="utf8") as fh:
        for e in evaluar:
            if e["dataset"] not in indice:
                sin_indice += 1
                pred = {"id": e["id"], "dataset": e["dataset"], "graphql": None, "ms": None,
                        "modelo": NOMBRE, "error": "sin pares de entrenamiento del conjunto"}
            else:
                pares, emb = indice[e["dataset"]]
                # El tiempo de inferencia incluye codificar la pregunta y buscar el vecino.
                t = time.perf_counter()
                q = modelo.encode([e["pregunta"]], prompt_name="query", normalize_embeddings=True,
                                  convert_to_numpy=True, show_progress_bar=False)[0]
                sims = emb @ q
                k = int(np.argmax(sims))
                ms = round((time.perf_counter() - t) * 1000, 1)
                v = pares[k]
                pred = {"id": e["id"], "dataset": e["dataset"], "graphql": v["graphql"], "ms": ms,
                        "modelo": NOMBRE, "vecino_id": v["id"], "vecino_pregunta": v["pregunta"],
                        "vecino_categoria": v["categoria"], "similitud": round(float(sims[k]), 4)}
            fh.write(json.dumps(pred, ensure_ascii=False) + "\n")

    meta = {
        "modelo": MODELO, "revision": revision, "entrenamiento_adicional": False,
        "metodo": "vecino más cercano por similitud de coseno dentro del mismo conjunto de datos",
        "particion": args.particion, "pares_evaluados": len(evaluar), "pares_indice": len(train),
        "sin_indice": sin_indice, "prompt_entrenamiento": args.prompt, "prompt_pregunta": "query",
        "dispositivo": dev, "ms_carga_modelo": ms_carga, "ms_indexado": ms_indice,
        "sentence_transformers": sentence_transformers.__version__, "python": platform.python_version(),
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (args.salida / f"{args.particion}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                                            encoding="utf8")
    iguales = sum(1 for l in out.read_text(encoding="utf8").splitlines()
                  if (p := json.loads(l)).get("vecino_categoria") is not None
                  and p["vecino_categoria"] == next(x["categoria"] for x in evaluar if x["id"] == p["id"]))
    print(f"{len(evaluar)} predicciones en {out} ({sin_indice} sin índice); "
          f"vecino de la misma categoría: {iguales}/{len(evaluar) - sin_indice}")


if __name__ == "__main__":
    main()
