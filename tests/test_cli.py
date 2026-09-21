import importlib
import json
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from mactop.metrics_store import MetricsSnapshot

cli = importlib.import_module("mactop.main")


@pytest.mark.parametrize(
    "arguments",
    [["-r", "0"], ["-r", "-1"], ["-r", "nan"], ["-r", "inf"], ["--count", "2"]],
)
def test_cli_rejects_invalid_sampling_options(arguments):
    result = CliRunner().invoke(cli.main, arguments)
    assert result.exit_code == 2


def test_json_count_and_shutdown(monkeypatch):
    manager = Mock()
    manager.next_sample.side_effect = [
        MetricsSnapshot(timestamp=1),
        MetricsSnapshot(timestamp=2),
    ]
    monkeypatch.setattr(cli, "MetricsManager", Mock(return_value=manager))
    result = CliRunner().invoke(cli.main, ["--json", "--count", "2"])
    assert result.exit_code == 0, result.output
    assert [json.loads(line)["timestamp"] for line in result.output.splitlines()] == [
        1,
        2,
    ]
    manager.stop.assert_called_once()


def test_failed_collector_is_not_an_endless_json_stream(monkeypatch):
    manager = Mock()
    manager.next_sample.side_effect = RuntimeError("native failure")
    monkeypatch.setattr(cli, "MetricsManager", Mock(return_value=manager))
    result = CliRunner().invoke(cli.main, ["--json", "--count", "1"])
    assert result.exit_code == 1
    assert "native failure" in result.output
    manager.stop.assert_called_once()


@pytest.mark.parametrize(
    "failure,exit_code", [(None, 0), (RuntimeError("render failed"), 1)]
)
def test_tui_exit_and_failure_always_stop_sampling(monkeypatch, failure, exit_code):
    manager = Mock()
    app = Mock(failure=failure)
    monkeypatch.setattr(cli, "MetricsManager", Mock(return_value=manager))
    monkeypatch.setattr(cli, "MactopApp", Mock(return_value=app))
    result = CliRunner().invoke(cli.main, ["-t", "m1.xml"])
    assert result.exit_code == exit_code, result.output
    app.run.assert_called_once()
    manager.stop.assert_called_once()
