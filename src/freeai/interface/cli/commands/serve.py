import typer
import uvicorn

from freeai.api.server import create_app
from freeai.core import get_settings

app = typer.Typer(help="Inicia o servidor FastAPI Gateway.")


@app.command(name="serve")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host de escuta do Gateway"),
    port: int = typer.Option(0, "--port", "-p", help="Porta HTTP do Gateway (padrão das configurações)"),
    reload: bool = typer.Option(False, "--reload", help="Ativar auto-reload"),
) -> None:
    """Inicia o servidor FastAPI Gateway em modo headless (em primeiro plano)."""
    settings = get_settings()
    final_port = port if port > 0 else settings.PORT
    final_host = host or settings.HOST

    typer.secho(
        f"🚀 Iniciando FreeAI Gateway em http://{final_host}:{final_port}/v1 ...", fg=typer.colors.CYAN, bold=True
    )
    uvicorn.run(create_app(), host=final_host, port=final_port, reload=reload)
