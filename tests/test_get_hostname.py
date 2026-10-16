from pathlib import Path

import pytest

from wltk.cli import main
from wltk.tools.get_hostname import make_keep

LINE_A1 = '1.1.1.1 - - [10/Jul/2025:09:30:00 +0700] "GET /a HTTP/1.1" 200 1 "-" "x"\n'
LINE_B = '2.2.2.2 - - [10/Jul/2025:09:31:00 +0700] "GET /b HTTP/1.1" 200 1 "-" "x"\n'
LINE_A2 = '1.1.1.1 - - [10/Jul/2025:09:32:00 +0700] "GET /c HTTP/1.1" 404 1 "-" "x"\n'
LINE_PREFIX = (
    '1.1.1.10 - - [10/Jul/2025:09:33:00 +0700] "GET /d HTTP/1.1" 200 1 "-" "x"\n'
)


@pytest.fixture
def log(tmp_path: Path) -> str:
    path = tmp_path / "access.log"
    path.write_text(LINE_A1 + LINE_B + LINE_A2 + LINE_PREFIX, encoding="utf-8")
    return str(path)


def test_exact_ip_only() -> None:
    keep = make_keep(["1.1.1.1"])

    assert keep({"hostname": "1.1.1.1"})
    assert not keep({"hostname": "1.1.1.10"})


def test_multiple_sources() -> None:
    keep = make_keep(["1.1.1.1", "2.2.2.2"])

    assert keep({"hostname": "2.2.2.2"})
    assert not keep({"hostname": "3.3.3.3"})


def test_cidr_range() -> None:
    keep = make_keep(["1.1.1.0/24"])

    assert keep({"hostname": "1.1.1.10"})
    assert not keep({"hostname": "1.1.2.1"})


def test_plain_hostname() -> None:
    keep = make_keep(["bot.example.com"])

    assert keep({"hostname": "bot.example.com"})
    assert not keep({"hostname": "1.1.1.1"})


def test_cli_stdout_keeps_lines_unchanged(
    log: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["get_hostname", log, "-i", "1.1.1.1"]) == 0

    assert capsys.readouterr().out.splitlines(keepends=True) == [LINE_A1, LINE_A2]


def test_cli_output_file(log: str, tmp_path: Path) -> None:
    out = tmp_path / "hostname.log"

    assert main(["get_hostname", log, "-i", "2.2.2.2", "-o", str(out)]) == 0

    assert out.read_text(encoding="utf-8") == LINE_B


def test_cli_no_match_fails(
    log: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "hostname.log"

    assert main(["get_hostname", log, "-i", "9.9.9.9", "-o", str(out)]) == 1
    assert "no matching lines" in capsys.readouterr().err
    assert not out.exists()


def test_cli_ip_is_required(log: str) -> None:
    with pytest.raises(SystemExit):
        main(["get_hostname", log])


def test_cli_missing_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["get_hostname", str(tmp_path / "nope.log"), "-i", "1.1.1.1"]) == 1
    assert "wltk:" in capsys.readouterr().err
