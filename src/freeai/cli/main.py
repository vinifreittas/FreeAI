import os
from pathlib import Path

import typer
import uvicorn
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from freeai.config import get_all_provider_keys, get_settings

app = typer.Typer(
    name="freeai",
    help="FreeAI — Gateway de Inteligência Artificial com Roteamento Inteligente e Fallbacks",
    add_completion=False,
)

console = Console()


@app.command()
def start(
    host: str | None = typer.Option(None, "--host", "-h", help="Endereço IP para vincular o servidor"),
    port: int | None = typer.Option(None, "--port", "-p", help="Porta para o servidor HTTP"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Habilitar auto-reload para desenvolvimento"),
) -> None:
    """Inicia o servidor API Gateway FreeAI."""
    settings = get_settings()
    server_host = host or settings.HOST
    server_port = port or settings.PORT

    console.print(
        Panel(
            f"[bold green]Servidor FreeAI Gateway em execução[/bold green]\n"
            f"[cyan]URL:[/cyan] http://{server_host}:{server_port}\n"
            f"[cyan]Docs:[/cyan] http://{server_host}:{server_port}/docs",
            title="[bold blue]FreeAI Gateway[/bold blue]",
        )
    )

    uvicorn.run(
        "freeai.gateway.server:create_app",
        factory=True,
        host=server_host,
        port=server_port,
        reload=reload,
    )


@app.command()
def models(
    config_path: Path | None = typer.Option(
        None, "--config", "-c", help="Caminho para arquivo YAML de modelos alternativo"
    ),
) -> None:
    """Lista os aliases de modelos configurados e os respectivos modelos backend."""
    settings = get_settings()
    target_path = config_path or settings.MODELS_CONFIG_PATH

    if not target_path.exists():
        console.print(f"[bold red]Arquivo de modelos não encontrado em {target_path}[/bold red]")
        raise typer.Exit(code=1)

    with open(target_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    model_list = raw_config.get("model_list", [])

    table = Table(title="Modelos & Aliases Configurados", show_header=True, header_style="bold magenta")
    table.add_column("Alias", style="bold cyan", width=12)
    table.add_column("Modelo Backend (LiteLLM)", style="green")

    for item in model_list:
        alias = item.get("model_name", "N/A")
        litellm_model = item.get("litellm_params", {}).get("model", "N/A")
        table.add_row(alias, litellm_model)

    console.print(table)


@app.command()
def status() -> None:
    """Exibe o status atual das configurações do Gateway e chaves de API dos provedores."""
    settings = get_settings()
    provider_keys = get_all_provider_keys()

    table = Table(title="Status do FreeAI Gateway", show_header=True, header_style="bold cyan")
    table.add_column("Configuração", style="bold yellow")
    table.add_column("Valor / Status")

    table.add_row("Endereço Padrão", f"{settings.HOST}:{settings.PORT}")
    table.add_row(
        "FreeAI Bearer Token", "[green]Configurado[/green]" if settings.FREEAI_API_KEY else "[red]Não configurado[/red]"
    )
    table.add_row("Chaves Detectadas", f"{len(provider_keys)} chave(s) no .env/ambiente")
    table.add_row("Arquivo de Modelos", str(settings.MODELS_CONFIG_PATH))

    console.print(table)


@app.command()
def check(
    alias: str | None = typer.Option(None, "--alias", "-a", help="Filtrar verificação por um alias específico"),
    config_path: Path | None = typer.Option(
        None, "--config", "-c", help="Caminho para arquivo YAML de modelos alternativo"
    ),
) -> None:
    """Executa diagnóstico de saúde e verificação de chaves dos modelos configurados."""
    settings = get_settings()
    target_path = config_path or settings.MODELS_CONFIG_PATH

    if not target_path.exists():
        console.print(f"[bold red]Arquivo de modelos não encontrado em {target_path}[/bold red]")
        raise typer.Exit(code=1)

    with open(target_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    model_list = raw_config.get("model_list", [])
    provider_keys = get_all_provider_keys()

    table = Table(
        title="Diagnóstico de Saúde & Disponibilidade de Provedores", show_header=True, header_style="bold cyan"
    )
    table.add_column("Alias", style="bold magenta", width=12)
    table.add_column("Modelo Backend", style="green")
    table.add_column("Provedor", style="yellow")
    table.add_column("Chave Esperada", style="blue")
    table.add_column("Status da Chave", style="bold")

    for item in model_list:
        item_alias = item.get("model_name", "N/A")
        if alias and item_alias != alias:
            continue

        litellm_model = item.get("litellm_params", {}).get("model", "N/A")
        provider = litellm_model.split("/")[0] if "/" in litellm_model else "litellm"

        expected_key = f"{provider.upper()}_API_KEY"
        if provider.lower() == "openrouter":
            expected_key = "OPENROUTER_API_KEY"

        has_key = (
            expected_key in provider_keys
            or expected_key in os.environ
            or f"{provider.upper()}_KEY" in provider_keys
            or f"{provider.upper()}_KEY" in os.environ
        )
        status_str = (
            "[green]Pronto / Chave Presente[/green]" if has_key else "[yellow]Ausente / Chave Não Detectada[/yellow]"
        )

        table.add_row(item_alias, litellm_model, provider, expected_key, status_str)

    console.print(table)


def main() -> None:
    """Ponto de entrada principal da CLI."""
    app()


if __name__ == "__main__":
    main()
