from typer.testing import CliRunner

from freeai.cli.main import app

runner = CliRunner()


def test_cli_models() -> None:
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "Aliases de Rotas" in result.output


def test_cli_status() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Status do FreeAI Gateway" in result.output


def test_cli_check() -> None:
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Diagnóstico de Disponibilidade" in result.output
