import asyncio
from typing import Annotated

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from freeai.core import build_router_catalog, get_settings
from freeai.services import Router

app = typer.Typer(
    name="freeai",
    help="FreeAI — API Gateway & AI Routing CLI Engine",
    add_completion=False,
)
console = Console()


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
            title="[bold blue]FreeAI Gateway v1.0.0[/bold blue]",
        )
    )

    uvicorn.run(
        "freeai.api.server:create_app",
        factory=True,
        host=server_host,
        port=server_port,
        reload=reload,
    )


@app.command()
def models() -> None:
    """Lista os aliases configurados, rotas ativas e mapeamento de modelos por provedor."""
    settings = get_settings()
    catalog = build_router_catalog(settings)

    # Tabela 1: Aliases e Rotas Resolvidas
    table_aliases = Table(title="Aliases de Rotas (Shortcuts)", show_header=True, header_style="bold magenta")
    table_aliases.add_column("Alias", style="bold cyan", width=16)
    table_aliases.add_column("Tipos Exigidos", style="green")
    table_aliases.add_column("Alvos Elegíveis (Fallback Chain)", style="yellow")
    table_aliases.add_column("Descrição", style="dim")

    for alias in settings.aliases:
        targets = catalog.get_targets(alias.alias)
        chain_str = " -> ".join(t.litellm_model for t in targets) if targets else "[red]Nenhum alvo ativo[/red]"
        types_str = ", ".join(alias.models_types_to_chain)
        table_aliases.add_row(alias.alias, types_str, chain_str, alias.description or "-")

    console.print(table_aliases)
    console.print()

    # Tabela 2: Provedores e Modelos Registrados
    table_models = Table(title="Modelos Mapeados no Catálogo", show_header=True, header_style="bold blue")
    table_models.add_column("Provedor", style="bold yellow")
    table_models.add_column("ID do Modelo", style="bold cyan")
    table_models.add_column("Modelo Remoto (API)", style="green")
    table_models.add_column("Tipos Declarados", style="magenta")

    for provider in settings.providers:
        for model in provider.models:
            types_str = ", ".join(model.types)
            table_models.add_row(provider.display_name, model.id, model.remote_model, types_str)

    console.print(table_models)


@app.command()
def status() -> None:
    """Exibe o status atual do Gateway, configurações e detecção de chaves de API."""
    settings = get_settings()
    catalog = build_router_catalog(settings)

    table = Table(title="Status do FreeAI Gateway v1.0.0", show_header=True, header_style="bold cyan")
    table.add_column("Configuração / Componente", style="bold yellow")
    table.add_column("Valor / Status")

    api_key_status = (
        "[green]Configurado[/green]" if settings.FREEAI_API_KEY else "[yellow]Não configurado (Acesso Aberto)[/yellow]"
    )

    table.add_row("Endereço Padrão", f"{settings.HOST}:{settings.PORT}")
    table.add_row("FreeAI Bearer Token", api_key_status)
    table.add_row("Arquivo de Configuração", str(settings.SETTINGS_CONFIG_PATH))
    table.add_row("Provedores Carregados", str(len(settings.providers)))
    table.add_row("Rotas Ativas no Catálogo", str(len(catalog.routes)))

    console.print(table)


@app.command()
def check() -> None:
    """Diagnóstico de saúde das variáveis de ambiente e chaves de API dos provedores."""
    settings = get_settings()

    table = Table(title="Diagnóstico de Disponibilidade de Provedores", show_header=True, header_style="bold cyan")
    table.add_column("Provedor", style="bold yellow")
    table.add_column("Variável de Ambiente", style="blue")
    table.add_column("Modelos Associados", style="magenta")
    table.add_column("Status da Chave", style="bold")

    for provider in settings.providers:
        models_count = len(provider.models)
        status_str = (
            "[green]Pronto / Chave Presente[/green]" if provider.api_key else "[red]Ausente / Chave Não Detectada[/red]"
        )
        table.add_row(provider.display_name, provider.api_key_env, str(models_count), status_str)

    console.print(table)


@app.command()
def ping(
    alias: Annotated[str, typer.Option("--alias", "-a", help="Alias ou ID do modelo para testar")] = "chat",
    prompt: Annotated[str, typer.Option("--prompt", "-p", help="Prompt curto para enviar")] = "Responder apenas 'OK'.",
) -> None:
    """Envia uma requisição de teste para o modelo/alias especificado via Router."""
    console.print(f"[bold cyan]Enviando ping para o modelo/alias '{alias}'...[/bold cyan]")
    settings = get_settings()
    catalog = build_router_catalog(settings)
    router = Router(
        catalog=catalog,
        minute_cooldown_seconds=settings.router_settings.minute_cooldown_seconds,
        daily_cooldown_seconds=settings.router_settings.daily_cooldown_seconds,
        num_retries=settings.router_settings.num_retries,
    )

    async def _run() -> None:
        try:
            response = await router.acompletion(
                model=alias,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
            )
            content = response.choices[0].message.content
            console.print(f"[bold green]✓ Sucesso![/bold green] Resposta: {content}")
        except Exception as e:
            console.print(f"[bold red]✗ Erro ao comunicar com '{alias}': {e}[/bold red]")
            raise typer.Exit(code=1) from e

    asyncio.run(_run())


if __name__ == "__main__":
    app()
