from pathlib import Path

import pytest

from wltk import __version__
from wltk.cli import main
from wltk.tools import CATEGORIES, TOOLS

README = Path(__file__).parent.parent / "README.md"


def test_help_lists_tools_by_category(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])

    out = capsys.readouterr().out
    for category in CATEGORIES:
        assert category in out
    for tool in TOOLS:
        assert tool.NAME in out
    assert "==SUPPRESS==" not in out


def test_every_tool_is_documented_in_the_readme() -> None:
    readme = README.read_text(encoding="utf-8")

    for tool in TOOLS:
        assert f"`{tool.NAME}`" in readme
        assert tool.HELP in readme


def test_tool_names_are_unique() -> None:
    names = [tool.NAME for tool in TOOLS]

    assert len(names) == len(set(names))


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])

    assert __version__ in capsys.readouterr().out


def test_tool_is_required() -> None:
    with pytest.raises(SystemExit):
        main([])
