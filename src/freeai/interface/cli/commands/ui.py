import typer

app = typer.Typer(help="Inicia a interface web do Streamlit.")


@app.command(name="ui")
def ui() -> None:
    """Explicitly start the Streamlit web interface."""
    from freeai.interface.web.app import main as run_web

    run_web()
