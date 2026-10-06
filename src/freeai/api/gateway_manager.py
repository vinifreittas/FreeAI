import threading
import time
from typing import Any

import uvicorn

from freeai.api.server import create_app
from freeai.core import get_settings, reload_settings

_server: uvicorn.Server | None = None
_thread: threading.Thread | None = None
_host: str = "0.0.0.0"
_port: int = 4000


def is_gateway_running() -> bool:
    """Verifica se o servidor FastAPI Gateway está ativo em segundo plano."""
    return _thread is not None and _thread.is_alive() and _server is not None and getattr(_server, "started", False)


def start_gateway(host: str | None = None, port: int | None = None) -> bool:
    """Inicia o servidor FastAPI Gateway em uma thread daemon em segundo plano."""
    global _server, _thread, _host, _port
    if is_gateway_running():
        return True

    settings = get_settings()
    _host = host or settings.HOST
    _port = port or settings.PORT

    app = create_app()
    config = uvicorn.Config(app=app, host=_host, port=_port, log_level="warning")
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
    """Para o servidor FastAPI Gateway em segundo plano."""
    global _server, _thread
    if _server:
        _server.should_exit = True
    if _thread and _thread.is_alive():
        _thread.join(timeout=1.5)
    _server = None
    _thread = None
    return True


def restart_gateway(host: str | None = None, port: int | None = None) -> bool:
    """Reinicia o servidor aplicando as novas configurações do vault."""
    stop_gateway()
    reload_settings()
    return start_gateway(host=host, port=port)


def get_gateway_info() -> dict[str, Any]:
    """Retorna informações de status do Gateway."""
    running = is_gateway_running()
    display_host = "localhost" if _host in ("0.0.0.0", "127.0.0.1") else _host
    return {
        "running": running,
        "host": _host,
        "port": _port,
        "url": f"http://{display_host}:{_port}",
        "docs_url": f"http://{display_host}:{_port}/docs",
    }
