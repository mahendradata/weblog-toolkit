from pathlib import Path

import pytest

from wltk.cli import main

LINES = [
    '1.1.1.1 - - [10/Jul/2025:09:05:00 +0000] "GET /a HTTP/1.1" 200 100 "-" "Moz"\n',
    '1.1.1.1 - - [10/Jul/2025:09:10:00 +0000] "GET /a|b HTTP/1.1" 404 300 "-" "Moz"\n',
    '2.2.2.2 - - [10/Jul/2025:10:20:00 +0000] "GET /<script> HTTP/1.1" 500 - "-" "x"\n',
    "not a log line\n",
]


@pytest.fixture
def log(tmp_path: Path) -> str:
    path = tmp_path / "access.log"
    path.write_text("".join(LINES), encoding="utf-8")
    return str(path)


def test_report_markdown(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", log, "--title", "Case 42"]) == 0

    out = capsys.readouterr().out
    assert out.startswith("# Case 42\n")
    assert "| Requests | 3 |" in out
    assert "| Unique clients | 2 |" in out
    assert "| Bytes sent | 400 |" in out
    assert "| Error rate (4xx/5xx) | 66.7% |" in out
    assert "| Period | 2025-07-10 09:05 to 2025-07-10 10:20 |" in out
    assert "## Traffic per hour" in out
    assert "| 2025-07-10 09:00 | 2 | 1 | 400 | 1 |" in out
    assert "| 2 | 66.7 | 1.1.1.1 |" in out


def test_report_escapes_untrusted_values(
    log: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["report", log]) == 0

    out = capsys.readouterr().out
    assert r"/a\|b" in out
    assert "&lt;script&gt;" in out
    assert "<script>" not in out


def test_report_html_file_by_extension(log: str, tmp_path: Path) -> None:
    out = tmp_path / "report.html"

    assert main(["report", log, "-o", str(out)]) == 0

    page = out.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    assert "<h2>Top URLs</h2>" in page
    assert "&lt;script&gt;" in page
    assert "<script>" not in page


def test_report_html_format_to_stdout(
    log: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["report", log, "-f", "html"]) == 0

    assert capsys.readouterr().out.startswith("<!doctype html>")


def test_report_uses_days_for_long_periods(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "long.log"
    path.write_text(LINES[0] + LINES[0].replace("10/Jul", "14/Jul"), encoding="utf-8")

    assert main(["report", str(path)]) == 0

    assert "## Traffic per day" in capsys.readouterr().out


def test_report_nothing_parsed_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    junk = tmp_path / "junk.log"
    junk.write_text("garbage\n", encoding="utf-8")

    assert main(["report", str(junk)]) == 1
    assert "no lines" in capsys.readouterr().err


def test_report_has_flagged_sections(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    attack = (
        "6.6.6.6 - - [10/Jul/2025:09:05:00 +0000] "
        '"GET /?q=1+union+select+1 HTTP/1.1" 200 1 "-" "x"\n'
    )
    path = tmp_path / "attack.log"
    path.write_text(attack, encoding="utf-8")

    assert main(["report", str(path)]) == 0

    out = capsys.readouterr().out
    assert "## Flagged requests by attack category" in out
    assert "| 1 | 100.0 | sql-injection |" in out
    assert "| 1 | 100.0 | 6.6.6.6 |" in out


def test_report_without_readable_times(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    line = LINES[0].replace("10/Jul/2025", "99/Jul/2025")
    path = tmp_path / "bad_time.log"
    path.write_text(line, encoding="utf-8")

    assert main(["report", str(path)]) == 0

    assert "| Period | unknown |" in capsys.readouterr().out
