import typer

app = typer.Typer(help="Inicia a interface web do Streamlit.")


@app.command(name="ui")
def ui() -> None:
    """Inicia explicitamente a interface web do Streamlit."""
    from freeai.interface.web.app import main as run_web

    run_web()
