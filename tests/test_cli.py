from typer.testing import CliRunner

from jobhunt.cli import app

runner = CliRunner()


def test_cli_help_exits_successfully():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Remote-first job hunt automation" in result.output


def test_sources_list_command_outputs_known_sources():
    result = runner.invoke(app, ["sources", "list"])
    assert result.exit_code == 0
    assert "remotive" in result.output
    assert "adzuna" in result.output


def test_sources_check_reports_adzuna_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    result = runner.invoke(app, ["sources", "check"])
    assert result.exit_code == 0
    assert "adzuna" in result.output


def test_scan_rejects_unknown_source():
    result = runner.invoke(app, ["scan", "--source", "does-not-exist"])
    assert result.exit_code != 0
