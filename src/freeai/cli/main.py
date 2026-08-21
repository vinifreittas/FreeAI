import logging
from typing import Annotated

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from freeai.config import get_settings

app = typer.Typer(
    name="freeai",
    help="FreeAI — API Gateway & AI Routing CLI Engine",
    add_completion=False,
)

console = Console()

# Silence third-party loggers
logging.getLogger("litellm").propagate = False
logging.getLogger("litellm").disabled = True


@app.command()
def start(
    host: Annotated[str | None, typer.Option("--host", "-h", help="Endereço IP para vincular o servidor")] = None,
    port: Annotated[int | None, typer.Option("--port", "-p", help="Porta para o servidor HTTP")] = None,
    reload: Annotated[bool, typer.Option("--reload", "-r", help="Habilitar auto-reload para desenvolvimento")] = False,
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
def models() -> None:
    """Lista os aliases configurados, seus alvos e os modelos/provedores disponíveis."""
    settings = get_settings()

    # Tabela 1: Aliases de Rotas
    table_aliases = Table(title="Aliases de Rotas (Shortcuts)", show_header=True, header_style="bold magenta")
    table_aliases.add_column("Alias", style="bold cyan", width=16)
    table_aliases.add_column("Modelo Alvo (Target ID)", style="green")
    table_aliases.add_column("Provedor Backend", style="yellow")
    table_aliases.add_column("Descrição", style="dim")

    for alias in settings.aliases:
        _, provider, _ = settings.resolve_alias(alias.alias)
        provider_name = provider.display_name if provider else "Não Encontrado"
        table_aliases.add_row(alias.alias, alias.target_model_id, provider_name, alias.description or "-")

    console.print(table_aliases)
    console.print()

    # Tabela 2: Provedores e Modelos
    table_models = Table(title="Modelos Mapeados por Provedor", show_header=True, header_style="bold blue")
    table_models.add_column("Provedor", style="bold yellow")
    table_models.add_column("ID do Modelo", style="bold cyan")
    table_models.add_column("Modelo Remoto (API)", style="green")

    for provider in settings.providers:
        for model in provider.models:
            table_models.add_row(provider.display_name, model.id, model.remote_model)

    console.print(table_models)


@app.command()
def status() -> None:
    """Exibe o status atual do Gateway, configurações e detecção de chaves de API."""
    settings = get_settings()

    table = Table(title="Status do FreeAI Gateway", show_header=True, header_style="bold cyan")
    table.add_column("Configuração / Componente", style="bold yellow")
    table.add_column("Valor / Status")

    api_key_status = (
        "[green]Configurado[/green]" if settings.FREEAI_API_KEY else "[yellow]Não configurado (Acesso Aberto)[/yellow]"
    )

    table.add_row("Endereço Padrão", f"{settings.HOST}:{settings.PORT}")
    table.add_row("FreeAI Bearer Token", api_key_status)
    table.add_row("Arquivo de Configuração", str(settings.MODELS_CONFIG_PATH))
    table.add_row("Provedores Carregados", str(len(settings.providers)))
    table.add_row("Aliases Configurados", str(len(settings.aliases)))

    console.print(table)


@app.command()
def check(
    alias: Annotated[
        str | None, typer.Option("--alias", "-a", help="Filtrar diagnóstico por um alias específico")
    ] = None,
) -> None:
    """Diagnóstico de saúde das variáveis de ambiente e chaves de API dos provedores."""
    settings = get_settings()

    aliases_to_check = [a for a in settings.aliases if not alias or a.alias == alias]

    if alias and not aliases_to_check:
        console.print(f"[bold red]Alias '{alias}' não foi encontrado na configuração.[/bold red]")
        raise typer.Exit(code=1)

    table = Table(title="Diagnóstico de Disponibilidade de Provedores", show_header=True, header_style="bold cyan")
    table.add_column("Alias / Entrada", style="bold magenta", width=16)
    table.add_column("Modelo Alvo", style="green")
    table.add_column("Provedor", style="yellow")
    table.add_column("Variável de Ambiente", style="blue")
    table.add_column("Status da Chave", style="bold")

    for item in aliases_to_check:
        model, provider, _ = settings.resolve_alias(item.alias)

        if not provider or not model:
            table.add_row(
                item.alias,
                item.target_model_id,
                "[red]Desconhecido[/red]",
                "N/A",
                "[red]Erro: Modelo/Provedor não mapeado[/red]",
            )
            continue

        status_str = (
            "[green]Pronto / Chave Presente[/green]" if provider.api_key else "[red]Ausente / Chave Não Detectada[/red]"
        )

        table.add_row(item.alias, model.remote_model, provider.display_name, provider.api_key_env, status_str)

    console.print(table)


def main() -> None:
    """Ponto de entrada principal da CLI."""
    app()


if __name__ == "__main__":
    main()
