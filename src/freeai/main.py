import typer

from freeai.interface.cli.commands import register_commands

app = typer.Typer(
    name="freeai",
    help="⚡ FreeAI — Gateway e Roteador Inteligente para Provedores Gratuitos",
    no_args_is_help=False,
)

register_commands(app)


@app.callback(invoke_without_command=True)
def default_callback(ctx: typer.Context) -> None:
    """Se nenhum subcomando for fornecido, inicia a interface gráfica Streamlit."""
    if ctx.invoked_subcommand is None:
        from freeai.interface.web.app import main as run_web

        run_web()
        raise typer.Exit()
