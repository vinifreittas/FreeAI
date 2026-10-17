import asyncio

import typer

from freeai.core import get_settings
from freeai.services.model_tester import test_all_models

app = typer.Typer(help="Teste de conectividade dos modelos configurados.")


@app.command(name="test")
def test_models(
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="Filtrar por provedor (ex: gemini, groq, openrouter)"
    ),
    timeout: float = typer.Option(10.0, "--timeout", "-t", help="Timeout em segundos por modelo"),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Número máximo de requisições concorrentes"),
) -> None:
    """Testa todos os modelos conectados de provedores aprovados/configurados."""
    settings = get_settings()
    active_providers = [p for p in settings.providers if p.api_key]

    typer.secho("\n⚡ FreeAI Gateway — Teste de Conexão dos Modelos\n", bold=True, fg=typer.colors.CYAN)

    if not active_providers:
        typer.secho(
            "  ✘ Nenhum provedor configurado com chave de API válida.",
            fg=typer.colors.RED,
            bold=True,
        )
        typer.secho(
            "  Execute 'freeai setup' ou acesse o Web UI para configurar suas chaves de API.\n",
            fg=typer.colors.WHITE,
        )
        raise typer.Exit(1)

    prov_filter_msg = f" (filtro: {provider})" if provider else ""
    typer.echo(f"  Testando modelos conectados{prov_filter_msg} (concorrência={concurrency}, timeout={timeout}s)...\n")

    results = asyncio.run(
        test_all_models(
            settings=settings,
            provider_id=provider,
            max_concurrency=concurrency,
            timeout=timeout,
        )
    )

    if not results:
        typer.secho("  Nenhum modelo encontrado para o filtro especificado.\n", fg=typer.colors.YELLOW)
        return

    typer.secho(
        f"  {'PROVEDOR':<14} {'MODELO':<36} {'STATUS':<14} {'LATÊNCIA':<10} DETALHES",
        bold=True,
        fg=typer.colors.WHITE,
    )
    typer.secho("  " + "—" * 95, fg=typer.colors.WHITE)

    ok_count = 0
    rl_count = 0
    err_count = 0

    for r in results:
        if r.status == "OK":
            ok_count += 1
            status_text = "✔ OK"
            color = typer.colors.GREEN
        elif r.status == "Rate Limit":
            rl_count += 1
            status_text = "⚠️ RateLimit"
            color = typer.colors.YELLOW
        else:
            err_count += 1
            status_text = "✘ Falha"
            color = typer.colors.RED

        lat_text = f"{r.latency_ms}ms"
        model_display = r.model_id if len(r.model_id) <= 34 else f"{r.model_id[:31]}..."
        typer.secho(
            f"  {r.provider_id:<14} {model_display:<36} {status_text:<14} {lat_text:<10} {r.details}",
            fg=color,
        )

    typer.echo()
    summary = (
        f"  Resumo: {len(results)} modelos | ✔ {ok_count} operacionais | ⚠️ {rl_count} rate limit | ✘ {err_count} falhas"
    )
    summary_color = typer.colors.GREEN if err_count == 0 else typer.colors.YELLOW
    typer.secho(summary + "\n", bold=True, fg=summary_color)
