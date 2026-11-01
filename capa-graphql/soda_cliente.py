"""Cliente de SODA3 con caché en disco (paso 6).

- Credenciales: SOCRATA_KEY_ID + SOCRATA_KEY_SECRET (API Key, autenticación básica) o SOCRATA_APP_TOKEN,
  tomadas del entorno o de un archivo .env (por defecto ../spike-soda3/.env). Nunca se registran.
- Caché SQLite en ~/.cache/tfm-graphql/soda.sqlite (variable SODA_CACHE): clave = conjunto + SoQL + tamaño de página. Modo offline: solo responde desde la caché
  (respaldo para la demostración y para validar el dataset de forma reproducible).
- Errores traducidos a los códigos de CONVENCIONES.md (apartado 8).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from traductor import TranslationError

BASE = "https://www.datos.gov.co"
HERE = Path(__file__).resolve().parent
# Fuera del repositorio: la carpeta del proyecto se sincroniza en la nube y SQLite no debe vivir ahí.
CACHE_POR_DEFECTO = Path(os.environ.get("SODA_CACHE", Path.home() / ".cache" / "tfm-graphql" / "soda.sqlite"))


def leer_credenciales(env_file: Path | None = None) -> dict:
    vals = {}
    env_file = env_file or Path(os.environ.get("SODA_ENV_FILE", HERE.parent / "spike-soda3" / ".env"))
    if env_file.exists():
        for line in env_file.read_text(encoding="utf8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip("\"'")
    for k in ("SOCRATA_APP_TOKEN", "SOCRATA_KEY_ID", "SOCRATA_KEY_SECRET"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    return {k: v for k, v in vals.items() if v}


@dataclass
class Resultado:
    rows: list
    ms: int
    cache: bool


class SodaCliente:
    def __init__(self, cache_path: Path | str | None = CACHE_POR_DEFECTO, ttl_s: int = 7 * 24 * 3600,
                 offline: bool = False, timeout_s: float = 60.0, credenciales: dict | None = None):
        self.ttl_s, self.offline = ttl_s, offline
        cred = credenciales if credenciales is not None else leer_credenciales()
        self.headers = {"Accept": "application/json"}
        self.auth = None
        if cred.get("SOCRATA_KEY_ID") and cred.get("SOCRATA_KEY_SECRET"):
            self.auth = (cred["SOCRATA_KEY_ID"], cred["SOCRATA_KEY_SECRET"])
        elif cred.get("SOCRATA_APP_TOKEN"):
            self.headers["X-App-Token"] = cred["SOCRATA_APP_TOKEN"]
        self.http = httpx.Client(timeout=timeout_s, headers=self.headers, auth=self.auth)
        self.db = None
        if cache_path:
            Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(str(cache_path), check_same_thread=False)
            self.db.execute("PRAGMA journal_mode=MEMORY")   # sin archivos auxiliares que haya que borrar
            self.db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, dataset TEXT, soql TEXT, "
                            "page_size INT, rows TEXT, ts REAL)")
            self.lock = threading.Lock()

    @staticmethod
    def _key(dataset, soql, page_size):
        return hashlib.sha256(f"{dataset}\n{soql}\n{page_size}".encode()).hexdigest()

    def _get_cache(self, k):
        if not self.db:
            return None
        with self.lock:
            r = self.db.execute("SELECT rows, ts FROM cache WHERE k = ?", (k,)).fetchone()
        if r and (self.offline or time.time() - r[1] < self.ttl_s):
            return json.loads(r[0])
        return None

    def _put_cache(self, k, dataset, soql, page_size, rows):
        if not self.db:
            return
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?, ?, ?)",
                            (k, dataset, soql, page_size, json.dumps(rows, ensure_ascii=False), time.time()))
            self.db.commit()

    def consultar(self, dataset: str, soql: str, page_size: int) -> Resultado:
        k = self._key(dataset, soql, page_size)
        t0 = time.perf_counter()
        hit = self._get_cache(k)
        if hit is not None:
            return Resultado(hit, round((time.perf_counter() - t0) * 1000), True)
        if self.offline:
            raise TranslationError("UPSTREAM_UNAVAILABLE", "Modo offline: la consulta no está en la caché")
        body = {"query": soql, "page": {"pageNumber": 1, "pageSize": page_size}, "includeSynthetic": False}
        url = f"{BASE}/api/v3/views/{dataset}/query.json"
        r = None
        for intento in range(2):                      # un reintento ante caída o error 5xx
            try:
                r = self.http.post(url, json=body)
            except httpx.HTTPError as e:
                if intento:
                    raise TranslationError("UPSTREAM_UNAVAILABLE", f"No se pudo contactar con datos.gov.co: {type(e).__name__}")
                time.sleep(1)
                continue
            if r.status_code < 500:
                break
            time.sleep(1)
        ms = round((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            rows = r.json()
            self._put_cache(k, dataset, soql, page_size, rows)
            return Resultado(rows, ms, False)
        try:
            p = r.json()
        except ValueError:
            p = {"message": r.text[:300]}
        if r.status_code in (401, 403):
            raise TranslationError("UPSTREAM_AUTH", "datos.gov.co rechazó las credenciales", {"soqlCode": p.get("code")})
        if r.status_code == 400:
            msg = (p.get("data") or {}).get("message") or p.get("message") or "Error de SoQL"
            raise TranslationError("SOQL_ERROR", f"datos.gov.co rechazó la consulta: {msg}",
                                   {"soqlCode": p.get("code"), "soql": soql})
        raise TranslationError("UPSTREAM_UNAVAILABLE", f"datos.gov.co respondió HTTP {r.status_code}")
