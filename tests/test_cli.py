from typer.testing import CliRunner

from freeai.cli.main import app

runner = CliRunner()


def test_cli_help():
    """Test freeai --help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "FreeAI" in result.output


def test_cli_status():
    """Test freeai status command output."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Status do FreeAI Gateway" in result.output
    assert "Endereço Padrão" in result.output


def test_cli_models():
    """Test freeai models command output."""
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "Modelos & Aliases Configurados" in result.output
    assert "chat" in result.output
    assert "fast" in result.output


def test_cli_check():
    """Test freeai check command output."""
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Diagnóstico de Saúde" in result.output
    assert "chat" in result.output
