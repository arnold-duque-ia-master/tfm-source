"""Prueba de McNemar entre dos modelos evaluados sobre las mismas preguntas (McNemar, 1947).

Compara la métrica elegida (por defecto, la exactitud de ejecución) de dos archivos de resultados
de `evaluar.py`. Usa la prueba exacta (binomial bilateral sobre los pares discordantes), adecuada
cuando hay pocos discordantes, e informa también del estadístico chi-cuadrado con corrección de
continuidad.

Uso:
    python3 mcnemar.py resultados/qwen-qlora/test.jsonl resultados/linea-base-recuperacion/test.jsonl
    python3 mcnemar.py A.jsonl B.jsonl --metrica valida_esquema --alfa 0.05
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def leer(p: Path) -> dict[str, dict]:
    return {r["id"]: r for r in (json.loads(l) for l in p.read_text(encoding="utf8").splitlines() if l.strip())}


def mcnemar_exacta(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cola = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * cola)


def chi2_corregido(b: int, c: int) -> tuple[float, float]:
    """Estadístico con corrección de continuidad y su p-valor (chi-cuadrado, 1 grado de libertad)."""
    if b + c == 0:
        return 0.0, 1.0
    x = (abs(b - c) - 1) ** 2 / (b + c)
    return x, math.erfc(math.sqrt(x / 2))


def comparar(a: dict[str, dict], b: dict[str, dict], metrica: str) -> dict:
    ids = sorted(set(a) & set(b))
    if set(a) != set(b):
        raise SystemExit(f"los archivos no tienen las mismas preguntas ({len(set(a) ^ set(b))} distintas)")
    n11 = sum(a[i][metrica] and b[i][metrica] for i in ids)
    n10 = sum(a[i][metrica] and not b[i][metrica] for i in ids)
    n01 = sum(not a[i][metrica] and b[i][metrica] for i in ids)
    n00 = len(ids) - n11 - n10 - n01
    x2, p_x2 = chi2_corregido(n10, n01)
    return {"metrica": metrica, "n": len(ids), "aciertos_a": n11 + n10, "aciertos_b": n11 + n01,
            "tasa_a": round((n11 + n10) / len(ids), 4), "tasa_b": round((n11 + n01) / len(ids), 4),
            "ambos": n11, "solo_a": n10, "solo_b": n01, "ninguno": n00,
            "p_exacta": mcnemar_exacta(n10, n01), "chi2_corregido": round(x2, 4), "p_chi2": p_x2}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("a", type=Path, help="resultados del modelo A (evaluar.py)")
    ap.add_argument("b", type=Path, help="resultados del modelo B (evaluar.py)")
    ap.add_argument("--metrica", default="exactitud_ejecucion")
    ap.add_argument("--alfa", type=float, default=0.05)
    args = ap.parse_args()
    r = comparar(leer(args.a), leer(args.b), args.metrica)
    r.update(a=str(args.a), b=str(args.b), alfa=args.alfa, significativa=r["p_exacta"] < args.alfa)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
