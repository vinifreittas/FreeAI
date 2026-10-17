from unittest.mock import patch

from typer.testing import CliRunner

from freeai.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "FreeAI" in result.output
    assert "serve" in result.output
    assert "status" in result.output
    assert "test" in result.output
    assert "ui" in result.output


def test_cli_status_command():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Status do Sistema" in result.output
    assert "Provedores:" in result.output


def test_cli_test_command():
    result = runner.invoke(app, ["test"])
    # If no providers active, exit code is 1 with explanation
    assert "FreeAI Gateway — Teste de Conexão dos Modelos" in result.output


def test_cli_default_callback_invokes_ui():
    with patch("freeai.interface.web.app.main") as mock_web_main:
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_web_main.assert_called_once()


def test_cli_ui_command_invokes_ui():
    with patch("freeai.interface.web.app.main") as mock_web_main:
        result = runner.invoke(app, ["ui"])
        assert result.exit_code == 0
        mock_web_main.assert_called_once()
