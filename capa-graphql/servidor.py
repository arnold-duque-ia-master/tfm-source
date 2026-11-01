"""Servidor HTTP de la capa GraphQL (paso 6).

Rutas:
  POST /graphql            {"query": "..."} -> respuesta GraphQL estándar (+ extensions con la SoQL)
  GET  /graphql            GraphiQL, para explorar el esquema y probar consultas
  GET  /conjuntos          conjuntos disponibles (id, alias, descripción)
  GET  /esquema/{id}       SDL compacto del conjunto (el que recibe el modelo)
  GET  /salud              comprobación de estado

Uso:
  python3 servidor.py [--puerto 8000] [--offline]
"""
from __future__ import annotations

import argparse

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route

from servicio import Servicio
from soda_cliente import SodaCliente

GRAPHIQL = """<!doctype html><html><head><meta charset="utf-8"><title>datos.gov.co · GraphQL</title>
<link rel="stylesheet" href="https://unpkg.com/graphiql@3/graphiql.min.css"/></head>
<body style="margin:0"><div id="g" style="height:100vh"></div>
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script crossorigin src="https://unpkg.com/graphiql@3/graphiql.min.js"></script>
<script>
ReactDOM.createRoot(document.getElementById('g')).render(React.createElement(GraphiQL, {
  fetcher: GraphiQL.createFetcher({ url: '/graphql' }),
  defaultQuery: '{ vacunacionAftosaVichadaAggregate(orderBy: [{sum: {totalAftosa: DESC}}]) { municipio sum { totalAftosa } } }'
}));
</script></body></html>"""


def crear_app(servicio: Servicio) -> Starlette:
    async def graphql_post(request: Request):
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({"errors": [{"message": "Cuerpo JSON no válido"}]}, status_code=400)
        q = body.get("query") if isinstance(body, dict) else None
        if not q:
            return JSONResponse({"errors": [{"message": "Falta el campo query"}]}, status_code=400)
        return JSONResponse(servicio.ejecutar(q))

    async def graphiql(_):
        return HTMLResponse(GRAPHIQL)

    async def conjuntos(_):
        return JSONResponse(servicio.conjuntos())

    async def esquema(request: Request):
        sdl = servicio.esquema_prompt(request.path_params["ds"])
        return PlainTextResponse(sdl) if sdl else PlainTextResponse("Conjunto desconocido", status_code=404)

    async def salud(_):
        return JSONResponse({"estado": "ok", "offline": servicio.cliente.offline})

    return Starlette(routes=[
        Route("/graphql", graphql_post, methods=["POST"]),
        Route("/graphql", graphiql, methods=["GET"]),
        Route("/conjuntos", conjuntos),
        Route("/esquema/{ds}", esquema),
        Route("/salud", salud),
    ])


if __name__ == "__main__":
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--offline", action="store_true", help="responder solo desde la caché")
    a = ap.parse_args()
    uvicorn.run(crear_app(Servicio(cliente=SodaCliente(offline=a.offline))), host=a.host, port=a.puerto)
