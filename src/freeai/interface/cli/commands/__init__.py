import typer

from freeai.interface.cli.commands.serve import app as serve_app
from freeai.interface.cli.commands.setup import app as setup_app
from freeai.interface.cli.commands.status import app as status_app
from freeai.interface.cli.commands.test import app as test_app
from freeai.interface.cli.commands.ui import app as ui_app


def register_commands(cli: typer.Typer) -> None:
    """Registra todos os subcomandos modulares no Typer principal."""
    cli.add_typer(serve_app)
    cli.add_typer(setup_app)
    cli.add_typer(status_app)
    cli.add_typer(test_app)
    cli.add_typer(ui_app)


__all__ = ["register_commands"]
