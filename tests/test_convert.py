import json
from datetime import datetime
from pathlib import Path

import pytest

from wltk.cli import main
from wltk.logio import COMMON, FORMATS, parse_log

COMBINED_EXTRA = (
    '127.0.0.1 - - [10/Jul/2025:09:30:00 +0700] "GET /index.html HTTP/1.1" '
    '200 1234 "http://example.com/start" "Mozilla/5.0" "extra-info"'
)
COMBINED = (
    '10.0.0.2 - bob [10/Jul/2025:09:31:00 +0700] "POST /login HTTP/1.1" '
    '302 - "-" "curl/8.0"'
)
COMMON_LINE = '10.0.0.3 - - [10/Jul/2025:09:32:00 +0700] "GET /a.gif HTTP/1.0" 404 512'


def write_log(tmp_path: Path, *lines: str) -> str:
    path = tmp_path / "access.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def test_combined_with_extra_field(tmp_path: Path) -> None:
    records = list(parse_log(write_log(tmp_path, COMBINED_EXTRA)))

    assert len(records) == 1
    record = records[0]
    assert record["hostname"] == "127.0.0.1"
    assert record["method"] == "GET"
    assert record["url"] == "/index.html"
    assert record["status"] == 200
    assert record["size"] == 1234
    assert record["referer"] == "http://example.com/start"
    assert record["user_agent"] == "Mozilla/5.0"
    assert record["extra"] == "extra-info"
    assert isinstance(record["time"], datetime)


def test_combined_without_extra_field_and_dash_size(tmp_path: Path) -> None:
    record = next(parse_log(write_log(tmp_path, COMBINED)))

    assert record["size"] == 0
    assert record["userid"] == "bob"
    assert record["extra"] is None


def test_common_format(tmp_path: Path) -> None:
    record = next(parse_log(write_log(tmp_path, COMMON_LINE), COMMON))

    assert list(record) == list(COMMON.groupindex)
    assert record["status"] == 404


def test_invalid_time_becomes_none(tmp_path: Path) -> None:
    line = COMBINED.replace("10/Jul/2025", "99/Jul/2025")

    assert next(parse_log(write_log(tmp_path, line)))["time"] is None


def test_malformed_lines_are_skipped(tmp_path: Path) -> None:
    records = list(parse_log(write_log(tmp_path, "garbage", COMBINED_EXTRA, "")))

    assert len(records) == 1


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list(parse_log(str(tmp_path / "nope.log")))


def test_formats_registry() -> None:
    assert set(FORMATS) == {"combined", "common"}


def test_cli_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["to_csv", write_log(tmp_path, COMBINED_EXTRA)]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("hostname,identity,userid,time")
    assert "/index.html" in lines[1]
    assert "2025-07-10T09:30:00+07:00" in lines[1]


def test_cli_output_file_and_limit(tmp_path: Path) -> None:
    log = write_log(tmp_path, COMBINED_EXTRA, COMBINED)
    out = tmp_path / "out.csv"

    assert main(["to_csv", log, "-o", str(out), "-n", "1"]) == 0

    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "/index.html" in lines[1]


def test_cli_no_match_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out.csv"

    assert main(["to_csv", write_log(tmp_path, "garbage"), "-o", str(out)]) == 1
    assert "no lines matched" in capsys.readouterr().err
    assert not out.exists()


def test_cli_missing_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["to_csv", str(tmp_path / "nope.log")]) == 1
    assert "wltk:" in capsys.readouterr().err


def test_to_json_lines(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = write_log(tmp_path, COMBINED_EXTRA, COMBINED)

    assert main(["to_json", log, "-n", "1"]) == 0

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(records) == 1
    assert records[0]["status"] == 200
    assert records[0]["size"] == 1234
    assert records[0]["time"] == "2025-07-10T09:30:00+07:00"


def test_to_json_array_to_file(tmp_path: Path) -> None:
    log = write_log(tmp_path, COMBINED_EXTRA, COMBINED)
    out = tmp_path / "log.json"

    assert main(["to_json", log, "--array", "-o", str(out)]) == 0

    records = json.loads(out.read_text(encoding="utf-8"))
    assert [record["url"] for record in records] == ["/index.html", "/login"]


def test_to_json_no_match_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["to_json", write_log(tmp_path, "garbage")]) == 1
    assert "no lines matched" in capsys.readouterr().err
