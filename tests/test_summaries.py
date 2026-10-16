from pathlib import Path

import pytest

from wltk.cli import main


def entry(host: str, time: str, url: str, status: int, size: str, agent: str) -> str:
    return (
        f'{host} - - [{time} +0000] "GET {url} HTTP/1.1" {status} {size} '
        f'"-" "{agent}"\n'
    )


LINES = [
    entry("1.1.1.1", "10/Jul/2025:09:05:00", "/a", 200, "100", "Mozilla"),
    entry("1.1.1.1", "10/Jul/2025:09:10:00", "/a", 200, "300", "Mozilla"),
    entry("2.2.2.2", "10/Jul/2025:09:20:00", "/b", 404, "-", "curl"),
    entry("1.1.1.1", "10/Jul/2025:10:30:00", "/c", 500, "50", "Mozilla"),
    entry("3.3.3.3", "11/Jul/2025:10:30:00", "/a", 200, "1000", "Mozilla"),
    "not a log line\n",
]


@pytest.fixture
def log(tmp_path: Path) -> str:
    path = tmp_path / "access.log"
    path.write_text("".join(LINES), encoding="utf-8")
    return str(path)


def run_csv(argv: list[str], capsys: pytest.CaptureFixture[str]) -> list[list[str]]:
    assert main([*argv, "--csv"]) == 0
    return [row.split(",") for row in capsys.readouterr().out.splitlines()]


def test_top_hostname_by_count(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    rows = run_csv(["top", log, "-n", "2"], capsys)

    assert rows == [
        ["count", "percent", "hostname"],
        ["3", "60.0", "1.1.1.1"],
        ["1", "20.0", "2.2.2.2"],
    ]


def test_top_by_bytes(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    rows = run_csv(["top", log, "-w", "bytes", "-n", "1"], capsys)

    assert rows[1] == ["1000", "69.0", "3.3.3.3"]


def test_top_by_url_and_status(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_csv(["top", log, "-b", "url", "-n", "1"], capsys)[1][2] == "/a"
    assert run_csv(["top", log, "-b", "status", "-n", "1"], capsys)[1][2] == "200"


def test_rare_lists_one_offs_first(
    log: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = run_csv(["rare", log, "-b", "url", "-n", "2"], capsys)

    assert [row[2] for row in rows[1:]] == ["/b", "/c"]
    assert rows[1][0] == "1"


def test_stats_per_hour(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    rows = run_csv(["stats", log], capsys)

    assert rows == [
        ["hour", "requests", "visitors", "bytes", "errors"],
        ["2025-07-10 09:00", "3", "2", "400", "1"],
        ["2025-07-10 10:00", "1", "1", "50", "1"],
        ["2025-07-11 10:00", "1", "1", "1000", "0"],
    ]


def test_stats_per_day(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    rows = run_csv(["stats", log, "-i", "day"], capsys)

    assert rows[1:] == [
        ["2025-07-10", "4", "2", "450", "2"],
        ["2025-07-11", "1", "1", "1000", "0"],
    ]


def test_table_output_is_aligned(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["top", log, "-n", "1"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["count", "percent", "hostname"]
    assert lines[1].split() == ["3", "60.0", "1.1.1.1"]


def test_output_file_is_csv(log: str, tmp_path: Path) -> None:
    out = tmp_path / "top.csv"

    assert main(["top", log, "-n", "1", "-o", str(out)]) == 0

    assert out.read_text(encoding="utf-8").splitlines() == [
        "count,percent,hostname",
        "3,60.0,1.1.1.1",
    ]


def test_nothing_parsed_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    junk = tmp_path / "junk.log"
    junk.write_text("garbage\n", encoding="utf-8")

    assert main(["top", str(junk)]) == 1
    assert "no lines" in capsys.readouterr().err
