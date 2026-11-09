"""Línea base: Granite-8B-Code-Instruct sin ajustar, con un ejemplo en contexto (OE4).

El modelo se usa tal como se publica, sin ningún entrenamiento adicional. Recibe la misma instrucción en
español que los modelos ajustados (`instruccion.py`), precedida de un ejemplo en contexto: un par de
`train.jsonl` del mismo conjunto de datos, elegido con una semilla fija y común a todas sus preguntas.
Como no está ajustado, la instrucción incluye además los tipos comunes del esquema (filtros, orden y
escalares), que los modelos ajustados aprenden en el entrenamiento (`--sin-comunes` los quita).

Si la instrucción con el ejemplo no cabe en la ventana de 4.096 tokens del modelo (dejando sitio para
la respuesta), se usa el ejemplo más corto del conjunto; si aun así no cabe, la pregunta se registra
como fallo (`error: "excede la ventana de contexto"`).

El conjunto reservado (`ni93-8mm5`) no tiene pares de entrenamiento de los que tomar el ejemplo, así que
la línea base solo se aplica a `test.jsonl` (o a `val.jsonl`).

Uso (desde esta carpeta, con las dependencias de `requirements.txt`):
    python3 linea_base_granite.py --tokens        # solo mide la longitud de las instrucciones (sin GPU)
    python3 linea_base_granite.py                 # genera las predicciones de test (4 bits en CUDA)
    python3 linea_base_granite.py --limite 10     # prueba rápida con 10 preguntas
    python3 linea_base_granite.py --cuantizacion ninguna --dispositivo mps    # MacBook (bf16, ~16 GB)

Salida: `predicciones/granite-8b/<particion>.jsonl` (formato común, ver README) y `<particion>.meta.json`.
Después: `python3 evaluar.py predicciones/granite-8b/test.jsonl`.
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from instruccion import SISTEMA, extraer_consulta, mensajes

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent / "dataset"
MODELO = "ibm-granite/granite-8b-code-instruct-4k"
NOMBRE = "granite-8b"
SEMILLA = 20261108
VENTANA = 4096


def leer(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf8").splitlines() if l.strip()]


def resolver_revision(modelo: str, revision: str | None) -> str | None:
    if revision:
        return revision
    try:
        from huggingface_hub import model_info
        return model_info(modelo).sha
    except Exception as e:
        print(f"aviso: no se pudo resolver la revisión de {modelo} ({e}); se usa la copia local")
        return None


def ejemplos_por_conjunto(train: list[dict]) -> dict[str, dict]:
    """Un ejemplo fijo por conjunto: elegido con semilla entre sus pares de entrenamiento, ordenados por id."""
    por = defaultdict(list)
    for e in train:
        por[e["dataset"]].append(e)
    rng = random.Random(SEMILLA)
    return {ds: rng.choice(sorted(pares, key=lambda e: e["id"])) for ds, pares in sorted(por.items())}


def mas_corto(pares: list[dict]) -> dict:
    return min(pares, key=lambda e: (len(e["pregunta"]) + len(e["graphql"]), e["id"]))


def cargar_modelo(args, revision):
    import torch
    from transformers import AutoModelForCausalLM

    dev = args.dispositivo
    if dev == "auto":
        dev = "cuda" if torch.cuda.is_available() else (
            "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
    kw = {"revision": revision}
    if args.cuantizacion == "4bit":
        if dev != "cuda":
            raise SystemExit("la cuantización en 4 bits (bitsandbytes) necesita CUDA; usa --cuantizacion ninguna")
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True)
        kw["device_map"] = {"": 0}
    else:
        kw["dtype"] = torch.bfloat16 if dev in ("cuda", "mps") else torch.float32
    modelo = AutoModelForCausalLM.from_pretrained(args.modelo, **kw)
    if args.cuantizacion != "4bit":
        modelo.to(dev)
    modelo.eval()
    return modelo, dev


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--particion", default="test", choices=["test", "val"])
    ap.add_argument("--modelo", default=MODELO, help="identificador en Hugging Face (otro modelo solo para pruebas)")
    ap.add_argument("--revision", help="commit del modelo en Hugging Face; por defecto, el último")
    ap.add_argument("--cuantizacion", default="4bit", choices=["4bit", "ninguna"])
    ap.add_argument("--dispositivo", default="auto", help="auto, cuda, mps o cpu")
    ap.add_argument("--max-nuevos", type=int, default=256, help="tokens máximos de la respuesta")
    ap.add_argument("--sin-comunes", action="store_true", help="no incluir los tipos comunes en la instrucción")
    ap.add_argument("--tokens", action="store_true", help="solo medir la longitud de las instrucciones")
    ap.add_argument("--limite", type=int, help="evaluar solo las primeras N preguntas (prueba rápida)")
    ap.add_argument("--salida", type=Path, help="carpeta de salida; por defecto predicciones/granite-8b")
    args = ap.parse_args()

    from transformers import AutoTokenizer
    import transformers

    con_comunes = not args.sin_comunes
    train = leer(DATASET / "train.jsonl")
    evaluar = leer(DATASET / f"{args.particion}.jsonl")
    if args.limite:
        evaluar = evaluar[:args.limite]
    revision = resolver_revision(args.modelo, args.revision)
    tok = AutoTokenizer.from_pretrained(args.modelo, revision=revision)
    presupuesto = VENTANA - args.max_nuevos

    por_conjunto = defaultdict(list)
    for e in train:
        por_conjunto[e["dataset"]].append(e)
    fijos = ejemplos_por_conjunto(train)

    def instruccion(e):
        """(ids de la instrucción, ejemplo usado, si se usó el corto) o (None, …) si no cabe."""
        if e["dataset"] not in fijos:
            return None, None, False, "sin pares de entrenamiento del conjunto"
        for ej, corto in ((fijos[e["dataset"]], False), (mas_corto(por_conjunto[e["dataset"]]), True)):
            ids = tok.apply_chat_template(mensajes(e["pregunta"], e["dataset"], ej, con_comunes),
                                          add_generation_prompt=True, return_tensors=None)
            if hasattr(ids, "keys"):  # algunas versiones devuelven un BatchEncoding
                ids = ids["input_ids"]
            if len(ids) <= presupuesto:
                return ids, ej, corto, None
        return None, ej, True, "excede la ventana de contexto"

    if args.tokens:
        longitudes = defaultdict(list)
        cortos = fallos = 0
        for e in evaluar:
            ids, _, corto, err = instruccion(e)
            cortos += corto and not err
            fallos += bool(err)
            if ids is not None:
                longitudes[e["dataset"]].append(len(ids))
        print(f"modelo {args.modelo}; ventana {VENTANA}, respuesta {args.max_nuevos}, presupuesto {presupuesto} tokens; "
              f"tipos comunes: {'sí' if con_comunes else 'no'}")
        for ds, xs in sorted(longitudes.items()):
            print(f"  {ds}: n={len(xs)}  mediana={statistics.median(xs):.0f}  max={max(xs)}")
        resp = [len(tok(e["graphql"])["input_ids"]) for e in evaluar]
        print(f"respuesta de referencia: mediana={statistics.median(resp):.0f}  max={max(resp)} tokens")
        print(f"ejemplo corto usado en {cortos}; no caben {fallos} de {len(evaluar)}")
        return

    import torch
    modelo, dev = cargar_modelo(args, revision)
    salida = args.salida or HERE / "predicciones" / NOMBRE
    salida.mkdir(parents=True, exist_ok=True)
    out = salida / f"{args.particion}.jsonl"
    t_ini = time.perf_counter()
    with open(out, "w", encoding="utf8") as fh:
        for i, e in enumerate(evaluar, 1):
            ids, ej, corto, err = instruccion(e)
            pred = {"id": e["id"], "dataset": e["dataset"], "graphql": None, "ms": None, "modelo": NOMBRE}
            if err:
                pred["error"] = err
            else:
                x = torch.tensor([ids], device=modelo.device)
                t = time.perf_counter()
                with torch.no_grad():
                    y = modelo.generate(x, attention_mask=torch.ones_like(x), max_new_tokens=args.max_nuevos,
                                        do_sample=False, pad_token_id=tok.pad_token_id or tok.eos_token_id)
                ms = round((time.perf_counter() - t) * 1000, 1)
                texto = tok.decode(y[0, x.shape[1]:], skip_special_tokens=True)
                pred.update(graphql=extraer_consulta(texto), ms=ms, respuesta=texto,
                            ejemplo_id=ej["id"], ejemplo_corto=corto, tokens_instruccion=len(ids))
            fh.write(json.dumps(pred, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 10 == 0:
                print(f"{i}/{len(evaluar)}", flush=True)

    meta = {
        "modelo": args.modelo, "revision": revision, "entrenamiento_adicional": False,
        "metodo": "un ejemplo en contexto del mismo conjunto de datos (semilla fija), decodificación voraz",
        "semilla_ejemplo": SEMILLA, "ejemplos": {ds: e["id"] for ds, e in fijos.items()},
        "tipos_comunes": con_comunes, "instruccion_sistema": SISTEMA, "particion": args.particion,
        "pares_evaluados": len(evaluar), "cuantizacion": args.cuantizacion, "dispositivo": dev,
        "max_nuevos": args.max_nuevos, "ventana": VENTANA, "s_total": round(time.perf_counter() - t_ini),
        "transformers": transformers.__version__, "torch": torch.__version__, "python": platform.python_version(),
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (salida / f"{args.particion}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                                       encoding="utf8")
    print(f"{len(evaluar)} predicciones en {out}")


if __name__ == "__main__":
    main()
