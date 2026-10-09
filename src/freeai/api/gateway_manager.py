import threading
import time
from typing import Any

import uvicorn

from freeai.api.server import create_app
from freeai.core import get_settings, reload_settings

_server: uvicorn.Server | None = None
_thread: threading.Thread | None = None
_app: Any = None
_host: str = "0.0.0.0"
_port: int = 4000


def is_gateway_running() -> bool:
    """Checks if FastAPI Gateway server is running in background."""
    return _thread is not None and _thread.is_alive() and _server is not None and getattr(_server, "started", False)


def start_gateway(host: str | None = None, port: int | None = None) -> bool:
    """Starts FastAPI Gateway server in a background daemon thread."""
    global _server, _thread, _app, _host, _port
    if is_gateway_running():
        return True

    settings = get_settings()
    _host = host or settings.HOST
    _port = port or settings.PORT

    _app = create_app()
    config = uvicorn.Config(app=_app, host=_host, port=_port, log_level="warning")
    _server = uvicorn.Server(config=config)

    def _run() -> None:
        if _server:
            _server.run()

    _thread = threading.Thread(target=_run, daemon=True, name="FreeAIGatewayThread")
    _thread.start()

    for _ in range(25):
        if getattr(_server, "started", False):
            break
        time.sleep(0.04)

    return is_gateway_running()


def stop_gateway() -> bool:
    """Stops background FastAPI Gateway server."""
    global _server, _thread, _app
    if _server:
        _server.should_exit = True
    if _thread and _thread.is_alive():
        _thread.join(timeout=1.5)
    _server = None
    _thread = None
    _app = None
    return True


def restart_gateway(host: str | None = None, port: int | None = None) -> bool:
    """Restarts server applying updated vault settings."""
    stop_gateway()
    reload_settings()
    return start_gateway(host=host, port=port)


def get_gateway_info() -> dict[str, Any]:
    """Returns Gateway status information."""
    running = is_gateway_running()
    display_host = "localhost" if _host in ("0.0.0.0", "127.0.0.1") else _host
    return {
        "running": running,
        "host": _host,
        "port": _port,
        "url": f"http://{display_host}:{_port}",
        "docs_url": f"http://{display_host}:{_port}/docs",
    }


def get_gateway_router() -> Any:
    """Returns active Router instance configured on running FastAPI app."""
    return getattr(_app.state, "router", None) if _app and hasattr(_app, "state") else None


def clear_gateway_cooldowns() -> bool:
    """Resets all cooldowns and disabled models/providers on active Router."""
    router = get_gateway_router()
    if router and hasattr(router, "reset_cooldowns"):
        router.reset_cooldowns()
        return True
    return False


def reload_gateway_catalog() -> bool:
    """Reloads active Gateway router catalog based on current settings."""
    router = get_gateway_router()
    if router:
        from freeai.core import build_router_catalog

        router.catalog = build_router_catalog(reload_settings())
        return True
    return False
