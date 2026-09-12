from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from freeai.api.v1.routes import router as v1_router
from freeai.core import build_router_catalog, get_settings
from freeai.services import Router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação FastAPI, inicializando o Router de roteamento."""
    if not hasattr(app.state, "router") or app.state.router is None:
        settings = get_settings()
        catalog = build_router_catalog(settings)
        app.state.router = Router(
            catalog=catalog,
            minute_cooldown_seconds=settings.router_settings.minute_cooldown_seconds,
            daily_cooldown_seconds=settings.router_settings.daily_cooldown_seconds,
            num_retries=settings.router_settings.num_retries,
        )
    yield


def create_app(router_instance: Router | None = None) -> FastAPI:
    """Instancia e configura a aplicação FastAPI para o Gateway FreeAI."""
    app = FastAPI(
        title="FreeAI API Gateway",
        description="Gateway de IA inteligente compatível com a especificação da OpenAI",
        version="1.0.0",
        lifespan=lifespan,
    )

    if router_instance:
        app.state.router = router_instance

    app.include_router(v1_router)
    return app
