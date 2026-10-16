from pathlib import Path

import pytest

from wltk.cli import main

ZONE = "+0700"


def entry(host: str, time: str, request: str, status: int, tail: str = "") -> str:
    stamp = f"[10/Jul/2025:{time} {ZONE}]"
    return f'{host} - - {stamp} "{request}" {status} 1{tail}\n'


GET_OK = entry("1.1.1.1", "09:30:00", "GET /index.html HTTP/1.1", 200, ' "-" "Moz"')
POST_LOGIN = entry(
    "2.2.2.2", "10:00:00", "POST /wp-login.php HTTP/1.1", 401, ' "-" "curl/8.0"'
)
TRAVERSAL = entry(
    "3.3.3.3", "11:00:00", "GET /a/%2e%2e/etc/passwd HTTP/1.1", 404, ' "-" "SQLMap"'
)
COMMON_LINE = entry("4.4.4.4", "12:00:00", "DELETE /x HTTP/1.0", 500)
JUNK = "not a log line\n"
ALL = [GET_OK, POST_LOGIN, TRAVERSAL, COMMON_LINE, JUNK]

DAY = "2025-07-10T"


@pytest.fixture
def log(tmp_path: Path) -> str:
    path = tmp_path / "access.log"
    path.write_text("".join(ALL), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["get_time", "--from", f"{DAY}10:00:00+07:00"], ALL[1:4]),
        (["get_time", "--to", f"{DAY}10:00:00+07:00"], ALL[:2]),
        (["get_time", "--from", f"{DAY}09:45", "--to", f"{DAY}10:30"], [POST_LOGIN]),
        (["get_time", "--from", f"{DAY}03:00Z", "--to", f"{DAY}03:00Z"], [POST_LOGIN]),
        (["get_url", "-u", r"\.php$"], [POST_LOGIN]),
        (["get_url", "-u", r"\.\./etc"], [TRAVERSAL]),
        (["get_status", "-s", "404"], [TRAVERSAL]),
        (["get_status", "-s", "4xx"], [POST_LOGIN, TRAVERSAL]),
        (["get_status", "-s", "200", "-s", "5xx"], [GET_OK, COMMON_LINE]),
        (["get_agent", "-a", "sqlmap|CURL"], [POST_LOGIN, TRAVERSAL]),
        (["get_method", "-m", "post", "-m", "DELETE"], [POST_LOGIN, COMMON_LINE]),
        (["get_hostname", "-i", "1.1.1.0/30", "-i", "4.4.4.4"], [GET_OK, COMMON_LINE]),
    ],
)
def test_filter_outputs_matching_raw_lines(
    log: str,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
    expected: list[str],
) -> None:
    assert main([args[0], log, *args[1:]]) == 0

    assert capsys.readouterr().out.splitlines(keepends=True) == expected


def test_get_time_needs_a_bound(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["get_time", log]) == 2
    assert "--from" in capsys.readouterr().err


def test_get_status_rejects_invalid_value(log: str) -> None:
    with pytest.raises(SystemExit):
        main(["get_status", log, "-s", "abc"])


def test_filter_no_match_fails(log: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["get_method", log, "-m", "TRACE"]) == 1
    assert "no matching lines" in capsys.readouterr().err
