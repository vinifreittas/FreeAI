import typer

from freeai.core import build_router_catalog, get_settings, load_vault

app = typer.Typer(help="Status dos provedores e rotas mapeadas.")


@app.command(name="status")
def status() -> None:
    """Exibe o diagnóstico dos provedores, modelos mapeados e configurações ativas."""
    settings = get_settings()
    catalog = build_router_catalog(settings)
    vault = load_vault()

    typer.secho("\n⚡ FreeAI Gateway — Status do Sistema\n", bold=True, fg=typer.colors.CYAN)
    typer.secho(
        f"  Host: {vault.get('HOST', settings.HOST)} | Porta: {vault.get('PORT', settings.PORT)}", fg=typer.colors.WHITE
    )
    bearer = "Protegido" if settings.FREEAI_API_KEY else "Livre (sem token)"
    typer.secho(f"  Bearer Token: {bearer}\n", fg=typer.colors.WHITE)

    typer.secho("  Provedores:", bold=True)
    for p in settings.providers:
        status_icon = "✔ Ativo" if p.api_key else "✘ Não configurado"
        color = typer.colors.GREEN if p.api_key else typer.colors.RED
        typer.secho(f"    • {p.display_name:<20} {status_icon} ({len(p.models)} modelos)", fg=color)

    typer.secho(f"\n  Rotas e Aliases Mapeados ({len(catalog.routes)}):", bold=True)
    for alias in settings.aliases:
        targets = catalog.get_targets(alias.alias)
        chain = " ➔ ".join(t.litellm_model for t in targets) if targets else "Nenhum alvo ativo"
        color = typer.colors.GREEN if targets else typer.colors.YELLOW
        typer.secho(f"    [{alias.alias:<7}] {chain}", fg=color)
    typer.echo()
