from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from litellm import Router

from freeai.gateway.routes import router as v1_router
from freeai.router import build_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação FastAPI, inicializando o litellm.Router se necessário."""
    if not hasattr(app.state, "router") or app.state.router is None:
        app.state.router = build_router()
    yield


def create_app(router_instance: Router | None = None) -> FastAPI:
    """Instancia e configura a aplicação FastAPI para o Gateway FreeAI.

    Args:
        router_instance: Instância opcional do litellm.Router para injeção de dependência/testes.

    Returns:
        FastAPI: Aplicação configurada com rotas e middleware de autenticação.
    """
    app = FastAPI(
        title="FreeAI API Gateway",
        description="Gateway de IA inteligente compatível com a especificação da OpenAI",
        version="0.1.0",
        lifespan=lifespan,
    )

    if router_instance:
        app.state.router = router_instance

    app.include_router(v1_router)

    return app
