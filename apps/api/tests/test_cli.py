"""Tests for the CLI entrypoints that don't require an API key."""

from __future__ import annotations

from pathlib import Path

import pytest

from obelisk_api.cli import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ATHLETE = str(PROJECT_ROOT / "data" / "sample_athlete.json")


def test_demo_offline_builds_and_renders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["demo-offline", "--athlete", ATHLETE])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Back Squat" in out and "220 → 240" in out
    # A workbook was written under ./runs/<id>/.
    xlsx = list((tmp_path / "runs").rglob("cycle_plan.xlsx"))
    assert len(xlsx) == 1


def test_list_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    rc = main(["list"])
    assert rc == 0
    assert "No saved Blocks" in capsys.readouterr().out


def test_new_block_without_key_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("obelisk_api.agent.loop.load_dotenv", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rc = main(["new-block", "--athlete", ATHLETE, "--goal", "test goal"])
    assert rc == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_missing_athlete_file_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("obelisk_api.agent.loop.load_dotenv", lambda: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    rc = main(["new-block", "--athlete", "nope.json", "--goal", "x"])
    assert rc == 1
    assert "error" in capsys.readouterr().err.lower()
